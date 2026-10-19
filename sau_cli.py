from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from patchright.async_api import async_playwright

from conf import BASE_DIR, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.article_render import ARTICLE_THEMES, render_article_file, setup_article_renderer
from uploader.xueqiu_uploader.article import XueqiuArticle
from uploader.xueqiu_uploader.constants import XUEQIU_DECLARATIONS, XUEQIU_VISIBILITY
from uploader.xueqiu_uploader.session import check_xueqiu_account, login_xueqiu_account
from uploader.xueqiu_uploader.verification import verify_xueqiu_result
from uploader.dayu_uploader.article import DayuArticle
from uploader.dayu_uploader.constants import (
    DAYU_SOURCE_TYPES, DAYU_VIDEO_CATEGORIES, DAYU_SCHEDULE_MIN_HOURS,
    DAYU_SCHEDULE_MAX_DAYS, DAYU_SCHEDULE_STEP_MINUTES,
)
from uploader.dayu_uploader.main import DayuVideo
from uploader.dayu_uploader.session import (
    DAYU_HOME_URL,
    check_dayu_account,
    load_dayu_identity,
    login_dayu_account,
    read_dayu_identity,
)
from uploader.dayu_uploader.verification import verify_dayu_article, verify_dayu_video
from uploader.baijiahao_uploader.main import (
    BaiJiaHaoVideo,
    baijiahao_setup,
    cookie_auth as baijiahao_cookie_auth,
)
from uploader.alipay_uploader.main import (
    AlipayVideo,
    alipay_setup,
    cookie_auth as alipay_cookie_auth,
)
from uploader.bilibili_uploader.runtime import run_biliup_command
from uploader.douyin_uploader.main import (
    DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
    DOUYIN_PUBLISH_STRATEGY_SCHEDULED,
    DouYinNote,
    DouYinVideo,
    cookie_auth as douyin_cookie_auth,
    douyin_setup,
)
from uploader.ks_uploader.main import (
    KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE,
    KUAISHOU_PUBLISH_STRATEGY_SCHEDULED,
    KSNote,
    KSVideo,
    cookie_auth as kuaishou_cookie_auth,
    ks_setup,
)
from uploader.tencent_uploader.main import (
    TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
    TENCENT_PUBLISH_STRATEGY_SCHEDULED,
    TencentVideo,
    cookie_auth as tencent_cookie_auth,
    tencent_setup,
)
from uploader.weibo_uploader.main import (
    WeiBoVideo,
    weibo_setup,
    cookie_auth as weibo_cookie_auth,
)
from uploader.hupu_uploader.main import (
    HuPuVideo,
    hupu_setup,
    cookie_auth as hupu_cookie_auth,
)
from uploader.xiaohongshu_uploader.main import (
    XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
    XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
    XiaoHongShuNote,
    XiaoHongShuVideo,
    cookie_auth as xiaohongshu_cookie_auth,
    xiaohongshu_setup,
)
from uploader.youtube_uploader.main import (
    YouTubeVideo,
    cookie_auth as youtube_cookie_auth,
    youtube_setup,
)
from uploader.meta_uploader.facebook_uploader.main import (
    DEFAULT_FACEBOOK_PROXY,
    FacebookVideo,
    FacebookPost,
    facebook_cookie_auth,
    facebook_setup,
)
from uploader.meta_uploader.facebook_page_uploader.main import (
    META_PROXY,
    MetaBusinessUploader,
    meta_cookie_auth,
    meta_setup,
)
from uploader.meta_uploader.facebook_uploader.posts import facebook_post_action
from uploader.meta_uploader.facebook_page_uploader.posts import meta_post_action

SCHEDULE_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(slots=True)
class DouyinVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    thumbnail_landscape_file: Path | None = None
    thumbnail_portrait_file: Path | None = None
    product_link: str = ""
    product_title: str = ""
    publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
    declaration: str | None = None
    collection_name: str | None = None


@dataclass(slots=True)
class DouyinNoteUploadRequest:
    account_name: str
    image_files: list[Path]
    title: str
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
    bgm: str = ""


@dataclass(slots=True)
class KuaishouVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    publish_strategy: str = KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
    collection_name: str | None = None


@dataclass(slots=True)
class KuaishouNoteUploadRequest:
    account_name: str
    image_files: list[Path]
    title: str
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class XiaohongshuVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class XiaohongshuNoteUploadRequest:
    account_name: str
    image_files: list[Path]
    title: str
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class BilibiliVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tid: int
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None


@dataclass(slots=True)
class TencentVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    thumbnail_landscape_file: Path | None = None
    thumbnail_portrait_file: Path | None = None
    short_title: str | None = None
    category: str | None = None
    is_draft: bool = False
    publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
    collection_name: str | None = None


@dataclass(slots=True)
class BaijiahaoVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    collection_name: str | None = None
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class AlipayVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    collection_name: str | None = None
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class WeiboVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    collection_name: str | None = None
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class HupuVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class YouTubeVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    playlist: str | None = None
    visibility: str = "public"
    schedule: datetime | int = 0
    debug: bool = True
    headless: bool = False


@dataclass(slots=True)
class FacebookVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    proxy: str = DEFAULT_FACEBOOK_PROXY
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class MetaUploadRequest:
    platform: str
    account_name: str
    title: str
    description: str
    tags: list[str]
    video_file: Path | None = None
    image_files: list[Path] | None = None
    schedule: datetime | int = 0
    page_name: str | None = None
    proxy: str = META_PROXY
    debug: bool = True
    headless: bool = False
    result_file: Path | None = None


def has_interactive_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def resolve_runtime_home() -> Path:
    return Path(BASE_DIR)


def resolve_account_file(platform: str, account_name: str) -> Path:
    account_file = resolve_runtime_home() / "cookies" / f"{platform}_{account_name}.json"
    account_file.parent.mkdir(exist_ok=True)
    return account_file


def parse_tags(raw_tags: str | None) -> list[str]:
    if not raw_tags:
        return []

    tags: list[str] = []
    for item in raw_tags.split(","):
        cleaned = item.strip().lstrip("#")
        if cleaned:
            tags.append(cleaned)
    return tags


def parse_image_files(raw_files: Iterable[Path]) -> list[Path]:
    return [Path(file) for file in raw_files]


def parse_schedule(raw_schedule: str | None) -> datetime | int:
    if not raw_schedule:
        return 0
    return datetime.strptime(raw_schedule, SCHEDULE_FORMAT)


async def login_douyin_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("douyin", account_name)
    return await douyin_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_douyin_account(account_name: str) -> bool:
    account_file = resolve_account_file("douyin", account_name)
    if not account_file.exists():
        return False
    return await douyin_cookie_auth(str(account_file))


async def login_kuaishou_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("kuaishou", account_name)
    return await ks_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_kuaishou_account(account_name: str) -> bool:
    account_file = resolve_account_file("kuaishou", account_name)
    if not account_file.exists():
        return False
    return await kuaishou_cookie_auth(str(account_file))


async def login_xiaohongshu_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("xiaohongshu", account_name)
    return await xiaohongshu_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_xiaohongshu_account(account_name: str) -> bool:
    account_file = resolve_account_file("xiaohongshu", account_name)
    if not account_file.exists():
        return False
    return await xiaohongshu_cookie_auth(str(account_file))


