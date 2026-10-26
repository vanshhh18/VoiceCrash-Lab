
import hashlib
import json
import os
import re

BENCHMARK_DIR = "data/benchmarks"


def create_benchmark_id(
    agent_role,
    business_context="",
    language="",
):
    role_slug = re.sub(
        r"[^a-z0-9]+",
        "_",
        agent_role.lower(),
    ).strip("_")

    identity = "|".join([
        str(agent_role).strip().lower(),
        str(business_context).strip().lower(),
        str(language).strip().lower(),
    ])

    suffix = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()[:8]

    return f"{role_slug}_{suffix}_v2"


def save_benchmark(
    agent_role,
    business_context,
    supported_tasks,
    language,
    scenarios,
):
    os.makedirs(BENCHMARK_DIR, exist_ok=True)

    if not isinstance(scenarios, dict):
        raise ValueError(
            "scenarios must be a dictionary containing "
            "'speech' and 'reasoning' lists."
        )

    speech_scenarios = scenarios.get("speech", [])
    reasoning_scenarios = scenarios.get("reasoning", [])

    if not isinstance(speech_scenarios, list):
        raise ValueError("'speech' must be a list.")

    if not isinstance(reasoning_scenarios, list):
        raise ValueError("'reasoning' must be a list.")

    benchmark_id = create_benchmark_id(
        agent_role,
        business_context,
        language,
    )

    benchmark = {
        "benchmark_id": benchmark_id,
        "benchmark_version": "2.0",
        "agent_role": agent_role,
        "business_context": business_context,
        "supported_tasks": supported_tasks,
        "language": language,
        "scenario_count": (
            len(speech_scenarios) + len(reasoning_scenarios)
        ),
        "scenario_counts": {
            "speech": len(speech_scenarios),
            "reasoning": len(reasoning_scenarios),
        },
        "scenarios": {
            "speech": speech_scenarios,
            "reasoning": reasoning_scenarios,
        },
    }

    benchmark_file = os.path.join(
        BENCHMARK_DIR,
        f"{benchmark_id}.json",
    )

    with open(benchmark_file, "w", encoding="utf-8") as file:
        json.dump(
            benchmark,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"Saved benchmark: {benchmark_id}")
    print(f"File: {benchmark_file}")
    print(f"Speech scenarios: {len(speech_scenarios)}")
    print(f"Reasoning scenarios: {len(reasoning_scenarios)}")
    print(f"Total scenarios: {benchmark['scenario_count']}")

    return benchmark_file


def load_benchmark(benchmark_id):
    benchmark_file = os.path.join(
        BENCHMARK_DIR,
        f"{benchmark_id}.json",
    )

    if not os.path.exists(benchmark_file):
        return None

    with open(benchmark_file, "r", encoding="utf-8") as file:
        return json.load(file)


def list_benchmarks():
    if not os.path.exists(BENCHMARK_DIR):
        return []

    return sorted(
        filename[:-5]
        for filename in os.listdir(BENCHMARK_DIR)
        if filename.endswith(".json")
    )


def benchmark_exists(
    agent_role,
    business_context="",
    language="",
):
    benchmark_id = create_benchmark_id(
        agent_role,
        business_context,
        language,
    )

    benchmark = load_benchmark(benchmark_id)

    return (
        benchmark is not None
        and isinstance(benchmark.get("scenarios"), dict)
        and "speech" in benchmark["scenarios"]
        and "reasoning" in benchmark["scenarios"]
    )


def normalize_text(value):
    return " ".join(
        str(value).strip().lower().split()
    )


def find_matching_benchmark(
    agent_role,
    business_context,
    language,
):
    if not os.path.exists(BENCHMARK_DIR):
        return None

    target_role = normalize_text(agent_role)
    target_business = normalize_text(business_context)
    target_language = normalize_text(language)

    for filename in os.listdir(BENCHMARK_DIR):
        if not filename.endswith(".json"):
            continue

        benchmark_file = os.path.join(
            BENCHMARK_DIR,
            filename,
        )

        try:
            with open(
                benchmark_file,
                "r",
                encoding="utf-8",
            ) as file:
                benchmark = json.load(file)
        except (json.JSONDecodeError, OSError):
            continue

        scenarios = benchmark.get("scenarios")

        if not (
            isinstance(scenarios, dict)
            and isinstance(scenarios.get("speech"), list)
            and isinstance(scenarios.get("reasoning"), list)
        ):
            continue

        if (
            normalize_text(benchmark.get("agent_role", ""))
            == target_role
            and normalize_text(
                benchmark.get("business_context", "")
            ) == target_business
            and normalize_text(
                benchmark.get("language", "")
            ) == target_language
        ):
            return benchmark

    return None


def get_benchmark_id(
    agent_role,
    business_context="",
    language="",
):
    return create_benchmark_id(
        agent_role,
        business_context,
        language,
    )
