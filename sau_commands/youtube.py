"""youtube 的命令参数与执行逻辑。"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uploader.youtube_uploader.main import YouTubeVideo, cookie_auth as youtube_cookie_auth, youtube_setup
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


async def login_youtube_account(account_name: str, headless: bool = False) -> dict:
    account_file = resolve_account_file("youtube", account_name)
    return await youtube_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_youtube_account(account_name: str) -> bool:
    account_file = resolve_account_file("youtube", account_name)
    if not account_file.exists():
        return False
    return await youtube_cookie_auth(str(account_file))


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


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
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
