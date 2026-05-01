# -*- coding: utf-8 -*-
from datetime import datetime

import asyncio
import inspect
import os
from pathlib import Path

from patchright.async_api import Locator, Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import DEBUG_MODE, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file
from utils.login_qrcode import save_data_url_image
from utils.log import douyin_logger
from utils.runtime_config import get_local_chrome_headless

DOUYIN_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
DOUYIN_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return

    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(success: bool, status: str, message: str, account_file: str, qrcode: dict | None = None, current_url: str = "") -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def _launch_douyin_browser(playwright: Playwright, *, headless: bool, executable_path: str | None = None):
    launch_kwargs = {"headless": headless}
    browser_path = executable_path or LOCAL_CHROME_PATH
    if browser_path:
        launch_kwargs["executable_path"] = browser_path
    else:
        launch_kwargs["channel"] = "chrome"
    return await playwright.chromium.launch(**launch_kwargs)


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await _launch_douyin_browser(playwright, headless=get_local_chrome_headless())
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            try:
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
            except Exception:
                return False

            if await page.get_by_text("手机号登录").count() or await page.get_by_text("扫码登录").count():
                return False

            return True
        finally:
            await browser.close()


async def douyin_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool | None = None):
    if headless is None:
        headless = get_local_chrome_headless()
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False
        douyin_logger.info(_msg("🥹", "cookie 失效了，准备打开浏览器重新登录"))
        result = await douyin_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def _extract_douyin_qrcode_src(page: Page) -> str:
    scan_login_tab = page.get_by_text("扫码登录", exact=True).first
    await scan_login_tab.wait_for(timeout=30000)

    qrcode_img = (
        scan_login_tab
        .locator("..")
        .locator("xpath=following-sibling::div[1]")
        .locator('img[aria-label="二维码"]')
        .first
    )

    if not await qrcode_img.count():
        qrcode_img = page.get_by_role("img", name="二维码").first

    await qrcode_img.wait_for(state="visible", timeout=30000)
    src = await qrcode_img.get_attribute("src")
    if not src:
        raise RuntimeError("未获取到抖音登录二维码地址")

    return src


async def _save_douyin_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_src = await _extract_douyin_qrcode_src(page)
    qrcode_path = save_data_url_image(qrcode_src, build_login_qrcode_path(account_file))
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            douyin_logger.info(_msg("🧹", f"临时二维码文件已清理: {previous_qrcode_path}"))
    douyin_logger.info(_msg("🖼️", f"二维码已经准备好啦，已保存到: {qrcode_path}"))
    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, "抖音APP")
    else:
        douyin_logger.warning(_msg("😵", f"终端没法完整显示二维码，请打开 {qrcode_path} 扫码"))
    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_douyin_login_completed(page: Page) -> bool:
    if not page.url.startswith("https://creator.douyin.com/creator-micro/home"):
        return False

    login_markers = [
        page.get_by_text("扫码登录", exact=True).first,
        page.get_by_text("手机号登录", exact=True).first,
        page.get_by_text("二维码失效", exact=True).first,
        page.get_by_role("img", name="二维码").first,
    ]

    for marker in login_markers:
        if not await marker.count():
            continue
        try:
            if await marker.is_visible():
                return False
        except Exception:
            continue

    return True


async def _wait_for_douyin_login(page: Page, account_file: str, qrcode_info: dict, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 100) -> dict:
    qrcode_path = Path(qrcode_info["image_path"])
    for _ in range(max_checks):
        if await _is_douyin_login_completed(page):
            douyin_logger.info(_msg("🥳", f"扫码成功，已经跳转到登录后页面: {page.url}"))
            return _build_login_result(True, "success", "抖音扫码登录成功", account_file, qrcode_info, page.url)

        expired_box = page.get_by_text("二维码失效", exact=True).locator("..").first
        if await expired_box.count() and await expired_box.is_visible():
            douyin_logger.warning(_msg("😵", "二维码失效了，小人马上去刷新"))
            await expired_box.click()
            await asyncio.sleep(1)
            qrcode_info = await _save_douyin_qrcode(page, account_file, qrcode_path, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])

        await asyncio.sleep(poll_interval)

    return _build_login_result(False, "timeout", "等待抖音扫码登录超时", account_file, qrcode_info, page.url)


