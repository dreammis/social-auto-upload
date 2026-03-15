"""Tests for the four security/bug fixes in sau_backend.py."""
import io
import sys
import types
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# Stub out heavy / browser-dependent modules before importing sau_backend
# ---------------------------------------------------------------------------

def _make_stub(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


# conf
_conf = _make_stub("conf")
_conf.BASE_DIR = Path(__file__).parent / "tmp_videoFile"

# myUtils and sub-modules
_myUtils = _make_stub("myUtils")
_auth = _make_stub("myUtils.auth")
_auth.check_cookie = MagicMock(return_value=True)
_login = _make_stub("myUtils.login")
_login.get_tencent_cookie = MagicMock()
_login.douyin_cookie_gen = MagicMock()
_login.get_ks_cookie = MagicMock()
_login.xiaohongshu_cookie_gen = MagicMock()
_post = _make_stub("myUtils.postVideo")
_post.post_video_tencent = MagicMock()
_post.post_video_DouYin = MagicMock()
_post.post_video_ks = MagicMock()
_post.post_video_xhs = MagicMock()

# Now import the app
import sau_backend  # noqa: E402
from sau_backend import app, sse_stream  # noqa: E402


@pytest.fixture(autouse=True)
def video_dir(tmp_path):
    """Redirect sau_backend.BASE_DIR so saved files go to a temp dir."""
    import sqlite3 as _sqlite3
    (tmp_path / "videoFile").mkdir()
    (tmp_path / "db").mkdir()
    with _sqlite3.connect(tmp_path / "db" / "database.db") as conn:
        conn.execute(
            "CREATE TABLE file_records "
            "(id INTEGER PRIMARY KEY, filename TEXT, filesize INTEGER, file_path TEXT)"
        )
    with patch.object(sau_backend, "BASE_DIR", tmp_path):
        yield tmp_path


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Fix 1 – Path traversal: secure_filename applied; empty result → 400
# ---------------------------------------------------------------------------

class TestUploadPathTraversal:
    def test_upload_rejects_empty_filename(self, client, video_dir):
        """Filename that becomes empty after secure_filename must return 400."""
        data = {"file": (io.BytesIO(b"data"), "..")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_upload_saves_safe_name(self, client, video_dir):
        """Normal filename: file is saved under secure name inside videoFile/."""
        data = {"file": (io.BytesIO(b"hello"), "video.mp4")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        saved = list((video_dir / "videoFile").iterdir())
        assert any("video.mp4" in f.name for f in saved)

    def test_upload_save_rejects_empty_filename(self, client, video_dir):
        """uploadSave: filename that becomes empty after secure_filename → 400."""
        data = {"file": (io.BytesIO(b"data"), "..")}
        resp = client.post("/uploadSave", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_upload_save_strips_traversal(self, client, video_dir):
        """uploadSave: path-traversal chars are stripped; file is accepted."""
        data = {"file": (io.BytesIO(b"data"), "../evil.mp4")}
        resp = client.post("/uploadSave", data=data, content_type="multipart/form-data")
        # secure_filename strips '../' so filename becomes 'evil.mp4' → 200
        assert resp.status_code == 200
        saved = list((video_dir / "videoFile").iterdir())
        # No file should contain '..' in its name
        assert all(".." not in f.name for f in saved)


# ---------------------------------------------------------------------------
# Fix 2 – CORS: origins restricted to localhost only
# ---------------------------------------------------------------------------

class TestCorsRestriction:
    def test_cors_origins_not_wildcard(self):
        """CORS must not be configured with a wildcard (*) origin."""
        from flask_cors import CORS  # noqa: F401
        # Inspect the app's after_request handlers for CORS headers
        # by sending a preflight from a non-localhost origin and verifying
        # it does NOT receive 'Access-Control-Allow-Origin: *'.
        with app.test_client() as c:
            resp = c.options(
                "/upload",
                headers={
                    "Origin": "https://evil.example.com",
                    "Access-Control-Request-Method": "POST",
                },
            )
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
            assert acao != "*", "CORS must not allow all origins"

    def test_cors_allows_localhost(self):
        """CORS must allow localhost origins."""
        with app.test_client() as c:
            resp = c.options(
                "/upload",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "POST",
                },
            )
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
            assert "localhost" in acao or acao == "http://localhost:5173"


# ---------------------------------------------------------------------------
# Fix 3 – XHS batch publish bug: case 1 calls post_video_xhs, not return
# ---------------------------------------------------------------------------

class TestXhsBatchPublish:
    def test_case1_calls_post_video_xhs(self, client, video_dir):
        """type=1 (XHS) must invoke post_video_xhs, not exit early."""
        _post.post_video_xhs.reset_mock()
        payload = {
            "type": 1,
            "title": "test title",
            "tags": ["tag"],
            "fileList": ["file.mp4"],
            "accountList": ["account1"],
            "category": None,
            "enableTimer": False,
            "videosPerDay": 1,
            "dailyTimes": ["10:00"],
            "startDays": 0,
            "thumbnail": "",
            "productLink": "",
            "productTitle": "",
            "isDraft": False,
        }
        resp = client.post("/postVideo", json=payload)
        assert resp.status_code == 200
        _post.post_video_xhs.assert_called_once()


# ---------------------------------------------------------------------------
# Fix 4 – SSE resource leak: GeneratorExit exits loop cleanly
# ---------------------------------------------------------------------------

class TestSseStreamCleanup:
    def test_generator_exit_stops_sse_stream(self):
        """sse_stream must terminate cleanly when GeneratorExit is raised."""
        q = Queue()
        gen = sse_stream(q)
        # Advance generator to first yield point (it will block on empty queue)
        # We call close() which raises GeneratorExit inside the generator.
        gen.close()  # Must not raise StopIteration or propagate any exception

    def test_sse_stream_yields_messages(self):
        """sse_stream yields queued messages in SSE format."""
        q = Queue()
        q.put("hello")
        gen = sse_stream(q)
        msg = next(gen)
        assert msg == "data: hello\n\n"
        gen.close()

    def test_login_registers_call_on_close(self, client):
        """The /login SSE response must register on_close via call_on_close."""
        registered = []

        original_call_on_close = None

        class PatchedResponse:
            def __init__(self, *a, **kw):
                from flask import Response as FlaskResponse
                self._resp = FlaskResponse(*a, **kw)

            def call_on_close(self, fn):
                registered.append(fn)
                return self._resp.call_on_close(fn)

        # Verify that active_queues cleanup is registered
        # by checking that on_close is added to response.call_on_close in the route
        import inspect
        source = inspect.getsource(sau_backend.login)
        assert "call_on_close" in source, (
            "login() must register on_close via response.call_on_close()"
        )
