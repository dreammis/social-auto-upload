# -*- coding: utf-8 -*-
"""测试支付宝生活号上传：使用已保存的 cookie 上传并发布一个视频。"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from uploader.alipay_uploader.main import AlipayVideo


async def main():
    base = Path(__file__).resolve().parents[1]
    video_path = Path(r"D:\video-moving\assets\outro\outro_horizontal.mp4")
    account_file = base / "cookies" / "alipay_uploader" / "account.json"

    app = AlipayVideo(
        title="测试发布标题",
        file_path=str(video_path),
        tags=["测试", "自动化"],
        account_file=str(account_file),
        desc="测试描述",
        thumbnail_path=r"C:\Users\admin\Downloads\ScreenShot_2026-08-04_170159_630.png",
        collection_name="",
        headless=False,
    )
    await app.main()


if __name__ == "__main__":
    asyncio.run(main())
