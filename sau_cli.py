from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from conf import BASE_DIR
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
from uploader.xiaohongshu_uploader.main import (
    XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
    XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
    XiaoHongShuNote,
    XiaoHongShuVideo,
    cookie_auth as xiaohongshu_cookie_auth,
    xiaohongshu_setup,
)

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
    product_link: str = ""
    product_title: str = ""
    publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


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
        thumbnail_portrait_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        productLink=request.product_link,
        productTitle=request.product_title,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
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
    if isinstance(request.publish_date, datetime):
        arguments.extend(["--dtime", str(int(request.publish_date.timestamp()))])

    result = run_biliup_command(arguments)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "").strip() or "Bilibili upload failed")
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
    upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional thumbnail path")
    upload_video_parser.add_argument("--product-link", default="", help="Optional product link")
    upload_video_parser.add_argument("--product-title", default="", help="Optional product title")
    add_runtime_flags(upload_video_parser)

    upload_note_parser = douyin_actions.add_parser("upload-note", help="Upload one note to Douyin")
    upload_note_parser.add_argument("--account", required=True, help="Douyin user-defined account_name")
    upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path, help="Image file paths")
    upload_note_parser.add_argument("--title", required=True, help="Note title")
    upload_note_parser.add_argument("--note", default="", help="Optional note content")
    upload_note_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
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
    bilibili_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    return parser


async def dispatch(args: argparse.Namespace) -> int:
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
                product_link=args.product_link,
                product_title=args.product_title,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_video(request)
            print(f"Douyin video upload submitted: {request.video_file}")
            return 0

        if args.action == "upload-note":
            request = DouyinNoteUploadRequest(
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
            request = XiaohongshuVideoUploadRequest(
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
            )
            await upload_xiaohongshu_video(request)
            print(f"Xiaohongshu video upload submitted: {request.video_file}")
            return 0

        if args.action == "upload-note":
            request = XiaohongshuNoteUploadRequest(
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
            )
            await upload_bilibili_video(request)
            print(f"Bilibili video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Bilibili action: {args.action}")

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
