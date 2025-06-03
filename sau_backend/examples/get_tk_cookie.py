import asyncio
from pathlib import Path

from sau_backend.conf import BASE_DIR
from sau_backend.uploader.tk_uploader.main_chrome import tiktok_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookies" / "tk_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)
    cookie_setup = asyncio.run(tiktok_setup(str(account_file), handle=True))
