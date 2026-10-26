import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import response_collector


class TestResponseCollector(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.results_dir = Path(self.temp_dir.name) / "results"
        self.registry_path = self.results_dir / "response_registry.json"

        self.patcher = patch.multiple(
            response_collector,
            RESULTS_DIR=self.results_dir,
            REGISTRY_PATH=self.registry_path,
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        self.audio_path = Path(self.temp_dir.name) / "response.wav"
        self.audio_path.write_bytes(b"temporary test audio")

    def test_completed_response_is_registered(self):
        record = response_collector.register_response(
            test_id="test_001",
            response_audio_path=str(self.audio_path),
        )

        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["test_id"], "test_001")
        self.assertTrue(self.registry_path.exists())

    def test_response_can_be_retrieved(self):
        response_collector.register_response(
            test_id="test_002",
            response_audio_path=str(self.audio_path),
        )

        record = response_collector.get_response("test_002")

        self.assertIsNotNone(record)
        self.assertEqual(record["test_id"], "test_002")

    def test_timeout_is_registered(self):
        record = response_collector.register_response(
            test_id="test_003",
            response_audio_path="",
            status="timeout",
            error="Target agent timed out",
        )

        self.assertEqual(record["status"], "timeout")
        self.assertIsNone(record["response_audio_path"])

    def test_failed_response_is_registered(self):
        record = response_collector.register_response(
            test_id="test_004",
            response_audio_path="",
            status="failed",
            error="Connection failed",
        )

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error"], "Connection failed")

    def test_missing_audio_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            response_collector.register_response(
                test_id="test_005",
                response_audio_path="missing_response.wav",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)