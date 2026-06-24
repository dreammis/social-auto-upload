"""Douyin platform operations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cli.models import DouyinNoteUploadRequest, DouyinVideoUploadRequest
from cli.utils import resolve_account_file
from uploader.douyin_uploader.main import (
    DouYinNote,
    DouYinVideo,
    cookie_auth,
    douyin_setup,
)


async def login(account_name: str, headless: bool = True, qrcode_callback=None) -> Any:
    """Login to Douyin account."""
    account_file = resolve_account_file('douyin', account_name)
    return await douyin_setup(
        str(account_file),
        handle=True,
        return_detail=True,
        headless=headless,
        qrcode_callback=qrcode_callback,
    )


async def check(account_name: str) -> bool:
    """Check if Douyin cookie is valid."""
    account_file = resolve_account_file('douyin', account_name)
    if not account_file.exists():
        return False
    return await cookie_auth(str(account_file))


async def upload_video(request: DouyinVideoUploadRequest) -> Path:
    """Upload video to Douyin."""
    account_file = resolve_account_file('douyin', request.account_name)
    is_ready = await douyin_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f'Douyin cookie is missing or expired: {account_file}. '
            f'Run `sau douyin login --account {request.account_name}` first.'
        )
    app = DouYinVideo(
        request.title,
        str(request.video_file),
        request.tags,
        request.publish_date,
        str(account_file),
        desc=request.description,
        thumbnail_landscape_path=str(request.thumbnail_landscape_file) if request.thumbnail_landscape_file else None,
        thumbnail_portrait_path=str(request.thumbnail_portrait_file or request.thumbnail_file) if request.thumbnail_portrait_file or request.thumbnail_file else None,
        productLink=request.product_link,
        productTitle=request.product_title,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    result = await app.douyin_upload_video()
    if result:
        print(f'[UPLOAD_RESULT]{json.dumps(result, ensure_ascii=False)}')
    return account_file


async def upload_note(request: DouyinNoteUploadRequest) -> Path:
    """Upload note to Douyin."""
    account_file = resolve_account_file('douyin', request.account_name)
    is_ready = await douyin_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f'Douyin cookie is missing or expired: {account_file}. '
            f'Run `sau douyin login --account {request.account_name}` first.'
        )
    app = DouYinNote(
        image_paths=[str(path) for path in request.image_files],
        title=request.title,
        note=request.note,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    result = await app.douyin_upload_note()
    if result:
        print(f'[UPLOAD_RESULT]{json.dumps(result, ensure_ascii=False)}')
    return account_file
