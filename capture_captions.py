"""Capture Windows Live Captions into organized recording sessions."""

import time
from datetime import datetime

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


def main() -> None:
    """Capture captions and save them as a managed session."""
    window = find_captions_window()

    if window is None:
        print("Windows Live Captions was not found.")
        print("Open Live Captions and run this script again.")
        return

    session = CaptureSession()

    # Establish the initial baseline to avoid writing existing caption
    # history until the next caption change.
    previous_text = get_caption_text(window)

    print("=" * 60)
    print("WINDOWS LIVE CAPTIONS SAVER")
    print("=" * 60)
    print(f"Session ID: {session.session_id}")
    print(f"Session folder: {session.session_dir.resolve()}")
    print(f"Transcript: {session.transcript_file.resolve()}")
    print(f"Snapshots: {session.snapshots_file.resolve()}")
    print(f"Metadata: {session.metadata_file.resolve()}")
    print("Capturing new caption changes. Press Ctrl+C to stop.\n")

    try:
        with (
            session.transcript_file.open("w", encoding="utf-8") as transcript,
            session.snapshots_file.open("w", encoding="utf-8") as snapshots,
        ):
            while True:
                try:
                    current_text = get_caption_text(window)

                    if current_text and current_text != previous_text:
                        timestamp = datetime.now().astimezone().isoformat(
                            timespec="seconds"
                        )

                        # Keep a history of snapshots for diagnostics.
                        snapshots.write(
                            f"[{timestamp}]\n{current_text}\n\n"
                        )
                        snapshots.flush()

                        # Windows exposes the accumulated caption history.
                        # Replace the transcript with the latest complete
                        # snapshot to avoid duplicating earlier captions.
                        transcript.seek(0)
                        transcript.write(current_text)
                        transcript.truncate()
                        transcript.flush()

                        previous_text = current_text

                        print(
                            f"\rCaptured {len(current_text)} characters...",
                            end="",
                            flush=True,
                        )

                except Exception as exc:
                    print(f"\nTemporary capture error: {exc}")

                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nCapture stopped.")

    finally:
        session.finish(status="completed")
        print(f"Transcript saved to: {session.transcript_file.resolve()}")
        print(f"Snapshots saved to: {session.snapshots_file.resolve()}")
        print(f"Metadata saved to: {session.metadata_file.resolve()}")


if __name__ == "__main__":
    main()