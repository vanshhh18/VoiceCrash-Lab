
import json
from pathlib import Path
from typing import Any


DEFAULT_RESULTS_PATH = Path(
    "data/results/food_delivery/evaluations/evaluation_results.json"
)


def load_evaluations(
    output_path: str | Path = DEFAULT_RESULTS_PATH,
) -> dict[str, dict[str, Any]]:
    """Load saved evaluations, indexed by test_id."""
    path = Path(output_path)

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Evaluation results must be a JSON object.")

    return data


def save_evaluation(
    test_id: str,
    evaluation: dict[str, Any],
    output_path: str | Path = DEFAULT_RESULTS_PATH,
) -> None:
    """Save or update one evaluation without discarding other results."""
    if not test_id or not isinstance(test_id, str):
        raise ValueError("test_id must be a non-empty string.")

    if not isinstance(evaluation, dict):
        raise TypeError("evaluation must be a dictionary.")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    evaluations = load_evaluations(path)
    evaluations[test_id] = evaluation

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(
            evaluations,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(path)
