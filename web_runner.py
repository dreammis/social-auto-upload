from __future__ import annotations

import asyncio
import base64
import json
import os
import queue as _queue
import sqlite3
import sys
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Generator

from flask import Flask, jsonify, request, Response
from flask_cors import CORS

BASE_DIR = Path(__file__).parent.resolve()
COOKIES_DIR = BASE_DIR / "cookies"
COOKIES_DIR.mkdir(exist_ok=True)

UPLOADS_DIR = BASE_DIR / ".sau_uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

DB_DIR = BASE_DIR / "db"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "database.db"

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

db_lock = threading.Lock()
task_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="sau-task")

sys.path.insert(0, str(BASE_DIR))


LOG_MAX_ROWS = 10_000
_log_trim_counter = 0

# Minimum acceptable upload size in bytes (~100KB). Reject obvious junk/empty data URIs early.
MIN_UPLOAD_BYTES = 10240

class _LogCapture:
    def __init__(self) -> None:
        self.buffer = StringIO()

    def write(self, data: str) -> int:
        text = data.rstrip("\n")
        if text:
            log(text)
            self.buffer.write(text + "\n")
        return len(data)

    def flush(self) -> None:
        pass


def log(message: str) -> None:
    _db_insert_log(
        ts=datetime.now().isoformat(timespec="seconds"),
        message=message,
    )


def _save_data_uri(data_uri: str) -> Path | None:
    if not data_uri:
        return None
    try:
        if data_uri.startswith("data:"):
            header, _, encoded = data_uri.partition(",")
            ext = ""
            if "/" in header:
                raw_ext = header.split(";")[0].split("/")[-1]
                ext = f".{raw_ext}" if raw_ext else ""
            raw = base64.b64decode(encoded)
        elif data_uri.startswith(("http://", "https://", "ftp://")):
            return _download_url(data_uri)
        else:
            raw = data_uri.encode()
            ext = ""
        return _write_upload(raw, ext)
    except Exception as exc:
        log(f"[upload] failed to save data uri: {exc}")
        return None


def _download_url(url: str) -> Path | None:
    """Download a URL to a temp file and return the path."""
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            raw = resp.read()
        ext = Path(url.split("?")[0]).suffix or ".jpg"
        return _write_upload(raw, ext)
    except Exception as exc:
        log(f"[upload] failed to download url {url[:60]}: {exc}")
        return None


def _write_upload(raw: bytes, ext: str = "") -> Path | None:
    """Write bytes to an upload temp file, respecting minimum size."""
    if len(raw) < MIN_UPLOAD_BYTES:
        log(f"[upload] rejected file: payload is only {len(raw)} bytes (min {MIN_UPLOAD_BYTES})")
        return None
    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOADS_DIR / name
    path.write_bytes(raw)
    log(f"[upload] saved temp file: {path} ({len(raw)} bytes)")
    return path


def _init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                platform TEXT,
                action TEXT,
                account TEXT,
                created TEXT,
                code INTEGER,
                error TEXT,
                argv TEXT,
                result TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                ts TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)
        conn.commit()
        # Add columns for existing databases
        for col in ("argv", "result", "publish_detail"):
            try:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
        # Index for incremental log reads and task_id filtering
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs (ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_message ON logs (message)")
        conn.commit()


_init_db()


def _cleanup_old_uploads() -> None:
    """Remove temp upload files older than 24 hours."""
    import time
    now = time.time()
    max_age = 24 * 60 * 60
    count = 0
    for f in UPLOADS_DIR.iterdir():
        if f.is_file() and (now - f.stat().st_mtime) > max_age:
            f.unlink(missing_ok=True)
            count += 1
    if count:
        print(f"[startup] cleaned {count} old temp files from {UPLOADS_DIR}")


_cleanup_old_uploads()

# ---------------------------------------------------------------------------
# DB helpers — tasks
# ---------------------------------------------------------------------------

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
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, status, platform, action, account, created, argv) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, status, platform, action, account, created, json.dumps(argv) if argv else None),
            )
            conn.commit()


