# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
import os
import time
from datetime import datetime
from pathlib import Path

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import BASE_DIR, DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import tencent_logger

TENCENT_LOGIN_URL = "https://channels.weixin.qq.com"
TENCENT_UPLOAD_URL = "https://channels.weixin.qq.com/platform/post/create"
TENCENT_MANAGE_URL = "https://channels.weixin.qq.com/platform/post/list"
TENCENT_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
TENCENT_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _resolve_account_file(account_file: str | Path) -> str:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return str(path)

    if len(path.parts) == 1:
        return str((Path(BASE_DIR) / "cookies" / "tencent_uploader" / path).resolve())

    return str(path.resolve())


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return

    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(
    success: bool,
    status: str,
    message: str,
    account_file: str,
    qrcode: dict | None = None,
    current_url: str = "",
) -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


def _build_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {"headless": headless}
    if LOCAL_CHROME_PATH:
        launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
    return launch_kwargs


def _resolve_persistent_profile_dir(account_file: str | Path) -> str:
    account_path = Path(_resolve_account_file(account_file))
    account_name = account_path.stem.removeprefix("tencent_") or "default"
    return str((Path(BASE_DIR) / "cookies" / "tencent_profiles" / account_name).resolve())


def _has_persistent_profile(account_file: str | Path) -> bool:
    profile_dir = Path(_resolve_persistent_profile_dir(account_file))
    return profile_dir.exists() and any(profile_dir.iterdir())


def _has_tencent_login_state(account_file: str | Path) -> bool:
    account_file = _resolve_account_file(account_file)
    return Path(account_file).exists() or _has_persistent_profile(account_file)


async def _launch_tencent_context(
    playwright: Playwright,
    account_file: str | Path,
    headless: bool,
    storage_state: bool = True,
    persistent: bool | None = None,
):
    account_file = _resolve_account_file(account_file)
    if persistent is None:
        persistent = _has_persistent_profile(account_file)

    if persistent:
        profile_dir = Path(_resolve_persistent_profile_dir(account_file))
        profile_dir.mkdir(parents=True, exist_ok=True)
        context = await playwright.chromium.launch_persistent_context(
            str(profile_dir),
            **_build_launch_kwargs(headless=headless),
        )
        return context, None

    browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
    try:
        if storage_state:
            context = await browser.new_context(storage_state=account_file)
        else:
            context = await browser.new_context()
        return context, browser
    except Exception:
        await browser.close()
        raise


def _get_qrcode_utils():
    from utils.login_qrcode import build_login_qrcode_path
    from utils.login_qrcode import decode_qrcode_from_path
    from utils.login_qrcode import print_terminal_qrcode
    from utils.login_qrcode import remove_qrcode_file
    from utils.login_qrcode import save_data_url_image

    return {
        "build_login_qrcode_path": build_login_qrcode_path,
        "decode_qrcode_from_path": decode_qrcode_from_path,
        "print_terminal_qrcode": print_terminal_qrcode,
        "remove_qrcode_file": remove_qrcode_file,
        "save_data_url_image": save_data_url_image,
    }


def format_str_for_short_title(origin_title: str) -> str:
    allowed_special_chars = "《》“”:+?%°"
    filtered_chars = [char if char.isalnum() or char in allowed_special_chars else " " if char == "," else "" for char in origin_title]
    formatted_string = "".join(filtered_chars)

    if len(formatted_string) > 16:
        formatted_string = formatted_string[:16]
    elif len(formatted_string) < 6:
        formatted_string += " " * (6 - len(formatted_string))

    return formatted_string


async def cookie_auth(account_file, headless: bool = True):
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        context = None
        browser = None
        try:
            context, browser = await _launch_tencent_context(playwright, account_file, headless=headless)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(TENCENT_UPLOAD_URL)
            await page.wait_for_url(TENCENT_UPLOAD_URL, timeout=5000)

            # 视频号助手 SPA 异步重定向：session 无效时先短暂停在 upload URL，
            # 然后跳转到 /login.html。等待重定向完成后再判断。
            await asyncio.sleep(3)
            if "login" in page.url:
                tencent_logger.info(_msg("🥹", "cookie 已失效，得重新登录一下"))
                return False

            login_markers = [
                page.get_by_text("扫码登录", exact=True).first,
                page.get_by_text("发表视频", exact=True).first,
                page.get_by_role("button", name="发表").first,
            ]

            if await login_markers[0].count():
                tencent_logger.info(_msg("🥹", "cookie 已失效，得重新登录一下"))
                return False

            tencent_logger.success(_msg("🥳", "cookie 有效"))
            return True
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"cookie 校验时出错，按失效处理: {exc}"))
            return False
        finally:
            if context:
                await context.close()
            if browser:
                await browser.close()


