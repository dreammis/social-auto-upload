"""Legacy direct-uploader example for Douyin.

Current mainline usage prefers:
    sau douyin login --account creator
    sau douyin upload-video ...
    sau douyin upload-note ...
"""

import asyncio
from datetime import datetime
from pathlib import Path

from conf import BASE_DIR
from uploader.douyin_uploader.main import (
    DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
    DOUYIN_PUBLISH_STRATEGY_SCHEDULED,
    DouYinNote,
    DouYinVideo,
)


def upload_video_to_douyin():
    account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / "account.json")
    video_file_path = Path(BASE_DIR) / "videos/demo.mp4"
    video_meta_title = "男子为了心爱之人每天坚守❤️‍🩹"
    video_meta_hashtags = ["坚持不懈", "爱情执着", "奋斗使者", "短视频"]
    thumbnail_landscape_path = Path(BASE_DIR) / "videos/demo.png"
    thumbnail_portrait_path = Path(BASE_DIR) / "videos/demo.png"
    video_meta_publish_time = datetime.strptime("2026-3-25 12:13", "%Y-%m-%d %H:%M")

    app = DouYinVideo(
        title=video_meta_title,
        file_path=video_file_path,
        tags=video_meta_hashtags,
        publish_date=video_meta_publish_time,
        thumbnail_landscape_path=thumbnail_landscape_path,
        thumbnail_portrait_path=thumbnail_portrait_path,
        account_file=account_file,
        publish_strategy=DOUYIN_PUBLISH_STRATEGY_SCHEDULED,
    )
    asyncio.run(app.douyin_upload_video())


def upload_note_to_douyin():
    account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / "account.json")
    image_paths = [Path(BASE_DIR) / "videos/demo.png", Path(BASE_DIR) / "videos/demo.png", Path(BASE_DIR) / "videos/demo.png"]
    note = "图文内容示例"
    tags = ["图文", "示例", "抖音图文"]
    video_meta_publish_time = datetime.strptime("2026-3-25 12:13", "%Y-%m-%d %H:%M")

    app = DouYinNote(
        image_paths=image_paths,
        note=note,
        tags=tags,
        publish_date=0,
        account_file=account_file,
        publish_strategy=DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
    )
    asyncio.run(app.douyin_upload_note())


if __name__ == "__main__":
    # upload_video_to_douyin()
    upload_note_to_douyin()
