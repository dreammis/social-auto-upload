"""TikTok platform operations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.models import TiktokVideoUploadRequest
from cli.utils import resolve_account_file
from uploader.tk_uploader.main import TiktokVideo, cookie_auth, tiktok_setup


async def login(account_name: str, headless: bool = True, qrcode_callback=None) -> Any:
    """Login to TikTok account."""
    account_file = resolve_account_file('tiktok', account_name)
    return await tiktok_setup(
        str(account_file),
        handle=True,
        return_detail=True,
        headless=headless,
        qrcode_callback=qrcode_callback,
    )


async def check(account_name: str) -> bool:
    """Check if TikTok cookie is valid."""
    account_file = resolve_account_file('tiktok', account_name)
    if not account_file.exists():
        return False
    return await cookie_auth(str(account_file))


async def upload_video(request: TiktokVideoUploadRequest) -> Path:
    """Upload video to TikTok."""
    account_file = resolve_account_file('tiktok', request.account_name)
    is_ready = await tiktok_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f'TikTok cookie is missing or expired: {account_file}. '
            f'Run `sau tiktok login --account {request.account_name}` first.'
        )
    app = TiktokVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
    )
    await app.main()
    return account_file
