# Language: 中文
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from uploader.douyin_uploader.main import DouYinNote


class DouyinNoteFlowTests(unittest.TestCase):
    def build_note(self):
        return DouYinNote(
            image_paths=["1.png"],
            title="图文标题",
            note="图文正文",
            tags=["测试"],
            publish_date=0,
            account_file="account.json",
            debug=False,
        )

    def test_fill_title_and_description_writes_note_before_tags(self):
        note = self.build_note()
        title_input = MagicMock()
        title_input.first = title_input
        title_input.wait_for = AsyncMock()
        title_input.fill = AsyncMock()
        editor = MagicMock()
        editor.first = editor
        editor.wait_for = AsyncMock()
        editor.click = AsyncMock()

        page = MagicMock()
        page.locator.side_effect = [title_input, editor]
        page.keyboard.press = AsyncMock()
        page.keyboard.insert_text = AsyncMock()
        page.keyboard.type = AsyncMock()

        asyncio.run(
            note.fill_title_and_description(page, "图文标题", "图文正文", ["测试"])
        )

        title_input.fill.assert_awaited_once_with("图文标题")
        page.keyboard.insert_text.assert_awaited_once_with("图文正文")
        page.keyboard.type.assert_awaited_once_with(" #测试")

    def test_fill_title_falls_back_to_alternate_placeholder(self):
        note = self.build_note()
        missing_title = MagicMock()
        missing_title.first = missing_title
        missing_title.wait_for = AsyncMock(side_effect=TimeoutError)
        alternate_title = MagicMock()
        alternate_title.first = alternate_title
        alternate_title.wait_for = AsyncMock()
        alternate_title.fill = AsyncMock()
        editor = MagicMock()
        editor.first = editor
        editor.wait_for = AsyncMock()
        editor.click = AsyncMock()

        page = MagicMock()
        page.locator.side_effect = [missing_title, alternate_title, editor]
        page.keyboard.press = AsyncMock()
        page.keyboard.insert_text = AsyncMock()
        page.keyboard.type = AsyncMock()

        asyncio.run(note.fill_title_and_description(page, "备用标题", "正文", []))

        alternate_title.fill.assert_awaited_once_with("备用标题")

    def test_upload_note_clicks_publish_only_once(self):
        note = self.build_note()
        note.fill_title_and_description = AsyncMock()
        note.wait_for_publish_result = AsyncMock()

        publish_button = MagicMock()
        publish_button.wait_for = AsyncMock()
        publish_button.click = AsyncMock()
        image_input = MagicMock()
        image_input.set_input_files = AsyncMock()

        page = MagicMock()
        page.url = "https://creator.douyin.com/creator-micro/content/post/image"
        page.wait_for_timeout = AsyncMock()
        page.wait_for_url = AsyncMock()
        page.get_by_text.return_value.click = AsyncMock()
        page.get_by_role.return_value = publish_button
        page.locator.return_value = image_input

        with patch("uploader.douyin_uploader.main.asyncio.sleep", new=AsyncMock()):
            asyncio.run(note.upload_note_content(page))

        publish_button.click.assert_awaited_once()
        note.wait_for_publish_result.assert_awaited_once_with(page, "图文")


if __name__ == "__main__":
    unittest.main()
