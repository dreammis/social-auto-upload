import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from uploader.douyin_uploader.main import DouYinBaseUploader


class SmsNoticeTests(unittest.TestCase):
    def page(self, count=1, visible=True):
        page = MagicMock()
        control = page.locator.return_value.first
        control.count = AsyncMock(return_value=count)
        control.is_visible = AsyncMock(return_value=visible)
        control.fill = AsyncMock()
        control.click = AsyncMock()
        return page, control

    def test_sms_only_reports_without_input_or_clicks(self):
        page, control = self.page()
        uploader = DouYinBaseUploader(0, 'unused.json')
        with patch('builtins.input') as prompt:
            with self.assertRaisesRegex(RuntimeError, '已停止本次发布.*人工处理'):
                asyncio.run(uploader.handle_sms_verification(page))
            prompt.assert_not_called()
        control.fill.assert_not_awaited()
        control.click.assert_not_awaited()
        page.get_by_text.assert_not_called()
        page.keyboard.press.assert_not_called()

    def test_absent_or_hidden_sms_does_not_interrupt(self):
        uploader = DouYinBaseUploader(0, 'unused.json')
        for count, visible in [(0, False), (1, False)]:
            with self.subTest(count=count, visible=visible):
                page, _ = self.page(count, visible)
                self.assertFalse(asyncio.run(uploader.handle_sms_verification(page)))
