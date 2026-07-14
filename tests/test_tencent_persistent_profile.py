import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import uploader.tencent_uploader.main as tencent_main


class FakeChromium:
    def __init__(self):
        self.launch_calls = []
        self.persistent_calls = []

    async def launch(self, **kwargs):
        self.launch_calls.append(kwargs)
        return object()

    async def launch_persistent_context(self, user_data_dir, **kwargs):
        self.persistent_calls.append((Path(user_data_dir), kwargs))
        return "context"


class FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium


class FakeEmptyLocator:
    @property
    def first(self):
        return self

    def locator(self, selector):
        return self

    async def count(self):
        return 0

    async def is_visible(self):
        return False

    async def click(self):
        raise AssertionError("empty locator should not be clicked")


class FakeVisibleLocator:
    def __init__(self, src=None):
        self._src = src
        self.clicked = False
        self.screenshot_path = None

    @property
    def first(self):
        return self

    def locator(self, selector):
        return self

    async def count(self):
        return 1

    async def is_visible(self):
        return True

    async def get_attribute(self, name):
        return self._src if name == "src" else None

    async def screenshot(self, path):
        self.screenshot_path = Path(path)
        self.screenshot_path.write_bytes(b"png")

    async def click(self):
        self.clicked = True


class FakeFrame:
    def __init__(self, selectors):
        self.selectors = selectors

    def locator(self, selector):
        for key, locator in self.selectors.items():
            if selector == key or selector.startswith(key):
                return locator
        return FakeEmptyLocator()


class FakePage:
    url = "https://channels.weixin.qq.com/login.html"

    def __init__(self, selectors):
        self.frames = [FakeFrame(selectors)]
        self.goto_calls = []

    def locator(self, selector):
        return FakeEmptyLocator()

    async def goto(self, url, **kwargs):
        self.goto_calls.append((url, kwargs))


