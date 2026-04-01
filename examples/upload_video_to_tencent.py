"""
当前文件先保留为视频号 uploader 的调试入口 / 历史直连路径。

注意：
1. `uploader/tencent_uploader/main.py` 里的核心页面交互逻辑目前是骨架；
2. 你需要自己补视频里的 `fill_title_and_tags` / `wait_for_upload_complete` / `set_thumbnail` / `submit_publish` 等方法；
3. 你需要自己补图文里的 `switch_to_note_mode` / `upload_note_images` / `fill_note_title_and_tags` / `submit_publish` 等方法；
3. 补完后，这个 example 就可以直接作为本地调试入口继续使用。
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from conf import BASE_DIR
from uploader.tencent_uploader.main import TENCENT_PUBLISH_STRATEGY_IMMEDIATE
from uploader.tencent_uploader.main import TENCENT_PUBLISH_STRATEGY_SCHEDULED
from uploader.tencent_uploader.main import TencentNote
from uploader.tencent_uploader.main import TencentVideo


ACCOUNT_FILE = Path(BASE_DIR / "cookies" / "tencent_uploader" / "account.json")


def upload_video_to_tencent():
    video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
    thumbnail_path = video_file.with_suffix(".png")
    app = TencentVideo(
        title="视频号视频示例",
        file_path=str(video_file),
        tags=["视频号", "自动上传", "调试入口"],
        publish_strategy=TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        publish_date=0,
        account_file=str(ACCOUNT_FILE),
        desc="这里是你后面准备填写的视频简介示例",
        thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
        short_title="视频号示例",
        category=None,
        is_draft=False,
    )
    asyncio.run(app.tencent_upload_video())


def upload_video_to_tencent_scheduled():
    video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
    thumbnail_path = video_file.with_suffix(".png")
    publish_time = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    app = TencentVideo(
        title="视频号定时发布示例",
        file_path=str(video_file),
        tags=["视频号", "定时发布", "调试入口"],
        publish_strategy=TENCENT_PUBLISH_STRATEGY_SCHEDULED,
        publish_date=publish_time,
        account_file=str(ACCOUNT_FILE),
        desc="这里是定时发布的视频简介示例",
        thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
        short_title="定时发布示例",
        category=None,
        is_draft=False,
    )
    asyncio.run(app.tencent_upload_video())


def upload_note_to_tencent():
    image_candidates = [
        Path(BASE_DIR) / "videos" / "demo.png",
        Path(BASE_DIR) / "videos" / "demo1.png",
        Path(BASE_DIR) / "videos" / "demo2.png",
    ]
    image_paths = [str(path) for path in image_candidates if path.exists()]
    app = TencentNote(
        image_paths=image_paths,
        note="视频号图文内容示例 #图文调试",
        tags=["视频号图文", "自动上传", "调试入口"],
        publish_strategy=TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        publish_date=0,
        account_file=str(ACCOUNT_FILE),
        title="视频号图文示例",
        is_draft=False,
    )
    asyncio.run(app.tencent_upload_note())


def upload_note_to_tencent_scheduled():
    image_candidates = [
        Path(BASE_DIR) / "videos" / "demo.png",
        Path(BASE_DIR) / "videos" / "demo1.png",
        Path(BASE_DIR) / "videos" / "demo2.png",
    ]
    image_paths = [str(path) for path in image_candidates if path.exists()]
    publish_time = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    app = TencentNote(
        image_paths=image_paths,
        note="视频号图文定时发布示例 #图文调试",
        tags=["视频号图文", "定时发布", "调试入口"],
        publish_strategy=TENCENT_PUBLISH_STRATEGY_SCHEDULED,
        publish_date=publish_time,
        account_file=str(ACCOUNT_FILE),
        title="视频号图文定时示例",
        is_draft=False,
    )
    asyncio.run(app.tencent_upload_note())


if __name__ == "__main__":
    upload_video_to_tencent()
    # upload_video_to_tencent_scheduled()
    # upload_note_to_tencent()
    # upload_note_to_tencent_scheduled()
