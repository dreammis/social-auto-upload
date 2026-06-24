"""AI content generation Blueprint for OpenRouter integration."""

import json
import queue as _queue
import sqlite3
import threading
import time
from datetime import datetime
from typing import Generator

from flask import Blueprint, jsonify, request, Response
import requests as http_requests

from web_runner import (
    DB_PATH,
    db_lock,
    log,
    _get_all_keys,
    _get_all_keys_cached,
    _get_next_key,
    _get_openroute_key,
    _delete_openroute_key,
    _add_api_key,
    _delete_api_key,
    _mark_rate_limited,
    _bust_key_cache,
)

ai_bp = Blueprint('ai', __name__)

OPENROUTE_BASE_URL = "https://openrouter.ai/api/v1"


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


@ai_bp.post("/api/ai/generate")
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


@ai_bp.get("/api/ai/models")
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


@ai_bp.get("/api/ai/config")
def ai_config_get():
    keys = _get_all_keys()
    configured = bool(keys) or bool(_get_openroute_key())
    return jsonify({"success": True, "data": {"configured": configured, "key_count": len(keys)}})


@ai_bp.get("/api/ai/keys")
def ai_keys_list():
    """List all API keys in the pool."""
    keys = _get_all_keys()
    return jsonify({"success": True, "data": [{
        "id": k["id"],
        "masked": k["masked"],
        "created": k["created"],
        "rate_limited": bool(k["rate_limited_at"]),
    } for k in keys]})


@ai_bp.post("/api/ai/config")
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


@ai_bp.delete("/api/ai/config")
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


@ai_bp.post("/api/ai/enhance-prompt")
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


@ai_bp.post("/api/ai/generate/stream")
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
