import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.tencent_uploader.main import tencent_setup


if __name__ == "__main__":
    account_file = Path(BASE_DIR / "cookies" / "tencent_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)
    asyncio.run(tencent_setup(str(account_file), handle=True))
