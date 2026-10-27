"""Tests for saved session history."""

import json
import tempfile
import unittest
from pathlib import Path

from capture.history import SessionHistory
from capture.session import CaptureSession


class TestSessionHistory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        self.history = SessionHistory(self.output_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_session(self, transcript="Example transcript"):
        session = CaptureSession(output_dir=self.output_dir)
        session.transcript_file.write_text(
            transcript,
            encoding="utf-8",
        )
        return session

    def test_list_sessions_returns_created_session(self):
        session = self.create_session()

        sessions = self.history.list_sessions()

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], session.session_id)

    def test_get_session_returns_metadata(self):
        session = self.create_session()

        result = self.history.get_session(session.session_id)

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "recording")

    def test_read_transcript(self):
        session = self.create_session("Bonjour tout le monde.")

        transcript = self.history.read_transcript(session.session_id)

        self.assertEqual(transcript, "Bonjour tout le monde.")

    def test_rename_session(self):
        session = self.create_session()

        self.history.rename_session(session.session_id, "French lesson")

        result = self.history.get_session(session.session_id)

        self.assertEqual(result["name"], "French lesson")

    def test_rename_rejects_empty_name(self):
        session = self.create_session()

        with self.assertRaises(ValueError):
            self.history.rename_session(session.session_id, "   ")

    def test_delete_session(self):
        session = self.create_session()

        self.history.delete_session(session.session_id)

        self.assertIsNone(self.history.get_session(session.session_id))
        self.assertFalse(session.session_dir.exists())

    def test_missing_output_directory_returns_empty_list(self):
        history = SessionHistory(self.output_dir / "missing")

        self.assertEqual(history.list_sessions(), [])

    def test_invalid_metadata_is_skipped(self):
        bad_session = self.output_dir / "session_invalid"
        bad_session.mkdir()
        (bad_session / "metadata.json").write_text(
            "{invalid json",
            encoding="utf-8",
        )

        self.assertEqual(self.history.list_sessions(), [])


if __name__ == "__main__":
    unittest.main()