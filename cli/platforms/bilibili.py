"""Bilibili platform operations."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from cli.models import BilibiliNoteUploadRequest, BilibiliVideoUploadRequest
from cli.utils import resolve_account_file
from uploader.bilibili_uploader.main import bilibili_cookie_auth, bilibili_setup
from uploader.bilibili_uploader.note import BilibiliNote
from uploader.bilibili_uploader.runtime import run_biliup_command


async def login(account_name: str, headless: bool = True, qrcode_callback=None) -> Any:
    """Login to Bilibili account."""
    account_file = resolve_account_file('bilibili', account_name)
    return await bilibili_setup(
        str(account_file),
        handle=True,
        return_detail=True,
        headless=headless,
        qrcode_callback=qrcode_callback,
    )


async def check(account_name: str) -> bool:
    """Check if Bilibili cookie is valid."""
    account_file = resolve_account_file('bilibili', account_name)
    if not account_file.exists():
        return False
    return await bilibili_cookie_auth(str(account_file))


async def upload_video(request: BilibiliVideoUploadRequest) -> Path:
    """Upload video to Bilibili."""
    account_file = resolve_account_file('bilibili', request.account_name)
    if not account_file.exists():
        raise RuntimeError(
            f'Bilibili account file is missing: {account_file}. '
            f'Run `sau bilibili login --account {request.account_name}` first.'
        )
    if not await bilibili_cookie_auth(str(account_file)):
        raise RuntimeError(
            f'Bilibili cookie is invalid or expired: {account_file}. '
            f'Run `sau bilibili login --account {request.account_name}` first.'
        )
    arguments = [
        '-u', str(account_file),
        'upload', str(request.video_file),
        '--title', request.title,
        '--desc', request.description,
        '--tid', str(request.tid),
    ]
    if request.tags:
        arguments.extend(['--tag', ','.join(request.tags)])
    if isinstance(request.publish_date, datetime):
        arguments.extend(['--dtime', str(int(request.publish_date.timestamp()))])
    result = run_biliup_command(arguments)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or '').strip() or 'Bilibili upload failed')
    return account_file


async def upload_note(request: BilibiliNoteUploadRequest) -> Path:
    """Upload note to Bilibili."""
    account_file = resolve_account_file('bilibili', request.account_name)
    if not account_file.exists():
        raise RuntimeError(
            f'Bilibili cookie is missing: {account_file}. '
            f'Run `sau bilibili login --account {request.account_name}` first.'
        )
    if not await bilibili_cookie_auth(str(account_file)):
        raise RuntimeError(
            f'Bilibili cookie is invalid or expired: {account_file}. '
            f'Run `sau bilibili login --account {request.account_name}` first.'
        )
    app = BilibiliNote(
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
    await app.main()
    return account_file
