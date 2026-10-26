
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from target_agent import call_target_agent
from evaluator.groq_judge import evaluate_with_groq

load_dotenv()


def run_audio_benchmark(stt_report_path, benchmark_path, output_file):
    stt_report_path = Path(stt_report_path)
    benchmark_path = Path(benchmark_path)
    output_file = Path(output_file)

    if not stt_report_path.is_file():
        raise FileNotFoundError(f"STT report not found: {stt_report_path}")

    if not benchmark_path.is_file():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")

    with stt_report_path.open("r", encoding="utf-8") as file:
        stt_report = json.load(file)

    with benchmark_path.open("r", encoding="utf-8") as file:
        benchmark = json.load(file)

    # Supports both a direct list and {"results": [...]}.
    if isinstance(stt_report, dict):
        stt_results = stt_report.get("results", [])
    else:
        stt_results = stt_report

    scenarios = {
        scenario["id"]: scenario
        for scenario in benchmark["scenarios"]["speech"]
    }

    results = []

    for index, item in enumerate(stt_results, start=1):
        scenario_id = item.get("scenario_id")
        scenario = scenarios.get(scenario_id)
        transcript = item.get("transcript")

        record = {
            "scenario_id": scenario_id,
            "attack_type": item.get("attack_type"),
            "audio_path": item.get("audio_path"),
            "transcript": transcript,
            "stt_status": item.get("status"),
            "agent_response": None,
            "evaluation": None,
            "status": "ERROR",
            "error": None,
        }

        print(
            f"\n[{index}/{len(stt_results)}] "
            f"{scenario_id} | {item.get('attack_type')}"
        )

        try:
            if not scenario:
                raise ValueError(
                    f"Scenario not found in benchmark: {scenario_id}"
                )

            if item.get("status", "").lower() != "success" or not transcript:
                raise ValueError("No successful STT transcript available")

            agent_response = call_target_agent(
                transcript,
                target_url=os.getenv("TARGET_AGENT_URL"),
            )

            evaluation = evaluate_with_groq(
                scenario,
                transcript,
                agent_response,
                original_text=scenario.get("caller", ""),
            )

            record["agent_response"] = agent_response
            record["evaluation"] = evaluation
            record["status"] = "SUCCESS"

            print("Agent:", agent_response)
            print("Evaluation:", evaluation)

        except Exception as exc:
            record["error"] = str(exc)
            print("Error:", exc)

        results.append(record)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    successful = sum(r["status"] == "SUCCESS" for r in results)
    failed = len(results) - successful

    print("\nAudio evaluation complete.")
    print(f"Processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Saved: {output_file}")

    return results
