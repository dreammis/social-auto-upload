# Language: 中文
import asyncio
import inspect
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from uploader.douyin_uploader import main as douyin_main
from uploader.douyin_uploader.main import DouYinVideo


class DouyinDeclarationTests(unittest.TestCase):
    def test_title_selector_accepts_current_placeholder_variants(self):
        video = DouYinVideo("标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json")
        title_input = MagicMock()
        title_input.wait_for = AsyncMock()
        title_input.fill = AsyncMock()
        description_editor = MagicMock()
        description_editor.wait_for = AsyncMock()
        description_editor.click = AsyncMock()
        page = MagicMock()
        page.locator.side_effect = [
            MagicMock(first=title_input),
            MagicMock(first=description_editor),
        ]
        page.keyboard.press = AsyncMock()
        page.keyboard.type = AsyncMock()

        asyncio.run(video.fill_title_and_description(page, "标题", "正文"))

        self.assertEqual(page.locator.call_args_list[0].args[0], 'input[placeholder*="作品标题"]')
        title_input.fill.assert_awaited_once_with("标题")

    def test_upload_only_sets_explicit_declaration(self):
        video = DouYinVideo(
            "标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json",
            declaration="已确认声明原文",
        )
        self.assertEqual(video.declaration, "已确认声明原文")

    def test_missing_declaration_does_not_fall_back_to_personal_opinion(self):
        video = DouYinVideo("标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json")
        self.assertIsNone(video.declaration)

    def test_legacy_positional_prefix_maps_to_thumbnail_and_product_fields(self):
        # postVideo.py 等调用点按位置传前 8 个参数，这部分契约必须保持稳定。
        video = DouYinVideo(
            "标题", "/tmp/demo.mp4", ["tag"], 0, "/tmp/cookie.json",
            "landscape.png", "https://item.example/1", "商品标题",
        )
        self.assertEqual(video.thumbnail_landscape_path, "landscape.png")
        self.assertEqual(video.productLink, "https://item.example/1")
        self.assertEqual(video.productTitle, "商品标题")

    def test_runtime_flags_are_honored_by_keyword(self):
        # collection_name 插到第 11 位后，尾部参数只能用关键字传，否则会静默错位。
        video = DouYinVideo(
            "标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json",
            publish_strategy="scheduled", debug=False, headless=False,
        )
        self.assertEqual(video.publish_strategy, "scheduled")
        self.assertFalse(video.debug)
        self.assertFalse(video.headless)
        self.assertIsNone(video.declaration)

    def test_apply_declaration_skips_when_unspecified(self):
        video = DouYinVideo("标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json")
        video.set_self_declaration = AsyncMock()
        asyncio.run(video.apply_self_declaration(object()))
        video.set_self_declaration.assert_not_awaited()

    def test_apply_declaration_uses_exact_explicit_text(self):
        page = object()
        video = DouYinVideo(
            "标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json",
            declaration="已确认声明原文",
        )
        video.set_self_declaration = AsyncMock(return_value=True)
        asyncio.run(video.apply_self_declaration(page))
        video.set_self_declaration.assert_awaited_once_with(page, "已确认声明原文")

    def test_explicit_declaration_failure_blocks_publish(self):
        video = DouYinVideo(
            "标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json",
            declaration="已确认声明原文",
        )
        video.set_self_declaration = AsyncMock(return_value=False)
        with self.assertRaisesRegex(RuntimeError, "自主声明"):
            asyncio.run(video.apply_self_declaration(object()))

    def test_declaration_failure_closes_browser_resources(self):
        video = DouYinVideo(
            "标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json",
            declaration="已确认声明原文",
        )
        video.validate_upload_args = AsyncMock()
        video.fill_title_and_description = AsyncMock()
        video.set_thumbnail = AsyncMock()
        video.apply_self_declaration = AsyncMock(side_effect=RuntimeError("抖音自主声明设置失败"))

        locator = MagicMock()
        locator.first = locator
        locator.locator = MagicMock(return_value=locator)
        locator.set_input_files = AsyncMock()
        locator.wait_for = AsyncMock()
        locator.count = AsyncMock(return_value=1)
        locator.is_visible = AsyncMock(return_value=False)
        locator.click = AsyncMock()
        page = MagicMock()
        page.goto = AsyncMock()
        page.wait_for_url = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.evaluate = AsyncMock()
        page.eval_on_selector = AsyncMock(return_value="")
        page.get_by_role = MagicMock(return_value=locator)
        page.get_by_text = MagicMock(return_value=locator)
        page.locator.return_value = locator

        context = MagicMock()
        context.new_page = AsyncMock(return_value=page)
        context.close = AsyncMock(side_effect=OSError("close failed"))
        browser = MagicMock()
        browser.new_context = AsyncMock(return_value=context)
        browser.close = AsyncMock()
        playwright = MagicMock()
        playwright.chromium.launch = AsyncMock(return_value=browser)

        with (
            patch.object(douyin_main, "set_init_script", AsyncMock(return_value=context)),
            patch.object(douyin_main.asyncio, "sleep", AsyncMock()),
            self.assertRaisesRegex(RuntimeError, "自主声明"),
        ):
            asyncio.run(video.upload(playwright))

        context.close.assert_awaited_once()
        browser.close.assert_awaited_once()


class DouyinOverlayCleanupTests(unittest.TestCase):
    def test_cleanup_targets_only_the_topic_suggestion_mount(self):
        video = DouYinVideo("标题", "/tmp/demo.mp4", [], 0, "/tmp/cookie.json")
        page = MagicMock()
        page.keyboard.press = AsyncMock()
        page.evaluate = AsyncMock()
        page.wait_for_timeout = AsyncMock()

        asyncio.run(video._clear_blocking_overlays(page))

        cleanup_script = page.evaluate.await_args.args[0]
        self.assertIn(".mention-suggest-mount-dom", cleanup_script)
        self.assertNotIn('[class*="mention-wrapper"]', cleanup_script)

        uploader_source = inspect.getsource(DouYinVideo)
        self.assertNotIn('[class*="mention-wrapper"]', uploader_source)
        self.assertGreaterEqual(uploader_source.count(".mention-suggest-mount-dom"), 2)


if __name__ == "__main__":
    unittest.main()
