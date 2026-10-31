"""Allow ``python -m ytdlp_gui``."""

import sys

from .cli import main, selftest

if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else main())