def _db_get_task(task_id: str) -> dict | None:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            return dict(row) if row else None


_TASK_COLUMNS = {"status", "platform", "action", "account", "created", "code", "error", "argv", "result", "publish_detail"}


def _db_update_task(task_id: str, **kwargs: str | int | None) -> None:
    if not kwargs:
        return
    filtered = {k: v for k, v in kwargs.items() if k in _TASK_COLUMNS}
    if not filtered:
        return
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            set_clause = ", ".join(f"{k} = ?" for k in filtered)
            values = list(filtered.values()) + [task_id]
            conn.execute(f"UPDATE tasks SET {set_clause} WHERE task_id = ?", values)
            conn.commit()


def _db_get_all_tasks() -> list[dict]:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM tasks ORDER BY task_id").fetchall()
            return [dict(row) for row in rows]


def _new_task_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"

# ---------------------------------------------------------------------------
# DB helpers — logs
# ---------------------------------------------------------------------------

def _db_insert_log(ts: str, message: str) -> None:
    global _log_trim_counter
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO logs (ts, message) VALUES (?, ?)",
                (ts, message),
            )
            _log_trim_counter += 1
            if _log_trim_counter % 50 == 0:
                conn.execute(
                    "DELETE FROM logs WHERE rowid NOT IN (SELECT rowid FROM logs ORDER BY rowid DESC LIMIT ?)",
                    (LOG_MAX_ROWS,),
                )
            conn.commit()


def _db_get_logs(after: str | None = None, task_id: str | None = None) -> list[dict]:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            if task_id:
                prefix = f"[{task_id}]"
                if after:
                    rows = conn.execute(
                        "SELECT ts, message FROM logs WHERE ts > ? AND message LIKE ? ORDER BY rowid",
                        (after, f"{prefix}%"),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT ts, message FROM logs WHERE message LIKE ? ORDER BY rowid",
                        (f"{prefix}%",),
                    ).fetchall()
            elif after:
                rows = conn.execute(
                    "SELECT ts, message FROM logs WHERE ts > ? ORDER BY rowid", (after,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT ts, message FROM logs ORDER BY rowid"
                ).fetchall()
            return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Orphaned-task recovery: when web_runner restarts, tasks that were
# pending/running in the previous process are stranded here forever.
# Recover them so the UI doesn't spin endlessly.
# ---------------------------------------------------------------------------

_ORPHAN_PENDING_THRESHOLD_SECONDS = 120  # pending/running for >2 min => treat as killed


def _recover_orphaned_tasks() -> None:
    """Mark long-stuck pending/running tasks as error so the UI stops spinning."""
    now = datetime.now()
    stuck: list[tuple[dict, float]] = []
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status IN ('pending', 'running') ORDER BY created"
            ).fetchall()
            for row in rows:
                task = dict(row)
                created_str = task.get("created")
                if not created_str:
                    continue
                try:
                    created = datetime.fromisoformat(created_str)
                except ValueError:
                    continue
                age_seconds = (now - created).total_seconds()
                if age_seconds > _ORPHAN_PENDING_THRESHOLD_SECONDS:
                    stuck.append((task, age_seconds))

    for task, age_seconds in stuck:
        previous_status = task.get("status", "pending")
        reason = (
            f"task was {previous_status} for {int(age_seconds)}s "
            f"and timed out; worker thread was lost or stuck"
        )
        _db_update_task(task["task_id"], status="error", error=reason)
        log(f"[{task['task_id']}] recovered orphaned {previous_status} task: {reason}")


# Immediately recover any stuck tasks from a previous process life
_recover_orphaned_tasks()