async def _find_tencent_qrcode(page: Page):
    selector_candidates = [
        "img.js_qrcode_img:visible",
        "img[src*='/connect/qrcode/']:visible",
        "img.qrcode:visible",
        "div.login-qrcode-wrap img.qrcode",
        "div.qrcode-wrap img.qrcode",
        "img.qrcode",
        'img[src^="data:image/"]',
    ]

    async def find_in_frame(frame):
        for selector in selector_candidates:
            qr_code_img = frame.locator(selector).first
            try:
                if not await qr_code_img.count() or not await qr_code_img.is_visible():
                    continue
                src = await qr_code_img.get_attribute("src")
                if src:
                    return qr_code_img, src
            except Exception:
                continue
        return None

    # The login iframe is ready before the QR img src is populated. Poll every frame
    # instead of reading once after "attached", otherwise today's run races and fails.
    for _ in range(20):
        for frame in page.frames:
            qrcode = await find_in_frame(frame)
            if qrcode:
                return qrcode
        await asyncio.sleep(1)

    raise RuntimeError("未获取到视频号登录二维码地址")


async def _extract_tencent_qrcode_src(page: Page) -> str:
    _, src = await _find_tencent_qrcode(page)
    return src


async def _save_tencent_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_utils = _get_qrcode_utils()
    qrcode_img, qrcode_src = await _find_tencent_qrcode(page)
    qrcode_path = qrcode_utils["build_login_qrcode_path"](account_file, suffix="tencent_login_qrcode")
    if qrcode_src.startswith("data:image/"):
        qrcode_path = qrcode_utils["save_data_url_image"](qrcode_src, qrcode_path)
    else:
        # open.weixin.qq.com sometimes exposes a relative /connect/qrcode/... img;
        # screenshot the visible QR element instead of fetching a cookie-bound URL.
        qrcode_path.parent.mkdir(parents=True, exist_ok=True)
        await qrcode_img.screenshot(path=str(qrcode_path))
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if qrcode_utils["remove_qrcode_file"](previous_qrcode_path):
            tencent_logger.info(_msg("🧹", f"临时二维码文件已清理: {previous_qrcode_path}"))

    tencent_logger.info(_msg("🖼️", f"二维码已经准备好啦，已保存到: {qrcode_path}"))
    qrcode_content = qrcode_utils["decode_qrcode_from_path"](qrcode_path)
    if qrcode_content:
        qrcode_utils["print_terminal_qrcode"](qrcode_content, qrcode_path, "微信")
    else:
        tencent_logger.warning(
            _msg(
                "😵",
                f"没能从二维码图片里解析出可打印内容，所以这次没法在终端重绘二维码；请直接打开 {qrcode_path} 扫码",
            )
        )

    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src if qrcode_src.startswith("data:image/") else None,
        "image_src": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_tencent_login_completed(page: Page) -> bool:
    publish_markers = [
        page.locator('div:has-text("发表视频")').first,
        page.locator('button:has-text("发表")').first,
        page.locator('button:has-text("保存草稿")').first,
    ]
    for marker in publish_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return True
        except Exception:
            continue

    if not (page.url.startswith(TENCENT_UPLOAD_URL) or page.url.startswith(TENCENT_MANAGE_URL)):
        return False

    login_markers = [
        page.locator("div.login-qrcode-wrap").first,
        page.locator("div.qrcode-wrap").first,
        page.locator("img.qrcode").first,
        page.locator('span:has-text("微信扫码登录 视频号助手")').first,
    ]
    for marker in login_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return False
        except Exception:
            continue

    return True


