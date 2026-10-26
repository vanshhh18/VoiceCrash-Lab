"""Run voice-agent tests and save the resulting response-recording metadata.

This is the agent-execution runner. It intentionally does not perform automatic
LLM evaluation; the Streamlit dashboard should reveal its Evaluate Responses
section only after all selected response recordings exist.
"""
import argparse
import json
import logging
from pathlib import Path
from typing import Any

from app.agent_adapters.api_agent import APIAgentAdapter
from app.agent_adapters.runner import run_single_test

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data" / "manifests"
DEFAULT_RESULTS_DIR = ROOT / "data" / "results" / "agent_responses"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resolve_manifest(manifest_arg: str | None) -> Path:
    """Resolve a supplied manifest, or choose the newest manifest in the default folder."""
    if manifest_arg:
        path = Path(manifest_arg)
        if not path.is_absolute():
            path = ROOT / path
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Manifest not found: {path}")
        return path

    candidates = sorted(
        DEFAULT_MANIFEST.glob("*_manifest.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No *_manifest.json files found in {DEFAULT_MANIFEST}"
        )
    return candidates[0].resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run audio test cases against a connected voice agent."
    )
    parser.add_argument(
        "--agent",
        choices=("api", "dummy"),
        default="api",
        help="Agent adapter to use (default: api).",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Path to the test manifest. Defaults to the newest manifest.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of tests to run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the manifest without sending audio to the agent.",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    manifest_path = resolve_manifest(args.manifest)
    with manifest_path.open("r", encoding="utf-8") as file:
        tests = json.load(file)

    if not isinstance(tests, list):
        raise ValueError("Manifest must contain a JSON list.")

    if any(not isinstance(test, dict) or not test.get("test_id") for test in tests):
        raise ValueError("Every manifest entry must be an object with a test_id.")

    test_ids = [test["test_id"] for test in tests]
    if len(test_ids) != len(set(test_ids)):
        raise ValueError("Manifest contains duplicate test IDs.")

    selected_tests = tests[: args.limit] if args.limit else tests
    DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DEFAULT_RESULTS_DIR / f"batch_results_{args.agent}.json"

    print("\n========== VOICE AGENT TEST RUN ==========")
    print(f"Agent: {args.agent}")
    print(f"Manifest: {manifest_path}")
    print(f"Tests selected: {len(selected_tests)}")

    if args.dry_run:
        print("Dry run only; no requests sent.")
        print("Manifest validation successful.")
        return 0

    if args.agent == "api":
        # APIAgentAdapter.from_config reads the endpoint/token settings from
        # the environment supplied by the Streamlit connection form.
        adapter = APIAgentAdapter.from_config()
    else:
        # Import only when the dummy adapter is requested, so API-only setups
        # do not fail if the dummy adapter module is absent.
        try:
            from app.agent_adapters.dummy_agent import DummyAgentAdapter
        except ImportError as exc:
            raise ImportError(
                "Dummy adapter was selected, but "
                "app.agent_adapters.dummy_agent.DummyAgentAdapter "
                "could not be imported."
            ) from exc
        adapter = DummyAgentAdapter()

    results: list[dict[str, Any]] = []
    total = len(selected_tests)

    for index, test_case in enumerate(selected_tests, start=1):
        test_id = test_case["test_id"]
        print(f"\n[{index}/{total}] Running {test_id}...")

        try:
            result = run_single_test(adapter, test_case)
            result.setdefault("test_id", test_id)
            result.setdefault("status", "success")
            results.append(result)
            print(f"Saved response recording for {test_id}: {result.get('response_audio_path', 'path not returned')}")
        except Exception as exc:
            logger.exception("Agent test failed for %s", test_id)
            results.append({
                "test_id": test_id,
                "status": "failed",
                "error": str(exc),
            })
            print(f"Test failed for {test_id}: {exc}")

        # Save incrementally so completed results survive if a later test fails.
        temp_path = output_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(output_path)

    succeeded = sum(item.get("status") == "success" for item in results)
    failed = len(results) - succeeded

    print("\n========== AGENT TEST SUMMARY ==========")
    print(f"Tests selected: {total}")
    print(f"Successful responses: {succeeded}")
    print(f"Failed tests: {failed}")
    print(f"Batch results saved to: {output_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
