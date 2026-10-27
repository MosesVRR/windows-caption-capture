"""Tests for capture session management."""

import json
import tempfile
import unittest
from pathlib import Path

from capture.session import CaptureSession


class TestCaptureSession(unittest.TestCase):
    def test_session_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = CaptureSession(output_dir=temp_dir)

            self.assertTrue(session.session_dir.is_dir())
            self.assertTrue(session.transcript_file.is_file())
            self.assertTrue(session.snapshots_file.is_file())
            self.assertTrue(session.metadata_file.is_file())

    def test_initial_metadata_marks_session_as_recording(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = CaptureSession(output_dir=temp_dir)

            metadata = json.loads(
                session.metadata_file.read_text(encoding="utf-8")
            )

            self.assertEqual(metadata["status"], "recording")
            self.assertIsNone(metadata["ended_at"])
            self.assertIsNone(metadata["duration_seconds"])

    def test_finish_updates_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = CaptureSession(output_dir=temp_dir)
            session.finish()

            metadata = json.loads(
                session.metadata_file.read_text(encoding="utf-8")
            )

            self.assertEqual(metadata["status"], "completed")
            self.assertIsNotNone(metadata["ended_at"])
            self.assertIsNotNone(metadata["duration_seconds"])

    def test_finish_can_record_interrupted_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session = CaptureSession(output_dir=temp_dir)
            session.finish(status="interrupted")

            metadata = json.loads(
                session.metadata_file.read_text(encoding="utf-8")
            )

            self.assertEqual(metadata["status"], "interrupted")


if __name__ == "__main__":
    unittest.main()