"""知乎的原稿完整性与命令契约；本地页面不冒充知乎实际上传验收。"""
import asyncio
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from patchright.async_api import async_playwright

from conf import LOCAL_CHROME_PATH
from sau_cli import build_parser
from uploader.zhihu_uploader.article import ZhihuArticle
from uploader.zhihu_uploader.video import ZhihuVideo
from utils.article_render import load_article


class ZhihuCLITests(unittest.TestCase):
    def test_video_at_or_below_100kb_is_rejected_before_browser_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "video.mp4"
            for size in (84693, 102400):
                with self.subTest(size=size):
                    video.write_bytes(b"\0" * size)
                    app = ZhihuVideo("视频标题示例", video, "account.json", "", None, [], None, "original")
                    with self.assertRaisesRegex(ValueError, "必须大于 100KB"):
                        app.validate_upload_args()

    def test_video_can_preview_runtime_choices_without_guessing_category(self):
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "video.mp4"
            video.touch()
            args = build_parser().parse_args([
                "zhihu", "upload-video", "--account", "creator", "--file", str(video),
                "--title", "视频标题示例", "--originality", "original", "--show-options",
            ])
        self.assertTrue(args.show_options)
        self.assertIsNone(args.category)
        self.assertFalse(hasattr(args, "topics"))
        self.assertFalse(hasattr(args, "category_second"))

    def test_unknown_menu_value_returns_all_legal_choices(self):
        app = ZhihuVideo("标题", "video.mp4", "account.json", "", None, [], None, "original")
        with self.assertRaisesRegex(ValueError, "科学、生活"):
            asyncio.run(app.select_option("所属领域", "不存在", ["科学", "生活"]))

    def test_cli_rejects_unknown_category_and_video_mark(self):
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "video.mp4"
            video.touch()
            command = ["zhihu", "upload-video", "--account", "creator", "--file", str(video),
                       "--title", "视频标题示例", "--originality", "original"]
            parser = build_parser()
            args = parser.parse_args(command + ["--category", "教育", "--video-mark", "含 AI 生成内容"])
            self.assertEqual(args.category, "教育")
            for flag in ("--category", "--video-mark"):
                with self.subTest(flag=flag), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        parser.parse_args(command + [flag, "不存在"])
                    self.assertEqual(error.exception.code, 2)

    def test_interactive_menu_accepts_index_and_shows_all_choices(self):
        app = ZhihuVideo("标题", "video.mp4", "account.json", "", None, [], None, "original")
        output = io.StringIO()
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="2"), contextlib.redirect_stderr(output):
            value = asyncio.run(app.select_option("所属领域", None, ["科学", "生活"]))
        self.assertEqual(value, "生活")
        self.assertIn("1. 科学", output.getvalue())
        self.assertIn("2. 生活", output.getvalue())


class ZhihuArticleContentTests(unittest.IsolatedAsyncioTestCase):
    async def test_original_order_is_required_and_format_loss_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "one.png").write_bytes(b"local resource")
            source = root / "article.html"
            source.write_text('<h2>标题</h2><p>第一段<strong>重点</strong></p>'
                              '<img src="one.png"><p>第二段<a href="https://example.com/">链接</a></p>', encoding="utf-8")
            app = ZhihuArticle("文章", source, root / "account.json")
            app.document = load_article(source)
            original = app.document.content_html
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=True)
                try:
                    page = await browser.new_page()
                    await page.set_content(original)
                    await app.check_article_body(page.locator("body"))
                    # 真实知乎 DraftJS 使用 styled span，并在链接文字前插入零宽字符。
                    await page.set_content(original.replace('<strong>', '<span style="font-weight: bold">')
                                           .replace('</strong>', '</span>')
                                           .replace('>链接</a>', '>\u200b链接</a>'))
                    await app.check_article_body(page.locator("body"))
                    # 图片数量相同，但移到文末必须失败，防止再次退回统一追加图片。
                    await page.set_content('<h2>标题</h2><p>第一段<strong>重点</strong></p>'
                                           '<p>第二段<a href="https://example.com/">链接</a></p><img src="one.png">')
                    with self.assertRaisesRegex(RuntimeError, "图片位置"):
                        await app.check_article_body(page.locator("body"))
                    await page.set_content(original.replace("<strong>", "<span>").replace("</strong>", "</span>"))
                    with self.assertRaisesRegex(RuntimeError, "格式不一致"):
                        await app.check_article_body(page.locator("body"))
                    await page.set_content(original.replace("https://example.com/", "https://example.org/"))
                    with self.assertRaisesRegex(RuntimeError, "链接"):
                        await app.check_article_body(page.locator("body"))
                finally:
                    await browser.close()
