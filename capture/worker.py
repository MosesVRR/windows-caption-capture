"""Background worker for capturing Windows Live Captions."""
import re
import threading
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from pywinauto import Desktop

from capture.session import CaptureSession

POLL_INTERVAL = 0.5


def get_caption_text(window) -> str:
    """Read the current caption text through Windows UI Automation."""
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


def normalize_caption_text(text: str) -> str:
    """Normalize caption text, treating UI line breaks as visual wrapping."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def format_transcript(text: str) -> str:
    """Add readable sentence and paragraph breaks to normalized caption text.

    Windows Live Captions exposes a changing text block rather than reliable
    paragraph metadata. Visual line breaks are therefore discarded, and
    sentence-ending punctuation is used as a conservative formatting cue.
    A blank line is inserted after every three detected sentences.
    """
    text = normalize_caption_text(text)
    if not text:
        return ""

    # Put a line break after sentence-ending punctuation when followed by a
    # likely sentence start. Avoid splitting common abbreviations and decimals
    # where possible by requiring whitespace and an uppercase/digit/opening
    # quote character after the punctuation.
    sentence_boundary = re.compile(r'([.!?…]+[”’"\']?)(\s+)(?=[A-ZÀ-ÖØ-Þ0-9“"\'])')
    pieces = sentence_boundary.split(text)
    sentences = []
    current = ""
    i = 0
    while i < len(pieces):
        current += pieces[i]
        if i + 2 < len(pieces) and pieces[i + 1] and pieces[i + 1].isspace():
            sentences.append(current.strip())
            current = ""
            i += 2
        else:
            i += 1
    if current.strip():
        sentences.append(current.strip())

    if not sentences:
        return text

    paragraphs = []
    for start in range(0, len(sentences), 3):
        paragraphs.append(" ".join(sentences[start:start + 3]))
    return "\n\n".join(paragraphs)


def text_after_baseline(baseline: str, current: str) -> str:
    """Return the session portion of a cumulative caption control."""
    if not current:
        return ""
    if not baseline:
        return current
    if current.startswith(baseline):
        return current[len(baseline):].lstrip()

    # If the caption UI trimmed or reset its history, do not attempt to append
    # a character-level delta. Use the current control text as the new view.
    # This avoids the word-fragment corruption caused by appending suffixes
    # from text that has been revised by Live Captions.
    return current


class CaptureWorker(QThread):
    """Capture caption snapshots without blocking the GUI thread."""

    recording_started = Signal(str, str)
    capture_error = Signal(str)
    status_update = Signal(str)
    transcript_update = Signal(str)
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

            # Capture the existing UI text as a baseline. It should not be
            # copied into the new session's transcript.
            baseline = normalize_caption_text(get_caption_text(window))
            previous_raw = get_caption_text(window)
            session_transcript = ""

            with (
                session.transcript_file.open("w", encoding="utf-8") as transcript,
                session.snapshots_file.open("w", encoding="utf-8") as snapshots,
            ):
                self.transcript_update.emit("")

                while not self._stop_event.is_set():
                    try:
                        current_raw = get_caption_text(window)
                        current = normalize_caption_text(current_raw)

                        if current_raw != previous_raw:
                            timestamp = datetime.now().astimezone().isoformat(
                                timespec="seconds"
                            )
                            snapshots.write(f"[{timestamp}]\n{current_raw}\n\n")
                            snapshots.flush()

                            # Rebuild from the current full UI text each poll.
                            # Do not append character suffixes: Live Captions
                            # can revise its latest words, which otherwise
                            # creates fragments such as "for estier".
                            latest_session_text = text_after_baseline(
                                baseline, current
                            )
                            formatted_session_text = format_transcript(
                                latest_session_text
                            )

                            if formatted_session_text != session_transcript:
                                session_transcript = formatted_session_text
                                transcript.seek(0)
                                transcript.write(session_transcript)
                                transcript.truncate()
                                transcript.flush()
                                self.transcript_update.emit(session_transcript)

                            previous_raw = current_raw

                    except Exception as exc:
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
