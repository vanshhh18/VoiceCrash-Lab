
import json
import logging
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path

from audio.stt.groq_stt import transcribe_audio
from evaluator.groq_judge import evaluate_with_groq

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALUATIONS_DIR = PROJECT_ROOT / "data" / "results" / "evaluations"


def evaluate_test(test_case: dict, agent_result: dict) -> dict:
    """Transcribe and evaluate one completed agent response."""

    total_started = perf_counter()
    test_id = test_case.get("test_id")
    response_path = agent_result.get("response_audio_path")

    if not test_id:
        raise ValueError("Test case is missing test_id")

    if agent_result.get("status") != "success":
        raise ValueError(
            f"Cannot evaluate {test_id}: agent status is "
            f"{agent_result.get('status')}"
        )

    if not response_path or not Path(response_path).is_file():
        raise FileNotFoundError(
            f"Response audio not found for {test_id}: {response_path}"
        )

    caller_audio_path = PROJECT_ROOT / test_case["audio_path"]

    if not caller_audio_path.is_file():
        raise FileNotFoundError(
            f"Caller audio not found for {test_id}: {caller_audio_path}"
        )

    # Time caller STT and agent-response STT separately to identify bottlenecks.
    caller_stt_started = perf_counter()
    caller_transcript = transcribe_audio(str(caller_audio_path))
    caller_stt_seconds = perf_counter() - caller_stt_started

    response_stt_started = perf_counter()
    response_transcript = transcribe_audio(str(response_path))
    response_stt_seconds = perf_counter() - response_stt_started

    # Adapt manifest field names to the judge's expected schema.
    scenario = {
        "type": test_case.get("scenario_type", "unknown"),
        "difficulty": (
            test_case.get("attack_level")
            if test_case.get("attack_level") is not None
            else test_case.get("condition", "unknown")
        ),
        "language": test_case.get("language", "unknown"),
        "expected": test_case.get("expected", ""),
        "caller": caller_transcript,
    }

    judge_started = perf_counter()
    evaluation = evaluate_with_groq(
        scenario=scenario,
        transcript=caller_transcript,
        response=response_transcript,
        original_text=caller_transcript,
    )
    judge_seconds = perf_counter() - judge_started
    total_seconds = perf_counter() - total_started

    timings = {
        "caller_stt_seconds": round(caller_stt_seconds, 3),
        "response_stt_seconds": round(response_stt_seconds, 3),
        "llm_judge_seconds": round(judge_seconds, 3),
        "total_seconds": round(total_seconds, 3),
    }
    logger.info(
        "VoiceCrashLab evaluation timing | test_id=%s | caller_stt=%.3fs | "
        "response_stt=%.3fs | llm_judge=%.3fs | total=%.3fs",
        test_id,
        caller_stt_seconds,
        response_stt_seconds,
        judge_seconds,
        total_seconds,
    )

    record = {
        "test_id": test_id,
        "scenario_id": test_case.get("scenario_id"),
        "evaluation_status": "completed",
        "caller_transcript": caller_transcript,
        "response_transcript": response_transcript,
        "evaluation": evaluation,
        "timings_seconds": timings,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Save each evaluation separately so one test does not overwrite another.
    EVALUATIONS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EVALUATIONS_DIR / f"{test_id}.json"
    temp_path = output_path.with_suffix(".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(record, file, ensure_ascii=False, indent=2)

    temp_path.replace(output_path)

    return record
