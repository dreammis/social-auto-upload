import asyncio
from datetime import datetime
from pathlib import Path

from conf import BASE_DIR
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo
from uploader.bilibili_uploader.runtime import run_biliup_command
from uploader.douyin_uploader.main import (
    DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
    DOUYIN_PUBLISH_STRATEGY_SCHEDULED,
    DouYinNote,
    DouYinVideo,
)
from uploader.ks_uploader.main import (
    KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE,
    KUAISHOU_PUBLISH_STRATEGY_SCHEDULED,
    KSNote,
    KSVideo,
)
from uploader.tk_uploader.main_chrome import TiktokVideo
from uploader.tencent_uploader.main import TencentVideo
from uploader.xiaohongshu_uploader.main import (
    XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
    XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
    XiaoHongShuNote,
    XiaoHongShuVideo,
)
from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day


def post_video_tencent(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0, is_draft=False):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = TencentVideo(title, str(file), tags, publish_datetimes[index], cookie, category, is_draft)
            asyncio.run(app.main(), debug=False)


def post_video_DouYin(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0,
                      thumbnail_path = '',
                      productLink = '', productTitle = ''):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = DouYinVideo(title, str(file), tags, publish_datetimes[index], cookie, thumbnail_path, productLink, productTitle)
            asyncio.run(app.douyin_upload_video(), debug=False)


def post_video_ks(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = KSVideo(title, str(file), tags, publish_datetimes[index], cookie)
            asyncio.run(app.main(), debug=False)

def post_video_xhs(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0):
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    file_num = len(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = 0
    for index, file in enumerate(files):
        for cookie in account_file:
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = XiaoHongShuVideo(title, file, tags, publish_datetimes, cookie)
            asyncio.run(app.main(), debug=False)


def post_note_douyin(title, files, note, tags, account_file, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
        publish_strategy = DOUYIN_PUBLISH_STRATEGY_SCHEDULED
    else:
        publish_datetimes = [0 for _ in range(len(files))]
        publish_strategy = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
    for cookie in account_file:
        app = DouYinNote(
            image_paths=[str(file) for file in files],
            title=title,
            note=note,
            tags=tags,
            publish_date=publish_datetimes[0] if publish_datetimes else 0,
            account_file=str(cookie),
            publish_strategy=publish_strategy,
        )
        asyncio.run(app.douyin_upload_note(), debug=False)


def post_note_ks(title, files, note, tags, account_file, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
        publish_strategy = KUAISHOU_PUBLISH_STRATEGY_SCHEDULED
    else:
        publish_datetimes = [0 for _ in range(len(files))]
        publish_strategy = KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE
    for cookie in account_file:
        app = KSNote(
            image_paths=[str(file) for file in files],
            title=title,
            note=note,
            tags=tags,
            publish_date=publish_datetimes[0] if publish_datetimes else 0,
            account_file=str(cookie),
            publish_strategy=publish_strategy,
        )
        asyncio.run(app.main(), debug=False)


def post_note_xhs(title, files, note, tags, account_file, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(1, videos_per_day, daily_times, start_days)
        publish_strategy = XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED
    else:
        publish_datetimes = [0]
        publish_strategy = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    for cookie in account_file:
        app = XiaoHongShuNote(
            image_paths=[str(file) for file in files],
            title=title,
            desc=note,
            note=note,
            tags=tags,
            publish_date=publish_datetimes[0] if publish_datetimes else 0,
            account_file=str(cookie),
            publish_strategy=publish_strategy,
        )
        asyncio.run(app.main(), debug=False)


def _resolve_video_files(files):
    return [Path(BASE_DIR / "videoFile" / file) for file in files]


def _resolve_cookie_files(account_file):
    return [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]


def _schedule_datetimes(file_count, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    if enableTimer:
        return generate_schedule_time_next_day(file_count, videos_per_day, daily_times, start_days)
    return [0 for _ in range(file_count)]


def _bilibili_cookie_path(cookie):
    cookie = Path(cookie)
    if cookie.is_absolute() or cookie.exists():
        return cookie
    return Path(BASE_DIR / "cookiesFile" / cookie)


def post_video_bilibili(title, files, tags, account_file, category=21, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0, description=''):
    resolved_files = _resolve_video_files(files)
    account_files = [_bilibili_cookie_path(file) for file in account_file]
    publish_datetimes = _schedule_datetimes(len(resolved_files), enableTimer, videos_per_day, daily_times, start_days)
    desc = description or title
    tid = int(category or 21)

    for index, file in enumerate(resolved_files):
        for cookie in account_files:
            if not cookie.exists():
                raise FileNotFoundError(f"Bilibili cookie 文件不存在: {cookie}")
            arguments = [
                "-u",
                str(cookie),
                "upload",
                str(file),
                "--title",
                title,
                "--desc",
                desc,
                "--tid",
                str(tid),
            ]
            if tags:
                arguments.extend(["--tag", ",".join(tags)])
            publish_date = publish_datetimes[index]
            if isinstance(publish_date, datetime):
                arguments.extend(["--dtime", str(int(publish_date.timestamp()))])

            result = run_biliup_command(arguments)
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "").strip() or "Bilibili upload failed")


def post_video_baijiahao(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    account_files = _resolve_cookie_files(account_file)
    resolved_files = _resolve_video_files(files)
    publish_datetimes = _schedule_datetimes(len(resolved_files), enableTimer, videos_per_day, daily_times, start_days)

    for index, file in enumerate(resolved_files):
        for cookie in account_files:
            app = BaiJiaHaoVideo(title, str(file), tags, publish_datetimes[index], str(cookie))
            asyncio.run(app.main(), debug=False)


def _resolve_tiktok_cookie(cookie):
    cookie = Path(cookie)
    if cookie.is_absolute() or cookie.exists():
        return str(cookie)
    return str(Path(BASE_DIR / "cookiesFile" / cookie))


def post_video_tiktok(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0, thumbnail_path=None):
    resolved_files = _resolve_video_files(files)
    publish_datetimes = _schedule_datetimes(len(resolved_files), enableTimer, videos_per_day, daily_times, start_days)
    thumbnail = str(Path(BASE_DIR / "videoFile" / thumbnail_path)) if thumbnail_path else None

    for index, file in enumerate(resolved_files):
        for cookie in account_file:
            app = TiktokVideo(title, str(file), tags, publish_datetimes[index], _resolve_tiktok_cookie(cookie), thumbnail)
            asyncio.run(app.main(), debug=False)
