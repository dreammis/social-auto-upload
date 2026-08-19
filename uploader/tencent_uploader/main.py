# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import base64
import inspect
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import BASE_DIR, DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import tencent_logger

TENCENT_LOGIN_URL = "https://channels.weixin.qq.com"
TENCENT_HOME_URL = "https://channels.weixin.qq.com/platform"
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
    else:
        launch_kwargs["channel"] = "chrome"
    return launch_kwargs


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

    # 视频号「短标题」要求 6~16 个字符/汉字；本项目按 >6 且 <16 从严控制在 7~15。
    formatted_string = formatted_string.strip()
    if len(formatted_string) > 15:
        formatted_string = formatted_string[:15]
    if len(formatted_string) < 7:
        # 不足下限时补足到 7；不能用尾部空格（会被平台 trim 掉导致仍不达标）
        filler = "，精彩内容分享"
        formatted_string = (formatted_string + filler)[:7] if formatted_string else "精彩视频内容分享"

    return formatted_string


async def cookie_auth(account_file):
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(TENCENT_UPLOAD_URL, wait_until="domcontentloaded")

            # cookie 失效时, 页面先停在 post/create, 随后由前端 JS 跳转到登录页;
            # 必须等待跳转完成再判断, 否则会误报"cookie 有效"
            try:
                await page.wait_for_url("**/login.html**", timeout=8000)
                tencent_logger.info(_msg("🥹", "cookie 已失效（页面跳转到登录页），得重新登录一下"))
                return False
            except Exception:
                pass  # 8 秒内未跳转, 大概率已登录

            # 双保险: 页面里出现微信扫码登录 iframe 也视为失效
            for fr in page.frames:
                if "open.weixin.qq.com/connect/qrconnect" in fr.url:
                    tencent_logger.info(_msg("🥹", "cookie 已失效（页面出现扫码登录框），得重新登录一下"))
                    return False

            tencent_logger.success(_msg("🥳", "cookie 有效"))
            return True
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"cookie 校验时出错，按失效处理: {exc}"))
            return False
        finally:
            await browser.close()


async def _extract_tencent_qrcode_src(page: Page) -> str:
    if hasattr(page, "frame_locator"):
        try:
            iframe_locator = page.frame_locator('[src*="login-for-iframe"]')
            qr_code_img = iframe_locator.locator('div#app img.qrcode').first
            await qr_code_img.wait_for(state="visible", timeout=8000)
            src = await qr_code_img.get_attribute("src")
            if src and src.startswith("data:image/"):
                return src
        except Exception:
            pass

    # 2026 新版登录页: 二维码在 open.weixin.qq.com/connect/qrconnect 的 iframe 里,
    # img.qrcode 的 src 是相对路径(如 /connect/qrcode/xxxx), 需要下载后转成 data URL
    for frame in page.frames:
        if "open.weixin.qq.com/connect/qrconnect" not in frame.url:
            continue
        try:
            qr_img = frame.locator("img.qrcode").first
            await qr_img.wait_for(state="attached", timeout=15000)
            src = None
            for _ in range(20):
                src = await qr_img.get_attribute("src")
                if src:
                    break
                await page.wait_for_timeout(500)
            if not src:
                continue
            if src.startswith("data:image/"):
                return src
            abs_url = urljoin(frame.url, src)
            resp = await page.context.request.get(abs_url)
            if resp.ok:
                body = await resp.body()
                content_type = resp.headers.get("content-type", "image/png").split(";")[0]
                return f"data:{content_type};base64,{base64.b64encode(body).decode()}"
        except Exception:
            continue

    selector_candidates = [
        "div.login-qrcode-wrap img.qrcode",
        "div.qrcode-wrap img.qrcode",
        "img.qrcode",
        'img[src^="data:image/"]',
    ]
    for selector in selector_candidates:
        qr_code_img = page.locator(selector).first
        try:
            if not await qr_code_img.count() or not await qr_code_img.is_visible():
                continue
            src = await qr_code_img.get_attribute("src")
            if src and src.startswith("data:image/"):
                return src
        except Exception:
            continue

    raise RuntimeError("未获取到视频号登录二维码地址")


