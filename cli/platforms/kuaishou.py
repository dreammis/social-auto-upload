"""Kuaishou platform operations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cli.models import KuaishouNoteUploadRequest, KuaishouVideoUploadRequest
from cli.utils import resolve_account_file
from uploader.ks_uploader.main import KSNote, KSVideo, cookie_auth, ks_setup


async def login(account_name: str, headless: bool = True, qrcode_callback=None) -> Any:
    """Login to Kuaishou account."""
    account_file = resolve_account_file('kuaishou', account_name)
    return await ks_setup(
        str(account_file),
        handle=True,
        return_detail=True,
        headless=headless,
        qrcode_callback=qrcode_callback,
    )


async def check(account_name: str) -> bool:
    """Check if Kuaishou cookie is valid."""
    account_file = resolve_account_file('kuaishou', account_name)
    if not account_file.exists():
        return False
    return await cookie_auth(str(account_file))


async def upload_video(request: KuaishouVideoUploadRequest) -> Path:
    """Upload video to Kuaishou."""
    account_file = resolve_account_file('kuaishou', request.account_name)
    is_ready = await ks_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f'Kuaishou cookie is missing or expired: {account_file}. '
            f'Run `sau kuaishou login --account {request.account_name}` first.'
        )
    app = KSVideo(
        title=request.title,
        file_path=str(request.video_file),
        desc=request.description,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def upload_note(request: KuaishouNoteUploadRequest) -> Path:
    """Upload note to Kuaishou."""
    account_file = resolve_account_file('kuaishou', request.account_name)
    is_ready = await ks_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f'Kuaishou cookie is missing or expired: {account_file}. '
            f'Run `sau kuaishou login --account {request.account_name}` first.'
        )
    app = KSNote(
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
