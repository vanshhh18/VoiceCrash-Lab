
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.llm_judge import _validate_result


def make_valid_result():
    return {
        "scores": {
            "task_success": 4,
            "instruction_adherence": 5,
            "hallucination": 5,
            "recovery": 3,
            "reasoning_correctness": 4,
        },
        "overall_pass": True,
        "evidence": [
            "The agent asked for the missing order identifier."
        ],
        "explanation": "The agent followed the clarification requirement.",
        "uncertainties": [
            "Actual order status was not independently verified."
        ],
    }


class TestLLMJudge(unittest.TestCase):

    def test_valid_result_is_accepted(self):
        result = make_valid_result()
        validated = _validate_result(result)

        self.assertEqual(validated["scores"]["task_success"], 4)
        self.assertTrue(validated["overall_pass"])

    def test_score_above_five_is_rejected(self):
        result = make_valid_result()
        result["scores"]["task_success"] = 6

        with self.assertRaises(ValueError):
            _validate_result(result)

    def test_missing_score_is_rejected(self):
        result = make_valid_result()
        del result["scores"]["recovery"]

        with self.assertRaises(ValueError):
            _validate_result(result)

    def test_non_boolean_overall_pass_is_rejected(self):
        result = make_valid_result()
        result["overall_pass"] = "yes"

        with self.assertRaises(ValueError):
            _validate_result(result)

    @patch("app.llm_judge.Groq")
    @patch.dict(os.environ, {
        "GROQ_API_KEY": "test-key",
        "GROQ_JUDGE_MODEL": "test-model",
    })
    def test_judge_transcript_returns_valid_result(self, mock_groq):
        from app.llm_judge import judge_transcript

        expected_result = make_valid_result()

        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(expected_result)
                    )
                )
            ]
        )

        scenario = {
            "id": "scenario_1",
            "type": "simple_request",
            "difficulty": "easy",
            "language": "Hinglish",
            "conditions": [],
            "caller": "Mera order track karo.",
            "expected": "Ask for an order ID if it is missing.",
        }

        result = judge_transcript(
            scenario,
            "Please share your order ID so I can check the status.",
        )

        self.assertEqual(result["scores"]["task_success"], 4)
        self.assertTrue(result["overall_pass"])
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.llm_judge.Groq")
    @patch.dict(os.environ, {
        "GROQ_API_KEY": "test-key",
        "GROQ_JUDGE_MODEL": "test-model",
    })
    def test_invalid_json_is_rejected(self, mock_groq):
        from app.llm_judge import judge_transcript

        mock_client = MagicMock()
        mock_groq.return_value = mock_client

        mock_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="not valid JSON")
                )
            ]
        )

        scenario = {
            "id": "scenario_1",
            "expected": "Ask for the missing order ID.",
        }

        with self.assertRaises(json.JSONDecodeError):
            judge_transcript(
                scenario,
                "Please share your order ID.",
            )


if __name__ == "__main__":
    unittest.main()
