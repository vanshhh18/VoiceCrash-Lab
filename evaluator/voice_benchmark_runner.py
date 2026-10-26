import json
import os

from audio.dummy_voice_agent import run_voice_agent
from audio.prisma_response_check import transcribe_response
from evaluator.groq_judge import evaluate_with_groq


RECORDING_DIR = "data/recordings"
RESULT_DIR = "data/results/voice"


def run_voice_benchmark(benchmark):

    benchmark_id = benchmark["benchmark_id"]
    scenarios = benchmark["scenarios"]

    recording_folder = os.path.join(
        RECORDING_DIR,
        benchmark_id
    )

    result_folder = os.path.join(
        RESULT_DIR,
        benchmark_id
    )

    os.makedirs(result_folder, exist_ok=True)

    results = []

    passed = 0

    print("\n" + "=" * 60)
    print("VOICECRASHLAB VOICE BENCHMARK")
    print("=" * 60)

    print(f"\nBenchmark: {benchmark_id}")
    print(f"Scenarios: {len(scenarios)}")

    for scenario in scenarios:

        scenario_id = scenario["id"]

        input_audio = os.path.join(
            recording_folder,
            f"{scenario_id}.mp3"
        )

        output_audio = os.path.join(
            result_folder,
            f"{scenario_id}_response.mp3"
        )

        print("\n" + "-" * 60)
        print(f"Testing: {scenario_id}")
        print(f"Type: {scenario['type']}")

        if not os.path.exists(input_audio):
            print("Input audio not found. Skipping.")

            continue

        # Step 1: Run target voice agent
        voice_result = run_voice_agent(
            input_audio,
            output_audio
        )

        caller_transcript = voice_result["transcript"]
        agent_response = voice_result["response"]

        # Step 2: Transcribe agent response with Prisma
        print("\nSending agent response to Prisma...")

        prisma_transcript = transcribe_response(
            output_audio
        )

        print("\nPrisma Transcript:")
        print(prisma_transcript)

        # Step 3: Judge the actual spoken response
        print("\nJudging agent response...")

        judge_result = evaluate_with_groq(
            scenario,
            caller_transcript,
            prisma_transcript
        )

        if judge_result["passed"]:
            passed += 1

        test_result = {
            "id": scenario_id,
            "type": scenario["type"],
            "caller_audio": input_audio,
            "caller_transcript": caller_transcript,
            "agent_response": agent_response,
            "response_audio": output_audio,
            "prisma_transcript": prisma_transcript,
            "result": (
                "PASS"
                if judge_result["passed"]
                else "FAIL"
            ),
            "category": judge_result["category"],
            "severity": judge_result["severity"],
            "reason": judge_result["reason"]
        }

        results.append(test_result)

        print("\nResult:")
        print(
            "PASS"
            if judge_result["passed"]
            else "FAIL"
        )

        print(
            f"Category: {judge_result['category']}"
        )

        print(
            f"Severity: {judge_result['severity']}"
        )

        print(
            f"Reason: {judge_result['reason']}"
        )

    total = len(results)
    failed = total - passed

    success_rate = (
        (passed / total) * 100
        if total > 0
        else 0
    )

    output = {
        "benchmark_id": benchmark_id,
        "benchmark_version": benchmark["benchmark_version"],
        "agent_role": benchmark["agent_role"],
        "business_context": benchmark["business_context"],
        "language": benchmark["language"],
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "success_rate": round(success_rate, 1),
        "tests": results
    }

    result_file = os.path.join(
        result_folder,
        "voice_results.json"
    )

    with open(
        result_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 60)
    print("VOICE BENCHMARK COMPLETE")
    print("=" * 60)

    print(f"\nTests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"\nResults saved to:")
    print(result_file)

    return output