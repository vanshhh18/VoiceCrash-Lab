
import asyncio
import json
import re
from pathlib import Path

import edge_tts


async def _record_scenario(text, output_file, voice):
    output_file.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_file))


def generate_scenario_audio(
    benchmark_path,
    output_dir=None,
    voice="hi-IN-SwaraNeural",
    force=False
):
    benchmark_path = Path(benchmark_path)

    with benchmark_path.open("r", encoding="utf-8") as f:
        benchmark = json.load(f)

    if isinstance(benchmark, list):
        scenarios = benchmark
        benchmark_id = benchmark_path.stem
    else:
        benchmark_id = benchmark.get(
            "benchmark_id",
            benchmark_path.stem
        )

        all_scenarios = benchmark.get("scenarios", {})

        if isinstance(all_scenarios, dict):
            scenarios = (
                all_scenarios.get("speech", [])
                + all_scenarios.get("reasoning", [])
            )
        else:
            # Backward compatibility with older flat benchmarks.
            scenarios = all_scenarios
    if not output_dir:
        output_dir = Path("data/recordings") / benchmark_id
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for index, scenario in enumerate(scenarios, start=1):
        scenario_id = scenario.get("id", f"scenario_{index}")
        caller_text = scenario.get("caller", "")

        if not isinstance(caller_text, str) or not caller_text.strip():
            print(f"Skipping {scenario_id}: missing caller text")
            continue

        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", scenario_id)
        output_file = output_dir / f"{index:02d}_{safe_id}.mp3"

        if output_file.exists() and not force:
            print(f"Exists, skipping: {output_file}")
            results.append(str(output_file))
            continue

        try:
            asyncio.run(
                _record_scenario(
                    caller_text.strip(),
                    output_file,
                    voice
                )
            )
            print(f"Recorded: {output_file}")
            results.append(str(output_file))

        except Exception as exc:
            print(f"Failed {scenario_id}: {exc}")

    print(f"\nCompleted: {len(results)}/{len(scenarios)} recordings")
    return results


if __name__ == "__main__":
    # Change this to the benchmark JSON you want to record.
    benchmark_file = (
        "data/benchmarks/"
        "banking_customer_support_agent_v1.json"
    )

    generate_scenario_audio(
        benchmark_path=benchmark_file,
        force=False
    )
