
import json
import time
from pathlib import Path
from collections import Counter

from audio.stt.router import transcribe_audio


BENCHMARK_ID = "banking_customer_support_agent_8a9aa9ac_v2"

MANIFEST_PATH = (
    Path("data/attacked")
    / BENCHMARK_ID
    / "manifest.json"
)

OUTPUT_PATH = (
    Path("data/results")
    / f"{BENCHMARK_ID}_stt_results.json"
)


def main():
    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    results = []

    for index, item in enumerate(manifest, start=1):
        audio_path = Path(item["audio_path"])

        print(f"\n[{index}/{len(manifest)}] {audio_path.name}")

        record = {
            **item,
            "transcript": None,
            "stt_latency_seconds": None,
            "status": "ERROR",
            "error": None,
        }

        try:
            start = time.perf_counter()
            transcript = transcribe_audio(str(audio_path))
            latency = time.perf_counter() - start

            record["transcript"] = transcript
            record["stt_latency_seconds"] = round(latency, 3)
            record["status"] = "SUCCESS"

            print(f"Latency: {latency:.2f}s")
            print(f"Transcript: {transcript}")

        except Exception as exc:
            record["error"] = str(exc)
            print(f"Error: {exc}")

        results.append(record)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    successful = sum(r["status"] == "SUCCESS" for r in results)
    latencies = [
        r["stt_latency_seconds"]
        for r in results
        if r["stt_latency_seconds"] is not None
    ]

    report = {
        "benchmark_id": BENCHMARK_ID,
        "stt_provider": "configured_router",
        "total_files": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "average_latency_seconds": (
            round(sum(latencies) / len(latencies), 3)
            if latencies else None
        ),
        "attack_type_counts": dict(
            Counter(r["attack_type"] for r in results)
        ),
        "results": results,
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 45)
    print("STT BENCHMARK COMPLETE")
    print("=" * 45)
    print(f"Total: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"Average STT latency: {report['average_latency_seconds']}s")
    print(f"Saved report: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
