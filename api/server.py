"""VoiceCrashLab FastAPI adapter.

Exposes the EXISTING testing pipeline as an HTTP API for the React frontend.
It only wraps functions that the Streamlit dashboard already uses
(dashboard/dashboard_app.py) and never reimplements testing logic:
- the full generation chain app.run_pipeline.run_pipeline
(scenarios generator + TTS + audio attacks + manifest)
- app.agent_adapters.api_agent.APIAgentAdapter.process_test / test_agent_connection
- audio.stt.groq_stt.transcribe_audio
- evaluator.groq_judge.evaluate_with_groq
- dashboard.dashboard_app.generate_llm_fix (guarded import; optional feature)
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from dotenv import load_dotenv  # noqa: E402  (advise: keep)

load_dotenv(ROOT_DIR / ".env")

from app.agent_adapters.api_agent import APIAgentAdapter, test_agent_connection  # noqa: E402
from app.run_pipeline import run_pipeline  # noqa: E402
from audio.stt.groq_stt import transcribe_audio  # noqa: E402
from evaluator.groq_judge import evaluate_with_groq  # noqa: E402

DATA_DIR = ROOT_DIR / "data"

try:
    # dashboard_app.py executes Streamlit UI code at import time, so we cannot
    # import it as a module. Instead we load ONLY the existing generate_llm_fix
    # function source verbatim (no logic is reimplemented, the file is untouched).
    import ast as _ast

    _dashboard_source = (ROOT_DIR / "dashboard" / "dashboard_app.py").read_text(encoding="utf-8")
    _tree = _ast.parse(_dashboard_source)
    generate_llm_fix = None
    for _node in _tree.body:
        if isinstance(_node, _ast.FunctionDef) and _node.name == "generate_llm_fix":
            _ns: dict[str, Any] = {"os": os, "json": json}
            exec(_ast.get_source_segment(_dashboard_source, _node), _ns)
            generate_llm_fix = _ns["generate_llm_fix"]
            break
    _FIX_AVAILABLE = generate_llm_fix is not None
except Exception as _exc:  # pragma: no cover
    generate_llm_fix = None  # type: ignore[assignment]
    _FIX_AVAILABLE = False
    print(f"[api] LLM fix suggestions unavailable (dashboard function not found): {_exc}", flush=True)


app = FastAPI(title="VoiceCrashLab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _atomic_json(path: Path, payload: list[Any]) -> None:
    """Same atomic write pattern used by the Streamlit dashboard loop.

    On Windows a concurrent reader (e.g. GET /api/results) can hold the
    destination file open exactly when os.replace() runs; retry briefly
    until the reader releases the lock instead of crashing the run.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    last_error: OSError | None = None
    for attempt in range(6):
        try:
            tmp.replace(path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.05 * (attempt + 1))
    try:
        tmp.unlink()
    except OSError:
        pass
    raise last_error


def _read_json(path: Path, error_detail: str) -> Any:
    if not path.is_file():
        raise HTTPException(status_code=404, detail=error_detail)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not read data file: {exc}") from exc


def _benchmark_id_path(benchmark_id: str) -> Path:
    """Resolve a benchmark id to its file, blocking path traversal."""
    if not benchmark_id or "/" in benchmark_id or "\\" in benchmark_id or ".." in benchmark_id:
        raise HTTPException(status_code=400, detail="Invalid benchmark id.")
    path = DATA_DIR / "benchmarks" / f"{benchmark_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Benchmark not found: {benchmark_id}")
    return path


def _agent_context_from_benchmark(benchmark: dict) -> dict:
    return {
        "agent_role": benchmark.get("agent_role", ""),
        "business_context": benchmark.get("business_context", ""),
        "supported_tasks": benchmark.get("supported_tasks", []),
        "language": benchmark.get("language", ""),
    }


# --------------------------------------------------------------------------- #
# Health & discovery                                                          #
# --------------------------------------------------------------------------- #


class FeatureSupport(BaseModel):
    overview_metrics: bool = True
    scenario_generation: bool = True
    agent_connection_test: bool = True
    per_test_execution: bool = True
    transcripts: bool = True
    latency_metrics: bool = False  # pipeline does not record any latency metric
    llm_fix_suggestions: bool = _FIX_AVAILABLE


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": "VoiceCrashLab API",
        "version": "1.0.0",
        "features": FeatureSupport().model_dump(),
    }


