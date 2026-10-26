
import json
from pathlib import Path
from typing import Any

from app.evaluation_storage import save_evaluation
from app.llm_judge import judge_transcript
from app.response_collector import load_manifest


DEFAULT_MANIFEST = Path("data/manifests/food_delivery_manifest.json")

DEFAULT_TRANSCRIPTS = Path(
    "data/results/food_delivery/transcripts/response_transcripts.json"
)

DEFAULT_OUTPUT = Path(
    "data/results/food_delivery/evaluations/evaluation_results.json"
)


def load_json(path: str | Path) -> Any:
    """Load JSON data from a file."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_scenario_lookup(benchmark_path: str | Path) -> dict:
    """Index scenarios using category and scenario ID."""
    benchmark = load_json(benchmark_path)
    lookup = {}

    for category in ("speech", "reasoning"):
        scenarios = benchmark.get("scenarios", {}).get(category, [])

        for scenario in scenarios:
            scenario_id = scenario.get("id")

            if scenario_id:
                lookup[(category, scenario_id)] = scenario

    return lookup


def evaluate_responses(
    manifest_path: str | Path = DEFAULT_MANIFEST,
    transcripts_path: str | Path = DEFAULT_TRANSCRIPTS,
    benchmark_path: str | Path | None = None,
    output_path: str | Path = DEFAULT_OUTPUT,
    model: str | None = None,
) -> dict:
    """
    Evaluate available response transcripts and save each result.

    Missing or failed transcriptions are recorded without calling the judge.
    """
    manifest = load_manifest(str(manifest_path))
    transcript_data = load_json(transcripts_path)

    if benchmark_path is None:
        benchmark_path = Path(
            "data/benchmarks/food_delivery_customer_support_agent_d1174b87_v2.json"
        )

    scenario_lookup = build_scenario_lookup(benchmark_path)

    if isinstance(transcript_data, dict):
        transcript_records = transcript_data.get("results", transcript_data)
    elif isinstance(transcript_data, list):
        transcript_records = {
            item["test_id"]: item
            for item in transcript_data
            if isinstance(item, dict) and item.get("test_id")
        }
    else:
        raise ValueError("Transcript data must be a JSON object or list.")

    if not isinstance(transcript_records, dict):
        raise ValueError("Transcript records must be a JSON object.")

    summary = {
        "total": len(manifest),
        "evaluated": 0,
        "skipped": 0,
        "failed": 0,
    }

    for test in manifest:
        test_id = test.get("test_id")

        if not test_id:
            summary["failed"] += 1
            continue

        transcript_record = transcript_records.get(test_id)

        if not isinstance(transcript_record, dict):
            save_evaluation(
                test_id,
                {
                    "status": "transcript_missing",
                    "overall_pass": False,
                    "error": "No transcript record found for this test.",
                },
                output_path,
            )
            summary["skipped"] += 1
            continue

        transcript_status = transcript_record.get("status")

        if transcript_status != "transcribed":
            save_evaluation(
                test_id,
                {
                    "status": "transcript_unavailable",
                    "overall_pass": False,
                    "error": (
                        transcript_record.get("error")
                        or f"Transcript status: {transcript_status}"
                    ),
                },
                output_path,
            )
            summary["skipped"] += 1
            continue

        transcript = transcript_record.get("transcript", "")

        if not isinstance(transcript, str) or not transcript.strip():
            save_evaluation(
                test_id,
                {
                    "status": "empty_transcript",
                    "overall_pass": False,
                    "error": "Transcript is empty.",
                },
                output_path,
            )
            summary["skipped"] += 1
            continue

        category = test.get("category")
        scenario_id = test.get("scenario_id")
        scenario = scenario_lookup.get((category, scenario_id))

        if scenario is None:
            save_evaluation(
                test_id,
                {
                    "status": "scenario_missing",
                    "overall_pass": False,
                    "error": (
                        f"No scenario found for category={category}, "
                        f"scenario_id={scenario_id}"
                    ),
                },
                output_path,
            )
            summary["failed"] += 1
            continue

        try:
            result = judge_transcript(
                scenario=scenario,
                transcript=transcript,
                model=model,
            )

            evaluation = {
                "status": "evaluated",
                "test_id": test_id,
                "category": category,
                "scenario_id": scenario_id,
                "attack_type": test.get("attack_type"),
                "transcript": transcript,
                **result,
            }

            save_evaluation(test_id, evaluation, output_path)
            summary["evaluated"] += 1

        except Exception as exc:
            save_evaluation(
                test_id,
                {
                    "status": "evaluation_failed",
                    "test_id": test_id,
                    "overall_pass": False,
                    "error": str(exc),
                },
                output_path,
            )
            summary["failed"] += 1

    return summary
