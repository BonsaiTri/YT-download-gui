"""Patterns for turning raw yt-dlp output into progress and status text."""

import re


# App
# ---------------------------------------------------------------------------

PROG_RE = re.compile(
    r"(\d{1,3}(?:\.\d+)?)%\s+of\s+~?\s*[\d.]+[A-Za-z]+"
    r"(?:\s+at\s+([\d.]+\s*[A-Za-z]+/s))?"
    r"(?:\s+ETA\s+(\S+))?",
    re.I,
)
DEST_RE = re.compile(r"Destination:\s*(.+?)\s*$")
TAG_RE = re.compile(r"^\[([A-Za-z][A-Za-z0-9_]*)\]\s+(.*)$")
ITEM_RE = re.compile(r"Downloading (?:item|video) (\d+) of (\d+)", re.I)
STATUS_TAGS = {
    "Merger", "ExtractAudio", "FFmpegMetadata", "EmbedThumbnail", "FixupM3u8",
    "EmbedSrt", "WriteSrt", "WriteSubs", "WriteAutomaticSubs", "MoveFiles",
    "Postprocessor", "VideoConversion", "Remux", "EmbedChapters", "SponsorBlock",
}
