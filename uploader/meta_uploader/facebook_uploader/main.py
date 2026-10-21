"""通过 Patchright 在 Facebook 个人主页发布视频。

这里使用 Facebook 首页的个人/主页发帖 composer。Meta Business Suite 的 Page
发布和定时发布需要另一套已登录主体与权限，不能把它们和个人主页流程混用。
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

from patchright.async_api import Page, Playwright, async_playwright, expect

from utils.log import facebook_logger


FACEBOOK_HOME_URL = "https://www.facebook.com/"
# 代理只从显式 CLI 参数或用户自行设置的环境变量读取；未设置时直连。
FACEBOOK_PROXY = os.environ.get("SAU_FACEBOOK_PROXY")
FACEBOOK_LOGIN_INPUT = 'input[name="email"]'
# 首页发帖附件同时接受图片与视频，头像/封面控件不具备这组 MIME 类型。
FACEBOOK_MEDIA_INPUT = 'input[type="file"][accept*="image/"][accept*="video/"]'


def _proxy_options(proxy: str | None) -> dict[str, str] | None:
    """未传参数时使用显式环境配置，否则直连；空字符串可覆盖环境配置并直连。"""
    address = (FACEBOOK_PROXY if proxy is None else proxy) or ""
    address = address.strip()
    return {"server": address} if address else None


async def _is_logged_out(page: Page) -> bool:
    """根据登录流程标记和首页发帖业务锚点判断会话是否有效。"""
    current_url = page.url.lower()
    # two_step_verification 是登录流程中的二次验证页，不能误判成已登录首页。
    if any(
        marker in current_url
        for marker in ("/login", "checkpoint", "two_step_verification", "/authentication/")
    ):
        return True
    email_input = page.locator(FACEBOOK_LOGIN_INPUT)
    if await email_input.count() and await email_input.first.is_visible():
        return True
    # 发帖附件控件是首页 composer 已挂载的正向证据，空白页/登录中页面不能当作已登录。
    return await page.locator(FACEBOOK_MEDIA_INPUT).count() != 1


async def _open_facebook_page(playwright: Playwright, account_file: Path, *, proxy: str | None, headless: bool):
    """使用 storage state 打开 Facebook，并保留代理配置到浏览器进程。"""
    launch_options = {
        "channel": "chrome",
        "headless": headless,
        "proxy": _proxy_options(proxy),
    }
    browser = await playwright.chromium.launch(**launch_options)
    try:
        context = await browser.new_context(storage_state=str(account_file))
        page = await context.new_page()
        page.set_default_timeout(30_000)
        await page.goto(FACEBOOK_HOME_URL, wait_until="domcontentloaded", timeout=90_000)
        await page.locator("body").wait_for(state="visible", timeout=30_000)
        return browser, context, page
    except Exception:
        # 导航或 storage state 失败时，浏览器已经属于本函数，必须在抛错前释放。
        await browser.close()
        raise


async def facebook_cookie_auth(account_file: str | Path, *, proxy: str | None = None) -> bool:
    """检查保存的 Facebook storage state 是否仍能进入已登录首页。"""
    account_file = Path(account_file)
    if not account_file.is_file():
        return False
    async with async_playwright() as playwright:
        browser, context, page = await _open_facebook_page(
            playwright, account_file, proxy=proxy, headless=True
        )
        try:
            return not await _is_logged_out(page)
        finally:
            await browser.close()


async def facebook_setup(
    account_file: str | Path,
    *,
    handle: bool = False,
    return_detail: bool = False,
    headless: bool = False,
    proxy: str | None = None,
    timeout_seconds: int = 600,
):
    """校验登录态；登录命令用可见浏览器等待用户完成登录后保存状态。"""
    account_file = Path(account_file)
    account_file.parent.mkdir(parents=True, exist_ok=True)
    valid = await facebook_cookie_auth(account_file, proxy=proxy)
    if valid:
        result = {
            "success": True,
            "status": "cookie_valid",
            "message": "Facebook 登录态有效",
            "account_file": str(account_file),
        }
        return result if return_detail else True
    if not handle:
        result = {
            "success": False,
            "status": "cookie_invalid",
            "message": "Facebook 登录态不存在或已失效",
            "account_file": str(account_file),
        }
        return result if return_detail else False

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            channel="chrome", headless=headless, proxy=_proxy_options(proxy)
        )
        try:
            context = await browser.new_context(
                storage_state=str(account_file) if account_file.is_file() else None
            )
            page = await context.new_page()
            page.set_default_timeout(30_000)
            await page.goto(FACEBOOK_HOME_URL, wait_until="domcontentloaded", timeout=90_000)
            facebook_logger.info("请在打开的 Facebook 浏览器中完成登录，程序会自动保存登录态")
            deadline = asyncio.get_running_loop().time() + timeout_seconds
            while asyncio.get_running_loop().time() < deadline:
                if not await _is_logged_out(page):
                    await context.storage_state(path=str(account_file))
                    result = {
                        "success": True,
                        "status": "logged_in",
                        "message": "Facebook 登录成功，登录态已保存",
                        "account_file": str(account_file),
                        "current_url": page.url,
                    }
                    return result if return_detail else True
                await page.wait_for_timeout(1000)
            result = {
                "success": False,
                "status": "timeout",
                "message": "等待 Facebook 登录超时，未保存登录态",
                "account_file": str(account_file),
                "current_url": page.url,
            }
            return result if return_detail else False
        finally:
            await browser.close()


class FacebookPost:
    """通过个人主页 composer 发布一个视频或一组图片。"""

    def __init__(
        self,
        title: str,
        file_path: str | Path | list[Path],
        description: str,
        tags: list[str],
        account_file: str | Path,
        proxy: str | None = None,
        headless: bool = True,
    ):
        self.title = title.strip()
        self.files = [Path(item) for item in file_path] if isinstance(file_path, list) else [Path(file_path)]
        self.file_path = self.files[0] if self.files else Path()
        self.description = description.strip()
        self.tags = [tag.strip().lstrip("#") for tag in tags if tag.strip().lstrip("#")]
        self.account_file = Path(account_file)
        self.proxy = proxy
        self.headless = headless

    def _caption(self) -> str:
        """Facebook 首页没有独立视频标题字段，按项目统一约定合并为正文。"""
        parts = [part for part in (self.title, self.description) if part]
        if self.tags:
            parts.append(" ".join(f"#{tag}" for tag in self.tags))
        return "\n\n".join(parts)

    async def _find_caption_editor(self, page: Page):
        # 外层 aria-modal dialog 属于本次发帖表单，排除首页评论框及隐藏模板。
        editor = page.locator('[role="dialog"][aria-modal="true"] [contenteditable="true"][role="textbox"]')
        await expect(editor).to_have_count(1)
        return editor

    async def _find_publish_button(self, page: Page):
        # 发帖 form 的最后一个业务动作是提交，前面的按钮分别为编辑器关闭、隐私及附件编辑。
        # 图文/视频实际 DOM 均已检查；嵌套 dialog 实际是编辑器标题栏，不能把它当提交区域。
        form = page.locator('[role="dialog"][aria-modal="true"] form')
        await expect(form).to_have_count(1)
        button = form.get_by_role('button').last
        await expect(button).to_be_visible()
        return button

    async def _wait_until_publishable(self, page: Page) -> None:
        deadline = asyncio.get_running_loop().time() + 180
        while asyncio.get_running_loop().time() < deadline:
            error = page.locator('[role="dialog"] [role="alert"]')
            if await error.count() and await error.first.is_visible():
                message = (await error.first.inner_text()).strip()
                if message:
                    raise RuntimeError(f"Facebook 视频上传失败: {message}")
            try:
                publish_button = await self._find_publish_button(page)
                if await publish_button.is_enabled():
                    return
            except RuntimeError as exc:
                if "未找到 Facebook 发布按钮" not in str(exc):
                    raise
            await page.wait_for_timeout(1000)
        raise TimeoutError("Facebook 视频上传或处理超时，发布按钮未就绪")

    async def _publish_and_verify(self, page: Page) -> None:
        publish_button = await self._find_publish_button(page)
        # 已实测成功提示是完整句子，不能把动态中任意“已发布”文案当成本次成功。
        success_pattern = re.compile(r"^(?:你的帖子已成功分享给.+|你的帖子已发布|Your post has been published[.!]?)$", re.I)
        success_text = page.get_by_text(success_pattern)
        for index in range(await success_text.count()):
            if await success_text.nth(index).is_visible():
                raise RuntimeError("提交前已存在发布成功提示，无法区分本次结果；未提交")
        await publish_button.click()
        deadline = asyncio.get_running_loop().time() + 90
        while asyncio.get_running_loop().time() < deadline:
            # 只接受状态提示或成功文案；弹窗消失本身不足以证明服务端已受理。
            success_text = page.get_by_text(success_pattern)
            if await success_text.count():
                for index in range(await success_text.count()):
                    if await success_text.nth(index).is_visible():
                        return
            await page.wait_for_timeout(1000)
        raise TimeoutError("已点击 Facebook 发布，但未观察到明确的发布成功状态")

    async def upload(self, playwright: Playwright) -> None:
        if not self.files:
            raise ValueError("Facebook 发布素材不能为空")
        for file in self.files:
            if not file.is_file():
                raise FileNotFoundError(f"Facebook 素材文件不存在: {file}")
        if not self.title:
            raise ValueError("Facebook 视频标题不能为空")
        if not self.account_file.is_file():
            raise RuntimeError(f"Facebook 登录态文件不存在: {self.account_file}")

        browser, context, page = await _open_facebook_page(
            playwright, self.account_file, proxy=self.proxy, headless=self.headless
        )
        try:
            if await _is_logged_out(page):
                raise RuntimeError("Facebook 登录态失效，请先执行 sau facebook login")

            # 已实测首页的唯一混合影音 input；按 accept 同时支持图片和视频限定，排除头像等控件。
            file_input = page.locator(FACEBOOK_MEDIA_INPUT)
            if await file_input.count() != 1:
                raise RuntimeError("首页发帖影音上传控件不唯一，未上传")
            await file_input.set_input_files([str(file) for file in self.files])

            # 选择素材后 composer 异步挂载；不能在同一轮立即检查 count 就判输入框不存在。
            await page.locator('[role="dialog"] [contenteditable="true"][role="textbox"]:visible').wait_for(timeout=30000)
            editor = await self._find_caption_editor(page)
            caption = self._caption()
            await editor.click()
            await editor.fill(caption)
            if (await editor.inner_text()).strip() != caption:
                raise RuntimeError("Facebook 正文输入框未读回预期内容")

            await self._wait_until_publishable(page)
            await self._publish_and_verify(page)
            await context.storage_state(path=str(self.account_file))
        finally:
            await browser.close()

    async def main(self) -> None:
        async with async_playwright() as playwright:
            await self.upload(playwright)


# 保留原视频调用方的类名；视频和图文实际共用同一发帖表单，无额外包装层。
FacebookVideo = FacebookPost
