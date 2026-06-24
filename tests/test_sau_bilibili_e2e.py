from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dummy_video(tmp_path: Path) -> Path:
    """Create a minimal dummy video file (just a few KB of zeros)."""
    path = tmp_path / "test_video.mp4"
    path.write_bytes(b"\x00" * 2048)
    return path


def _dummy_cookie(cookies_dir: Path, account: str) -> str:
    """Create a dummy bilibili cookie file and return its path."""
    cookie_path = cookies_dir / f"bilibili_{account}.json"
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    cookie_path.write_text(json.dumps([
        {"name": "SESSDATA", "value": "mock-sessdata", "domain": ".bilibili.com", "path": "/", "expires": -1},
        {"name": "bili_jct", "value": "mock-csrf", "domain": ".bilibili.com", "path": "/", "expires": -1},
    ]))
    return str(cookie_path)


# ---------------------------------------------------------------------------
# E2E smoketest: argv → dispatch → run_biliup_command
# ---------------------------------------------------------------------------


class TestBilibiliE2ESmoke:
    """Verify the full chain: web-built argv → sau_main → upload_bilibili_video → run_biliup_command."""

    def test_upload_bilibili_video_e2e_basic(self):
        """Basic upload with all required fields — verify biliup args."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            cookies_dir = tmp / "cookies"
            cookies_dir.mkdir()
            video_path = _dummy_video(tmp)

            # Resolve account file into our temp dir
            def _mock_resolve_account(platform: str, account_name: str) -> Path:
                return cookies_dir / f"{platform}_{account_name}.json"

            # Create the cookie file
            _dummy_cookie(cookies_dir, "testup")

            # Mock the biliup command to capture arguments
            mock_run = MagicMock(return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="upload ok\n", stderr="",
            ))

            from sau_cli import main as sau_main

            with (
                patch("cli.platforms.bilibili.resolve_account_file", side_effect=_mock_resolve_account),
                patch("cli.platforms.bilibili.bilibili_cookie_auth", new=AsyncMock(return_value=True)),
                patch("cli.platforms.bilibili.run_biliup_command", mock_run),
            ):
                rc = sau_main([
                    "bilibili",
                    "upload-video",
                    "--account", "testup",
                    "--file", str(video_path),
                    "--title", "测试B站视频",
                    "--desc", "这是视频描述",
                    "--tid", "171",
                    "--tags", "教程,Python",
                ])

            assert rc == 0, f"expected exit 0, got {rc}"
            mock_run.assert_called_once()
            biliup_args: list[str] = mock_run.call_args[0][0]

            # Verify biliup invocation structure
            assert "-u" in biliup_args
            u_idx = biliup_args.index("-u")
            cookie_path = biliup_args[u_idx + 1]
            assert "bilibili_testup.json" in cookie_path
            assert "upload" in biliup_args
            assert str(video_path) in biliup_args
            assert "--title" in biliup_args
            title_idx = biliup_args.index("--title")
            assert biliup_args[title_idx + 1] == "测试B站视频"
            assert "--desc" in biliup_args
            desc_idx = biliup_args.index("--desc")
            assert biliup_args[desc_idx + 1] == "这是视频描述"
            assert "--tid" in biliup_args
            tid_idx = biliup_args.index("--tid")
            assert biliup_args[tid_idx + 1] == "171"
            assert "--tag" in biliup_args
            tag_idx = biliup_args.index("--tag")
            assert biliup_args[tag_idx + 1] == "教程,Python"

    def test_upload_bilibili_video_default_tid_233(self):
        """When no explicit tid, CLI defaults to the one from web (233)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            cookies_dir = tmp / "cookies"
            cookies_dir.mkdir()
            video_path = _dummy_video(tmp)

            def _mock_resolve_account(platform: str, account_name: str) -> Path:
                return cookies_dir / f"{platform}_{account_name}.json"

            _dummy_cookie(cookies_dir, "testup")
            mock_run = MagicMock(return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr="",
            ))

            from sau_cli import main as sau_main

            with (
                patch("cli.platforms.bilibili.resolve_account_file", side_effect=_mock_resolve_account),
                patch("cli.platforms.bilibili.bilibili_cookie_auth", new=AsyncMock(return_value=True)),
                patch("cli.platforms.bilibili.run_biliup_command", mock_run),
            ):
                rc = sau_main([
                    "bilibili",
                    "upload-video",
                    "--account", "testup",
                    "--file", str(video_path),
                    "--title", "默认TID",
                    "--desc", "desc",
                    "--tid", "233",
                    "--tags", "",
                ])

            assert rc == 0
            biliup_args: list[str] = mock_run.call_args[0][0]
            tid_idx = biliup_args.index("--tid")
            assert biliup_args[tid_idx + 1] == "233"

    def test_upload_bilibili_video_with_schedule(self):
        """Scheduled upload should include --dtime in biliup args."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            cookies_dir = tmp / "cookies"
            cookies_dir.mkdir()
            video_path = _dummy_video(tmp)

            def _mock_resolve_account(platform: str, account_name: str) -> Path:
                return cookies_dir / f"{platform}_{account_name}.json"

            _dummy_cookie(cookies_dir, "testup")
            mock_run = MagicMock(return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr="",
            ))

            from sau_cli import main as sau_main

            with (
                patch("cli.platforms.bilibili.resolve_account_file", side_effect=_mock_resolve_account),
                patch("cli.platforms.bilibili.bilibili_cookie_auth", new=AsyncMock(return_value=True)),
                patch("cli.platforms.bilibili.run_biliup_command", mock_run),
            ):
                rc = sau_main([
                    "bilibili",
                    "upload-video",
                    "--account", "testup",
                    "--file", str(video_path),
                    "--title", "定时发布",
                    "--desc", "desc",
                    "--tid", "17",
                    "--schedule", "2099-12-31 23:59",
                ])

            assert rc == 0
            biliup_args: list[str] = mock_run.call_args[0][0]
            assert "--dtime" in biliup_args
            dtime_idx = biliup_args.index("--dtime")
            # Verify it's a reasonable timestamp (year 2099)
            dtime_val = int(biliup_args[dtime_idx + 1])
            from datetime import datetime
            dt = datetime.fromtimestamp(dtime_val)
            assert dt.year == 2099
            assert dt.month == 12
            assert dt.day == 31

    def test_upload_bilibili_video_no_tags(self):
        """Upload with empty tags should NOT include --tag in biliup args."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            cookies_dir = tmp / "cookies"
            cookies_dir.mkdir()
            video_path = _dummy_video(tmp)

            def _mock_resolve_account(platform: str, account_name: str) -> Path:
                return cookies_dir / f"{platform}_{account_name}.json"

            _dummy_cookie(cookies_dir, "testup")
            mock_run = MagicMock(return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr="",
            ))

            from sau_cli import main as sau_main

            with (
                patch("cli.platforms.bilibili.resolve_account_file", side_effect=_mock_resolve_account),
                patch("cli.platforms.bilibili.bilibili_cookie_auth", new=AsyncMock(return_value=True)),
                patch("cli.platforms.bilibili.run_biliup_command", mock_run),
            ):
                rc = sau_main([
                    "bilibili",
                    "upload-video",
                    "--account", "testup",
                    "--file", str(video_path),
                    "--title", "无标签",
                    "--desc", "no tags",
                    "--tid", "233",
                    "--tags", "",
                ])

            assert rc == 0
            biliup_args: list[str] = mock_run.call_args[0][0]
            assert "--tag" not in biliup_args

    def test_missing_cookie_file_raises_error(self):
        """Upload without an existing cookie file should raise RuntimeError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            cookies_dir = tmp / "cookies"
            cookies_dir.mkdir()
            video_path = _dummy_video(tmp)

            def _mock_resolve_account(platform: str, account_name: str) -> Path:
                return cookies_dir / f"{platform}_{account_name}.json"

            # Do NOT create cookie file

            from sau_cli import main as sau_main

            with (
                patch("cli.platforms.bilibili.resolve_account_file", side_effect=_mock_resolve_account),
                patch("cli.platforms.bilibili.bilibili_cookie_auth", new=AsyncMock(return_value=True)),
                patch("cli.platforms.bilibili.run_biliup_command") as mock_run,
            ):
                rc = sau_main([
                    "bilibili",
                    "upload-video",
                    "--account", "nonexistent",
                    "--file", str(video_path),
                    "--title", "test",
                    "--desc", "test",
                    "--tid", "233",
                ])

            # Should fail with non-zero exit code
            assert rc != 0
            # run_biliup_command should NOT be called
            mock_run.assert_not_called()

    def test_biliup_failure_raises_error(self):
        """When biliup returns non-zero, the function should raise."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            cookies_dir = tmp / "cookies"
            cookies_dir.mkdir()
            video_path = _dummy_video(tmp)

            def _mock_resolve_account(platform: str, account_name: str) -> Path:
                return cookies_dir / f"{platform}_{account_name}.json"

            _dummy_cookie(cookies_dir, "testup")
            mock_run = MagicMock(return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="upload failed: network error",
            ))

            from sau_cli import main as sau_main

            with (
                patch("cli.platforms.bilibili.resolve_account_file", side_effect=_mock_resolve_account),
                patch("cli.platforms.bilibili.bilibili_cookie_auth", new=AsyncMock(return_value=True)),
                patch("cli.platforms.bilibili.run_biliup_command", mock_run),
            ):
                rc = sau_main([
                    "bilibili",
                    "upload-video",
                    "--account", "testup",
                    "--file", str(video_path),
                    "--title", "test",
                    "--desc", "test",
                    "--tid", "171",
                ])

            assert rc != 0  # upload should fail
            mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# Web → CLI integration: verify the full argv passthrough
