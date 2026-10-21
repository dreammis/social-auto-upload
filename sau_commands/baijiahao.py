"""baijiahao 的命令参数与执行逻辑。"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from uploader.baijiahao_uploader.main import (
    BaiJiaHaoVideo,
    baijiahao_setup,
    cookie_auth as baijiahao_cookie_auth,
)
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


async def run(args):
    """执行本平台命令；发布结果由平台实现核验。"""
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