async def _save_tencent_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_utils = _get_qrcode_utils()
    qrcode_src = await _extract_tencent_qrcode_src(page)
    qrcode_path = qrcode_utils["save_data_url_image"](
        qrcode_src,
        qrcode_utils["build_login_qrcode_path"](account_file, suffix="tencent_login_qrcode"),
    )
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
        "image_data_url": qrcode_src,
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
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for selector in tip_selectors:
        tip = page.locator(selector).first
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
    for selector in scanned_tips:
        tip = page.locator(selector).first
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
    for selector in visible_refresh_selectors:
        refresh_wrap = page.locator(selector).first
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
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for selector in tip_selectors:
        tip = page.locator(selector).first
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

    fallback_refresh = page.locator("div.login-qrcode-wrap div.refresh-wrap").first
    if await fallback_refresh.count():
        await fallback_refresh.click()
        return

    raise RuntimeError("未找到可点击的视频号二维码刷新区域")


async def _wait_for_tencent_login(
    page: Page,
    account_file: str,
    qrcode_info: dict | None,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
) -> dict:
    qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info else None
    scanned_logged = False
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
            try:
                qrcode_info = await _save_tencent_qrcode(
                    page,
                    account_file,
                    previous_qrcode_path=qrcode_path,
                    qrcode_callback=qrcode_callback,
                )
                qrcode_path = Path(qrcode_info["image_path"])
            except Exception as exc:
                tencent_logger.warning(_msg("⚠️", f"刷新后未能重新提取二维码({exc})，请直接在浏览器窗口中扫码"))

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
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        qrcode_path = None
        result = _build_login_result(False, "failed", "视频号登录失败", account_file)
        try:
            page = await context.new_page()
            await page.goto(TENCENT_LOGIN_URL)
            try:
                qrcode_info = await _save_tencent_qrcode(page, account_file, qrcode_callback=qrcode_callback)
                qrcode_path = Path(qrcode_info["image_path"])
            except Exception as exc:
                tencent_logger.warning(
                    _msg("⚠️", f"提取二维码图片失败({exc})，请直接在弹出的浏览器窗口中扫码，登录流程不受影响")
                )
                qrcode_info = None
                qrcode_path = None
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
                if not await cookie_auth(account_file):
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
            await context.close()
            await browser.close()


