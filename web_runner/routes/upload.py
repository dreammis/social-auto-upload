"""Upload routes."""
from __future__ import annotations

import json
import queue as _queue
import uuid
from datetime import datetime
from pathlib import Path
from typing import Generator

from flask import Blueprint, Response, jsonify, request

from web_runner.utils import (
    DESC_PLATFORMS,
    MIN_UPLOAD_BYTES,
    NOTE_PLATFORMS,
    PLATFORM_CONFIG,
    THUMBNAIL_DUAL_PLATFORMS,
    THUMBNAIL_PLATFORMS,
    UPLOADS_DIR,
    _db_get_task,
    _db_insert_task,
    _db_update_task,
    _headless_flag,
    _new_task_id,
    _normalise_schedule,
    _progress_sub_lock,
    _progress_subscribers,
    _run_sau,
    _save_data_uri,
    _schedule_task,
    _store_result,
    _SSE_TIMEOUT_SECONDS,
    log,
    task_executor,
)

bp = Blueprint("upload", __name__)


@bp.post("/api/upload/video")
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

    argv = [platform, "upload-video", "--account", account, "--title", title, "--tags", tags]
    hflag = _headless_flag(headless)
    if hflag and platform != "bilibili":
        argv.append("--headless" if hflag == "true" else "--headed")
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
        parsed = datetime.strptime(normalised, '%Y-%m-%d %H:%M')
        _db_insert_task(task_id=task_id, status="scheduled", platform=platform, action="upload-video", account=account, created=datetime.now().isoformat(timespec="seconds"), argv=argv)
        _schedule_task(task_id, argv, parsed)
    else:
        _db_insert_task(task_id=task_id, status="pending", platform=platform, action="upload-video", account=account, created=datetime.now().isoformat(timespec="seconds"), argv=argv)
        task_executor.submit(_run_sau, task_id, argv)
    return jsonify({"success": True, "data": {"task_id": task_id}})


@bp.post("/api/upload/note")
def upload_note():
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

    argv = [platform, "upload-note", "--account", account, "--title", title, "--note", note, "--tags", tags, "--images", *saved_images]
    hflag = _headless_flag(headless)
    if hflag:
        argv.append("--headless" if hflag == "true" else "--headed")
    if debug in ("true", "1"):
        argv.append("--debug")
    if platform == "tencent":
        data_input = request.get_json(silent=True) if request.is_json else None
        is_draft_raw = (data_input.get("is_draft", "") if isinstance(data_input, dict) else request.form.get("is_draft", ""))
        if str(is_draft_raw).lower() in ("true", "1", "yes", "on"):
            argv.append("--draft")

    task_id = _new_task_id("upload-note")
    if schedule:
        normalised = _normalise_schedule(schedule)
        parsed = datetime.strptime(normalised, '%Y-%m-%d %H:%M')
        _db_insert_task(task_id=task_id, status="scheduled", platform=platform, action="upload-note", account=account, created=datetime.now().isoformat(timespec="seconds"), argv=argv)
        _schedule_task(task_id, argv, parsed)
    else:
        _db_insert_task(task_id=task_id, status="pending", platform=platform, action="upload-note", account=account, created=datetime.now().isoformat(timespec="seconds"), argv=argv)
        task_executor.submit(_run_sau, task_id, argv)
    return jsonify({"success": True, "data": {"task_id": task_id}})


@bp.get("/api/upload/progress")
def upload_progress_sse():
    task_id = request.args.get("task_id", "")
    if not task_id:
        return jsonify({"success": False, "message": "task_id is required"}), 400
    task = _db_get_task(task_id)
    if not task:
        return jsonify({"success": False, "message": f"Task not found: {task_id}"}), 404

    terminal_statuses = {"success", "failed", "error"}
    if task.get("status") in terminal_statuses:
        return jsonify({"success": True, "data": {"status": task["status"], "code": task.get("code"), "error": task.get("error"), "result": task.get("result")}})

    with _progress_sub_lock:
        active_count = sum(len(qs) for qs in _progress_subscribers.values())
        if active_count >= 5:
            return jsonify({"success": False, "message": "Too many SSE connections"}), 429

    q: _queue.Queue = _queue.Queue()
    with _progress_sub_lock:
        _progress_subscribers.setdefault(task_id, []).append(q)

    def generate() -> Generator:
        yield f": {' ' * 4096}\n\n"
        import time
        start_time = time.time()
        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > _SSE_TIMEOUT_SECONDS:
                    yield f"event: error\ndata: {json.dumps({'message': 'SSE timeout'})}\n\n"
                    break
                try:
                    msg = q.get(timeout=2)
                    yield f"event: log\ndata: {json.dumps({'message': msg})}\n\n"
                except _queue.Empty:
                    pass
                task = _db_get_task(task_id)
                if task and task.get("status") in terminal_statuses:
                    yield f"event: done\ndata: {json.dumps({'status': task['status'], 'code': task.get('code'), 'error': task.get('error'), 'result': task.get('result')})}\n\n"
                    break
                yield f"event: ping\ndata: {json.dumps({'ts': datetime.now().isoformat()})}\n\n"
        finally:
            with _progress_sub_lock:
                subs = _progress_subscribers.get(task_id, [])
                if q in subs:
                    subs.remove(q)
                if not subs:
                    _progress_subscribers.pop(task_id, None)

    return Response(generate(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})
