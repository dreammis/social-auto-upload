# -*- coding: utf-8 -*-
# pyright: reportArgumentType=false
import unittest
from unittest.mock import AsyncMock, patch

from uploader.tencent_uploader.main import TencentVideo


class FakeLocator:
    def __init__(self, *, count=1, wait_error=None):
        self._count = count
        self._wait_error = wait_error
        self.files = []

    @property
    def first(self):
        return self

    async def count(self):
        return self._count

    async def wait_for(self, **_kwargs):
        if self._wait_error:
            raise self._wait_error

    async def set_input_files(self, path):
        self.files.append(path)


class ConfirmLocator(FakeLocator):
    def __init__(self, *, count=1):
        super().__init__(count=count)
        self.clicked = False

    async def click(self, **_kwargs):
        self.clicked = True


class FakeCoverDialog:
    def __init__(self, *, confirm_count=1, close_error=None):
        self.file_input = FakeLocator()
        self.confirm = ConfirmLocator(count=confirm_count)
        self.close_error = close_error
        self.wait_states = []

    async def wait_for(self, **kwargs):
        state = kwargs.get("state")
        self.wait_states.append(state)
        if state == "hidden" and self.close_error:
            raise self.close_error

    def locator(self, selector):
        if 'input[type="file"]' in selector:
            return self.file_input
        return self.confirm


class FakePage:
    async def wait_for_timeout(self, _milliseconds):
        return None

    def locator(self, _selector):
        raise AssertionError("封面确认不得使用页面全局 locator")


class FakeThumbnailPage:
    def __init__(self):
        self.scripts = []

    async def evaluate(self, script):
        self.scripts.append(script)


class FakePublishButton(FakeLocator):
    async def element_handle(self):
        return self


class FakePublishPage:
    def __init__(self):
        self.url = "https://channels.weixin.qq.com/platform/post/create"
        self.publish_button = FakePublishButton()
        self.publish_clicks = 0
        self.navigation_attempts = 0

    def locator(self, selector):
        if "发表" in selector:
            return self.publish_button
        return FakeLocator(count=0)

    async def evaluate(self, _script, arg=None):
        if arg is self.publish_button:
            self.publish_clicks += 1

    async def wait_for_url(self, *_args, **_kwargs):
        self.navigation_attempts += 1
        raise TimeoutError("SPA did not confirm navigation")


class TencentThumbnailTests(unittest.IsolatedAsyncioTestCase):
    def make_uploader(self):
        return TencentVideo(
            title="标题",
            file_path="video.mp4",
            tags=[],
            publish_date=0,
            account_file="account.json",
            thumbnail_path="cover.png",
        )

    async def test_missing_confirm_button_aborts_thumbnail_upload(self):
        with self.assertRaisesRegex(RuntimeError, "封面确认"):
            await self.make_uploader().upload_thumbnail_in_dialog(
                FakePage(), FakeCoverDialog(confirm_count=0), "cover.png"
            )

    async def test_missing_thumbnail_dialog_aborts_publish(self):
        uploader = self.make_uploader()
        with (
            patch.object(
                uploader, "_cover_preview_fingerprint", AsyncMock(return_value="before")
            ),
            patch.object(
                uploader, "open_thumbnail_dialog", AsyncMock(return_value=None)
            ),
            self.assertRaisesRegex(RuntimeError, "封面编辑弹窗"),
        ):
            await uploader.set_single_thumbnail(
                object(), "cover.png", ["entry"], ["dialog"], "3:4 竖版"
            )

    async def test_confirmed_thumbnail_waits_for_editor_to_close(self):
        dialog = FakeCoverDialog()
        await self.make_uploader().upload_thumbnail_in_dialog(
            FakePage(), dialog, "cover.png"
        )
        self.assertIn("hidden", dialog.wait_states)

    async def test_confirm_uses_current_dialog_instead_of_hidden_page_template(self):
        dialog = FakeCoverDialog()
        await self.make_uploader().upload_thumbnail_in_dialog(
            FakePage(), dialog, "cover.png"
        )
        self.assertTrue(dialog.confirm.clicked)

    async def test_open_thumbnail_editor_after_confirm_aborts_upload(self):
        with self.assertRaisesRegex(RuntimeError, "弹窗未关闭"):
            await self.make_uploader().upload_thumbnail_in_dialog(
                FakePage(),
                FakeCoverDialog(close_error=TimeoutError("dialog stayed open")),
                "cover.png",
            )

    async def test_thumbnail_entry_clears_overlays_before_opening_editor(self):
        uploader = self.make_uploader()
        page = FakeThumbnailPage()
        with patch.object(
            uploader, "set_single_thumbnail", AsyncMock()
        ) as set_thumbnail:
            await uploader.set_thumbnail(page)
        self.assertIn(".weui-desktop-dialog__wrp", page.scripts[0])
        set_thumbnail.assert_awaited_once()

    async def test_publish_navigation_failure_does_not_click_twice(self):
        page = FakePublishPage()
        with self.assertRaisesRegex(RuntimeError, "禁止重复点击"):
            await self.make_uploader().submit_publish(page)
        self.assertEqual(page.publish_clicks, 1)
        self.assertEqual(page.navigation_attempts, 1)

    async def test_thumbnail_failure_is_not_downgraded_to_skip(self):
        uploader = self.make_uploader()
        with (
            patch.object(
                uploader, "_cover_preview_fingerprint", AsyncMock(return_value="before")
            ),
            patch.object(
                uploader, "open_thumbnail_dialog", AsyncMock(return_value=object())
            ),
            patch.object(
                uploader,
                "upload_thumbnail_in_dialog",
                AsyncMock(side_effect=RuntimeError("封面确认失败")),
            ),
            self.assertRaisesRegex(RuntimeError, "封面确认失败"),
        ):
            await uploader.set_single_thumbnail(
                object(), "cover.png", ["entry"], ["dialog"], "3:4 竖版"
            )

    async def test_unchanged_cover_preview_aborts_publish(self):
        uploader = self.make_uploader()
        with (
            patch.object(
                uploader, "open_thumbnail_dialog", AsyncMock(return_value=object())
            ),
            patch.object(uploader, "upload_thumbnail_in_dialog", AsyncMock()),
            patch.object(
                uploader,
                "_cover_preview_fingerprint",
                AsyncMock(side_effect=["video-frame"] * 21),
            ),
            self.assertRaisesRegex(RuntimeError, "封面预览未更新"),
        ):
            await uploader.set_single_thumbnail(
                FakePage(), "cover.png", ["entry"], ["dialog"], "3:4 竖版"
            )

    async def test_changed_cover_preview_is_accepted(self):
        uploader = self.make_uploader()
        with (
            patch.object(
                uploader, "open_thumbnail_dialog", AsyncMock(return_value=object())
            ),
            patch.object(uploader, "upload_thumbnail_in_dialog", AsyncMock()),
            patch.object(
                uploader,
                "_cover_preview_fingerprint",
                AsyncMock(side_effect=["video-frame", "uploaded-cover"]),
            ),
        ):
            await uploader.set_single_thumbnail(
                object(), "cover.png", ["entry"], ["dialog"], "3:4 竖版"
            )


if __name__ == "__main__":
    unittest.main()