async def douyin_cookie_gen(
    account_file,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
    headless: bool | None = None,
):
    if headless is None:
        headless = get_local_chrome_headless()
    async with async_playwright() as playwright:
        browser = await _launch_douyin_browser(playwright, headless=headless)
        context = await browser.new_context()
        context = await set_init_script(context)
        qrcode_path = None
        result = _build_login_result(False, "failed", "抖音登录失败", account_file)
        try:
            page = await context.new_page()
            await page.goto("https://creator.douyin.com/")
            qrcode_info = await _save_douyin_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])
            douyin_logger.info(_msg("🧍", "请扫码，小人正在耐心等待登录完成"))
            result = await _wait_for_douyin_login(
                page,
                account_file,
                qrcode_info,
                qrcode_callback=qrcode_callback,
                poll_interval=poll_interval,
                max_checks=max_checks,
            )
            if result["success"]:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                if not await cookie_auth(account_file):
                    result = _build_login_result(
                        False,
                        "cookie_invalid",
                        "抖音扫码流程结束，但 cookie 校验失败",
                        account_file,
                        qrcode_info,
                        page.url,
                    )
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                douyin_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                douyin_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()
        return result


class DouYinBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool | None = None,
    ):
        self.publish_date = publish_date
        self.account_file = account_file
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.date_format = "%Y年%m月%d日 %H:%M"
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = get_local_chrome_headless() if headless is None else headless

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成抖音登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成抖音登录: {self.account_file}")
        if self.publish_strategy not in {DOUYIN_PUBLISH_STRATEGY_IMMEDIATE, DOUYIN_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def set_schedule_time_douyin(self, page, publish_date):
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await asyncio.sleep(1)
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

    async def fill_title_and_description(self, page: Page, title: str, description: str, tags: list[str] | None = None):
        description_section = (
            page.get_by_text("作品描述", exact=True)
            .locator("xpath=ancestor::div[2]")
            .locator("xpath=following-sibling::div[1]")
        )

        title_input = description_section.locator('input[type="text"]').first
        await title_input.wait_for(state="visible", timeout=10000)
        await title_input.fill(title[:30])

        description_editor = description_section.locator('.zone-container[contenteditable="true"]').first
        await description_editor.wait_for(state="visible", timeout=10000)
        await description_editor.click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.press("Delete")
        await page.keyboard.type(description)

        for tag in tags or []:
            await page.keyboard.type(" #" + tag)
            await page.keyboard.press("Space")

    async def set_location(self, page: Page, location: str = ""):
        if not location:
            return
        await page.locator('div.semi-select span:has-text("输入地理位置")').click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    async def handle_product_dialog(self, page: Page, product_title: str):
        await page.wait_for_timeout(2000)
        await page.wait_for_selector('input[placeholder="请输入商品短标题"]', timeout=10000)
        short_title_input = page.locator('input[placeholder="请输入商品短标题"]')
        if not await short_title_input.count():
            douyin_logger.error(_msg("😵", "没找到商品短标题输入框"))
            return False

        product_title = product_title[:10]
        await short_title_input.fill(product_title)
        await page.wait_for_timeout(1000)

        finish_button = page.locator('button:has-text("完成编辑")')
        if "disabled" not in await finish_button.get_attribute("class"):
            await finish_button.click()
            douyin_logger.debug(_msg("🥳", "已点击“完成编辑”按钮"))
            await page.wait_for_selector(".semi-modal-content", state="hidden", timeout=5000)
            return True

        douyin_logger.error(_msg("😵", "“完成编辑”按钮是灰的，小人先把弹窗关掉"))
        cancel_button = page.locator('button:has-text("取消")')
        if await cancel_button.count():
            await cancel_button.click()
        else:
            close_button = page.locator(".semi-modal-close")
            await close_button.click()
        await page.wait_for_selector(".semi-modal-content", state="hidden", timeout=5000)
        return False

    async def set_product_link(self, page: Page, product_link: str, product_title: str):
        await page.wait_for_timeout(2000)
        try:
            await page.wait_for_selector("text=添加标签", timeout=10000)
            dropdown = page.get_by_text("添加标签").locator("..").locator("..").locator("..").locator(".semi-select").first
            if not await dropdown.count():
                douyin_logger.error(_msg("😵", "没找到标签下拉框"))
                return False
            douyin_logger.debug(_msg("🧍", "找到标签下拉框，小人准备选择“购物车”"))
            await dropdown.click()
            await page.wait_for_selector('[role="listbox"]', timeout=5000)
            await page.locator('[role="option"]:has-text("购物车")').click()
            douyin_logger.debug(_msg("🥳", "已经选中“购物车”"))

            await page.wait_for_selector('input[placeholder="粘贴商品链接"]', timeout=5000)
            input_field = page.locator('input[placeholder="粘贴商品链接"]')
            await input_field.fill(product_link)
            douyin_logger.debug(_msg("🔗", f"商品链接已经填好了: {product_link}"))

            add_button = page.locator('span:has-text("添加链接")')
            button_class = await add_button.get_attribute("class")
            if "disable" in button_class:
                douyin_logger.error(_msg("😵", "“添加链接”按钮现在点不了"))
                return False
            await add_button.click()
            douyin_logger.debug(_msg("🥳", "已点击“添加链接”按钮"))

            await page.wait_for_timeout(2000)
            error_modal = page.locator("text=未搜索到对应商品")
            if await error_modal.count():
                confirm_button = page.locator('button:has-text("确定")')
                await confirm_button.click()
                douyin_logger.error(_msg("😢", "这个商品链接无效"))
                return False

            if not await self.handle_product_dialog(page, product_title):
                return False

            douyin_logger.debug(_msg("🥳", "商品链接设置好了"))
            return True
        except Exception as e:
            douyin_logger.error(_msg("😢", f"设置商品链接时出错: {str(e)}"))
            return False


class DouYinVideo(DouYinBaseUploader):
    upload_page = "https://creator.douyin.com/creator-micro/content/upload"

    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        thumbnail_landscape_path=None,
        productLink="",
        productTitle="",
        declaration_info: dict | None = None,
        thumbnail_portrait_path=None,
        desc: str | None = None,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool | None = None,
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
        self.tags = tags
        self.thumbnail_landscape_path = thumbnail_landscape_path
        self.thumbnail_portrait_path = thumbnail_portrait_path
        self.productLink = productLink
        self.productTitle = productTitle
        self.declaration_info = declaration_info
        self.desc = desc or ""

    async def validate_upload_args(self):
        await self.validate_base_args()
        if (not self.title or not str(self.title).strip()) and (not self.desc or not str(self.desc).strip()):
            raise ValueError("视频模式下，title或者description是必须的")

        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_landscape_path:
            self.thumbnail_landscape_path = str(self.validate_image_file(self.thumbnail_landscape_path))
        if self.thumbnail_portrait_path:
            self.thumbnail_portrait_path = str(self.validate_image_file(self.thumbnail_portrait_path))

    async def handle_upload_error(self, page):
        douyin_logger.warning(_msg("😵", "视频上传摔了一跤，小人马上重新上传"))
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def handle_auto_video_cover(self, page):
        if await page.get_by_text("请设置封面后再发布").first.is_visible():
            douyin_logger.info(_msg("🧍", "发布前还得先把封面弄好"))
            recommend_cover = page.locator('[class^="recommendCover-"]').first
            if await recommend_cover.count():
                douyin_logger.info(_msg("🏃", "小人去选第一个推荐封面"))
                try:
                    await recommend_cover.click()
                    await asyncio.sleep(1)
                    confirm_text = "是否确认应用此封面？"
                    if await page.get_by_text(confirm_text).first.is_visible():
                        douyin_logger.info(_msg("🪟", f"弹出确认框了: {confirm_text}"))
                        await page.get_by_role("button", name="确定").click()
                        douyin_logger.info(_msg("🥳", "推荐封面已经应用"))
                        await asyncio.sleep(1)
                    douyin_logger.info(_msg("🥳", "封面选择流程完成"))
                    return True
                except Exception as e:
                    douyin_logger.warning(_msg("😵", f"推荐封面没选成功: {e}"))
        return False

    async def set_thumbnail(self, page: Page):
        if not self.thumbnail_landscape_path and not self.thumbnail_portrait_path:
            return

        douyin_logger.info(_msg("🏃", "小人正在设置视频封面"))
        open_cover_tip = "竖封面3:4" if self.thumbnail_portrait_path else "横封面4:3"
        cover_locator = await self._open_cover_editor(page, open_cover_tip)

        if self.thumbnail_portrait_path:
            await self._switch_cover_step(page, cover_locator, "设置竖封面")
            await self._upload_cover_image(page, cover_locator, self.thumbnail_portrait_path, "竖版封面")
            douyin_logger.info(_msg("🖼️", "竖版封面上传完成"))

        if self.thumbnail_landscape_path:
            await self._switch_cover_step(page, cover_locator, "设置横封面")
            await self._upload_cover_image(page, cover_locator, self.thumbnail_landscape_path, "横版封面")
            douyin_logger.info(_msg("🖼️", "横版封面上传完成"))

        await self._finish_cover_editor(cover_locator)
        douyin_logger.info(_msg("🥳", "视频封面设置完成"))

    async def _open_cover_editor(self, page: Page, cover_tip: str) -> Locator:
        cover_control = page.locator(f"div.coverControl-CjlzqC:has-text('{cover_tip}')").first
        await cover_control.wait_for(state="visible", timeout=30000)
        await cover_control.scroll_into_view_if_needed()
        await cover_control.locator("div.cover-Jg3T4p").first.click()

        cover_locator = page.locator("#dy-creator-content-modal-body").last
        try:
            await cover_locator.wait_for(state="visible", timeout=10000)
            return cover_locator
        except Exception:
            return await self._wait_for_cover_modal(page)

    async def _switch_cover_step(self, page: Page, cover_locator: Locator, step_text: str):
        button_candidates = []
        if step_text == "设置横封面":
            button_candidates.append(
                cover_locator.locator('div.buttons-BoCvr4 button:has-text("设置横封面")').first
            )

        button_candidates.extend(
            [
                cover_locator.get_by_role("button", name=step_text, exact=True).first,
                cover_locator.locator(f"div.steps-cgzd9T div.step-dXVbPX:has(span:text-is('{step_text}'))").first,
                cover_locator.get_by_text(step_text, exact=True).first,
            ]
        )

        for candidate in button_candidates:
            try:
                if not await candidate.count():
                    continue
                await candidate.scroll_into_view_if_needed()
                await candidate.click()
                await page.wait_for_timeout(500)
                return
            except Exception:
                continue

        if step_text == "设置竖封面":
            return

        raise RuntimeError(f"未找到封面步骤入口: {step_text}")

    async def _upload_cover_image(self, page: Page, cover_locator: Locator, image_path: str, cover_name: str):
        upload_container = cover_locator.locator("div.container-XzaV9h.upload-ZOJTUA").first
        if await upload_container.count():
            await upload_container.wait_for(state="visible", timeout=10000)
        else:
            upload_container = cover_locator.locator('div:has-text("上传封面")').first

        upload_input = upload_container.locator("input[type='file']").first if await upload_container.count() else None
        upload_drag_area = upload_container.locator("div.semi-upload-drag-area").first if await upload_container.count() else cover_locator.locator("div.semi-upload-drag-area").last
        if upload_input and await upload_input.count():
            await upload_input.set_input_files(image_path)
        elif await upload_drag_area.count():
            async with page.expect_file_chooser() as file_chooser_info:
                await upload_drag_area.click()
            file_chooser = await file_chooser_info.value
            await file_chooser.set_files(image_path)
        else:
            raise RuntimeError(f"未找到{cover_name}上传控件")

        await page.wait_for_timeout(2000)

    async def _finish_cover_editor(self, cover_locator: Locator):
        await cover_locator.locator('button:visible:has-text("完成")').click()
        try:
            await cover_locator.wait_for(state="hidden", timeout=10000)
        except Exception:
            await cover_locator.wait_for(state="detached", timeout=10000)

    async def _wait_for_cover_modal(self, page: Page) -> Locator:
        cover_locator = page.locator("#dy-creator-content-modal-body").last
        for _ in range(20):
            try:
                if await cover_locator.count() and await cover_locator.is_visible():
                    has_upload_area = await cover_locator.locator("div.container-XzaV9h.upload-ZOJTUA").count()
                    has_finish_button = await cover_locator.locator('button:has-text("完成")').count()
                    if has_upload_area or has_finish_button:
                        return cover_locator
            except Exception:
                pass
            await asyncio.sleep(0.5)

        modal_groups = [
            page.locator(".semi-modal-content"),
            page.locator("[role='dialog']"),
            page.locator(".semi-modal"),
        ]

        for _ in range(20):
            for group in modal_groups:
                count = await group.count()
                for index in range(count - 1, -1, -1):
                    modal = group.nth(index)
                    try:
                        if not await modal.is_visible():
                            continue
                    except Exception:
                        continue

                    has_upload_drag_area = await modal.locator("div.semi-upload-drag-area").count()
                    has_upload_input = await modal.locator("input[type='file']").count()
                    has_finish_button = await modal.locator('button:has-text("完成")').count()
                    if has_upload_drag_area or has_upload_input or has_finish_button:
                        return modal

            await asyncio.sleep(0.5)

        raise RuntimeError("未找到封面上传弹窗")

    async def set_declaration(self, page: Page, declaration_info: dict):
        """Restore Douyin declaration support from main while keeping the refactored uploader flow."""
        try:
            declaration_type = declaration_info.get("declaration_type")
            declaration_location = declaration_info.get("declaration_location")
            declaration_date = declaration_info.get("declaration_date")

            target = None
            if await page.get_by_text("添加声明").count():
                target = page.get_by_text("添加声明").first
            elif await page.get_by_role("button", name="添加声明").count():
                target = page.get_by_role("button", name="添加声明").first
            elif await page.get_by_text("自主声明").count():
                container = page.get_by_text("自主声明").first
                follow_button = container.locator("xpath=following::button[contains(., '添加声明')]").first
                if await follow_button.count():
                    target = follow_button

            if not target:
                douyin_logger.error("[-] 未找到添加声明入口")
                return False

            await target.scroll_into_view_if_needed()
            await target.click()
            await page.wait_for_timeout(500)

            option = None
            if await page.locator(f"label:has-text('{declaration_type}')").count():
                option = page.locator(f"label:has-text('{declaration_type}')").first
            elif await page.locator(f"[role='radio']:has-text('{declaration_type}')").count():
                option = page.locator(f"[role='radio']:has-text('{declaration_type}')").first
            elif await page.get_by_text(declaration_type).count():
                option = page.get_by_text(declaration_type).first

            if not option:
                douyin_logger.error("[-] 未找到声明选项")
                return False

            await option.scroll_into_view_if_needed()
            await option.click()

            if declaration_type == "内容自行拍摄":
                await self._handle_self_shooting_declaration(page, declaration_location, declaration_date)
            elif declaration_type == "内容取材网络":
                await self._handle_network_material_declaration(page)

            if await page.get_by_role("button", name="确定").count():
                await page.get_by_role("button", name="确定").click()
            elif await page.get_by_role("button", name="完成").count():
                await page.get_by_role("button", name="完成").click()
            await page.wait_for_timeout(500)
            return True
        except Exception as exc:
            douyin_logger.error(f"[-] 设置自主声明时出错: {exc}")
            return False

    async def _handle_self_shooting_declaration(self, page: Page, declaration_location, declaration_date):
        if declaration_location and isinstance(declaration_location, (list, tuple)):
            dialog = page.locator(".semi-modal-content").first if await page.locator(".semi-modal-content").count() else None
            trigger = None
            if dialog and await dialog.locator(".semi-cascader-selection").count():
                trigger = dialog.locator(".semi-cascader-selection").first
            elif await page.locator(".semi-cascader-selection").count():
                trigger = page.locator(".semi-cascader-selection").first
            elif dialog and await dialog.locator(".semi-cascader-arrow").count():
                trigger = dialog.locator(".semi-cascader-arrow").first
            elif await page.locator(".semi-cascader-arrow").count():
                trigger = page.locator(".semi-cascader-arrow").first

            if trigger:
                await trigger.scroll_into_view_if_needed()
                await trigger.click()
                await page.wait_for_timeout(300)
                for index, item in enumerate(declaration_location):
                    await page.wait_for_selector('[role="listbox"]', timeout=5000)
                    current_panel = page.locator('[role="listbox"]').last
                    option = None
                    if await current_panel.locator(f'[role="option"]:has-text("{item}")').count():
                        option = current_panel.locator(f'[role="option"]:has-text("{item}")').first
                    elif await current_panel.locator(f'.semi-cascader-option:has-text("{item}")').count():
                        option = current_panel.locator(f'.semi-cascader-option:has-text("{item}")').first
                    elif await page.get_by_role("option", name=item, exact=False).count():
                        option = page.get_by_role("option", name=item, exact=False).first
                    elif dialog and await dialog.locator(f'text="{item}"').count():
                        option = dialog.locator(f'text="{item}"').first
                    elif await page.get_by_text(item).count():
                        option = page.get_by_text(item).first

                    if not option:
                        douyin_logger.error(f"[-] 未找到地点选项: {item}")
                        continue

                    try:
                        await option.scroll_into_view_if_needed()
                        try:
                            await option.click()
                        except Exception:
                            await option.hover()
                            await page.wait_for_timeout(150)
                            await option.click()
                        if index < len(declaration_location) - 1:
                            await page.wait_for_timeout(300)
                    except Exception as exc:
                        douyin_logger.error(f"[-] 点击地点选项失败: {item}, {exc}")

        if declaration_date and await page.get_by_placeholder("设置拍摄日期").count():
            picker = page.get_by_placeholder("设置拍摄日期").first
            await picker.scroll_into_view_if_needed()
            await picker.click()
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.type(str(declaration_date))
            await page.keyboard.press("Enter")

    async def _handle_network_material_declaration(self, page: Page):
        candidates = [
            page.locator("label:has-text('取材站外')").first,
            page.locator("[role='radio']:has-text('取材站外')").first,
            page.get_by_text("取材站外").first,
        ]
        for candidate in candidates:
            try:
                if not await candidate.count():
                    continue
                await candidate.scroll_into_view_if_needed()
                inner = candidate.locator(".semi-radio-inner")
                if await inner.count():
                    await inner.click()
                else:
                    await candidate.click()
                return True
            except Exception:
                continue
        douyin_logger.error("[-] 未能点击到'取材站外'单选项")
        return False

    async def upload(self, playwright: Playwright) -> None:
        douyin_logger.info(_msg("🧍", "小人先检查 cookie、视频文件、封面和发布时间"))
        await self.validate_upload_args()
        douyin_logger.info(_msg("🥳", "上传前检查通过"))

        browser = await _launch_douyin_browser(
            playwright,
            headless=self.headless,
            executable_path=self.local_executable_path,
        )
        context = await browser.new_context(
            storage_state=f"{self.account_file}",
            permissions=["geolocation"],
        )
        context = await set_init_script(context)

        page = await context.new_page()
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        douyin_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}.mp4"))
        douyin_logger.info(_msg("🧭", "小人正在赶往上传主页"))
        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")
        await page.locator("div[class^='container'] input").set_input_files(self.file_path)

        while True:
            try:
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page",
                    timeout=3000,
                )
                douyin_logger.info(_msg("🥳", "已经进入 version_1 发布页面"))
                break
            except Exception:
                try:
                    await page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                        timeout=3000,
                    )
                    douyin_logger.info(_msg("🥳", "已经进入 version_2 发布页面"))
                    break
                except Exception:
                    douyin_logger.debug(_msg("🧍", "还没进到视频发布页面，小人继续等一会"))
                    await asyncio.sleep(0.5)

        await asyncio.sleep(1)
        douyin_logger.info(_msg("✍️", "小人开始填标题、描述和话题"))
        await self.fill_title_and_description(page, self.title, self.desc, self.tags)
        douyin_logger.info(_msg("🏷️", f"小人一共贴了 {len(self.tags)} 个话题"))

        while True:
            try:
                number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                if number > 0:
                    douyin_logger.success(_msg("🥳", "视频已经传完啦"))
                    break
                douyin_logger.info(_msg("🏃", "小人正在努力上传视频"))
                await asyncio.sleep(2)
                if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                    douyin_logger.error(_msg("😵", "检测到上传失败，小人准备重试"))
                    await self.handle_upload_error(page)
            except Exception:
                douyin_logger.debug(_msg("🧍", "小人还在等视频上传完成"))
                await asyncio.sleep(2)

        if self.productLink and self.productTitle:
            douyin_logger.info(_msg("🛒", "小人正在设置商品链接"))
            douyin_logger.debug(_msg("🧍", "先等一下页面把商品弹窗相关控件准备好"))
            await page.wait_for_timeout(3000)
            await self.set_product_link(page, self.productLink, self.productTitle)
            douyin_logger.info(_msg("🥳", "商品链接设置完成"))

        await self.set_thumbnail(page)

        third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
        if await page.locator(third_part_element).count():
            if "semi-switch-checked" not in await page.eval_on_selector(third_part_element, "div => div.className"):
                await page.locator(third_part_element).locator("input.semi-switch-native-control").click()

        if self.declaration_info:
            douyin_logger.info(f"[+] 开始设置自主声明: {self.declaration_info}")
            await self.set_declaration(page, self.declaration_info)

        if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        while True:
            try:
                publish_button = page.get_by_role("button", name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/manage**",
                    timeout=3000,
                )
                douyin_logger.success(_msg("🥳", "视频发布成功，小人开心收工"))
                break
            except Exception:
                await self.handle_auto_video_cover(page)
                douyin_logger.info(_msg("🏃", "小人正在冲刺发布视频"))
                if self.debug:
                    await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

        await context.storage_state(path=self.account_file)
        douyin_logger.success(_msg("🥳", "cookie 更新完毕"))
        await asyncio.sleep(2)
        await context.close()
        await browser.close()

    async def douyin_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.douyin_upload_video()


