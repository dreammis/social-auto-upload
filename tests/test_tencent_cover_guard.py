"""Offline regressions: no browser, credentials, or platform requests."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import cv2
import numpy as np

from uploader.tencent_uploader.main import TencentVideo
from utils.cover_verification import verify_cover_preview


class CoverGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'cover.png'
        self.source = np.full((480, 360, 3), (30, 20, 10), dtype=np.uint8)
        cv2.rectangle(self.source, (30, 180), (330, 260), (200, 220, 240), -1)
        cv2.putText(self.source, 'TITLE', (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (30, 40, 60), 4)
        self.path.write_bytes(cv2.imencode('.png', self.source)[1].tobytes())

    def verify(self, image):
        return verify_cover_preview(str(self.path), cv2.imencode('.jpg', image)[1].tobytes())

    def test_scaled_compressed_cover_passes(self):
        self.verify(cv2.resize(self.source, (180, 240), interpolation=cv2.INTER_AREA))

    def test_missing_title_fails(self):
        with self.assertRaises(ValueError):
            self.verify(np.full_like(self.source, (30, 20, 10)))

    def test_wrong_crop_fails(self):
        with self.assertRaises(ValueError):
            self.verify(cv2.resize(self.source[120:360, 90:270], (360, 480)))

    def test_wrong_aspect_ratio_fails(self):
        with self.assertRaises(ValueError):
            self.verify(cv2.resize(self.source, (360, 360)))

    def test_dialog_failure_prevents_preview_acceptance(self):
        uploader = TencentVideo('test', 'unused.mp4', [], 0, 'unused.json')
        uploader.open_thumbnail_dialog = AsyncMock(return_value=object())
        uploader.upload_thumbnail_in_dialog = AsyncMock(side_effect=RuntimeError('dialog still open'))
        uploader.verify_thumbnail_preview = AsyncMock()
        page = MagicMock()
        page.locator.return_value.first.count = AsyncMock(return_value=0)
        with self.assertRaises(RuntimeError):
            asyncio.run(uploader.set_single_thumbnail(page, str(self.path), [], [], '3:4 竖版'))
        uploader.verify_thumbnail_preview.assert_not_awaited()

    def test_unclosed_cover_dialog_prevents_preview_acceptance(self):
        uploader = TencentVideo('test', 'unused.mp4', [], 0, 'unused.json')
        uploader.open_thumbnail_dialog = AsyncMock(return_value=object())
        uploader.upload_thumbnail_in_dialog = AsyncMock(return_value=False)
        uploader.verify_thumbnail_preview = AsyncMock()
        page = MagicMock()
        page.locator.return_value.first.count = AsyncMock(return_value=0)
        with self.assertRaisesRegex(RuntimeError, '未关闭'):
            asyncio.run(uploader.set_single_thumbnail(page, str(self.path), [], [], '3:4 竖版'))
        uploader.verify_thumbnail_preview.assert_not_awaited()

    def test_upload_cannot_submit_after_failed_cover_check(self):
        from unittest.mock import patch
        uploader = TencentVideo('test', 'unused.mp4', [], 0, 'unused.json')
        context = AsyncMock()
        for method in ('validate_upload_args', 'open_upload_page', 'upload_video_file',
                       'prepare_video_for_publish', 'wait_for_upload_complete', 'apply_collection',
                       'apply_original_statement', 'set_short_title', 'submit_publish'):
            setattr(uploader, method, AsyncMock())
        uploader.set_thumbnail = AsyncMock(side_effect=RuntimeError('wrong cover'))
        with patch('uploader.tencent_uploader.main.launch_tencent_context', AsyncMock(return_value=context)):
            with self.assertRaises(RuntimeError):
                asyncio.run(uploader.upload(None))
        uploader.submit_publish.assert_not_awaited()
        context.close.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
