from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conf import BASE_DIR


if __name__ == "__main__":
    cli_path = Path(BASE_DIR) / "sau_cli.py"
    subprocess.run(
        [
            sys.executable,
            str(cli_path),
            "bilibili",
            "login",
            "--account",
            "creator",
        ],
        check=True,
    )
