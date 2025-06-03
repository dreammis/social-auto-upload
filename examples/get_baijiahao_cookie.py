import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.baijiahao_uploader.main import baijiahao_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookies" / "baijiahao_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)
    cookie_setup = asyncio.run(baijiahao_setup(str(account_file), handle=True))
