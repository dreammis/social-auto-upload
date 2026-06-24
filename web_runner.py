from __future__ import annotations

import asyncio
import base64
import binascii
import json
import os
import queue as _queue
import re
import sqlite3
import sys
import tempfile
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Generator

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from utils.log import logger as _task_logger
import requests as http_requests
import patchright

from web_runner.db import DB_PATH, BASE_DIR, db_lock, init_db, get_connection

COOKIES_DIR = BASE_DIR / "cookies"
COOKIES_DIR.mkdir(exist_ok=True)

UPLOADS_DIR = BASE_DIR / ".sau_uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB
def _parse_cors_allowed_origins(raw_value: str | None) -> list[str]:
    """解析环境变量启明的 CORS 来源。空值返回 []，避免思首中默许 "*"。

    用法:
        SAU_CORS_ALLOWED_ORIGINS="https://app.example.com,http://localhost:5173"

    - 不设置 / 设置为空 → 返回 []，调用方不会启用 CORS（保持默认拒绝）。
    - 多值用逗号分隔，前后空格被去掉；空项被跳过。
    """
    if not raw_value:
        return []
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


_cors_allowed_origins = _parse_cors_allowed_origins(os.environ.get("SAU_CORS_ALLOWED_ORIGINS"))
if _cors_allowed_origins:
    CORS(app, resources={r"/api/*": {"origins": _cors_allowed_origins}})
    _task_logger.info(f"[web] CORS enabled for /api/* origins: {_cors_allowed_origins}")
else:
    _task_logger.warning(
        "[web] CORS disabled (SAU_CORS_ALLOWED_ORIGINS is unset/empty). "
        "Set e.g. SAU_CORS_ALLOWED_ORIGINS='http://localhost:5173,http://localhost:5174' "
        "to allow cross-origin clients."
    )

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

# Minimum acceptable upload size in bytes (~100KB). Reject obvious junk/empty data URIs early.
MIN_UPLOAD_BYTES = 10240

# AI Content Generation - OpenRoute API Configuration
OPENROUTE_API_KEY = os.environ.get("OPENROUTE_API_KEY", "")
OPENROUTE_BASE_URL = "https://openrouter.ai/api/v1"


def _get_openroute_key() -> str:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT value FROM ai_config WHERE key = 'openroute_api_key'").fetchone()
            if row and row[0]:
                return row[0]
    return OPENROUTE_API_KEY


def _set_openroute_key(key: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ai_config (key, value, updated) VALUES (?, ?, ?)",
                ("openroute_api_key", key, now),
            )
            conn.commit()


def _delete_openroute_key() -> None:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM ai_config WHERE key = 'openroute_api_key'")
            conn.commit()


# ── Multi-key pool helpers (rate-limit rotation) ──────────────────────────────
_KEY_POOL_COOLDOWN = 300  # seconds to skip a rate-limited key


def _migrate_legacy_key_to_pool() -> None:
    """One-time migration: move the legacy single OpenRouter key into the new pool.

    Caller MUST guarantee ``_init_db()`` has run first so that both ``ai_config``
    and ``ai_api_keys`` exist. ``_init_db()`` invokes this at the end so the
    dependency is explicit.
    """
    legacy_key = ""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT value FROM ai_config WHERE key = 'openroute_api_key'").fetchone()
            if row and row[0]:
                legacy_key = row[0]
    if not legacy_key:
        return
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            already = conn.execute("SELECT 1 FROM ai_api_keys WHERE api_key = ?", (legacy_key,)).fetchone()
            if not already:
                masked = legacy_key[:8] + "****" + legacy_key[-4:] if len(legacy_key) > 12 else "****"
                conn.execute(
                    "INSERT OR IGNORE INTO ai_api_keys (api_key, masked, created) VALUES (?, ?, ?)",
                    (legacy_key, masked, datetime.now().isoformat(timespec="seconds")),
                )
                conn.commit()
                log("[AI] migrated legacy API key to multi-key pool")


def _get_all_keys() -> list[dict]:
    """Return all API keys in the pool with their metadata."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM ai_api_keys ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]


def _add_api_key(key: str) -> dict:
    """Add a key to the pool. Returns the new row dict or raises IntegrityError."""
    masked = key[:8] + "****" + key[-4:] if len(key) > 12 else "****"
    now = datetime.now().isoformat(timespec="seconds")
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO ai_api_keys (api_key, masked, created) VALUES (?, ?, ?)",
                (key, masked, now),
            )
            conn.commit()
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            _bust_key_cache()
            return {"id": row_id, "masked": masked, "created": now}


def _delete_api_key(key_id: int) -> bool:
    """Delete a key by id. Returns True if a row was deleted."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute("DELETE FROM ai_api_keys WHERE id = ?", (key_id,))
            conn.commit()
            _bust_key_cache()
            return cur.rowcount > 0


def _mark_rate_limited(key: str) -> None:
    """Mark a key as having hit a 429 rate limit."""
    now = datetime.now().isoformat(timespec="seconds")
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE ai_api_keys SET rate_limited_at = ? WHERE api_key = ?",
                (now, key),
            )
            conn.commit()
            _bust_key_cache()


_key_cache: list[dict] = []
_key_cache_mtime: float = 0.0
_KEY_CACHE_TTL = 5.0  # seconds


def _get_all_keys_cached() -> list[dict]:
    """Return keys from cache, refreshing from DB every _KEY_CACHE_TTL seconds."""
    import time
    global _key_cache, _key_cache_mtime
    now = time.time()
    if not _key_cache or now - _key_cache_mtime > _KEY_CACHE_TTL:
        _key_cache = _get_all_keys()
        _key_cache_mtime = now
    return _key_cache


def _bust_key_cache() -> None:
    """Force a refresh on next read (call after add/delete/mark)."""
    global _key_cache_mtime
    _key_cache_mtime = 0.0


def _get_next_key() -> str:
    """Return the next available API key using round-robin rotation.

    Skips keys that were rate-limited within the cooldown window.
    Returns an empty string if no keys are available.
    """
    all_keys = _get_all_keys_cached()
    if not all_keys:
        return ""

    # Auto-clear rate-limited keys whose cooldown has expired
    import time
    now_ts = time.time()
    for k in all_keys:
        if k["rate_limited_at"]:
            try:
                rl_ts = datetime.fromisoformat(k["rate_limited_at"]).timestamp()
                if now_ts - rl_ts >= _KEY_POOL_COOLDOWN:
                    with db_lock:
                        with sqlite3.connect(DB_PATH) as conn:
                            conn.execute(
                                "UPDATE ai_api_keys SET rate_limited_at = NULL WHERE id = ?",
                                (k["id"],),
                            )
                            conn.commit()
                            _bust_key_cache()
                    k["rate_limited_at"] = None
            except (ValueError, KeyError):
                pass

    # Prefer a non-rate-limited key
    healthy = [k for k in all_keys if not k["rate_limited_at"]]
    if healthy:
        # Simple round-robin: pick the first healthy key (db ordering by id)
        # A persistent cursor is unnecessary — we just cycle through all healthy ones
        return healthy[0]["api_key"]

    # All keys rate-limited — use the one that was limited earliest (closest to recovery)
    all_keys.sort(key=lambda k: k["rate_limited_at"] or "")
    return all_keys[0]["api_key"]


