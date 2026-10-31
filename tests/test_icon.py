"""Tests for icon lookup (never requires Tkinter to succeed)."""

import os
import unittest

from ytdlp_gui import icon


class TestFindIcon(unittest.TestCase):
    def test_finds_the_generated_icons(self):
        # build/make_icon.py is committed, so both files exist in the repo.
        self.assertIsNotNone(icon.find_icon(("icon.ico",)))
        self.assertIsNotNone(icon.find_icon(("icon.png",)))

    def test_returns_absolute_existing_path(self):
        path = icon.find_icon(("icon.png",))
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(os.path.isfile(path))

    def test_missing_icon_returns_none(self):
        self.assertIsNone(icon.find_icon(("definitely-not-here.png",)))


if __name__ == "__main__":
    unittest.main()
