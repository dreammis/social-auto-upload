"""Legacy direct login helper for Kuaishou.

Current mainline usage prefers:
    sau kuaishou login --account creator
"""

import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.ks_uploader.main import ks_setup


def login_to_kuaishou():
    account_file = Path(BASE_DIR / "cookies" / "kuaishou_creator.json")
    account_file.parent.mkdir(exist_ok=True)
    asyncio.run(ks_setup(str(account_file), handle=True))


if __name__ == '__main__':
    login_to_kuaishou()
