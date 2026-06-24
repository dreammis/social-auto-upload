"""Tencent/WeChat Channels platform operations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.models import TencentNoteUploadRequest, TencentVideoUploadRequest
from cli.utils import resolve_account_file
from uploader.tencent_uploader.main import (
    TencentNote,
    TencentVideo,
    cookie_auth,
    tencent_setup,
)


async def login(account_name: str, headless: bool = True, qrcode_callback=None) -> Any:
    """Login to Tencent/WeChat Channels account."""
    account_file = resolve_account_file('tencent', account_name)
    return await tencent_setup(
        str(account_file),
        handle=True,
        return_detail=True,
        headless=headless,
        qrcode_callback=qrcode_callback,
    )


async def check(account_name: str) -> bool:
    """Check if Tencent/WeChat Channels cookie is valid."""
    account_file = resolve_account_file('tencent', account_name)
    if not account_file.exists():
        return False
    return await cookie_auth(str(account_file))


async def upload_video(request: TencentVideoUploadRequest) -> Path:
    """Upload video to Tencent/WeChat Channels."""
    account_file = resolve_account_file('tencent', request.account_name)
    is_ready = await tencent_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f'Tencent/WeChat Channels cookie is missing or expired: {account_file}. '
            f'Run `sau tencent login --account {request.account_name}` first.'
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
        thumbnail_landscape_path=str(request.thumbnail_landscape_file) if request.thumbnail_landscape_file else None,
        thumbnail_portrait_path=str(request.thumbnail_portrait_file) if request.thumbnail_portrait_file else None,
        short_title=request.short_title,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    await app.tencent_upload_video()
    return account_file


async def upload_note(request: TencentNoteUploadRequest) -> Path:
    """Upload note to Tencent/WeChat Channels."""
    account_file = resolve_account_file('tencent', request.account_name)
    is_ready = await tencent_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f'Tencent/WeChat Channels cookie is missing or expired: {account_file}. '
            f'Run `sau tencent login --account {request.account_name}` first.'
        )
    app = TencentNote(
        image_paths=[str(path) for path in request.image_files],
        note=request.note,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        title=request.title,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        is_draft=request.is_draft,
    )
    await app.tencent_upload_note()
    return account_file
