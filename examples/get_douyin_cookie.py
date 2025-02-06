import asyncio
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))

from conf import BASE_DIR
from uploader.douyin_uploader.main import douyin_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / "account.json")
    cookie_setup = asyncio.run(douyin_setup(str(account_file), handle=True))
