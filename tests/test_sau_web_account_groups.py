from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def app():
    """Flask test client with isolated temporary cookies dir and DB."""
    import web_runner as wr

    wr.app.config["TESTING"] = True
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # Redirect COOKIES_DIR to temp
        orig_cookies_dir = wr.COOKIES_DIR
        wr.COOKIES_DIR = tmp / "cookies"
        wr.COOKIES_DIR.mkdir(exist_ok=True)

        # Redirect DB to temp
        orig_db_path = wr.DB_PATH
        db_path = tmp / "test.db"
        wr.DB_PATH = db_path

        # Re-initialise DB tables in the temp DB
        _init_temp_db(db_path)

        with wr.app.test_client() as client:
            yield client

        wr.COOKIES_DIR = orig_cookies_dir
        wr.DB_PATH = orig_db_path


def _init_temp_db(db_path: Path) -> None:
    """Create all required tables in a temp DB (prevents watchdog noise on tasks/logs)."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS account_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS account_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                cookie_file TEXT NOT NULL,
                created TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES account_groups(id) ON DELETE CASCADE,
                UNIQUE(group_id, platform)
            )
        """)
        # Also create tasks/logs tables so the orphan watchdog daemon doesn't error
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, status TEXT, platform TEXT,
                action TEXT, account TEXT, created TEXT, code INTEGER,
                error TEXT, argv TEXT, result TEXT, publish_detail TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                ts TEXT NOT NULL, message TEXT NOT NULL
            )
        """)
        conn.commit()


def _create_group(db_path: Path, name: str) -> int:
    """Insert a test group and return its ID."""
    from datetime import datetime

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO account_groups (name, created) VALUES (?, ?)",
            (name, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_authorization(db_path: Path, group_id: int, platform: str, cookie_file: str) -> None:
    """Insert an existing authorization for a group."""
    from datetime import datetime

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO account_authorizations (group_id, platform, cookie_file, created) VALUES (?, ?, ?, ?)",
            (group_id, platform, cookie_file, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()


def _authorize(app, group_id: int, platform: str) -> tuple[int, dict]:
    """POST /api/account-groups/<id>/authorize and return (status_code, json_body)."""
    resp = app.post(
        f"/api/account-groups/{group_id}/authorize",
        data=json.dumps({"platform": platform}),
        content_type="application/json",
    )
    return resp.status_code, resp.get_json()


# ===========================================================================
#  QR PLATFORM BRANCH
# ===========================================================================


class TestAuthorizeQrPlatforms:
    """QR platforms (douyin, kuaishou, xiaohongshu, tencent, bilibili) return 200 with group_name/platform/cookie_file."""

    QR_PLATFORMS = ["douyin", "kuaishou", "xiaohongshu", "tencent", "bilibili"]

    def test_all_qr_platforms_return_200(self, app):
        import web_runner as wr

        for platform in self.QR_PLATFORMS:
            group_id = _create_group(wr.DB_PATH, f"test-{platform[:4]}")

            status, data = _authorize(app, group_id, platform)
            assert status == 200, f"{platform}: expected 200, got {status}"
            assert data["success"] is True, f"{platform}: {data}"
            assert data["data"]["platform"] == platform
            assert data["data"]["group_name"] == f"test-{platform[:4]}"
            assert "cookie_file" in data["data"]

            # cookie_file should point to cookies/{platform}_{group_name}.json
            expected_cookie = str(wr.COOKIES_DIR / f"{platform}_test-{platform[:4]}.json")
            assert data["data"]["cookie_file"] == expected_cookie

            # task_id must NOT be in response (was removed in a prev fix)
            assert "task_id" not in data["data"], f"{platform}: task_id should not be in response"

    # ---- Douyin specific ----

    def test_douyin_authorize_returns_correct_cookie_path(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "创作组")
        _, data = _authorize(app, group_id, "douyin")

        expected = str(wr.COOKIES_DIR / "douyin_创作组.json")
        assert data["data"]["cookie_file"] == expected
        assert data["data"]["group_name"] == "创作组"
        assert data["data"]["platform"] == "douyin"

    # ---- Bilibili specific ----

    def test_bilibili_authorize_returns_correct_cookie_path(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "B站组")
        _, data = _authorize(app, group_id, "bilibili")

        expected = str(wr.COOKIES_DIR / "bilibili_B站组.json")
        assert data["data"]["cookie_file"] == expected

    # ---- Tencent specific ----

    def test_tencent_authorize_returns_correct_cookie_path(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "视频号组")
        _, data = _authorize(app, group_id, "tencent")

        expected = str(wr.COOKIES_DIR / "tencent_视频号组.json")
        assert data["data"]["cookie_file"] == expected


# ===========================================================================
#  NON-QR PLATFORM BRANCH  (tiktok, baijiahao)
# ===========================================================================


class TestAuthorizeNonQrPlatforms:
    """Non-QR platforms (tiktok, baijiahao) return 200 with the same fields but no task_id."""

    NON_QR_PLATFORMS = ["tiktok", "baijiahao"]

    def test_all_non_qr_platforms_return_200(self, app):
        import web_runner as wr

        for platform in self.NON_QR_PLATFORMS:
            group_id = _create_group(wr.DB_PATH, f"test-{platform[:4]}")

            status, data = _authorize(app, group_id, platform)
            assert status == 200, f"{platform}: expected 200, got {status}"
            assert data["success"] is True, f"{platform}: {data}"
            assert data["data"]["platform"] == platform
            assert data["data"]["group_name"] == f"test-{platform[:4]}"
            assert "cookie_file" in data["data"]
            assert "task_id" not in data["data"], f"{platform}: task_id should not be in response"

    def test_tiktok_authorize_returns_correct_cookie_path(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "海外组")
        _, data = _authorize(app, group_id, "tiktok")

        expected = str(wr.COOKIES_DIR / "tiktok_海外组.json")
        assert data["data"]["cookie_file"] == expected

    def test_baijiahao_authorize_returns_correct_cookie_path(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "自媒体组")
        _, data = _authorize(app, group_id, "baijiahao")

        expected = str(wr.COOKIES_DIR / "baijiahao_自媒体组.json")
        assert data["data"]["cookie_file"] == expected

    def test_non_qr_branch_does_not_trigger_background_task(self, app):
        """Non-QR authorize must NOT spawn a background task (no _run_sau call)."""
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "manual-test")

        with patch("web_runner._run_sau") as mock_run:
            status, data = _authorize(app, group_id, "tiktok")

        assert status == 200
        mock_run.assert_not_called(), "_run_sau should NOT be called for non-QR platforms"


# ===========================================================================
#  ERROR CASES
# ===========================================================================


class TestAuthorizeErrors:
    """Error handling: missing platform, missing group, duplicate authorization."""

    def test_missing_platform_returns_400(self, app):
        resp = app.post(
            "/api/account-groups/1/authorize",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "platform" in data["message"].lower()

    def test_nonexistent_group_returns_404(self, app):
        status, data = _authorize(app, 99999, "douyin")

        assert status == 404
        assert data["success"] is False
        assert "not found" in data["message"].lower()

    def test_already_authorized_returns_409(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "dup-test")
        _insert_authorization(wr.DB_PATH, group_id, "douyin", "/fake/path.json")

        status, data = _authorize(app, group_id, "douyin")

        assert status == 409
        assert data["success"] is False
        assert "already authorized" in data["message"].lower()

    def test_already_authorized_returns_409_for_non_qr_too(self, app):
        """Duplicate check applies to non-QR platforms as well."""
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "dup-nonqr")
        _insert_authorization(wr.DB_PATH, group_id, "tiktok", "/fake/tiktok.json")

        status, data = _authorize(app, group_id, "tiktok")

        assert status == 409
        assert data["success"] is False
        assert "already authorized" in data["message"].lower()

    def test_group_still_accepts_different_platforms(self, app):
        """Authorizing one platform does not block another platform on the same group."""
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "multi-platform")

        # Authorize douyin (endpoint returns 200 but does NOT insert into DB)
        status1, data1 = _authorize(app, group_id, "douyin")
        assert status1 == 200

        # Still can authorize kuaishou (different platform, same group)
        status2, data2 = _authorize(app, group_id, "kuaishou")
        assert status2 == 200

        # Manually persist the douyin authorization to simulate confirm-authorize
        _insert_authorization(wr.DB_PATH, group_id, "douyin", "/fake/douyin.json")

        # Now douyin again is 409 (duplicate check works once persisted)
        status3, _ = _authorize(app, group_id, "douyin")
        assert status3 == 409


# ===========================================================================
#  EDGE CASES
# ===========================================================================


class TestAuthorizeEdgeCases:
    """Edge cases: special characters in group names, concurrent behavior."""

    def test_group_name_with_spaces(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "My Test Group")
        _, data = _authorize(app, group_id, "douyin")

        expected = str(wr.COOKIES_DIR / "douyin_My Test Group.json")
        assert data["data"]["cookie_file"] == expected
        assert data["data"]["group_name"] == "My Test Group"

    def test_group_name_with_special_chars(self, app):
        """Group names with underscores and hyphens are valid."""
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "test_user-01")
        _, data = _authorize(app, group_id, "xiaohongshu")

        expected = str(wr.COOKIES_DIR / "xiaohongshu_test_user-01.json")
        assert data["data"]["cookie_file"] == expected

    def test_multiple_qr_platforms_on_same_group(self, app):
        """A single group can have multiple QR platform authorizations."""
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "全能组")
        platforms = ["douyin", "kuaishou", "xiaohongshu", "bilibili", "tencent"]

        for platform in platforms:
            status, data = _authorize(app, group_id, platform)
            assert status == 200, f"{platform}: expected 200, got {status}"
            assert data["data"]["group_name"] == "全能组"

    def test_unlisted_platform_treated_as_non_qr(self, app):
        """A platform not in _QR_LOGIN_PLATFORMS falls through to the non-QR branch (200)."""
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "unlisted-plat")
        status, data = _authorize(app, group_id, "weibo")

        # weibo is not in _QR_LOGIN_PLATFORMS, so it hits the non-QR branch
        assert status == 200
        assert data["data"]["platform"] == "weibo"


# ===========================================================================
#  FS-SAFETY: create + rename endpoint
# ===========================================================================


import os as _test_os  # used only in TestAccountGroupFsSafety.disk-failure paths


class TestAccountGroupFsSafety:
    """Create + Rename endpoint filesystem-safety contract.

    Mirrors the frontend `validateGroupName` and backend `_validate_group_name`:
        - empty / whitespace-only     \u2192 400
        - > 64 chars                   \u2192 400
        - contains / \\ : * ? " < > | or control char \u2192 400
        - whitespace stripped on success

    Rename cascade contract:
        - updates `account_groups.name`
        - updates `account_authorizations.cookie_file` to new path
        - renames cookie files on disk (best-effort rollback on OSError)
    """

    FORBIDDEN_CHARS = ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\x00", "\n"]

    # \u2500\u2500 Create-endpoint validation \u2500\u2500

    def test_create_rejects_empty_name(self, app):
        resp = app.post(
            "/api/account-groups",
            data=json.dumps({"name": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["success"] is False
        assert "\u4e3a\u7a7a" in body["message"]

    def test_create_rejects_whitespace_only(self, app):
        resp = app.post(
            "/api/account-groups",
            data=json.dumps({"name": "   "}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_create_rejects_too_long_name(self, app):
        resp = app.post(
            "/api/account-groups",
            data=json.dumps({"name": "x" * 65}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "64" in body["message"]

    def test_create_rejects_illegal_chars(self, app):
        for ch in self.FORBIDDEN_CHARS:
            resp = app.post(
                "/api/account-groups",
                data=json.dumps({"name": f"bad{ch}name"}),
                content_type="application/json",
            )
            assert resp.status_code == 400, f"char {ch!r} not rejected"
            assert "\u4e0d\u5141\u8bb8" in resp.get_json()["message"]

    def test_create_accepts_valid_chinese(self, app):
        resp = app.post(
            "/api/account-groups",
            data=json.dumps({"name": "\u5168\u80fd\u7ec4"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["name"] == "\u5168\u80fd\u7ec4"

    def test_create_strips_whitespace(self, app):
        resp = app.post(
            "/api/account-groups",
            data=json.dumps({"name": "  spaced-group  "}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["name"] == "spaced-group"

    # \u2500\u2500 Rename-endpoint \u2500\u2500

    @staticmethod
    def _post_rename(client, group_id, name):
        resp = client.post(
            f"/api/account-groups/{group_id}/rename",
            data=json.dumps({"name": name}),
            content_type="application/json",
        )
        return resp.status_code, resp.get_json()

    def test_rename_happy_path_updates_db_and_disk(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "\u65e7\u540d")
        _insert_authorization(
            wr.DB_PATH,
            group_id,
            "douyin",
            str(wr.COOKIES_DIR / "douyin_\u65e7\u540d.json"),
        )
        (wr.COOKIES_DIR / "douyin_\u65e7\u540d.json").write_text('{"cookies":[]}')

        status, body = self._post_rename(app, group_id, "\u65b0\u540d")

        assert status == 200
        assert body["success"] is True
        assert body["data"]["name"] == "\u65b0\u540d"

        # DB row updated + cookie_file column points to new path
        with sqlite3.connect(wr.DB_PATH) as conn:
            assert conn.execute(
                "SELECT name FROM account_groups WHERE id = ?", (group_id,)
            ).fetchone()[0] == "\u65b0\u540d"
            cookie_row = conn.execute(
                "SELECT cookie_file FROM account_authorizations WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            assert cookie_row[0] == str(wr.COOKIES_DIR / "douyin_\u65b0\u540d.json")

        # Disk file renamed (old gone, new exists, content preserved)
        assert not (wr.COOKIES_DIR / "douyin_\u65e7\u540d.json").exists()
        assert (wr.COOKIES_DIR / "douyin_\u65b0\u540d.json").exists()
        assert (
            (wr.COOKIES_DIR / "douyin_\u65b0\u540d.json").read_text() == '{"cookies":[]}'
        )

    def test_rename_rejects_empty_name(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "stable")
        status, _ = self._post_rename(app, group_id, "   ")
        assert status == 400

    def test_rename_rejects_illegal_chars(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "stable")
        status, body = self._post_rename(app, group_id, "bad/name")
        assert status == 400
        assert "\u4e0d\u5141\u8bb8" in body["message"]

    def test_rename_nonexistent_returns_404(self, app):
        status, body = self._post_rename(app, 99999, "anything")
        assert status == 404
        assert "\u4e0d\u5b58\u5728" in body["message"]

    def test_rename_dup_name_returns_409(self, app):
        import web_runner as wr

        _create_group(wr.DB_PATH, "alpha")
        b = _create_group(wr.DB_PATH, "beta")
        status, _ = self._post_rename(app, b, "alpha")
        assert status == 409

    def test_rename_idempotent_when_name_unchanged(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "stable")
        status, body = self._post_rename(app, group_id, "stable")
        assert status == 200
        assert body["data"]["name"] == "stable"

    def test_rename_with_no_authorizations_succeeds(self, app):
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "empty")
        status, body = self._post_rename(app, group_id, "renamed")
        assert status == 200
        assert body["data"]["name"] == "renamed"

    def test_rename_disk_failure_rolls_back_earlier_success(self, app):
        """1 platform: forward rename works; 2nd platform: PermissionError.
        Verify rollback restored the first file and DB row unchanged.
        """
        import web_runner as wr

        group_id = _create_group(wr.DB_PATH, "\u539f\u59cb")
        _insert_authorization(
            wr.DB_PATH,
            group_id,
            "douyin",
            str(wr.COOKIES_DIR / "douyin_\u539f\u59cb.json"),
        )
        _insert_authorization(
            wr.DB_PATH,
            group_id,
            "kuaishou",
            str(wr.COOKIES_DIR / "kuaishou_\u539f\u59cb.json"),
        )
        (wr.COOKIES_DIR / "douyin_\u539f\u59cb.json").write_text("d")
        (wr.COOKIES_DIR / "kuaishou_\u539f\u59cb.json").write_text("k")

        real_rename = _test_os.rename
        counter = {"n": 0}

        def fake_rename(src, dst):
            counter["n"] += 1
            if counter["n"] == 2:
                raise PermissionError("simulated file lock")
            return real_rename(src, dst)

        with patch("web_runner.os.rename", side_effect=fake_rename):
            status, body = self._post_rename(app, group_id, "\u65b0\u540d")

        assert status == 409

        # DB row untouched
        with sqlite3.connect(wr.DB_PATH) as conn:
            assert (
                conn.execute(
                    "SELECT name FROM account_groups WHERE id = ?", (group_id,)
                ).fetchone()[0]
                == "\u539f\u59cb"
            )

        # Disk files restored to original names; no new-name files exist
        assert (wr.COOKIES_DIR / "douyin_\u539f\u59cb.json").exists()
        assert (wr.COOKIES_DIR / "kuaishou_\u539f\u59cb.json").exists()
        assert not (wr.COOKIES_DIR / "douyin_\u65b0\u540d.json").exists()
        assert not (wr.COOKIES_DIR / "kuaishou_\u65b0\u540d.json").exists()

