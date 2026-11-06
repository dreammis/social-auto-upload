"""Offline submission regressions; no browser or platform connection."""
import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uploader.tencent_uploader.main import TencentVideo

class SubmissionReceiptTests(unittest.TestCase):
    def objects(self):
        uploader = TencentVideo('test', 'unused.mp4', [], 0, 'unused.json')
        uploader._dismiss_switch_account_dialog = AsyncMock()
        button = MagicMock()
        button.count = AsyncMock(return_value=1)
        button.is_visible = AsyncMock(return_value=True)
        button.is_enabled = AsyncMock(return_value=True)
        button.click = AsyncMock()
        page = MagicMock()
        page.url = 'https://channels.weixin.qq.com/platform/post/create'
        page.get_by_role.return_value.first = button
        return uploader, page, button

    def test_disappearing_button_does_not_prove_publication(self):
        u, p, b = self.objects()
        async def clicked(**kwargs):
            b.count.return_value = 0
        b.click.side_effect = clicked
        with patch('uploader.tencent_uploader.main.asyncio.sleep', AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, '结果未知'):
                asyncio.run(u.submit_publish(p))
        b.click.assert_awaited_once()

    def test_disabled_button_is_not_forced(self):
        u, p, b = self.objects()
        b.is_enabled.return_value = False
        with patch('uploader.tencent_uploader.main.asyncio.sleep', AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, '不强制点击'):
                asyncio.run(u.submit_publish(p))
        b.click.assert_not_awaited()

    def test_click_failure_does_not_retry(self):
        u, p, b = self.objects()
        b.click.side_effect = TimeoutError('click timeout')
        with self.assertRaisesRegex(RuntimeError, '结果不明'):
            asyncio.run(u.submit_publish(p))
        b.click.assert_awaited_once()

    def test_list_navigation_is_submission_only(self):
        u, p, b = self.objects()
        async def clicked(**kwargs):
            p.url = 'https://channels.weixin.qq.com/platform/post/list'
        b.click.side_effect = clicked
        with patch('uploader.tencent_uploader.main.asyncio.sleep', AsyncMock()):
            asyncio.run(u.submit_publish(p))
        b.click.assert_awaited_once()

    def test_batch_receipt_never_marks_published(self):
        path = Path(__file__).resolve().parents[2]/'Scripts/publish_tencent_batch_today.py'
        spec = importlib.util.spec_from_file_location('batch', path)
        batch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(batch)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p/'STATUS.md').write_text('# 项目\n\n`待发布`\n')
            batch.mark_submitted(p, '')
            text = (p/'STATUS.md').read_text()
            self.assertIn('已提交待核验', text)
            self.assertNotIn('`已发布`', text)
            self.assertIn('不据此认定已发布', text)

if __name__ == '__main__':
    unittest.main()
