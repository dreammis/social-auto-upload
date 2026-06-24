from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def app():
    import web_runner as wr

    wr.app.config["TESTING"] = True
    with tempfile.TemporaryDirectory() as tmp_dir:
        orig_cookies_dir = wr.COOKIES_DIR
        wr.COOKIES_DIR = Path(tmp_dir)
        with wr.app.test_client() as client:
            yield client
        wr.COOKIES_DIR = orig_cookies_dir


class TestHealth:
    def test_health(self, app):
        resp = app.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True


def _data_uri_png() -> str:
    """Minimal 1x1 red PNG as data URI for testing."""
    raw = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    import base64
    return f"data:image/png;base64,{base64.b64encode(raw).decode()}"


class TestAccounts:
    def test_list_accounts_empty(self, app):
        resp = app.get("/api/accounts")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"] == []

    def test_list_accounts_with_files(self, app):
        import web_runner as wr
        from unittest.mock import patch

        mock_accounts = [
            {"platform": "douyin", "account_name": "testuser", "path": "/fake/douyin_testuser.json"},
            {"platform": "kuaishou", "account_name": "testuser", "path": "/fake/kuaishou_testuser.json"},
        ]
        def mock_account_files(platform=None):
            if platform:
                return [a for a in mock_accounts if a["platform"] == platform]
            return mock_accounts

        with patch.object(wr, '_account_files', side_effect=mock_account_files):
            resp = app.get("/api/accounts")
            data = resp.get_json()
            accounts = data["data"]
            assert len(accounts) == 2

            resp = app.get("/api/accounts?platform=douyin")
            data = resp.get_json()
            accounts = data["data"]
            assert len(accounts) == 1
            assert accounts[0]["platform"] == "douyin"
            assert accounts[0]["account_name"] == "testuser"

    def test_delete_account(self, app):
        import web_runner as wr

        (wr.COOKIES_DIR / "douyin_testuser.json").write_text("{}")
        assert (wr.COOKIES_DIR / "douyin_testuser.json").exists()

        resp = app.post(
            "/api/accounts/delete",
            data=json.dumps({"platform": "douyin", "account": "testuser"}),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["success"] is True
        assert not (wr.COOKIES_DIR / "douyin_testuser.json").exists()

    def test_delete_account_not_found(self, app):
        resp = app.post(
            "/api/accounts/delete",
            data=json.dumps({"platform": "douyin", "account": "nonexistent"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_delete_account_missing_params(self, app):
        resp = app.post(
            "/api/accounts/delete",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_login_missing_params(self, app):
        resp = app.post(
            "/api/accounts/login",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_login_response_has_data_task_id(self, app):
        with patch("web_runner._run_sau"):
            resp = app.post(
                "/api/accounts/login",
                data=json.dumps({"platform": "douyin", "account": "test"}),
                content_type="application/json",
            )
        data = resp.get_json()
        assert data["success"] is True
        assert "task_id" in data["data"]


class TestUpload:
    def test_upload_video_missing_file_data(self, app):
        resp = app.post(
            "/api/upload/video",
            data=json.dumps({"platform": "douyin", "account": "test", "title": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_upload_video_response_has_data_task_id(self, app):
        with patch("web_runner._run_sau"), patch("web_runner.MIN_UPLOAD_BYTES", 0):
            resp = app.post(
                "/api/upload/video",
                data={
                    "platform": "douyin",
                    "account": "test",
                    "title": "test",
                    "file_data": _data_uri_png(),
                },
            )
        data = resp.get_json()
        assert data["success"] is True
        assert "task_id" in data["data"]

    def test_upload_note_with_data_uris(self, app):
        with patch("web_runner._run_sau"), patch("web_runner.MIN_UPLOAD_BYTES", 0):
            resp = app.post(
                "/api/upload/note",
                data=json.dumps({
                    "platform": "douyin",
                    "account": "test",
                    "title": "test",
                    "images": [_data_uri_png(), _data_uri_png()],
                }),
                content_type="application/json",
            )
        data = resp.get_json()
        assert data["success"] is True
        assert "task_id" in data["data"]

    def test_upload_note_missing_images(self, app):
        resp = app.post(
            "/api/upload/note",
            data=json.dumps({"platform": "douyin", "account": "test", "title": "test"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestLogs:
    def test_get_logs_empty(self, app):
        resp = app.get("/api/logs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_get_logs_with_data(self, app):
        import web_runner as wr

        wr.log("test message 1")
        wr.log("test message 2")

        resp = app.get("/api/logs")
        data = resp.get_json()
        assert len(data["data"]) >= 2
        assert any("test message 1" in entry["message"] for entry in data["data"])

    def test_get_logs_with_after_filter(self, app):
        import web_runner as wr

        wr.log("before message")
        ts = "2099-01-01T00:00:00"
        resp = app.get(f"/api/logs?after={ts}")
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)


class TestTasks:
    def test_get_tasks(self, app):
        resp = app.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)


class TestFrontend:
    def test_index_returns_html_or_default(self, app):
        resp = app.get("/")
        assert resp.status_code == 200
        assert resp.content_type.startswith("text/html")
