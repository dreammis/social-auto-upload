"""Shared utilities for web_runner routes."""
from __future__ import annotations

import base64
import binascii
import json
import os
import queue as _queue
import re
import sqlite3
import sys
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Generator

from utils.log import logger as _task_logger

from web_runner.db import DB_PATH, BASE_DIR, db_lock, get_connection

COOKIES_DIR = BASE_DIR / "cookies"
COOKIES_DIR.mkdir(exist_ok=True)

UPLOADS_DIR = BASE_DIR / ".sau_uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

task_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="sau-task")
_scheduled_timers: dict[str, threading.Timer] = {}
_timer_lock = threading.Lock()
_progress_subscribers: dict[str, list] = {}
_progress_sub_lock = threading.Lock()
_MAX_SSE_CONNECTIONS = 5
_SSE_TIMEOUT_SECONDS = 300

sys.path.insert(0, str(BASE_DIR))

LOG_MAX_ROWS = 10_000
_log_trim_counter = 0
_error_event_trim_counter = 0
MIN_UPLOAD_BYTES = 10240


class _LogCapture:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def write(self, message: str) -> None:
        text = message.strip()
        if text:
            self.messages.append(text)

    def flush(self) -> None:
        pass


def log(message: str) -> None:
    _task_logger.info(message)
    _db_insert_log(datetime.now().isoformat(timespec="milliseconds"), message)


def _save_data_uri(data_uri: str) -> Path | None:
    if not data_uri:
        return None
    try:
        if "," in data_uri:
            header, raw = data_uri.split(",", 1)
            ext_part = header.split(";")[0].split("/")[1] if "/" in header else ""
            ext = f".{ext_part}" if ext_part else ""
        else:
            raw = data_uri
            ext = ""
        if not raw.strip():
            return None
        decoded = base64.b64decode(raw)
        return _write_upload(decoded, ext)
    except (binascii.Error, UnicodeEncodeError, OSError, ValueError, TypeError) as exc:
        log(f"[upload] failed to save data uri: {type(exc).__name__}")
        return None


def _download_url(url: str) -> Path | None:
    import http.client
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            raw = resp.read()
        ext = Path(url.split("?")[0]).suffix or ".jpg"
        return _write_upload(raw, ext)
    except (http.client.HTTPException, urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError, ValueError, TypeError) as exc:
        log(f"[upload] failed to download url {url[:60]}: {type(exc).__name__}")
        return None


def _write_upload(raw: bytes, ext: str = "") -> Path | None:
    if len(raw) < MIN_UPLOAD_BYTES:
        log(f"[upload] rejected file: payload is only {len(raw)} bytes (min {MIN_UPLOAD_BYTES})")
        return None
    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOADS_DIR / name
    path.write_bytes(raw)
    log(f"[upload] saved temp file: {path} ({len(raw)} bytes)")
    return path


def _db_insert_task(
    task_id: str,
    status: str,
    platform: str,
    action: str,
    account: str,
    created: str,
    argv: list[str] | None = None,
) -> None:
    with db_lock:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, status, platform, action, account, created, argv) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, status, platform, action, account, created, json.dumps(argv) if argv else None),
            )
            conn.commit()


def _db_get_task(task_id: str) -> dict | None:
    with db_lock:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            return dict(row) if row else None


def _db_update_task(task_id: str, **kwargs: str | int | None) -> None:
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [task_id]
    with db_lock:
        with get_connection() as conn:
            conn.execute(f"UPDATE tasks SET {set_clause} WHERE task_id = ?", values)
            conn.commit()


def _db_get_all_tasks(limit: int | None = None, offset: int = 0) -> list[dict]:
    with db_lock:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM tasks ORDER BY created DESC"
            params: list = []
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


def _new_task_id(prefix: str) -> str:
    ts = datetime.now().strftime("%H%M%S")
    short_uuid = uuid.uuid4().hex[:6]
    return f"{prefix}-{ts}-{short_uuid}"


