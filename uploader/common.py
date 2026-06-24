# -*- coding: utf-8 -*-
"""Shared utility functions for all platform uploaders."""

from __future__ import annotations

import inspect

from patchright.async_api import Page


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return

    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(
    success: bool,
    status: str,
    message: str,
    account_file: str,
    qrcode: dict | None = None,
    current_url: str = "",
) -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def _check_login_markers(page: Page, markers: list[str]) -> bool:
    """Check if any login-related text markers are visible on the page.

    Uses ``exact=True`` to avoid false positives from substring matches
    (the root cause of the Bilibili ``cookie_invalid`` bug).

    Intended for use in both ``cookie_auth()`` and ``_is_*_login_completed()``
    to keep login detection logic consistent across all platform uploaders.

    Returns ``True`` if at least one marker is visible on the page.
    """
    for text in markers:
        try:
            locator = page.get_by_text(text, exact=True).first
            if await locator.count() and await locator.is_visible():
                return True
        except Exception:
            continue
    return False


async def _all_login_markers_hidden(page: Page, markers: list[str]) -> bool:
    """Check that all login markers are absent or hidden.

    The inverse of ``_check_login_markers`` — returns ``True`` when none
    of the markers are visible, meaning the user has successfully logged
    in and entered an authenticated page.
    """
    for text in markers:
        try:
            locator = page.get_by_text(text, exact=True).first
            if await locator.count():
                try:
                    if await locator.is_visible():
                        return False
                except Exception:
                    continue
        except Exception:
            continue
    return True
