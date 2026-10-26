"""Generate VoiceCrashLab scenarios, recordings, attacks, and a manifest.

This stage deliberately does NOT run STT or call the target agent. The UI has
separate steps for generating a suite and then testing/evaluating the agent.
"""
import json
from pathlib import Path

from dotenv import load_dotenv

from scenarios.adversarial_generator import generate_adversarial_scenarios
from audio.scenario_audio import generate_scenario_audio
from audio.audio_attacks import generate_attack_set
from audio.build_manifest import build_manifest

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _project_path(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def run_pipeline(agent_role, business_context, supported_tasks,
                 language="Hinglish", scenario_count=5,
                 voice="hi-IN-SwaraNeural"):
    """Create 2*scenario_count scenarios and all available audio variants."""
    agent_role = str(agent_role).strip()
    business_context = str(business_context).strip()
    supported_tasks = [str(task).strip() for task in supported_tasks
                       if isinstance(task, str) and task.strip()]
    scenario_count = int(scenario_count)
    if not agent_role:
        raise ValueError("Agent name / role is required.")
    if not business_context:
        raise ValueError("Business context is required.")
    if not supported_tasks:
        raise ValueError("Enter at least one supported task.")
    if not 1 <= scenario_count <= 20:
        raise ValueError("Scenario count must be between 1 and 20.")

    scenarios, benchmark_path = generate_adversarial_scenarios(
        agent_role=agent_role, business_context=business_context,
        supported_tasks=supported_tasks, language=language,
        count=scenario_count, reuse_existing=False,
    )
    if not scenarios or not benchmark_path:
        raise RuntimeError("Scenario generation failed. Check the terminal for details.")

    benchmark_path = _project_path(benchmark_path).resolve()
    benchmark_id = benchmark_path.stem
    recording_dir = ROOT / "data" / "recordings" / benchmark_id
    attacked_dir = ROOT / "data" / "attacked" / benchmark_id
    manifest_path = ROOT / "data" / "manifests" / f"{benchmark_id}_manifest.json"

    recordings = generate_scenario_audio(
        benchmark_path=str(benchmark_path), output_dir=str(recording_dir),
        voice=voice, force=True,
    )
    if not recordings:
        raise RuntimeError("No scenario recordings were generated.")

    # The attack generator creates the attacked variants from the speech clean
    # recordings. Reasoning clean recordings remain in the manifest too.
    speech_count = len(scenarios.get("speech", [])) if isinstance(scenarios, dict) else scenario_count
    generate_attack_set(input_dir=str(recording_dir), output_dir=str(attacked_dir),
                        noise_dir=str(ROOT / "data" / "background_noise"),
                        max_files=speech_count)
    manifest_path = Path(build_manifest(
        clean_dir=recording_dir, attacked_dir=attacked_dir,
        benchmark_path=benchmark_path, output_file=manifest_path,
    )).resolve()
    if not manifest_path.is_file():
        raise RuntimeError("Manifest generation failed.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest:
        raise RuntimeError("No audio inputs were generated; manifest is empty.")

    clean_count = sum(item.get("condition") == "clean" for item in manifest)
    attacked_count = sum(item.get("condition") == "attacked" for item in manifest)
    reasoning_count = sum(item.get("category") == "reasoning" for item in manifest)
    speech_count = sum(item.get("category") == "speech" for item in manifest)
    result = {
        "agent_role": agent_role,
        "benchmark_path": str(benchmark_path),
        "recording_dir": str(recording_dir),
        "attacked_dir": str(attacked_dir),
        "manifest_path": str(manifest_path),
        "scenario_count": sum(len(v) for v in scenarios.values()) if isinstance(scenarios, dict) else len(scenarios),
        "recording_count": len(recordings),
        "clean_count": clean_count,
        "attack_count": attacked_count,
        "manifest_input_count": len(manifest),
        "speech_test_count": speech_count,
        "reasoning_test_count": reasoning_count,
        "status": "generated",
    }
    print("\nTest suite generation completed (agent not called yet).")
    for key, value in result.items():
        print(f"{key}: {value}")
    return result
