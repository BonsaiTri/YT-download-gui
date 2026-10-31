"""Tests for app-root resolution."""

import os
import unittest

from ytdlp_gui import paths


class TestAppDir(unittest.TestCase):
    def test_source_mode_points_at_project_root(self):
        expected = os.path.dirname(os.path.dirname(os.path.abspath(paths.__file__)))
        self.assertFalse(paths.FROZEN)
        self.assertEqual(paths.APP_DIR, expected)

    def test_config_and_downloads_live_in_app_dir(self):
        self.assertEqual(paths.CONFIG_PATH, os.path.join(paths.APP_DIR, "config.json"))
        self.assertEqual(paths.DEFAULT_OUTDIR, os.path.join(paths.APP_DIR, "downloads"))

    def test_app_dir_exists(self):
        self.assertTrue(os.path.isdir(paths.APP_DIR))


if __name__ == "__main__":
    unittest.main()