async def login_bilibili_account(account_name: str) -> dict:
    account_file = resolve_account_file("bilibili", account_name)
    if not has_interactive_terminal():
        return {
            "success": False,
            "message": (
                "Bilibili login requires a local interactive terminal. "
                f"Please run `sau bilibili login --account {account_name}` yourself in a local terminal. "
                "If the terminal QR code does not render completely, open `./qrcode.png` and scan that image."
            ),
            "account_file": str(account_file),
        }

    result = run_biliup_command(["-u", str(account_file), "login"], interactive=True)
    success = result.returncode == 0
    return {
        "success": success,
        "message": (result.stderr or result.stdout or "").strip() or "Bilibili login completed" if success else (result.stderr or result.stdout or "").strip() or "Bilibili login failed",
        "account_file": str(account_file),
    }


async def check_bilibili_account(account_name: str) -> bool:
    account_file = resolve_account_file("bilibili", account_name)
    if not account_file.exists():
        return False
    result = run_biliup_command(["-u", str(account_file), "renew"])
    return result.returncode == 0


async def login_tencent_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("tencent", account_name)
    return await tencent_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_tencent_account(account_name: str) -> bool:
    account_file = resolve_account_file("tencent", account_name)
    if not account_file.exists():
        return False
    return await tencent_cookie_auth(str(account_file))


async def login_youtube_account(account_name: str, headless: bool = False) -> dict:
    account_file = resolve_account_file("youtube", account_name)
    return await youtube_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_youtube_account(account_name: str) -> bool:
    account_file = resolve_account_file("youtube", account_name)
    if not account_file.exists():
        return False
    return await youtube_cookie_auth(str(account_file))


async def login_facebook_account(
    account_name: str, *, headless: bool = False, proxy: str | None = DEFAULT_FACEBOOK_PROXY
) -> dict:
    account_file = resolve_account_file("facebook", account_name)
    return await facebook_setup(
        account_file,
        handle=True,
        return_detail=True,
        headless=headless,
        proxy=proxy,
    )


async def check_facebook_account(
    account_name: str, *, proxy: str | None = DEFAULT_FACEBOOK_PROXY
) -> bool:
    account_file = resolve_account_file("facebook", account_name)
    if not account_file.exists():
        return False
    return await facebook_cookie_auth(account_file, proxy=proxy)


async def upload_youtube_video(request: YouTubeVideoUploadRequest) -> Path:
    account_file = resolve_account_file("youtube", request.account_name)
    is_ready = await youtube_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"YouTube cookie is missing or expired: {account_file}. Run `sau youtube login --account {request.account_name}` first."
        )

    app = YouTubeVideo(
        request.title,
        str(request.video_file),
        request.tags,
        str(account_file),
        description=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        playlist=request.playlist,
        visibility=request.visibility,
        debug=request.debug,
        headless=request.headless,
    )
    app.set_publish_date(request.schedule)
    await app.main()
    return account_file


async def upload_facebook_video(request: FacebookVideoUploadRequest) -> Path:
    account_file = resolve_account_file("facebook", request.account_name)
    is_ready = await facebook_setup(
        account_file,
        handle=False,
        proxy=request.proxy,
    )
    if not is_ready:
        raise RuntimeError(
            f"Facebook 登录态不存在或已失效: {account_file}. "
            f"请先执行 `sau facebook login --account {request.account_name}`。"
        )

    app = FacebookVideo(
        title=request.title,
        file_path=request.video_file,
        description=request.description,
        tags=request.tags,
        account_file=account_file,
        proxy=request.proxy,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def login_meta_account(platform: str, account_name: str, *, headless: bool = False, proxy: str | None = META_PROXY) -> dict:
    account_file = resolve_account_file(platform, account_name)
    return await meta_setup(
        account_file,
        handle=True,
        return_detail=True,
        headless=headless,
        proxy=proxy,
    )


async def check_meta_account(platform: str, account_name: str, *, proxy: str | None = META_PROXY) -> bool:
    account_file = resolve_account_file(platform, account_name)
    return await meta_cookie_auth(account_file, proxy=proxy)


async def upload_meta_content(request: MetaUploadRequest) -> dict:
    account_file = resolve_account_file(request.platform, request.account_name)
    if not await meta_cookie_auth(account_file, proxy=request.proxy):
        raise RuntimeError(
            f"{request.platform} Business Suite 登录态不存在或已失效: {account_file}. "
            f"请先执行 `sau {request.platform} login --account {request.account_name}`。"
        )
    app = MetaBusinessUploader(
        request.platform,
        account_file,
        title=request.title,
        description=request.description,
        tags=request.tags,
        video_file=request.video_file,
        image_files=request.image_files,
        schedule=request.schedule,
        page_name=request.page_name,
        proxy=request.proxy,
        headless=request.headless,
        result_file=request.result_file,
    )
    return await app.upload()


async def upload_video(request: DouyinVideoUploadRequest) -> Path:
    account_file = resolve_account_file("douyin", request.account_name)
    is_ready = await douyin_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Douyin cookie is missing or expired: {account_file}. Run `sau douyin login --account {request.account_name}` first."
        )

    app = DouYinVideo(
        request.title,
        str(request.video_file),
        request.tags,
        request.publish_date,
        str(account_file),
        desc=request.description,
        thumbnail_landscape_path=(
            str(request.thumbnail_landscape_file) if request.thumbnail_landscape_file else None
        ),
        thumbnail_portrait_path=str(
            request.thumbnail_portrait_file or request.thumbnail_file
        ) if request.thumbnail_portrait_file or request.thumbnail_file else None,
        productLink=request.product_link,
        productTitle=request.product_title,
        declaration=request.declaration,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        collection_name=request.collection_name,
    )
    await app.douyin_upload_video()
    return account_file


async def upload_note(request: DouyinNoteUploadRequest) -> Path:
    account_file = resolve_account_file("douyin", request.account_name)
    is_ready = await douyin_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Douyin cookie is missing or expired: {account_file}. Run `sau douyin login --account {request.account_name}` first."
        )

    app = DouYinNote(
        image_paths=[str(path) for path in request.image_files],
        title=request.title,
        note=request.note,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        bgm=request.bgm,
    )
    await app.douyin_upload_note()
    return account_file


async def upload_kuaishou_video(request: KuaishouVideoUploadRequest) -> Path:
    account_file = resolve_account_file("kuaishou", request.account_name)
    is_ready = await ks_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Kuaishou cookie is missing or expired: {account_file}. Run `sau kuaishou login --account {request.account_name}` first."
        )

    app = KSVideo(
        title=request.title,
        file_path=str(request.video_file),
        desc=request.description,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        collection_name=request.collection_name,
    )
    await app.main()
    return account_file


