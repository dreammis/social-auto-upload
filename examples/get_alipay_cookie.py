# -*- coding: utf-8 -*-
"""获取支付宝生活号 cookie：打开浏览器扫码登录后自动保存到 cookies/alipay_uploader/account.json"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from uploader.alipay_uploader.main import alipay_cookie_gen


async def main():
    account_file = Path(__file__).resolve().parents[1] / "cookies" / "alipay_uploader" / "account.json"
    await alipay_cookie_gen(str(account_file))


if __name__ == "__main__":
    asyncio.run(main())