async def tencent_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
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
        collection_name: str | None = None,
    ):
        self.publish_date = publish_date
        self.account_file = _resolve_account_file(account_file)
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.headless = headless
        self.collection_name = collection_name
        self.local_executable_path = LOCAL_CHROME_PATH

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成视频号登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成视频号登录: {self.account_file}")
        if self.publish_strategy not in {TENCENT_PUBLISH_STRATEGY_IMMEDIATE, TENCENT_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def wait_for_realtime_verification(
        self,
        page: Page,
        qr_path: str | Path | None = None,
        timeout_seconds: float = 10 * 60,
        poll_interval_seconds: float = 2,
    ) -> Path | None:
        dialog = page.locator("div.weui-desktop-dialog__wrp:visible").filter(has_text="实名验证").first
        if not await dialog.count() or not await dialog.is_visible():
            return None

        output_path = Path(qr_path) if qr_path else Path(self.account_file).with_name(
            f"{Path(self.account_file).stem}_verification_qr.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await dialog.screenshot(path=str(output_path))
        tencent_logger.warning(_msg("📱", f"需要管理员微信扫码完成实名验证: {output_path}"))

        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while await dialog.count() and await dialog.is_visible():
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("等待视频号管理员实名验证超时")
            await asyncio.sleep(poll_interval_seconds)

        tencent_logger.success(_msg("🥳", "管理员实名验证已完成，继续发表"))
        return output_path

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
        # 视频号已改版：直接全页加载 /platform/post/create 会被跳回 /platform 首页，
        # 发布表单 iframe 只加载空壳（Vue 不挂载），页面上没有任何 input[type=file]。
        # 正确入口：先进首页，再点可见的「发表视频」按钮做客户端跳转，表单才会真正挂载。
        await page.goto(TENCENT_HOME_URL, timeout=120000, wait_until="domcontentloaded")
        # cookie 失效时前端 JS 会跳转到登录页, 提前发现并报明确的错误
        try:
            await page.wait_for_url("**/login.html**", timeout=8000)
            raise RuntimeError("视频号 cookie 已失效（被跳转到登录页），请重新扫码登录后再发布")
        except TimeoutError:
            pass  # 8 秒内未跳转, 正常
        except RuntimeError:
            raise
        except Exception:
            pass
        if any("open.weixin.qq.com/connect/qrconnect" in fr.url for fr in page.frames):
            raise RuntimeError("视频号 cookie 已失效（被跳转到登录页），请重新扫码登录后再发布")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        # 注意：get_by_text("发表视频") 会命中一个隐藏的说明 <p>（不可点）；
        # 首页真正可点的入口是 button.weui-desktop-btn。
        publish_entry = page.locator("button.weui-desktop-btn", has_text="发表视频").first
        try:
            await publish_entry.wait_for(state="visible", timeout=30000)
            await publish_entry.click()
        except Exception:
            # 兜底：按钮没点到时退回老逻辑直接跳转（可能仍是空壳，但保持向后兼容）
            await page.goto(TENCENT_UPLOAD_URL, timeout=120000, wait_until="domcontentloaded")
        try:
            await page.wait_for_url("**/platform/post/create", timeout=120000)
        except Exception:
            pass

        # 上传表单在 micro/content/post/create 这个 iframe 里，domcontentloaded 时它还是空的。
        # 不等网络静默就去找 input[type=file]，会误报「未找到视频号文件上传框」——
        # 失败截图上左栏渲染正常、主内容区一片空白，看起来完全不像加载没完成。
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass  # 静默不了就算了，下面还有重试兜底

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
        clicked_publish = False
        for _ in range(60):
            if fi is not None:
                break
            if not clicked_publish:
                # 新版视频号助手可能先落在首页，且「发表视频」按钮异步出现。
                # 持续轮询所有可访问 button；Patchright 在当前页面上按名称精确匹配不稳定。
                try:
                    publish_buttons = await page.get_by_role("button").all()
                except Exception:
                    publish_buttons = []
                for candidate in publish_buttons:
                    try:
                        button_text = (await candidate.inner_text()).strip()
                        is_visible = await candidate.is_visible()
                    except Exception:
                        continue
                    if "发表视频" in button_text and is_visible:
                        await candidate.click(force=True)
                        clicked_publish = True
                        break
            fi = await find_file_input()
            if fi is None:
                await asyncio.sleep(1)
        if fi is None:
            # 留现场：这个错误的可能原因太多（没登录 / 落到首页 / iframe 没加载完 /
            # 平台改版），只看错误字符串没法区分，截图能一眼看出是哪种。
            try:
                shot = Path(BASE_DIR) / "debug_tencent_no_file_input.png"
                await page.screenshot(path=str(shot), full_page=True)
                tencent_logger.info(_msg(
                    "📸",
                    f"失败现场已截图 {shot}; url={page.url}; "
                    f"frames={[fr.url[:80] for fr in page.frames]}",
                ))
            except Exception:
                pass
            raise RuntimeError("未找到视频号文件上传框")
        await fi.set_input_files(file_path)

    async def set_short_title(self, page: Page, title: str, short_title: str | None = None) -> None:
        # 视频号「短标题」即界面上要求填写的“标题”（那个大编辑区其实是“视频描述”）。
        # 走 format_str_for_short_title 保证长度落在 7~15，避免发布时被校验拦下。
        value = format_str_for_short_title(short_title or title)
        # 优先用 placeholder 定位（已 dump 验证更稳），兜底旧的“短标题”相邻 input。
        field = page.locator('input[placeholder="填写短标题有机会获得更多流量"]').first
        if not await field.count():
            field = (
                page.get_by_text("短标题", exact=True)
                .locator("..")
                .locator("xpath=following-sibling::div")
                .locator('span input[type="text"]')
            )
        if await field.count():
            await field.fill(value)
            tencent_logger.info(_msg("🏷️", f"短标题已填写（{len(value)}字）：{value}"))
        else:
            tencent_logger.info(_msg("🧾", "未找到短标题输入框，跳过短标题"))

    async def _dismiss_switch_account_dialog(self, page: Page) -> None:
        # 视频号上传后偶发弹出「切换视频号」对话框(.changeAccount-dialog / .common-dialog)遮挡发布表单。
        # 它带「取消」按钮、非强制，点「取消」/ 右上角 × / Esc 跳过即可，用当前账号继续发布。
        cancel = page.locator('.changeAccount-dialog button:has-text("取消")').first
        closeb = page.locator('.changeAccount-dialog .weui-desktop-dialog__close-btn').first
        for cand in (cancel, closeb):
            try:
                if await cand.count() and await cand.is_visible():
                    await cand.click(timeout=2000)
                    await page.wait_for_timeout(600)
                    return
            except Exception:
                continue
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(600)
        except Exception:
            pass

    async def fill_title_and_tags(self, page: Page) -> None:
        # 上传后偶发「切换视频号」弹窗遮挡描述框，点不动就关弹窗重试（以能点中描述框为成功标志）。
        for _ in range(4):
            try:
                await page.locator("div.input-editor").click(timeout=5000)
                break
            except Exception:
                await self._dismiss_switch_account_dialog(page)
                await page.wait_for_timeout(500)
        else:
            await page.locator("div.input-editor").click(timeout=8000)
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
        """在发布表单页"添加到合集"下拉框按合集名精确选中（页面结构：option-item > .item > .name/.desc）。

        找不到匹配名字的合集时不展开/不选（保持未选状态直接发布，界面允许留空，
        不阻断主发布流程）。旧实现是"下拉项数>1就选第一项"，等价于随机选，已改为精确匹配。
        """
        if not self.collection_name:
            return
        try:
            trigger = page.get_by_text("添加到合集").first
            if await trigger.count() == 0:
                tencent_logger.info(_msg("🧾", "当前页面未发现「添加到合集」入口，跳过归集"))
                return
            dropdown = trigger.locator("xpath=following-sibling::div").first
            await dropdown.click(timeout=8000)
            await page.wait_for_timeout(800)

            option = dropdown.locator(".option-list-wrap .option-item").filter(
                has=page.locator(f'.name:text-is("{self.collection_name}")')
            )
            if await option.count() == 0:
                tencent_logger.warning(
                    _msg("😵", f"合集下拉框未找到「{self.collection_name}」，跳过归集，保持未选状态")
                )
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                return

            # headless 下 option 常报 "element is not visible"：下拉列表开在视口外/
            # 在 .option-list-wrap 滚动容器内，headful（大窗口）时在视野里能直接点中，
            # headless 默认视口小就点不中。先把目标 option 滚进视野再点；普通 click
            # 仍被判不可见时 → force 点击（跳过可见性 actionability）→ 派发原生 click 兜底。
            target = option.first
            try:
                await target.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            try:
                await target.click(timeout=4000)
            except Exception:
                try:
                    await target.click(force=True, timeout=4000)
                except Exception:
                    await target.dispatch_event("click")
            await page.wait_for_timeout(500)
            tencent_logger.success(_msg("🥳", f"已选择合集：{self.collection_name}"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"选择合集失败，跳过归集继续发布: {exc}"))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

    async def apply_original_statement(self, page: Page) -> None:
        # 视频号「视频标注」下拉：本项目成片经 AI 处理（TTS 配音、AI 字幕、AI 前贴片），
        # 依平台合规要求如实选「含AI生成内容」（与「内容为转载」等并列，选定即可、无需填写来源）。
        # 注意：这与上方独立的「声明原创」复选框是两个不同字段，本项目走 AI 标注、不勾原创声明。
        label_text = getattr(self, "content_label", None) or "含AI生成内容"
        try:
            entry = page.get_by_text("选择视频标注", exact=True).first
            if not await entry.count():
                tencent_logger.info(_msg("🧾", "当前页面未发现「视频标注」入口，跳过标注继续发布"))
                return
            await entry.click()
            await page.wait_for_timeout(800)
            option = page.get_by_text(label_text, exact=True).first
            await option.wait_for(state="visible", timeout=5000)
            await option.click()
            await page.wait_for_timeout(500)
            tencent_logger.success(_msg("🏷️", f"视频标注已选择：{label_text}"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"设置视频标注「{label_text}」失败，跳过继续发布：{exc}"))

    async def wait_for_upload_complete(
        self, page: Page, timeout_seconds: int = 3600, max_retries: int = 3
    ) -> None:
        """等上传完成。

        **必须有个头，而且重试必须有上限。** 原来是没有出口的 while True：上传出错就
        删掉重传，失败再删再传，永远循环；中间每 2 秒打一行「正在上传视频中...」——
        这条日志和真的在传一模一样，从外面完全分不出。

        实测（2026-08-11，172MB / 上行 ~0.5Mbps）：每次传到 4 分钟左右报错，然后重来，
        整整循环了近 2 小时也不会停，进程也不会退。用户看到的只有「正在上传视频中」，
        真相是同一段视频被反复上传了 20 多次。

        默认 1 小时 / 3 次重试：慢网络上大文件确实会传很久，上限要给够；
        但到点、或者重试用完，就带现场截图明确报错，不要静默地转下去。
        """
        deadline = time.monotonic() + timeout_seconds
        last_report = 0.0
        retries = 0
        while True:
            if time.monotonic() > deadline:
                try:
                    shot = Path(BASE_DIR) / "debug_tencent_upload_timeout.png"
                    await page.screenshot(path=str(shot), full_page=True)
                    tencent_logger.error(_msg("📸", f"上传超时现场已截图 {shot}"))
                except Exception:
                    pass
                raise RuntimeError(
                    f"视频号上传超过 {timeout_seconds} 秒仍未完成（「发表」按钮一直不可用）"
                )
            try:
                publish_button = page.locator('div.form-btns button:has-text("发表"):visible').first
                if await publish_button.count():
                    button_class = await publish_button.get_attribute("class")
                    if (
                        not await publish_button.is_disabled()
                        and (not button_class or "weui-desktop-btn_disabled" not in button_class)
                    ):
                        tencent_logger.info(_msg("🥳", "视频上传完毕"))
                        break

                # 每 2 秒刷一行同样的话没有信息量，只是把日志冲爆（实测 50 分钟刷了 1600 行）。
                # 30 秒一行，并且带上已等多久——「还要多久」是这里唯一有用的信息。
                now = time.monotonic()
                if now - last_report >= 30:
                    waited = int(timeout_seconds - (deadline - now))
                    tencent_logger.info(_msg("🏃", f"正在上传视频中...（已等 {waited} 秒）"))
                    last_report = now
                await asyncio.sleep(2)

                upload_failed = await page.locator("div.status-msg.error").count()
                delete_button = await page.locator('div.media-status-content div.tag-inner:has-text("删除")').count()
                if upload_failed and delete_button:
                    retries += 1
                    if retries > max_retries:
                        try:
                            shot = Path(BASE_DIR) / "debug_tencent_upload_failed.png"
                            await page.screenshot(path=str(shot), full_page=True)
                            tencent_logger.error(_msg("📸", f"上传反复失败，现场已截图 {shot}"))
                        except Exception:
                            pass
                        raise RuntimeError(
                            f"视频号上传连续失败 {max_retries} 次，已停止重试"
                            "（常见原因：文件过大、上行带宽太慢导致平台侧超时，或走了代理/VPN）"
                        )
                    tencent_logger.error(_msg("😵", f"发现上传出错了，准备重试（第 {retries}/{max_retries} 次）"))
                    await self.handle_upload_error(page)
            except RuntimeError:
                raise
            except Exception:
                await asyncio.sleep(2)

    async def submit_publish(self, page: Page) -> None:
        is_draft = getattr(self, "is_draft", False)
        # 先等待并清理遮罩/弹窗,再等发表按钮出现
        for wait_round in range(60):
            await self._dismiss_switch_account_dialog(page)
            try:
                await page.evaluate("""() => document.querySelectorAll('.mask, .changeAccount-dialog, .common-dialog').forEach(e => e.remove())""")
            except Exception:
                pass
            publish_btn = page.get_by_role("button", name="发表", exact=True).first if not is_draft else page.get_by_role("button", name="保存草稿").first
            try:
                if await publish_btn.count() and await publish_btn.is_visible():
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        else:
            tencent_logger.warning(_msg("😵", "60s 内未找到可见的发表/草稿按钮，尝试强制继续"))
        # 点发表/草稿
        for attempt in range(20):
            try:
                if await publish_btn.count():
                    try:
                        await publish_btn.click(timeout=4000)
                    except Exception:
                        await publish_btn.evaluate("el => el.click()")
                if is_draft:
                    await page.wait_for_url("**/post/list**", timeout=5000)
                    tencent_logger.success(_msg("🥳", "视频草稿保存成功"))
                else:
                    # 发表成功后视频号可能跳 /platform（首页）、/post/list 或留在 create 页但按钮消失。
                    # 综合判断：URL 离开 /post/create 或 发表按钮不再存在。
                    for _ in range(10):
                        await asyncio.sleep(1)
                        cur = page.url
                        if "/post/create" not in cur:
                            tencent_logger.success(_msg("🥳", "视频发布成功"))
                            return
                        if not await publish_btn.count():
                            tencent_logger.success(_msg("🥳", "视频发布成功（按钮已消失）"))
                            return
                    raise Exception("发表后 10s 页面未变化")
                return
            except Exception as exc:
                current_url = page.url
                if is_draft and ("post/list" in current_url or "draft" in current_url):
                    tencent_logger.success(_msg("🥳", "视频草稿保存成功"))
                    return
                if (not is_draft) and "/post/create" not in current_url:
                    tencent_logger.success(_msg("🥳", "视频发布成功"))
                    return
                if attempt and attempt % 5 == 0:
                    tencent_logger.warning(_msg("😵", f"发布仍未完成(第{attempt}次)，异常: {str(exc)[:60]}"))
                tencent_logger.info(_msg("🏃", "视频正在发布中..."))
                await asyncio.sleep(1)
        raise RuntimeError("发布未在预期时间内完成，请检查发布页面")


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
        collection_name: str | None = None,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
            collection_name=collection_name,
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

    async def open_thumbnail_dialog(self, page: Page, selectors: list[str], dialog_titles: list[str]):
        for selector in selectors:
            cover_entry = page.locator(selector).first
            try:
                if not await cover_entry.count():
                    continue
                await cover_entry.wait_for(state="visible", timeout=3000)
                await cover_entry.click()
                await page.wait_for_timeout(500)
                break
            except Exception:
                continue

        for title in dialog_titles:
            cover_dialog = page.locator("div.weui-desktop-dialog").filter(has_text=title).first
            if await cover_dialog.count():
                return cover_dialog
        return None

    async def confirm_thumbnail_crop(self, page: Page) -> None:
        crop_dialog = page.locator("div.weui-desktop-dialog").filter(has_text="裁剪封面图").first
        if not await crop_dialog.count():
            return

        try:
            await crop_dialog.wait_for(state="visible", timeout=10000)
            crop_confirm_button = crop_dialog.locator(
                'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确定")'
            ).first
            if await crop_confirm_button.count():
                await crop_confirm_button.wait_for(state="visible", timeout=5000)
                await crop_confirm_button.click()
                await page.wait_for_timeout(1000)
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"封面裁剪确认时出错，小人继续尝试保存主弹窗: {exc}"))

    async def upload_thumbnail_in_dialog(self, page: Page, cover_dialog, thumbnail_path: str) -> None:
        await cover_dialog.wait_for(state="visible", timeout=5000)
        file_input = cover_dialog.locator('.single-cover-uploader-wrap input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(thumbnail_path)
        await page.wait_for_timeout(2000)

        confirm_button = cover_dialog.locator(
            'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确认")'
        ).first
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()

    async def set_single_thumbnail(
        self,
        page: Page,
        thumbnail_path: str,
        selectors: list[str],
        dialog_titles: list[str],
        label: str,
    ) -> None:
        cover_dialog = await self.open_thumbnail_dialog(page, selectors, dialog_titles)
        if not cover_dialog:
            tencent_logger.info(_msg("🧍", f"当前页面没有出现{label}封面编辑弹窗，小人先跳过"))
            return

        try:
            await self.upload_thumbnail_in_dialog(page, cover_dialog, thumbnail_path)
            tencent_logger.success(_msg("🥳", f"{label}封面已经设置完成"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"{label}封面设置失败，这次先跳过: {exc}"))

    async def set_thumbnail(self, page: Page) -> None:
        if not self.thumbnail_landscape_path and not self.thumbnail_portrait_path:
            return

        tencent_logger.info(_msg("🖼️", "小人准备设置封面"))

        landscape_selectors = [
            'div.horizontal-cover-wrap:has-text("4:3")',
            'div[class*="cover-wrap"]:has-text("4:3"):has-text("动态")',
            'div:has-text("视频号动态"):has-text("4:3")',
            'div:has-text("横版封面"):has-text("4:3")',
        ]
        portrait_selectors = [
            'div.vertical-cover-wrap:has-text("个人主页卡片"):has-text("3:4")',
            'div.vertical-cover-wrap:has-text("3:4")',
            'div.vertical-cover-wrap:has-text("个人主页卡片")',
        ]

        if self.thumbnail_landscape_path:
            await self.set_single_thumbnail(
                page,
                self.thumbnail_landscape_path,
                landscape_selectors,
                ["编辑视频号动态封面", "编辑动态封面", "编辑封面"],
                "4:3 横版",
            )
        if self.thumbnail_portrait_path:
            await self.set_single_thumbnail(
                page,
                self.thumbnail_portrait_path,
                portrait_selectors,
                ["编辑个人主页卡片", "编辑封面"],
                "3:4 竖版",
            )

    async def prepare_video_for_publish(self, page: Page) -> None:
        await self.wait_for_realtime_verification(page)
        await self.fill_title_and_tags(page)
        await self.fill_description(page)
        # 合集不在这里选：此时视频还在上传，上传完成后表单会刷新，
        # 上传中选的合集会被重置/不绑定（"日志说选了、后台没加"的根因）。
        # 改到 wait_for_upload_complete 之后再选，见 upload()。

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "小人先检查 cookie、视频文件和发布时间"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "上传前检查通过"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}"))

            await self.upload_video_file(page, self.file_path)
            await self.prepare_video_for_publish(page)
            await self.wait_for_upload_complete(page)
            # 上传完成、表单稳定后再选合集（否则上传中选的会被重置）
            await self.apply_collection(page)
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

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)
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
            await browser.close()

    async def tencent_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_note()