def _get_openroute_key_with_fallback(key_id: int | None = None) -> str:
    """Get a specific key by id, or the next available key via rotation.

    Falls back to the legacy single-key config if the pool is empty.
    """
    if key_id is not None:
        with db_lock:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT api_key FROM ai_api_keys WHERE id = ?", (key_id,)).fetchone()
                if row and row[0]:
                    return row[0]
    key = _get_next_key()
    if key:
        return key
    # Fallback to legacy single-key storage
    return _get_openroute_key()


def _has_any_api_key() -> bool:
    """Check if there is at least one API key in the pool or legacy storage."""
    if _get_all_keys():
        return True
    return bool(_get_openroute_key())
AI_MODELS = {
    "google/gemma-4-26b-a4b-it:free": "Gemma 4 26B",
    "qwen/qwen3-coder:free": "Qwen3 Coder 480B",
    "qwen/qwen3-next-80b-a3b-instruct:free": "Qwen3 Next 80B",
    "nvidia/nemotron-3-ultra-550b-a55b:free": "Nemotron 3 Ultra 550B",
    "openai/gpt-oss-120b:free": "GPT-OSS 120B",
}
_ai_request_semaphore = threading.Semaphore(5)
_ai_request_queue: _queue.Queue = _queue.Queue()
_ai_queue_worker_started = False
_ai_queue_lock = threading.Lock()


def _build_media_content(images: list, prompt: str = "") -> list:
    user_content = []
    for img in images:
        if isinstance(img, dict) and img.get("url"):
            url = img["url"]
        elif isinstance(img, str):
            url = img
        else:
            continue
        if url.startswith("data:video/"):
            user_content.append({"type": "video_url", "video_url": {"url": url}})
        else:
            user_content.append({"type": "image_url", "image_url": {"url": url}})
    if prompt:
        user_content.append({"type": "text", "text": prompt})
    return user_content


PLATFORM_PROMPTS = {
    "douyin": "你是抖音内容创作专家。生成的内容需要：\n- 标题简短有力，15字以内，善用悬念和数字\n- 描述节奏明快，适合短视频配文\n- 标签紧跟热点，使用抖音流行标签风格\n- 语气年轻化、有感染力",
    "kuaishou": "你是快手内容创作专家。生成的内容需要：\n- 标题接地气，贴近生活\n- 描述真实自然，有老铁感\n- 标签覆盖生活、技能类关键词\n- 语气真诚、朴实",
    "xiaohongshu": "你是小红书内容创作专家。生成的内容需要：\n- 标题善用emoji，制造种草感\n- 描述采用分享式口吻，有体验感和干货\n- 标签精准覆盖搜索关键词\n- 语气亲切、有生活品味",
    "bilibili": "你是B站内容创作专家。生成的内容需要：\n- 标题可以稍长，有信息量\n- 描述内容详实，适合深度内容受众\n- 标签覆盖分区关键词和兴趣标签\n- 语气专业但不失趣味",
    "tencent": "你是视频号内容创作专家。生成的内容需要：\n- 标题稳重大气\n- 描述适合微信生态分享\n- 标签简洁精准\n- 语气成熟、有品质感",
    "tiktok": "你是TikTok内容创作专家。生成的内容需要：\n- 标题英文，简短有冲击力\n- 描述英文，适合国际受众\n- 标签使用英文热门标签\n- 语气活泼、国际化",
    "baijiahao": "你是百家号内容创作专家。生成的内容需要：\n- 标题信息量大，适合资讯类内容\n- 描述结构清晰，有条理\n- 标签覆盖行业关键词\n- 语气正式、有权威感",
}

DEFAULT_SYSTEM_PROMPT = "你是一个专业的内容创作助手，擅长为社交媒体平台生成高质量的帖子内容。请用中文回复。"

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
    # Forward to SSE progress subscribers
    import re as _re
    m = _re.match(r"\[([^\]]+)\]", message)
    if m:
        task_id = m.group(1)
        with _progress_sub_lock:
            queues = _progress_subscribers.get(task_id, [])
            for q in queues:
                try:
                    q.put_nowait(message)
                except _queue.Full:
                    pass


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
    except (binascii.Error, UnicodeEncodeError, OSError, ValueError, TypeError) as exc:
        log(f"[upload] failed to save data uri: {type(exc).__name__}")
        return None


def _download_url(url: str) -> Path | None:
    """Download a URL to a temp file and return the path."""
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
    """Write bytes to an upload temp file, respecting minimum size."""
    if len(raw) < MIN_UPLOAD_BYTES:
        log(f"[upload] rejected file: payload is only {len(raw)} bytes (min {MIN_UPLOAD_BYTES})")
        return None
    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOADS_DIR / name
    path.write_bytes(raw)
    log(f"[upload] saved temp file: {path} ({len(raw)} bytes)")
    return path


init_db()
_migrate_legacy_key_to_pool()


def _sync_cookie_files_to_db() -> None:
    """Import existing cookie files into account_authorizations on startup.

    For each ``{platform}_{account_name}.json`` in COOKIES_DIR that is NOT yet
    tracked in the ``account_authorizations`` table, create (or reuse) an
    ``account_groups`` row named ``account_name`` and insert an authorization
    row pointing at the cookie file.  Idempotent — safe to call every startup.
    """


@app.errorhandler(Exception)
def _handle_unexpected_error(exc):
    if isinstance(exc, HTTPException):
        return exc.get_response()
    log(f"[error] unhandled exception: {exc}")
    return jsonify({"success": False, "message": "Internal server error"}), 500


@app.errorhandler(413)
def _handle_request_too_large(exc):
    return jsonify({"success": False, "message": "Request entity too large (max 200MB)"}), 413


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


def _db_get_all_tasks(limit: int | None = None, offset: int = 0) -> list[dict]:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            if limit is not None:
                rows = conn.execute("SELECT * FROM tasks ORDER BY task_id LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            else:
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


def _db_get_logs(after: str | None = None, task_id: str | None = None, limit: int | None = None, offset: int = 0) -> list[dict]:
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            if task_id:
                prefix = f"[{task_id}]"
                escaped_prefix = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                if after:
                    rows = conn.execute(
                        "SELECT ts, message FROM logs WHERE ts > ? AND message LIKE ? ESCAPE '\\' ORDER BY rowid",
                        (after, f"{escaped_prefix}%"),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT ts, message FROM logs WHERE message LIKE ? ESCAPE '\\' ORDER BY rowid",
                        (f"{escaped_prefix}%",),
                    ).fetchall()
            elif after:
                rows = conn.execute(
                    "SELECT ts, message FROM logs WHERE ts > ? ORDER BY rowid", (after,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT ts, message FROM logs ORDER BY rowid"
                ).fetchall()
            result = [dict(row) for row in rows]
            if limit is not None:
                result = result[offset:offset + limit]
            return result


# ---------------------------------------------------------------------------
# DB helpers — error_events (structured failure capture for stalls analytics)
# ---------------------------------------------------------------------------

# Cap long tracebacks / messages to keep SQLite rows bounded. Full stack
# beyond the last frames is rarely useful, and full stdout dumps can be huge.
# 8000 chars covers most deep Playwright selector-chain failures while still
# keeping each row ~4× smaller than an unbounded traceback.
_TRACEBACK_TAIL_CAP = 8000
_MESSAGE_CAP = 2000


def _log_error_event(
    *,
    phase: str,
    task_id: str | None = None,
    platform: str | None = None,
    account: str | None = None,
    action: str | None = None,
    exc: BaseException | None = None,
    exc_type: str | None = None,
    exc_message: str | None = None,
    level: str = "error",
    argv: list[str] | None = None,
    attempt_no: int | None = None,
    retry_count: int | None = None,
    status_code: int | None = None,
) -> int:
    """Write one row to ``error_events``.

    Caller may pass either a live ``exc`` (preferred — captures type, message,
    and traceback automatically) or explicit ``exc_type``/``exc_message`` for
    cases like a CLI non-zero exit or an SSE login result-dict-derived
    failure that does not have a live exception object.
    """
    global _error_event_trim_counter
    if exc is not None:
        derived_exc_type = type(exc).__name__
        derived_exc_message = str(exc)
        tb_text = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
    else:
        derived_exc_type = exc_type or "Unknown"
        derived_exc_message = exc_message or ""
        tb_text = ""
    if len(tb_text) > _TRACEBACK_TAIL_CAP:
        tb_text = "...[truncated]...\n" + tb_text[-_TRACEBACK_TAIL_CAP:]
    if len(derived_exc_message) > _MESSAGE_CAP:
        derived_exc_message = derived_exc_message[:_MESSAGE_CAP] + "...[truncated]"
    if status_code is not None and exc is None:
        derived_exc_message = f"exit code {status_code}: {derived_exc_message}"
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                "INSERT INTO error_events ("
                "ts, task_id, level, phase, platform, account, action, "
                "exc_type, exc_message, traceback, argv, "
                "attempt_no, retry_count, status_code"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    task_id,
                    level,
                    phase,
                    platform,
                    account,
                    action,
                    derived_exc_type,
                    derived_exc_message,
                    tb_text,
                    json.dumps(argv) if argv else None,
                    attempt_no,
                    retry_count,
                    status_code,
                ),
            )
            inserted_id = cur.lastrowid
            _error_event_trim_counter += 1
            if _error_event_trim_counter % 50 == 0:
                conn.execute(
                    "DELETE FROM error_events WHERE id NOT IN "
                    "(SELECT id FROM error_events ORDER BY id DESC LIMIT ?)",
                    (LOG_MAX_ROWS,),
                )
            conn.commit()
    return int(inserted_id or 0)