def _start_orphan_watchdog(interval_seconds: int = 120) -> None:
    """Periodically recover stuck pending/running tasks in the background."""
    def _loop() -> None:
        import time
        while True:
            time.sleep(interval_seconds)
            try:
                _recover_orphaned_tasks()
            except Exception as exc:
                print(f"[watchdog] error: {exc}")

    t = threading.Thread(target=_loop, daemon=True, name="orphan-watchdog")
    t.start()


_start_orphan_watchdog()


# ---------------------------------------------------------------------------
# Platform configuration — single source of truth
# ---------------------------------------------------------------------------

PLATFORM_CONFIG: dict[str, dict] = {
    "douyin":     {"label": "抖音",    "desc": True,  "note": True,  "thumbnail": True,  "thumbnail_dual": True,  "product": True,  "tid": False, "tencent_extra": False},
    "kuaishou":   {"label": "快手",    "desc": True,  "note": True,  "thumbnail": True,  "thumbnail_dual": False, "product": False, "tid": False, "tencent_extra": False},
    "xiaohongshu":{"label": "小红书",  "desc": True,  "note": True,  "thumbnail": True,  "thumbnail_dual": False, "product": False, "tid": False, "tencent_extra": False},
    "bilibili":   {"label": "Bilibili", "desc": True, "note": True, "thumbnail": False, "thumbnail_dual": False, "product": False, "tid": True, "tencent_extra": False},
    "tencent":    {"label": "视频号",  "desc": True,  "note": False, "thumbnail": True,  "thumbnail_dual": True,  "product": False, "tid": False, "tencent_extra": True},
    "tiktok":     {"label": "TikTok",  "desc": False, "note": False, "thumbnail": False, "thumbnail_dual": False, "product": False, "tid": False, "tencent_extra": False},
    "baijiahao":  {"label": "百家号",  "desc": False, "note": False, "thumbnail": False, "thumbnail_dual": False, "product": False, "tid": False, "tencent_extra": False},
}

DESC_PLATFORMS: set[str] = {k for k, v in PLATFORM_CONFIG.items() if v["desc"]}
NOTE_PLATFORMS: set[str] = {k for k, v in PLATFORM_CONFIG.items() if v["note"]}
THUMBNAIL_PLATFORMS: set[str] = {k for k, v in PLATFORM_CONFIG.items() if v["thumbnail"]}
THUMBNAIL_DUAL_PLATFORMS: set[str] = {k for k, v in PLATFORM_CONFIG.items() if v["thumbnail_dual"]}


def _account_files(platform: str | None = None) -> list[dict]:
    """List cookie files stored in COOKIES_DIR. Platform prefix is `{platform}_`."""
    result: list[dict] = []
    for path in sorted(COOKIES_DIR.glob("*.json")):
        if path.name.endswith("_login_qrcode_2026"):
            continue
        if platform:
            if not path.name.startswith(f"{platform}_"):
                continue
        parts = path.stem.split("_", 1)
        plat = parts[0]
        acct = parts[1] if len(parts) > 1 else path.stem
        result.append({
            "platform": plat,
            "account_name": acct,
            "path": str(path),
        })
    return result


COOKIE_MAX_AGE_DAYS = 7


def _quick_check_cookie(platform: str, account: str) -> dict:
    import time
    import json as _json
    
    cookie_path = COOKIES_DIR / f"{platform}_{account}.json"
    
    if not cookie_path.exists():
        return {"valid": False, "reason": "no_file", "age_hours": None, "file_size": None}
    
    try:
        stat = cookie_path.stat()
        age_hours = (time.time() - stat.st_mtime) / 3600
        file_size = stat.st_size
        
        if file_size < 10:
            return {"valid": False, "reason": "empty", "age_hours": age_hours, "file_size": file_size}
        
        content = cookie_path.read_text(encoding="utf-8")
        data = _json.loads(content)
        
        if isinstance(data, dict):
            cookies = data.get("cookies", data.get("session", []))
            if isinstance(cookies, list) and len(cookies) == 0:
                return {"valid": False, "reason": "empty_cookies", "age_hours": age_hours, "file_size": file_size}
        
        if age_hours > COOKIE_MAX_AGE_DAYS * 24:
            return {"valid": True, "reason": "stale", "age_hours": age_hours, "file_size": file_size}
        
        return {"valid": True, "reason": "fresh", "age_hours": age_hours, "file_size": file_size}
        
    except (_json.JSONDecodeError, OSError) as e:
        return {"valid": False, "reason": f"error: {str(e)}", "age_hours": None, "file_size": None}


