"""tencent 的命令参数与执行逻辑。"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uploader.tencent_uploader.main import (
    TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
    TENCENT_PUBLISH_STRATEGY_SCHEDULED,
    TencentVideo,
    cookie_auth as tencent_cookie_auth,
    tencent_setup,
)
from sau_commands.arguments import (
    SCHEDULE_FORMAT,
    add_runtime_flags,
    existing_file_path,
    parse_tags,
    resolve_account_file,
    schedule_value,
)


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
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


async def login_tencent_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("tencent", account_name)
    return await tencent_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_tencent_account(account_name: str) -> bool:
    account_file = resolve_account_file("tencent", account_name)
    if not account_file.exists():
        return False
    return await tencent_cookie_auth(str(account_file))


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


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
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
