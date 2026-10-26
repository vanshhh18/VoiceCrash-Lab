
from pathlib import Path
import json
from pydub import AudioSegment

ROOT = Path("data/attacked/banking_customer_support_agent_v1")
MANIFEST = ROOT / "manifest.json"

if not MANIFEST.exists():
    raise FileNotFoundError(
        f"Manifest not found: {MANIFEST}. Run python -m audio.build_manifest first."
    )

items = json.loads(MANIFEST.read_text(encoding="utf-8"))
passed = 0
failed = []

for item in items:
    path = Path(item["audio_path"])

    try:
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError("File missing or empty")

        audio = AudioSegment.from_file(path)

        if len(audio) == 0:
            raise ValueError("Audio duration is zero")

        item["duration_ms"] = len(audio)
        item["sample_rate"] = audio.frame_rate
        item["channels"] = audio.channels
        item["file_size_bytes"] = path.stat().st_size
        item["validation"] = "PASS"
        passed += 1

    except Exception as exc:
        item["validation"] = "FAIL"
        item["error"] = str(exc)
        failed.append((str(path), str(exc)))

MANIFEST.write_text(
    json.dumps(items, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(f"Total files: {len(items)}")
print(f"Passed: {passed}")
print(f"Failed: {len(failed)}")

for path, error in failed:
    print(f"FAIL: {path} -> {error}")