async def _is_tencent_qrcode_expired(page: Page) -> bool:
    tip_selectors = [
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for frame in page.frames:
        for selector in tip_selectors:
            tip = frame.locator(selector).first
            try:
                if await tip.count() and await tip.is_visible():
                    return True
            except Exception:
                continue
    return False


async def _is_tencent_qrcode_scanned(page: Page) -> bool:
    scanned_tips = [
        'div.qr-tip div:has-text("已扫码")',
        'div.qr-tip div:has-text("需在手机上进行确认")',
    ]
    for frame in page.frames:
        for selector in scanned_tips:
            tip = frame.locator(selector).first
            try:
                if await tip.count() and await tip.is_visible():
                    return True
            except Exception:
                continue
    return False


async def _refresh_tencent_qrcode(page: Page) -> None:
    visible_refresh_selectors = [
        "div.login-qrcode-wrap div.mask.show div.refresh-wrap",
        "div.login-qrcode-wrap div.mask.show .refresh-wrap",
    ]
    for frame in page.frames:
        for selector in visible_refresh_selectors:
            refresh_wrap = frame.locator(selector).first
            try:
                if not await refresh_wrap.count() or not await refresh_wrap.is_visible():
                    continue
                await refresh_wrap.click()
                return
            except Exception:
                continue

    tip_selectors = [
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for frame in page.frames:
        for selector in tip_selectors:
            tip = frame.locator(selector).first
            try:
                if not await tip.count() or not await tip.is_visible():
                    continue
                refresh_wrap = tip.locator("xpath=ancestor::div[contains(@class, 'refresh-wrap')]").first
                if await refresh_wrap.count():
                    await refresh_wrap.click()
                else:
                    await tip.click()
                return
            except Exception:
                continue

    for frame in page.frames:
        fallback_refresh = frame.locator("div.login-qrcode-wrap div.refresh-wrap").first
        if await fallback_refresh.count():
            await fallback_refresh.click()
            return

    raise RuntimeError("未找到可点击的视频号二维码刷新区域")


async def _wait_for_tencent_login(
    page: Page,
    account_file: str,
    qrcode_info: dict,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
    refresh_seconds: int | None = 90,
) -> dict:
    qrcode_path = Path(qrcode_info["image_path"])
    scanned_logged = False
    last_qrcode_refresh = time.monotonic()
    for _ in range(max_checks):
        if await _is_tencent_login_completed(page):
            tencent_logger.info(_msg("🥳", f"扫码成功，已经跳转到登录后页面: {page.url}"))
            return _build_login_result(True, "success", "视频号扫码登录成功", account_file, qrcode_info, page.url)

        if not scanned_logged and await _is_tencent_qrcode_scanned(page):
            tencent_logger.info(_msg("📱", "已经扫码啦，还差手机端确认一下"))
            scanned_logged = True

        if await _is_tencent_qrcode_expired(page):
            tencent_logger.warning(_msg("😵", "二维码失效了，小人马上去刷新"))
            await _refresh_tencent_qrcode(page)
            await asyncio.sleep(1)
            qrcode_info = await _save_tencent_qrcode(
                page,
                account_file,
                previous_qrcode_path=qrcode_path,
                qrcode_callback=qrcode_callback,
            )
            qrcode_path = Path(qrcode_info["image_path"])
            last_qrcode_refresh = time.monotonic()

        if (
            refresh_seconds is not None
            and time.monotonic() - last_qrcode_refresh >= refresh_seconds
        ):
            tencent_logger.warning(_msg("⏰", "二维码可能已过期，按时间兜底刷新并重新保存"))
            try:
                await _refresh_tencent_qrcode(page)
            except Exception as exc:
                tencent_logger.warning(_msg("😵", f"点击刷新失败，改为重载登录页: {exc}"))
                await page.goto(TENCENT_LOGIN_URL, timeout=120000, wait_until="domcontentloaded")
            await asyncio.sleep(1)
            qrcode_info = await _save_tencent_qrcode(
                page,
                account_file,
                previous_qrcode_path=qrcode_path,
                qrcode_callback=qrcode_callback,
            )
            qrcode_path = Path(qrcode_info["image_path"])
            last_qrcode_refresh = time.monotonic()

        await asyncio.sleep(poll_interval)

    return _build_login_result(False, "timeout", "等待视频号扫码登录超时", account_file, qrcode_info, page.url)


async def tencent_cookie_gen(
    account_file,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        context = None
        browser = None
        context, browser = await _launch_tencent_context(
            playwright,
            account_file,
            headless=headless,
            storage_state=False,
            persistent=True,
        )
        context = await set_init_script(context)
        qrcode_path = None
        result = _build_login_result(False, "failed", "视频号登录失败", account_file)
        try:
            page = await context.new_page()
            await page.goto(TENCENT_LOGIN_URL)
            qrcode_info = await _save_tencent_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])
            tencent_logger.info(_msg("🧍", "请扫码，小人正在耐心等待登录完成"))
            result = await _wait_for_tencent_login(
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
                if not await cookie_auth(account_file, headless=headless):
                    result = _build_login_result(
                        False,
                        "cookie_invalid",
                        "视频号扫码流程结束，但 cookie 校验失败",
                        account_file,
                        qrcode_info,
                        page.url,
                    )
            return result
        except Exception as exc:
            result = _build_login_result(
                False,
                "failed",
                str(exc),
                account_file,
                current_url=page.url if "page" in locals() else "",
            )
            return result
        finally:
            qrcode_utils = _get_qrcode_utils()
            if qrcode_utils["remove_qrcode_file"](qrcode_path):
                tencent_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                tencent_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            if context:
                await context.close()
            if browser:
                await browser.close()


async def tencent_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    if not _has_tencent_login_state(account_file) or not await cookie_auth(account_file, headless=headless):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False

        tencent_logger.info(_msg("🥹", "cookie 失效了，准备打开浏览器重新登录"))
        result = await tencent_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def get_tencent_cookie(account_file, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    return await tencent_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)


async def weixin_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    return await tencent_setup(
        account_file,
        handle=handle,
        return_detail=return_detail,
        qrcode_callback=qrcode_callback,
        headless=headless,
    )


class TencentBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.publish_date = publish_date
        self.account_file = _resolve_account_file(account_file)
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH

    async def validate_base_args(self):
        if not _has_tencent_login_state(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成视频号登录: {self.account_file}")
        if not await cookie_auth(self.account_file, headless=self.headless):
            raise RuntimeError(f"cookie文件已失效，请先完成视频号登录: {self.account_file}")
        if self.publish_strategy not in {TENCENT_PUBLISH_STRATEGY_IMMEDIATE, TENCENT_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def set_schedule_time_tencent(self, page: Page, publish_date: datetime):
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()
        await page.click('input[placeholder="请选择发表时间"]')

        current_month = publish_date.strftime("%m月")
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')
        if page_month != current_month:
            await page.click("button.weui-desktop-btn__icon__right")

        elements = await page.query_selector_all("table.weui-desktop-picker__table a")
        for element in elements:
            if "weui-desktop-picker__disabled" in await element.evaluate("el => el.className"):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        await page.click('input[placeholder="请选择时间"]')
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(publish_date.strftime("%H"))
        await page.keyboard.press("Enter")  # 确认小时并关闭时间下拉
        await page.wait_for_timeout(500)
        # 收起时间选择浮层：直接点描述区可能被 weui-desktop-dialog 遮挡，做容错
        try:
            await page.locator("div.input-editor").click(timeout=5000)
        except Exception:
            await page.keyboard.press("Escape")

    async def open_upload_page(self, page: Page) -> None:
        await page.goto(TENCENT_UPLOAD_URL, timeout=120000, wait_until="domcontentloaded")
        await page.wait_for_url(TENCENT_UPLOAD_URL, timeout=120000)

    async def upload_video_file(self, page: Page, file_path: str) -> None:
        async def find_file_input():
            for fr in page.frames:  # 主 frame + 所有 iframe（视频号编辑器可能在 iframe 内）
                try:
                    fi = fr.locator('input[type="file"]')
                    if await fi.count():
                        return fi.first
                except Exception:
                    continue
            return None

        fi = await find_file_input()
        if fi is None:
            # 助手落在首页：先点「发表视频」唤出编辑器与上传控件
            publish_btn = page.get_by_text("发表视频").first
            if await publish_btn.count():
                await publish_btn.click()
                await asyncio.sleep(3)
            for _ in range(20):
                fi = await find_file_input()
                if fi is not None:
                    break
                await asyncio.sleep(1)
        if fi is None:
            # 最后尝试：点"从相册选择"区域，它可能触发原生文件选择器
            album_selectors = [
                page.locator('div:has-text("从相册选择")'),
                page.locator('div:has-text("上传视频")'),
                page.locator('div.upload-area'),
                page.locator('div:has-text("选择文件")'),
            ]
            for sel in album_selectors:
                try:
                    if await sel.count():
                        await sel.first.click()
                        await asyncio.sleep(2)
                        fi = await find_file_input()
                        if fi is not None:
                            break
                except Exception:
                    continue
        if fi is None:
            raise RuntimeError("未找到视频号文件上传框")
        await fi.set_input_files(file_path)

    async def set_short_title(self, page: Page, title: str, short_title: str | None = None) -> None:
        short_title_element = (
            page.get_by_text("短标题", exact=True)
            .locator("..")
            .locator("xpath=following-sibling::div")
            .locator('span input[type="text"]')
        )
        if await short_title_element.count():
            await short_title_element.fill(short_title or format_str_for_short_title(title))

    async def fill_title_and_tags(self, page: Page) -> None:
        await page.locator("div.input-editor").click()
        await page.keyboard.type(self.title)
        await page.keyboard.press("Enter")
        for tag in self.tags:
            await page.keyboard.type("#" + tag)
            await page.keyboard.press("Space")
        tencent_logger.info(_msg("🏷️", f"成功添加 hashtag: {len(self.tags)}"))

    async def fill_description(self, page: Page) -> None:
        await page.keyboard.press("Enter")
        await page.keyboard.type(self.desc)
        tencent_logger.info(_msg("🏷️", f"成功添加 desc: {len(self.desc)}"))

    async def apply_collection(self, page: Page) -> None:
        collection_elements = (
            page.get_by_text("添加到合集")
            .locator("xpath=following-sibling::div")
            .locator(".option-list-wrap > div")
        )
        if await collection_elements.count() > 1:
            await page.get_by_text("添加到合集").locator("xpath=following-sibling::div").click()
            await collection_elements.first.click()

    async def apply_original_statement(self, page: Page) -> None:
        original_set = False
        if await page.get_by_label("视频为原创").count():
            await page.get_by_label("视频为原创").check()
            original_set = True

        try:
            label_locator = await page.locator('label:has-text("我已阅读并同意 《视频号原创声明使用条款》")').is_visible()
        except Exception:
            label_locator = False

        if label_locator:
            await page.get_by_label("我已阅读并同意 《视频号原创声明使用条款》").check()
            await page.get_by_role("button", name="声明原创").click()
            original_set = True

        declaration_entry = page.locator(
            'div.label span:has-text("声明原创"), '
            'div:has-text("声明原创"):has(input.ant-checkbox-input), '
            'div:has-text("原创声明"):has(input.ant-checkbox-input)'
        ).first
        if await declaration_entry.count():
            original_checkbox = page.locator("div.declare-original-checkbox input.ant-checkbox-input").first
            if await original_checkbox.count() and not await original_checkbox.is_disabled():
                await original_checkbox.click()
                await page.wait_for_timeout(500)
                checked_locator = page.locator(
                    "div.declare-original-dialog "
                    "label.ant-checkbox-wrapper.ant-checkbox-wrapper-checked:visible"
                )
                if not await checked_locator.count():
                    await page.locator("div.declare-original-dialog input.ant-checkbox-input:visible").first.click()

            original_type_form = page.locator('div.original-type-form > div.form-label:has-text("原创类型"):visible')
            if await original_type_form.count():
                category = getattr(self, "category", None)
                await page.locator("div.form-content:visible").click()
                option = None
                if category:
                    option = page.locator(
                        "ul.weui-desktop-dropdown__list "
                        f'li.weui-desktop-dropdown__list-ele:has-text("{category}")'
                    ).first
                    if not await option.count():
                        option = None
                if option is None:
                    option = page.locator(
                        "ul.weui-desktop-dropdown__list "
                        "li.weui-desktop-dropdown__list-ele:visible"
                    ).first
                if await option.count():
                    await option.click()
                await page.wait_for_timeout(1000)

            declare_button = page.locator('button:has-text("声明原创"):visible')
            if await declare_button.count():
                await declare_button.first.click()
                original_set = True
                await page.wait_for_timeout(1000)

        if not original_set:
            for original_text in ("声明原创", "原创声明", "视频为原创"):
                try:
                    modern_original = page.locator(f'text="{original_text}"').first
                    if await modern_original.count() and await modern_original.is_visible():
                        await modern_original.click()
                        original_set = True
                        await page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue

        content_declaration = page.locator('text="内容声明"').first
        try:
            if await content_declaration.count() and await content_declaration.is_visible():
                await content_declaration.click()
                for option_text in ("无需声明", "不声明", "无"):
                    option = page.locator(f'text="{option_text}"').first
                    if await option.count() and await option.is_visible():
                        await option.click()
                        tencent_logger.info(_msg("🧾", f"内容声明已选择: {option_text}"))
                        break
            else:
                tencent_logger.info(_msg("🧾", "当前页面未发现内容声明字段"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"内容声明设置失败，继续前先人工确认页面: {exc}"))

        if not original_set:
            try:
                diagnostic_path = Path(BASE_DIR) / "debug_tencent_original_missing.png"
                await page.screenshot(path=str(diagnostic_path), full_page=True)
                visible_text = (await page.locator("body").first.inner_text())[-4000:]
                tencent_logger.warning(_msg("😵", f"未确认声明原创，诊断截图: {diagnostic_path}"))
                tencent_logger.warning(_msg("🧾", f"页面末尾文本: {visible_text}"))
            except Exception as exc:
                tencent_logger.warning(_msg("😵", f"生成原创声明诊断信息失败: {exc}"))
            # 视频号「声明原创」为可选项：页面无对应入口时跳过并继续发布，而非中止。
            tencent_logger.warning(_msg("📭", "本视频未声明原创（页面无入口或为可选项），跳过并继续发布"))

    async def wait_for_upload_complete(self, page: Page) -> None:
        # ponytail: 2min timeout — WeChat cover generation can stall indefinitely
        max_wait = 120
        waited = 0
        while waited < max_wait:
            try:
                publish_button = page.get_by_role("button", name="发表")
                button_class = await publish_button.get_attribute("class")
                if button_class and "weui-desktop-btn_disabled" not in button_class:
                    tencent_logger.info(_msg("🥳", "视频上传完毕"))
                    break

                tencent_logger.info(_msg("🏃", "正在上传视频中..."))
                await asyncio.sleep(2)
                waited += 2

                upload_failed = await page.locator("div.status-msg.error").count()
                delete_button = await page.locator('div.media-status-content div.tag-inner:has-text("删除")').count()
                if upload_failed and delete_button:
                    tencent_logger.error(_msg("😵", "发现上传出错了，准备重试"))
                    await self.handle_upload_error(page)
            except Exception:
                tencent_logger.info(_msg("🏃", "正在上传视频中..."))
                await asyncio.sleep(2)
                waited += 2
        else:
            tencent_logger.warning(_msg("⏰", f"等待上传完成超时({max_wait}s)，尝试保存草稿"))
            # 封面生成卡住时发表按钮一直 disabled，但保存草稿可用
            draft_btn = page.locator('button:has-text("保存草稿"):visible')
            if await draft_btn.count():
                cls = await draft_btn.first.get_attribute("class") or ""
                if "disabled" not in cls:
                    await draft_btn.first.click()
                    await asyncio.sleep(3)
                    tencent_logger.success(_msg("🥳", "视频草稿保存成功（封面生成超时）"))
                    self.is_draft = True
                    self._draft_saved = True
                    return
            tencent_logger.warning(_msg("😵", "保存草稿也失败，尝试直接发表"))

    async def submit_publish(self, page: Page) -> None:
        if getattr(self, "_draft_saved", False):
            tencent_logger.info(_msg("🥳", "草稿已保存，跳过发表步骤"))
            return

        await page.evaluate(
            "() => document.querySelectorAll('.share-card,.form-item.flex-start,.weui-desktop-dialog__wrp').forEach(e => e.remove())"
        )
        is_draft = getattr(self, "is_draft", False)
        label = "保存草稿" if is_draft else "发表"
        button = page.locator(f'div.form-btns button:has-text("{label}")')
        if not await button.count():
            raise RuntimeError(f"未找到视频号{label}按钮")

        await page.evaluate("(el) => el.click()", await button.element_handle())
        try:
            await page.wait_for_url("**/post/list**" if is_draft else TENCENT_MANAGE_URL, timeout=15000)
        except Exception as exc:
            if "post/list" in page.url or (not is_draft and TENCENT_MANAGE_URL in page.url):
                pass
            else:
                raise RuntimeError(f"视频号{label}已提交但页面未确认，禁止重复点击；请到后台核验") from exc

        tencent_logger.success(_msg("🥳", "视频草稿保存成功" if is_draft else "视频发布成功"))


class TencentVideo(TencentBaseUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        category=None,
        is_draft=False,
        desc: str | None = None,
        thumbnail_path: str | None = None,
        thumbnail_landscape_path: str | None = None,
        thumbnail_portrait_path: str | None = None,
        short_title: str | None = None,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
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
        self.category = category
        self.is_draft = is_draft
        self.desc = desc or ""
        self.thumbnail_path = thumbnail_path
        self.thumbnail_landscape_path = thumbnail_landscape_path
        self.thumbnail_portrait_path = thumbnail_portrait_path or thumbnail_path
        self.short_title = short_title

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("视频模式下，title 是必须的")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_landscape_path:
            self.thumbnail_landscape_path = str(self.validate_image_file(self.thumbnail_landscape_path))
        if self.thumbnail_portrait_path:
            self.thumbnail_portrait_path = str(self.validate_image_file(self.thumbnail_portrait_path))

    async def handle_upload_error(self, page: Page) -> None:
        tencent_logger.info(_msg("😵", "视频出错了，重新上传中"))
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role("button", name="删除", exact=True).click()
        await self.upload_video_file(page, self.file_path)

    async def open_thumbnail_dialog(
        self, page: Page, selectors: list[str], dialog_titles: list[str],
        confirm_texts: list[str] | None = None,
    ):
        for selector in selectors:
            cover_entry = page.locator(selector).first
            try:
                if not await cover_entry.count():
                    continue
                # JS click bypasses wujie microfrontend sandbox blocking
                # (WeChat closes previous cover dialog and blocks next click)
                await cover_entry.evaluate('el => el.click()')
                await page.wait_for_timeout(500)
                # Fallback: if JS click didn't trigger, try Playwright click
                if not await page.locator('div.weui-desktop-dialog:visible').count():
                    await cover_entry.click(timeout=1000)
                await page.wait_for_timeout(500)
                if await page.locator('div.weui-desktop-dialog:visible').count():
                    break
            except Exception:
                continue

        # Handle intermediate confirmation dialog (portrait cover in WeChat Channels
        # now shows "使用此素材作为封面？" first, requiring "直接编辑" to proceed)
        if confirm_texts:
            for confirm_text in confirm_texts:
                try:
                    confirm_dialog = page.locator("div.weui-desktop-dialog").filter(has_text=confirm_text).first
                    if await confirm_dialog.count():
                        edit_btn = confirm_dialog.locator('button:has-text("直接编辑")').first
                        if await edit_btn.count():
                            await edit_btn.click()
                            await page.wait_for_timeout(1000)
                            break
                except Exception:
                    continue

        for title in dialog_titles:
            cover_dialog = page.locator("div.weui-desktop-dialog").filter(has_text=title).first
            if await cover_dialog.count():
                return cover_dialog
        return None

    async def upload_thumbnail_in_dialog(self, page: Page, cover_dialog, thumbnail_path: str) -> None:
        await cover_dialog.wait_for(state="visible", timeout=5000)
        file_input = cover_dialog.locator('.single-cover-uploader-wrap input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(thumbnail_path)
        await page.wait_for_timeout(3000)

        confirm_button = cover_dialog.locator(
            'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确认")'
        ).first
        if not await confirm_button.count():
            raise RuntimeError("未找到可见的封面确认按钮")
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()

        try:
            await cover_dialog.wait_for(state="hidden", timeout=10000)
        except Exception as exc:
            raise RuntimeError("封面确认后编辑弹窗未关闭，拒绝继续发布") from exc

    async def _cover_preview_fingerprint(self, page: Page, selectors: list[str]) -> str | None:
        for selector in selectors:
            if "cover-wrap" not in selector:
                continue
            entry = page.locator(selector).first
            if not await entry.count():
                continue
            fingerprint = await entry.evaluate("""
                el => {
                    const media = [];
                    for (const node of [el, ...el.querySelectorAll('*')]) {
                        if (node.currentSrc) media.push(`src:${node.currentSrc}`);
                        else if (node.src) media.push(`src:${node.src}`);
                        if (node.poster) media.push(`poster:${node.poster}`);
                        const bg = getComputedStyle(node).backgroundImage;
                        if (bg && bg !== 'none') media.push(`bg:${bg}`);
                        if (node.tagName === 'CANVAS') {
                            try { media.push(`canvas:${node.toDataURL()}`); } catch (_) {}
                        }
                    }
                    return JSON.stringify(media);
                }
            """)
            if fingerprint and fingerprint != "[]":
                return fingerprint
        return None

    async def set_single_thumbnail(
        self,
        page: Page,
        thumbnail_path: str,
        selectors: list[str],
        dialog_titles: list[str],
        label: str,
        confirm_texts: list[str] | None = None,
    ) -> None:
        before = await self._cover_preview_fingerprint(page, selectors)
        if not before:
            raise RuntimeError(f"无法读取{label}封面预览，拒绝无验证发布")

        cover_dialog = await self.open_thumbnail_dialog(page, selectors, dialog_titles, confirm_texts)
        if not cover_dialog:
            raise RuntimeError(f"当前页面没有出现{label}封面编辑弹窗")

        await self.upload_thumbnail_in_dialog(page, cover_dialog, thumbnail_path)
        for _ in range(20):
            after = await self._cover_preview_fingerprint(page, selectors)
            if after and after != before:
                break
            await page.wait_for_timeout(500)
        else:
            raise RuntimeError(f"{label}封面预览未更新，拒绝继续发布")
        tencent_logger.success(_msg("🥳", f"{label}封面已经设置完成"))

    async def set_thumbnail(self, page: Page) -> None:
        if not self.thumbnail_landscape_path and not self.thumbnail_portrait_path:
            return

        await page.evaluate(
            "() => document.querySelectorAll('.share-card,.form-item.flex-start,.weui-desktop-dialog__wrp').forEach(e => e.remove())"
        )
        tencent_logger.info(_msg("🖼️", "小人准备设置封面"))

        landscape_selectors = [
            'div.horizon-cover-wrap:has-text("4:3")',
            'div.horizon-cover-wrap',
            'div[class*="horizon-cover"]:has-text("4:3")',
            'div:has-text("分享卡片"):has-text("4:3")',
            # text fallbacks: after portrait dialog closes, DOM re-renders
            'div:has-text("分享卡片 4:3")',
            'div:has-text("编辑"):has-text("分享卡片"):has-text("4:3")',
        ]
        portrait_selectors = [
            'div.vertical-cover-wrap:has-text("个人主页卡片"):has-text("3:4")',
            'div.vertical-cover-wrap:has-text("3:4")',
            'div.vertical-cover-wrap:has-text("个人主页卡片")',
            # text fallbacks: after landscape dialog closes, DOM re-renders and
            # class names change, but the label text stays visible
            'div:has-text("个人主页卡片 3:4")',
            'div:has-text("编辑"):has-text("个人主页卡片"):has-text("3:4")',
        ]

        # Default: set one main cover only. User prioritizes mobile/homepage,
        # so portrait wins when both paths are provided. Double-setting covers
        # is unstable because WeChat re-renders the cover DOM after dialog close.
        if self.thumbnail_portrait_path:
            if self.thumbnail_landscape_path:
                tencent_logger.info(_msg("🧍", "检测到两个封面参数；按策略只设置3:4竖版主封面，跳过4:3横版"))
            await self.set_single_thumbnail(
                page,
                self.thumbnail_portrait_path,
                portrait_selectors,
                ["编辑个人主页卡片", "编辑封面"],
                "3:4 竖版",
                confirm_texts=["使用此素材作为封面？"],
            )
        elif self.thumbnail_landscape_path:
            await self.set_single_thumbnail(
                page,
                self.thumbnail_landscape_path,
                landscape_selectors,
                ["编辑分享卡片", "编辑视频号动态封面", "编辑动态封面", "编辑封面"],
                "4:3 横版",
            )

    async def prepare_video_for_publish(self, page: Page) -> None:
        await self.fill_title_and_tags(page)
        await self.fill_description(page)
        await self.apply_collection(page)

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "小人先检查 cookie、视频文件和发布时间"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "上传前检查通过"))

        context, browser = await _launch_tencent_context(
            playwright,
            self.account_file,
            headless=self.headless,
        )

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}"))

            await self.upload_video_file(page, self.file_path)
            await self.prepare_video_for_publish(page)
            await self.wait_for_upload_complete(page)
            await self.apply_original_statement(page)
            await self.set_thumbnail(page)

            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)

            await self.set_short_title(page, self.title, self.short_title)
            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            tencent_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            if browser:
                await browser.close()

    async def tencent_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_video()


class TencentNote(TencentBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        is_draft: bool = False,
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
        self.is_draft = is_draft

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("图文模式下，title 是必须的")
        if not self.image_paths:
            raise ValueError("图文模式下，图片是必须的")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def switch_to_note_mode(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.switch_to_note_mode 中补充视频号切换到图文发布模式的逻辑")

    async def upload_note_images(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.upload_note_images 中补充视频号图文图片上传逻辑")

    async def fill_note_title_and_tags(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.fill_note_title_and_tags 中补充视频号图文标题/话题填写逻辑")

    async def fill_note_body(self, page: Page) -> None:
        return None

    async def prepare_note_for_publish(self, page: Page) -> None:
        await self.fill_note_title_and_tags(page)
        await self.fill_note_body(page)
        await self.apply_collection(page)
        await self.apply_original_statement(page)

    async def upload_note_content(self, page: Page) -> None:
        await self.switch_to_note_mode(page)
        await self.upload_note_images(page)
        await self.prepare_note_for_publish(page)

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "小人先检查 cookie、图文图片和发布时间"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "图文上传前检查通过"))

        context, browser = await _launch_tencent_context(
            playwright,
            self.account_file,
            headless=self.headless,
        )
        context = await set_init_script(context)

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"小人开始搬运图文，共 {len(self.image_paths)} 张图片"))

            await self.upload_note_content(page)

            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)

            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            tencent_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            if browser:
                await browser.close()

    async def tencent_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_note()
