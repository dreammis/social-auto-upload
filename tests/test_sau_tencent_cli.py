import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import sau_cli


class FakeTencentVideo:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def tencent_upload_video(self):
        return None


class TencentCliTests(unittest.TestCase):
    def test_build_parser_accepts_tencent_login_headed(self):
        parser = sau_cli.build_parser()
        args = parser.parse_args(["tencent", "login", "--account", "diyi", "--headed"])
        self.assertEqual(args.platform, "tencent")
        self.assertEqual(args.action, "login")
        self.assertFalse(args.headless)

    def test_upload_tencent_video_checks_cookie_with_request_headless_flag(self):
        request = sau_cli.TencentVideoUploadRequest(
            account_name="diyi",
            video_file=Path("demo.mp4"),
            title="demo",
            description="desc",
            tags=[],
            publish_date=0,
            headless=False,
        )

        with patch("sau_cli.tencent_setup", new=AsyncMock(return_value=True)) as mock_setup:
            with patch("sau_cli.TencentVideo", FakeTencentVideo):
                asyncio.run(sau_cli.upload_tencent_video(request))

        mock_setup.assert_awaited_once()
        awaited = mock_setup.await_args
        self.assertIsNotNone(awaited)
        self.assertFalse(awaited.kwargs["headless"])


if __name__ == "__main__":
    unittest.main()
