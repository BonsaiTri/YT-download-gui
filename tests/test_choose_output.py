"""Tests for build/choose_output.py - the build output folder menu.

The module is loaded by path because ``build/`` is not a package: the builders
call it as a script (``python build/choose_output.py``).
"""

import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "build", "choose_output.py")


def _load():
    spec = importlib.util.spec_from_file_location("ytdlp_gui_build_choose_output", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeTTY(io.StringIO):
    """Looks like a terminal to choose_output, so it prompts."""

    def isatty(self):
        return True


class ChooseOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.co = _load()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ytdlp-gui-pick-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._env = dict(os.environ)
        self.addCleanup(self._restore_env)
        for key in ("YTDLP_GUI_BUILD_OUT", "YTDLP_GUI_BUILD_DEFAULT", "YTDLP_GUI_BUILD_ROOT"):
            os.environ.pop(key, None)

    def _restore_env(self):
        os.environ.clear()
        os.environ.update(self._env)

    def _run(self, lines, stdin_tty=True):
        stdin = _FakeTTY("\n".join(lines) + "\n")
        if not stdin_tty:
            stdin = io.StringIO("")  # isatty() -> False
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = stdin
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = self.co.main(["choose_output.py"])
        finally:
            sys.stdin = old_stdin
        self.last_err = err.getvalue()
        return code, out.getvalue().strip()

    # -- prepare() ---------------------------------------------------------
    def test_prepare_creates_the_folder(self):
        target = os.path.join(self.tmp, "a", "b")
        self.assertEqual(self.co.prepare(target), os.path.normpath(target))
        self.assertTrue(os.path.isdir(target))

    def test_prepare_rejects_a_file(self):
        path = os.path.join(self.tmp, "afile")
        with open(path, "w") as handle:
            handle.write("x")
        with self.assertRaises(self.co.OutputError):
            self.co.prepare(path)

    def test_prepare_accepts_quoted_and_trailing_space_paths(self):
        target = os.path.join(self.tmp, "quoted")
        self.assertTrue(os.path.isdir(self.co.prepare('  "%s"  ' % target)))

    def test_prepare_refuses_the_repo_root(self):
        os.environ["YTDLP_GUI_BUILD_ROOT"] = self.tmp
        with self.assertRaises(self.co.OutputError):
            self.co.prepare(self.tmp)
        # a subfolder is fine
        self.co.prepare(os.path.join(self.tmp, "dist"))

    # -- prompt ------------------------------------------------------------
    def test_default_is_used_when_the_answer_is_empty(self):
        default = os.path.join(self.tmp, "dist")
        os.environ["YTDLP_GUI_BUILD_DEFAULT"] = default
        code, out = self._run([""])
        self.assertEqual((code, out), (0, default))

    def test_choice_one_means_the_default(self):
        default = os.path.join(self.tmp, "dist")
        os.environ["YTDLP_GUI_BUILD_DEFAULT"] = default
        self.assertEqual(self._run(["1"]), (0, default))

    def test_pasted_path_is_accepted(self):
        pasted = os.path.join(self.tmp, "somewhere", "else")
        self.assertEqual(self._run([pasted]), (0, pasted))
        self.assertTrue(os.path.isdir(pasted))

    def test_cancel_exits_nonzero_and_prints_nothing(self):
        self.assertEqual(self._run(["4"]), (1, ""))

    def test_type_option_asks_for_the_path(self):
        typed = os.path.join(self.tmp, "typed")
        self.assertEqual(self._run(["3", typed]), (0, typed))

    def test_garbage_answer_reprompts(self):
        target = os.path.join(self.tmp, "after-garbage")
        self.assertEqual(self._run(["nonsense", target]), (0, target))

    def test_unusable_location_reprompts(self):
        good = os.path.join(self.tmp, "good")
        blocker = os.path.join(self.tmp, "blocker")
        with open(blocker, "w") as handle:
            handle.write("x")
        self.assertEqual(self._run([blocker, good]), (0, good))

    def test_non_interactive_uses_the_env_override(self):
        os.environ["YTDLP_GUI_BUILD_OUT"] = os.path.join(self.tmp, "ci-out")
        os.environ["YTDLP_GUI_BUILD_DEFAULT"] = os.path.join(self.tmp, "ignored")
        self.assertEqual(self._run([], stdin_tty=False), (0, os.path.join(self.tmp, "ci-out")))

    def test_non_interactive_uses_the_default_and_never_prompts(self):
        default = os.path.join(self.tmp, "dist")
        os.environ["YTDLP_GUI_BUILD_DEFAULT"] = default
        self.assertEqual(self._run([], stdin_tty=False), (0, default))

    def test_the_menu_is_printed_on_stderr_not_stdout(self):
        os.environ["YTDLP_GUI_BUILD_DEFAULT"] = os.path.join(self.tmp, "dist")
        code, out = self._run(["4"])
        self.assertEqual((code, out), (1, ""))
        self.assertIn("where should the finished build be written?", self.last_err)
        self.assertIn("[2] Browse for a folder...", self.last_err)

    def test_stdout_carries_only_the_path(self):
        default = os.path.join(self.tmp, "dist")
        os.environ["YTDLP_GUI_BUILD_DEFAULT"] = default
        code, out = self._run([""])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
