# -*- coding: utf-8 -*-
"""淘宝光合 (creator.guanghe.taobao.com) 视频上传模块

⚠️ 选择器说明 / Caveat
----------------------
本模块的 upload 流程是骨架实现，对应的 CSS / 文本选择器来自
``uploader/taobao_guanghe_uploader/selector.py``，其中大部分选择器被
标记为 "待确认"（占位符），可能需要根据真实页面录制后再修正。

骨架按以下顺序执行（与 douyin_uploader 流程对齐）：

1. 打开创作者中心 https://creator.guanghe.taobao.com/
2. 进入视频上传页
3. 上传本地视频文件（``set_input_files``）
4. 等待视频处理完成
5. 填写标题 / 描述 / 标签
6. 可选：关联商品（商品链接 / 标题）
7. 可选：设置定时发布时间
8. 点击"发布"按钮

如果中途某个步骤的选择器不匹配，会抛出明确的 ``RuntimeError``，
方便定位是哪个步骤需要录制新的选择器。
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from uploader.taobao_guanghe_uploader.login import cookie_auth
from uploader.taobao_guanghe_uploader.selector import (
    CREATOR_CENTER_URL,
    GUANGHE_HOME_URL,
    TaobaoGuangheSelectors,
)
from utils.base_social_media import set_init_script
from utils.log import taobao_guanghe_logger

TAOBAO_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
TAOBAO_PUBLISH_STRATEGY_SCHEDULED = "scheduled"

_SELECTORS = TaobaoGuangheSelectors()


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


class TaobaoGuangheBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = TAOBAO_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.publish_date = publish_date
        self.account_file = account_file
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = headless

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie 文件不存在，请先完成淘宝光合登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie 已失效，请重新登录淘宝光合: {self.account_file}")
        if self.publish_strategy not in {
            TAOBAO_PUBLISH_STRATEGY_IMMEDIATE,
            TAOBAO_PUBLISH_STRATEGY_SCHEDULED,
        }:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == TAOBAO_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    def _browser_launch_options(self) -> dict:
        opts: dict = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        }
        if self.local_executable_path:
            opts["executable_path"] = self.local_executable_path
        else:
            opts["channel"] = "chrome"
        return opts


class TaobaoGuangheVideo(TaobaoGuangheBaseUploader):
    def __init__(
        self,
        title: str,
        file_path: str,
        tags: list[str] | None,
        publish_date: datetime | int,
        account_file,
        productLink: str = "",
        productTitle: str = "",
        publish_strategy: str = TAOBAO_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
        )
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.productLink = productLink
        self.productTitle = productTitle

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("淘宝光合视频上传：title 必填")
        self.file_path = str(self.validate_video_file(self.file_path))

    async def _wait_for_visible(self, page: Page, selector: str, timeout: int = 10000):
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout)
        return loc

    async def _open_upload_page(self, page: Page) -> None:
        """导航到创作者中心的视频上传入口。"""
        taobao_guanghe_logger.info(_msg("🌐", f"打开创作者中心: {CREATOR_CENTER_URL}"))
        await page.goto(CREATOR_CENTER_URL, timeout=60000, wait_until="domcontentloaded")
        # 关闭可能的引导弹窗
        try:
            guide_close = page.locator(_SELECTORS.guide_modal_close).first
            if await guide_close.count() and await guide_close.is_visible():
                await guide_close.click()
        except Exception:
            pass

        # 点击上传视频入口（占位符选择器）
        taobao_guanghe_logger.info(_msg("🧭", "寻找视频上传入口..."))
        entry = page.locator(_SELECTORS.upload_entry).first
        try:
            await entry.wait_for(state="visible", timeout=15000)
            await entry.click()
        except Exception as exc:
            raise RuntimeError(
                f"未找到淘宝光合视频上传入口 (选择器: {_SELECTORS.upload_entry});"
                f" 可能需要根据真实页面录制新选择器。原始错误: {exc}"
            ) from exc

    async def _upload_video(self, page: Page) -> None:
        taobao_guanghe_logger.info(_msg("📤", f"开始上传视频: {self.file_path}"))
        file_input = page.locator(_SELECTORS.video_upload_input).first
        try:
            await file_input.wait_for(state="attached", timeout=10000)
        except Exception as exc:
            raise RuntimeError(
                f"未找到淘宝光合视频文件 input (选择器: {_SELECTORS.video_upload_input});"
                f" 需要根据真实页面录制新选择器。原始错误: {exc}"
            ) from exc
        await file_input.set_input_files(self.file_path)

        # 等待视频处理完成
        taobao_guanghe_logger.info(_msg("⏳", "等待视频处理完成..."))
        for _ in range(120):  # 最多等 4 分钟
            try:
                done = page.locator(_SELECTORS.video_complete).first
                if await done.count() and await done.is_visible():
                    taobao_guanghe_logger.success(_msg("🥳", "视频已处理完成"))
                    return
            except Exception:
                pass
            await asyncio.sleep(2)
        raise RuntimeError("淘宝光合视频处理超时（>4 分钟），请检查网络或视频文件")

    async def _fill_title_and_tags(self, page: Page) -> None:
        taobao_guanghe_logger.info(_msg("📝", "填写标题和标签"))
        try:
            title_input = await self._wait_for_visible(page, _SELECTORS.title_input)
            await title_input.fill(self.title)
        except Exception as exc:
            raise RuntimeError(
                f"填写淘宝光合标题失败 (选择器: {_SELECTORS.title_input});"
                f" 需要录制新选择器。原始错误: {exc}"
            ) from exc

        for tag in self.tags:
            try:
                tag_input = page.locator(_SELECTORS.tag_input).first
                await tag_input.click()
                await page.keyboard.type(str(tag))
                add_btn = page.locator(_SELECTORS.add_tag_button).first
                if await add_btn.count():
                    await add_btn.click()
            except Exception as exc:
                taobao_guanghe_logger.warning(
                    _msg("😵", f"添加标签 {tag} 失败，跳过: {exc}")
                )

    async def _link_product(self, page: Page) -> None:
        if not (self.productLink and self.productTitle):
            return
        taobao_guanghe_logger.info(_msg("🛒", "关联商品"))
        try:
            link_btn = page.locator(_SELECTORS.link_product_button).first
            if await link_btn.count():
                await link_btn.click()
            link_input = page.locator(_SELECTORS.product_link_input).first
            await link_input.wait_for(state="visible", timeout=10000)
            await link_input.fill(self.productLink)
            title_input = page.locator(_SELECTORS.product_title_input).first
            if await title_input.count():
                await title_input.fill(self.productTitle)
        except Exception as exc:
            taobao_guanghe_logger.warning(
                _msg("😵", f"商品关联失败，跳过: {exc}")
            )

    async def _set_schedule_time(self, page: Page) -> None:
        if self.publish_date in (None, 0):
            return
        taobao_guanghe_logger.info(_msg("🕒", f"设置定时发布: {self.publish_date}"))
        try:
            scheduled = page.locator(_SELECTORS.publish_scheduled).first
            if await scheduled.count():
                await scheduled.click()
            date_input = page.locator(_SELECTORS.schedule_date_input).first
            await date_input.click()
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.type(self.publish_date.strftime("%Y-%m-%d"))
            await page.keyboard.press("Tab")
            time_input = page.locator(_SELECTORS.schedule_time_input).first
            await time_input.click()
            await page.keyboard.type(self.publish_date.strftime("%H:%M"))
            await page.keyboard.press("Enter")
        except Exception as exc:
            raise RuntimeError(
                f"设置淘宝光合定时发布时间失败: {exc}"
            ) from exc

    async def _click_publish(self, page: Page) -> None:
        taobao_guanghe_logger.info(_msg("🚀", "点击发布"))
        publish_btn = page.locator(_SELECTORS.publish_button).first
        try:
            await publish_btn.wait_for(state="visible", timeout=10000)
            await publish_btn.click()
        except Exception as exc:
            raise RuntimeError(
                f"未找到淘宝光合发布按钮 (选择器: {_SELECTORS.publish_button});"
                f" 需要录制新选择器。原始错误: {exc}"
            ) from exc

        # 二次确认
        try:
            confirm = page.locator(_SELECTORS.confirm_publish_button).first
            if await confirm.count() and await confirm.is_visible():
                await confirm.click()
        except Exception:
            pass

    async def upload(self, playwright: Playwright) -> None:
        await self.validate_upload_args()

        browser = await playwright.chromium.launch(**self._browser_launch_options())
        try:
            context = await browser.new_context(storage_state=self.account_file)
            context = await set_init_script(context)
            page = await context.new_page()

            await self._open_upload_page(page)
            await self._upload_video(page)
            await self._fill_title_and_tags(page)
            await self._link_product(page)
            await self._set_schedule_time(page)
            await self._click_publish(page)

            taobao_guanghe_logger.success(_msg("🥳", "淘宝光合视频发布完成"))
            # 刷新 cookie
            await asyncio.sleep(2)
            await context.storage_state(path=self.account_file)
        finally:
            await context.close()
            await browser.close()

    async def main(self) -> None:
        async with async_playwright() as playwright:
            await self.upload(playwright)
