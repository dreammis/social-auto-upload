"""Account management routes."""
from __future__ import annotations

import asyncio
import json
import queue as _queue
import threading
from datetime import datetime
from typing import Generator

import patchright
from flask import Blueprint, Response, jsonify, request

from web_runner.utils import (
    _QR_LOGIN_PLATFORMS,
    _account_files,
    _db_insert_task,
    _db_get_task,
    _headless_flag,
    _log_error_event,
    _new_task_id,
    _quick_check_cookie,
    _run_sau,
    log,
    task_executor,
)

bp = Blueprint("accounts", __name__)


@bp.get("/api/accounts")
def list_accounts():
    platform = request.args.get("platform")
    return jsonify({"success": True, "data": _account_files(platform)})


@bp.post("/api/accounts/delete")
def delete_account():
    from web_runner.utils import COOKIES_DIR
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")
    account = payload.get("account")
    if not platform or not account:
        return jsonify({"success": False, "message": "platform and account are required"}), 400
    cookie_path = COOKIES_DIR / f"{platform}_{account}.json"
    if not cookie_path.exists():
        return jsonify({"success": False, "message": f"Account file not found: {cookie_path}"}), 404
    cookie_path.unlink()
    log(f"[accounts] deleted: {platform}_{account}.json")
    return jsonify({"success": True, "message": f"已删除 {platform}/{account}"})


@bp.post("/api/accounts/check")
def check_account():
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")
    account = payload.get("account")
    deep = payload.get("deep", False)
    if not platform or not account:
        return jsonify({"success": False, "message": "platform and account are required"}), 400
    quick_result = _quick_check_cookie(platform, account)
    if not deep:
        return jsonify({"success": True, "data": {"quick": quick_result, "deep_check": None, "task_id": None}})
    argv = [platform, "check", "--account", account]
    task_id = _new_task_id("check")
    _db_insert_task(
        task_id=task_id, status="pending", platform=platform,
        action="check", account=account,
        created=datetime.now().isoformat(timespec="seconds"), argv=argv,
    )
    task_executor.submit(_run_sau, task_id, argv)
    return jsonify({"success": True, "data": {"quick": quick_result, "deep_check": "pending", "task_id": task_id}})


@bp.post("/api/accounts/check-all")
def check_all_accounts():
    accounts = _account_files()
    results = []
    for acct in accounts:
        quick_result = _quick_check_cookie(acct["platform"], acct["account_name"])
        results.append({"platform": acct["platform"], "account": acct["account_name"], "quick": quick_result})
    return jsonify({"success": True, "data": results})


@bp.post("/api/accounts/login")
def login_account():
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")
    account = payload.get("account")
    if not platform or not account:
        return jsonify({"success": False, "message": "platform and account are required"}), 400
    argv = [platform, "login", "--account", account]
    hflag = _headless_flag(payload.get("headless", True))
    if hflag == "true":
        argv.append("--headless")
    elif hflag == "false":
        argv.append("--headed")
    task_id = _new_task_id("login")
    _db_insert_task(
        task_id=task_id, status="pending", platform=platform,
        action="login", account=account,
        created=datetime.now().isoformat(timespec="seconds"), argv=argv,
    )
    task_executor.submit(_run_sau, task_id, argv)
    return jsonify({"success": True, "data": {"task_id": task_id}})


@bp.get("/api/accounts/login/sse")
def login_account_sse():
    platform = request.args.get("platform", "")
    account = request.args.get("account", "")
    headless_str = request.args.get("headless", "true")
    if not platform or not account:
        return jsonify({"success": False, "message": "platform and account are required"}), 400
    if platform not in _QR_LOGIN_PLATFORMS:
        return jsonify({
            "success": False,
            "message": f"Platform {platform} does not support QR-code login in web UI. Please use CLI: sau {platform} login --account {account}"
        }), 400

    q: _queue.Queue = _queue.Queue()

    def _qrcode_callback(qrcode_info: dict) -> None:
        q.put({"event": "qrcode", "data": qrcode_info})

    def _run_login() -> None:
        try:
            from cli.platforms import douyin, kuaishou, xiaohongshu, tencent, bilibili, tiktok, baijiahao
            headless = headless_str.lower() in ("true", "1", "yes")
            _LOGIN_FN_MAP = {
                "douyin": douyin.login, "kuaishou": kuaishou.login,
                "xiaohongshu": xiaohongshu.login, "tencent": tencent.login,
                "bilibili": bilibili.login, "tiktok": tiktok.login,
                "baijiahao": baijiahao.login,
            }
            login_fn = _LOGIN_FN_MAP.get(platform)
            if not login_fn:
                q.put({"event": "error", "data": {"message": f"Unsupported platform: {platform}"}})
                return
            result: dict = asyncio.run(login_fn(account, headless=headless, qrcode_callback=_qrcode_callback))
            q.put({"event": "result", "data": result})
            if not result.get("success", True):
                _log_error_event(
                    phase="sse_login", platform=platform, account=account,
                    action="login", exc_type=f'LoginFailed[{result.get("status", "unknown")}]',
                    exc_message=result.get("message", ""),
                )
        except (patchright.async_api.Error, OSError, asyncio.TimeoutError, RuntimeError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            q.put({"event": "result", "data": {"success": False, "message": str(exc)}})
            _log_error_event(phase="sse_login", platform=platform, account=account, action="login", exc=exc)

    thread = threading.Thread(target=_run_login, daemon=True)
    thread.start()

    def generate() -> Generator:
        yield f": {' ' * 4096}\n\n"
        while thread.is_alive() or not q.empty():
            try:
                msg = q.get(timeout=2)
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'], ensure_ascii=False)}\n\n"
                if msg["event"] in ("result", "error"):
                    break
            except _queue.Empty:
                yield f"event: ping\ndata: {json.dumps({'ts': datetime.now().isoformat()})}\n\n"

    return Response(
        generate(), mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
