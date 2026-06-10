#!/usr/bin/env python3
"""淘宝光合自动登录"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from uploader.taobao_guanghe_uploader.login import taobao_guanghe_setup


async def main():
    account_file = Path("cookies/taobao_guanghe_uploader/test_account.json")

    print("开始登录淘宝光合...")
    print(f"Cookie 文件: {account_file}")

    result = await taobao_guanghe_setup(
        account_file=account_file,
        handle=True,
        headless=False,
        use_system_chrome=True,
    )

    if result:
        print(f"\n✅ 登录成功")
    else:
        print(f"\n❌ 登录失败")

    return result


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
