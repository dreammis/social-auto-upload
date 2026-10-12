import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from patchright.async_api import TimeoutError as BrowserTimeoutError
from uploader.douyin_uploader.main import DOUYIN_UPLOAD_URL, DouYinBaseUploader


class UploadPageTests(unittest.TestCase):
    def run_open(self, page):
        uploader = DouYinBaseUploader(publish_date=0, account_file="unused.json")
        asyncio.run(uploader.open_authenticated_upload_page(page))

    def page(self):
        page = MagicMock()
        page.url = DOUYIN_UPLOAD_URL
        page.goto = AsyncMock()
        page.wait_for_url = AsyncMock()
        marker = page.get_by_text.return_value.first
        marker.count = AsyncMock(return_value=0)
        marker.is_visible = AsyncMock(return_value=False)
        return page

    def test_does_not_wait_for_optional_resources(self):
        page = self.page()

        async def wait_for_url(*args, **kwargs):
            if kwargs.get("wait_until", "load") == "load":
                raise BrowserTimeoutError("optional resource never finishes")

        page.wait_for_url.side_effect = wait_for_url
        self.run_open(page)

    def test_visible_login_still_rejected(self):
        page = self.page()
        page.get_by_text.return_value.first.count.return_value = 1
        page.get_by_text.return_value.first.is_visible.return_value = True
        with self.assertRaisesRegex(RuntimeError, "cookie 已失效"):
            self.run_open(page)

    def test_timeout_is_not_reported_as_invalid_cookie(self):
        page = self.page()
        page.wait_for_url.side_effect = BrowserTimeoutError("timeout")
        with self.assertRaisesRegex(RuntimeError, "上传页就绪检查超时"):
            self.run_open(page)

    def test_browser_error_preserves_original_cause(self):
        page = self.page()
        page.wait_for_url.side_effect = ValueError("browser disconnected")
        with self.assertRaisesRegex(ValueError, "browser disconnected"):
            self.run_open(page)
