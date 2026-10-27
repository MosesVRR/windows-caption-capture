"""Capture text exposed by the Windows Live Captions interface."""

import time
from datetime import datetime
from pathlib import Path

from pywinauto import Desktop


POLL_INTERVAL = 0.5
OUTPUT_DIR = Path("transcripts")


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
    """Capture captions into a new transcript session."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    window = find_captions_window()

    if window is None:
        print("Windows Live Captions was not found.")
        print("Open Live Captions and run this script again.")
        return

    session_id = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S_%f")
    transcript_file = OUTPUT_DIR / f"{session_id}_transcript.txt"
    snapshots_file = OUTPUT_DIR / f"{session_id}_snapshots.txt"

    # Use the currently visible text as a baseline to avoid copying
    # existing caption history into the new transcript.
    previous_text = get_caption_text(window)

    print("=" * 60)
    print("WINDOWS LIVE CAPTIONS SAVER")
    print("=" * 60)
    print(f"Transcript: {transcript_file.resolve()}")
    print(f"Snapshots:  {snapshots_file.resolve()}")
    print("Existing visible captions will be used as the starting baseline.")
    print("Capturing new caption changes. Press Ctrl+C to stop.\n")

    try:
        with (
            transcript_file.open("w", encoding="utf-8") as transcript,
            snapshots_file.open("w", encoding="utf-8") as snapshots,
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

                        # Save the latest complete caption snapshot.
                        # Overwriting prevents older text from being
                        # appended repeatedly.
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
        print(f"Transcript saved to: {transcript_file.resolve()}")
        print(f"Snapshots saved to: {snapshots_file.resolve()}")


if __name__ == "__main__":
    main()