def _db_insert_log(ts: str, message: str) -> None:
    global _log_trim_counter
    with db_lock:
        with get_connection() as conn:
            conn.execute("INSERT INTO logs (ts, message) VALUES (?, ?)", (ts, message))
            conn.commit()
            _log_trim_counter += 1
            if _log_trim_counter >= 200:
                _log_trim_counter = 0
                conn.execute(
                    "DELETE FROM logs WHERE ts NOT IN (SELECT ts FROM logs ORDER BY ts DESC LIMIT ?)",
                    (LOG_MAX_ROWS,),
                )
                conn.commit()


def _db_get_logs(after: str | None = None, task_id: str | None = None, limit: int | None = None, offset: int = 0) -> list[dict]:
    with db_lock:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT ts, message FROM logs"
            conditions: list[str] = []
            params: list = []
            if after:
                conditions.append("ts > ?")
                params.append(after)
            if task_id:
                conditions.append("message LIKE ?")
                params.append(f"%{task_id}%")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY ts ASC"
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


def _log_error_event(
    phase: str,
    platform: str = "",
    account: str = "",
    action: str = "",
    task_id: str | None = None,
    exc: BaseException | None = None,
    exc_type: str = "",
    exc_message: str = "",
    tb: str | None = None,
    argv: list[str] | None = None,
    attempt_no: int | None = None,
    retry_count: int | None = None,
    status_code: int | None = None,
) -> None:
    global _error_event_trim_counter
    now = datetime.now().isoformat(timespec="seconds")
    if exc is not None and not exc_type:
        exc_type = type(exc).__name__
    if exc is not None and not exc_message:
        exc_message = str(exc)
    if tb is None and exc is not None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    with db_lock:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO error_events
                   (ts, task_id, level, phase, platform, account, action,
                    exc_type, exc_message, traceback, argv, attempt_no, retry_count, status_code)
                   VALUES (?, ?, 'error', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (now, task_id, phase, platform, account, action,
                 exc_type, exc_message, tb,
                 json.dumps(argv) if argv else None,
                 attempt_no, retry_count, status_code),
            )
            conn.commit()
            _error_event_trim_counter += 1
            if _error_event_trim_counter >= 100:
                _error_event_trim_counter = 0
                conn.execute(
                    "DELETE FROM error_events WHERE id NOT IN (SELECT id FROM error_events ORDER BY ts DESC LIMIT ?)",
                    (LOG_MAX_ROWS,),
                )
                conn.commit()


