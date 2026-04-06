"""
当前主线优先使用 CLI：

    sau xiaohongshu login --account <account_name>

这个脚本保留为小红书 uploader 的调试入口 / 历史直连路径。
"""

import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.xiaohongshu_uploader.main import xiaohongshu_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookies" / "xiaohongshu_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)
    result = asyncio.run(
        xiaohongshu_setup(
            str(account_file),
            handle=True,
            return_detail=True,
        )
    )