def _parse_upload_result(stdout: str) -> str | None:
    for line in stdout.splitlines():
        prefix = "[UPLOAD_RESULT]"
        idx = line.find(prefix)
        if idx >= 0:
            return line[idx + len(prefix):].strip()
    return None


def _store_result(task_id: str, stdout: str) -> None:
    raw = _parse_upload_result(stdout)
    if raw:
        try:
            result_json = json.loads(raw)
            _db_update_task(task_id, result=json.dumps(result_json, ensure_ascii=False))
            log(f"[{task_id}] stored upload result: {raw[:200]}")
            # Store publish verification detail separately for quick access
            if isinstance(result_json, dict):
                verified = result_json.get("verified")
                publish_status = result_json.get("publish_status", "")
                if verified is not None or publish_status:
                    detail = json.dumps({
                        "verified": verified,
                        "publish_status": publish_status,
                        "video_url": result_json.get("video_url", ""),
                    }, ensure_ascii=False)
                    _db_update_task(task_id, publish_detail=detail)
                    if verified:
                        log(f"[{task_id}] ✅ 发布已验证: 状态={publish_status}")
                    else:
                        log(f"[{task_id}] ⚠️ 发布未验证: 视频可能未真正发布，请检查平台后台")
        except (json.JSONDecodeError, Exception) as exc:
            log(f"[{task_id}] failed to parse upload result: {exc}")


def _run_sau(task_id: str, argv: list[str]) -> None:
        from sau_cli import main as sau_main  # noqa: E402

        from utils.log import logger as _task_logger

        class _LoguruToDeque:
            def write(self, msg: str) -> int:
                text = msg.rstrip("\n")
                if text:
                    log(text)
                return len(msg)

        _loguru_handler_id: int | None = None
        try:
            _loguru_handler_id = _task_logger.add(
                _LoguruToDeque(),
                format="{message}",
                level="INFO",
            )
            cap = _LogCapture()
            log(f"[{task_id}] start: sau {' '.join(argv)}")
            _db_update_task(task_id, status="running")
            try:
                with redirect_stdout(cap), redirect_stderr(cap):
                    rc = int(sau_main(argv))
                stdout_text = cap.buffer.getvalue()
                if rc != 0:
                    stderr_text = stdout_text.strip()
                    if stderr_text:
                        _db_update_task(task_id, status="failed", code=rc, error=stderr_text)
                else:
                    _db_update_task(task_id, status="success", code=rc)
                    _store_result(task_id, stdout_text)
                log(f"[{task_id}] finished with exit code {rc}")
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 1
                stdout_text = cap.buffer.getvalue()
                if rc != 0:
                    stderr_text = stdout_text.strip()
                    _db_update_task(task_id, status="failed", code=rc, error=stderr_text if stderr_text else None)
                else:
                    _db_update_task(task_id, status="success", code=rc)
                    _store_result(task_id, stdout_text)
                log(f"[{task_id}] finished with exit code {rc}")
            except Exception as exc:
                _db_update_task(task_id, status="error", error=str(exc))
                log(f"[{task_id}] error: {exc}")
        finally:
            if _loguru_handler_id is not None:
                _task_logger.remove(_loguru_handler_id)


def _normalise_schedule(schedule: str | None) -> str | None:
    """Convert HTML datetime-local format (2026-06-19T14:30) to CLI format (2026-06-19 14:30)."""
    if not schedule:
        return None
    return schedule.replace("T", " ").replace("t", " ")