async def upload_kuaishou_note(request: KuaishouNoteUploadRequest) -> Path:
    account_file = resolve_account_file("kuaishou", request.account_name)
    is_ready = await ks_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Kuaishou cookie is missing or expired: {account_file}. Run `sau kuaishou login --account {request.account_name}` first."
        )

    app = KSNote(
        image_paths=[str(path) for path in request.image_files],
        title=request.title,
        note=request.note,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def upload_xiaohongshu_video(request: XiaohongshuVideoUploadRequest) -> Path:
    account_file = resolve_account_file("xiaohongshu", request.account_name)
    is_ready = await xiaohongshu_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Xiaohongshu cookie is missing or expired: {account_file}. Run `sau xiaohongshu login --account {request.account_name}` first."
        )

    app = XiaoHongShuVideo(
        title=request.title,
        file_path=str(request.video_file),
        desc=request.description,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def upload_xiaohongshu_note(request: XiaohongshuNoteUploadRequest) -> Path:
    account_file = resolve_account_file("xiaohongshu", request.account_name)
    is_ready = await xiaohongshu_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Xiaohongshu cookie is missing or expired: {account_file}. Run `sau xiaohongshu login --account {request.account_name}` first."
        )

    app = XiaoHongShuNote(
        image_paths=[str(path) for path in request.image_files],
        title=request.title,
        desc=request.note,
        note=request.note,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def upload_bilibili_video(request: BilibiliVideoUploadRequest) -> Path:
    account_file = resolve_account_file("bilibili", request.account_name)
    if not account_file.exists():
        raise RuntimeError(
            f"Bilibili account file is missing: {account_file}. Run `sau bilibili login --account {request.account_name}` first."
        )

    arguments = [
        "-u",
        str(account_file),
        "upload",
        str(request.video_file),
        "--title",
        request.title,
        "--desc",
        request.description,
        "--tid",
        str(request.tid),
    ]
    if request.tags:
        arguments.extend(["--tag", ",".join(request.tags)])
    if request.thumbnail_file:
        arguments.extend(["--cover", str(request.thumbnail_file)])
    if isinstance(request.publish_date, datetime):
        arguments.extend(["--dtime", str(int(request.publish_date.timestamp()))])

    result = run_biliup_command(arguments)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "").strip() or "Bilibili upload failed")
    return account_file


async def upload_tencent_video(request: TencentVideoUploadRequest) -> Path:
    account_file = resolve_account_file("tencent", request.account_name)
    is_ready = await tencent_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Tencent/WeChat Channels cookie is missing or expired: {account_file}. "
            f"Run `sau tencent login --account {request.account_name}` first."
        )

    app = TencentVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        category=request.category,
        is_draft=request.is_draft,
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        thumbnail_landscape_path=(
            str(request.thumbnail_landscape_file) if request.thumbnail_landscape_file else None
        ),
        thumbnail_portrait_path=(
            str(request.thumbnail_portrait_file) if request.thumbnail_portrait_file else None
        ),
        short_title=request.short_title,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        collection_name=request.collection_name,
    )
    await app.tencent_upload_video()
    return account_file


async def login_baijiahao_account(account_name: str, headless: bool = True, qrcode_callback=None) -> dict:
    account_file = resolve_account_file("baijiahao", account_name)
    return await baijiahao_setup(str(account_file), handle=True, return_detail=True, headless=headless, qrcode_callback=qrcode_callback)


async def check_baijiahao_account(account_name: str) -> bool:
    account_file = resolve_account_file("baijiahao", account_name)
    if not account_file.exists():
        return False
    return await baijiahao_cookie_auth(str(account_file))


async def upload_baijiahao_video(request: BaijiahaoVideoUploadRequest) -> Path:
    account_file = resolve_account_file("baijiahao", request.account_name)
    is_ready = await baijiahao_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Baijiahao cookie is missing or expired: {account_file}. Run `sau baijiahao login --account {request.account_name}` first."
        )

    app = BaiJiaHaoVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        account_file=str(account_file),
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        collection_name=request.collection_name,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def login_alipay_account(account_name: str, headless: bool = True, qrcode_callback=None) -> dict:
    account_file = resolve_account_file("alipay", account_name)
    return await alipay_setup(str(account_file), handle=True, return_detail=True, headless=headless, qrcode_callback=qrcode_callback)


async def check_alipay_account(account_name: str) -> bool:
    account_file = resolve_account_file("alipay", account_name)
    if not account_file.exists():
        return False
    return await alipay_cookie_auth(str(account_file))


async def upload_alipay_video(request: AlipayVideoUploadRequest) -> Path:
    account_file = resolve_account_file("alipay", request.account_name)
    is_ready = await alipay_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Alipay cookie is missing or expired: {account_file}. Run `sau alipay login --account {request.account_name}` first."
        )

    app = AlipayVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        account_file=str(account_file),
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        collection_name=request.collection_name,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def login_weibo_account(account_name: str, headless: bool = True, qrcode_callback=None) -> dict:
    account_file = resolve_account_file("weibo", account_name)
    return await weibo_setup(str(account_file), handle=True, return_detail=True, headless=headless, qrcode_callback=qrcode_callback)


async def check_weibo_account(account_name: str) -> bool:
    account_file = resolve_account_file("weibo", account_name)
    if not account_file.exists():
        return False
    return await weibo_cookie_auth(str(account_file))


async def upload_weibo_video(request: WeiboVideoUploadRequest) -> Path:
    account_file = resolve_account_file("weibo", request.account_name)
    is_ready = await weibo_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Weibo cookie is missing or expired: {account_file}. Run `sau weibo login --account {request.account_name}` first."
        )

    app = WeiBoVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        account_file=str(account_file),
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        collection_name=request.collection_name,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def login_hupu_account(account_name: str, headless: bool = False, qrcode_callback=None) -> dict:
    account_file = resolve_account_file("hupu", account_name)
    return await hupu_setup(str(account_file), handle=True, return_detail=True, headless=headless, qrcode_callback=qrcode_callback)


async def check_hupu_account(account_name: str) -> bool:
    account_file = resolve_account_file("hupu", account_name)
    if not account_file.exists():
        return False
    return await hupu_cookie_auth(str(account_file))


async def upload_hupu_video(request: HupuVideoUploadRequest) -> Path:
    account_file = resolve_account_file("hupu", request.account_name)
    is_ready = await hupu_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Hupu cookie is missing or expired: {account_file}. Run `sau hupu login --account {request.account_name}` first."
        )

    app = HuPuVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        account_file=str(account_file),
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