def _db_get_error_events(
    after: str | None = None,
    platform: str | None = None,
    account: str | None = None,
    action: str | None = None,
    exc_type: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    with db_lock:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM error_events"
            conditions: list[str] = []
            params: list = []
            if after:
                conditions.append("ts > ?")
                params.append(after)
            if platform:
                conditions.append("platform = ?")
                params.append(platform)
            if account:
                conditions.append("account = ?")
                params.append(account)
            if action:
                conditions.append("action = ?")
                params.append(action)
            if exc_type:
                conditions.append("exc_type = ?")
                params.append(exc_type)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY ts DESC"
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


def _recover_orphaned_tasks() -> None:
    with db_lock:
        with get_connection() as conn:
            orphans = conn.execute(
                "SELECT task_id, argv FROM tasks WHERE status = 'running'"
            ).fetchall()
            for row in orphans:
                task_id, argv_json = row
                conn.execute(
                    "UPDATE tasks SET status = 'error', error = ? WHERE task_id = ?",
                    ("Orphaned: server restarted while task was running", task_id),
                )
                log(f"[recover] marked orphaned task as error: {task_id}")
            conn.commit()


def _start_orphan_watchdog(interval_seconds: int = 120) -> None:
    def _watchdog() -> None:
        while True:
            time.sleep(interval_seconds)
            try:
                _recover_orphaned_tasks()
            except (sqlite3.Error, OSError) as exc:
                log(f"[watchdog] error: {exc}")

    t = threading.Thread(target=_watchdog, daemon=True, name="orphan-watchdog")
    t.start()


def _sync_cookie_files_to_db() -> None:
    if not COOKIES_DIR.exists():
        return
    with db_lock:
        with get_connection() as conn:
            for cookie_file in COOKIES_DIR.glob("*.json"):
                name = cookie_file.stem
                parts = name.split("_", 1)
                if len(parts) != 2:
                    continue
                platform, account_name = parts
                existing = conn.execute(
                    "SELECT aa.id FROM account_authorizations aa "
                    "JOIN account_groups ag ON aa.group_id = ag.id "
                    "WHERE ag.name = ? AND aa.platform = ?",
                    (account_name, platform),
                ).fetchone()
                if existing:
                    continue
                group = conn.execute(
                    "SELECT id FROM account_groups WHERE name = ?",
                    (account_name,),
                ).fetchone()
                if group:
                    group_id = group[0]
                else:
                    conn.execute(
                        "INSERT INTO account_groups (name, created) VALUES (?, ?)",
                        (account_name, datetime.now().isoformat(timespec="seconds")),
                    )
                    group_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute(
                    "INSERT OR IGNORE INTO account_authorizations (group_id, platform, cookie_file, created) VALUES (?, ?, ?, ?)",
                    (group_id, platform, str(cookie_file), datetime.now().isoformat(timespec="seconds")),
                )
            conn.commit()


def _account_files(platform: str | None = None) -> list[dict]:
    if not COOKIES_DIR.exists():
        return []
    results: list[dict] = []
    for f in sorted(COOKIES_DIR.glob("*.json")):
        name = f.stem
        parts = name.split("_", 1)
        if len(parts) != 2:
            continue
        plat, acct = parts
        if platform and plat != platform:
            continue
        results.append({"platform": plat, "account_name": acct, "path": str(f)})
    return results


def _quick_check_cookie(platform: str, account: str) -> dict:
    cookie_path = COOKIES_DIR / f"{platform}_{account}.json"
    if not cookie_path.exists():
        return {"valid": False, "reason": "no_file", "age_hours": None, "file_size": None}
    try:
        stat = cookie_path.stat()
        age_hours = (time.time() - stat.st_mtime) / 3600
        file_size = stat.st_size
        if file_size < 10:
            return {"valid": False, "reason": "empty_file", "age_hours": round(age_hours, 1), "file_size": file_size}
        with open(cookie_path) as f:
            data = json.load(f)
        if not data:
            return {"valid": False, "reason": "empty_json", "age_hours": round(age_hours, 1), "file_size": file_size}
        return {"valid": True, "reason": "ok", "age_hours": round(age_hours, 1), "file_size": file_size}
    except (json.JSONDecodeError, OSError):
        return {"valid": False, "reason": "invalid_json", "age_hours": None, "file_size": None}


def _parse_upload_result(stdout: str) -> str | None:
    for line in stdout.splitlines():
        if line.startswith("[UPLOAD_RESULT]"):
            return line[len("[UPLOAD_RESULT]"):]
    return None


def _store_result(task_id: str, stdout: str) -> None:
    result_json = _parse_upload_result(stdout)
    if result_json:
        _db_update_task(task_id, result=result_json)


def _run_sau(task_id: str, argv: list[str]) -> None:
    import subprocess
    _db_update_task(task_id, status="running")
    log(f"[{task_id}] starting: sau {' '.join(argv)}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "sau_cli"] + argv,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(BASE_DIR),
        )
        if result.returncode == 0:
            _db_update_task(task_id, status="success", code=0)
            _store_result(task_id, result.stdout)
            log(f"[{task_id}] completed successfully")
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            _db_update_task(task_id, status="failed", code=result.returncode, error=error_msg)
            log(f"[{task_id}] failed with code {result.returncode}: {error_msg[:200]}")
            _log_error_event(
                phase="cli",
                task_id=task_id,
                exc_type="NonZeroExit",
                exc_message=error_msg[:500],
                tb=result.stderr[-2000:] if result.stderr else None,
                argv=argv,
                status_code=result.returncode,
            )
    except subprocess.TimeoutExpired:
        _db_update_task(task_id, status="error", error="Task timed out after 600 seconds")
        log(f"[{task_id}] timed out")
        _log_error_event(
            phase="cli",
            task_id=task_id,
            exc_type="TimeoutExpired",
            exc_message="Task timed out after 600 seconds",
            argv=argv,
        )
    except (OSError, ValueError) as exc:
        _db_update_task(task_id, status="error", error=str(exc))
        log(f"[{task_id}] error: {exc}")
        _log_error_event(
            phase="cli",
            task_id=task_id,
            exc=exc,
            argv=argv,
        )


def _schedule_task(task_id: str, argv: list[str], schedule_time: datetime) -> None:
    delay = (schedule_time - datetime.now()).total_seconds()
    if delay <= 0:
        task_executor.submit(_run_sau, task_id, argv)
        return
    log(f"[{task_id}] scheduled for {schedule_time.isoformat()} (in {delay:.0f}s)")
    timer = threading.Timer(delay, lambda: task_executor.submit(_run_sau, task_id, argv))
    timer.daemon = True
    with _timer_lock:
        _scheduled_timers[task_id] = timer
    timer.start()


def _normalise_schedule(schedule: str | None) -> str | None:
    if not schedule:
        return None
    return schedule.replace("T", " ").strip()


def _headless_flag(headless: object) -> str | None:
    if headless is None:
        return None
    if isinstance(headless, bool):
        return "true" if headless else "false"
    s = str(headless).strip().lower()
    if s in ("true", "1", "yes"):
        return "true"
    if s in ("false", "0", "no"):
        return "false"
    return None


def _validate_group_name(raw: object) -> tuple[bool, str]:
    _FORBIDDEN_NAME_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1F\x7F]')
    _NAME_MAX_LEN = 64
    if not isinstance(raw, str):
        return False, "分组名不能为空"
    cleaned = raw.strip()
    if not cleaned:
        return False, "分组名不能为空"
    if len(cleaned) > _NAME_MAX_LEN:
        return False, f"分组名长度不能超过 {_NAME_MAX_LEN} 个字符"
    if _FORBIDDEN_NAME_CHARS.search(cleaned):
        return False, '分组名包含不允许的字符（/\\:*?"<>|）'
    return True, cleaned