class TencentPersistentProfileTests(unittest.TestCase):
    def test_profile_dir_is_derived_from_tencent_account_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_base_dir = tencent_main.BASE_DIR
            try:
                tencent_main.BASE_DIR = Path(tmp_dir)
                account_file = Path(tmp_dir) / "cookies" / "tencent_diyi.json"

                profile_dir = Path(tencent_main._resolve_persistent_profile_dir(account_file))
            finally:
                tencent_main.BASE_DIR = original_base_dir

        self.assertEqual(
            profile_dir,
            Path(tmp_dir) / "cookies" / "tencent_profiles" / "diyi",
        )

    def test_launch_context_uses_persistent_profile_when_forced(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_base_dir = tencent_main.BASE_DIR
            try:
                tencent_main.BASE_DIR = Path(tmp_dir)
                account_file = Path(tmp_dir) / "cookies" / "tencent_diyi.json"
                chromium = FakeChromium()

                context, browser = asyncio.run(
                    tencent_main._launch_tencent_context(
                        FakePlaywright(chromium),
                        account_file,
                        headless=False,
                        storage_state=False,
                        persistent=True,
                    )
                )
            finally:
                tencent_main.BASE_DIR = original_base_dir

        self.assertEqual(context, "context")
        self.assertIsNone(browser)
        self.assertEqual(chromium.launch_calls, [])
        self.assertEqual(
            chromium.persistent_calls[0][0],
            Path(tmp_dir) / "cookies" / "tencent_profiles" / "diyi",
        )

    def test_save_qrcode_screenshots_visible_wechat_connect_qr(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            account_file = Path(tmp_dir) / "cookies" / "tencent_diyi.json"
            qr_path = Path(tmp_dir) / "cookies" / "qr.png"
            locator = FakeVisibleLocator("/connect/qrcode/demo")

            fake_utils = {
                "build_login_qrcode_path": lambda account, suffix: qr_path,
                "decode_qrcode_from_path": lambda path: None,
                "print_terminal_qrcode": lambda *args, **kwargs: None,
                "remove_qrcode_file": lambda path: False,
                "save_data_url_image": lambda *args, **kwargs: (_ for _ in ()).throw(
                    AssertionError("data saver should not run")
                ),
            }
            with patch("uploader.tencent_uploader.main._get_qrcode_utils", return_value=fake_utils):
                info = asyncio.run(
                    tencent_main._save_tencent_qrcode(
                        FakePage({"img.js_qrcode_img": locator}),
                        str(account_file),
                    )
                )

        self.assertEqual(info["image_path"], str(qr_path))
        self.assertEqual(info["image_src"], "/connect/qrcode/demo")
        self.assertEqual(locator.screenshot_path, qr_path)

    def test_expired_qrcode_is_detected_inside_login_iframe(self):
        expired_tip = FakeVisibleLocator()
        page = FakePage({'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")': expired_tip})

        self.assertTrue(asyncio.run(tencent_main._is_tencent_qrcode_expired(page)))

    def test_hidden_bare_refresh_tip_is_not_treated_as_expired(self):
        hidden_template_tip = FakeVisibleLocator()
        page = FakePage({'p.refresh-tip:has-text("二维码已过期，点击刷新")': hidden_template_tip})

        self.assertFalse(asyncio.run(tencent_main._is_tencent_qrcode_expired(page)))

    def test_refresh_qrcode_clicks_refresh_tip_inside_login_iframe(self):
        refresh_tip = FakeVisibleLocator()
        page = FakePage({'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")': refresh_tip})

        asyncio.run(tencent_main._refresh_tencent_qrcode(page))

        self.assertTrue(refresh_tip.clicked)

    def test_wait_refreshes_qrcode_by_time_before_timeout(self):
        page = FakePage({})
        refreshed_info = {"image_path": "/tmp/qr2.png"}

        with patch(
            "uploader.tencent_uploader.main._is_tencent_login_completed",
            new=AsyncMock(return_value=False),
        ), patch(
            "uploader.tencent_uploader.main._is_tencent_qrcode_scanned",
            new=AsyncMock(return_value=False),
        ), patch(
            "uploader.tencent_uploader.main._is_tencent_qrcode_expired",
            new=AsyncMock(return_value=False),
        ), patch(
            "uploader.tencent_uploader.main._save_tencent_qrcode",
            new=AsyncMock(return_value=refreshed_info),
        ) as save_qr, patch(
            "uploader.tencent_uploader.main.asyncio.sleep",
            new=AsyncMock(),
        ):
            result = asyncio.run(
                tencent_main._wait_for_tencent_login(
                    page,
                    "account.json",
                    {"image_path": "/tmp/qr1.png"},
                    max_checks=2,
                    poll_interval=0,
                    refresh_seconds=0,
                )
            )

        self.assertEqual(result["status"], "timeout")
        self.assertEqual(page.goto_calls[0][0], tencent_main.TENCENT_LOGIN_URL)
        save_qr.assert_awaited()

    def test_wait_refreshes_even_when_scanned_logged_true(self):
        page = FakePage({})
        refreshed_info = {"image_path": "/tmp/qr3.png"}

        with patch(
            "uploader.tencent_uploader.main._is_tencent_login_completed",
            new=AsyncMock(return_value=False),
        ), patch(
            "uploader.tencent_uploader.main._is_tencent_qrcode_scanned",
            new=AsyncMock(return_value=True),
        ), patch(
            "uploader.tencent_uploader.main._is_tencent_qrcode_expired",
            new=AsyncMock(return_value=False),
        ), patch(
            "uploader.tencent_uploader.main._save_tencent_qrcode",
            new=AsyncMock(return_value=refreshed_info),
        ) as save_qr, patch(
            "uploader.tencent_uploader.main.asyncio.sleep",
            new=AsyncMock(),
        ):
            result = asyncio.run(
                tencent_main._wait_for_tencent_login(
                    page,
                    "account.json",
                    {"image_path": "/tmp/qr1.png"},
                    max_checks=2,
                    poll_interval=0,
                    refresh_seconds=0,
                )
            )

        self.assertEqual(result["status"], "timeout")
        save_qr.assert_awaited()


if __name__ == "__main__":
    unittest.main()
