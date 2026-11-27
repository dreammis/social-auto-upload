import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from uploader.tencent_uploader import main as tencent

LOGIN_MARKERS = "div.login-qrcode-wrap, div.qrcode-wrap, img.qrcode, " + 'span:has-text("微信扫码登录 视频号助手")'


def page_with(*, url=tencent.TENCENT_HOME_URL, frames=(), buttons=(), login=False):
    page = Mock(url=url, frames=[SimpleNamespace(url=value) for value in frames])
    marker = Mock(is_visible=AsyncMock(return_value=login))
    page.goto = AsyncMock()
    page.locator.side_effect = lambda selector, **kwargs: Mock(all=AsyncMock(return_value=
        [marker] if selector == LOGIN_MARKERS else [Mock(is_visible=AsyncMock(return_value=value)) for value in buttons]))
    return page


class TencentAuthTests(unittest.IsolatedAsyncioTestCase):
    async def probe(self, page, timeout=0.6):
        now = 0
        async def sleep(delay):
            nonlocal now
            now += delay
        with patch.object(tencent.time, "monotonic", side_effect=lambda: now), patch.object(tencent.asyncio, "sleep", side_effect=sleep):
            return await tencent._probe_tencent_auth(page, timeout=timeout)

    async def test_visible_backend_entry_is_valid(self):
        page = page_with(buttons=(False, True))
        self.assertEqual(await self.probe(page), "valid")
        page.locator.assert_called_with("button.weui-desktop-btn", has_text="发表视频")

    async def test_login_signals_override_backend_button(self):
        for kwargs in [
            {"url": "https://channels.weixin.qq.com/login.html?secret=hidden"},
            {"frames": ["https://open.weixin.qq.com/connect/qrconnect?secret=hidden"]},
            {"login": True},
        ]:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(await self.probe(page_with(buttons=(True,), **kwargs)), "invalid")

    async def test_empty_or_hidden_entry_expires_unknown(self):
        for buttons in [(), (False,)]:
            with self.subTest(buttons=buttons):
                self.assertEqual(await self.probe(page_with(buttons=buttons)), "unknown")

    async def test_locator_exception_is_unknown(self):
        page = page_with()
        page.locator.side_effect = RuntimeError("SECRET exception must not be logged")
        self.assertEqual(await self.probe(page), "unknown")

    async def test_delayed_backend_entry_is_observed(self):
        page = page_with()
        polls = 0
        def locator(selector, **kwargs):
            nonlocal polls
            if selector == LOGIN_MARKERS:
                return Mock(all=AsyncMock(return_value=[]))
            polls += 1
            return Mock(all=AsyncMock(return_value=[Mock(is_visible=AsyncMock(return_value=polls > 1))]))
        page.locator.side_effect = locator
        self.assertEqual(await self.probe(page), "valid")
        self.assertEqual(polls, 2)

    async def test_cookie_auth_home_navigation_and_failure_boundaries(self):
        for failure in [None, "goto", "context", "launch", "close"]:
            with self.subTest(failure=failure):
                page = page_with(buttons=(True,))
                context = Mock(new_page=AsyncMock(return_value=page))
                browser = Mock(new_context=AsyncMock(return_value=context), close=AsyncMock())
                launcher = AsyncMock(return_value=browser)
                if failure == "goto": page.goto.side_effect = RuntimeError("SECRET navigation error")
                if failure == "context": browser.new_context.side_effect = RuntimeError("SECRET context error")
                if failure == "launch": launcher.side_effect = RuntimeError("SECRET launch error")
                if failure == "close": browser.close.side_effect = RuntimeError("SECRET close error")
                session = Mock()
                session.__aenter__ = AsyncMock(return_value=SimpleNamespace(chromium=Mock(launch=launcher)))
                session.__aexit__ = AsyncMock(return_value=False)
                with patch.object(tencent, "async_playwright", return_value=session), patch.object(tencent, "set_init_script", AsyncMock(return_value=context)), patch.object(tencent, "tencent_logger") as logger:
                    self.assertEqual(await tencent.cookie_auth("unused.json"), failure is None)
                    self.assertNotIn("SECRET", str(logger.mock_calls))
                if failure not in ["context", "launch"]:
                    page.goto.assert_awaited_once_with(tencent.TENCENT_HOME_URL, wait_until="domcontentloaded", timeout=30000)
                if failure != "launch": browser.close.assert_awaited_once()

    def test_unknown_diagnostic_omits_credentials_and_qr_content(self):
        page = page_with(url="https://user:password@channels.weixin.qq.com/platform?cookie=SECRET#token", frames=[
            "https://open.weixin.qq.com/connect/qrconnect?ticket=SECRET",
            "https://open.weixin.qq.com/connect/qrcode/SECRET",
            "https://SECRET.invalid/secret/path",
        ])
        with patch.object(tencent, "tencent_logger") as logger:
            tencent._log_tencent_auth_state(page, "unknown")
            text = str(logger.mock_calls)
            self.assertIn("state=unknown", text)
            self.assertIn(tencent.TENCENT_HOME_URL, text)
            self.assertNotIn("SECRET", text)
            self.assertNotIn("password", text)
            self.assertNotIn("cookie=", text)