@app.get("/api/benchmarks")
def list_benchmarks() -> dict:
    benchmarks_dir = DATA_DIR / "benchmarks"
    items: list[dict] = []
    if benchmarks_dir.is_dir():
        for path in sorted(benchmarks_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue  # legacy/malformed benchmark archives are not API-visible
            items.append(
                {
                    "benchmark_id": data.get("benchmark_id", path.stem),
                    "agent_role": data.get("agent_role", ""),
                    "language": data.get("language", ""),
                    "scenario_count": data.get("scenario_count", 0),
                    "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                }
            )
    return {"items": items}


@app.get("/api/benchmarks/{benchmark_id}")
def get_benchmark(benchmark_id: str) -> dict:
    return _read_json(_benchmark_id_path(benchmark_id), "Benchmark not found.")


@app.get("/api/manifest/{benchmark_id}")
def get_manifest(benchmark_id: str) -> dict:
    path = DATA_DIR / "manifests" / f"{benchmark_id}_manifest.json"
    manifest = _read_json(path, f"Manifest not found for {benchmark_id}. Generate the suite first.")
    return {"items": manifest}


# --------------------------------------------------------------------------- #
# Agent connection check (thin wrap of existing function)                      #
# --------------------------------------------------------------------------- #


class AgentConnectRequest(BaseModel):
    endpoint: str
    name: str = "Voice Agent"
    token: str = ""
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    input_field: str = "audio"
    response_text_field: str = "response"
    response_audio_url_field: str = "audio_url"
    timeout: int = 60


@app.post("/api/agent/connect")
def agent_connect(req: AgentConnectRequest) -> dict:
    try:
        return test_agent_connection(req.model_dump())
    except (ConnectionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Suite generation (existing pipeline)                                         #
# --------------------------------------------------------------------------- #


class GenerateRequest(BaseModel):
    agent_role: str
    business_context: str
    supported_tasks: list[str]
    language: str = "Hinglish"
    scenario_count: int = 5
    voice: str = "Pranav"


@app.post("/api/generate")
def generate(req: GenerateRequest) -> dict:
    try:
        result = run_pipeline(
            agent_role=req.agent_role,
            business_context=req.business_context,
            supported_tasks=req.supported_tasks,
            language=req.language,
            scenario_count=req.scenario_count,
            voice=req.voice,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # generator/TTS errors surface as 502 to keep UI honest
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {exc}") from exc

    benchmark = _read_json(Path(result["benchmark_path"]), "Benchmark file missing after generation.")
    return {
        "pipeline": result,
        "benchmark": {
            "benchmark_id": benchmark.get("benchmark_id"),
            "scenario_count": benchmark.get("scenario_count"),
            "scenario_counts": benchmark.get("scenario_counts"),
        },
        "scenarios": benchmark.get("scenarios", {"speech": [], "reasoning": []}),
        "voice_agent_context": _agent_context_from_benchmark(benchmark),
    }


# --------------------------------------------------------------------------- #
# Test execution (one worker thread per benchmark, dashboard-equivalent loop)   #
# --------------------------------------------------------------------------- #


class ExecuteRequest(BaseModel):
    benchmark_id: str
    name: str = "Voice Agent"
    endpoint: str
    token: str = ""
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    input_field: str = "audio"
    response_text_field: str = "response"
    response_audio_url_field: str = "audio_url"
    timeout: int = 60


EXECUTION_WORKERS = max(1, int(os.getenv("EXECUTION_WORKERS", "5")))

_EXEC_LOCK = threading.Lock()
_EXECUTIONS: dict[str, dict] = {}
_WORKERS: dict[str, threading.Thread] = {}


def _process_test(
    state: dict,
    adapter: APIAgentAdapter,
    context: dict,
    index: int,
    test: dict,
) -> dict:
    """Run a single test end-to-end (agent call + transcription + LLM judge).

    Runs inside the bounded thread pool; returns one bundle with the agent
    response entry, the evaluation record, and its status label.
    """
    benchmark = state["benchmark"]
    test_id = str(test.get("test_id", f"test_{index:03d}"))
    category = str(test.get("category", "speech"))
    scenario = next(
        (s for s in benchmark.get("scenarios", {}).get(category, [])
         if str(s.get("id", "")) == str(test.get("scenario_id", ""))),
        None,
    )
    caller_text = str(scenario.get("caller", "")) if scenario else ""
    with _EXEC_LOCK:
        state["status"][test_id] = "running"

    # --- agent call (existing adapter) ---
    try:
        agent_result = adapter.process_test(test)
        agent_result.update({
            "scenario_id": test.get("scenario_id"),
            "category": test.get("category"),
            "attack_type": test.get("attack_type"),
            "condition": test.get("condition"),
            "audio_path": test.get("audio_path"),
        })
        agent_entry, agent_error = agent_result, None
    except Exception as exc:
        agent_entry, agent_error = {
            "test_id": test_id, "status": "failed", "error": str(exc),
            "scenario_id": test.get("scenario_id"), "category": test.get("category"),
            "attack_type": test.get("attack_type"), "condition": test.get("condition"),
            "audio_path": test.get("audio_path"),
        }, str(exc)

    if agent_error is not None:
        record = {
            "test_id": test_id, "scenario_id": test.get("scenario_id"),
            "category": test.get("category"), "scenario_type": test.get("scenario_type"),
            "attack_type": test.get("attack_type"), "condition": test.get("condition"),
            "audio_path": test.get("audio_path"), "caller_transcript": caller_text,
            "expected": scenario.get("expected", test.get("expected", "")) if scenario else test.get("expected", ""),
            "agent_response": "", "status": "failed", "error": agent_error,
            "evaluation": {"passed": False, "category": "AGENT_REQUEST_FAILURE", "reason": agent_error},
            "suggested_fix": "Check endpoint reachability, authentication, multipart field name, timeout, and the API's accepted audio format.",
            "example_response": "",
        }
        return {"agent_entry": agent_entry, "record": record,
                "evaluated_ok": False, "status": "failed"}

    # --- transcript + evaluation (existing functions, dashboard order) ---
    try:
        if not scenario:
            raise ValueError(f"Scenario not found for {test.get('scenario_id')}")
        if agent_entry.get("response_text"):
            response_text = agent_entry["response_text"]
        elif agent_entry.get("response_audio_path"):
            response_text = transcribe_audio(agent_entry["response_audio_path"])
        else:
            raise ValueError("Agent returned neither response text nor response audio.")
        agent_entry["agent_response"] = response_text

        # Standardize the transcript of the test-save record
        sidecar_dir = DATA_DIR / "results" / "evaluations"
        sidecar = sidecar_dir / f"{test_id}.json"
        if not sidecar.is_file():
            _atomic_json(sidecar, [{
                "test_id": test_id,
                "scenario": {"id": scenario.get("id"), "type": scenario.get("type"),
                             "difficulty": test.get("difficulty", scenario.get("difficulty"))},
                "caller_transcript": caller_text,
                "agent_response": response_text,
            }])

        evaluation = evaluate_with_groq(
            scenario={**scenario, "type": scenario.get("type", test.get("scenario_type", "unknown")),
                      "difficulty": test.get("attack_level", test.get("condition", "unknown")),
                      "language": test.get("language", state.get("language", scenario.get("language")))},
            transcript=caller_text, response=response_text, original_text=caller_text,
            agent_info=context,
        )
        if evaluation.get("passed") is True or generate_llm_fix is None:
            fix = {"suggested_fix": "No fix required; this test passed." if evaluation.get("passed") else "",
                   "example_response": ""}
        else:
            fix = generate_llm_fix(scenario, evaluation, caller_text, response_text, context)
        record = {
            "test_id": test_id, "scenario_id": test.get("scenario_id"),
            "category": test.get("category"), "scenario_type": test.get("scenario_type"),
            "attack_type": test.get("attack_type"), "condition": test.get("condition"),
            "audio_path": test.get("audio_path"), "caller_transcript": caller_text,
            "expected": scenario.get("expected", test.get("expected", "")),
            "agent_response": response_text, "status": "evaluated",
            "evaluation": evaluation, **fix,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"agent_entry": agent_entry, "record": record,
                "evaluated_ok": bool((evaluation or {}).get("passed")),
                "status": "evaluated" if record["status"] == "evaluated" else "evaluation_failed"}
    except Exception as exc:
        record = {
            "test_id": test_id, "scenario_id": test.get("scenario_id"),
            "category": test.get("category"), "scenario_type": test.get("scenario_type"),
            "attack_type": test.get("attack_type"), "condition": test.get("condition"),
            "audio_path": test.get("audio_path"), "caller_transcript": caller_text,
            "expected": scenario.get("expected", test.get("expected", "")) if scenario else test.get("expected", ""),
            "agent_response": agent_entry.get("response_text", ""),
            "status": "evaluation_failed", "error": str(exc),
            "evaluation": {"passed": False, "category": "EVALUATION_ERROR", "reason": str(exc)},
            "suggested_fix": "Evaluation failed. Check GROQ_API_KEY, GROQ_JUDGE_MODEL, and response transcription settings.",
            "example_response": "",
        }
        return {"agent_entry": agent_entry, "record": record,
                "evaluated_ok": False, "status": "evaluation_failed"}


def _worker(benchmark_id: str, adapter: APIAgentAdapter, context: dict) -> None:
    state = _EXECUTIONS[benchmark_id]
    run_dir = DATA_DIR / "results" / benchmark_id
    response_file = run_dir / "agent_responses.json"
    evaluation_file = run_dir / "evaluation_results.json"

    responses: list[dict] = []
    evaluations: list[dict] = []
    try:
        state.update(total=len(state["manifest"]), completed=0, passed=0, failed=0, running=True)

        with ThreadPoolExecutor(max_workers=EXECUTION_WORKERS) as pool:
            futures = [
                pool.submit(_process_test, state, adapter, context, index, test)
                for index, test in enumerate(state["manifest"], start=1)
            ]
            for future in as_completed(futures):
                try:
                    bundle = future.result()
                except Exception as exc:  # defensive: pool thread should never raise past here
                    with _EXEC_LOCK:
                        state["completed"] += 1
                        state["failed"] += 1
                    print(f"[api] execution task error: {exc}", flush=True)
                    continue

                responses.append(bundle["agent_entry"])
                evaluations.append(bundle["record"])
                _atomic_json(response_file, responses)
                _atomic_json(evaluation_file, evaluations)
                with _EXEC_LOCK:
                    state["completed"] += 1
                    if bundle["evaluated_ok"]:
                        state["passed"] += 1
                    else:
                        state["failed"] += 1
                    state["status"][bundle["record"]["test_id"]] = bundle["status"]
    finally:
        responses.sort(key=lambda r: str(r.get("test_id", "")))
        evaluations.sort(key=lambda r: str(r.get("test_id", "")))
        _atomic_json(response_file, responses)
        _atomic_json(evaluation_file, evaluations)
        with _EXEC_LOCK:
            state["running"] = False
            state["finished_at"] = datetime.now(timezone.utc).isoformat()


@app.post("/api/execute/{benchmark_id}")
def start_execution(benchmark_id: str, req: ExecuteRequest) -> dict:
    benchmark_path = _benchmark_id_path(benchmark_id)
    benchmark = _read_json(benchmark_path, "Benchmark not found.")
    manifest_path = DATA_DIR / "manifests" / f"{benchmark_id}_manifest.json"
    manifest = _read_json(manifest_path, f"Manifest not found for {benchmark_id}. Generate the suite first.")
    if not manifest:
        raise HTTPException(status_code=400, detail="Manifest is empty.")
    if not req.endpoint:
        raise HTTPException(status_code=400, detail="Agent endpoint is required.")

    adapter = APIAgentAdapter.from_mapping(req.model_dump())
    context = _agent_context_from_benchmark(benchmark)

    with _EXEC_LOCK:
        previous = _EXECUTIONS.get(benchmark_id)
        if previous and previous.get("running"):
            raise HTTPException(status_code=409, detail="A run is already in progress for this benchmark.")
        _EXECUTIONS[benchmark_id] = {
            "running": True,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "total": len(manifest),
            "completed": 0,
            "passed": 0,
            "failed": 0,
            "status": {},
            "manifest": manifest,
            "benchmark": benchmark,
            "language": benchmark.get("language", ""),
        }

    thread = threading.Thread(
        target=_worker, args=(benchmark_id, adapter, context), daemon=True, name=f"execute-{benchmark_id}",
    )
    _WORKERS[benchmark_id] = thread
    thread.start()
    return {"status": "started", "benchmark_id": benchmark_id, "total": len(manifest)}


@app.get("/api/execute/{benchmark_id}/status")
def execution_status(benchmark_id: str) -> dict:
    state = _EXECUTIONS.get(benchmark_id)
    if not state:
        raise HTTPException(status_code=404, detail="No run started for this benchmark in this API session.")
    with _EXEC_LOCK:
        return {
            "running": state["running"],
            "started_at": state["started_at"],
            "finished_at": state.get("finished_at"),
            "total": state["total"],
            "completed": state["completed"],
            "passed": state["passed"],
            "failed": state["failed"],
            "per_test": dict(state["status"]),
        }


@app.get("/api/results/{benchmark_id}")
def get_results(benchmark_id: str) -> dict:
    run_dir = DATA_DIR / "results" / benchmark_id
    responses = _read_json(run_dir / "agent_responses.json", "No agent responses recorded yet.")
    evaluations = _read_json(run_dir / "evaluation_results.json", "No evaluation results recorded yet.")
    return {
        "benchmark_id": benchmark_id,
        "agent_responses": responses,
        "evaluation_records": evaluations,
    }


# --------------------------------------------------------------------------- #
# Audio files (recordings / attacked / agent responses / transcripts)          #
# --------------------------------------------------------------------------- #


def _resolve_audio_path(raw: str) -> Path:
    if not raw:
        raise HTTPException(status_code=400, detail="Missing audio path.")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT_DIR / raw
    path = path.resolve()
    try:
        path.relative_to(ROOT_DIR)
    except ValueError:
        raise HTTPException(status_code=403, detail="Audio path is outside the project.") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Audio file not found: {path.name}")
    return path


@app.get("/api/audio")
def get_audio(path: str = Query(...)) -> FileResponse:
    file_path = _resolve_audio_path(path)
    return FileResponse(str(file_path))
