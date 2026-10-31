"""Tests for the pure settings -> CLI argument logic (no GUI needed)."""

import unittest

from ytdlp_gui.settings import DEFAULTS, build_args


class Base(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(DEFAULTS)

    def args(self, **overrides):
        self.cfg.update(overrides)
        return build_args(self.cfg, ["https://example.com/v"])


class TestQuality(Base):
    def test_default_is_best_and_keeps_playlist_off(self):
        a = self.args()
        self.assertEqual(a[0], "-f")
        self.assertEqual(a[1], "bestvideo*+bestaudio/best")
        self.assertIn("--no-playlist", a)
        self.assertEqual(a[-1], "https://example.com/v")

    def test_resolution_cap_is_applied_to_both_selectors(self):
        a = self.args(quality="1080p")
        self.assertEqual(a[1], "bestvideo[height<=1080]+bestaudio/best[height<=1080]")

    def test_audio_only_uses_extract_audio(self):
        a = self.args(quality="Audio only (MP3)")
        self.assertIn("--extract-audio", a)
        self.assertIn("--audio-format", a)
        self.assertIn("mp3", a)
        self.assertNotIn("-f", a)

    def test_audio_m4a_threads_codec(self):
        a = self.args(quality="Audio only (M4A)")
        self.assertIn("m4a", a)


class TestOutput(Base):
    def test_container_and_template(self):
        a = self.args(merge_format="mp4", template="%(title)s.%(ext)s")
        self.assertIn("--merge-output-format", a)
        self.assertIn("mp4", a)
        self.assertIn("-o", a)
        self.assertIn("%(title)s.%(ext)s", a)

    def test_outdir_uses_paths_flag_not_output_dir(self):
        # yt-dlp 2025.12+ removed --output-dir in favour of --paths
        a = self.args(outdir="/tmp/videos")
        self.assertIn("--paths", a)
        self.assertNotIn("--output-dir", a)
        self.assertIn("home:/tmp/videos", a)

    def test_embed_toggles(self):
        a = self.args(embed_metadata=True, embed_thumbnail=True, embed_chapters=True)
        for flag in ("--embed-metadata", "--embed-thumbnail", "--embed-chapters"):
            self.assertIn(flag, a)

    def test_restrict_filenames(self):
        self.assertIn("--restrict-filenames", self.args(restrict_filenames=True))

    def test_archive_only_when_enabled(self):
        self.assertNotIn("--download-archive", self.args())
        a = self.args(skip_archived=True, archive="/tmp/a.txt")
        self.assertIn("--download-archive", a)
        self.assertIn("/tmp/a.txt", a)


class TestPlaylist(Base):
    def test_playlist_modes(self):
        self.assertIn("--no-playlist", self.args(playlist_mode="Single video only"))
        self.assertIn("--yes-playlist", self.args(playlist_mode="Full playlist"))
        a = self.args(playlist_mode="Custom range (1-10, 13, 20-25)",
                      playlist_items="1-3, 7")
        self.assertIn("--playlist-items", a)
        self.assertIn("1-3, 7", a)


class TestSubtitles(Base):
    def test_subs_flags(self):
        a = self.args(write_subs=True, sub_langs="en,de", sub_format="srt")
        self.assertIn("--write-subs", a)
        self.assertIn("--sub-langs", a)
        self.assertIn("en,de", a)
        self.assertIn("--sub-format", a)

    def test_auto_subs_and_embed(self):
        a = self.args(write_auto_subs=True, embed_subs=True)
        self.assertIn("--write-auto-subs", a)
        self.assertIn("--embed-subs", a)


class TestAdvanced(Base):
    def test_network_flags(self):
        a = self.args(proxy="http://127.0.0.1:8080", rate_limit="2M",
                      concurrent_fragments="8", retries="5",
                      fragment_retries="3", sleep_interval="1.5")
        self.assertEqual(a[a.index("--proxy") + 1], "http://127.0.0.1:8080")
        self.assertEqual(a[a.index("--limit-rate") + 1], "2M")
        self.assertEqual(a[a.index("--concurrent-fragments") + 1], "8")
        self.assertEqual(a[a.index("--retries") + 1], "5")
        self.assertEqual(a[a.index("--fragment-retries") + 1], "3")
        self.assertEqual(a[a.index("--sleep-requests") + 1], "1.5")

    def test_clip_section(self):
        a = self.args(start_time="1:30", end_time="2:00")
        joined = " ".join(a)
        self.assertIn("--download-sections", joined)
        self.assertIn("1:30-2:00", joined)

    def test_sponsorblock_modes(self):
        self.assertIn("--sponsorblock-mark", self.args(sponsor_action="Mark chapters"))
        self.assertIn("--sponsorblock-remove", self.args(sponsor_action="Remove segments"))

    def test_cookies_file_beats_browser(self):
        # Only one source is ever passed: both would make yt-dlp try the
        # browser too and emit DPAPI decryption errors on Windows.
        a = self.args(cookies="/tmp/c.txt", cookies_from_browser="chrome")
        self.assertIn("--cookies", a)
        self.assertNotIn("--cookies-from-browser", a)

    def test_cookies_from_browser_used_when_no_file(self):
        a = self.args(cookies_from_browser="firefox")
        self.assertIn("--cookies-from-browser", a)
        self.assertIn("firefox", a)
        self.assertNotIn("--cookies", a)

    def test_comments_of_extra_args_are_split(self):
        a = self.args(extra_args="--no-part --windows-filenames")
        self.assertIn("--no-part", a)
        self.assertIn("--windows-filenames", a)


class TestValidation(Base):
    def test_bad_int_is_rejected(self):
        for key, value in (("concurrent_fragments", "9999"),
                           ("concurrent_fragments", "abc"),
                           ("retries", "-1")):
            with self.subTest(key=key, value=value):
                self.cfg.update(DEFAULTS)
                with self.assertRaises(ValueError):
                    self.args(**{key: value})

    def test_bad_time_is_rejected(self):
        for value in ("abc", "1:2:3:4", "::"):
            with self.subTest(value=value):
                self.cfg.update(DEFAULTS)
                with self.assertRaises(ValueError):
                    self.args(start_time=value)

    def test_unbalanced_quotes_in_extra_args_rejected(self):
        with self.assertRaises(ValueError):
            self.args(extra_args="--x 'unclosed")

    def test_newline_flag_present_once(self):
        self.assertEqual(self.args().count("--newline"), 1)


if __name__ == "__main__":
    unittest.main()
