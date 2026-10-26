import argparse
from pathlib import Path

from app.response_collector import load_manifest, register_response


SUPPORTED_AUDIO_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def import_responses(manifest_path: str, response_dir: str) -> dict:
    """Import audio responses from any compatible voice agent."""

    manifest = load_manifest(manifest_path)
    response_root = Path(response_dir)

    if not response_root.is_dir():
        raise FileNotFoundError(
            f"Response directory not found: {response_root}"
        )

    imported = []
    missing = []

    for test in manifest:
        test_id = test["test_id"]

        matches = [
            file
            for file in response_root.glob(f"{test_id}.*")
            if file.is_file()
            and file.suffix.lower() in SUPPORTED_AUDIO_FORMATS
        ]

        if len(matches) > 1:
            raise ValueError(
                f"Multiple response recordings found for {test_id}"
            )

        if not matches:
            missing.append(test_id)
            continue

        record = register_response(
            test_id=test_id,
            response_audio_path=str(matches[0].resolve()),
            status="completed",
        )

        imported.append(record["test_id"])

    result = {
        "manifest_total": len(manifest),
        "imported_count": len(imported),
        "missing_count": len(missing),
        "imported_test_ids": imported,
        "missing_test_ids": missing,
    }

    print(f"Manifest tests: {result['manifest_total']}")
    print(f"Responses imported: {result['imported_count']}")
    print(f"Responses not found: {result['missing_count']}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import voice-agent response recordings into VoiceCrashLab."
    )

    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to the VoiceCrashLab test manifest",
    )

    parser.add_argument(
        "--response-dir",
        required=True,
        help="Folder containing response audio files named by test_id",
    )

    args = parser.parse_args()

    import_responses(
        manifest_path=args.manifest,
        response_dir=args.response_dir,
    )