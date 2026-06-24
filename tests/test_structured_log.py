from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def client():
    """Build a Flask test client with isolated cookies dir; uses the real DB.

    Each test purges its own ``error_events`` rows before and after so we don't
    pollute the rest of the suite.
    """
    import web_runner as wr

    wr.app.config["TESTING"] = True
    with tempfile.TemporaryDirectory() as tmp_dir:
        orig_cookies_dir = wr.COOKIES_DIR
        wr.COOKIES_DIR = Path(tmp_dir)
        with wr.app.test_client() as c:
            yield c
        wr.COOKIES_DIR = orig_cookies_dir


def _purge_error_events() -> None:
    import web_runner as wr
    with wr.db_lock:
        with sqlite3.connect(wr.DB_PATH) as conn:
            conn.execute("DELETE FROM error_events")
            conn.commit()


class TestLogErrorEventHelper:
    def setup_method(self) -> None:
        _purge_error_events()

    def teardown_method(self) -> None:
        _purge_error_events()

    def test_writes_exc_type_message_and_traceback(self) -> None:
        import web_runner as wr

        try:
            raise ValueError("programmer bug")
        except ValueError as exc:
            wr._log_error_event(
                phase="cli",
                task_id="task-st-1",
                platform="douyin",
                account="acct-x",
                action="upload-video",
                exc=exc,
            )

        rows = wr._db_get_error_events(platform="douyin")
        assert len(rows) == 1
        row = rows[0]
        assert row["exc_type"] == "ValueError"
        assert "programmer bug" in row["exc_message"]
        assert "ValueError" in row["traceback"]
        assert "Traceback" in row["traceback"]
        assert row["platform"] == "douyin"
        assert row["account"] == "acct-x"
        assert row["action"] == "upload-video"
        assert row["task_id"] == "task-st-1"
        assert row["phase"] == "cli"
        assert row["level"] == "error"
        # newest-first ordering
        assert rows[0]["id"] > 0

    def test_truncates_oversized_traceback(self) -> None:
        import web_runner as wr

        def recurse(n: int) -> None:
            if n == 0:
                raise RuntimeError("bottom")
            recurse(n - 1)

        try:
            recurse(80)
        except RuntimeError as exc:
            wr._log_error_event(phase="cli", exc=exc)

        rows = wr._db_get_error_events()
        assert len(rows) == 1
        tb = rows[0]["traceback"]
        assert "[truncated]" in tb, "oversized traceback should carry a tail-cap marker"
        assert len(tb) <= 8100, f"traceback tail-cap broke (got {len(tb)})"

    def test_non_zero_exit_writes_synthetic_exc(self) -> None:
        import web_runner as wr

        wr._log_error_event(
            phase="cli",
            task_id="task-st-2",
            platform="bilibili",
            account="bilibili-alice",
            action="login",
            exc_type="NonZeroExit",
            exc_message="cookie expired after 30d",
            status_code=2,
            argv=["bilibili", "check", "--account", "bilibili-alice"],
        )

        rows = wr._db_get_error_events(account="bilibili-alice")
        assert len(rows) == 1
        row = rows[0]
        assert row["exc_type"] == "NonZeroExit"
        assert row["status_code"] == 2
        assert row["exc_message"].startswith("exit code 2 ")
        assert "cookie expired" in row["exc_message"]
        assert row["platform"] == "bilibili"
        # argv stored as JSON list
        assert row["argv"] is not None
        decoded_argv = json.loads(row["argv"])
        assert decoded_argv == ["bilibili", "check", "--account", "bilibili-alice"]
        assert row["traceback"] == "", "NonZeroExit (no live exc) must not invent traceback"

    def test_argv_captured_and_roundtrips(self) -> None:
        import web_runner as wr

        argv = ["douyin", "upload-video", "--account", "u", "--title", "hi"]
        wr._log_error_event(
            phase="cli", exc_type="NonZeroExit", exc_message="boom",
            status_code=1, argv=argv,
        )
        row = wr._db_get_error_events()[0]
        assert json.loads(row["argv"]) == argv

    def test_filter_by_account_returns_only_rows(self) -> None:
        import web_runner as wr

        for acct in ("alice", "bob", "carol"):
            try:
                raise RuntimeError(f"fail-{acct}")
            except RuntimeError as exc:
                wr._log_error_event(phase="cli", account=acct, exc=exc)

        alice_rows = wr._db_get_error_events(account="alice")
        assert len(alice_rows) == 1
        assert alice_rows[0]["account"] == "alice"
        assert "fail-alice" in alice_rows[0]["exc_message"]

    def test_filter_combination(self) -> None:
        import web_runner as wr

        wr._log_error_event(
            phase="cli", platform="douyin", account="x", action="login",
            exc_type="NonZeroExit", exc_message="", status_code=1,
        )
        wr._log_error_event(
            phase="cli", platform="douyin", account="x", action="upload-video",
            exc_type="NonZeroExit", exc_message="", status_code=2,
        )
        wr._log_error_event(
            phase="cli", platform="douyin", account="y", action="upload-video",
            exc_type="NonZeroExit", exc_message="", status_code=2,
        )

        all_x_login = wr._db_get_error_events(platform="douyin", account="x", action="login")
        assert len(all_x_login) == 1
        all_uploads = wr._db_get_error_events(platform="douyin", action="upload-video")
        assert len(all_uploads) == 2

    def test_after_filter_excludes_old_rows(self) -> None:
        import web_runner as wr

        wr._log_error_event(phase="cli", exc_type="NonZeroExit", exc_message="x", status_code=1)
        far_future = "2099-01-01T00:00:00"
        rows = wr._db_get_error_events(after=far_future)
        assert rows == []


