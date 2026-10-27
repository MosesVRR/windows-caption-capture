"""Background worker for capturing Windows Live Captions."""
import threading
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from pywinauto import Desktop

from capture.session import CaptureSession


POLL_INTERVAL = 0.5


def get_caption_text(window) -> str:
    """Read the current caption text from Windows UI Automation."""
    for element in window.descendants():
        try:
            if element.element_info.automation_id == "CaptionsTextBlock":
                return element.element_info.name or ""
        except Exception:
            continue
    return ""


def find_captions_window():
    """Return the Live Captions window if it can be found."""
    desktop = Desktop(backend="uia")
    window = desktop.window(
        title="Live Captions",
        class_name="LiveCaptionsDesktopWindow",
    )
    if not window.exists():
        return None
    return window


class CaptureWorker(QThread):
    """Capture caption snapshots without blocking the GUI thread."""

    recording_started = Signal(str, str)
    capture_error = Signal(str)
    status_update = Signal(str)
    recording_finished = Signal(str, str)

    def __init__(self, output_dir: str = "transcripts") -> None:
        super().__init__()
        self.output_dir = output_dir
        self._stop_event = threading.Event()
        self._session_id = ""

    def stop(self) -> None:
        """Request a graceful stop."""
        self._stop_event.set()

    def run(self) -> None:
        """Run capture until a stop request is received."""
        session = None
        status = "completed"

        try:
            window = find_captions_window()
            if window is None:
                self.capture_error.emit(
                    "Windows Live Captions was not found. Open Live Captions "
                    "and try starting the recording again."
                )
                self.recording_finished.emit("", "failed")
                return

            session = CaptureSession(output_dir=self.output_dir)
            self._session_id = session.session_id
            self.recording_started.emit(
                session.session_id, str(session.session_dir.resolve())
            )

            previous_text = get_caption_text(window)

            with (
                session.transcript_file.open("w", encoding="utf-8") as transcript,
                session.snapshots_file.open("w", encoding="utf-8") as snapshots,
            ):
                while not self._stop_event.is_set():
                    try:
                        current_text = get_caption_text(window)

                        if current_text and current_text != previous_text:
                            timestamp = datetime.now().astimezone().isoformat(
                                timespec="seconds"
                            )

                            snapshots.write(
                                f"[{timestamp}]\n{current_text}\n\n"
                            )
                            snapshots.flush()

                            # Windows exposes accumulated caption history.
                            # Replace the transcript with the latest snapshot.
                            transcript.seek(0)
                            transcript.write(current_text)
                            transcript.truncate()
                            transcript.flush()

                            previous_text = current_text

                    except Exception as exc:
                        # Transient UI Automation errors should not stop capture.
                        self.status_update.emit(
                            f"Temporary caption capture error: {exc}"
                        )

                    self._stop_event.wait(POLL_INTERVAL)

        except Exception as exc:
            status = "failed"
            self.capture_error.emit(f"Caption capture failed: {exc}")

        finally:
            if session is not None:
                try:
                    session.finish(status=status)
                except Exception as exc:
                    status = "failed"
                    self.capture_error.emit(
                        f"Could not finalize recording metadata: {exc}"
                    )
                self.recording_finished.emit(session.session_id, status)
