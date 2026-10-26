import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.response_collector import get_response, load_manifest
from audio.stt.groq_stt import transcribe_audio


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MANIFEST = (
    PROJECT_ROOT / "data" / "manifests" / "food_delivery_manifest.json"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "food_delivery"
    / "transcripts"
    / "response_transcripts.json"
)


def save_transcripts(output_path: Path, records: list[dict]) -> None:
    """Save the transcript records as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = output_path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)


def transcribe_responses(
    manifest_path: str | Path = DEFAULT_MANIFEST,
    output_path: str | Path = DEFAULT_OUTPUT,
) -> dict:
    """Transcribe registered target-agent response recordings."""
    manifest = load_manifest(str(manifest_path))
    output_path = Path(output_path)

    records = []
    counts = {
        "transcribed": 0,
        "response_missing": 0,
        "response_failed": 0,
        "transcription_failed": 0,
    }

    for index, test in enumerate(manifest, start=1):
        test_id = test["test_id"]
        print(f"[{index}/{len(manifest)}] Processing {test_id}...")

        record = {
            "test_id": test_id,
            "scenario_id": test.get("scenario_id"),
            "category": test.get("category"),
            "condition": test.get("condition"),
            "attack_type": test.get("attack_type"),
            "response_audio_path": None,
            "transcript": None,
            "status": None,
            "error": None,
            "transcribed_at": datetime.now(timezone.utc).isoformat(),
        }

        response = get_response(test_id)

        if response is None:
            record["status"] = "response_missing"
            counts["response_missing"] += 1

        elif response.get("status") != "completed":
            record["status"] = "response_failed"
            record["error"] = (
                response.get("error")
                or f"Response status: {response.get('status')}"
            )
            counts["response_failed"] += 1

        else:
            audio_path = response.get("response_audio_path")

            if not audio_path or not Path(audio_path).is_file():
                record["status"] = "response_missing"
                record["error"] = "Registered response audio file not found."
                counts["response_missing"] += 1

            else:
                record["response_audio_path"] = str(Path(audio_path).resolve())

                try:
                    transcript = transcribe_audio(audio_path)

                    if not transcript:
                        raise ValueError("Groq Whisper returned an empty transcript.")

                    record["transcript"] = transcript
                    record["status"] = "transcribed"
                    counts["transcribed"] += 1

                except Exception as exc:
                    record["status"] = "transcription_failed"
                    record["error"] = f"{type(exc).__name__}: {exc}"
                    counts["transcription_failed"] += 1

        records.append(record)

        # Save after each test so progress is not lost if a later call fails.
        save_transcripts(output_path, records)

        print(f"    Status: {record['status']}")

    summary = {
        "manifest_total": len(manifest),
        **counts,
        "output_path": str(output_path.resolve()),
    }

    print("\nTranscription summary")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe registered target-agent response recordings."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to the benchmark manifest.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path for the transcript JSON output.",
    )
    args = parser.parse_args()

    transcribe_responses(
        manifest_path=args.manifest,
        output_path=args.output,
    )