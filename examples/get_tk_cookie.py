import asyncio
from pathlib import Path

from conf import BASE_DIR
from tk_uploader.main import tiktok_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "tk_uploader" / "account.json")
    cookie_setup = asyncio.run(tiktok_setup(str(account_file), handle=True))
