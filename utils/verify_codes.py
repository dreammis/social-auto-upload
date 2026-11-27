# -*- coding: utf-8 -*-
"""Thread-safe bridge for SMS verification triggered by browser publishers.

The publishing worker creates a request when a platform asks for an SMS code.
The web UI polls for the pending request, submits the code, and the worker
consumes it before retrying the platform verification dialog.
"""
from __future__ import annotations

import threading
import time
import uuid

MAX_REQUEST_AGE_SECONDS = 30 * 60

_lock = threading.RLock()
_requests: dict[str, dict] = {}
_context = threading.local()


def set_context(title: str = "", platform: str = "", file_name: str = "") -> str:
    """Mark the current publishing thread as web-verification enabled."""
    context_id = uuid.uuid4().hex
    _context.id = context_id
    _context.title = title or ""
    _context.platform = platform or ""
    _context.file_name = file_name or ""
    return context_id


def clear_context(cancel_pending: bool = True, reason: str = "发布流程已结束") -> None:
    """Release the current thread context and optionally cancel its requests."""
    context_id = getattr(_context, "id", None)
    if cancel_pending and context_id:
        _cancel_requests(lambda request: request.get("context_id") == context_id, reason)
    for attr in ("id", "title", "platform", "file_name"):
        try:
            delattr(_context, attr)
        except AttributeError:
            pass


def is_enabled() -> bool:
    """Whether the current thread may wait for a code from the web UI."""
    return bool(getattr(_context, "id", None))


def _snapshot(request: dict) -> dict:
    return {key: value for key, value in request.items() if key != "code"}


def _current_context() -> dict:
    return {
        "context_id": getattr(_context, "id", None),
        "title": getattr(_context, "title", ""),
        "platform": getattr(_context, "platform", ""),
        "file_name": getattr(_context, "file_name", ""),
    }


def _cleanup_expired(now: float) -> None:
    for request_id, request in list(_requests.items()):
        if now - request["updated_at"] < MAX_REQUEST_AGE_SECONDS:
            continue
        if request["status"] in ("pending", "verifying"):
            request["status"] = "cancelled"
            request["updated_at"] = now
        elif request["status"] in ("resolved", "cancelled"):
            _requests.pop(request_id, None)


def create_request(platform: str = "", account_file: str = "", account_name: str = "") -> dict:
    """Create or reuse the active request for the current worker thread."""
    now = time.time()
    context = _current_context()
    account_file = str(account_file or "")
    with _lock:
        _cleanup_expired(now)
        for request in _requests.values():
            if (
                request["status"] in ("pending", "verifying")
                and request.get("context_id") == context["context_id"]
                and request.get("account_file") == account_file
            ):
                return _snapshot(request)

        request_id = uuid.uuid4().hex
        request = {
            "id": request_id,
            "context_id": context["context_id"],
            "title": context["title"],
            "file_name": context["file_name"],
            "platform": platform or context["platform"] or "抖音",
            "account_file": account_file,
            "account_name": account_name or "",
            "status": "pending",
            "message": "平台要求短信验证，请查看手机短信并输入验证码",
            "error": "",
            "resend_requested": False,
            "created_at": now,
            "updated_at": now,
        }
        _requests[request_id] = request
        return _snapshot(request)


def latest_pending() -> dict | None:
    """Return the oldest request that is still waiting for user input."""
    now = time.time()
    with _lock:
        _cleanup_expired(now)
        pending = [request for request in _requests.values() if request["status"] == "pending"]
        if not pending:
            return None
        pending.sort(key=lambda request: request["created_at"])
        return _snapshot(pending[0])


def submit_code(request_id: str, code: str) -> tuple[bool, str]:
    with _lock:
        request = _requests.get(request_id)
        if not request:
            return False, "验证码请求不存在或已结束"
        if request["status"] != "pending":
            return False, "该验证码请求已处理，请等待最新弹窗"
        request["code"] = str(code or "").strip()
        request["status"] = "submitted"
        request["error"] = ""
        request["updated_at"] = time.time()
        return True, ""


def poll_code(request_id: str) -> str:
    """Consume a submitted code. Called from the publishing worker."""
    with _lock:
        request = _requests.get(request_id)
        if not request or request["status"] != "submitted":
            return ""
        code = request.get("code") or ""
        request["code"] = ""
        request["status"] = "verifying"
        request["updated_at"] = time.time()
        return code


def report_result(request_id: str, success: bool, error: str = "") -> None:
    with _lock:
        request = _requests.get(request_id)
        if not request:
            return
        request["updated_at"] = time.time()
        if success:
            request["status"] = "resolved"
            request["error"] = ""
            request["resend_requested"] = False
            return
        request["status"] = "pending"
        request["error"] = error or "验证码验证失败，请重新输入"
        request["resend_requested"] = True


def request_resend(request_id: str) -> tuple[bool, str]:
    with _lock:
        request = _requests.get(request_id)
        if not request:
            return False, "验证码请求不存在或已结束"
        if request["status"] != "pending":
            return False, "当前无需重新发送验证码"
        request["resend_requested"] = True
        request["error"] = ""
        request["updated_at"] = time.time()
        return True, ""


def consume_resend(request_id: str) -> bool:
    with _lock:
        request = _requests.get(request_id)
        if not request or not request.get("resend_requested"):
            return False
        request["resend_requested"] = False
        return True


def cancel_request(request_id: str, reason: str = "发布流程已结束") -> None:
    with _lock:
        request = _requests.get(request_id)
        if not request or request["status"] in ("resolved", "cancelled"):
            return
        request["status"] = "cancelled"
        request["error"] = reason
        request["updated_at"] = time.time()


def _cancel_requests(predicate, reason: str) -> None:
    with _lock:
        for request in _requests.values():
            if not predicate(request) or request["status"] in ("resolved", "cancelled"):
                continue
            request["status"] = "cancelled"
            request["error"] = reason
            request["updated_at"] = time.time()


def reset() -> None:
    """Clear all in-memory state. Intended for tests and process restarts."""
    with _lock:
        _requests.clear()
    for attr in ("id", "title", "platform", "file_name"):
        try:
            delattr(_context, attr)
        except AttributeError:
            pass
