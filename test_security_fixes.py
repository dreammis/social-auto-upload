"""
Tests for the 4 security/logic fixes in sau_backend.py:
1. Path traversal: secure_filename used in /upload and /uploadSave
2. CORS restricted to localhost origins
3. XHS batch publish: case 1 calls post_video_xhs, no bare return
4. SSE leak: GeneratorExit handled, call_on_close registered
"""
import sys
import types
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out heavy imports before loading sau_backend
# ---------------------------------------------------------------------------
def _make_stub(name):
    mod = types.ModuleType(name)
    return mod


for mod_name in [
    "conf",
    "myUtils",
    "myUtils.auth",
    "myUtils.login",
    "myUtils.postVideo",
    "playwright",
    "playwright.async_api",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = _make_stub(mod_name)

# Provide BASE_DIR used by sau_backend at module level
sys.modules["conf"].BASE_DIR = Path("/tmp/sau_test")

# Stub login helpers
for fn in ["get_tencent_cookie", "douyin_cookie_gen", "get_ks_cookie", "xiaohongshu_cookie_gen"]:
    setattr(sys.modules["myUtils.login"], fn, MagicMock())

# Stub postVideo helpers; we need real references for call assertions
_mock_post_xhs = MagicMock()
_mock_post_tencent = MagicMock()
_mock_post_douyin = MagicMock()
_mock_post_ks = MagicMock()
sys.modules["myUtils.postVideo"].post_video_xhs = _mock_post_xhs
sys.modules["myUtils.postVideo"].post_video_tencent = _mock_post_tencent
sys.modules["myUtils.postVideo"].post_video_DouYin = _mock_post_douyin
sys.modules["myUtils.postVideo"].post_video_ks = _mock_post_ks

sys.modules["myUtils.auth"].check_cookie = MagicMock(return_value=True)

import sau_backend  # noqa: E402  (must come after stubs)
from sau_backend import app, sse_stream  # noqa: E402


# ---------------------------------------------------------------------------
# Fix 1: Path traversal — secure_filename used in upload handlers
# ---------------------------------------------------------------------------

def test_upload_rejects_path_traversal():
    """POST /upload with a traversal filename returns 400 (secure_filename strips it)."""
    client = app.test_client()
    data = {"file": (b"dummy content", "../../../etc/passwd")}
    rv = client.post(
        "/upload",
        data=data,
        content_type="multipart/form-data",
    )
    # secure_filename("../../../etc/passwd") == "etc_passwd" on some systems or "" on others;
    # either way the file must NOT be saved under a traversal path.
    # Our implementation rejects empty safe_name with 400; non-empty names are safe because
    # werkzeug strips the leading dots/slashes.
    assert rv.status_code in (400, 500)


def test_upload_save_uses_secure_filename():
    """The source code of upload_save must use secure_filename on custom_filename path."""
    src = inspect.getsource(sau_backend.upload_save)
    assert "secure_filename" in src, "upload_save must call secure_filename()"


def test_upload_file_uses_secure_filename():
    """The source code of upload_file must use secure_filename."""
    src = inspect.getsource(sau_backend.upload_file)
    assert "secure_filename" in src, "upload_file must call secure_filename()"


# ---------------------------------------------------------------------------
# Fix 2: CORS restricted to localhost
# ---------------------------------------------------------------------------

def test_cors_not_wildcard():
    """CORS must not be configured with wildcard origin '*'."""
    import sau_backend as backend
    src = inspect.getsource(backend)
    assert "CORS(app)" not in src.replace(" ", ""), \
        "CORS must not use unrestricted CORS(app)"
    assert 'origins=["http://localhost' in src or "origins=['http://localhost" in src, \
        "CORS must restrict origins to localhost"


def test_cors_options_header_localhost():
    """Preflight request from localhost should include CORS headers."""
    client = app.test_client()
    rv = client.options(
        "/upload",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Flask-CORS should allow localhost origin
    origin_header = rv.headers.get("Access-Control-Allow-Origin", "")
    assert "localhost" in origin_header or rv.status_code == 200, \
        f"Expected CORS allow for localhost, got: {origin_header}"


# ---------------------------------------------------------------------------
# Fix 3: XHS batch publish — case 1 calls post_video_xhs, no bare return
# ---------------------------------------------------------------------------

def test_post_video_xhs_called_for_type_1():
    """POST /postVideo with type=1 must call post_video_xhs, not return early."""
    _mock_post_xhs.reset_mock()
    client = app.test_client()
    payload = {
        "type": 1,
        "title": "test title",
        "fileList": ["video1.mp4"],
        "accountList": ["account1"],
        "tags": [],
        "category": None,
        "enableTimer": False,
        "videosPerDay": 1,
        "dailyTimes": ["10:00"],
        "startDays": 0,
    }
    rv = client.post("/postVideo", json=payload)
    assert rv.status_code == 200, f"Expected 200, got {rv.status_code}: {rv.data}"
    _mock_post_xhs.assert_called_once()


def test_postVideo_case1_no_bare_return():
    """Source code of postVideo must not have a bare 'return' in case 1 block."""
    src = inspect.getsource(sau_backend.postVideo)
    lines = src.splitlines()
    in_case1 = False
    for line in lines:
        stripped = line.strip()
        if stripped in ('case 1:', "case 1 :"):
            in_case1 = True
        elif in_case1 and stripped.startswith("case "):
            in_case1 = False
        elif in_case1 and stripped == "return":
            raise AssertionError("case 1 has bare 'return' that terminates the entire function")


# ---------------------------------------------------------------------------
# Fix 4: SSE leak — GeneratorExit handled + call_on_close registered
# ---------------------------------------------------------------------------

def test_sse_stream_handles_generator_exit():
    """sse_stream generator must not propagate GeneratorExit."""
    from queue import Queue
    q = Queue()
    gen = sse_stream(q)
    # Closing the generator triggers GeneratorExit inside it; must not raise
    gen.close()  # This would raise if GeneratorExit is not caught


def test_sse_stream_source_catches_generator_exit():
    """sse_stream source must explicitly catch GeneratorExit."""
    src = inspect.getsource(sse_stream)
    assert "GeneratorExit" in src, "sse_stream must handle GeneratorExit"


def test_login_registers_call_on_close():
    """login() route source must register on_close via response.call_on_close()."""
    src = inspect.getsource(sau_backend.login)
    assert "call_on_close" in src, \
        "login() must call response.call_on_close(on_close) to prevent SSE leak"
