"""Account groups routes."""
from __future__ import annotations

import os
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

from web_runner.db import DB_PATH, get_connection
from web_runner.utils import (
    COOKIES_DIR,
    _QR_LOGIN_PLATFORMS,
    _quick_check_cookie,
    _validate_group_name,
    log,
)

bp = Blueprint("account_groups", __name__)


@bp.get("/api/account-groups")
def list_account_groups():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        groups = conn.execute("SELECT * FROM account_groups ORDER BY sort_order ASC, created DESC").fetchall()
        result = []
        for group in groups:
            auths = conn.execute(
                "SELECT * FROM account_authorizations WHERE group_id = ? ORDER BY sort_order ASC",
                (group["id"],)
            ).fetchall()
            authorizations = []
            for auth in auths:
                cookie_path = Path(auth["cookie_file"])
                quick = _quick_check_cookie(auth["platform"], group["name"]) if cookie_path.exists() else {"valid": False, "reason": "no_file"}
                authorizations.append({
                    "id": auth["id"], "platform": auth["platform"],
                    "cookie_file": auth["cookie_file"], "valid": quick["valid"], "reason": quick.get("reason"),
                })
            result.append({"id": group["id"], "name": group["name"], "created": group["created"], "authorizations": authorizations})
    return jsonify({"success": True, "data": result})


@bp.post("/api/account-groups")
def create_account_group():
    payload = request.get_json(silent=True) or {}
    valid, cleaned_or_msg = _validate_group_name(payload.get("name"))
    if not valid:
        return jsonify({"success": False, "message": cleaned_or_msg}), 400
    name = cleaned_or_msg
    with get_connection() as conn:
        try:
            conn.execute("INSERT INTO account_groups (name, created) VALUES (?, ?)", (name, datetime.now().isoformat(timespec="seconds")))
            conn.commit()
            group_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "分组名已存在"}), 409
    log(f"[account-groups] created: {name}")
    return jsonify({"success": True, "data": {"id": group_id, "name": name}})


@bp.delete("/api/account-groups/<int:group_id>")
def delete_account_group(group_id: int):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT * FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404
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


@bp.post("/api/account-groups/<int:group_id>/rename")
def rename_account_group(group_id: int):
    payload = request.get_json(silent=True) or {}
    valid, cleaned_or_msg = _validate_group_name(payload.get("name"))
    if not valid:
        return jsonify({"success": False, "message": cleaned_or_msg}), 400
    new_name = cleaned_or_msg
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT id, name FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "分组不存在"}), 404
        old_name = group["name"]
        if old_name == new_name:
            return jsonify({"success": True, "data": {"id": group_id, "name": new_name}})
        auth_rows = conn.execute("SELECT id, platform, cookie_file FROM account_authorizations WHERE group_id = ?", (group_id,)).fetchall()
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
                for op, np in reversed(renamed_so_far):
                    try:
                        os.rename(np, op)
                    except OSError:
                        pass
                log(f"[account-groups] rename FAIL: {old_path} -> {new_path}: {e}")
                return jsonify({"success": False, "message": f"无法移动 cookie 文件 {old_path.name}，文件可能正在被使用"}), 409
        try:
            conn.execute("UPDATE account_groups SET name = ? WHERE id = ?", (new_name, group_id))
            for auth in auth_rows:
                new_path = COOKIES_DIR / f"{auth['platform']}_{new_name}.json"
                conn.execute("UPDATE account_authorizations SET cookie_file = ? WHERE id = ?", (str(new_path), auth["id"]))
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


@bp.post("/api/account-groups/<int:group_id>/authorize")
def authorize_account_group(group_id: int):
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")
    if not platform:
        return jsonify({"success": False, "message": "platform is required"}), 400
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT * FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404
        existing = conn.execute("SELECT * FROM account_authorizations WHERE group_id = ? AND platform = ?", (group_id, platform)).fetchone()
        if existing:
            return jsonify({"success": False, "message": f"Platform '{platform}' already authorized"}), 409
    cookie_file = COOKIES_DIR / f"{platform}_{group['name']}.json"
    return jsonify({"success": True, "data": {"group_name": group["name"], "platform": platform, "cookie_file": str(cookie_file)}})


@bp.post("/api/account-groups/<int:group_id>/confirm-authorize")
def confirm_authorize_account_group(group_id: int):
    payload = request.get_json(silent=True) or {}
    platform = payload.get("platform")
    if not platform:
        return jsonify({"success": False, "message": "platform is required"}), 400
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT * FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404
    cookie_file = COOKIES_DIR / f"{platform}_{group['name']}.json"
    for _ in range(10):
        if cookie_file.exists():
            quick = _quick_check_cookie(platform, group["name"])
            if quick["valid"]:
                break
        time.sleep(0.5)
    else:
        return jsonify({"success": False, "message": "Cookie file not found or invalid after login"}), 400
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO account_authorizations (group_id, platform, cookie_file, created) VALUES (?, ?, ?, ?)",
                (group_id, platform, str(cookie_file), datetime.now().isoformat(timespec="seconds"))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.execute(
                "UPDATE account_authorizations SET cookie_file = ?, created = ? WHERE group_id = ? AND platform = ?",
                (str(cookie_file), datetime.now().isoformat(timespec="seconds"), group_id, platform)
            )
            conn.commit()
    log(f"[account-groups] authorized: {group['name']} -> {platform}")
    return jsonify({"success": True, "message": f"Platform '{platform}' authorized for group '{group['name']}'"})


@bp.delete("/api/account-groups/<int:group_id>/authorize/<platform>")
def remove_authorization(group_id: int, platform: str):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        group = conn.execute("SELECT * FROM account_groups WHERE id = ?", (group_id,)).fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404
        auth = conn.execute("SELECT * FROM account_authorizations WHERE group_id = ? AND platform = ?", (group_id, platform)).fetchone()
        if not auth:
            return jsonify({"success": False, "message": "Authorization not found"}), 404
        cookie_path = Path(auth["cookie_file"])
        if cookie_path.exists():
            cookie_path.unlink()
        conn.execute("DELETE FROM account_authorizations WHERE id = ?", (auth["id"],))
        conn.commit()
    log(f"[account-groups] removed authorization: {group['name']} -> {platform}")
    return jsonify({"success": True, "message": f"Platform '{platform}' authorization removed"})


@bp.post("/api/account-groups/reorder")
def reorder_account_groups():
    payload = request.get_json(silent=True) or {}
    group_ids = payload.get("group_ids", [])
    if not group_ids:
        return jsonify({"success": False, "message": "group_ids is required"}), 400
    with get_connection() as conn:
        for idx, group_id in enumerate(group_ids):
            conn.execute("UPDATE account_groups SET sort_order = ? WHERE id = ?", (idx, group_id))
        conn.commit()
    log(f"[account-groups] reordered: {len(group_ids)} groups")
    return jsonify({"success": True, "message": "Groups reordered successfully"})


@bp.post("/api/account-groups/<int:group_id>/reorder-authorizations")
def reorder_authorizations(group_id: int):
    payload = request.get_json(silent=True) or {}
    auth_ids = payload.get("auth_ids", [])
    if not auth_ids:
        return jsonify({"success": False, "message": "auth_ids is required"}), 400
    with get_connection() as conn:
        for idx, auth_id in enumerate(auth_ids):
            conn.execute("UPDATE account_authorizations SET sort_order = ? WHERE id = ? AND group_id = ?", (idx, auth_id, group_id))
        conn.commit()
    log(f"[account-groups] reordered authorizations: group {group_id}, {len(auth_ids)} items")
    return jsonify({"success": True, "message": "Authorizations reordered successfully"})
