"""Utilities for reconstructing text from Windows Live Captions snapshots."""


def find_new_text(previous: str, current: str) -> str:
    """Extract text that appears new in the current caption snapshot.

    Handles:
    - Empty snapshots.
    - Identical snapshots.
    - Snapshots that extend previous text.
    - Overlapping snapshots.
    - Snapshots containing only text already seen.

    Returns:
        The apparently new text, or an empty string if no new text
        can be identified.

    Note:
        This is a heuristic. If Windows revises earlier captions or
        presents entirely different text without overlap, it cannot
        reliably determine which words are genuinely new.
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

    # The current snapshot contains only text we've already seen.
    if current in previous:
        return ""

    # Find the longest exact overlap between the end of the previous
    # snapshot and the beginning of the current snapshot.
    max_overlap = min(len(previous), len(current))

    for overlap_length in range(max_overlap, 0, -1):
        previous_suffix = previous[-overlap_length:]
        current_prefix = current[:overlap_length]

        if previous_suffix == current_prefix:
            return current[overlap_length:]

    # No overlap was found. Preserve the new snapshot rather than
    # silently discarding potentially useful text.
    #
    # The caller should treat this as a possible discontinuity.
    return "\n" + current