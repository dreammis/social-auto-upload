"""uploadpost（Upload-Post API 版海外平台发布）的命令参数与执行逻辑。"""
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uploader.uploadpost_uploader.main import (
    SUPPORTED_PLATFORMS,
    UploadPostUncertain,
    UploadPostVideo,
    check_credentials,
    get_status,
)
from sau_commands.arguments import (
    SCHEDULE_FORMAT,
    existing_file_path,
    parse_tags,
    schedule_value,
)

# 退出码：0 已受理 / 已完成；1 确定失败；2 仍在处理或部分完成；4 结果不确定（不要重发）
EXIT_PENDING = 2
EXIT_UNCERTAIN = 4


def register(platform_parsers):
    """声明本平台命令、参数及合法选项。"""
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
    uploadpost_parser = platform_parsers.add_parser(
        "uploadpost",
        help="Upload-Post operations (API publishing to TikTok/Instagram/YouTube/X/..., no browser)",
    )
    uploadpost_actions = uploadpost_parser.add_subparsers(dest="action", required=True)

    uploadpost_actions.add_parser("check", help="Check the Upload-Post API key and profile in conf.py")
    uploadpost_actions.add_parser("platforms", help="List the platforms Upload-Post can publish to")

    status_parser = uploadpost_actions.add_parser("status", help="Show the per-platform result of one upload")
    status_parser.add_argument("--id", dest="request_id", required=True, help="request_id printed by upload-video")

    upload_parser = uploadpost_actions.add_parser(
        "upload-video", help="Publish one video to several platforms in a single request")
    upload_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    upload_parser.add_argument("--title", default="", help="Video title (required for youtube and reddit)")
    upload_parser.add_argument(
        "--platforms", required=True,
        help=f"Comma-separated platforms. Supported: {', '.join(SUPPORTED_PLATFORMS)}")
    upload_parser.add_argument("--desc", default="", help="Optional description (YouTube/LinkedIn/Facebook/Pinterest)")
    upload_parser.add_argument("--tags", default="", help="Comma-separated tags, appended to the title as hashtags")
    upload_parser.add_argument(
        "--schedule", type=schedule_value,
        help=f"Schedule time in {schedule_help}, local time in --timezone")
    upload_parser.add_argument(
        "--timezone", default=None,
        help="IANA timezone for --schedule, e.g. Asia/Shanghai (default UTC)")


@dataclass(slots=True)
class UploadPostVideoUploadRequest:
    video_file: Path
    title: str
    platforms: list[str]
    description: str = ""
    tags: list[str] = field(default_factory=list)
    publish_date: datetime | int = 0
    timezone: str | None = None


async def check_uploadpost_credentials() -> bool:
    return await check_credentials()


async def upload_uploadpost_video(request: UploadPostVideoUploadRequest) -> dict:
    app = UploadPostVideo(
        request.title,
        str(request.video_file),
        request.tags,
        request.platforms,
        publish_date=request.publish_date,
        description=request.description,
        timezone=request.timezone,
    )
    return await app.main()


def describe_platform_result(item: dict) -> str:
    """把单个平台结果归为：已发布 / 草稿 / 处理中 / 失败 / 未知。"""
    platform = item.get("platform", "?")
    state = item.get("status")
    if item.get("fallback_to_inbox"):
        return f"{platform}: 草稿（已送到 TikTok 收件箱，需在 App 内手动发布）"
    if item.get("skipped") or state == "skipped":
        return f"{platform}: 跳过（profile 未绑定该平台）"
    if state in ("queued", "processing", "retryable"):
        return f"{platform}: 处理中（{state}）"
    if state is None and str(item.get("message", "")).strip().lower() in ("queued", "processing"):
        return f"{platform}: 处理中（{item['message']}）"
    if state == "failed" or item.get("success") is False:
        return f"{platform}: 失败 - {item.get('error') or item.get('message') or ''}".rstrip(" -")
    if state == "completed" or item.get("success") is True:
        link = item.get("post_url") or item.get("url") or item.get("post_id")
        return f"{platform}: 已发布" + (f" {link}" if link else "（未返回链接，请到平台核对）")
    return f"{platform}: 未知（响应里没有结果状态）"


def status_exit_code(result: dict) -> int:
    state = result.get("status")
    if state == "completed":
        return 0
    if state == "failed":
        return 1
    if state in ("not_found", "unknown", None):
        return EXIT_UNCERTAIN
    return EXIT_PENDING


async def run(args):
    """执行本平台命令。"""
    if args.action == "platforms":
        print("\n".join(SUPPORTED_PLATFORMS))
        return 0

    if args.action == "check":
        is_valid = await check_uploadpost_credentials()
        print("valid" if is_valid else "invalid")
        return 0 if is_valid else 1

    if args.action == "status":
        result = await get_status(args.request_id)
        print(f"request_id={args.request_id} status={result.get('status')}")
        for item in result.get("results") or []:
            if isinstance(item, dict):
                print("  " + describe_platform_result(item))
        if result.get("message"):
            print(f"  {result['message']}")
        return status_exit_code(result)

    if args.action == "upload-video":
        request = UploadPostVideoUploadRequest(
            video_file=args.file,
            title=args.title,
            platforms=parse_tags(args.platforms),
            description=args.desc,
            tags=parse_tags(args.tags),
            publish_date=args.schedule or 0,
            timezone=args.timezone,
        )
        try:
            result = await upload_uploadpost_video(request)
        except UploadPostUncertain as exc:
            print(str(exc), file=sys.stderr)
            return EXIT_UNCERTAIN
        request_id = result.get("request_id")
        verb = "已受理定时发布" if request.publish_date else "已受理"
        print(f"Upload-Post {verb}: {request.video_file} (request_id={request_id})")
        print(f"各平台结果: sau uploadpost status --id {request_id}")
        return 0

    raise RuntimeError(f"Unsupported Upload-Post action: {args.action}")
