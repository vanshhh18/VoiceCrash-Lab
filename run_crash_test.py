import argparse

from evaluator.benchmark_runner import (
    get_or_create_benchmark,
    run_benchmark
)
from target_agent import call_target_agent


def main():

    parser = argparse.ArgumentParser(
        description="VoiceCrashLab Agent Tester"
    )

    parser.add_argument(
        "--role",
        required=True,
        help="Target agent role"
    )

    parser.add_argument(
        "--business",
        required=True,
        help="Business context"
    )

    parser.add_argument(
        "--tasks",
        required=True,
        help="Supported agent tasks, comma-separated"
    )

    parser.add_argument(
        "--language",
        default="Hinglish",
        help="Agent language"
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Target agent API URL"
    )

    args = parser.parse_args()

    tasks = [
        task.strip()
        for task in args.tasks.split(",")
        if task.strip()
    ]

    print("\nGenerating / loading test suite...")

    benchmark = get_or_create_benchmark(
        args.role,
        args.business,
        tasks,
        args.language
    )

    print(
        f"\nBenchmark: "
        f"{benchmark['benchmark_id']}"
    )

    print(
        f"Tests: "
        f"{len(benchmark['scenarios'])}"
    )

    print("\nTarget Agent:")
    print(args.url)

    print("\nStarting crash test...")

    run_benchmark(
        benchmark,
        args.url
    )


if __name__ == "__main__":
    main()