def _headless_flag(headless: object) -> str | None:
    """Normalise headless param to 'true'/'false' or None (unset)."""
    if headless is None:
        return None
    if isinstance(headless, bool):
        return "true" if headless else "false"
    s = str(headless).lower().strip()
    return "true" if s in ("true", "1", "yes") else "false"


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/api/accounts")
def list_accounts():
    platform = request.args.get("platform")
    return jsonify({
        "success": True,
        "data": _account_files(platform),
    })


@app.post("/api/accounts/delete")
def delete_account():
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


@app.post("/api/accounts/check")
def check_account():
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")
    account = payload.get("account")
    deep = payload.get("deep", False)

    if not platform or not account:
        return jsonify({"success": False, "message": "platform and account are required"}), 400

    quick_result = _quick_check_cookie(platform, account)
    
    if not deep:
        return jsonify({
            "success": True,
            "data": {
                "quick": quick_result,
                "deep_check": None,
                "task_id": None,
            }
        })

    argv = [platform, "check", "--account", account]
    task_id = _new_task_id("check")
    _db_insert_task(
        task_id=task_id,
        status="pending",
        platform=platform,
        action="check",
        account=account,
        created=datetime.now().isoformat(timespec="seconds"),
        argv=argv,
    )
    task_executor.submit(_run_sau, task_id, argv)
    return jsonify({
        "success": True,
        "data": {
            "quick": quick_result,
            "deep_check": "pending",
            "task_id": task_id,
        }
    })


@app.post("/api/accounts/check-all")
def check_all_accounts():
    accounts = _account_files()
    results: list[dict] = []
    
    for acct in accounts:
        quick_result = _quick_check_cookie(acct["platform"], acct["account_name"])
        results.append({
            "platform": acct["platform"],
            "account": acct["account_name"],
            "quick": quick_result,
        })
    
    return jsonify({"success": True, "data": results})


@app.post("/api/accounts/login")
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
        task_id=task_id,
        status="pending",
        platform=platform,
        action="login",
        account=account,
        created=datetime.now().isoformat(timespec="seconds"),
        argv=argv,
    )
    task_executor.submit(_run_sau, task_id, argv)
    return jsonify({"success": True, "data": {"task_id": task_id}})


# Platforms that support QR-code-based login via qrcode_callback
_QR_LOGIN_PLATFORMS = {"douyin", "kuaishou", "xiaohongshu", "tencent"}


@app.get("/api/accounts/login/sse")
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
        from sau_cli import (
            login_douyin_account,
            login_kuaishou_account,
            login_xiaohongshu_account,
            login_tencent_account,
        )

        headless = headless_str.lower() in ("true", "1", "yes")

        _LOGIN_FN_MAP = {
            "douyin": login_douyin_account,
            "kuaishou": login_kuaishou_account,
            "xiaohongshu": login_xiaohongshu_account,
            "tencent": login_tencent_account,
        }

        login_fn = _LOGIN_FN_MAP.get(platform)
        if not login_fn:
            q.put({"event": "error", "data": {"message": f"Unsupported platform: {platform}"}})
            return

        try:
            result: dict = asyncio.run(login_fn(account, headless=headless, qrcode_callback=_qrcode_callback))
            q.put({"event": "result", "data": result})
        except Exception as exc:
            q.put({"event": "result", "data": {"success": False, "message": str(exc)}})

    thread = threading.Thread(target=_run_login, daemon=True)
    thread.start()

    def generate() -> Generator:
        while thread.is_alive() or not q.empty():
            try:
                msg = q.get(timeout=2)
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'], ensure_ascii=False)}\n\n"
                if msg["event"] in ("result", "error"):
                    break
            except _queue.Empty:
                yield f"event: ping\ndata: {json.dumps({'ts': datetime.now().isoformat()})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/upload/video")
