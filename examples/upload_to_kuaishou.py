"""Legacy direct-uploader example for Kuaishou.

Current mainline usage prefers:
    sau kuaishou login --account creator
    sau kuaishou upload-video ...
    sau kuaishou upload-note ...
"""

import asyncio
from datetime import datetime
from pathlib import Path

from conf import BASE_DIR
from uploader.ks_uploader.main import (
    KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE,
    KUAISHOU_PUBLISH_STRATEGY_SCHEDULED,
    KSNote,
    KSVideo,
)


def upload_video_to_kuaishou():
    account_file = Path(BASE_DIR / "cookies" / "kuaishou_creator.json")
    account_file.parent.mkdir(exist_ok=True)

    video_file_path = Path(BASE_DIR) / "videos/demo.mp4"
    thumbnail_path = video_file_path.with_suffix(".png")
    video_meta_title = "快手视频上传示例"
    video_meta_hashtags = ["快手", "自动上传", "示例"]
    video_meta_publish_time = datetime.strptime("2026-03-27 12:13", "%Y-%m-%d %H:%M")
    publish_strategy = KUAISHOU_PUBLISH_STRATEGY_SCHEDULED

    app = KSVideo(
        title=video_meta_title,
        file_path=video_file_path,
        tags=video_meta_hashtags,
        publish_date=video_meta_publish_time,
        account_file=account_file,
        thumbnail_path=thumbnail_path if thumbnail_path.exists() else None,
        publish_strategy=publish_strategy,
    )
    asyncio.run(app.main())


def upload_note_to_kuaishou():
    account_file = Path(BASE_DIR / "cookies" / "kuaishou_creator.json")
    account_file.parent.mkdir(exist_ok=True)

    image_paths = [
        Path(BASE_DIR) / "videos/demo.png",
        Path(BASE_DIR) / "videos/demo1.png",
        Path(BASE_DIR) / "videos/demo2.png",
    ]
    note = "快手图文内容示例"
    tags = ["快手图文", "自动上传", "示例"]
    note_meta_publish_time = datetime.strptime("2026-03-27 12:13", "%Y-%m-%d %H:%M")
    publish_strategy = KUAISHOU_PUBLISH_STRATEGY_SCHEDULED

    app = KSNote(
        image_paths=image_paths,
        note=note,
        tags=tags,
        publish_date=note_meta_publish_time,
        account_file=account_file,
        publish_strategy=publish_strategy,
    )
    asyncio.run(app.main())


if __name__ == '__main__':
    upload_video_to_kuaishou()
    # upload_note_to_kuaishou()
