import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import response_collector
from app.import_responses import import_responses


class TestResponseImporter(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.manifest_path = self.root / "manifest.json"
        self.response_dir = self.root / "responses"

        self.response_dir.mkdir()

        manifest = [
            {"test_id": "test_001"},
            {"test_id": "test_002"},
            {"test_id": "test_003"},
        ]

        self.manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        (self.response_dir / "test_001.wav").write_bytes(b"audio 1")
        (self.response_dir / "test_002.mp3").write_bytes(b"audio 2")

        self.results_dir = self.root / "results"
        self.registry_path = self.results_dir / "response_registry.json"

        patcher = patch.multiple(
            response_collector,
            RESULTS_DIR=self.results_dir,
            REGISTRY_PATH=self.registry_path,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_imports_available_recordings(self):
        result = import_responses(
            str(self.manifest_path),
            str(self.response_dir),
        )

        self.assertEqual(result["manifest_total"], 3)
        self.assertEqual(result["imported_count"], 2)
        self.assertEqual(result["missing_count"], 1)

    def test_missing_recording_is_reported(self):
        result = import_responses(
            str(self.manifest_path),
            str(self.response_dir),
        )

        self.assertEqual(result["missing_test_ids"], ["test_003"])

    def test_imported_responses_are_registered(self):
        import_responses(
            str(self.manifest_path),
            str(self.response_dir),
        )

        record = response_collector.get_response("test_001")

        self.assertIsNotNone(record)
        self.assertEqual(record["status"], "completed")


if __name__ == "__main__":
    unittest.main(verbosity=2)