def _cleanup_old_uploads() -> None:
    now = time.time()
    max_age = 24 * 60 * 60
    count = 0
    for f in UPLOADS_DIR.iterdir():
        if f.is_file() and (now - f.stat().st_mtime) > max_age:
            f.unlink(missing_ok=True)
            count += 1
    if count:
        print(f"[startup] cleaned {count} old temp files from {UPLOADS_DIR}")


PLATFORM_CONFIG: dict[str, dict] = {
    "douyin": {"video": True, "note": True, "thumbnail": True, "thumbnail_dual": True, "product": True},
    "kuaishou": {"video": True, "note": True, "thumbnail": True},
    "xiaohongshu": {"video": True, "note": True, "thumbnail": True},
    "bilibili": {"video": True, "note": True},
    "tencent": {"video": True, "note": True, "thumbnail": True, "thumbnail_dual": True, "tencent_extra": True},
    "tiktok": {"video": True},
    "baijiahao": {"video": True},
}

DESC_PLATFORMS = {"douyin", "kuaishou", "xiaohongshu", "bilibili", "tencent"}
THUMBNAIL_PLATFORMS = {"douyin", "kuaishou", "xiaohongshu", "tencent"}
THUMBNAIL_DUAL_PLATFORMS = {"douyin", "tencent"}
NOTE_PLATFORMS = {p for p, cfg in PLATFORM_CONFIG.items() if cfg.get("note")}
_QR_LOGIN_PLATFORMS = {"douyin", "kuaishou", "xiaohongshu", "tencent", "bilibili", "tiktok", "baijiahao"}
