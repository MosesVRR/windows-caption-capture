"""Discover and manage saved caption capture sessions."""

import json
import shutil
from pathlib import Path


class SessionHistory:
    """Provide access to saved capture sessions."""

    def __init__(self, output_dir: str | Path = "transcripts") -> None:
        self.output_dir = Path(output_dir)

    def list_sessions(self) -> list[dict]:
        """Return session metadata, newest first."""
        if not self.output_dir.exists():
            return []

        sessions = []

        for session_dir in self.output_dir.iterdir():
            if not session_dir.is_dir():
                continue

            metadata_file = session_dir / "metadata.json"

            if not metadata_file.is_file():
                continue

            try:
                metadata = json.loads(
                    metadata_file.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                continue

            metadata["_directory"] = str(session_dir)
            sessions.append(metadata)

        sessions.sort(
            key=lambda item: item.get("started_at", ""),
            reverse=True,
        )

        return sessions

    def get_session(self, session_id: str) -> dict | None:
        """Return metadata for one session."""
        for session in self.list_sessions():
            if session.get("session_id") == session_id:
                return session

        return None

    def read_transcript(self, session_id: str) -> str:
        """Read the transcript belonging to a session."""
        session = self.get_session(session_id)

        if session is None:
            raise FileNotFoundError(f"Session not found: {session_id}")

        session_dir = Path(session["_directory"])
        transcript_name = session.get("transcript_file", "transcript.txt")
        transcript_path = session_dir / transcript_name

        # Prevent metadata from pointing outside its session directory.
        if transcript_path.resolve().parent != session_dir.resolve():
            raise ValueError("Invalid transcript path in session metadata.")

        return transcript_path.read_text(encoding="utf-8")

    def rename_session(self, session_id: str, new_name: str) -> None:
        """Set a user-facing name for a saved session."""
        new_name = new_name.strip()

        if not new_name:
            raise ValueError("Session name cannot be empty.")

        session = self.get_session(session_id)

        if session is None:
            raise FileNotFoundError(f"Session not found: {session_id}")

        session_dir = Path(session["_directory"])
        metadata_path = session_dir / "metadata.json"

        metadata = {
            key: value
            for key, value in session.items()
            if key != "_directory"
        }
        metadata["name"] = new_name

        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def delete_session(self, session_id: str) -> None:
        """Permanently delete one session and its files."""
        session = self.get_session(session_id)

        if session is None:
            raise FileNotFoundError(f"Session not found: {session_id}")

        session_dir = Path(session["_directory"]).resolve()
        output_dir = self.output_dir.resolve()

        # Only delete a direct child of the configured output directory.
        if session_dir.parent != output_dir:
            raise ValueError("Session directory is outside the output folder.")

        shutil.rmtree(session_dir)