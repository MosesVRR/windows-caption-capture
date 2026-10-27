import time
from datetime import datetime
from pathlib import Path

from pywinauto import Desktop


# Configuration
POLL_INTERVAL = 0.5
OUTPUT_DIR = Path("transcripts")
TRANSCRIPT_FILE = OUTPUT_DIR / "transcript.txt"
SNAPSHOT_FILE = OUTPUT_DIR / "snapshots.txt"


def get_caption_text(window):
    """Read the current caption text through Windows UI Automation."""

    for element in window.descendants():
        try:
            if element.element_info.automation_id == "CaptionsTextBlock":
                return element.element_info.name or ""
        except Exception:
            continue

    return ""


def find_new_text(previous, current):
    """
    Identify text added to the end of a changing caption snapshot.

    Handles both cumulative captions and snapshots where older text
    has scrolled out of view.
    """

    if not current:
        return ""

    if not previous:
        return current

    if current == previous:
        return ""

    # The current snapshot extends the previous snapshot.
    if current.startswith(previous):
        return current[len(previous):]

    # Search for the longest overlap between the end of the previous
    # snapshot and the beginning of the current snapshot.
    max_overlap = min(len(previous), len(current))

    for size in range(max_overlap, 0, -1):
        if previous[-size:] == current[:size]:
            return current[size:]

    # No overlap was found. Preserve the new snapshot rather than
    # silently losing potentially important text.
    return "\n" + current


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    desktop = Desktop(backend="uia")
    window = desktop.window(
        title="Live Captions",
        class_name="LiveCaptionsDesktopWindow",
    )

    if not window.exists():
        print("Live Captions was not found.")
        print("Open Live Captions and run this script again.")
        return

    previous_text = ""

    print("=" * 60)
    print("WINDOWS LIVE CAPTIONS SAVER")
    print("=" * 60)
    print(f"Transcript: {TRANSCRIPT_FILE.resolve()}")
    print(f"Snapshots:  {SNAPSHOT_FILE.resolve()}")
    print("\nCapturing captions. Press Ctrl+C to stop.\n")

    try:
        with (
            TRANSCRIPT_FILE.open("w", encoding="utf-8") as transcript,
            SNAPSHOT_FILE.open("w", encoding="utf-8") as snapshots,
        ):
            while True:
                try:
                    current_text = get_caption_text(window)

                    if current_text and current_text != previous_text:
                        timestamp = datetime.now().astimezone().isoformat(
                            timespec="seconds"
                        )

                        # Preserve each distinct snapshot for debugging
                        # and possible future transcript reconstruction.
                        snapshots.write(
                            f"\n[{timestamp}]\n{current_text}\n"
                        )
                        snapshots.flush()

                        new_text = find_new_text(
                            previous_text,
                            current_text,
                        )

                        if new_text:
                            transcript.write(new_text)
                            transcript.flush()

                            print(new_text, end="", flush=True)

                        previous_text = current_text

                except Exception as exc:
                    print(f"\nTemporary capture error: {exc}")

                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nCapture stopped.")
        print(f"Transcript saved to: {TRANSCRIPT_FILE.resolve()}")
        print(f"Snapshots saved to: {SNAPSHOT_FILE.resolve()}")


if __name__ == "__main__":
    main()