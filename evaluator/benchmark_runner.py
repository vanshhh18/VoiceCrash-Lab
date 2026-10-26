import json
import os

from scenarios.scenario_storage import load_benchmark
from target_agent import call_target_agent
from evaluator.groq_judge import evaluate_with_groq
from evaluator.crash_score import calculate_crash_score


def get_or_create_benchmark(
    agent_role,
    business_context,
    supported_tasks,
    language="Hinglish"
):
    from scenarios.scenario_storage import (
        find_matching_benchmark
    )

    # 1. Look for an existing matching benchmark
    benchmark = find_matching_benchmark(
        agent_role,
        business_context,
        language
    )

    if benchmark:
        print(
            f"\nMatching benchmark found: "
            f"{benchmark['benchmark_id']}"
        )

        from audio.scenario_audio import (
            ensure_scenario_recordings
        )

        ensure_scenario_recordings(benchmark)

        return benchmark

    # 2. No matching benchmark found
    print("\nNo matching benchmark found.")
    print("Generating new test suite with LLM...")

    from scenarios.adversarial_generator import (
        generate_adversarial_scenarios
    )

    scenarios = generate_adversarial_scenarios(
        agent_role,
        business_context,
        supported_tasks,
        language
    )

    from scenarios.scenario_validator import validate_scenarios
    from scenarios.scenario_storage import save_benchmark

    valid_scenarios, invalid_scenarios = validate_scenarios(
        scenarios
    )

    if not valid_scenarios:
        raise ValueError(
            "Generated scenarios failed validation."
        )

    if invalid_scenarios:
        print(
            f"Warning: {len(invalid_scenarios)} "
            f"scenarios failed validation."
        )

    save_benchmark(
        agent_role,
        business_context,
        supported_tasks,
        language,
        valid_scenarios
    )

    from scenarios.scenario_storage import (
        get_benchmark_id,
        load_benchmark
    )

    benchmark_id = get_benchmark_id(agent_role)

    benchmark = load_benchmark(benchmark_id)

    if benchmark is None:
        raise ValueError(
            "Benchmark could not be created."
        )

    from audio.scenario_audio import ensure_scenario_recordings

    ensure_scenario_recordings(benchmark)

    return benchmark


RESULT_DIR = "data/results"

def run_benchmark(
    benchmark,
    target_agent_url=None
):


    if not benchmark:
        print("No benchmark found.")
        return
   
    scenarios = benchmark["scenarios"]

    print("\n" + "=" * 60)
    print("VOICECRASHLAB BENCHMARK TEST")
    print("=" * 60)

    print(f"\nAgent Role: {benchmark['agent_role']}")
    print(f"Business: {benchmark['business_context']}")
    print(f"Language: {benchmark['language']}")
    print(f"Tests: {len(scenarios)}")

    results = []
    passed = 0

    for scenario in scenarios:

        print("\n" + "-" * 60)
        print(f"Test {scenario['id']}: {scenario['type']}")
        print(f"Caller: {scenario['caller']}")

        response = call_target_agent(
            scenario["caller"],
            target_agent_url
        )

        result = evaluate_with_groq(
            scenario,
            scenario["caller"],
            response
        )

        if result["passed"]:
            passed += 1

        test_result = {
            "id": scenario["id"],
            "type": scenario["type"],
            "caller": scenario["caller"],
            "expected": scenario["expected"],
            "agent_response": response,
            "result": (
                "PASS"
                if result["passed"]
                else "FAIL"
            ),
            "category": result["category"],
            "severity": result["severity"],
            "reason": result["reason"]
        }

        results.append(test_result)

        print(f"Agent: {response}")
        print(f"Result: {test_result['result']}")
        print(f"Category: {result['category']}")
        print(f"Severity: {result['severity']}")
        print(f"Reason: {result['reason']}")

    total = len(results)
    failed = total - passed

    success_rate = (
        (passed / total) * 100
        if total > 0
        else 0
    )

    benchmark_output = {
        "benchmark_id": benchmark["benchmark_id"],
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

    crash_score = calculate_crash_score(
        {
            "tests": [
                {
                    "category": test["category"]
                }
                for test in results
            ]
        }
    )

    benchmark_output["crash_score"] = crash_score

    os.makedirs(RESULT_DIR, exist_ok=True)

    result_file = os.path.join(
        RESULT_DIR,
        f"{benchmark['benchmark_id']}_results.json"
    )

    with open(
        result_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            benchmark_output,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)

    print(f"\nTests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Crash Score: {crash_score}/100")

    print(f"\nResults saved to: {result_file}")


if __name__ == "__main__":
    print(
        "Use run_crash_test.py to run VoiceCrashLab."
    )