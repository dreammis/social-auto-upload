"""Offline Channels regression: rejected releases never touch accounts/browser."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import sau_cli
from uploader.tencent_uploader import main as tencent


class ChannelsApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_rejects_before_account_lookup(self):
        request = SimpleNamespace(account_name='dagaju', video_file=Path('/tmp/unapproved.mp4'))
        with patch.object(sau_cli, 'resolve_account_file') as account, self.assertRaisesRegex(RuntimeError, 'BLOCKED_APPROVAL_GATE'):
            await sau_cli.upload_tencent_video(request)
        account.assert_not_called()

    async def test_legacy_upload_rejects_before_validation_or_browser(self):
        video = tencent.TencentVideo('候选', '/tmp/unapproved.mp4', [], 0, '/tmp/tencent_dagaju.json')
        with patch.object(video, 'validate_upload_args', AsyncMock()) as validate, patch.object(tencent, 'launch_tencent_context', AsyncMock()) as launch, self.assertRaisesRegex(RuntimeError, 'BLOCKED_APPROVAL_GATE'):
            await video.upload(object())
        validate.assert_not_awaited()
        launch.assert_not_awaited()

    async def test_main_rejects_before_playwright(self):
        video = tencent.TencentVideo('候选', '/tmp/unapproved.mp4', [], 0, '/tmp/tencent_dagaju.json')
        with patch.object(tencent, 'async_playwright') as driver, self.assertRaisesRegex(RuntimeError, 'BLOCKED_APPROVAL_GATE'):
            await video.main()
        driver.assert_not_called()


if __name__ == '__main__':
    unittest.main()
