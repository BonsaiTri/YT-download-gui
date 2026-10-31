"""Tests for the --selftest output helper (no engine run required)."""

import io
import unittest
from unittest import mock

from ytdlp_gui import cli


class TestWriteStdout(unittest.TestCase):
    def test_missing_stdout_is_a_no_op(self):
        # Windowed (--noconsole) builds have sys.stdout is None.
        with mock.patch.object(cli.sys, "stdout", None):
            cli._write_stdout("text")  # must not raise

    def test_writes_text(self):
        stream = io.StringIO()
        with mock.patch.object(cli.sys, "stdout", stream):
            cli._write_stdout("hello\n")
        self.assertEqual(stream.getvalue(), "hello\n")

    def test_closed_stream_is_swallowed(self):
        stream = io.StringIO()
        stream.close()
        with mock.patch.object(cli.sys, "stdout", stream):
            cli._write_stdout("text")  # must not raise


if __name__ == "__main__":
    unittest.main()
