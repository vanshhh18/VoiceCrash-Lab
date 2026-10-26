import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.transcribe_responses import transcribe_responses


class TestTranscribeResponses(unittest.TestCase):

    def test_missing_responses_are_recorded_without_api_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            manifest_path = root / "manifest.json"
            output_path = root / "transcripts.json"

            manifest = [
                {
                    "test_id": "test_001",
                    "scenario_id": "scenario_1",
                    "category": "speech",
                    "condition": "clean",
                    "attack_type": None,
                },
                {
                    "test_id": "test_002",
                    "scenario_id": "scenario_2",
                    "category": "speech",
                    "condition": "attacked",
                    "attack_type": "traffic_noise",
                },
            ]

            manifest_path.write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            with (
                patch(
                    "app.transcribe_responses.get_response",
                    return_value=None,
                ),
                patch(
                    "app.transcribe_responses.transcribe_audio"
                ) as mock_transcribe,
            ):
                summary = transcribe_responses(
                    manifest_path=manifest_path,
                    output_path=output_path,
                )

            mock_transcribe.assert_not_called()

            self.assertEqual(summary["manifest_total"], 2)
            self.assertEqual(summary["response_missing"], 2)
            self.assertEqual(summary["transcribed"], 0)

            saved = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(len(saved), 2)
            self.assertEqual(saved[0]["test_id"], "test_001")
            self.assertEqual(saved[0]["status"], "response_missing")
            self.assertEqual(saved[1]["test_id"], "test_002")
            self.assertEqual(saved[1]["status"], "response_missing")


if __name__ == "__main__":
    unittest.main()