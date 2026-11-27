# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from uploader.douyin_uploader.main import DouYinVideo
from uploader.ks_uploader.main import KSVideo
from uploader.tencent_uploader.main import TencentVideo, _matches_tencent_schedule
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
from utils.base_social_media import get_select_all_shortcut


class FakeInput:
    def __init__(self, initial_value: str = "", revert_on_invalid: bool = False):
        self.value = initial_value
        self.revert_on_invalid = revert_on_invalid
        self.default_value = initial_value
        self.selected_all = False
        self.clicked = 0
        self.filled_values = []

    @property
    def first(self):
        return self

    async def wait_for(self, **kwargs):
        return None

    async def click(self, **kwargs):
        self.clicked += 1

    async def fill(self, value: str):
        self.filled_values.append(value)
        if not self.revert_on_invalid:
            self.value = value

    async def input_value(self) -> str:
        return self.value


class FakeButton:
    def __init__(self, children=None):
        self.clicked = 0
        self.children = children or {}

    @property
    def first(self):
        return self

    def filter(self, **kwargs):
        return self

    def nth(self, index: int):
        return self

    def locator(self, selector: str):
        return self.children.get(selector, FakeButton())

    async def click(self, **kwargs):
        self.clicked += 1


class FakeKeyboard:
    def __init__(self, target_input: FakeInput | None = None, platform: str = "darwin"):
        self.actions = []
        self.target_input = target_input
        self.platform = platform

    async def press(self, key: str):
        self.actions.append(("press", key))
        if not self.target_input:
            return
        select_all_works = (self.platform == "darwin" and key == "Meta+KeyA") or (
            self.platform != "darwin" and key in ("Control+KeyA", "Control+A", "Control+a")
        )
        if select_all_works:
            self.target_input.selected_all = True
        elif key in ("Backspace", "Delete") and self.target_input.selected_all:
            self.target_input.value = ""
            self.target_input.selected_all = False
        elif key == "Enter" and self.target_input.revert_on_invalid:
            self.target_input.value = self.target_input.default_value

    async def type(self, text: str, delay=None):
        self.actions.append(("type", text))
        if not self.target_input:
            return
        if self.target_input.selected_all:
            self.target_input.value = text
            self.target_input.selected_all = False
        else:
            self.target_input.value = text + self.target_input.value


class CrossPlatformSelectAllTests(unittest.TestCase):
    def test_select_all_shortcut_by_platform(self):
        self.assertEqual(get_select_all_shortcut("darwin"), "Meta+KeyA")
        self.assertEqual(get_select_all_shortcut("win32"), "Control+KeyA")
        self.assertEqual(get_select_all_shortcut("linux"), "Control+KeyA")


class DouyinScheduleTests(unittest.TestCase):
    def test_macos_schedule_uses_meta_select_all_and_verifies_value(self):
        target = datetime(2026, 11, 27, 20, 0)
        schedule_input = FakeInput(initial_value="2026-11-27 03:40")
        radio = FakeButton()
        page = MagicMock()
        page.keyboard = FakeKeyboard(schedule_input, platform="darwin")
        page.locator.side_effect = lambda sel: radio if "radio" in sel else schedule_input

        uploader = DouYinVideo("标题", "/tmp/demo.mp4", [], target, "/tmp/cookie.json", publish_strategy="scheduled")
        with (
            patch("utils.base_social_media.sys.platform", "darwin"),
            patch("uploader.douyin_uploader.main.asyncio.sleep", AsyncMock()),
        ):
            asyncio.run(uploader.set_schedule_time_douyin(page, target))

        self.assertIn(("press", "Meta+KeyA"), page.keyboard.actions)
        self.assertNotIn(("press", "Control+KeyA"), page.keyboard.actions)
        self.assertEqual(schedule_input.value, "2026-11-27 20:00")

    def test_schedule_mismatch_raises_instead_of_publishing_at_default_time(self):
        target = datetime(2026, 11, 27, 20, 0)
        schedule_input = FakeInput(initial_value="2026-11-27 03:40", revert_on_invalid=True)
        radio = FakeButton()
        page = MagicMock()
        page.keyboard = FakeKeyboard(schedule_input, platform="darwin")
        page.locator.side_effect = lambda sel: radio if "radio" in sel else schedule_input

        uploader = DouYinVideo("标题", "/tmp/demo.mp4", [], target, "/tmp/cookie.json", publish_strategy="scheduled")
        with (
            patch("utils.base_social_media.sys.platform", "darwin"),
            patch("uploader.douyin_uploader.main.asyncio.sleep", AsyncMock()),
            self.assertRaisesRegex(RuntimeError, "定时发布时间设置校验失败"),
        ):
            asyncio.run(uploader.set_schedule_time_douyin(page, target))


