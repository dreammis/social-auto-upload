from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conf import BASE_DIR


if __name__ == "__main__":
    # 建议直接在本地真实终端里运行这个脚本。
    # 如果终端里的二维码显示不完整，可以打开当前目录下的 qrcode.png 扫码。
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
