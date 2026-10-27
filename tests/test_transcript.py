"""Unit tests for caption transcript reconstruction."""

import unittest

from capture.transcript import find_new_text


class TestFindNewText(unittest.TestCase):
    """Tests for extracting new text from caption snapshots."""

    def test_empty_current_snapshot(self):
        result = find_new_text("Hello", "")
        self.assertEqual(result, "")

    def test_first_snapshot(self):
        result = find_new_text("", "Hello")
        self.assertEqual(result, "Hello")

    def test_identical_snapshots(self):
        result = find_new_text("Hello world", "Hello world")
        self.assertEqual(result, "")

    def test_snapshot_extends_previous_text(self):
        result = find_new_text("Hello", "Hello world")
        self.assertEqual(result, " world")

    def test_overlapping_snapshots(self):
        result = find_new_text("Hello world", "world again")
        self.assertEqual(result, " again")

    def test_longest_overlap_is_used(self):
        result = find_new_text("abcXYZ", "XYZdef")
        self.assertEqual(result, "def")

    def test_current_snapshot_is_contained_in_previous(self):
        result = find_new_text("Hello wonderful world", "wonderful")
        self.assertEqual(result, "")

    def test_non_overlapping_snapshots(self):
        result = find_new_text("Hello there", "Good morning")
        self.assertEqual(result, "\nGood morning")

    def test_empty_snapshots(self):
        result = find_new_text("", "")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()