from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from conf import BASE_DIR
from uploader.douyin_uploader.main import (
    DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
    DOUYIN_PUBLISH_STRATEGY_SCHEDULED,
    DouYinNote,
    DouYinVideo,
    cookie_auth,
    douyin_setup,
)

SCHEDULE_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(slots=True)
class DouyinVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
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
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


def resolve_runtime_home() -> Path:
    return Path(BASE_DIR)


def resolve_account_file(account_name: str) -> Path:
    account_file = resolve_runtime_home() / "cookies" / f"douyin_{account_name}.json"
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


async def login_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file(account_name)
    return await douyin_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_account(account_name: str) -> bool:
    account_file = resolve_account_file(account_name)
    if not account_file.exists():
        return False
    return await cookie_auth(str(account_file))


async def upload_video(request: DouyinVideoUploadRequest) -> Path:
    account_file = resolve_account_file(request.account_name)
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
    account_file = resolve_account_file(request.account_name)
    is_ready = await douyin_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Douyin cookie is missing or expired: {account_file}. Run `sau douyin login --account {request.account_name}` first."
        )

    app = DouYinNote(
        image_paths=[str(path) for path in request.image_files],
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
        action_parser.add_argument("--account", required=True, help="Douyin account alias")
        if action_name == "login":
            add_runtime_flags(action_parser)

    upload_video_parser = douyin_actions.add_parser("upload-video", help="Upload one video to Douyin")
    upload_video_parser.add_argument("--account", required=True, help="Douyin account alias")
    upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    upload_video_parser.add_argument("--title", required=True, help="Video title")
    upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional thumbnail path")
    upload_video_parser.add_argument("--product-link", default="", help="Optional product link")
    upload_video_parser.add_argument("--product-title", default="", help="Optional product title")
    add_runtime_flags(upload_video_parser)

    upload_note_parser = douyin_actions.add_parser("upload-note", help="Upload one note to Douyin")
    upload_note_parser.add_argument("--account", required=True, help="Douyin account alias")
    upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path, help="Image file paths")
    upload_note_parser.add_argument("--note", required=True, help="Note content")
    upload_note_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    upload_note_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(upload_note_parser)
    return parser


async def dispatch(args: argparse.Namespace) -> int:
    if args.platform != "douyin":
        raise RuntimeError(f"Unsupported platform: {args.platform}")

    if args.action == "login":
        result = await login_account(args.account, headless=args.headless)
        if not result["success"]:
            raise RuntimeError(result["message"])
        print(f"Douyin login flow completed: {result['account_file']}")
        return 0

    if args.action == "check":
        is_valid = await check_account(args.account)
        print("valid" if is_valid else "invalid")
        return 0 if is_valid else 1

    publish_strategy = DOUYIN_PUBLISH_STRATEGY_SCHEDULED if args.schedule else DOUYIN_PUBLISH_STRATEGY_IMMEDIATE

    if args.action == "upload-video":
        request = DouyinVideoUploadRequest(
            account_name=args.account,
            video_file=args.file,
            title=args.title,
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
