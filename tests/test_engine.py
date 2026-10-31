"""Tests for engine discovery and quoting (no downloads performed)."""

import os
import tempfile
import unittest
from unittest import mock

from ytdlp_gui import engine


class TestShellQuote(unittest.TestCase):
    def test_plain_words_are_left_alone(self):
        self.assertEqual(engine._shell_quote("bestvideo*+bestaudio/best"),
                         "bestvideo*+bestaudio/best")

    def test_paths_with_spaces_are_quoted(self):
        self.assertEqual(engine._shell_quote(r"C:\my videos"),
                         r'"C:\my videos"')

    def test_shell_metacharacters_are_quoted(self):
        for token in ("a&b", "a|b", "a>b", "a%b", "a!b", 'a"b'):
            with self.subTest(token=token):
                self.assertTrue(engine._shell_quote(token).startswith('"'))


class TestJsRuntimeArgs(unittest.TestCase):
    def setUp(self):
        engine._JS_RUNTIME_ARGS = None  # bypass the module-level cache

    tearDown = setUp

    def test_detects_node(self):
        with mock.patch.object(engine, "which", lambda n: "/usr/bin/" + n if n == "node" else None):
            self.assertEqual(engine.js_runtime_args(),
                             ["--js-runtimes", "node", "--remote-components", "ejs:github"])

    def test_detects_deno(self):
        with mock.patch.object(engine, "which", lambda n: "/usr/bin/" + n if n == "deno" else None):
            self.assertEqual(engine.js_runtime_args()[1], "deno")

    def test_empty_when_nothing_found(self):
        with mock.patch.object(engine, "which", lambda n: None):
            self.assertEqual(engine.js_runtime_args(), [])


class TestResolve(unittest.TestCase):
    def test_ytdlp_home_wins_over_sibling_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "engine")
            os.makedirs(os.path.join(root, "yt_dlp"))
            open(os.path.join(root, "yt_dlp", "__init__.py"), "w").close()
            open(os.path.join(root, "yt_dlp", "__main__.py"), "w").close()
            with mock.patch.dict(os.environ, {"YTDLP_HOME": root}):
                prefix, engine_root, label = engine.resolve_yt_dlp()
            self.assertEqual(engine_root, os.path.abspath(root))
            self.assertEqual(label, "checkout: " + os.path.abspath(root))
            self.assertEqual(prefix[-2:], ["-m", "yt_dlp"])

    def test_old_checkout_falls_back_to_script_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "old")
            os.makedirs(os.path.join(root, "yt_dlp"))
            open(os.path.join(root, "yt_dlp", "__init__.py"), "w").close()
            open(os.path.join(root, "yt_dlp.py"), "w").close()
            with mock.patch.dict(os.environ, {"YTDLP_HOME": root}):
                prefix, engine_root, _label = engine.resolve_yt_dlp()
            self.assertEqual(engine_root, os.path.abspath(root))
            self.assertTrue(prefix[-1].endswith("yt_dlp.py"))

    def test_nonexistent_ytdlp_home_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"YTDLP_HOME": os.path.join(tmp, "nope")}):
                prefix, engine_root, label = engine.resolve_yt_dlp()
            # Falls through to the sibling checkout used by this repo.
            self.assertNotEqual(engine_root, os.path.join(tmp, "nope"))
            if prefix is not None:
                self.assertNotIn("nope", engine_root)

    def test_missing_engine_returns_none_tuple(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(engine, "_candidate_repo_roots", lambda: []), \
             mock.patch.object(engine, "which", lambda n: None):
            prefix, engine_root, label = engine.resolve_yt_dlp()
        self.assertIsNone(prefix)
        self.assertIsNone(engine_root)
        self.assertIsNone(label)


if __name__ == "__main__":
    unittest.main()
