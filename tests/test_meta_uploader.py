import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from patchright.async_api import async_playwright

import sau_cli
from uploader.meta_uploader.facebook_page_uploader.main import MetaBusinessUploader, _is_business_logged_out


class MetaBusinessValidationTests(unittest.TestCase):
    def test_caption_contains_title_description_and_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.mp4"
            path.write_bytes(b"placeholder")
            uploader = MetaBusinessUploader(
                "facebook-page",
                Path(directory) / "account.json",
                title="标题",
                description="正文",
                tags=["#一个", "两个"],
                video_file=path,
            )
        self.assertEqual(uploader._caption(), "标题\n\n正文\n\n#一个 #两个")

    def test_schedule_requires_future_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.mp4"
            path.write_bytes(b"placeholder")
            with self.assertRaises(ValueError):
                MetaBusinessUploader(
                    "facebook-page",
                    Path(directory) / "account.json",
                    title="标题",
                    video_file=path,
                    schedule=datetime.now() + timedelta(minutes=5),
                )

    def test_business_suite_nav_is_positive_login_evidence(self):
        async def scenario():
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True, channel="chrome")
                page = await browser.new_page()
                await page.set_content('<nav><a href="/latest/home">Meta Business Suite</a></nav>')
                result = await _is_business_logged_out(page)
                await browser.close()
                return result

        self.assertFalse(asyncio.run(scenario()))

    def test_meta_cli_exposes_schedule_and_images(self):
        args = sau_cli.build_parser().parse_args(
            [
                "facebook-page",
                "upload-note",
                "--account",
                "creator",
                "--images",
                __file__,
                "--title",
                "标题",
                "--schedule",
                "2026-10-21 10:30",
            ]
        )
        self.assertEqual(args.platform, "facebook-page")
        self.assertEqual(args.images, [Path(__file__)])
        self.assertEqual(args.schedule.year, 2026)


if __name__ == "__main__":
    unittest.main()
