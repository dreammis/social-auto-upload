"""bilibili 的命令参数与执行逻辑。"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uploader.bilibili_uploader.runtime import run_biliup_command
from sau_commands.arguments import (
    SCHEDULE_FORMAT,
    existing_file_path,
    has_interactive_terminal,
    parse_tags,
    resolve_account_file,
    schedule_value,
)


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
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


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
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
