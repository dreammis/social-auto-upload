"""Task management routes."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from flask import Blueprint, jsonify, request

from web_runner.db import DB_PATH, db_lock, get_connection
from web_runner.utils import (
    _db_get_all_tasks,
    _db_get_error_events,
    _db_get_logs,
    _db_get_task,
    _db_insert_task,
    _new_task_id,
    _run_sau,
    _scheduled_timers,
    _timer_lock,
    log,
    task_executor,
)

bp = Blueprint("tasks", __name__)


@bp.get("/api/tasks")
def list_tasks():
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", 0, type=int)
    rows = _db_get_all_tasks(limit=limit, offset=offset)
    return jsonify({"success": True, "data": rows})


@bp.post("/api/tasks/retry")
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
        task_id=new_task_id, status="pending",
        platform=task.get("platform", "") or "",
        action=f"retry-{task.get('action', 'unknown')}",
        account=task.get("account", "") or "",
        created=datetime.now().isoformat(timespec="seconds"), argv=argv,
    )
    task_executor.submit(_run_sau, new_task_id, argv)
    log(f"[{new_task_id}] retry of {task_id}: sau {' '.join(argv)}")
    return jsonify({"success": True, "data": {"task_id": new_task_id}})


@bp.post("/api/tasks/delete")
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
        with get_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
    log(f"[tasks] deleted task: {task_id}")
    return jsonify({"success": True, "message": f"Task {task_id} deleted"})


@bp.post("/api/tasks/clear")
def clear_tasks():
    payload = request.get_json(silent=True) or {}
    status_filter = payload.get("status", ["success", "failed", "error"])
    if isinstance(status_filter, str):
        status_filter = [status_filter]
    placeholders = ",".join("?" for _ in status_filter)
    with db_lock:
        with get_connection() as conn:
            cursor = conn.execute(f"DELETE FROM tasks WHERE status IN ({placeholders})", status_filter)
            deleted = cursor.rowcount
            conn.commit()
    log(f"[tasks] cleared {deleted} tasks with status: {status_filter}")
    return jsonify({"success": True, "data": {"deleted": deleted}})


@bp.post("/api/tasks/add")
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
        task_id=task_id, status="pending", platform=platform,
        action=action, account=account,
        created=datetime.now().isoformat(timespec="seconds"), argv=argv,
    )
    task_executor.submit(_run_sau, task_id, argv)
    log(f"[{task_id}] manual task: sau {' '.join(argv)}")
    return jsonify({"success": True, "data": {"task_id": task_id}})


@bp.get("/api/logs")
def get_logs():
    after = request.args.get("after")
    task_id = request.args.get("task_id")
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", 0, type=int)
    return jsonify({"success": True, "data": _db_get_logs(after, task_id, limit=limit, offset=offset)})


@bp.get("/api/error-events")
def get_error_events_route():
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
