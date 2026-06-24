"""AI content generation routes."""
from __future__ import annotations

import json
import os
import queue as _queue
import threading
from typing import Generator

from flask import Blueprint, Response, jsonify, request
import requests as http_requests

from web_runner.db import DB_PATH, db_lock, get_connection
from web_runner.utils import log

bp = Blueprint("ai", __name__)

OPENROUTE_BASE_URL = "https://openrouter.ai/api/v1"

_ai_request_queue: _queue.Queue = _queue.Queue()
_ai_request_semaphore = threading.Semaphore(2)
_ai_queue_lock = threading.Lock()
_ai_queue_worker_started = False

# Hard cap on multi-turn messages array length — bounds LLM cost and
# context-window abuse. See specs/ai-stream-multimessage.
MAX_MESSAGES_PER_REQUEST = 30

AI_MODELS = {
    "google/gemma-4-26b-a4b-it:free": "Gemma 4 26B",
    "deepseek/deepseek-chat-v3-0324:free": "DeepSeek V3",
    "qwen/qwen3-235b-a22b:free": "Qwen3 235B",
}

DEFAULT_SYSTEM_PROMPT = """你是一个专业的社交媒体内容创作者。请根据用户的要求生成高质量的社交媒体内容。
要求：
- 内容要有吸引力和互动性
- 适合中国社交媒体平台
- 语言自然、亲切
- 包含适当的emoji"""

PLATFORM_PROMPTS = {
    "douyin": "你是抖音内容创作专家。生成适合短视频平台的吸引人文案，要简洁有力，有hook。",
    "xiaohongshu": "你是小红书内容创作专家。生成种草风格的笔记内容，要有真实感和分享感。",
    "kuaishou": "你是快手内容创作专家。生成接地气、有温度的内容。",
    "bilibili": "你是B站内容创作专家。生成适合年轻用户群体的创意内容。",
}