class DouYinNote(DouYinBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool | None = None,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
        )
        self.image_paths = image_paths
        self.note = note or ""
        self.title = title or (self.note[:30] if self.note else "")
        self.tags = tags or []

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("图文模式下，title 是必须的")
        if not self.image_paths:
            raise ValueError("图文模式下，图片是必须的")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        if len(self.image_paths) > 35:
            raise ValueError("图文模式下最多只支持上传 35 张图片")

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def upload_note_content(self, page: Page) -> None:
        douyin_logger.info(_msg("🏃", f"小人开始搬运图文，共 {len(self.image_paths)} 张图片"))
        douyin_logger.info(_msg("🔀", "小人正在切换到图文发布"))
        await page.get_by_text("发布图文", exact=True).click()
        await page.wait_for_timeout(1000)

        douyin_logger.info(_msg("📤", "小人正在上传图片"))
        await page.locator("div[class^='container'] input[accept*='image']").set_input_files(self.image_paths)

        while True:
            try:
                await page.wait_for_url(
                    "**/creator-micro/content/post/image?**",
                    timeout=3000,
                )
                douyin_logger.info(_msg("🥳", "已经进入图文发布页面"))
                break
            except Exception:
                douyin_logger.debug(_msg("🧍", "小人还在等图片上传完成"))
                await asyncio.sleep(0.5)

        await asyncio.sleep(1)
        douyin_logger.info(_msg("✍️", "小人开始填标题、描述和话题"))
        await self.fill_title_and_description(page, self.title, self.note, self.tags)
        douyin_logger.info(_msg("🏷️", f"小人一共贴了 {len(self.tags)} 个话题"))

        if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        while True:
            try:
                publish_button = page.get_by_role("button", name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()
                await page.wait_for_url(
                    "**/creator-micro/content/manage?enter_from=publish**",
                    timeout=3000,
                )
                douyin_logger.success(_msg("🥳", "图文发布成功，小人开心收工"))
                break
            except Exception:
                douyin_logger.info(_msg("🏃", "小人正在冲刺发布图文"))
                await asyncio.sleep(0.5)

    async def upload(self, playwright: Playwright) -> None:
        douyin_logger.info(_msg("🧍", "小人先检查 cookie、图片和发布时间"))
        await self.validate_upload_args()
        douyin_logger.info(_msg("🥳", "图文上传前检查通过"))

        browser = await _launch_douyin_browser(
            playwright,
            headless=self.headless,
            executable_path=self.local_executable_path,
        )
        context = await browser.new_context(
            storage_state=f"{self.account_file}",
            permissions=["geolocation"],
        )
        context = await set_init_script(context)

        upload_success = False
        try:
            page = await context.new_page()
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            douyin_logger.info(_msg("🧭", "小人正在赶往图文发布页"))
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")

            await self.upload_note_content(page)
            upload_success = True
        finally:
            if upload_success:
                await context.storage_state(path=self.account_file)
                douyin_logger.success(_msg("🥳", "cookie 更新完毕"))
                await asyncio.sleep(2)
            await context.close()
            await browser.close()

    async def douyin_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
