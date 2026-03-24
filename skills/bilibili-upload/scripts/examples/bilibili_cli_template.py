from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conf import BASE_DIR
from utils.constant import VideoZoneTypes


def main() -> None:
    account = "account_a"
    # account_name is user-defined. One account_name maps to one account file.
    # You can prepare multiple account names and run them in parallel.
    cli_path = Path(BASE_DIR) / "sau_cli.py"
    command = [
        sys.executable,
        str(cli_path),
        "bilibili",
        "upload-video",
        "--account",
        account,
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
