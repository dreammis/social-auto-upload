import asyncio
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import ANY, AsyncMock, Mock, patch

import sau_cli


class BilibiliCliTests(unittest.TestCase):
    def test_build_parser_accepts_bilibili_login(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["bilibili", "login", "--account", "creator"])
        self.assertEqual(args.platform, "bilibili")
        self.assertEqual(args.action, "login")

    def test_build_parser_requires_tid_for_upload_video(self):
        parser = sau_cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "bilibili",
                    "upload-video",
                    "--account",
                    "creator",
                    "--file",
                    "demo.mp4",
                    "--title",
                    "hello",
                    "--desc",
                    "hello",
                ]
            )

    def test_dispatch_bilibili_check_prints_valid(self):
        args = Namespace(platform="bilibili", action="check", account="creator")
        with patch("sau_cli.check_bilibili_account", new=AsyncMock(return_value=True)):
            code = asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(code, 0)

    def test_login_bilibili_account_returns_friendly_message_without_terminal(self):
        with patch("sau_cli.has_interactive_terminal", return_value=False):
            result = asyncio.run(sau_cli.login_bilibili_account("creator"))
        self.assertFalse(result["success"])
        self.assertIn("local interactive terminal", result["message"].lower())
        self.assertIn("qrcode.png", result["message"].lower())

    # --- 封面运输回归测试（RED 阶段） ---

    def test_bilibili_upload_video_parser_accepts_thumbnail(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            thumb = Path(tmp_dir) / "thumb.png"
            video = Path(tmp_dir) / "demo.mp4"
            thumb.write_text("fake")
            video.write_text("fake")
            parser = sau_cli.build_parser()
            args = parser.parse_args(
                [
                    "bilibili",
                    "upload-video",
                    "--account",
                    "creator",
                    "--file",
                    str(video),
                    "--title",
                    "hello",
                    "--desc",
                    "hello",
                    "--tid",
                    "232",
                    "--thumbnail",
                    str(thumb),
                ]
            )
        self.assertEqual(args.thumbnail, thumb)

    def test_dispatch_bilibili_upload_passes_thumbnail_to_request(self):
        captured = {}

        async def fake_upload(req):
            captured["thumbnail_file"] = req.thumbnail_file

        with tempfile.TemporaryDirectory() as tmp_dir:
            thumb = Path(tmp_dir) / "thumb.png"
            thumb.write_text("fake")
            video = Path(tmp_dir) / "demo.mp4"
            video.write_text("fake")
            args = Namespace(
                platform="bilibili",
                action="upload-video",
                account="creator",
                file=video,
                title="hello",
                desc="hello",
                tid=232,
                tags="tag1,tag2",
                schedule=0,
                thumbnail=thumb,
            )
            with patch("sau_cli.upload_bilibili_video", new=fake_upload):
                asyncio.run(sau_cli.dispatch(args))
        self.assertEqual(captured.get("thumbnail_file"), thumb)

    def test_upload_bilibili_video_translates_thumbnail_to_cover(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            thumb = Path(tmp_dir) / "thumb.png"
            thumb.write_text("fake")
            video = Path(tmp_dir) / "demo.mp4"
            video.write_text("fake")
            request = sau_cli.BilibiliVideoUploadRequest(
                account_name="creator",
                video_file=video,
                title="hello",
                description="hello",
                tid=232,
                tags=[],
                publish_date=0,
                thumbnail_file=thumb,
            )
            with patch("sau_cli.run_biliup_command") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")
                with patch(
                    "sau_cli.resolve_account_file",
                    return_value=thumb.parent / "account.json",
                ):
                    with patch("pathlib.Path.exists", return_value=True):
                        asyncio.run(sau_cli.upload_bilibili_video(request))
            mock_run.assert_called_once()
            args_list = mock_run.call_args[0][0]
            self.assertIn("--cover", args_list)
            cover_idx = args_list.index("--cover")
            self.assertEqual(args_list[cover_idx + 1], str(thumb))

    def test_upload_bilibili_video_without_thumbnail_omits_cover(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            video = Path(tmp_dir) / "demo.mp4"
            video.write_text("fake")
            request = sau_cli.BilibiliVideoUploadRequest(
                account_name="creator",
                video_file=video,
                title="hello",
                description="hello",
                tid=232,
                tags=[],
                publish_date=0,
            )
            with patch("sau_cli.run_biliup_command") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")
                with patch(
                    "sau_cli.resolve_account_file",
                    return_value=video.parent / "account.json",
                ):
                    with patch("pathlib.Path.exists", return_value=True):
                        asyncio.run(sau_cli.upload_bilibili_video(request))
            mock_run.assert_called_once()
            args_list = mock_run.call_args[0][0]
            self.assertNotIn("--cover", args_list)
