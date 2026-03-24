from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conf import BASE_DIR
from utils.constant import VideoZoneTypes


def main() -> None:
    cli_path = Path(BASE_DIR) / "sau_cli.py"
    command = [
        sys.executable,
        str(cli_path),
        "bilibili",
        "upload-video",
        "--account",
        "creator",
        "--file",
        str(Path(BASE_DIR) / "videos" / "demo.mp4"),
        "--title",
        "Bilibili CLI Demo",
        "--desc",
        "Bilibili CLI Demo",
        "--tid",
        str(VideoZoneTypes.SPORTS_FOOTBALL.value),
        "--tags",
        "足球,测试",
        "--schedule",
        "2026-03-26 16:00",
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
