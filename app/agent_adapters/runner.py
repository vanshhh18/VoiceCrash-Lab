from typing import Any

from app.agent_adapters.base import AgentAdapter


def run_single_test(
    adapter: AgentAdapter,
    test_case: dict[str, Any],
) -> dict[str, Any]:
    """Run one test through any compatible agent adapter."""

    test_id = test_case.get("test_id")

    if not test_id:
        raise ValueError("Test case must contain a test_id")

    result = adapter.process_test(test_case)

    if not isinstance(result, dict):
        raise TypeError("Adapter must return a dictionary")

    if result.get("test_id") != test_id:
        raise ValueError(
            f"Expected test_id {test_id}, "
            f"but adapter returned {result.get('test_id')}"
        )

    if not result.get("status"):
        raise ValueError("Adapter result must contain a status")

    return result