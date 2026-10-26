from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class AgentAdapter(ABC):
    """Common interface for connecting different voice agents."""

    @abstractmethod
    def process_test(self, test_case: dict[str, Any]) -> dict[str, Any]:
        """
        Run one test against the target agent.

        Return a dictionary containing:
        - test_id
        - status
        - response_audio_path (when available)
        """
        raise NotImplementedError