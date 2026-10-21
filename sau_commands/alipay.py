"""alipay 的命令参数与执行逻辑。"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from uploader.alipay_uploader.main import AlipayVideo, alipay_setup, cookie_auth as alipay_cookie_auth
from sau_commands.arguments import (
    SCHEDULE_FORMAT,
    add_runtime_flags,
    existing_file_path,
    parse_tags,
    resolve_account_file,
)


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
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


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
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