def _get_all_keys_cached() -> list[dict]:
    with db_lock:
        with get_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            rows = conn.execute("SELECT * FROM ai_api_keys ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]


def _get_next_key() -> str:
    keys = _get_all_keys_cached()
    if not keys:
        return os.environ.get("OPENROUTE_API_KEY", "")
    for k in keys:
        if not k.get("rate_limited_at"):
            return k["api_key"]
    return keys[0]["api_key"] if keys else ""


def _mark_rate_limited(key: str) -> None:
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    with db_lock:
        with get_connection() as conn:
            conn.execute("UPDATE ai_api_keys SET rate_limited_at = ? WHERE api_key = ?", (now, key))
            conn.commit()


def _has_any_api_key() -> bool:
    keys = _get_all_keys_cached()
    if keys:
        return True
    return bool(os.environ.get("OPENROUTE_API_KEY", ""))


def _build_media_content(images: list, prompt: str = "") -> list:
    content = []
    for img in images:
        if img.startswith("data:image"):
            content.append({"type": "image_url", "image_url": {"url": img}})
        elif img.startswith("http"):
            content.append({"type": "image_url", "image_url": {"url": img}})
    if prompt:
        content.append({"type": "text", "text": prompt})
    return content


def _ai_queue_worker():
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
                    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
                else:
                    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
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
                            headers={"Authorization": f"Bearer {current_key}", "Content-Type": "application/json"},
                            json={"model": payload.get("model", "google/gemma-4-26b-a4b-it:free"), "messages": messages, "max_tokens": 2000, "temperature": 0.7},
                            timeout=(10, 120),
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
    global _ai_queue_worker_started
    with _ai_queue_lock:
        if not _ai_queue_worker_started:
            t = threading.Thread(target=_ai_queue_worker, daemon=True, name="ai-queue-worker")
            t.start()
            _ai_queue_worker_started = True


def _stream_openrouter(model: str, messages: list[dict], max_tokens: int = 2000, temperature: float = 0.7) -> Generator[str, None, None]:
    all_keys = _get_all_keys_cached()
    max_attempts = max(len(all_keys), 1)
    current_key = _get_next_key()
    for _ in range(max_attempts):
        if not current_key:
            yield f"event: error\ndata: {json.dumps({'message': 'No API keys available.'})}\n\n"
            return
        try:
            resp = http_requests.post(
                f"{OPENROUTE_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {current_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature, "stream": True},
                timeout=(10, 120), stream=True,
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


@bp.post("/api/ai/generate")
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
    _ai_request_queue.put((result_event, {"prompt": prompt, "model": model, "system_prompt": system_prompt, "images": images}, result_holder))
    result_event.wait(timeout=120)
    if not result_event.is_set():
        return jsonify({"success": False, "message": "Request timed out."})
    return jsonify(result_holder)


@bp.get("/api/ai/models")
def ai_models():
    try:
        resp = http_requests.get("https://openrouter.ai/api/v1/models", headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code == 200:
            all_models = resp.json().get("data", [])
            free_models = []
            for m in all_models:
                if ":free" not in m["id"]:
                    continue
                arch = m.get("architecture", {})
                input_mods = arch.get("input_modalities", ["text"])
                tags = []
                if "text" in input_mods:
                    tags.append("text")
                if "image" in input_mods:
                    tags.append("image")
                free_models.append({"id": m["id"], "name": m.get("name", m["id"]).replace(" (free)", "").replace(":free", ""), "context_length": m.get("context_length", 0), "tags": tags})
            free_models.sort(key=lambda x: x.get("context_length", 0), reverse=True)
            if free_models:
                return jsonify({"success": True, "data": free_models, "source": "live"})
    except (http_requests.RequestException, OSError, TimeoutError, json.JSONDecodeError, ValueError):
        pass
    models = [{"id": k, "name": v, "tags": ["text"]} for k, v in AI_MODELS.items()]
    return jsonify({"success": True, "data": models, "source": "fallback"})


@bp.get("/api/ai/config")
def ai_config_get():
    with db_lock:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM ai_api_keys").fetchall()
    configured = bool(rows) or bool(os.environ.get("OPENROUTE_API_KEY", ""))
    return jsonify({"success": True, "data": {"configured": configured, "key_count": len(rows)}})


@bp.get("/api/ai/keys")
def ai_keys_list():
    keys = _get_all_keys_cached()
    return jsonify({"success": True, "data": [{"id": k["id"], "masked": k["masked"], "created": k["created"], "rate_limited": bool(k.get("rate_limited_at"))} for k in keys]})


@bp.post("/api/ai/config")
def ai_config_set():
    from datetime import datetime
    data = request.get_json(silent=True) or {}
    key = data.get("api_key", "").strip()
    if not key:
        return jsonify({"success": False, "message": "API key is required."})
    masked = key[:8] + "****" + key[-4:] if len(key) > 12 else "****"
    now = datetime.now().isoformat(timespec="seconds")
    try:
        with db_lock:
            with get_connection() as conn:
                conn.execute("INSERT INTO ai_api_keys (api_key, masked, created) VALUES (?, ?, ?)", (key, masked, now))
                conn.commit()
                row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return jsonify({"success": True, "data": {"configured": True, "key_masked": masked, "key_id": row_id}})
    except __import__("sqlite3").IntegrityError:
        return jsonify({"success": False, "message": "该 Key 已经添加过了。"}), 409


@bp.delete("/api/ai/config")
def ai_config_delete():
    data = request.get_json(silent=True) or {}
    key_id = data.get("key_id")
    if key_id is not None:
        with db_lock:
            with get_connection() as conn:
                cur = conn.execute("DELETE FROM ai_api_keys WHERE id = ?", (int(key_id),))
                conn.commit()
                if cur.rowcount == 0:
                    return jsonify({"success": False, "message": "Key not found."}), 404
        return jsonify({"success": True, "message": "Key removed."})
    with db_lock:
        with get_connection() as conn:
            conn.execute("DELETE FROM ai_api_keys")
            conn.commit()
    return jsonify({"success": True, "message": "All API keys removed."})


@bp.post("/api/ai/keys/batch")
def ai_keys_batch():
    from datetime import datetime
    data = request.get_json(silent=True) or {}
    raw = data.get("keys", [])
    if not isinstance(raw, list):
        return jsonify({"success": False, "message": "keys must be an array."}), 400

    now = datetime.now().isoformat(timespec="seconds")
    added = 0
    skipped = 0
    errors: list[str] = []
    with db_lock:
        with get_connection() as conn:
            for entry in raw:
                key = (entry if isinstance(entry, str) else str(entry)).strip()
                if not key or not key.startswith("sk-"):
                    skipped += 1
                    continue
                masked = key[:8] + "****" + key[-4:] if len(key) > 12 else "****"
                try:
                    conn.execute(
                        "INSERT INTO ai_api_keys (api_key, masked, created) VALUES (?, ?, ?)",
                        (key, masked, now),
                    )
                    added += 1
                except __import__("sqlite3").IntegrityError:
                    skipped += 1
            conn.commit()
    return jsonify({"success": True, "data": {"added": added, "skipped": skipped}})


@bp.post("/api/ai/enhance-prompt")
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

    ENHANCE_SYSTEM = "You are a world-class prompt engineer. Transform the user's rough idea into a detailed, vivid content brief. Output in the SAME language as the input. Output ONLY the enhanced prompt."
    if platform:
        ENHANCE_SYSTEM += f"\n\n目标平台：{platform}"

    if images:
        user_content = _build_media_content(images)
        user_content.append({"type": "text", "text": f"用户的补充说明：{text}" if text else "请根据这些图片生成社交媒体内容的详细提示词。"})
        messages = [{"role": "system", "content": ENHANCE_SYSTEM}, {"role": "user", "content": user_content}]
    else:
        messages = [{"role": "system", "content": ENHANCE_SYSTEM}, {"role": "user", "content": f"请增强以下内容描述：\n\n{text}"}]

    return Response(
        _stream_openrouter(model, messages, max_tokens=1500, temperature=0.8),
        mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.post("/api/ai/generate/stream")
def ai_generate_stream():
    if not _has_any_api_key():
        def err():
            yield f"event: error\ndata: {json.dumps({'message': 'AI service not configured.'})}\n\n"
        return Response(err(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    data = request.get_json(silent=True) or {}
    model = data.get("model", "google/gemma-4-26b-a4b-it:free")

    # Multi-turn entry-point: when the client supplies a non-empty
    # `messages` array, forward it verbatim to OpenRouter. The legacy
    # single-turn `prompt` / `system_prompt` / `images` path is the
    # fallback for clients that haven't been upgraded yet.
    raw_messages = data.get("messages")
    if isinstance(raw_messages, list) and len(raw_messages) > 0:
        if len(raw_messages) > MAX_MESSAGES_PER_REQUEST:
            def cap_err():
                yield f"event: error\ndata: {json.dumps({'message': f'Too many messages in conversation (max {MAX_MESSAGES_PER_REQUEST}).'})}\n\n"
            return Response(cap_err(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
        return Response(
            _stream_openrouter(model, raw_messages),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Legacy single-turn fallback.
    prompt = data.get("prompt", "").strip()
    system_prompt = data.get("system_prompt", "")
    platform = data.get("platform", "")
    images = data.get("images", [])
    if not prompt and not images:
        def err():
            yield f"event: error\ndata: {json.dumps({'message': 'Prompt or image is required.'})}\n\n"
        return Response(err(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    if not system_prompt:
        system_prompt = PLATFORM_PROMPTS.get(platform, DEFAULT_SYSTEM_PROMPT)
    if images:
        user_content = _build_media_content(images, prompt)
        fallback_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
    else:
        fallback_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    return Response(
        _stream_openrouter(model, fallback_messages),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