class TestErrorEventsApiRoute:
    def setup_method(self) -> None:
        _purge_error_events()

    def teardown_method(self) -> None:
        _purge_error_events()

    def test_get_endpoint_returns_rows(self, client) -> None:
        import web_runner as wr

        try:
            raise OSError("transient I/O")
        except OSError as exc:
            wr._log_error_event(
                phase="cli", platform="tk", account="acct-tk",
                action="upload-video", exc=exc,
            )

        resp = client.get("/api/error-events?platform=tk")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 1
        entry = data["data"][0]
        assert entry["exc_type"] == "OSError"
        assert entry["platform"] == "tk"

    def test_get_endpoint_filters_by_account_and_exc_type(self, client) -> None:
        import web_runner as wr

        wr._log_error_event(
            phase="cli", platform="douyin", account="alice-account",
            exc_type="NonZeroExit", exc_message="x", status_code=2,
        )
        wr._log_error_event(
            phase="cli", platform="douyin", account="bob-account",
            exc_type="RuntimeError", exc_message="different",
        )

        resp_alice = client.get("/api/error-events?account=alice-account")
        rows = resp_alice.get_json()["data"]
        assert len(rows) == 1
        assert rows[0]["exc_type"] == "NonZeroExit"

        resp_runtime = client.get("/api/error-events?exc_type=RuntimeError")
        rows = resp_runtime.get_json()["data"]
        assert len(rows) == 1
        assert rows[0]["account"] == "bob-account"

    def test_get_endpoint_limit_offset(self, client) -> None:
        import web_runner as wr

        for i in range(5):
            wr._log_error_event(
                phase="cli", account=f"acct-{i}",
                exc_type="NonZeroExit", exc_message=str(i), status_code=1,
            )

        resp = client.get("/api/error-events?limit=2&offset=1")
        rows = resp.get_json()["data"]
        assert len(rows) == 2

    def test_empty_filter_returns_empty_list(self, client) -> None:
        resp = client.get("/api/error-events?platform=does-not-exist")
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"] == []