def _db_get_error_events(
    *,
    after: str | None = None,
    platform: str | None = None,
    account: str | None = None,
    action: str | None = None,
    exc_type: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Read failure rows. Filters are AND-combined; results are newest-first."""
    clauses: list[str] = []
    params: list = []
    if after:
        clauses.append("ts > ?")
        params.append(after)
    if platform:
        clauses.append("platform = ?")
        params.append(platform)
    if account:
        clauses.append("account = ?")
        params.append(account)
    if action:
        clauses.append("action = ?")
        params.append(action)
    if exc_type:
        clauses.append("exc_type = ?")
        params.append(exc_type)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM error_events{where} ORDER BY id DESC"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [limit, offset]
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql, params).fetchall()]


# ---------------------------------------------------------------------------
# Orphaned-task recovery: when web_runner restarts, tasks that were
# pending/running in the previous process are stranded here forever.
# Recover them so the UI doesn't spin endlessly.
# ---------------------------------------------------------------------------

_ORPHAN_PENDING_THRESHOLD_SECONDS = 120  # pending/running for >2 min => treat as killed


def _recover_orphaned_tasks() -> None:
    """Mark stuck pending/running tasks as error; recover orphaned scheduled tasks."""
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

    # in-memory timers lost on restart → recover orphaned scheduled tasks
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            scheduled_rows = conn.execute(
                "SELECT * FROM tasks WHERE status = 'scheduled' ORDER BY created"
            ).fetchall()
    for task in scheduled_rows:
        task_dict = dict(task)
        reason = "server restarted, scheduled timer was lost — please retry"
        _db_update_task(task_dict["task_id"], status="error", error=reason)
        log(f"[{task_dict['task_id']}] recovered orphaned scheduled task: {reason}")


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
            except (sqlite3.OperationalError, OSError, ValueError, KeyError) as exc:
                print(f"[watchdog] error: {type(exc).__name__}")

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
    "tencent":    {"label": "视频号",  "desc": True,  "note": True,  "thumbnail": True,  "thumbnail_dual": True,  "product": False, "tid": False, "tencent_extra": True},
    "tiktok":     {"label": "TikTok",  "desc": False, "note": False, "thumbnail": False, "thumbnail_dual": False, "product": False, "tid": False, "tencent_extra": False},
    "baijiahao":  {"label": "百家号",  "desc": False, "note": False, "thumbnail": False, "thumbnail_dual": False, "product": False, "tid": False, "tencent_extra": False},
}

DESC_PLATFORMS: set[str] = {k for k, v in PLATFORM_CONFIG.items() if v["desc"]}
NOTE_PLATFORMS: set[str] = {k for k, v in PLATFORM_CONFIG.items() if v["note"]}
THUMBNAIL_PLATFORMS: set[str] = {k for k, v in PLATFORM_CONFIG.items() if v["thumbnail"]}
THUMBNAIL_DUAL_PLATFORMS: set[str] = {k for k, v in PLATFORM_CONFIG.items() if v["thumbnail_dual"]}


def _sync_cookie_files_to_db() -> None:
    """Import existing cookie files into account_authorizations on startup.

    For each ``{platform}_{account_name}.json`` in COOKIES_DIR that is NOT yet
    tracked in the ``account_authorizations`` table, create (or reuse) an
    ``account_groups`` row named ``account_name`` and insert an authorization
    row pointing at the cookie file.  Idempotent — safe to call every startup.
    """
    _SKIP_SUFFIX = "_login_qrcode_2026"
    _VALID_PLATFORMS = set(PLATFORM_CONFIG)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        existing = {
            (row["platform"], row["cookie_file"])
            for row in conn.execute(
                "SELECT platform, cookie_file FROM account_authorizations"
            ).fetchall()
        }

        for path in sorted(COOKIES_DIR.glob("*.json")):
            if path.name.endswith(_SKIP_SUFFIX):
                continue
            parts = path.stem.split("_", 1)
            if len(parts) != 2:
                continue
            platform, account_name = parts
            if platform not in _VALID_PLATFORMS:
                continue
            cookie_file = str(path)
            if (platform, cookie_file) in existing:
                continue

            row = conn.execute(
                "SELECT id FROM account_groups WHERE name = ?", (account_name,)
            ).fetchone()
            if row:
                group_id = row["id"]
            else:
                conn.execute(
                    "INSERT INTO account_groups (name, created) VALUES (?, ?)",
                    (account_name, datetime.now().isoformat(timespec="seconds")),
                )
                group_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            try:
                conn.execute(
                    "INSERT INTO account_authorizations "
                    "(group_id, platform, cookie_file, created) VALUES (?, ?, ?, ?)",
                    (group_id, platform, cookie_file,
                     datetime.now().isoformat(timespec="seconds")),
                )
            except sqlite3.IntegrityError:
                pass

        conn.commit()


_sync_cookie_files_to_db()


def _account_files(platform: str | None = None) -> list[dict]:
    """List accounts from account_authorizations table (single source of truth)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT platform, cookie_file FROM account_authorizations"
        params: list[str] = []
        if platform:
            query += " WHERE platform = ?"
            params.append(platform)
        query += " ORDER BY sort_order ASC"
        auths = conn.execute(query, params).fetchall()
        result: list[dict] = []
        for auth in auths:
            cookie_path = Path(auth["cookie_file"])
            parts = cookie_path.stem.split("_", 1)
            account_name = parts[1] if len(parts) > 1 else cookie_path.stem
            result.append({
                "platform": auth["platform"],
                "account_name": account_name,
                "path": str(cookie_path),
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
            return {"valid": False, "reason": "stale", "age_hours": age_hours, "file_size": file_size}
        
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
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            log(f"[{task_id}] failed to parse upload result: {type(exc).__name__}")


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
                    task = _db_get_task(task_id) or {}
                    _log_error_event(
                        phase="cli",
                        task_id=task_id,
                        platform=task.get("platform"),
                        account=task.get("account"),
                        action=task.get("action"),
                        exc_type="NonZeroExit",
                        exc_message=stderr_text or f"exit code {rc}",
                        status_code=rc,
                        argv=argv,
                    )
                else:
                    _db_update_task(task_id, status="success", code=rc)
                    _store_result(task_id, stdout_text)
                log(f"[{task_id}] finished with exit code {rc}")
            except (patchright.async_api.Error, OSError, asyncio.TimeoutError, sqlite3.OperationalError, RuntimeError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                _db_update_task(task_id, status="error", error=str(exc))
                task = _db_get_task(task_id) or {}
                _log_error_event(
                    phase="cli",
                    task_id=task_id,
                    platform=task.get("platform"),
                    account=task.get("account"),
                    action=task.get("action"),
                    exc=exc,
                    argv=argv,
                )
                log(f"[{task_id}] error: {exc}")
        finally:
            if _loguru_handler_id is not None:
                _task_logger.remove(_loguru_handler_id)


def _schedule_task(task_id: str, argv: list[str], schedule_time: datetime) -> None:
    """Schedule a task to run at the specified time via system timer (not platform scheduling).

    The CLI argv must NOT include --schedule, so the uploader uses immediate mode.
    """
    now = datetime.now()
    delay = (schedule_time - now).total_seconds()
    if delay <= 0:
        log(f"[{task_id}] schedule time already passed ({schedule_time.isoformat()}), running immediately")
        _db_update_task(task_id, status="pending")
        task_executor.submit(_run_sau, task_id, argv)
        return

    log(f"[{task_id}] scheduled for {schedule_time.isoformat()} (in {int(delay)}s)")

    def _run() -> None:
        _db_update_task(task_id, status="pending")
        task_executor.submit(_run_sau, task_id, argv)
        with _timer_lock:
            _scheduled_timers.pop(task_id, None)

    timer = threading.Timer(delay, _run)
    timer.daemon = True
    timer.start()
    with _timer_lock:
        _scheduled_timers[task_id] = timer


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
_QR_LOGIN_PLATFORMS = {"douyin", "kuaishou", "xiaohongshu", "tencent", "bilibili", "tiktok", "baijiahao"}


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
        try:
            from cli.platforms import (
                douyin,
                kuaishou,
                xiaohongshu,
                tencent,
                bilibili,
                tiktok,
                baijiahao,
            )

            headless = headless_str.lower() in ("true", "1", "yes")

            _LOGIN_FN_MAP = {
                "douyin": douyin.login,
                "kuaishou": kuaishou.login,
                "xiaohongshu": xiaohongshu.login,
                "tencent": tencent.login,
                "bilibili": bilibili.login,
                "tiktok": tiktok.login,
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
                    phase="sse_login",
                    platform=platform,
                    account=account,
                    action="login",
                    exc_type=f'LoginFailed[{result.get("status", "unknown")}]',
                    exc_message=result.get("message", ""),
                )
        except (patchright.async_api.Error, OSError, asyncio.TimeoutError, RuntimeError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            q.put({"event": "result", "data": {"success": False, "message": str(exc)}})
            _log_error_event(
                phase="sse_login",
                platform=platform,
                account=account,
                action="login",
                exc=exc,
            )

    thread = threading.Thread(target=_run_login, daemon=True)
    thread.start()

    def generate() -> Generator:
        # Force WSGI/proxy send buffer flush immediately so the browser EventSource
        # receives the HTTP 200 + headers within milliseconds. Without this, tiny
        # SSE payloads (e.g. Bilibili's ~150B QR-code URL) sit in the Vite dev proxy
        # 4–8 KB buffer until idle timeout, which closes the connection and fires
        # eventSource.onerror on the frontend.
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
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/upload/progress")
def upload_progress_sse():
    task_id = request.args.get("task_id", "")
    if not task_id:
        return jsonify({"success": False, "message": "task_id is required"}), 400

    task = _db_get_task(task_id)
    if not task:
        return jsonify({"success": False, "message": f"Task not found: {task_id}"}), 404

    terminal_statuses = {"success", "failed", "error"}
    if task.get("status") in terminal_statuses:
        return jsonify({
            "success": True,
            "data": {
                "status": task["status"],
                "code": task.get("code"),
                "error": task.get("error"),
                "result": task.get("result"),
            },
        })

    with _progress_sub_lock:
        active_count = sum(len(qs) for qs in _progress_subscribers.values())
        if active_count >= _MAX_SSE_CONNECTIONS:
            return jsonify({"success": False, "message": "Too many SSE connections"}), 429

    q: _queue.Queue = _queue.Queue()

    with _progress_sub_lock:
        _progress_subscribers.setdefault(task_id, []).append(q)

    def generate() -> Generator:
        yield f": {' ' * 4096}\n\n"
        start_time = time.time()
        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > _SSE_TIMEOUT_SECONDS:
                    yield f"event: error\ndata: {json.dumps({'message': 'SSE timeout'}, ensure_ascii=False)}\n\n"
                    break

                try:
                    msg = q.get(timeout=2)
                    yield f"event: log\ndata: {json.dumps({'message': msg}, ensure_ascii=False)}\n\n"
                except _queue.Empty:
                    pass

                task = _db_get_task(task_id)
                if task and task.get("status") in terminal_statuses:
                    yield f"event: done\ndata: {json.dumps({'status': task['status'], 'code': task.get('code'), 'error': task.get('error'), 'result': task.get('result')}, ensure_ascii=False)}\n\n"
                    break

                yield f"event: ping\ndata: {json.dumps({'ts': datetime.now().isoformat()})}\n\n"
        finally:
            with _progress_sub_lock:
                subs = _progress_subscribers.get(task_id, [])
                if q in subs:
                    subs.remove(q)
                if not subs:
                    _progress_subscribers.pop(task_id, None)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Account Groups API
# ---------------------------------------------------------------------------

@app.get("/api/account-groups")
def list_account_groups():
    """List all account groups with their authorizations."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        groups = conn.execute("SELECT * FROM account_groups ORDER BY sort_order ASC, created DESC").fetchall()
        result = []
        for group in groups:
            auths = conn.execute(
                "SELECT * FROM account_authorizations WHERE group_id = ? ORDER BY sort_order ASC",
                (group["id"],)
            ).fetchall()
            # Check cookie validity for each authorization
            authorizations = []
            for auth in auths:
                cookie_path = Path(auth["cookie_file"])
                quick = _quick_check_cookie(auth["platform"], group["name"]) if cookie_path.exists() else {"valid": False, "reason": "no_file"}
                authorizations.append({
                    "id": auth["id"],
                    "platform": auth["platform"],
                    "cookie_file": auth["cookie_file"],
                    "valid": quick["valid"],
                    "reason": quick.get("reason"),
                })
            result.append({
                "id": group["id"],
                "name": group["name"],
                "created": group["created"],
                "authorizations": authorizations,
            })
    return jsonify({"success": True, "data": result})


# ── Account-group name validation (filesystem-safe) ───────────────────
_FORBIDDEN_NAME_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1F\x7F]')
_NAME_MAX_LEN = 64


def _validate_group_name(raw: object) -> tuple[bool, str]:
    """Validate an account-group name against filesystem-safety rules.

    Returns ``(True, cleaned_name)`` on success or ``(False, error_message)``
    on failure. ``cleaned_name`` has surrounding whitespace stripped.
    """
    if not isinstance(raw, str):
        return False, "分组名不能为空"
    cleaned = raw.strip()
    if not cleaned:
        return False, "分组名不能为空"
    if len(cleaned) > _NAME_MAX_LEN:
        return False, f"分组名长度不能超过 {_NAME_MAX_LEN} 个字符"
    if _FORBIDDEN_NAME_CHARS.search(cleaned):
        return False, "分组名包含不允许的字符（/\\:*?\"<>|）"
    return True, cleaned


@app.post("/api/account-groups")
def create_account_group():
    """Create a new account group."""
    payload = request.get_json(silent=True) or {}
    valid, cleaned_or_msg = _validate_group_name(payload.get("name"))
    if not valid:
        return jsonify({"success": False, "message": cleaned_or_msg}), 400
    name = cleaned_or_msg

    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute(
                "INSERT INTO account_groups (name, created) VALUES (?, ?)",
                (name, datetime.now().isoformat(timespec="seconds"))
            )
            conn.commit()
            group_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "分组名已存在"}), 409

    log(f"[account-groups] created: {name}")
    return jsonify({"success": True, "data": {"id": group_id, "name": name}})


@app.delete("/api/account-groups/<int:group_id>")
def delete_account_group(group_id: int):
    """Delete an account group and its authorizations."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT * FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404
        
        # Delete authorization cookie files
        auths = conn.execute("SELECT * FROM account_authorizations WHERE group_id = ?", (group_id,)).fetchall()
        for auth in auths:
            cookie_path = Path(auth["cookie_file"])
            if cookie_path.exists():
                cookie_path.unlink()
        
        conn.execute("DELETE FROM account_authorizations WHERE group_id = ?", (group_id,))
        conn.execute("DELETE FROM account_groups WHERE id = ?", (group_id,))
        conn.commit()
    
    log(f"[account-groups] deleted: {group['name']}")
    return jsonify({"success": True, "message": f"Group '{group['name']}' deleted"})


@app.post("/api/account-groups/<int:group_id>/rename")
def rename_account_group(group_id: int):
    """Rename an existing account group; cascade-rename cookie files."""
    payload = request.get_json(silent=True) or {}
    valid, cleaned_or_msg = _validate_group_name(payload.get("name"))
    if not valid:
        return jsonify({"success": False, "message": cleaned_or_msg}), 400
    new_name = cleaned_or_msg

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute(
            "SELECT id, name FROM account_groups WHERE id = ?",
            (group_id,),
        ).fetchone()
        if not group:
            return jsonify({"success": False, "message": "分组不存在"}), 404

        old_name = group["name"]
        if old_name == new_name:
            return jsonify({"success": True, "data": {"id": group_id, "name": new_name}})

        auth_rows = conn.execute(
            "SELECT id, platform, cookie_file FROM account_authorizations WHERE group_id = ?",
            (group_id,),
        ).fetchall()

        # Phase 1 — rename cookie files on disk. Roll back on first OSError.
        rename_plan: list[tuple[Path, Path]] = []
        for auth in auth_rows:
            old_path = Path(auth["cookie_file"])
            new_path = COOKIES_DIR / f"{auth['platform']}_{new_name}.json"
            if old_path.exists():
                rename_plan.append((old_path, new_path))

        renamed_so_far: list[tuple[Path, Path]] = []
        for old_path, new_path in rename_plan:
            try:
                os.rename(old_path, new_path)
                renamed_so_far.append((old_path, new_path))
            except OSError as e:
                # Best-effort rollback before bailing.
                for op, np in reversed(renamed_so_far):
                    try:
                        os.rename(np, op)
                    except OSError:
                        pass
                log(f"[account-groups] rename FAIL: {old_path} -> {new_path}: {e}")
                return jsonify({
                    "success": False,
                    "message": f"无法移动 cookie 文件 {old_path.name}，文件可能正在被使用",
                }), 409

        # Phase 2 — update DB. UNIQUE on name races => 409 IntegrityError.
        try:
            conn.execute(
                "UPDATE account_groups SET name = ? WHERE id = ?",
                (new_name, group_id),
            )
            for auth in auth_rows:
                new_path = COOKIES_DIR / f"{auth['platform']}_{new_name}.json"
                conn.execute(
                    "UPDATE account_authorizations SET cookie_file = ? WHERE id = ?",
                    (str(new_path), auth["id"]),
                )
            conn.commit()
        except sqlite3.IntegrityError:
            for op, np in reversed(renamed_so_far):
                try:
                    os.rename(np, op)
                except OSError:
                    pass
            return jsonify({"success": False, "message": "分组名已存在"}), 409

    log(f"[account-groups] renamed: {old_name} -> {new_name} (id={group_id})")
    return jsonify({"success": True, "data": {"id": group_id, "name": new_name}})


@app.post("/api/account-groups/<int:group_id>/authorize")
def authorize_account_group(group_id: int):
    """Add a platform authorization to a group (triggers QR login)."""
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")
    headless = payload.get("headless", True)

    if not platform:
        return jsonify({"success": False, "message": "platform is required"}), 400

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT * FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404
        
        # Check if already authorized
        existing = conn.execute(
            "SELECT * FROM account_authorizations WHERE group_id = ? AND platform = ?",
            (group_id, platform)
        ).fetchone()
        if existing:
            return jsonify({"success": False, "message": f"Platform '{platform}' already authorized"}), 409

    # The cookie file will be named: {platform}_{group_name}.json
    cookie_file = COOKIES_DIR / f"{platform}_{group['name']}.json"
    
    # For QR login platforms, the SSE endpoint handles the login flow.
    # All 7 platforms now support QR-code login via SSE.
    if platform not in _QR_LOGIN_PLATFORMS:
        return jsonify({
            "success": True,
            "data": {
                "group_name": group["name"],
                "platform": platform,
                "cookie_file": str(cookie_file),
            }
        })

    return jsonify({
        "success": True,
        "data": {
            "group_name": group["name"],
            "platform": platform,
            "cookie_file": str(cookie_file),
        }
    })


@app.post("/api/account-groups/<int:group_id>/confirm-authorize")
def confirm_authorize_account_group(group_id: int):
    """Confirm and save platform authorization after QR login."""
    import time
    
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")

    if not platform:
        return jsonify({"success": False, "message": "platform is required"}), 400

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT * FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404

    cookie_file = COOKIES_DIR / f"{platform}_{group['name']}.json"
    
    # Wait for cookie file to be written (with retry)
    for attempt in range(10):
        if cookie_file.exists():
            # Check if file is valid
            quick = _quick_check_cookie(platform, group["name"])
            if quick["valid"]:
                break
        time.sleep(0.5)
    else:
        return jsonify({"success": False, "message": "Cookie file not found or invalid after login"}), 400

    # Save authorization to database
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute(
                "INSERT INTO account_authorizations (group_id, platform, cookie_file, created) VALUES (?, ?, ?, ?)",
                (group_id, platform, str(cookie_file), datetime.now().isoformat(timespec="seconds"))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Update existing authorization
            conn.execute(
                "UPDATE account_authorizations SET cookie_file = ?, created = ? WHERE group_id = ? AND platform = ?",
                (str(cookie_file), datetime.now().isoformat(timespec="seconds"), group_id, platform)
            )
            conn.commit()

    log(f"[account-groups] authorized: {group['name']} -> {platform}")
    return jsonify({"success": True, "message": f"Platform '{platform}' authorized for group '{group['name']}'"})


@app.delete("/api/account-groups/<int:group_id>/authorize/<platform>")
def remove_authorization(group_id: int, platform: str):
    """Remove a platform authorization from a group."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT * FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404
        
        auth = conn.execute(
            "SELECT * FROM account_authorizations WHERE group_id = ? AND platform = ?",
            (group_id, platform)
        ).fetchone()
        if not auth:
            return jsonify({"success": False, "message": "Authorization not found"}), 404
        
        # Delete cookie file
        cookie_path = Path(auth["cookie_file"])
        if cookie_path.exists():
            cookie_path.unlink()
        
        conn.execute("DELETE FROM account_authorizations WHERE id = ?", (auth["id"],))
        conn.commit()

    log(f"[account-groups] removed authorization: {group['name']} -> {platform}")
    return jsonify({"success": True, "message": f"Platform '{platform}' authorization removed"})


@app.post("/api/account-groups/reorder")
def reorder_account_groups():
    """Reorder account groups by updating their sort_order."""
    payload = request.get_json(silent=True) or {}
    group_ids = payload.get("group_ids", [])
    if not group_ids:
        return jsonify({"success": False, "message": "group_ids is required"}), 400

    with sqlite3.connect(DB_PATH) as conn:
        for idx, group_id in enumerate(group_ids):
            conn.execute(
                "UPDATE account_groups SET sort_order = ? WHERE id = ?",
                (idx, group_id)
            )
        conn.commit()

    log(f"[account-groups] reordered: {len(group_ids)} groups")
    return jsonify({"success": True, "message": "Groups reordered successfully"})


@app.post("/api/account-groups/<int:group_id>/reorder-authorizations")
def reorder_authorizations(group_id: int):
    """Reorder authorizations within a group by updating their sort_order."""
    payload = request.get_json(silent=True) or {}
    auth_ids = payload.get("auth_ids", [])
    if not auth_ids:
        return jsonify({"success": False, "message": "auth_ids is required"}), 400

    with sqlite3.connect(DB_PATH) as conn:
        for idx, auth_id in enumerate(auth_ids):
            conn.execute(
                "UPDATE account_authorizations SET sort_order = ? WHERE id = ? AND group_id = ?",
                (idx, auth_id, group_id)
            )
        conn.commit()

    log(f"[account-groups] reordered authorizations: group {group_id}, {len(auth_ids)} items")
    return jsonify({"success": True, "message": "Authorizations reordered successfully"})


@app.post("/api/upload/video")
def upload_video():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        platform = data.get("platform")
        account = data.get("account")
        title = data.get("title")
        desc = data.get("desc", "")
        tags = data.get("tags", "")
        schedule = data.get("schedule")
        product_link = data.get("product_link", "")
        product_title = data.get("product_title", "")
        tid = data.get("tid")
        headless = data.get("headless")
        short_title = data.get("short_title", "")
        category = data.get("category", "")
        is_draft = data.get("is_draft", "")
        debug = data.get("debug", "")
        file_data = data.get("file_data")
        thumbnail = data.get("thumbnail")
        thumbnail_landscape = data.get("thumbnail_landscape")
        thumbnail_portrait = data.get("thumbnail_portrait")
    else:
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
        debug = request.form.get("debug", "")
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
    # bilibili upload-video uses biliup CLI (not a browser), so --headless is not accepted
    if hflag and platform != "bilibili":
        argv.append("--headless" if hflag == "true" else "--headed")
    # Always pass --desc for platforms that support it (bilibili requires it)
    if platform in DESC_PLATFORMS:
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

    # schedule is omitted from argv — _schedule_task() handles delay, uploader uses immediate mode
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
    if debug in ("true", "1"):
        argv.append("--debug")

    task_id = _new_task_id("upload-video")
    if schedule:
        normalised = _normalise_schedule(schedule)
        parsed = datetime.strptime(normalised, '%Y-%m-%d %H:%M')  # type: ignore[arg-type]
        _db_insert_task(
            task_id=task_id,
            status="scheduled",
            platform=platform,
            action="upload-video",
            account=account,
            created=datetime.now().isoformat(timespec="seconds"),
            argv=argv,
        )
        _schedule_task(task_id, argv, parsed)
    else:
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
        debug = payload.get("debug", "")
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
        debug = request.form.get("debug", "")

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
    if debug in ("true", "1"):
        argv.append("--debug")
    # 仅视频号（tencent）的图文可保存为草稿——CLI 现在提供 --draft。
    # 该字段从 JSON 或 form 中的 "is_draft" 读取，其他平台忽略。
    if platform == "tencent":
        data_input = request.get_json(silent=True) if request.is_json else None
        is_draft_raw = (
            data_input.get("is_draft", "") if isinstance(data_input, dict) else request.form.get("is_draft", "")
        )
        if str(is_draft_raw).lower() in ("true", "1", "yes", "on"):
            argv.append("--draft")
    task_id = _new_task_id("upload-note")
    if schedule:
        normalised = _normalise_schedule(schedule)
        parsed = datetime.strptime(normalised, '%Y-%m-%d %H:%M')  # type: ignore[arg-type]
        _db_insert_task(
            task_id=task_id,
            status="scheduled",
            platform=platform,
            action="upload-note",
            account=account,
            created=datetime.now().isoformat(timespec="seconds"),
            argv=argv,
        )
        _schedule_task(task_id, argv, parsed)
    else:
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
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", 0, type=int)
    rows = _db_get_all_tasks(limit=limit, offset=offset)
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

    with _timer_lock:
        timer = _scheduled_timers.pop(task_id, None)
    if timer:
        timer.cancel()

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
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", 0, type=int)
    return jsonify({
        "success": True,
        "data": _db_get_logs(after, task_id, limit=limit, offset=offset),
    })


@app.get("/api/error-events")
def get_error_events_route():
    """Structured failure log. Filters: ``after`` / ``platform`` / ``account`` / ``action`` / ``exc_type``."""
    platform = request.args.get("platform")
    account = request.args.get("account")
    action = request.args.get("action")
    exc_type = request.args.get("exc_type")
    after = request.args.get("after")
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", 0, type=int)
    return jsonify({
        "success": True,
        "data": _db_get_error_events(
            after=after, platform=platform, account=account,
            action=action, exc_type=exc_type, limit=limit, offset=offset,
        ),
    })


# ── AI Content Generation Endpoints ──────────────────────────────────────────

def _ai_queue_worker():
    """Background worker that processes AI generation requests from the queue.

    Uses key rotation: on a 429 rate-limit, marks the current key and retries
    with the next available key in the pool (up to pool-size attempts).
    """
    while True:
        item = _ai_request_queue.get()
        if item is None:
            break
        result_event, payload, result_holder = item
        with _ai_request_semaphore:
            try:
                images = payload.get("images", [])
                prompt = payload.get("prompt", "")
                system_prompt = payload.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

                if images:
                    user_content = _build_media_content(images, prompt)
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ]
                else:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ]

                # Key rotation: try up to pool-size keys
                all_keys = _get_all_keys_cached()
                max_attempts = max(len(all_keys), 1)
                current_key = _get_next_key()
                result_holder["success"] = False
                result_holder["message"] = "All API keys exhausted"

                for _ in range(max_attempts):
                    if not current_key:
                        break
                    try:
                        resp = http_requests.post(
                            f"{OPENROUTE_BASE_URL}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {current_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": payload.get("model", "google/gemma-4-26b-a4b-it:free"),
                                "messages": messages,
                                "max_tokens": 2000,
                                "temperature": 0.7,
                            },
                            timeout=(10, 120),  # connect=10s, read=120s
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                            result_holder["success"] = True
                            result_holder["data"] = {"content": content.strip()}
                            break
                        elif resp.status_code == 429:
                            _mark_rate_limited(current_key)
                            current_key = _get_next_key()
                            continue
                        else:
                            result_holder["message"] = resp.json().get("error", {}).get("message", f"API error: {resp.status_code}")
                            break
                    except (json.JSONDecodeError, ValueError):
                        result_holder["message"] = "Failed to parse API response"
                        break
            except (http_requests.RequestException, OSError, TimeoutError, json.JSONDecodeError, ValueError, KeyError) as e:
                result_holder["success"] = False
                result_holder["message"] = type(e).__name__
            finally:
                result_event.set()
                _ai_request_queue.task_done()


def _ensure_ai_worker():
    """Start the queue worker thread if not already running."""
    global _ai_queue_worker_started
    with _ai_queue_lock:
        if not _ai_queue_worker_started:
            t = threading.Thread(target=_ai_queue_worker, daemon=True, name="ai-queue-worker")
            t.start()
            _ai_queue_worker_started = True


@app.post("/api/ai/generate")
def ai_generate():
    _ensure_ai_worker()
    if not _has_any_api_key():
        return jsonify({"success": False, "message": "AI service not configured. Please set your OpenRouter API key in the AI sidebar settings."})

    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    model = data.get("model", "google/gemma-4-26b-a4b-it:free")
    system_prompt = data.get("system_prompt", "")
    platform = data.get("platform", "")
    images = data.get("images", [])

    if not prompt and not images:
        return jsonify({"success": False, "message": "Prompt or image is required."})

    if not system_prompt:
        system_prompt = PLATFORM_PROMPTS.get(platform, DEFAULT_SYSTEM_PROMPT)

    result_holder: dict = {}
    result_event = threading.Event()
    _ai_request_queue.put((result_event, {
        "prompt": prompt,
        "model": model,
        "system_prompt": system_prompt,
        "images": images,
    }, result_holder))

    queue_size = _ai_request_queue.qsize()
    if queue_size > 1:
        log(f"[AI] Request queued (position: {queue_size})")

    result_event.wait(timeout=120)

    if not result_event.is_set():
        return jsonify({"success": False, "message": "Request timed out."})

    # Retry with next key if rate-limited
    retries = 0
    max_retries = max(len(_get_all_keys_cached()), 1)
    while (not result_holder.get("success") and
           "429" in result_holder.get("message", "") and
           retries < max_retries):
        result_holder.clear()
        result_event = threading.Event()
        _ai_request_queue.put((result_event, {
            "prompt": prompt,
            "model": model,
            "system_prompt": system_prompt,
            "images": images,
        }, result_holder))
        result_event.wait(timeout=120)
        retries += 1

    return jsonify(result_holder)


@app.get("/api/ai/models")
def ai_models():
    try:
        resp = http_requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            all_models = resp.json().get("data", [])
            free_models = []
            for m in all_models:
                if ":free" not in m["id"]:
                    continue
                arch = m.get("architecture", {})
                modality = arch.get("modality", "text->text")
                input_mods = arch.get("input_modalities", ["text"])
                output_mods = arch.get("output_modalities", ["text"])
                tags = []
                if "text" in input_mods:
                    tags.append("text")
                if "image" in input_mods:
                    tags.append("image")
                if "video" in input_mods:
                    tags.append("video")
                if "audio" in input_mods:
                    tags.append("audio")
                if "file" in input_mods:
                    tags.append("file")
                free_models.append({
                    "id": m["id"],
                    "name": m.get("name", m["id"]).replace(" (free)", "").replace(":free", ""),
                    "context_length": m.get("context_length", 0),
                    "modality": modality,
                    "input_modalities": input_mods,
                    "output_modalities": output_mods,
                    "tags": tags,
                })
            free_models.sort(key=lambda x: x.get("context_length", 0), reverse=True)
            if free_models:
                return jsonify({"success": True, "data": free_models, "source": "live"})
    except (http_requests.RequestException, OSError, TimeoutError, json.JSONDecodeError, ValueError):
        pass
    models = [{"id": k, "name": v, "tags": ["text"]} for k, v in AI_MODELS.items()]
    return jsonify({"success": True, "data": models, "source": "fallback"})


@app.get("/api/ai/config")
def ai_config_get():
    keys = _get_all_keys()
    configured = bool(keys) or bool(_get_openroute_key())
    return jsonify({"success": True, "data": {"configured": configured, "key_count": len(keys)}})


@app.get("/api/ai/keys")
def ai_keys_list():
    """List all API keys in the pool."""
    keys = _get_all_keys()
    return jsonify({"success": True, "data": [{
        "id": k["id"],
        "masked": k["masked"],
        "created": k["created"],
        "rate_limited": bool(k["rate_limited_at"]),
    } for k in keys]})


@app.post("/api/ai/config")
def ai_config_set():
    """Add one or more API keys to the rotation pool."""
    data = request.get_json(silent=True) or {}
    key = data.get("api_key", "").strip()
    if not key:
        return jsonify({"success": False, "message": "API key is required."})
    try:
        info = _add_api_key(key)
    except (sqlite3.IntegrityError,) as _:
        return jsonify({"success": False, "message": "该 Key 已经添加过了。"}), 409
    masked = key[:8] + "****" + key[-4:] if len(key) > 12 else "****"
    return jsonify({"success": True, "data": {"configured": True, "key_masked": masked, "key_id": info["id"]}})


@app.delete("/api/ai/config")
def ai_config_delete():
    """Delete a specific API key by id, or all keys if no id provided."""
    data = request.get_json(silent=True) or {}
    key_id = data.get("key_id")
    if key_id is not None:
        ok = _delete_api_key(int(key_id))
        if not ok:
            return jsonify({"success": False, "message": "Key not found."}), 404
        remaining = _get_all_keys()
        return jsonify({"success": True, "message": "Key removed.", "data": {"remaining": len(remaining)}})
    # No key_id — delete all from pool + legacy
    for k in _get_all_keys():
        _delete_api_key(k["id"])
    _delete_openroute_key()
    return jsonify({"success": True, "message": "All API keys removed."})



def _stream_openrouter(
    model: str,
    messages: list[dict],
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> Generator[str, None, None]:
    """Shared SSE streaming generator with key rotation and 429 retry logic."""
    all_keys = _get_all_keys()
    max_attempts = max(len(all_keys), 1)
    current_key = _get_next_key()

    for _ in range(max_attempts):
        if not current_key:
            yield f"event: error\ndata: {json.dumps({'message': 'No API keys available.'})}\n\n"
            return

        key_info = None
        for k in _get_all_keys():
            if k["api_key"] == current_key:
                key_info = {"id": k["id"], "masked": k["masked"]}
                break
        if key_info:
            yield f"event: key_info\ndata: {json.dumps(key_info)}\n\n"

        try:
            resp = http_requests.post(
                f"{OPENROUTE_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {current_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True,
                },
                timeout=(10, 120),  # connect=10s, read=120s
                stream=True,
            )

            if resp.status_code == 429:
                _mark_rate_limited(current_key)
                current_key = _get_next_key()
                continue

            if resp.status_code != 200:
                error_msg = resp.json().get("error", {}).get("message", f"API error: {resp.status_code}")
                yield f"event: error\ndata: {json.dumps({'message': error_msg})}\n\n"
                return

            full_content = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8", errors="replace")
                if not line_str.startswith("data: "):
                    continue
                chunk_str = line_str[6:]
                if chunk_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(chunk_str)
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        full_content += content
                        yield f"event: data\ndata: {json.dumps({'content': content})}\n\n"
                except json.JSONDecodeError:
                    continue

            yield f"event: done\ndata: {json.dumps({'content': full_content.strip()})}\n\n"
            return

        except (http_requests.RequestException, OSError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError) as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e) or type(e).__name__})}\n\n"
            return

    yield f"event: error\ndata: {json.dumps({'message': 'All API keys rate-limited. Please wait a few minutes and try again.'})}\n\n"


ENHANCE_PROMPT_SYSTEM = """You are a world-class prompt engineer and social media content strategist. Your job is to transform a user's rough, simple idea into a highly detailed, vivid, and creative content brief that will produce exceptional social media posts.

## Your Enhancement Process

1. **Understand the core intent** — What is the user really trying to communicate?
2. **Enrich with sensory details** — Add visual, emotional, and contextual specifics
3. **Add creative direction** — Suggest tone, style, hooks, and narrative structure
4. **Optimize for engagement** — Include elements that drive shares, saves, and comments
5. **Platform awareness** — Tailor language and format for the target platform

## Rules
- Output the enhanced prompt in the SAME language as the input (Chinese in → Chinese out)
- Be specific and actionable, not vague
- Include concrete examples of what the content should cover
- Suggest a content angle or hook
- Keep it focused — enhance, don't hallucinate a completely different topic
- Output ONLY the enhanced prompt text, no meta-commentary

## Enhancement Template
When enhancing, naturally incorporate these dimensions:
- 🎯 Core message / value proposition
- 🎨 Visual style and mood (if applicable)
- 📖 Narrative structure (hook → body → CTA)
- 💡 Unique angle or fresh perspective
- 🔥 Emotional triggers and engagement hooks
- #️⃣ Hashtag and keyword suggestions (woven in naturally)

## Example
Input: "美食探店"
Enhanced: "这是一期城市隐藏美食探店内容。请以'本地人都不一定知道的宝藏小店'为切入角度，营造发现感和稀缺感。描述食物时注重色香味的细节刻画——酱汁的光泽、食材的层次、入口的口感变化。融入店主故事或店铺历史增加温度。结尾设置互动钩子：'你们还想看哪个区的宝藏店？评论区告诉我'。整体风格：真实不做作，像在跟朋友安利。适合小红书/抖音种草向内容。"""

ENHANCE_PROMPT_VISION = """You are a world-class visual content analyst and prompt engineer. You will receive an image or video frame. Your job is to:

1. **Analyze the visual content in detail** — subjects, setting, colors, mood, actions, composition
2. **Infer the story/context** — What's happening? What's the feeling? What would resonate?
3. **Generate a detailed content creation brief** based on what you see

## Output Format
Output a detailed Chinese prompt that describes:
- 📸 画面描述：详细描述图片/视频中的主要内容（人物、场景、物品、动作、色彩、氛围）
- 🎯 内容角度：基于画面内容，建议一个有吸引力的发布角度
- 📝 文案方向：基于画面信息，给出标题、描述、标签的创作方向
- 💡 创意建议：可以加入什么元素让内容更有吸引力（故事、情感、互动点）

## Rules
- Output in Chinese
- Be highly specific to what you actually see in the image/video
- Focus on details that would make great social media content
- Suggest hooks and angles based on the visual content
- Output ONLY the analysis and prompt, no meta-commentary"""


@app.post("/api/ai/enhance-prompt")
def ai_enhance_prompt():
    if not _has_any_api_key():
        return jsonify({"success": False, "message": "AI service not configured."})

    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    images = data.get("images", [])
    model = data.get("model", "google/gemma-4-26b-a4b-it:free")
    platform = data.get("platform", "")

    if not text and not images:
        return jsonify({"success": False, "message": "请输入文字或上传图片。"})

    has_media = len(images) > 0
    system_prompt = ENHANCE_PROMPT_VISION if has_media else ENHANCE_PROMPT_SYSTEM
    if platform:
        system_prompt += f"\n\n目标平台：{platform}"

    if has_media:
        user_content = _build_media_content(images)
        if text:
            user_content.append({"type": "text", "text": f"用户的补充说明：{text}"})
        else:
            user_content.append({"type": "text", "text": "请根据这些图片/视频生成社交媒体内容的详细提示词。"})
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    else:
        enhance_text = f"请增强以下内容描述，将其转化为详细、生动、有创意的社交媒体内容创作提示词：\n\n{text}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": enhance_text},
        ]

    all_keys = _get_all_keys()
    max_attempts = max(len(all_keys), 1)

    def generate():
        current_key = _get_next_key()
        for _attempt in range(max_attempts):
            if not current_key:
                yield f"event: error\ndata: {json.dumps({'message': 'No API keys available.'})}\n\n"
                return
            key_info = None
            for k in _get_all_keys():
                if k["api_key"] == current_key:
                    key_info = {"id": k["id"], "masked": k["masked"]}
                    break
            if key_info:
                yield f"event: key_info\ndata: {json.dumps(key_info)}\n\n"
            try:
                resp = http_requests.post(
                    f"{OPENROUTE_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {current_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": 1500,
                        "temperature": 0.8,
                        "stream": True,
                    },
                    timeout=120,
                    stream=True,
                )

                if resp.status_code == 429:
                    _mark_rate_limited(current_key)
                    current_key = _get_next_key()
                    continue

                if resp.status_code != 200:
                    error_msg = resp.json().get("error", {}).get("message", f"API error: {resp.status_code}")
                    yield f"event: error\ndata: {json.dumps({'message': error_msg})}\n\n"
                    return

                full_content = ""
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8", errors="replace")
                    if not line_str.startswith("data: "):
                        continue
                    chunk_str = line_str[6:]
                    if chunk_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(chunk_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_content += content
                            yield f"event: data\ndata: {json.dumps({'content': content})}\n\n"
                    except json.JSONDecodeError:
                        continue

                yield f"event: done\ndata: {json.dumps({'content': full_content.strip()})}\n\n"
                return

            except (http_requests.RequestException, OSError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError) as e:
                yield f"event: error\ndata: {json.dumps({'message': str(e) or type(e).__name__})}\n\n"
                return

        yield f"event: error\ndata: {json.dumps({'message': 'All API keys rate-limited. Please wait a few minutes.'})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/ai/generate/stream")
def ai_generate_stream():
    if not _has_any_api_key():
        def err_no_key():
            yield f"event: error\ndata: {json.dumps({'message': 'AI service not configured. Please set your OpenRouter API key in the AI sidebar settings.'})}\n\n"
        return Response(err_no_key(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    model = data.get("model", "google/gemma-4-26b-a4b-it:free")
    system_prompt = data.get("system_prompt", "")
    platform = data.get("platform", "")
    images = data.get("images", [])

    if not prompt and not images:
        def err_no_prompt():
            yield f"event: error\ndata: {json.dumps({'message': 'Prompt or image is required.'})}\n\n"
        return Response(err_no_prompt(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    if not system_prompt:
        system_prompt = PLATFORM_PROMPTS.get(platform, DEFAULT_SYSTEM_PROMPT)

    if images:
        user_content = _build_media_content(images, prompt)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

    return Response(
        _stream_openrouter(model, messages, max_tokens=2000, temperature=0.7),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
    app.run(host="0.0.0.0", port=6001, debug=True)
