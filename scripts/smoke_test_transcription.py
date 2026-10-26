import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from app import response_collector
from app.response_collector import register_response
from app.transcribe_responses import transcribe_responses


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MANIFEST_AUDIO = (
    PROJECT_ROOT
    / "data"
    / "recordings"
    / "timbre_test_food_delivery"
    / "01_scenario_1.mp3"
)


def main():
    if not MANIFEST_AUDIO.is_file():
        raise FileNotFoundError(
            f"Smoke-test audio not found: {MANIFEST_AUDIO}"
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        results_dir = root / "results"
        results_dir.mkdir(parents=True)

        registry_path = results_dir / "response_registry.json"
        manifest_path = root / "smoke_manifest.json"
        output_path = root / "response_transcripts.json"

        manifest = [
            {
                "test_id": "smoke_test_001",
                "scenario_id": "scenario_1",
                "category": "speech",
                "condition": "clean",
                "attack_type": None,
            }
        ]

        manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with (
            patch.object(
                response_collector,
                "RESULTS_DIR",
                results_dir,
            ),
            patch.object(
                response_collector,
                "REGISTRY_PATH",
                registry_path,
            ),
        ):
            register_response(
                test_id="smoke_test_001",
                response_audio_path=str(MANIFEST_AUDIO),
                status="completed",
            )

            summary = transcribe_responses(
                manifest_path=manifest_path,
                output_path=output_path,
            )

        saved_records = json.loads(
            output_path.read_text(encoding="utf-8")
        )

        print("\nSmoke-test result:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        if saved_records:
            print("\nSaved transcript record:")
            print(
                json.dumps(
                    saved_records[0],
                    indent=2,
                    ensure_ascii=False,
                )
            )

        if (
            summary["transcribed"] != 1
            or saved_records[0]["test_id"] != "smoke_test_001"
            or not saved_records[0]["transcript"]
        ):
            raise RuntimeError("Transcription smoke test failed.")

        print("\nPASS: audio → Groq Whisper → transcript JSON")


if __name__ == "__main__":
    main()