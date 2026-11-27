import unittest
from unittest.mock import AsyncMock, Mock

from uploader.tencent_uploader.main import TencentBaseUploader


class TencentShortTitleTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_short_title_does_not_access_page(self):
        uploader = TencentBaseUploader(publish_date=0, account_file="unused")
        for kwargs in ({}, {"short_title": None}, {"short_title": ""}):
            with self.subTest(kwargs=kwargs):
                page = Mock()
                page.locator.side_effect = AssertionError("Short title must be skipped")
                await uploader.set_short_title(page, "催我", **kwargs)
                self.assertEqual(page.mock_calls, [])

    async def test_explicit_short_title_keeps_existing_fill_behavior(self):
        uploader = TencentBaseUploader(publish_date=0, account_file="unused")
        field = Mock()
        field.count = AsyncMock(return_value=1)
        field.fill = AsyncMock()
        page = Mock()
        page.locator.return_value.first = field

        await uploader.set_short_title(page, "不应采用的主标题", "明确")

        page.locator.assert_called_once_with(
            'input[placeholder="填写短标题有机会获得更多流量"]'
        )
        field.fill.assert_awaited_once_with("明确，精彩内容")
        page.get_by_text.assert_not_called()
