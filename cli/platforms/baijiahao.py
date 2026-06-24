"""Baijiahao platform operations."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from cli.models import BaijiahaoVideoUploadRequest
from cli.utils import resolve_account_file
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo, cookie_auth, baijiahao_setup


async def login(account_name: str, headless: bool = True, qrcode_callback=None) -> Any:
    """Login to Baijiahao account."""
    account_file = resolve_account_file('baijiahao', account_name)
    return await baijiahao_setup(
        str(account_file),
        handle=True,
        return_detail=True,
        headless=headless,
        qrcode_callback=qrcode_callback,
    )


async def check(account_name: str) -> bool:
    """Check if Baijiahao cookie is valid."""
    account_file = resolve_account_file('baijiahao', account_name)
    if not account_file.exists():
        return False
    return await cookie_auth(str(account_file))


async def upload_video(request: BaijiahaoVideoUploadRequest) -> Path:
    """Upload video to Baijiahao."""
    account_file = resolve_account_file('baijiahao', request.account_name)
    is_ready = await baijiahao_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f'Baijiahao cookie is missing or expired: {account_file}. '
            f'Run `sau baijiahao login --account {request.account_name}` first.'
        )
    publish_date = request.publish_date if isinstance(request.publish_date, datetime) else datetime.now()
    app = BaiJiaHaoVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        publish_date=publish_date,
        account_file=str(account_file),
    )
    await app.main()
    return account_file