def existing_file_path(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {value}")
    return path


def schedule_value(value: str):
    try:
        return parse_schedule(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid schedule '{value}'. Expected format: {SCHEDULE_FORMAT}"
        ) from exc


def add_runtime_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument("--headed", dest="headless", action="store_false", help="Run with browser UI")
    headless_group.add_argument("--headless", dest="headless", action="store_true", help="Run in headless mode")
    parser.set_defaults(headless=True)


def build_parser() -> argparse.ArgumentParser:
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
    parser = argparse.ArgumentParser(
        prog="sau",
        description="CLI for social-auto-upload.",
    )
    platform_parsers = parser.add_subparsers(dest="platform", required=True)
    article_parser = platform_parsers.add_parser("article", help="本地文章转换与主题预览，不登录或发表")
    article_actions = article_parser.add_subparsers(dest="action", required=True)
    article_actions.add_parser("themes", help="列出内置主题")
    article_actions.add_parser("setup", help="安装锁定版本的 Markdown 渲染依赖（需要 Node.js 22+）")
    article_render = article_actions.add_parser("render", help="将正文文件转换为可预览 HTML")
    article_render.add_argument("--content-file", required=True, type=existing_file_path, help="UTF-8 Markdown、HTML 或 TXT 文件")
    article_render.add_argument("--theme", choices=ARTICLE_THEMES, help="Markdown 主题，默认 default；HTML/TXT 不使用主题")
    article_render.add_argument("--output", required=True, type=Path, help="输出 .html 文件路径")
    article_render.add_argument("--overwrite", action="store_true", help="覆盖已有输出文件，不允许覆盖原稿")

    douyin_parser = platform_parsers.add_parser("douyin", help="Douyin operations")
    douyin_actions = douyin_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = douyin_actions.add_parser(action_name, help=f"Douyin {action_name}")
        action_parser.add_argument("--account", required=True, help="Douyin user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    upload_video_parser = douyin_actions.add_parser("upload-video", help="Upload one video to Douyin")
    upload_video_parser.add_argument("--account", required=True, help="Douyin user-defined account_name")
    upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    upload_video_parser.add_argument("--title", required=True, help="Video title")
    upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional 3:4 portrait thumbnail path")
    upload_video_parser.add_argument("--thumbnail-landscape", type=existing_file_path, help="Optional 4:3 landscape thumbnail path")
    upload_video_parser.add_argument("--thumbnail-portrait", type=existing_file_path, help="Optional 3:4 portrait thumbnail path")
    upload_video_parser.add_argument("--product-link", default="", help="Optional product link")
    upload_video_parser.add_argument("--product-title", default="", help="Optional product title")
    upload_video_parser.add_argument(
        "--declaration",
        help="Exact Douyin self-declaration option text; omitted means do not set one",
    )
    upload_video_parser.add_argument("--collection", default=None, help="Optional collection name to add the work into (must already exist)")
    add_runtime_flags(upload_video_parser)

    upload_note_parser = douyin_actions.add_parser("upload-note", help="Upload one note to Douyin")
    upload_note_parser.add_argument("--account", required=True, help="Douyin user-defined account_name")
    upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path, help="Image file paths")
    upload_note_parser.add_argument("--title", required=True, help="Note title")
    upload_note_parser.add_argument("--note", default="", help="Optional note content")
    upload_note_parser.add_argument("--notef", default="", help="Read note content from file (txt/md)")
    upload_note_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    upload_note_parser.add_argument("--bgm", default="", help="BGM music name to search and select")
    upload_note_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(upload_note_parser)

    kuaishou_parser = platform_parsers.add_parser("kuaishou", help="Kuaishou operations")
    kuaishou_actions = kuaishou_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = kuaishou_actions.add_parser(action_name, help=f"Kuaishou {action_name}")
        action_parser.add_argument("--account", required=True, help="Kuaishou user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    kuaishou_upload_video_parser = kuaishou_actions.add_parser("upload-video", help="Upload one video to Kuaishou")
    kuaishou_upload_video_parser.add_argument("--account", required=True, help="Kuaishou user-defined account_name")
    kuaishou_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    kuaishou_upload_video_parser.add_argument("--title", required=True, help="Video title")
    kuaishou_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    kuaishou_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    kuaishou_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    kuaishou_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional thumbnail path")
    kuaishou_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name to add the work into (must already exist)")
    add_runtime_flags(kuaishou_upload_video_parser)

    kuaishou_upload_note_parser = kuaishou_actions.add_parser("upload-note", help="Upload one note to Kuaishou")
    kuaishou_upload_note_parser.add_argument("--account", required=True, help="Kuaishou user-defined account_name")
    kuaishou_upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path, help="Image file paths")
    kuaishou_upload_note_parser.add_argument("--title", required=True, help="Note title")
    kuaishou_upload_note_parser.add_argument("--note", default="", help="Optional note content")
    kuaishou_upload_note_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    kuaishou_upload_note_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(kuaishou_upload_note_parser)

    xiaohongshu_parser = platform_parsers.add_parser("xiaohongshu", help="Xiaohongshu operations")
    xiaohongshu_actions = xiaohongshu_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = xiaohongshu_actions.add_parser(action_name, help=f"Xiaohongshu {action_name}")
        action_parser.add_argument("--account", required=True, help="Xiaohongshu user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    xiaohongshu_upload_video_parser = xiaohongshu_actions.add_parser("upload-video", help="Upload one video to Xiaohongshu")
    xiaohongshu_upload_video_parser.add_argument("--account", required=True, help="Xiaohongshu user-defined account_name")
    xiaohongshu_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    xiaohongshu_upload_video_parser.add_argument("--title", required=True, help="Video title")
    xiaohongshu_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    xiaohongshu_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    xiaohongshu_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    xiaohongshu_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional thumbnail path")
    add_runtime_flags(xiaohongshu_upload_video_parser)

    xiaohongshu_upload_note_parser = xiaohongshu_actions.add_parser("upload-note", help="Upload one note to Xiaohongshu")
    xiaohongshu_upload_note_parser.add_argument("--account", required=True, help="Xiaohongshu user-defined account_name")
    xiaohongshu_upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path, help="Image file paths")
    xiaohongshu_upload_note_parser.add_argument("--title", required=True, help="Note title")
    xiaohongshu_upload_note_parser.add_argument("--note", default="", help="Optional note content")
    xiaohongshu_upload_note_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    xiaohongshu_upload_note_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(xiaohongshu_upload_note_parser)

    bilibili_parser = platform_parsers.add_parser("bilibili", help="Bilibili operations")
    bilibili_actions = bilibili_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = bilibili_actions.add_parser(action_name, help=f"Bilibili {action_name}")
        action_parser.add_argument("--account", required=True, help="Bilibili user-defined account_name")

    bilibili_upload_video_parser = bilibili_actions.add_parser("upload-video", help="Upload one video to Bilibili")
    bilibili_upload_video_parser.add_argument("--account", required=True, help="Bilibili user-defined account_name")
    bilibili_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    bilibili_upload_video_parser.add_argument("--title", required=True, help="Video title")
    bilibili_upload_video_parser.add_argument("--desc", required=True, help="Video description")
    bilibili_upload_video_parser.add_argument("--tid", required=True, type=int, help="Bilibili category id")
    bilibili_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    bilibili_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional Bilibili cover image path")
    bilibili_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")

    tencent_parser = platform_parsers.add_parser("tencent", help="Tencent/WeChat Channels operations")
    tencent_actions = tencent_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = tencent_actions.add_parser(action_name, help=f"Tencent/WeChat Channels {action_name}")
        action_parser.add_argument("--account", required=True, help="Tencent user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    tencent_upload_video_parser = tencent_actions.add_parser("upload-video", help="Upload one video to WeChat Channels")
    tencent_upload_video_parser.add_argument("--account", required=True, help="Tencent user-defined account_name")
    tencent_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    tencent_upload_video_parser.add_argument("--title", required=True, help="Video title")
    tencent_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    tencent_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    tencent_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    tencent_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional 3:4 portrait thumbnail path")
    tencent_upload_video_parser.add_argument("--thumbnail-landscape", type=existing_file_path, help="Optional 4:3 landscape thumbnail path")
    tencent_upload_video_parser.add_argument("--thumbnail-portrait", type=existing_file_path, help="Optional 3:4 portrait thumbnail path")
    tencent_upload_video_parser.add_argument("--short-title", help="Optional WeChat Channels short title")
    tencent_upload_video_parser.add_argument("--category", help="Optional original content category")
    tencent_upload_video_parser.add_argument("--draft", action="store_true", help="Save as draft instead of publishing")
    tencent_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name to add the work into (must already exist)")
    add_runtime_flags(tencent_upload_video_parser)

    alipay_parser = platform_parsers.add_parser("alipay", help="Alipay life account operations")
    alipay_actions = alipay_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = alipay_actions.add_parser(action_name, help=f"Alipay {action_name}")
        action_parser.add_argument("--account", required=True, help="Alipay user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    alipay_upload_video_parser = alipay_actions.add_parser("upload-video", help="Upload one video to Alipay")
    alipay_upload_video_parser.add_argument("--account", required=True, help="Alipay user-defined account_name")
    alipay_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    alipay_upload_video_parser.add_argument("--title", required=True, help="Video title")
    alipay_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    alipay_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    alipay_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional cover image path")
    alipay_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name to add the work into (must already exist)")
    add_runtime_flags(alipay_upload_video_parser)

    # ── Weibo ──
    weibo_parser = platform_parsers.add_parser("weibo", help="Sina Weibo operations")
    weibo_actions = weibo_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = weibo_actions.add_parser(action_name, help=f"Weibo {action_name}")
        action_parser.add_argument("--account", required=True, help="Weibo user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    weibo_upload_video_parser = weibo_actions.add_parser("upload-video", help="Upload one video to Weibo")
    weibo_upload_video_parser.add_argument("--account", required=True, help="Weibo user-defined account_name")
    weibo_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    weibo_upload_video_parser.add_argument("--title", required=True, help="Video title (max 30 chars)")
    weibo_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    weibo_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    weibo_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional cover image path (<5MB)")
    weibo_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name")
    add_runtime_flags(weibo_upload_video_parser)

    # ── Hupu ──
    hupu_parser = platform_parsers.add_parser("hupu", help="Hupu (虎扑) operations")
    hupu_actions = hupu_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = hupu_actions.add_parser(action_name, help=f"Hupu {action_name}")
        action_parser.add_argument("--account", required=True, help="Hupu user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    hupu_upload_video_parser = hupu_actions.add_parser("upload-video", help="Upload one video to Hupu")
    hupu_upload_video_parser.add_argument("--account", required=True, help="Hupu user-defined account_name")
    hupu_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    hupu_upload_video_parser.add_argument("--title", required=True, help="Video title (4-40 chars)")
    hupu_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    hupu_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    hupu_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional cover image path")
    add_runtime_flags(hupu_upload_video_parser)

    facebook_parser = platform_parsers.add_parser("facebook", help="Facebook personal post operations")
    facebook_actions = facebook_parser.add_subparsers(dest="action", required=True)

    for action in ("verify", "delete"):
        post_parser = facebook_actions.add_parser(action, help="核对原作品" if action == "verify" else "核对原作品后移至垃圾箱（30 天后平台删除）")
        post_parser.add_argument("--account", required=True)
        post_parser.add_argument("--post-url", required=True, help="原作品的 Facebook 链接")
        post_parser.add_argument("--owner-id", required=True, help="原作品所属个人主页的数字 ID")
        post_parser.add_argument("--expected-text", required=True, help="原作品中用于交叉核验的正文")
        post_parser.add_argument("--result", type=Path, help="保存查询或删除结果 JSON")
        post_parser.add_argument("--from-trash", action="store_true", help="原作品已在垃圾箱，从垃圾箱核验")
        if action == "delete":
            post_parser.add_argument("--permanent", action="store_true", help="将核实的原作品从垃圾箱永久删除（无法恢复）")
        else:
            post_parser.add_argument("--deleted", action="store_true", help="只查询垃圾箱原 ID 是否已删除，不执行删除")
        post_parser.add_argument("--proxy", default=DEFAULT_FACEBOOK_PROXY)
        add_runtime_flags(post_parser)
        post_parser.set_defaults(headless=False)

    for action_name in ("login", "check"):
        action_parser = facebook_actions.add_parser(action_name, help=f"Facebook {action_name}")
        action_parser.add_argument("--account", required=True, help="Facebook user-defined account_name")
        action_parser.add_argument(
            "--proxy",
            default=DEFAULT_FACEBOOK_PROXY,
            help="浏览器代理地址；默认使用 http://127.0.0.1:10808，传空字符串表示直连",
        )
        if action_name == "login":
            add_runtime_flags(action_parser)
            # Facebook 登录必须在可见 Chrome 中完成，避免无头模式下用户看不到登录挑战。
            action_parser.set_defaults(headless=False)

    facebook_upload_video_parser = facebook_actions.add_parser(
        "upload-video", help="Upload one video to a Facebook personal post"
    )
    facebook_upload_video_parser.add_argument("--account", required=True, help="Facebook user-defined account_name")
    facebook_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    facebook_upload_video_parser.add_argument("--title", required=True, help="Post title, merged into Facebook caption")
    facebook_upload_video_parser.add_argument("--desc", default="", help="Optional post description")
    facebook_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    facebook_upload_video_parser.add_argument(
        "--proxy",
        default=DEFAULT_FACEBOOK_PROXY,
        help="浏览器代理地址；默认使用 http://127.0.0.1:10808，传空字符串表示直连",
    )
    add_runtime_flags(facebook_upload_video_parser)

    facebook_note = facebook_actions.add_parser("upload-note", help="向个人主页发布图片及正文")
    facebook_note.add_argument("--account", required=True)
    facebook_note.add_argument("--images", required=True, nargs="+", type=existing_file_path)
    facebook_note.add_argument("--title", required=True)
    facebook_note.add_argument("--note", default="")
    facebook_note.add_argument("--tags", default="")
    facebook_note.add_argument("--proxy", default=DEFAULT_FACEBOOK_PROXY)
    add_runtime_flags(facebook_note)
    facebook_note.set_defaults(headless=False)

    for meta_platform, meta_help in (
        ("facebook-page", "Facebook Page Business Suite operations"),
    ):
        meta_parser = platform_parsers.add_parser(meta_platform, help=meta_help)
        meta_actions = meta_parser.add_subparsers(dest="action", required=True)
        if meta_platform == "facebook-page":
            for action in ("verify", "delete"):
                post_parser = meta_actions.add_parser(action, help="按编号核对原作品" if action == "verify" else "核对编号后删除：定时作品永久删除，已发布作品移至垃圾箱")
                post_parser.add_argument("--account", required=True)
                post_parser.add_argument("--page-id", required=True)
                post_parser.add_argument("--page", required=True)
                post_parser.add_argument("--content-id", required=True)
                post_parser.add_argument("--expected-text", required=True)
                post_parser.add_argument("--scheduled", action="store_true", help="在已定时列表查询或取消定时作品")
                post_parser.add_argument("--result", type=Path)
                post_parser.add_argument("--proxy", default=META_PROXY)
                add_runtime_flags(post_parser)
                post_parser.set_defaults(headless=False)
        for action_name in ("login", "check"):
            action_parser = meta_actions.add_parser(action_name, help=f"{meta_platform} {action_name}")
            action_parser.add_argument("--account", required=True, help="Meta account name")
            action_parser.add_argument("--proxy", default=META_PROXY, help="代理地址，默认 http://127.0.0.1:10808")
            if action_name == "login":
                add_runtime_flags(action_parser)
                action_parser.set_defaults(headless=False)

        upload_video_parser = meta_actions.add_parser("upload-video", help=f"Upload a video to {meta_platform}")
        upload_video_parser.add_argument("--account", required=True)
        upload_video_parser.add_argument("--file", required=True, type=existing_file_path)
        upload_video_parser.add_argument("--title", required=True)
        upload_video_parser.add_argument("--desc", default="")
        upload_video_parser.add_argument("--tags", default="")
        upload_video_parser.add_argument("--page", default=None, help="Business Suite 发布主体名称；不传使用当前主体")
        upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"定时发布时间，格式 {schedule_help}")
        upload_video_parser.add_argument("--proxy", default=META_PROXY)
        upload_video_parser.add_argument("--result", type=Path, help="保存内容编号和发布结果 JSON")
        add_runtime_flags(upload_video_parser)
        upload_video_parser.set_defaults(headless=False)

        upload_note_parser = meta_actions.add_parser("upload-note", help=f"Upload images to {meta_platform}")
        upload_note_parser.add_argument("--account", required=True)
        upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path)
        upload_note_parser.add_argument("--title", required=True)
        upload_note_parser.add_argument("--note", default="")
        upload_note_parser.add_argument("--tags", default="")
        upload_note_parser.add_argument("--page", default=None, help="Business Suite 发布主体名称；不传使用当前主体")
        upload_note_parser.add_argument("--schedule", type=schedule_value, help=f"定时发布时间，格式 {schedule_help}")
        upload_note_parser.add_argument("--proxy", default=META_PROXY)
        upload_note_parser.add_argument("--result", type=Path, help="保存内容编号和发布结果 JSON")
        add_runtime_flags(upload_note_parser)
        upload_note_parser.set_defaults(headless=False)

    youtube_parser = platform_parsers.add_parser("youtube", help="YouTube operations")
    youtube_actions = youtube_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = youtube_actions.add_parser(action_name, help=f"YouTube {action_name}")
        action_parser.add_argument("--account", required=True, help="YouTube user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    youtube_upload_video_parser = youtube_actions.add_parser("upload-video", help="Upload one video to YouTube")
    youtube_upload_video_parser.add_argument("--account", required=True, help="YouTube user-defined account_name")
    youtube_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    youtube_upload_video_parser.add_argument("--title", required=True, help="Video title (<=100 chars)")
    youtube_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    youtube_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    youtube_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional thumbnail image path")
    youtube_upload_video_parser.add_argument("--playlist", help="Optional playlist name to add the video to (for series)")
    youtube_upload_video_parser.add_argument(
        "--visibility", default="public", choices=["public", "unlisted", "private"], help="Video visibility")
    youtube_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(youtube_upload_video_parser)

    baijiahao_parser = platform_parsers.add_parser("baijiahao", help="Baidu Baijiahao operations")
    baijiahao_actions = baijiahao_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = baijiahao_actions.add_parser(action_name, help=f"Baijiahao {action_name}")
        action_parser.add_argument("--account", required=True, help="Baijiahao user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    baijiahao_upload_video_parser = baijiahao_actions.add_parser("upload-video", help="Upload one video to Baijiahao")
    baijiahao_upload_video_parser.add_argument("--account", required=True, help="Baijiahao user-defined account_name")
    baijiahao_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    baijiahao_upload_video_parser.add_argument("--title", required=True, help="Video title")
    baijiahao_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    baijiahao_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    baijiahao_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional cover image path")
    baijiahao_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name")
    add_runtime_flags(baijiahao_upload_video_parser)

    dayu_parser = platform_parsers.add_parser("dayu", help="Dayu (大鱼号) video publishing and verification")
    dayu_actions = dayu_parser.add_subparsers(dest="action", required=True)
    dayu_login = dayu_actions.add_parser("login", help="Log in manually with visible Chrome")
    dayu_login.add_argument("--account", required=True, help="Local account alias")
    dayu_login.add_argument("--expected-name", help="Expected name displayed by Dayu")
    dayu_login.add_argument("--timeout", type=int, default=600, help="Login timeout in seconds")
    dayu_check = dayu_actions.add_parser("check", help="Check login and bound Dayu identity")
    dayu_check.add_argument("--account", required=True)
    dayu_upload = dayu_actions.add_parser("upload-video", help="Publish a video; succeed when Dayu confirms submission")
    dayu_upload.add_argument("--account", required=True)
    dayu_upload.add_argument("--file", required=True, type=existing_file_path)
    dayu_upload.add_argument("--title", required=True, help="Title, 5-60 Chinese character units")
    dayu_upload.add_argument("--desc", default="")
    dayu_upload.add_argument("--tags", default="", help="Comma-separated tags")
    dayu_upload.add_argument("--category", required=True, choices=DAYU_VIDEO_CATEGORIES, help="视频分类，按页面选项选择")
    dayu_upload.add_argument("--source", required=True, choices=DAYU_SOURCE_TYPES, help="按实际内容选择信息来源")
    dayu_upload.add_argument("--source-url", default="", help="转载时必填的 http/https 原文链接")
    dayu_upload.add_argument("--thumbnail", required=True, type=existing_file_path)
    dayu_upload.add_argument("--schedule", type=schedule_value,
                            help=f"{schedule_help}，北京时间，{DAYU_SCHEDULE_MIN_HOURS}小时后至{DAYU_SCHEDULE_MAX_DAYS}天内，分钟为{DAYU_SCHEDULE_STEP_MINUTES}的倍数")
    dayu_upload.add_argument("--prepare-only", action="store_true", help="Upload and fill only; do not click publish")
    dayu_upload.add_argument("--upload-timeout", type=int, default=600, help="Upload/processing timeout in seconds")
    add_runtime_flags(dayu_upload)
    dayu_article = dayu_actions.add_parser("upload-article", help="从正文文件发表图文，平台确认发表后返回成功")
    dayu_article.add_argument("--account", required=True, help="已登录的本地账号名称")
    dayu_article.add_argument("--title", required=True, help="图文标题，5–50字")
    dayu_article.add_argument("--content-file", required=True, type=existing_file_path, help="UTF-8 HTML、Markdown 或 TXT 正文文件")
    dayu_article.add_argument("--theme", choices=ARTICLE_THEMES, help="Markdown 渲染主题，默认 default；按大鱼号兼容排版发表")
    dayu_article.add_argument("--source", required=True, choices=DAYU_SOURCE_TYPES, help="按实际内容选择信息来源")
    dayu_article.add_argument("--source-url", default="", help="转载时必填的 http/https 原文链接")
    dayu_article.add_argument("--author", help="选填作者名称；省略时沿用网页已有值")
    dayu_article.add_argument("--cover-indices", nargs="+", type=int, help="选填1或3个正文图片序号（从1开始），对应单封面或三封面")
    dayu_article.add_argument("--schedule", type=schedule_value,
                             help=f"{schedule_help}，北京时间，{DAYU_SCHEDULE_MIN_HOURS}小时后至{DAYU_SCHEDULE_MAX_DAYS}天内，分钟为{DAYU_SCHEDULE_STEP_MINUTES}的倍数")
    dayu_article.add_argument("--prepare-only", action="store_true", help="上传和填写后结束，不发表")
    dayu_article.add_argument("--upload-timeout", type=int, default=600, help="每张图片上传等待秒数")
    add_runtime_flags(dayu_article)
    dayu_verify = dayu_actions.add_parser("verify", help="Check an existing publication without uploading again")
    dayu_verify.add_argument("--account", required=True)
    dayu_verify.add_argument("--type", choices=("video", "article"), help="作品类型；使用结果文件时自动识别，其余情况默认为video")
    dayu_target = dayu_verify.add_mutually_exclusive_group(required=True)
    dayu_target.add_argument("--content-id", help="Published content_id returned by Dayu")
    dayu_target.add_argument("--origin-id", help="Draft ID captured before confirming publication")
    dayu_target.add_argument("--result", type=existing_file_path, help="Saved Dayu result JSON to recover")
    dayu_verify.add_argument("--public", action="store_true", help="额外等待审核后检查公开正文或播放；不影响发表命令的成功判定")
    dayu_verify.add_argument("--timeout", type=int, default=60)
    add_runtime_flags(dayu_verify)

    xueqiu_parser = platform_parsers.add_parser("xueqiu", help="雪球创作者中心图文长文")
    xueqiu_actions = xueqiu_parser.add_subparsers(dest="action", required=True)
    xueqiu_login = xueqiu_actions.add_parser("login", help="在可见 Chrome 中登录并保存本地会话")
    xueqiu_login.add_argument("--account", required=True, help="本地账号别名")
    xueqiu_login.add_argument("--expected-name", help="期望的雪球昵称")
    xueqiu_login.add_argument("--timeout", type=int, default=600, help="登录等待秒数")
    xueqiu_check = xueqiu_actions.add_parser("check", help="检查登录状态及绑定用户 ID")
    xueqiu_check.add_argument("--account", required=True)
    add_runtime_flags(xueqiu_check)
    xueqiu_check.set_defaults(headless=False)
    xueqiu_verify = xueqiu_actions.add_parser("verify", help="根据结果文件查询原作品，不重复发表")
    xueqiu_verify.add_argument("--account", required=True)
    xueqiu_verify.add_argument("--result", required=True, type=existing_file_path)
    add_runtime_flags(xueqiu_verify)
    xueqiu_verify.set_defaults(headless=False)
    xueqiu_article = xueqiu_actions.add_parser("upload-article", help="HTML/Markdown/TXT 长文及原位置配图")
    xueqiu_article.add_argument("--account", required=True)
    xueqiu_article.add_argument("--title", required=True, help="非空单行标题")
    xueqiu_article.add_argument("--content-file", required=True, type=existing_file_path, help="UTF-8 HTML/Markdown/TXT；图片由原稿位置决定")
    xueqiu_article.add_argument("--cover", type=existing_file_path, help="独立封面；采用平台默认裁剪区域")
    xueqiu_article.add_argument("--visibility", choices=XUEQIU_VISIBILITY, default="公开", help="分享范围")
    xueqiu_article.add_argument("--declaration", choices=XUEQIU_DECLARATIONS, required=True, help="按实际创作方式选择")
    xueqiu_article.add_argument("--prepare-only", action="store_true", help="检查预览后结束；雪球会自动保存远端草稿")
    add_runtime_flags(xueqiu_article)
    # 本机真实验收使用可见 Chrome；headless 访问曾触发下载/访问拦截，用户可显式选择。
    xueqiu_article.set_defaults(headless=False)

    return parser


async def dispatch(args: argparse.Namespace) -> int:
    if args.platform == "xueqiu":
        account_file = resolve_account_file("xueqiu", args.account)
        if args.action == "login":
            result = await login_xueqiu_account(account_file, args.expected_name, args.timeout)
        elif args.action == "check":
            valid = await check_xueqiu_account(account_file, args.headless)
            print("valid" if valid else "invalid")
            return 0 if valid else 1
        elif args.action == "verify":
            result = await verify_xueqiu_result(account_file, args.result, args.headless)
        else:
            app = XueqiuArticle(
                title=args.title, content_file=args.content_file, account_file=account_file,
                visibility=args.visibility, declaration=args.declaration,
                prepare_only=args.prepare_only, headless=args.headless, debug=args.debug,
                cover=args.cover,
            )
            result = await app.main()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.platform == "article":
        if args.action == "setup":
            setup_article_renderer()
            print("文章渲染依赖已安装")
        elif args.action == "themes":
            for name, description in ARTICLE_THEMES.items():
                print(f"{name}\t{description}")
        else:
            print(json.dumps(render_article_file(args.content_file, args.output, args.theme, args.overwrite), ensure_ascii=False))
        return 0
    if args.platform == "dayu":
        account_file = resolve_account_file("dayu", args.account)
        if args.action == "login":
            if args.timeout <= 0:
                raise ValueError("登录期限必须大于 0 秒")
            result = await login_dayu_account(account_file, args.expected_name, args.timeout)
        elif args.action == "check":
            valid = await check_dayu_account(account_file)
            print("valid" if valid else "invalid")
            return 0 if valid else 1
        elif args.action == "upload-video":
            app = DayuVideo(
                title=args.title, file_path=args.file, tags=parse_tags(args.tags),
                account_file=account_file, thumbnail_path=args.thumbnail, category=args.category,
                source=args.source, desc=args.desc, headless=args.headless, debug=args.debug,
                prepare_only=args.prepare_only, upload_timeout=args.upload_timeout,
                source_url=args.source_url, schedule=args.schedule,
            )
            result = await app.main()
        elif args.action == "upload-article":
            app = DayuArticle(
                title=args.title, content_file=args.content_file, account_file=account_file,
                source=args.source, source_url=args.source_url, author=args.author,
                theme=args.theme, schedule=args.schedule,
                cover_indices=args.cover_indices, headless=args.headless, debug=args.debug,
                prepare_only=args.prepare_only, upload_timeout=args.upload_timeout,
            )
            result = await app.main()
        elif args.action == "verify":
            if args.timeout <= 0:
                raise ValueError("核验期限必须大于 0 秒")
            saved = json.loads(args.result.read_text(encoding="utf-8")) if args.result else {}
            expected = load_dayu_identity(account_file)
            if saved and saved.get("identity", {}).get("wmid") != expected["wmid"]:
                raise RuntimeError("结果文件与所选大鱼号主体不一致")
            kind = args.type or saved.get("type", "video")
            if saved.get("type") and saved["type"] != kind:
                raise ValueError("指定作品类型与结果文件不一致")
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=args.headless,
                )
                try:
                    context = await browser.new_context(storage_state=str(account_file))
                    page = await context.new_page()
                    await page.goto(DAYU_HOME_URL, wait_until="domcontentloaded", timeout=45000)
                    identity = await read_dayu_identity(page)
                    if identity["wmid"] != expected["wmid"]:
                        raise RuntimeError("核验时大鱼号主体与账号绑定不一致")
                    if kind == "article":
                        result = await verify_dayu_article(
                            context, browser, identity,
                            content_id=args.content_id or saved.get("content_id"),
                            origin_id=args.origin_id or saved.get("origin_id"),
                            title=saved.get("title"), timeout=args.timeout, manifest=saved.get("manifest"), public=args.public,
                            schedule=saved.get("schedule"),
                        )
                    else:
                        result = await verify_dayu_video(
                            context, browser, identity,
                            content_id=args.content_id or saved.get("content_id"),
                            origin_id=args.origin_id or saved.get("origin_id"),
                            title=saved.get("title"), timeout=args.timeout, public=args.public,
                            schedule=saved.get("schedule"),
                        )
                    if args.result:
                        saved.update(result)
                        saved.pop("error", None)
                        args.result.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
                finally:
                    await browser.close()
        else:
            raise RuntimeError(f"Unsupported Dayu action: {args.action}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.platform == "douyin":
        if args.action == "login":
            result = await login_douyin_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Douyin login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_douyin_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        publish_strategy = DOUYIN_PUBLISH_STRATEGY_SCHEDULED if args.schedule else DOUYIN_PUBLISH_STRATEGY_IMMEDIATE

        if args.action == "upload-video":
            request = DouyinVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
                thumbnail_landscape_file=args.thumbnail_landscape,
                thumbnail_portrait_file=args.thumbnail_portrait,
                product_link=args.product_link,
                product_title=args.product_title,
                declaration=args.declaration,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
                collection_name=args.collection,
            )
            await upload_video(request)
            print(f"Douyin video upload submitted: {request.video_file}")
            return 0

        if args.action == "upload-note":
            # 如果指定了 --notef，读取文件内容作为 note
            note_content = args.note
            if args.notef:
                note_file = Path(args.notef)
                if not note_file.exists():
                    print(f"错误：文件不存在: {note_file}", file=sys.stderr)
                    return 1
                note_content = note_file.read_text(encoding="utf-8")

            request = DouyinNoteUploadRequest(
                account_name=args.account,
                image_files=parse_image_files(args.images),
                title=args.title,
                note=note_content,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
                bgm=args.bgm or "",
            )
            await upload_note(request)
            print(f"Douyin note upload submitted: {len(request.image_files)} images")
            return 0

        raise RuntimeError(f"Unsupported Douyin action: {args.action}")

    if args.platform == "kuaishou":
        if args.action == "login":
            result = await login_kuaishou_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Kuaishou login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_kuaishou_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        publish_strategy = KUAISHOU_PUBLISH_STRATEGY_SCHEDULED if args.schedule else KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE

        if args.action == "upload-video":
            request = KuaishouVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
                collection_name=args.collection,
            )
            await upload_kuaishou_video(request)
            print(f"Kuaishou video upload submitted: {request.video_file}")
            return 0

        if args.action == "upload-note":
            request = KuaishouNoteUploadRequest(
                account_name=args.account,
                image_files=parse_image_files(args.images),
                title=args.title,
                note=args.note,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_kuaishou_note(request)
            print(f"Kuaishou note upload submitted: {len(request.image_files)} images")
            return 0

        raise RuntimeError(f"Unsupported Kuaishou action: {args.action}")

    if args.platform == "xiaohongshu":
        if args.action == "login":
            result = await login_xiaohongshu_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Xiaohongshu login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_xiaohongshu_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        publish_strategy = (
            XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED if args.schedule else XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
        )

        if args.action == "upload-video":
            parsed_tags = parse_tags(args.tags)
            if len(parsed_tags) > 10:
                print(f"错误：小红书标签最多 10 个，当前提供了 {len(parsed_tags)} 个: {parsed_tags}", file=sys.stderr)
                return 1
            request = XiaohongshuVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parsed_tags,
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_xiaohongshu_video(request)
            print(f"Xiaohongshu video upload submitted: {request.video_file}")
            return 0

        if args.action == "upload-note":
            parsed_tags = parse_tags(args.tags)
            if len(parsed_tags) > 10:
                print(f"错误：小红书标签最多 10 个，当前提供了 {len(parsed_tags)} 个: {parsed_tags}", file=sys.stderr)
                return 1
            request = XiaohongshuNoteUploadRequest(
                account_name=args.account,
                image_files=parse_image_files(args.images),
                title=args.title,
                note=args.note,
                tags=parsed_tags,
                publish_date=args.schedule or 0,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_xiaohongshu_note(request)
            print(f"Xiaohongshu note upload submitted: {len(request.image_files)} images")
            return 0

        raise RuntimeError(f"Unsupported Xiaohongshu action: {args.action}")

    if args.platform == "bilibili":
        if args.action == "login":
            result = await login_bilibili_account(args.account)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Bilibili login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_bilibili_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = BilibiliVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tid=args.tid,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
            )
            await upload_bilibili_video(request)
            print(f"Bilibili video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Bilibili action: {args.action}")

    if args.platform == "tencent":
        if args.action == "login":
            result = await login_tencent_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Tencent/WeChat Channels login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_tencent_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        publish_strategy = TENCENT_PUBLISH_STRATEGY_SCHEDULED if args.schedule else TENCENT_PUBLISH_STRATEGY_IMMEDIATE

        if args.action == "upload-video":
            request = TencentVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
                thumbnail_landscape_file=args.thumbnail_landscape,
                thumbnail_portrait_file=args.thumbnail_portrait,
                short_title=args.short_title,
                category=args.category,
                is_draft=args.draft,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
                collection_name=args.collection,
            )
            await upload_tencent_video(request)
            print(f"Tencent/WeChat Channels video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Tencent/WeChat Channels action: {args.action}")

    if args.platform == "alipay":
        if args.action == "login":
            result = await login_alipay_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Alipay login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_alipay_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = AlipayVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                collection_name=args.collection,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_alipay_video(request)
            print(f"Alipay video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Alipay action: {args.action}")

    if args.platform == "weibo":
        if args.action == "login":
            result = await login_weibo_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Weibo login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_weibo_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = WeiboVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                collection_name=args.collection,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_weibo_video(request)
            print(f"Weibo video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Weibo action: {args.action}")

    if args.platform == "hupu":
        if args.action == "login":
            result = await login_hupu_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Hupu login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_hupu_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = HupuVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_hupu_video(request)
            print(f"Hupu video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Hupu action: {args.action}")

    if args.platform == "youtube":
        if args.action == "login":
            result = await login_youtube_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"YouTube login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_youtube_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = YouTubeVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                playlist=args.playlist,
                visibility=args.visibility,
                schedule=args.schedule or 0,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_youtube_video(request)
            print(f"YouTube video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported YouTube action: {args.action}")

    if args.platform == "facebook":
        if args.action == "upload-note":
            for image in args.images:
                BaseVideoUploader.validate_image_file(image)
            app = FacebookPost(args.title, args.images, args.note, parse_tags(args.tags),
                               resolve_account_file("facebook", args.account), proxy=args.proxy, headless=args.headless)
            await app.main()
            print("Facebook image post submitted")
            return 0
        if args.action in {"verify", "delete"}:
            result = await facebook_post_action(
                resolve_account_file("facebook", args.account), post_url=args.post_url,
                owner_id=args.owner_id, expected_text=args.expected_text,
                delete=args.action == "delete", proxy=args.proxy, headless=args.headless,
                permanent=getattr(args, "permanent", False), from_trash=args.from_trash,
                deleted=getattr(args, "deleted", False),
            )
            if args.result:
                args.result.parent.mkdir(parents=True, exist_ok=True)
                args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.action == "login":
            result = await login_facebook_account(
                args.account, headless=args.headless, proxy=args.proxy
            )
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Facebook login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_facebook_account(args.account, proxy=args.proxy)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = FacebookVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                proxy=args.proxy,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_facebook_video(request)
            print(f"Facebook video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Facebook action: {args.action}")

    if args.platform == "facebook-page":
        if args.platform == "facebook-page" and args.action in {"verify", "delete"}:
            result = await meta_post_action(
                resolve_account_file(args.platform, args.account), page_id=args.page_id, page_name=args.page,
                content_id=args.content_id, expected_text=args.expected_text, scheduled=args.scheduled,
                delete=args.action == "delete", proxy=args.proxy, headless=args.headless,
            )
            if args.result:
                args.result.parent.mkdir(parents=True, exist_ok=True)
                args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.action == "login":
            result = await login_meta_account(args.platform, args.account, headless=args.headless, proxy=args.proxy)
            if not result["success"]:
                raise RuntimeError(result.get("message", f"{args.platform} login failed"))
            print(f"{args.platform} login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_meta_account(args.platform, args.account, proxy=args.proxy)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action in {"upload-video", "upload-note"}:
            request = MetaUploadRequest(
                platform=args.platform,
                account_name=args.account,
                title=args.title,
                description=args.desc if args.action == "upload-video" else args.note,
                tags=parse_tags(args.tags),
                video_file=args.file if args.action == "upload-video" else None,
                image_files=parse_image_files(args.images) if args.action == "upload-note" else None,
                schedule=args.schedule or 0,
                page_name=args.page,
                result_file=args.result,
                proxy=args.proxy,
                debug=args.debug,
                headless=args.headless,
            )
            result = await upload_meta_content(request)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        raise RuntimeError(f"Unsupported {args.platform} action: {args.action}")

    if args.platform == "baijiahao":
        if args.action == "login":
            result = await login_baijiahao_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Baijiahao login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_baijiahao_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = BaijiahaoVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                collection_name=args.collection,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_baijiahao_video(request)
            print(f"Baijiahao video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Baijiahao action: {args.action}")

    raise RuntimeError(f"Unsupported platform: {args.platform}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return asyncio.run(dispatch(args))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
