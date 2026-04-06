"""
当前主线优先使用 CLI：

    sau xiaohongshu login --account <account_name>
    sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "示例标题" --desc "示例简介"
    sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png --title "图文标题" --note "图文正文"

这个脚本保留为小红书 uploader 的调试入口 / 历史直连路径。
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from conf import BASE_DIR
from uploader.xiaohongshu_uploader.main import XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
from uploader.xiaohongshu_uploader.main import XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED
from uploader.xiaohongshu_uploader.main import XiaoHongShuNote
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo


ACCOUNT_FILE = Path(BASE_DIR / "cookies" / "xiaohongshu_uploader" / "account.json")


def upload_video_to_xiaohongshu():
    video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
    thumbnail_path = video_file.with_suffix(".png")
    app = XiaoHongShuVideo(
        title="小红书视频示例",
        file_path=str(video_file),
        desc="你好",
        tags=["小红书", "视频示例", "调试入口"],
        publish_strategy=XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
        publish_date=0,
        account_file=str(ACCOUNT_FILE),
        thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
    )
    asyncio.run(app.xiaohongshu_upload_video())


def upload_video_to_xiaohongshu_scheduled():
    video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
    thumbnail_path = video_file.with_suffix(".png")
    publish_time = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    app = XiaoHongShuVideo(
        title="小红书视频定时发布示例",
        file_path=str(video_file),
        desc="这是一条定时发布的小红书视频示例",
        tags=["小红书", "定时发布", "调试入口"],
        publish_strategy=XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
        publish_date=publish_time,
        account_file=str(ACCOUNT_FILE),
        thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
    )
    asyncio.run(app.xiaohongshu_upload_video())


def upload_note_to_xiaohongshu():
    image_candidates = [
        Path(BASE_DIR) / "videos" / "demo.png",
        Path(BASE_DIR) / "videos" / "demo1.png",
        Path(BASE_DIR) / "videos" / "demo2.png",
    ]
    image_paths = [str(path) for path in image_candidates if path.exists()]
    app = XiaoHongShuNote(
        image_paths=image_paths,
        note="小红书图文内容示例 #图文调试",
        tags=["小红书图文", "自动上传", "调试入口"],
        publish_strategy=XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
        publish_date=0,
        account_file=str(ACCOUNT_FILE),
        title="小红书图文示例",
    )
    asyncio.run(app.xiaohongshu_upload_note())

def upload_note_to_xiaohongshu_scheduled():
    image_candidates = [
        Path(BASE_DIR) / "videos" / "demo.png",
        Path(BASE_DIR) / "videos" / "demo1.png",
        Path(BASE_DIR) / "videos" / "demo2.png",
    ]
    image_paths = [str(path) for path in image_candidates if path.exists()]
    publish_time = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    app = XiaoHongShuNote(
        image_paths=image_paths,
        note="小红书图文内容示例 #图文调试",
        tags=["小红书图文", "自动上传", "调试入口"],
        publish_strategy=XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
        publish_date=publish_time,
        account_file=str(ACCOUNT_FILE),
        title="小红书图文示例",
    )
    asyncio.run(app.xiaohongshu_upload_note())


if __name__ == '__main__':
    # upload_video_to_xiaohongshu()
    # upload_video_to_xiaohongshu_scheduled()
    # upload_note_to_xiaohongshu()
    upload_note_to_xiaohongshu_scheduled()
