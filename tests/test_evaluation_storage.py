
import tempfile
import unittest
from pathlib import Path

from app.evaluation_storage import load_evaluations, save_evaluation


class TestEvaluationStorage(unittest.TestCase):

    def test_missing_file_returns_empty_dictionary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "results.json"

            result = load_evaluations(output_path)

            self.assertEqual(result, {})

    def test_save_and_reload_evaluation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "results.json"

            evaluation = {
                "status": "evaluated",
                "scores": {
                    "task_success": 4,
                    "hallucination": 5,
                },
                "overall_pass": True,
            }

            save_evaluation("test_001", evaluation, output_path)
            loaded = load_evaluations(output_path)

            self.assertEqual(loaded["test_001"], evaluation)

    def test_updating_one_test_preserves_other_tests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "results.json"

            save_evaluation(
                "test_001",
                {"status": "evaluated", "overall_pass": True},
                output_path,
            )
            save_evaluation(
                "test_002",
                {"status": "failed", "overall_pass": False},
                output_path,
            )
            save_evaluation(
                "test_001",
                {"status": "evaluated", "overall_pass": False},
                output_path,
            )

            loaded = load_evaluations(output_path)

            self.assertEqual(len(loaded), 2)
            self.assertFalse(loaded["test_001"]["overall_pass"])
            self.assertEqual(loaded["test_002"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
