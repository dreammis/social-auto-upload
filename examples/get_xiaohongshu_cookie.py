import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.xiaohongshu_uploader.main import xiaohongshu_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookies" / "xiaohongshu_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)
    cookie_setup = asyncio.run(xiaohongshu_setup(str(account_file), handle=True))
