"""Utility functions for CLI."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from conf import BASE_DIR

SCHEDULE_FORMAT = '%Y-%m-%d %H:%M'


def resolve_runtime_home() -> Path:
    """Return the runtime home directory."""
    return Path(BASE_DIR)


def resolve_account_file(platform: str, account_name: str) -> Path:
    """Return the path to the account cookie file.

    *account_name* may be a short label (e.g. ``"66"``) or an absolute path
    to an existing cookie JSON file (e.g.
    ``/…/cookies/xiaohongshu_66.json``).  When an absolute path ending with
    ``.json`` is provided it is returned as-is.
    """
    candidate = Path(account_name)
    if candidate.is_absolute() and candidate.suffix == '.json':
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate
    account_file = resolve_runtime_home() / 'cookies' / f'{platform}_{account_name}.json'
    account_file.parent.mkdir(exist_ok=True)
    return account_file


def parse_tags(raw_tags: str | None) -> list[str]:
    """Parse comma-separated tags string into a list."""
    if not raw_tags:
        return []
    tags: list[str] = []
    for item in raw_tags.split(','):
        cleaned = item.strip().lstrip('#')
        if cleaned:
            tags.append(cleaned)
    return tags


def parse_image_files(raw_files: Iterable[Path]) -> list[Path]:
    """Convert image file paths to Path objects."""
    return [Path(file) for file in raw_files]


def parse_schedule(raw_schedule: str | None) -> datetime | int:
    """Parse schedule string into datetime object."""
    if not raw_schedule:
        return 0
    return datetime.strptime(raw_schedule, SCHEDULE_FORMAT)
