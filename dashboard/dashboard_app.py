"""VoiceCrashLab dashboard: connect -> configure -> generate -> test/evaluate."""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from app.agent_adapters.api_agent import APIAgentAdapter, test_agent_connection
from app.run_pipeline import run_pipeline
from audio.stt.groq_stt import transcribe_audio
from evaluator.groq_judge import evaluate_with_groq

st.set_page_config(page_title="VoiceCrashLab", page_icon="🎙️", layout="wide")
st.title("🎙️ VoiceCrashLab")
st.caption("Connect any HTTP audio-in agent, generate adversarial audio, then test and evaluate each response.")

for key, default in {
    "agent_connected": False,
    "connected_agent_config": None,
    "latest_pipeline_result": None,
    "voice_agent_context": None,
    "latest_agent_responses": [],
    "latest_evaluation_results": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def find_scenario(benchmark: dict, category: str, scenario_id: str) -> dict:
    for item in benchmark.get("scenarios", {}).get(category, []):
        if str(item.get("id")) == str(scenario_id):
            return item
    # Fallback by ID if older manifests omit category.
    for items in benchmark.get("scenarios", {}).values():
        for item in items:
            if str(item.get("id")) == str(scenario_id):
                return item
    return {}


def generate_llm_fix(scenario: dict, evaluation: dict, caller_text: str,
                     agent_response: str, context: dict) -> dict:
    """Generate a concrete remediation for a failed case; failure is still saved if this call fails."""
    if evaluation.get("passed") is True:
        return {"suggested_fix": "No fix required; this case passed.", "example_response": ""}
    if not os.getenv("GROQ_API_KEY"):
        return {"suggested_fix": "Configure GROQ_API_KEY to generate an LLM remediation suggestion.", "example_response": ""}
    try:
        from langchain_groq import ChatGroq
        model = os.getenv("GROQ_JUDGE_MODEL", "openai/gpt-oss-120b")
        llm = ChatGroq(model=model, temperature=0, api_key=os.getenv("GROQ_API_KEY"))
        prompt = f"""You are a voice-agent reliability engineer. Give a specific remediation based only on this evidence.
Agent role: {context.get('agent_role', '')}
Business context: {context.get('business_context', '')}
Supported tasks: {context.get('supported_tasks', [])}
Language: {context.get('language', '')}
Scenario: {json.dumps(scenario, ensure_ascii=False)}
Caller input: {caller_text}
Observed agent response: {agent_response}
Evaluation: {json.dumps(evaluation, ensure_ascii=False)}
Return ONLY JSON with string fields suggested_fix and example_response. Do not invent business policies or claim actions were completed without evidence."""
        message = llm.invoke(prompt)
        data = json.loads(message.content)
        return {
            "suggested_fix": str(data.get("suggested_fix", "Review the failed behavior and add a targeted regression test.")),
            "example_response": str(data.get("example_response", "")),
        }
    except Exception as exc:
        return {"suggested_fix": f"LLM fix generation failed: {exc}", "example_response": ""}


# STEP 1 — connection form. Do not reveal agent setup until endpoint reachability succeeds.
st.header("1. Connect your agent")
with st.form("connect_agent_form"):
    endpoint = st.text_input("Agent audio endpoint URL", placeholder="https://your-agent.example/api/voice")
    agent_name = st.text_input("Agent name", placeholder="e.g. Banking Voice Assistant")
    token = st.text_input("API token (optional)", type="password")
    auth_header = st.text_input("Authentication header", value="Authorization")
    auth_scheme = st.text_input("Authentication scheme/prefix", value="Bearer", help="Leave blank if the API expects the raw token.")
    input_field = st.text_input("Multipart audio field name", value="audio")
    response_text_field = st.text_input("JSON response text field", value="response")
    response_audio_url_field = st.text_input("JSON response audio URL field", value="audio_url")
    timeout = st.number_input("Request timeout (seconds)", min_value=5, max_value=600, value=60)
    connect_clicked = st.form_submit_button("Connect Agent", type="primary")

if connect_clicked:
    config = {
        "name": agent_name.strip() or "Connected Voice Agent",
        "endpoint": endpoint.strip(), "token": token.strip(),
        "auth_header": auth_header.strip() or "Authorization",
        "auth_scheme": auth_scheme.strip(), "input_field": input_field.strip() or "audio",
        "response_text_field": response_text_field.strip() or "response",
        "response_audio_url_field": response_audio_url_field.strip() or "audio_url",
        "timeout": int(timeout),
    }
    try:
        with st.spinner("Checking endpoint reachability and authentication..."):
            check = test_agent_connection(config)
        st.session_state["agent_connected"] = True
        st.session_state["connected_agent_config"] = config
        st.success(f"Connected to {config['name']}. {check['message']}")
    except Exception as exc:
        st.session_state["agent_connected"] = False
        st.session_state["connected_agent_config"] = None
        st.error(f"Connection failed: {exc}")

if not st.session_state["agent_connected"]:
    st.info("Connect successfully to unlock Agent Info and test-suite generation.")
    st.stop()

config = st.session_state["connected_agent_config"]
with st.expander("Connected agent configuration", expanded=False):
    safe_config = {k: v for k, v in config.items() if k != "token"}
    st.json(safe_config)
    st.caption("Endpoint reachability is checked on Connect. The real multipart audio request is validated during Test Your Agent.")

# STEP 2 — agent info and test suite generation.
st.divider()
st.header("2. Agent info & generate test suite")
with st.form("agent_info_form"):
    agent_role = st.text_input("Agent role/name", placeholder="e.g. Banking Customer Support Agent")
    business_context = st.text_area("Business context", placeholder="Describe the business, policies, and agent capabilities.")
    tasks_text = st.text_area("Supported tasks (one per line)", placeholder="track order\nrequest refund\nreschedule delivery")
    language = st.selectbox("Caller language", ["Hinglish", "Hindi", "English"])
    scenario_count = st.number_input("Scenarios per track", min_value=1, max_value=20, value=5, step=1)
    voice = st.text_input("TTS voice for generated caller audio", value=os.getenv("VOICECRASHLAB_TTS_VOICE", "hi-IN-SwaraNeural"))
    generate_clicked = st.form_submit_button("Generate Test Suite", type="primary")

if generate_clicked:
    tasks = [line.strip() for line in tasks_text.splitlines() if line.strip()]
    if not agent_role.strip() or not business_context.strip() or not tasks:
        st.error("Agent role, business context, and at least one supported task are required.")
    else:
        context = {"agent_role": agent_role.strip(), "business_context": business_context.strip(),
                   "supported_tasks": tasks, "language": language}
        try:
            with st.spinner("Generating speech + reasoning scenarios, recording clean audio, applying attacks, and building the manifest..."):
                result = run_pipeline(agent_role=context["agent_role"], business_context=context["business_context"],
                                      supported_tasks=tasks, language=language,
                                      scenario_count=int(scenario_count), voice=voice.strip())
            st.session_state["latest_pipeline_result"] = result
            st.session_state["voice_agent_context"] = context
            st.session_state["latest_agent_responses"] = []
            st.session_state["latest_evaluation_results"] = []
            st.success("Test suite generated. No agent requests have been sent yet.")
        except Exception as exc:
            st.error(f"Test-suite generation failed: {exc}")
            st.exception(exc)

result = st.session_state.get("latest_pipeline_result")
if not result:
    st.info("Fill in agent info and generate a test suite to continue.")
    st.stop()

st.subheader("Generated suite")
cols = st.columns(4)
cols[0].metric("Scenarios", result.get("scenario_count", 0))
cols[1].metric("Clean audio", result.get("clean_count", result.get("recording_count", 0)))
cols[2].metric("Attacked audio", result.get("attack_count", 0))
cols[3].metric("Total audio tests", result.get("manifest_input_count", 0))
st.caption(f"Manifest: {result['manifest_path']}")
benchmark_path = Path(result["benchmark_path"])
if benchmark_path.is_file():
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    with st.expander("View generated scenarios"):
        for category, items in benchmark.get("scenarios", {}).items():
            st.markdown(f"**{category.title()} ({len(items)})**")
            for scenario in items:
                st.write(f"**{scenario.get('id')} · {scenario.get('type', 'unknown')}** — {scenario.get('caller', '')}")
                st.caption(f"Expected: {scenario.get('expected', '')}")
    st.download_button("Download benchmark JSON", benchmark_path.read_bytes(), file_name=benchmark_path.name, mime="application/json")

# STEP 3 — send original generated audio to the connected audio endpoint and evaluate each response immediately.
st.divider()
st.header("3. Test agent & evaluate responses")
st.write("Each generated audio file is sent directly to the connected endpoint. As soon as a response arrives, VoiceCrashLab evaluates it and saves the result before moving to the next test.")
manifest_path = Path(result["manifest_path"])
if not manifest_path.is_file():
    st.error("Manifest is missing. Generate the test suite again.")
    st.stop()
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if not manifest:
    st.error("Manifest is empty.")
    st.stop()

if st.button("🚀 Test Your Agent", type="primary"):
    adapter = APIAgentAdapter.from_mapping(config)
    benchmark = json.loads(Path(result["benchmark_path"]).read_text(encoding="utf-8"))
    run_dir = ROOT_DIR / "data" / "results" / Path(result["benchmark_path"]).stem
    run_dir.mkdir(parents=True, exist_ok=True)
    response_file = run_dir / "agent_responses.json"
    evaluation_file = run_dir / "evaluation_results.json"
    responses, evaluations = [], []
    progress = st.progress(0, text="Starting agent tests...")
    live_status = st.empty()
    live_results = st.empty()
    total = len(manifest)
    for index, test in enumerate(manifest, start=1):
        test_id = str(test.get("test_id", f"test_{index:03d}"))
        scenario = find_scenario(benchmark, str(test.get("category", "speech")), str(test.get("scenario_id", "")))
        caller_text = str(scenario.get("caller", "")) if scenario else ""
        live_status.info(f"Sending original audio {index}/{total}: {test_id}")
        try:
            agent_result = adapter.process_test(test)
            agent_result.update({
                "scenario_id": test.get("scenario_id"),
                "category": test.get("category"),
                "attack_type": test.get("attack_type"),
                "condition": test.get("condition"),
                "audio_path": test.get("audio_path"),
            })
            responses.append(agent_result)
            atomic_json(response_file, responses)
        except Exception as exc:
            failed_response = {
                "test_id": test_id, "status": "failed", "error": str(exc),
                "scenario_id": test.get("scenario_id"), "category": test.get("category"),
                "attack_type": test.get("attack_type"), "condition": test.get("condition"),
                "audio_path": test.get("audio_path"),
            }
            responses.append(failed_response)
            atomic_json(response_file, responses)
            record = {
                "test_id": test_id, "scenario_id": test.get("scenario_id"),
                "category": test.get("category"), "scenario_type": test.get("scenario_type"),
                "attack_type": test.get("attack_type"), "condition": test.get("condition"),
                "audio_path": test.get("audio_path"), "caller_transcript": caller_text,
                "expected": scenario.get("expected", test.get("expected", "")) if scenario else test.get("expected", ""),
                "agent_response": "", "status": "failed", "error": str(exc),
                "evaluation": {"passed": False, "category": "AGENT_REQUEST_FAILURE", "reason": str(exc)},
                "suggested_fix": "Check endpoint reachability, authentication, multipart field name, timeout, and the API's accepted audio format.",
                "example_response": "",
            }
            evaluations.append(record)
            atomic_json(evaluation_file, evaluations)
            st.session_state["latest_agent_responses"] = responses
            st.session_state["latest_evaluation_results"] = evaluations
            progress.progress(index / total, text=f"Completed {index}/{total}")
            continue

        # Agent response is already persisted. Evaluate it immediately, without
        # waiting for the rest of the batch to finish.
        live_status.info(f"Evaluating response {index}/{total}: {test_id}")
        try:
            if not scenario:
                raise ValueError(f"Scenario not found for {test.get('scenario_id')}")
            if agent_result.get("response_text"):
                response_text = agent_result["response_text"]
            elif agent_result.get("response_audio_path"):
                response_text = transcribe_audio(agent_result["response_audio_path"])
            else:
                raise ValueError("Agent returned neither response text nor response audio.")
            agent_result["agent_response"] = response_text
            # Update the response file with its readable transcript as well.
            atomic_json(response_file, responses)
            evaluation = evaluate_with_groq(
                scenario={**scenario, "type": scenario.get("type", test.get("scenario_type", "unknown")),
                          "difficulty": test.get("attack_level", test.get("condition", "unknown")),
                          "language": test.get("language", language)},
                transcript=caller_text, response=response_text, original_text=caller_text,
                agent_info=st.session_state.get("voice_agent_context") or {},
            )
            fix = {"suggested_fix": "No fix required; this test passed.", "example_response": ""}
            if evaluation.get("passed") is not True:
                fix = generate_llm_fix(scenario, evaluation, caller_text, response_text,
                                       st.session_state.get("voice_agent_context") or {})
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
        except Exception as exc:
            record = {
                "test_id": test_id, "scenario_id": test.get("scenario_id"),
                "category": test.get("category"), "scenario_type": test.get("scenario_type"),
                "attack_type": test.get("attack_type"), "condition": test.get("condition"),
                "audio_path": test.get("audio_path"), "caller_transcript": caller_text,
                "expected": scenario.get("expected", test.get("expected", "")) if scenario else test.get("expected", ""),
                "agent_response": agent_result.get("response_text", ""),
                "status": "evaluation_failed", "error": str(exc),
                "evaluation": {"passed": False, "category": "EVALUATION_ERROR", "reason": str(exc)},
                "suggested_fix": "Evaluation failed. Check GROQ_API_KEY, GROQ_JUDGE_MODEL, and response transcription settings.",
                "example_response": "",
            }
        evaluations.append(record)
        atomic_json(evaluation_file, evaluations)
        st.session_state["latest_agent_responses"] = responses
        st.session_state["latest_evaluation_results"] = evaluations
        passed = sum(bool((r.get("evaluation") or {}).get("passed")) for r in evaluations)
        failed = sum((r.get("evaluation") or {}).get("passed") is False for r in evaluations)
        live_results.metric("Processed", len(evaluations), help="Each response and evaluation is saved immediately.")
        progress.progress(index / total, text=f"Completed {index}/{total} · {passed} passed · {failed} failed/review")
    live_status.success(f"Testing and evaluation finished. Results saved to {evaluation_file}")

# Always show available partial/final results, including after reruns.
evaluations = st.session_state.get("latest_evaluation_results") or []
responses = st.session_state.get("latest_agent_responses") or []
if evaluations:
    st.divider()
    st.header("4. Evaluation summary")
    passed_count = sum((r.get("evaluation") or {}).get("passed") is True for r in evaluations)
    failed_count = sum((r.get("evaluation") or {}).get("passed") is False or r.get("status") == "failed" for r in evaluations)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Evaluated/processed", len(evaluations))
    m2.metric("Passed", passed_count)
    m3.metric("Failed", failed_count)
    m4.metric("Pass rate", f"{(passed_count / len(evaluations) * 100):.1f}%" if evaluations else "0%")
    for row in evaluations:
        ev = row.get("evaluation") or {}
        passed = ev.get("passed") is True
        label = "PASS" if passed else (ev.get("category", "FAILED") or "FAILED")
        with st.expander(f"{'🟢' if passed else '🔴'} {row.get('test_id')} · {label}"):
            st.write("**Scenario:**", row.get("scenario_id", ""), "| **Attack:**", row.get("attack_type", "none"))
            st.write("**Caller:**", row.get("caller_transcript", ""))
            st.write("**Expected:**", row.get("expected", ""))
            st.write("**Agent response:**", row.get("agent_response", "") or row.get("error", "No response"))
            st.write("**Evaluation reason:**", ev.get("reason", row.get("error", "")))
            if ev.get("checks"):
                st.json(ev["checks"])
            st.write("**LLM suggested fix:**", row.get("suggested_fix", "Not available"))
            if row.get("example_response"):
                st.write("**Suggested example response:**", row["example_response"])
    result_dir = ROOT_DIR / "data" / "results" / Path(result["benchmark_path"]).stem
    st.download_button("Download evaluation results JSON", json.dumps(evaluations, ensure_ascii=False, indent=2),
                       file_name="evaluation_results.json", mime="application/json")
    st.download_button("Download collected agent responses JSON", json.dumps(responses, ensure_ascii=False, indent=2),
                       file_name="agent_responses.json", mime="application/json")