class TencentScheduleTests(unittest.TestCase):
    def test_matches_tencent_schedule_formats(self):
        target = datetime(2026, 11, 27, 20, 30)
        self.assertTrue(_matches_tencent_schedule("2026-11-27 20:30", target))
        self.assertTrue(_matches_tencent_schedule("2026年11月27日 20:30", target))
        self.assertFalse(_matches_tencent_schedule("2026-11-27 03:04", target))
        self.assertFalse(_matches_tencent_schedule("2026-11-27 20:00", target))

    def test_macos_schedule_sets_hour_and_minute_and_verifies(self):
        target = datetime(2026, 11, 27, 20, 30)
        time_input = FakeInput(initial_value="03:04")
        main_input = FakeInput(initial_value="2026-11-27 03:04")

        class SyncingKeyboard(FakeKeyboard):
            async def press(self, key: str):
                await super().press(key)
                if key == "Enter" and time_input.value == "20:30":
                    main_input.value = "2026-11-27 20:30"

        day_el = MagicMock()
        day_el.evaluate = AsyncMock(return_value="weui-desktop-picker__day")
        day_el.inner_text = AsyncMock(return_value="27")
        day_el.click = AsyncMock()

        page = MagicMock()
        page.keyboard = SyncingKeyboard(time_input, platform="darwin")
        page.click = AsyncMock()
        page.inner_text = AsyncMock(return_value="11月")
        page.query_selector_all = AsyncMock(return_value=[day_el])
        page.wait_for_timeout = AsyncMock()
        page.locator.side_effect = lambda sel: (
            time_input if "请选择时间" in sel
            else main_input if "请选择发表时间" in sel
            else FakeButton()
        )

        uploader = TencentVideo("标题", "/tmp/demo.mp4", [], target, "/tmp/cookie.json", publish_strategy="scheduled")
        with patch("utils.base_social_media.sys.platform", "darwin"):
            asyncio.run(uploader.set_schedule_time_tencent(page, target))

        self.assertIn(("press", "Meta+KeyA"), page.keyboard.actions)
        self.assertIn(("type", "20:30"), page.keyboard.actions)
        self.assertEqual(main_input.value, "2026-11-27 20:30")

    def test_schedule_mismatch_raises_runtime_error(self):
        target = datetime(2026, 11, 27, 20, 30)
        time_input = FakeInput(initial_value="03:04", revert_on_invalid=True)
        main_input = FakeInput(initial_value="2026-11-27 03:04", revert_on_invalid=True)

        day_el = MagicMock()
        day_el.evaluate = AsyncMock(return_value="weui-desktop-picker__day")
        day_el.inner_text = AsyncMock(return_value="27")
        day_el.click = AsyncMock()

        page = MagicMock()
        page.keyboard = FakeKeyboard(time_input, platform="darwin")
        page.click = AsyncMock()
        page.inner_text = AsyncMock(return_value="11月")
        page.query_selector_all = AsyncMock(return_value=[day_el])
        page.wait_for_timeout = AsyncMock()
        page.locator.side_effect = lambda sel: (
            time_input if "请选择时间" in sel
            else main_input if "请选择发表时间" in sel
            else FakeButton()
        )

        uploader = TencentVideo("标题", "/tmp/demo.mp4", [], target, "/tmp/cookie.json", publish_strategy="scheduled")
        with (
            patch("utils.base_social_media.sys.platform", "darwin"),
            self.assertRaisesRegex(RuntimeError, "视频号定时发布时间设置校验失败"),
        ):
            asyncio.run(uploader.set_schedule_time_tencent(page, target))


class KuaishouAndXiaohongshuScheduleTests(unittest.TestCase):
    def test_kuaishou_missing_schedule_input_raises_instead_of_silent_return(self):
        target = datetime(2026, 11, 27, 20, 0)
        schedule_input = FakeInput()
        page = MagicMock()
        page.keyboard = FakeKeyboard()
        page.evaluate = AsyncMock(return_value=False)
        page.locator.side_effect = lambda sel: schedule_input if "选择日期时间" in sel else FakeButton()

        uploader = KSVideo("标题", "/tmp/demo.mp4", [], target, "/tmp/cookie.json", publish_strategy="scheduled")
        with (
            patch("uploader.ks_uploader.main.asyncio.sleep", AsyncMock()),
            self.assertRaisesRegex(RuntimeError, "找不到快手定时发布时间输入框"),
        ):
            asyncio.run(uploader.set_schedule_time(page, target))

    def test_kuaishou_schedule_mismatch_raises(self):
        target = datetime(2026, 11, 27, 20, 0)
        schedule_input = FakeInput(initial_value="")
        page = MagicMock()
        page.keyboard = FakeKeyboard()
        page.evaluate = AsyncMock(return_value=True)
        page.locator.side_effect = lambda sel: schedule_input if "选择日期时间" in sel else FakeButton()

        uploader = KSVideo("标题", "/tmp/demo.mp4", [], target, "/tmp/cookie.json", publish_strategy="scheduled")
        with (
            patch("uploader.ks_uploader.main.asyncio.sleep", AsyncMock()),
            self.assertRaisesRegex(RuntimeError, "快手定时发布时间设置校验失败"),
        ):
            asyncio.run(uploader.set_schedule_time(page, target))

    def test_xiaohongshu_schedule_verifies_value_and_raises_on_mismatch(self):
        target = datetime(2026, 11, 27, 20, 30)
        ok_input = FakeInput()
        page_ok = MagicMock()
        page_ok.keyboard = FakeKeyboard(ok_input)
        page_ok.locator.side_effect = lambda sel: ok_input if "d-datepicker" in sel else FakeButton()

        uploader = XiaoHongShuVideo("标题", "/tmp/demo.mp4", [], target, "/tmp/cookie.json", publish_strategy="scheduled")
        with patch("uploader.xiaohongshu_uploader.main.asyncio.sleep", AsyncMock()):
            asyncio.run(uploader.set_schedule_time_xiaohongshu(page_ok, target))
        self.assertEqual(ok_input.value, "2026-11-27 20:30")

        bad_input = FakeInput(initial_value="2026-11-27 03:40", revert_on_invalid=True)
        page_bad = MagicMock()
        page_bad.keyboard = FakeKeyboard(bad_input)
        page_bad.locator.side_effect = lambda sel: bad_input if "d-datepicker" in sel else FakeButton()
        with (
            patch("uploader.xiaohongshu_uploader.main.asyncio.sleep", AsyncMock()),
            self.assertRaisesRegex(RuntimeError, "小红书定时发布时间设置校验失败"),
        ):
            asyncio.run(uploader.set_schedule_time_xiaohongshu(page_bad, target))


if __name__ == "__main__":
    unittest.main()