def upload_video():
    platform = request.form.get("platform")
    account = request.form.get("account")
    title = request.form.get("title")
    desc = request.form.get("desc", "")
    tags = request.form.get("tags", "")
    schedule = request.form.get("schedule")
    product_link = request.form.get("product_link", "")
    product_title = request.form.get("product_title", "")
    tid = request.form.get("tid")
    headless = request.form.get("headless")
    short_title = request.form.get("short_title", "")
    category = request.form.get("category", "")
    is_draft = request.form.get("is_draft", "")
    file_data = request.form.get("file_data")
    thumbnail = request.form.get("thumbnail")
    thumbnail_landscape = request.form.get("thumbnail_landscape")
    thumbnail_portrait = request.form.get("thumbnail_portrait")

    if not platform or not account or not title:
        return jsonify({"success": False, "message": "platform, account and title are required"}), 400

    argv = [
        platform,
        "upload-video",
        "--account", account,
        "--title", title,
        "--tags", tags,
    ]
    hflag = _headless_flag(headless)
    if hflag:
        argv.append("--headless" if hflag == "true" else "--headed")
    if desc and platform in DESC_PLATFORMS:
        argv += ["--desc", desc]

    uploaded_file = request.files.get("file")
    if uploaded_file and uploaded_file.filename:
        raw = uploaded_file.read()
        ext = Path(uploaded_file.filename).suffix
        if len(raw) < MIN_UPLOAD_BYTES:
            return jsonify({"success": False, "message": f"Uploaded file is too small: {len(raw)} bytes (min {MIN_UPLOAD_BYTES})"}), 400
        name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOADS_DIR / name
        file_path.write_bytes(raw)
        log(f"[upload] saved uploaded file: {file_path} ({len(raw)} bytes)")
    else:
        file_path = _save_data_uri(file_data) if file_data else None

    if not file_path:
        return jsonify({"success": False, "message": "file_data is required (base64 / data URI or multipart file field 'file')"}), 400
    argv += ["--file", str(file_path)]

    if schedule:
        argv += ["--schedule", _normalise_schedule(schedule)]
    if thumbnail and platform in THUMBNAIL_PLATFORMS:
        thumb_path = _save_data_uri(thumbnail)
        if thumb_path:
            argv += ["--thumbnail", str(thumb_path)]
    if thumbnail_landscape and platform in THUMBNAIL_DUAL_PLATFORMS:
        thumb_path = _save_data_uri(thumbnail_landscape)
        if thumb_path:
            argv += ["--thumbnail-landscape", str(thumb_path)]
    if thumbnail_portrait and platform in THUMBNAIL_DUAL_PLATFORMS:
        thumb_path = _save_data_uri(thumbnail_portrait)
        if thumb_path:
            argv += ["--thumbnail-portrait", str(thumb_path)]
    if platform == "douyin":
        if product_link:
            argv += ["--product-link", product_link]
        if product_title:
            argv += ["--product-title", product_title]
    if platform == "bilibili":
        argv += ["--tid", str(tid if tid else 233)]
    if platform == "tencent":
        config = PLATFORM_CONFIG.get("tencent", {})
        if config.get("tencent_extra"):
            if short_title:
                argv += ["--short-title", short_title]
            if category:
                argv += ["--category", category]
            if is_draft in ("true", "1"):
                argv.append("--draft")

    task_id = _new_task_id("upload-video")
    _db_insert_task(
        task_id=task_id,
        status="pending",
        platform=platform,
        action="upload-video",
        account=account,
        created=datetime.now().isoformat(timespec="seconds"),
        argv=argv,
    )
    task_executor.submit(_run_sau, task_id, argv)
    return jsonify({"success": True, "data": {"task_id": task_id}})