# ---------------------------------------------------------------------------


class TestBilibiliWebToCliIntegration:
    """Verify argv built by the web endpoint passes through sau_main into biliup correctly."""

    def test_web_argv_flows_to_biliup(self):
        """Build argv exactly as web_runner does, then call sau_main and verify biliup args."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            cookies_dir = tmp / "cookies"
            cookies_dir.mkdir()
            video_path = _dummy_video(tmp)

            def _mock_resolve_account(platform: str, account_name: str) -> Path:
                return cookies_dir / f"{platform}_{account_name}.json"

            _dummy_cookie(cookies_dir, "webuser")
            mock_run = MagicMock(return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr="",
            ))

            # Simulate the argv that web_runner's upload_video builds for bilibili
            argv = [
                "bilibili",
                "upload-video",
                "--account", "webuser",
                "--title", "Web上传的视频",
                "--tags", "技术,前端",
                "--desc", "通过Web端上传",  # always passed for bilibili
                "--file", str(video_path),
                "--tid", "217",  # 217 = 动物圈
            ]
            # Note: --headless is NOT in argv (web skips it for bilibili)

            from sau_cli import main as sau_main

            with (
                patch("cli.platforms.bilibili.resolve_account_file", side_effect=_mock_resolve_account),
                patch("cli.platforms.bilibili.bilibili_cookie_auth", new=AsyncMock(return_value=True)),
                patch("cli.platforms.bilibili.run_biliup_command", mock_run),
            ):
                rc = sau_main(argv)

            assert rc == 0
            biliup_args: list[str] = mock_run.call_args[0][0]

            # Verify the biliup arguments match what upload_bilibili_video constructs
            assert "-u" in biliup_args
            u_idx = biliup_args.index("-u")
            assert "bilibili_webuser.json" in biliup_args[u_idx + 1]

            assert "upload" in biliup_args
            assert str(video_path) in biliup_args
            assert biliup_args[biliup_args.index("--title") + 1] == "Web上传的视频"
            assert biliup_args[biliup_args.index("--desc") + 1] == "通过Web端上传"
            assert biliup_args[biliup_args.index("--tid") + 1] == "217"
            assert biliup_args[biliup_args.index("--tag") + 1] == "技术,前端"
