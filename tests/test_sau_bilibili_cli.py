import asyncio
import unittest
from argparse import Namespace
from unittest.mock import AsyncMock, patch

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

    def test_login_bilibili_account_runs_biliup_without_terminal(self):
        with patch("sau_cli.run_biliup_command") as run_command:
            run_command.return_value.returncode = 0
            run_command.return_value.stdout = ""
            run_command.return_value.stderr = ""
            result = asyncio.run(sau_cli.login_bilibili_account("creator"))
        self.assertTrue(result["success"])
        run_command.assert_called_once()
        self.assertIn("Bilibili login completed", result["message"])
