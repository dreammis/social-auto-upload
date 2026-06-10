"""淘宝光合 Uploader 模块

该包被以下入口使用：
- 旧版后端 myUtils/login.py + sau_backend.py（type=5 平台，cookiesFile/{uuid}.json 路径）
- 新版 CLI sau_cli.py 与 uploader/account_manager（cookies/taobao_guanghe_uploader/{account}.json 路径）
"""

from pathlib import Path
from conf import BASE_DIR

# 提前创建 cookies 目录（CLI 风格路径），避免首次写入时报错
_COOKIE_DIR = Path(BASE_DIR) / "cookies" / "taobao_guanghe_uploader"
_COOKIE_DIR.mkdir(parents=True, exist_ok=True)

from uploader.taobao_guanghe_uploader.login import (
    cookie_auth,
    taobao_guanghe_setup,
    taobao_guanghe_cookie_gen,
)

__all__ = [
    "cookie_auth",
    "taobao_guanghe_setup",
    "taobao_guanghe_cookie_gen",
]