@app.post("/api/upload/note")
def upload_note():
    # Support both JSON (data-URI) and multipart/form-data (file fields images_0, images_1, ...)
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        platform = payload.get("platform")
        account = payload.get("account")
        title = payload.get("title")
        note = payload.get("note", "")
        tags = payload.get("tags", "")
        schedule = payload.get("schedule")
        headless = payload.get("headless")
        raw_images: list[str] = payload.get("images", [])

        if not platform or not account or not title:
            return jsonify({"success": False, "message": "platform, account and title are required"}), 400

        saved_images: list[str] = []
        for uri in raw_images:
            path = _save_data_uri(uri)
            if path:
                saved_images.append(str(path))
            else:
                log(f"[upload] failed to decode image: {uri[:40]}...")
    else:
        platform = request.form.get("platform")
        account = request.form.get("account")
        title = request.form.get("title")
        note = request.form.get("note", "")
        tags = request.form.get("tags", "")
        schedule = request.form.get("schedule")
        headless = request.form.get("headless")

        if not platform or not account or not title:
            return jsonify({"success": False, "message": "platform, account and title are required"}), 400

        # Collect uploaded images — fields named images_0, images_1, ...
        saved_images: list[str] = []
        idx = 0
        while True:
            field = f"images_{idx}"
            f = request.files.get(field)
            if not f or not f.filename:
                break
            raw = f.read()
            ext = Path(f.filename).suffix
            name = f"{uuid.uuid4().hex}{ext}"
            path = UPLOADS_DIR / name
            path.write_bytes(raw)
            log(f"[upload] saved note image: {path} ({len(raw)} bytes)")
            saved_images.append(str(path))
            idx += 1

    if not saved_images:
        return jsonify({"success": False, "message": "至少需要一张有效图片"}), 400

    if platform not in NOTE_PLATFORMS:
        return jsonify({"success": False, "message": f"平台 {platform} 不支持图文上传"}), 400

    argv = [
        platform,
        "upload-note",
        "--account", account,
        "--title", title,
        "--note", note,
        "--tags", tags,
        "--images", *saved_images,
    ]
    hflag = _headless_flag(headless)
    if hflag:
        argv.append("--headless" if hflag == "true" else "--headed")
    if schedule:
        argv += ["--schedule", _normalise_schedule(schedule)]

    task_id = _new_task_id("upload-note")
    _db_insert_task(
        task_id=task_id,
        status="pending",
        platform=platform,
        action="upload-note",
        account=account,
        created=datetime.now().isoformat(timespec="seconds"),
        argv=argv,
    )
    task_executor.submit(_run_sau, task_id, argv)
    return jsonify({"success": True, "data": {"task_id": task_id}})


@app.get("/api/tasks")
def list_tasks():
    rows = _db_get_all_tasks()
    return jsonify({
        "success": True,
        "data": rows,
    })


@app.post("/api/tasks/retry")
def retry_task():
    payload = request.get_json(silent=True) or {}
    task_id = payload.get("task_id")

    if not task_id:
        return jsonify({"success": False, "message": "task_id is required"}), 400

    task = _db_get_task(task_id)
    if not task:
        return jsonify({"success": False, "message": f"Task not found: {task_id}"}), 404

    stored_argv = task.get("argv")
    if not stored_argv:
        return jsonify({"success": False, "message": "Cannot retry: no stored argv for this task"}), 400

    try:
        argv = json.loads(stored_argv)
    except (json.JSONDecodeError, TypeError):
        return jsonify({"success": False, "message": "Cannot retry: invalid stored argv"}), 400

    new_task_id = _new_task_id("retry")
    _db_insert_task(
        task_id=new_task_id,
        status="pending",
        platform=task.get("platform", "") or "",
        action=f"retry-{task.get('action', 'unknown')}",
        account=task.get("account", "") or "",
        created=datetime.now().isoformat(timespec="seconds"),
        argv=argv,
    )
    task_executor.submit(_run_sau, new_task_id, argv)
    log(f"[{new_task_id}] retry of {task_id}: sau {' '.join(argv)}")
    return jsonify({"success": True, "data": {"task_id": new_task_id}})


