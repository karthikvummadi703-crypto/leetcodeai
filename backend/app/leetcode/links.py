"""Helpers for parsing a LeetCode profile link or bare username.

Users can connect their account by pasting the full public profile URL
(``https://leetcode.com/u/username`` or ``https://leetcode.com/username``)
or just the username itself.
"""

from __future__ import annotations

import re

_URL_PATTERN = re.compile(r"leetcode\.com/(?:u/)?([^/?#]+)", re.IGNORECASE)


def extract_leetcode_username(input_str: str) -> str:
    """Extract the username from a raw username or a full profile URL."""
    s = input_str.strip().rstrip("/")
    match = _URL_PATTERN.search(s)
    if match:
        return match.group(1).strip()
    return s
