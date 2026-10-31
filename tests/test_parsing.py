"""Tests for the yt-dlp output patterns that drive the progress UI."""

import unittest

from ytdlp_gui.parsing import DEST_RE, ITEM_RE, PROG_RE, STATUS_TAGS, TAG_RE


def progress(line):
    m = PROG_RE.search(line)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


class TestProgress(unittest.TestCase):
    def test_full_line(self):
        self.assertEqual(
            progress("[download]  12.3% of ~10.00MiB at 1.20MiB/s ETA 00:07"),
            ("12.3", "1.20MiB/s", "00:07"))

    def test_without_size_tilde(self):
        self.assertEqual(
            progress("[download]  42.0% of 120.5MiB at 3.4MiB/s ETA 00:21"),
            ("42.0", "3.4MiB/s", "00:21"))

    def test_percent_only(self):
        self.assertEqual(progress("[download] 100% of 5MiB"), ("100", None, None))

    def test_completed_line_reports_100(self):
        # "... in 00:01" means finished; percent is still reported so the bar
        # reaches 100 before the process exits.
        self.assertEqual(progress("[download] 100% of 5MiB in 00:01"), ("100", None, None))

    def test_unrelated_line(self):
        self.assertIsNone(progress("[youtube] Extracting URL"))

    def test_percent_is_parsed_from_multi_stream_output(self):
        self.assertEqual(
            progress("[download]  99.9% of 1.00GiB at 10.00MiB/s ETA 00:01")[0], "99.9")


class TestDestination(unittest.TestCase):
    def test_windows_path(self):
        m = DEST_RE.search(r"[download] Destination: C:\out\My File.mp4")
        self.assertEqual(m.group(1), r"C:\out\My File.mp4")

    def test_posix_path(self):
        m = DEST_RE.search("[download] Destination: /home/u/v.mp4")
        self.assertEqual(m.group(1), "/home/u/v.mp4")


class TestItem(unittest.TestCase):
    def test_item_of_total(self):
        m = ITEM_RE.search("[download] Downloading item 3 of 12")
        self.assertEqual((int(m.group(1)), int(m.group(2))), (3, 12))

    def test_video_of_total(self):
        m = ITEM_RE.search("[download] Downloading video 1 of 5")
        self.assertEqual((m.group(1), m.group(2)), ("1", "5"))


class TestTag(unittest.TestCase):
    def test_known_tags(self):
        for line in ("[Merger] Merging formats into \"v.mkv\"",
                     "[ExtractAudio] Destination: a.mp3",
                     "[EmbedThumbnail] Adding thumbnail"):
            m = TAG_RE.match(line)
            self.assertIsNotNone(m)
            self.assertIn(m.group(1), STATUS_TAGS)

    def test_unknown_tag_is_still_parsed(self):
        m = TAG_RE.match("[SomeNewPP] doing things")
        self.assertEqual(m.group(1), "SomeNewPP")
        self.assertNotIn(m.group(1), STATUS_TAGS)


if __name__ == "__main__":
    unittest.main()