@app.post("/api/tasks/delete")
def delete_task():
    payload = request.get_json(silent=True) or {}
    task_id = payload.get("task_id")

    if not task_id:
        return jsonify({"success": False, "message": "task_id is required"}), 400

    task = _db_get_task(task_id)
    if not task:
        return jsonify({"success": False, "message": f"Task not found: {task_id}"}), 404

    if task.get("status") in ("pending", "running"):
        return jsonify({"success": False, "message": "Cannot delete running task"}), 400

    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()

    log(f"[tasks] deleted task: {task_id}")
    return jsonify({"success": True, "message": f"Task {task_id} deleted"})


@app.post("/api/tasks/clear")
def clear_tasks():
    payload = request.get_json(silent=True) or {}
    status_filter = payload.get("status", ["success", "failed", "error"])
    
    if isinstance(status_filter, str):
        status_filter = [status_filter]

    placeholders = ",".join("?" for _ in status_filter)
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                f"DELETE FROM tasks WHERE status IN ({placeholders})",
                status_filter
            )
            deleted = cursor.rowcount
            conn.commit()

    log(f"[tasks] cleared {deleted} tasks with status: {status_filter}")
    return jsonify({"success": True, "data": {"deleted": deleted}})


@app.post("/api/tasks/add")
def add_task():
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")
    action = payload.get("action")
    account = payload.get("account")
    argv = payload.get("argv")

    if not platform or not action or not account:
        return jsonify({"success": False, "message": "platform, action, account are required"}), 400

    if not argv:
        argv = [platform, action, "--account", account]
        if action == "upload-video":
            title = payload.get("title", "Untitled")
            file_path = payload.get("file")
            if not file_path:
                return jsonify({"success": False, "message": "file is required for upload-video"}), 400
            argv += ["--title", title, "--file", file_path]
        elif action == "upload-note":
            title = payload.get("title", "Untitled")
            images = payload.get("images", [])
            if not images:
                return jsonify({"success": False, "message": "images are required for upload-note"}), 400
            argv += ["--title", title, "--images", *images]

    task_id = _new_task_id(action)
    _db_insert_task(
        task_id=task_id,
        status="pending",
        platform=platform,
        action=action,
        account=account,
        created=datetime.now().isoformat(timespec="seconds"),
        argv=argv,
    )
    task_executor.submit(_run_sau, task_id, argv)
    log(f"[{task_id}] manual task: sau {' '.join(argv)}")
    return jsonify({"success": True, "data": {"task_id": task_id}})


@app.get("/api/logs")
def get_logs():
    after = request.args.get("after")
    task_id = request.args.get("task_id")
    return jsonify({
        "success": True,
        "data": _db_get_logs(after, task_id),
    })


def _list_proposals() -> list[dict]:
    """Read openspec change proposals from openspec/changes/*/_index.json."""
    changes_dir = BASE_DIR / "openspec" / "changes"
    if not changes_dir.is_dir():
        return []
    proposals: list[dict] = []
    for change_dir in sorted(changes_dir.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        index_file = change_dir / "_index.json"
        if index_file.is_file():
            try:
                data = json.loads(index_file.read_text())
                data["dir"] = change_dir.name
                proposals.append(data)
            except (json.JSONDecodeError, OSError):
                pass
    return proposals


@app.get("/api/proposals")
def list_proposals():
    """List openspec change proposals visible to the frontend."""
    return jsonify({"success": True, "data": _list_proposals()})


def _frontend_dist() -> Path | None:
    dist = BASE_DIR / "sau_web" / "frontend" / "dist"
    return dist if (dist / "index.html").exists() else None


@app.get("/")
def index():
    dist = _frontend_dist()
    if dist:
        return Response((dist / "index.html").read_text(encoding="utf-8"), mimetype="text/html")
    return Response(
        "<h1>social-auto-upload web shell</h1><p>frontend not built yet.</p>",
        mimetype="text/html",
    )


if __name__ == "__main__":
    import atexit
    atexit.register(task_executor.shutdown, wait=False)
    app.run(host="0.0.0.0", port=5409, debug=True)
