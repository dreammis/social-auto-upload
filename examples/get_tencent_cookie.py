import asyncio
from pathlib import Path

from conf import BASE_DIR
from tencent_uploader.main import weixin_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "tencent_uploader" / "account.json")
    cookie_setup = asyncio.run(weixin_setup(str(account_file), handle=True))
