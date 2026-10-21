import sau_commands.facebook
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import sau_cli
from patchright.async_api import async_playwright

from uploader.meta_uploader.facebook_uploader.main import FacebookVideo, _is_logged_out, facebook_cookie_auth


class FacebookCaptionTests(unittest.TestCase):
    def test_caption_merges_title_description_and_tags(self):
        uploader = FacebookVideo(
            title="标题",
            file_path="video.mp4",
            description="正文",
            tags=["#一个", " 两个 "],
            account_file="account.json",
        )

        self.assertEqual(uploader._caption(), "标题\n\n正文\n\n#一个 #两个")

    def test_caption_omits_empty_optional_fields(self):
        uploader = FacebookVideo(
            title="标题",
            file_path="video.mp4",
            description="",
            tags=[],
            account_file="account.json",
        )

        self.assertEqual(uploader._caption(), "标题")


class FacebookPageStateTests(unittest.TestCase):
    def test_logged_out_marker_is_based_on_login_form(self):
        async def scenario():
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True, channel="chrome")
                page = await browser.new_page()
                await page.set_content('<h1>登录 Facebook</h1><input name="email">')
                result = await _is_logged_out(page)
                await browser.close()
                return result

        self.assertTrue(asyncio.run(scenario()))

    def test_logged_in_page_without_login_form_is_not_marked_out(self):
        async def scenario():
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True, channel="chrome")
                page = await browser.new_page()
                await page.set_content(
                    '<main><input type="file" accept="image/*,video/*" hidden></main>'
                )
                result = await _is_logged_out(page)
                await browser.close()
                return result

        self.assertFalse(asyncio.run(scenario()))

    def test_two_step_verification_is_not_treated_as_logged_in(self):
        async def scenario():
            class PageStub:
                url = "https://www.facebook.com/two_step_verification/authentication/"

            return await _is_logged_out(PageStub())

        self.assertTrue(asyncio.run(scenario()))

    def test_blank_facebook_page_is_not_treated_as_logged_in(self):
        async def scenario():
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True, channel="chrome")
                page = await browser.new_page()
                await page.set_content("<body></body>")
                result = await _is_logged_out(page)
                await browser.close()
                return result

        self.assertTrue(asyncio.run(scenario()))


class FacebookCliTests(unittest.TestCase):
    def test_parser_exposes_proxy_and_headed_login(self):
        args = sau_cli.build_parser().parse_args(
            ["facebook", "login", "--account", "creator", "--proxy", "http://proxy.example:8080"]
        )
        self.assertEqual(args.proxy, "http://proxy.example:8080")
        self.assertFalse(args.headless)

    def test_dispatch_upload_forwards_facebook_request(self):
        args = sau_cli.build_parser().parse_args(
            [
                "facebook",
                "upload-video",
                "--account",
                "creator",
                "--file",
                __file__,
                "--title",
                "标题",
                "--desc",
                "正文",
                "--tags",
                "一个,两个",
                "--proxy",
                "http://proxy.example:8080",
            ]
        )
        with patch("sau_commands.facebook.upload_facebook_video", new=AsyncMock()) as mock_upload:
            result = asyncio.run(sau_cli.dispatch(args))

        self.assertEqual(result, 0)
        request = mock_upload.await_args.args[0]
        self.assertEqual(request.title, "标题")
        self.assertEqual(request.description, "正文")
        self.assertEqual(request.tags, ["一个", "两个"])
        self.assertEqual(request.proxy, "http://proxy.example:8080")


class FacebookStorageStateTests(unittest.TestCase):
    def test_missing_storage_state_is_invalid_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(
                facebook_cookie_auth(Path(directory) / "missing.json", proxy="")
            )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
