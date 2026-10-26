import argparse
import json
from pathlib import Path

from app.agent_adapters.api_agent import APIAgentAdapter
from app.agent_adapters.config import load_agent_config
from app.agent_adapters.runner import run_single_test


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "manifests" / "food_delivery_manifest.json"


def main():
    parser = argparse.ArgumentParser(
        description="Connect and test a voice agent"
    )
    parser.add_argument("--test-id", default="test_001")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without calling the agent API",
    )
    args = parser.parse_args()

    config = load_agent_config()

    with MANIFEST.open(encoding="utf-8") as file:
        tests = json.load(file)

    test_case = next(
        (test for test in tests if test["test_id"] == args.test_id),
        None,
    )

    if test_case is None:
        raise ValueError(f"Test ID not found in manifest: {args.test_id}")

    if args.dry_run:
        print("Dry run: OK")
        print(f"Agent: {config.name}")
        print(f"Endpoint: {config.endpoint}")
        print(f"Input field: {config.input_field}")
        print(f"Token configured: {'yes' if config.token else 'no'}")
        print(f"Test ID: {test_case['test_id']}")
        print("Agent API was NOT called.")
        return

    adapter = APIAgentAdapter.from_config()
    result = run_single_test(adapter, test_case)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()