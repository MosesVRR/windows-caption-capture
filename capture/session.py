"""Manage transcript capture sessions and their metadata."""

import json
import time
from datetime import datetime
from pathlib import Path


class CaptureSession:
    """Represent a single Windows Live Captions capture session."""

    def __init__(self, output_dir: str | Path = "transcripts") -> None:
        self.output_dir = Path(output_dir)
        self.session_id = datetime.now().astimezone().strftime(
            "%Y-%m-%d_%H-%M-%S_%f"
        )

        self.session_dir = self.output_dir / f"session_{self.session_id}"
        self.transcript_file = self.session_dir / "transcript.txt"
        self.snapshots_file = self.session_dir / "snapshots.txt"
        self.metadata_file = self.session_dir / "metadata.json"

        self.started_at = datetime.now().astimezone()
        self.ended_at: datetime | None = None
        self.status = "recording"

        self.session_dir.mkdir(parents=True, exist_ok=False)
        self.transcript_file.touch()
        self.snapshots_file.touch()

        self._save_metadata()

    def _save_metadata(self) -> None:
        """Write the current session metadata to disk."""
        metadata = {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "ended_at": (
                self.ended_at.isoformat(timespec="seconds")
                if self.ended_at
                else None
            ),
            "duration_seconds": (
                round((self.ended_at - self.started_at).total_seconds(), 2)
                if self.ended_at
                else None
            ),
            "status": self.status,
            "language": None,
            "transcript_file": "transcript.txt",
            "snapshots_file": "snapshots.txt",
        }

        self.metadata_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def finish(self, status: str = "completed") -> None:
        """Mark the session as finished and update its metadata."""
        if self.ended_at is not None:
            return

        self.ended_at = datetime.now().astimezone()
        self.status = status
        self._save_metadata()