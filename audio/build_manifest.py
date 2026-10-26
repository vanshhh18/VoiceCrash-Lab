import argparse
import json
from pathlib import Path


ATTACK_SUFFIXES = {
    "_traffic": ("traffic_noise", "-2 dB SNR"),
    "_fan": ("fan_noise", "-10 dB SNR"),
    "_crowd": ("crowd_noise", "2 dB SNR"),
    "_phone": ("phone_line", None),
    "_dropouts": ("audio_dropouts", None),
    "_muffled": ("muffled_speech", None),
}


def classify_audio(file):
    stem = file.stem

    for suffix, details in ATTACK_SUFFIXES.items():
        if stem.endswith(suffix):
            return details

    return "clean", None


def build_manifest(clean_dir, attacked_dir, benchmark_path, output_file):
    clean_root = Path(clean_dir)
    attacked_root = Path(attacked_dir)
    benchmark_path = Path(benchmark_path)
    output_path = Path(output_file)

    for folder in (clean_root, attacked_root):
        if not folder.is_dir():
            raise FileNotFoundError(f"Directory not found: {folder}")

    if not benchmark_path.is_file():
        raise FileNotFoundError(f"Benchmark not found: {benchmark_path}")

    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))

    scenario_lookup = {}
    speech_scenarios = benchmark.get("scenarios", {}).get("speech", [])
    reasoning_scenarios = benchmark.get("scenarios", {}).get("reasoning", [])
    for category, scenarios in (("speech", speech_scenarios), ("reasoning", reasoning_scenarios)):
        for scenario in scenarios:
            key = (category, scenario["id"])
            scenario_lookup[key] = {
                "category": category,
                "scenario_type": scenario.get("type", "unknown"),
                "expected": scenario.get("expected", ""),
                "language": benchmark.get("language", "unknown"),
            }

    manifest = []
    seen = set()
    speech_count = len(speech_scenarios)
    reasoning_count = len(reasoning_scenarios)

    def add_audio(file, category, scenario_id, condition, attack_type, attack_level):
        key = (category, scenario_id)
        if key not in scenario_lookup:
            print(f"Skipping: {file.name} (scenario not found: {key})")
            return
        resolved_path = file.resolve()
        if resolved_path in seen:
            return
        seen.add(resolved_path)
        scenario = scenario_lookup[key]
        manifest.append({
            "test_id": f"test_{len(manifest) + 1:03d}",
            "scenario_id": scenario_id,
            "category": scenario["category"],
            "scenario_type": scenario["scenario_type"],
            "language": scenario["language"],
            "condition": condition,
            "attack_type": attack_type,
            "attack_level": attack_level,
            "expected": scenario["expected"],
            "audio_path": str(resolved_path),
        })

    def scenario_for_clean_file(file):
        prefix = file.stem.split("_", 1)[0]
        if not prefix.isdigit():
            return None
        number = int(prefix)
        if 1 <= number <= speech_count:
            return "speech", speech_scenarios[number - 1].get("id")
        reasoning_index = number - speech_count - 1
        if 0 <= reasoning_index < reasoning_count:
            return "reasoning", reasoning_scenarios[reasoning_index].get("id")
        return None

    for file in sorted(clean_root.rglob("*")):
        if not file.is_file() or file.suffix.lower() not in {".wav", ".mp3"}:
            continue
        mapping = scenario_for_clean_file(file)
        if mapping:
            add_audio(file, mapping[0], mapping[1], "clean", "none", None)

    # Attacked filenames preserve the numeric prefix of their source clean recording.
    for file in sorted(attacked_root.rglob("*")):
        if not file.is_file() or file.suffix.lower() not in {".wav", ".mp3"}:
            continue
        prefix = file.stem.split("_", 1)[0]
        if not prefix.isdigit():
            continue
        number = int(prefix)
        if not 1 <= number <= speech_count:
            continue
        scenario_id = speech_scenarios[number - 1].get("id")
        attack_type, attack_level = classify_audio(file)
        add_audio(file, "speech", scenario_id, "attacked", attack_type, attack_level)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    clean_count = sum(x["condition"] == "clean" for x in manifest)
    attacked_count = sum(x["condition"] == "attacked" for x in manifest)

    print(f"Manifest created: {output_path}")
    print(f"Clean inputs: {clean_count}")
    print(f"Attacked inputs: {attacked_count}")
    print(f"Total inputs: {len(manifest)}")

    expected_count = speech_count + reasoning_count + (6 * speech_count)
    if len(manifest) != expected_count:
        print(f"WARNING: Expected {expected_count} inputs from this benchmark, found {len(manifest)}.")

    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a VoiceCrashLab audio test manifest."
    )

    parser.add_argument("--clean-dir", required=True)
    parser.add_argument("--attacked-dir", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    build_manifest(
        clean_dir=args.clean_dir,
        attacked_dir=args.attacked_dir,
        benchmark_path=args.benchmark,
        output_file=args.output,
    )