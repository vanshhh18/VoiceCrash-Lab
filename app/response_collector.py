import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = PROJECT_ROOT / "data" / "results"
REGISTRY_PATH = RESULTS_DIR / "response_registry.json"


def register_response(
    test_id: str,
    response_audio_path: str,
    status: str = "completed",
    error: str | None = None,
) -> dict:
    """Register a target-agent response against its unique test ID."""

    if not test_id.strip():
        raise ValueError("test_id cannot be empty")

    allowed_statuses = {"completed", "failed", "timeout"}

    if status not in allowed_statuses:
        raise ValueError(
            f"status must be one of {sorted(allowed_statuses)}"
        )

    audio_path = Path(response_audio_path)

    if status == "completed":
        if not audio_path.is_file():
            raise FileNotFoundError(
                f"Response audio file not found: {audio_path}"
            )

        if audio_path.suffix.lower() not in {
            ".wav", ".mp3", ".m4a", ".flac", ".ogg"
        }:
            raise ValueError("Unsupported response audio format")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open("r", encoding="utf-8") as file:
            registry = json.load(file)
    else:
        registry = {}

    record = {
        "test_id": test_id,
        "status": status,
        "response_audio_path": (
            str(audio_path.resolve()) if status == "completed" else None
        ),
        "error": error,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    registry[test_id] = record

    temporary_path = REGISTRY_PATH.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(registry, file, indent=2, ensure_ascii=False)

    temporary_path.replace(REGISTRY_PATH)

    return record


def get_response(test_id: str) -> dict | None:
    """Retrieve a registered response by its unique test ID."""

    if not REGISTRY_PATH.exists():
        return None

    with REGISTRY_PATH.open("r", encoding="utf-8") as file:
        registry = json.load(file)

    return registry.get(test_id)


def load_manifest(manifest_path: str) -> list[dict]:
    """Load and validate the VoiceCrashLab test manifest."""

    path = Path(manifest_path)

    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    if not isinstance(manifest, list):
        raise ValueError("Manifest must contain a list of test cases")

    test_ids = [item.get("test_id") for item in manifest]

    if any(not test_id for test_id in test_ids):
        raise ValueError("Every manifest entry must have a test_id")

    if len(test_ids) != len(set(test_ids)):
        raise ValueError("Manifest contains duplicate test_id values")

    return manifest


def get_pending_tests(manifest_path: str) -> list[dict]:
    """Return tests that do not yet have a completed response."""

    manifest = load_manifest(manifest_path)

    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open("r", encoding="utf-8") as file:
            registry = json.load(file)
    else:
        registry = {}

    pending = []

    for test in manifest:
        test_id = test["test_id"]
        record = registry.get(test_id)

        if record is None or record.get("status") != "completed":
            pending.append(test)

    return pending