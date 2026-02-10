"""Project-local type aliases for yt-dlp data structures.

yt-dlp has no type stubs, so all info dictionaries and progress hook
payloads come back as bare ``dict``.  These aliases give basedpyright
enough information to stop reporting ``dict[Unknown, Unknown]`` while
remaining accurate about what yt-dlp actually returns.
"""

from __future__ import annotations

from typing import Any

# yt-dlp info_dict: keys are always strings, values vary (str, int, list, nested dict, etc.)
YtdlpInfo = dict[str, Any]

# yt-dlp progress hook payload (download status, speed, ETA, etc.)
ProgressDict = dict[str, Any]
