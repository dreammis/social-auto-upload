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

from patchright.async_api import BrowserContext
from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import BASE_DIR, BROWSER_PROFILES_DIR, DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from profile_storage import ensure_private_profile_dir
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import tencent_logger
from utils.cover_verification import verify_cover_preview

TENCENT_LOGIN_URL = "https://channels.weixin.qq.com"
TENCENT_HOME_URL = "https://channels.weixin.qq.com/platform"
TENCENT_UPLOAD_URL = "https://channels.weixin.qq.com/platform/post/create"
TENCENT_MANAGE_URL = "https://channels.weixin.qq.com/platform/post/list"
TENCENT_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
TENCENT_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def require_dageju_release(uploader) -> None:
    """Reject protected legacy entrypoints before cookie or browser access."""
    import sys
    scripts = Path(__file__).resolve().parents[3] / 'Scripts'
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from dageju_autopilot.channels_release_gate import require_approved_upload
    protected = Path(__file__).resolve().parents[4] / '05_ContentOS/Douyin/大格局视界/videos'
    file = Path(getattr(uploader, 'file_path', '/no-media'))
    if (Path(uploader.account_file).stem in {'tencent_dagaju', 'dagaju'} or
            file.resolve().is_relative_to(protected.resolve())):
        require_approved_upload('dagaju', file.resolve().parent.parent)


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


def get_tencent_profile_dir(account_file: str | Path, create: bool = True) -> Path:
    account_stem = Path(account_file).stem
    profile_name = account_stem if account_stem.startswith("tencent_") else f"tencent_{account_stem}"
    profile_dir = BROWSER_PROFILES_DIR / profile_name
    if create:
        profile_dir = ensure_private_profile_dir(BROWSER_PROFILES_DIR, profile_name)
    return profile_dir


def _has_tencent_profile(account_file: str | Path) -> bool:
    profile_dir = get_tencent_profile_dir(account_file, create=False)
    return (profile_dir / "Local State").exists() or (profile_dir / "Default").exists()


def _use_minimal_cookie() -> bool:
    """最小 cookie 方案开关：默认启用；SAU_TENCENT_PERSISTENT=1 可强制回持久化模式。"""
    return os.environ.get("SAU_TENCENT_PERSISTENT", "0") != "1"


async def launch_tencent_minimal_context(
    playwright: Playwright,
    account_file: str | Path,
    headless: bool = True,
    executable_path: str | None = None,
) -> BrowserContext:
    """全新临时上下文 + 账号 JSON 最小 cookie，不用持久化 profile。

    最小 cookie 重建方案 (2026-11-04)：不再复用 browser_profiles/tencent_dagaju
    持久化目录，每次用全新临时上下文，只注入账号 JSON 里的 sessionid/wxuin，
    避免持久化指纹（LocalStorage/IndexedDB/设备历史）触发风控导致约 24h 掉线。
    """
    import json as _json

    launch_args = [
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]
    launch_kwargs: dict = {"headless": headless, "args": launch_args}
    exec_path = executable_path or LOCAL_CHROME_PATH or None
    if exec_path and os.path.exists(exec_path):
        launch_kwargs["executable_path"] = exec_path
    else:
        launch_kwargs["channel"] = "chrome"

    browser = await playwright.chromium.launch(**launch_kwargs)
    context = await browser.new_context(bypass_csp=True)
    context = await set_init_script(context)

    cookies: list = []
    try:
        state_data = _json.loads(Path(account_file).read_text(encoding="utf-8"))
        all_cookies = state_data.get("cookies", [])
        cookies = [c for c in all_cookies if c.get("name") in ("sessionid", "wxuin")] or all_cookies
    except Exception as exc:
        tencent_logger.warning(_msg("⚠️", f"读取视频号最小 cookie 失败: {exc}"))
    if cookies:
        await context.add_cookies(cookies)
        tencent_logger.info(_msg("🍪", f"最小 cookie 模式：已注入 {len(cookies)} 个 cookie，用全新临时上下文（无持久化 profile）"))

    _orig_close = context.close

    async def _close_all() -> None:
        try:
            await _orig_close()
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    context.close = _close_all  # type: ignore[attr-defined]
    return context


async def launch_tencent_context(
    playwright: Playwright,
    account_file: str | Path,
    headless: bool = True,
    executable_path: str | None = None,
    minimal: bool | None = None,
) -> BrowserContext:
    """Launch WeChat Channels in one stable Chrome profile per account.

    The JSON storage_state remains a compatibility backup. On the first profile
    launch we import its cookies once, then let Chrome persist cookies,
    LocalStorage, IndexedDB and device history in the profile itself.

    minimal=True（默认，除非 SAU_TENCENT_PERSISTENT=1）时改走
    launch_tencent_minimal_context：全新临时上下文 + 最小 cookie，不用持久化目录。
    扫码登录流程（tencent_cookie_gen）固定走持久化模式，不受开关影响。
    """
    if minimal is None:
        minimal = _use_minimal_cookie()
    if minimal:
        return await launch_tencent_minimal_context(
            playwright, account_file, headless=headless, executable_path=executable_path
        )
    profile_dir = get_tencent_profile_dir(account_file)
    seed_marker = profile_dir / ".sau_profile_initialized"
    first_profile_launch = not seed_marker.exists()

    launch_args = [
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]
    kwargs = {
        "user_data_dir": str(profile_dir),
        "headless": headless,
        "args": launch_args,
        # 视频号新版封面生成器会创建 blob: Worker。站点当前返回的 CSP
        # 没有允许 blob: worker，自动化浏览器里会被拦截，表现为封面永远
        # 停在“生成中”。绕过页面 CSP 仅用于恢复站点自身前端 Worker，
        # 不改变上传/发布请求本身。
        "bypass_csp": True,
    }
    exec_path = executable_path or LOCAL_CHROME_PATH or None
    if exec_path and os.path.exists(exec_path):
        kwargs["executable_path"] = exec_path
    else:
        kwargs["channel"] = "chrome"

    tencent_logger.info(_msg("🌐", f"启动持久化视频号环境: {profile_dir.name}"))
    context = await playwright.chromium.launch_persistent_context(**kwargs)
    context = await set_init_script(context)

    if first_profile_launch and os.path.exists(account_file):
        try:
            import json as _json

            state_data = _json.loads(Path(account_file).read_text(encoding="utf-8"))
            cookies = state_data.get("cookies", [])
            if cookies:
                await context.add_cookies(cookies)
                tencent_logger.info(_msg("🍪", "已把现有视频号 cookies 迁移到持久化浏览器环境"))
        except Exception as exc:
            tencent_logger.warning(_msg("⚠️", f"迁移现有 cookies 到持久化环境失败: {exc}"))

    seed_marker.touch(exist_ok=True)
    return context


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
        # 不足下限时补足到 7；不能用尾部空格（会被平台 trim 掉导致仍不达标）。
        # 视频号当前会把中文逗号「，」判为非法特殊字符，所以补位文本只用汉字。
        filler = "精彩内容分享"
        formatted_string = (formatted_string + filler)[:7] if formatted_string else "精彩视频内容分享"

    return formatted_string


async def cookie_auth(account_file):
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) and not _has_tencent_profile(account_file):
        return False

    async with async_playwright() as playwright:
        context = None
        try:
            context = await launch_tencent_context(
                playwright=playwright,
                account_file=account_file,
                headless=True,
            )
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(TENCENT_UPLOAD_URL, wait_until="domcontentloaded")

            try:
                await page.wait_for_url("**/login.html**", timeout=20000)
                tencent_logger.info(_msg("🥹", "视频号持久化登录已失效，需要重新扫码一次"))
                return False
            except Exception:
                pass

            for fr in page.frames:
                if "open.weixin.qq.com/connect/qrconnect" in fr.url:
                    tencent_logger.info(_msg("🥹", "视频号持久化环境出现扫码登录框，需要重新扫码一次"))
                    return False

            await context.storage_state(path=account_file)
            tencent_logger.success(_msg("🥳", "视频号持久化登录有效"))
            return True
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"视频号持久化登录校验出错，按失效处理: {exc}"))
            return False
        finally:
            if context is not None:
                await context.close()


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
        context = await launch_tencent_context(
            playwright=playwright,
            account_file=account_file,
            headless=headless,
            minimal=False,
        )
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
                # This is a persistent Chrome context. Calling cookie_auth() here would
                # launch a second Chrome instance against the same user_data_dir while
                # the login context is still open, which triggers Chromium's
                # ProcessSingleton/SingletonLock protection. The scan result has already
                # been verified by _wait_for_tencent_login; persist state now, close this
                # context in finally, and let the caller's next standalone check validate
                # the profile after the lock is released.
                tencent_logger.success(_msg("🥳", "视频号扫码登录完成，登录状态已写入持久化环境"))
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


async def tencent_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    if not await cookie_auth(account_file):
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
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"视频号持久化登录已失效，请先完成视频号登录: {self.account_file}")
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

    async def _close_global_error_modal(self, page: Page) -> None:
        """关闭视频号助手首页的全局错误弹窗（#error-modal.active）。

        该弹窗由平台自身 JS 报错（如 ReferenceError: WXE is not defined）触发，
        会拦截整页 pointer events；且可能在页面活动后再次弹出，需反复清理。
        """
        try:
            modal = page.locator("#error-modal.active")
            if await modal.count():
                for sel in ("button:has-text('确定')", "button:has-text('×')", ".error-modal button"):
                    btn = modal.locator(sel).first
                    try:
                        if await btn.count() and await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                            tencent_logger.info(_msg("🧹", "已关闭全局错误弹窗 #error-modal"))
                            return
                    except Exception:
                        continue
        except Exception:
            pass

    async def _modal_guard_loop(self, page: Page) -> None:
        """发布期间持续清理全局错误弹窗，直到任务被取消。"""
        while True:
            await self._close_global_error_modal(page)
            await asyncio.sleep(1.5)

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
        await self._close_global_error_modal(page)
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
                await self._close_global_error_modal(page)
                if not clicked_publish:
                    # 弹窗清理后主入口可能变为可点，重试一次主入口
                    try:
                        entry = page.locator("button.weui-desktop-btn", has_text="发表视频").first
                        if await entry.count() and await entry.is_visible():
                            await entry.click(force=True)
                            clicked_publish = True
                    except Exception:
                        pass
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
                # 合集较多时下拉列表是懒加载/虚拟滚动：目标项不滚动就不渲染，
                # 首屏必然找不到。逐屏滚动选项列表并反复重找；同时做去空白
                # 容错匹配，避免名字里夹了不可见空格导致 :text-is 落空。
                wanted = "".join(self.collection_name.split())
                list_wrap = dropdown.locator(".option-list-wrap").first
                seen_names: list[str] = []
                search_deadline = time.monotonic() + 12
                while time.monotonic() < search_deadline:
                    names = dropdown.locator(".option-list-wrap .option-item .name")
                    for index in range(await names.count()):
                        try:
                            text = (await names.nth(index).inner_text()).strip()
                        except Exception:
                            continue
                        if text and text not in seen_names:
                            seen_names.append(text)
                        if "".join(text.split()) == wanted:
                            option = dropdown.locator(".option-list-wrap .option-item").filter(
                                has=names.nth(index)
                            )
                            break
                    if await option.count():
                        break
                    try:
                        await list_wrap.evaluate("el => { el.scrollTop = el.scrollTop + el.clientHeight * 0.8; }")
                    except Exception:
                        break
                    await page.wait_for_timeout(400)
                if not await option.count():
                    tencent_logger.warning(
                        _msg(
                            "😵",
                            f"合集下拉框未找到「{self.collection_name}」（可见项: {seen_names[:40]}），"
                            "跳过归集，保持未选状态",
                        )
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
        # 先声明原创：账号当前发布规则要求勾选「声明原创」。
        # 该复选框与下方「视频标注」是两个独立字段，可以同时设置。
        try:
            original_text = None
            original_scope = None
            scopes = [page, *page.frames]
            for scope in scopes:
                for original_label in ("声明原创", "原创声明", "该内容为原创", "原创"):
                    candidate = scope.get_by_text(original_label, exact=True).first
                    try:
                        if await candidate.count() and await candidate.is_visible():
                            original_text = candidate
                            original_scope = scope
                            break
                    except Exception:
                        continue
                if original_text is not None:
                    break

            if original_text is not None and original_scope is not None:
                # 2026 新版页面中，“声明原创”左侧文字只是字段标题；真正 checkbox
                # 位于同一个 .form-item 行的右侧 .form-item-body 内，不能点标题文字。
                row = original_text.locator("xpath=ancestor::div[contains(@class, 'form-item')][1]")
                checkbox = row.locator('input[type="checkbox"]').first
                if not await checkbox.count():
                    raise RuntimeError("已找到『声明原创』字段，但未找到同一行的 checkbox")

                if not await checkbox.is_checked():
                    await checkbox.check(force=True)
                    await page.wait_for_timeout(500)

                # 首次勾选会弹出“原创权益”确认窗。该弹窗包含独立的条款复选框，
                # 必须先勾选“我已阅读并同意《原创声明须知》和《使用条款》”，
                # 再点击“声明原创”。仅检查外层 checkbox 会造成“日志成功、弹窗仍遮挡页面”的假成功。
                original_dialog = row.locator(
                    "div.declare-original-dialog div.weui-desktop-dialog__wrp"
                ).first
                try:
                    if await original_dialog.count() and await original_dialog.is_visible():
                        terms_checkbox = original_dialog.locator('input[type="checkbox"]').first
                        if not await terms_checkbox.count():
                            raise RuntimeError("原创权益弹窗中未找到条款确认 checkbox")
                        if not await terms_checkbox.is_checked():
                            await terms_checkbox.check(force=True)
                            await page.wait_for_timeout(300)

                        declare_button = original_dialog.get_by_role(
                            "button", name="声明原创", exact=True
                        ).first
                        if not await declare_button.count():
                            declare_button = original_dialog.locator(
                                'button:has-text("声明原创")'
                            ).first
                        if not await declare_button.count() or not await declare_button.is_visible():
                            raise RuntimeError("原创权益弹窗中未找到可见的『声明原创』按钮")
                        if not await declare_button.is_enabled():
                            raise RuntimeError("已勾选原创条款，但『声明原创』按钮仍不可用")
                        await declare_button.click()
                        try:
                            await original_dialog.wait_for(state="hidden", timeout=5000)
                        except Exception as exc:
                            raise RuntimeError("已点击『声明原创』，但原创权益弹窗未关闭") from exc
                except Exception as dialog_exc:
                    tencent_logger.error(_msg("🧾", f"原创权益弹窗处理失败: {dialog_exc}"))
                    raise

                verified = await checkbox.is_checked()
                dialog_still_visible = False
                try:
                    dialog_still_visible = bool(
                        await original_dialog.count() and await original_dialog.is_visible()
                    )
                except Exception:
                    pass
                if not verified or dialog_still_visible:
                    try:
                        await page.screenshot(
                            path=str(BASE_DIR / "debug_tencent_original_control.png"),
                            full_page=True,
                        )
                        debug_html = await original_text.evaluate(
                            "el => { const rows=[]; let node=el; for(let i=0;i<6 && node;i++,node=node.parentElement){ rows.push(node.outerHTML.slice(0,2500)); } return rows.join(' ---PARENT--- '); }"
                        )
                        tencent_logger.info(_msg("🧾", f"原创控件现场 DOM: {debug_html[:12000]}"))
                    except Exception as debug_exc:
                        tencent_logger.warning(_msg("🧾", f"原创控件现场抓取失败: {debug_exc}"))
                    raise RuntimeError("已点击『声明原创』，但页面未能确认最终原创状态")
                tencent_logger.success(_msg("✅", "已勾选并确认：声明原创"))
            else:
                original_lines = []
                for scope in scopes:
                    try:
                        bodies = scope.locator("body")
                        for index in range(await bodies.count()):
                            body_text = await bodies.nth(index).inner_text()
                            original_lines.extend(
                                line.strip()
                                for line in body_text.splitlines()
                                if "原创" in line or "声明" in line or "标注" in line
                            )
                    except Exception:
                        continue
                if original_lines:
                    tencent_logger.info(_msg("🧾", f"页面中与原创/声明相关的文案: {original_lines[:20]}"))
                raise RuntimeError("当前页面未识别到『声明原创』入口，已停止发布以避免漏勾原创")
        except Exception as exc:
            tencent_logger.error(_msg("😵", f"设置「声明原创」失败，停止发布：{exc}"))
            raise

        # 当前账号发布规则：只勾选「声明原创」，视频标注保持未选择。
        # 不在这里自动选择「含AI生成内容」或其他视频标注。
        tencent_logger.info(_msg("🏷️", "视频标注保持未选择"))

    async def apply_ai_label(self, page: Page) -> None:
        """显式 opt-in：为AI生成内容在「视频标注」下拉中选择AI生成标注。

        仅当 SAU_TENCENT_AI_LABEL=1 时调用；找不到标注入口则 fail-closed 抛错，
        绝不静默跳过（漏标AI生成属于合规风险）。

        2026-10-20 根因修复：视频标注是 .mark-tag-select 下拉框，选项由
        finderGetObjectTagList 接口动态加载，且选项文本只在下拉展开后才渲染进
        DOM。旧代码直接按文本查找「人工智能生成」，展开前必然找不到导致
        fail-closed。现在先展开下拉再匹配选项。
        """
        last_err = None
        # 1) 定位「视频标注」所在的 form-item 行（可能位于 iframe 中）
        for scope in [page, *page.frames]:
            try:
                label = scope.get_by_text("视频标注", exact=True).first
                if not await label.count():
                    continue
                row = label.locator("xpath=ancestor::div[contains(@class,'form-item')][1]").first
                if not await row.count():
                    continue
                select = row.locator(".mark-tag-select").first
                if not await select.count():
                    continue
                await select.scroll_into_view_if_needed()
                await select.click()
                options = scope.locator(".mark-tag-options")
                await options.wait_for(state="visible", timeout=5000)
                # 2) 在展开的选项中匹配 AI 相关标注
                for label_text in ("内容由AI生成", "AI生成", "含AI生成内容", "人工智能生成", "由AI生成"):
                    option = options.get_by_text(label_text, exact=False).first
                    try:
                        await option.wait_for(timeout=1500)
                        await option.click()
                        await page.wait_for_timeout(800)
                        # 3) 部分 tagType 会弹确认对话框，需要点确认
                        dialog = scope.locator(".weui-desktop-dialog__wrp").first
                        try:
                            if await dialog.count() and await dialog.is_visible():
                                for btn_text in ("确定", "确认", "声明", "提交", "我知道了", "知道了"):
                                    btn = dialog.get_by_role("button", name=btn_text).first
                                    if await btn.count() and await btn.is_visible() and await btn.is_enabled():
                                        await btn.click()
                                        await page.wait_for_timeout(600)
                                        break
                        except Exception:
                            pass
                        tencent_logger.success(_msg("✅", f"已选择视频标注：{label_text}"))
                        await page.screenshot(path=str(BASE_DIR / "debug_tencent_ai_label.png"))
                        return
                    except Exception as exc:
                        last_err = exc
                        continue
                # 下拉已展开但没有匹配到任何 AI 选项文本——把实际选项 dump 出来再报错
                try:
                    opts_text = await options.inner_text()
                    tencent_logger.info(_msg("🧾", f"视频标注下拉实际选项: {opts_text[:500]}"))
                except Exception:
                    pass
            except Exception as exc:
                last_err = exc
                continue
        shot = BASE_DIR / "debug_tencent_ai_label_missing.png"
        await page.screenshot(path=str(shot), full_page=True)
        raise RuntimeError(
            f"未找到『视频标注/AI生成』入口，无法声明AI生成，按 fail-closed 停止发布（截图 {shot}）: {last_err}"
        )

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
                # 平台的表单校验错误会让「发表」长期保持 disabled。以前把这种状态
                # 误判成“视频仍在上传”，最终白等一小时。遇到可见校验错误应立即失败，
                # 把真正原因暴露出来。
                visible_errors = page.locator('.error-title:visible')
                if await visible_errors.count():
                    messages = []
                    for index in range(await visible_errors.count()):
                        text = (await visible_errors.nth(index).inner_text()).strip()
                        if text:
                            messages.append(text)
                    if messages:
                        raise RuntimeError("视频号发布表单校验失败：" + "；".join(dict.fromkeys(messages)))

                publish_button = page.locator('div.form-btns button:has-text("发表"):visible').first
                if await publish_button.count():
                    button_class = await publish_button.get_attribute("class")
                    if (
                        not await publish_button.is_disabled()
                        and (not button_class or "weui-desktop-btn_disabled" not in button_class)
                    ):
                        # 填写短标题后「发表」会立刻解除 disabled，但视频往往还在传。
                        # 封面区此时会盖着 .vertical-mask-layer，并提示「文件上传中」。
                        # 必须等这两个信号消失，才能进入封面编辑。
                        waited_so_far = int(timeout_seconds - (deadline - time.monotonic()))
                        uploading_mask = page.locator(".vertical-mask-layer:visible")
                        uploading_text = page.locator(':text("文件上传中"):visible')
                        mask_count = await uploading_mask.count()
                        text_count = await uploading_text.count()
                        if waited_so_far < 5 or mask_count or text_count:
                            now = time.monotonic()
                            if now - last_report >= 30:
                                tencent_logger.info(
                                    _msg(
                                        "🏃",
                                        "视频仍在上传"
                                        f"（发表按钮已可点，遮罩 {mask_count}，上传提示 {text_count}）"
                                        f"...（已等 {waited_so_far} 秒）",
                                    )
                                )
                                last_report = now
                            await asyncio.sleep(2)
                            continue
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
        publish_btn = (page.get_by_role("button", name="保存草稿").first if is_draft
                       else page.get_by_role("button", name="发表", exact=True).first)
        # Never force a hidden/disabled control or repeat an ambiguous submission.
        for _ in range(60):
            await self._dismiss_switch_account_dialog(page)
            if (await publish_btn.count() and await publish_btn.is_visible()
                    and await publish_btn.is_enabled()):
                break
            await asyncio.sleep(1)
        else:
            raise RuntimeError("发表/草稿按钮不可用，停止；不强制点击")
        try:
            await publish_btn.click(timeout=4000)
        except Exception as exc:
            raise RuntimeError("提交点击结果不明，停止；核对后台后再决定是否重试") from exc
        if is_draft:
            await page.wait_for_url("**/post/list**", timeout=10000)
            tencent_logger.success(_msg("🥳", "视频草稿保存成功"))
            return
        # 2026-10-24：加入创作分成计划后，点「发表」会弹「是否声明原创」确认框。
        # 用户既定政策：视频号照常声明原创 → 自动点「声明原创」继续。
        # 弹窗渲染在 <wujie-app> 的 shadow DOM 里：frame.evaluate + querySelectorAll
        # 穿不透，所以旧版 JS 点击一直报 no_dialog。改用 Playwright 定位器（可穿透 open shadow DOM）。
        # 只点「声明原创」，绝不点「直接发表」/「不再提醒」（那样会以非原创发出）。
        try:
            declare_btns = page.get_by_role("button", name="声明原创", exact=True)
            clicks = 0
            for _ in range(15):
                if "/post/list" in page.url:
                    break
                visible_btn = None
                for i in range(await declare_btns.count()):
                    btn = declare_btns.nth(i)
                    if await btn.is_visible():
                        visible_btn = btn
                if visible_btn is None:
                    await asyncio.sleep(1)
                    continue
                # 第二层弹窗需先勾「我已阅读并同意」条款
                dialog = visible_btn.locator(
                    "xpath=ancestor::div[contains(@class,'dialog')][1]"
                )
                if await dialog.count():
                    terms = dialog.locator('input[type="checkbox"]')
                    for i in range(await terms.count()):
                        if not await terms.nth(i).is_checked():
                            await terms.nth(i).check(force=True)
                            await page.wait_for_timeout(300)
                if await visible_btn.is_enabled():
                    await visible_btn.click(timeout=4000)
                    clicks += 1
                    tencent_logger.info(_msg("✅", f"已按既定政策点击弹窗「声明原创」（第 {clicks} 次）"))
                    if clicks >= 4:
                        break
                await asyncio.sleep(1.5)
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"分成计划原创弹窗处理异常: {exc}"))
        for _ in range(10):
            await asyncio.sleep(1)
            if "/post/list" in page.url:
                tencent_logger.info(_msg("🧾", "提交后进入作品列表；发布状态与封面仍待独立核验"))
                return
        try:
            shot = Path(BASE_DIR) / "debug_tencent_submit_stuck.png"
            await page.screenshot(path=str(shot), full_page=True)
            tencent_logger.warning(_msg("📸", f"提交后页面未跳转，现场已截图 {shot}"))
            walk = ("(() => { function dig(root){ let out=''; for(const el of root.querySelectorAll('*')){ if(el.shadowRoot) out+=(el.shadowRoot.textContent||'')+dig(el.shadowRoot); } return out } "
                    "let t=document.body?document.body.innerText:''; t+='\\n@@SHADOW@@'+dig(document); return t.slice(0,30000) })()")
            lines = []
            for fi, fr in enumerate(page.frames):
                try:
                    t = await fr.evaluate(walk)
                    lines.append(f"FRAME#{fi} url={fr.url}\n{t}\n")
                except Exception as e:
                    lines.append(f"FRAME#{fi} url={fr.url} ERR={e}\n")
            (Path(BASE_DIR) / "debug_tencent_frames.txt").write_text("\n=====\n".join(lines), encoding="utf-8")
            tencent_logger.warning(_msg("🔎", f"各 frame 文本已导出 debug_tencent_frames.txt（{len(page.frames)} frames）"))
            tencent_logger.warning(_msg("🔎", "弹窗 DOM 已导出 debug_tencent_dialog.html"))
        except Exception:
            pass
        raise RuntimeError("提交后未取得作品列表回执，结果未知；不重复点击，不记为已发布")


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
        # 视频号会分别使用 4:3「视频号动态」封面和 3:4「个人主页卡片」封面。
        # 大格局视界要求两个展示位都必须使用设计封面；缺任意一张就停止发布，
        # 避免出现“3:4 设置成功，但动态页仍显示系统自动截帧”的假成功。
        if not self.thumbnail_landscape_path or not self.thumbnail_portrait_path:
            raise ValueError(
                "视频号发布必须同时提供 4:3 横版封面和 3:4 竖版封面："
                "请同时传 --thumbnail-landscape 与 --thumbnail-portrait"
            )
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
        clicked_entry = False
        for selector in selectors:
            entries = page.locator(selector)
            for index in range(await entries.count()):
                cover_entry = entries.nth(index)
                try:
                    if not await cover_entry.is_visible():
                        continue
                    # 新版视频号会先异步生成默认封面。此时 3:4 封面位已经可见，
                    # 但仍显示“生成中”，点击不会打开编辑弹窗。旧逻辑只等 500ms，
                    # 因而稳定误报“没有出现封面编辑入口”。等默认封面生成完成再点。
                    generation_deadline = time.monotonic() + 120
                    while time.monotonic() < generation_deadline:
                        entry_text = (await cover_entry.inner_text()).strip()
                        loading = cover_entry.locator('.loading-wrap:visible, .gen-text:visible')
                        blocked = cover_entry.locator('.vertical-mask-layer:visible')
                        if (
                            "生成中" not in entry_text
                            and not await loading.count()
                            and not await blocked.count()
                        ):
                            break
                        await page.wait_for_timeout(500)
                    else:
                        # 不能再把隐藏的编辑器 wrapper 直接改成 display:block。
                        # 那只是把 Vue 已挂载但尚未激活的组件“画出来”，编辑器里虽然
                        # 能看到上传预览，点击“确认”却不会把状态提交回发布页，最终会
                        # 用平台默认截帧发布。必须通过真实封面位的点击事件打开编辑器。
                        # 遮罩只影响命中测试，因此用 DOM click 触发绑定在预览/容器上的
                        # 真实事件；如果组件状态没有因此打开，就直接失败，禁止发布。
                        preview_image = cover_entry.locator('img').first
                        clicked = False
                        if await preview_image.count():
                            try:
                                await preview_image.evaluate("el => el.click()")
                                clicked = True
                            except Exception:
                                pass
                        if not clicked:
                            await cover_entry.evaluate("el => el.click()")

                        real_dialog = page.locator(
                            '.edit-cover-dialog > .weui-desktop-dialog__wrp > .weui-desktop-dialog'
                        ).first
                        try:
                            await real_dialog.wait_for(state="visible", timeout=5000)
                            tencent_logger.warning(
                                _msg("🖼️", "平台默认封面仍在生成，但已通过真实封面位打开编辑器")
                            )
                            return real_dialog
                        except Exception as exc:
                            raise RuntimeError(
                                "平台默认封面生成超时，且真实封面位未能打开编辑器；停止发布"
                            ) from exc

                    # 新版封面位的点击事件绑定在编辑按钮或预览图上；直接点外层 wrap 可能无法打开“编辑封面”
                    edit_btn = cover_entry.locator('.edit-btn, button:has-text("编辑"), span:has-text("编辑")').first
                    preview_image = cover_entry.locator('img').first
                    if await edit_btn.count():
                        try:
                            await edit_btn.click(timeout=2000)
                        except Exception:
                            await edit_btn.evaluate("el => el.click()")
                    elif await preview_image.count():
                        try:
                            await preview_image.click(timeout=2000)
                        except Exception:
                            await preview_image.evaluate("el => el.click()")
                    else:
                        try:
                            await cover_entry.click(timeout=2000)
                        except Exception:
                            await cover_entry.evaluate("el => el.click()")
                    await page.wait_for_timeout(1000)
                    clicked_entry = True
                    break
                except Exception:
                    continue
            if clicked_entry:
                break

        if not clicked_entry:
            try:
                preview_wraps = page.locator("div.cover-preview-wrap")
                for preview_index in range(await preview_wraps.count()):
                    preview = preview_wraps.nth(preview_index)
                    if await preview.is_visible():
                        preview_html = await preview.evaluate("el => el.outerHTML")
                        tencent_logger.info(
                            _msg("🧾", f"封面预览 DOM[{preview_index}]: {preview_html[:16000]}")
                        )
                shot = Path(BASE_DIR) / "debug_tencent_cover_entry_missing.png"
                await page.screenshot(path=str(shot), full_page=True)
                tencent_logger.info(_msg("📸", f"封面入口未识别，现场已截图: {shot}"))
            except Exception as debug_exc:
                tencent_logger.warning(_msg("🧾", f"封面入口现场抓取失败: {debug_exc}"))
            return None

        dialog_deadline = time.monotonic() + 10
        found_titles = []
        while time.monotonic() < dialog_deadline:
            # 兼容普通弹窗以及封面专属 edit-cover-dialog
            all_dialogs = page.locator("div.weui-desktop-dialog, div.edit-cover-dialog")
            for d_idx in range(await all_dialogs.count()):
                d = all_dialogs.nth(d_idx)
                try:
                    # 检查元素本身或其子容器是否在视觉上可见（display != 'none'）
                    is_vis = await d.evaluate("""el => {
                        const style = window.getComputedStyle(el);
                        const wrp = el.closest('.weui-desktop-dialog__wrp') || el.querySelector('.weui-desktop-dialog__wrp');
                        const wrpStyle = wrp ? window.getComputedStyle(wrp) : null;
                        if (style.display === 'none' || style.visibility === 'hidden') return false;
                        if (wrpStyle && (wrpStyle.display === 'none' || wrpStyle.visibility === 'hidden')) return false;
                        return true;
                    }""")
                    if not is_vis:
                        continue
                    title_elem = d.locator('.weui-desktop-dialog__title').first
                    t_text = (await title_elem.inner_text()).strip() if await title_elem.count() else ""
                    if t_text not in found_titles:
                        found_titles.append(t_text)
                    for title in dialog_titles:
                        if title in t_text:
                            inner_dialog = d.locator('div.weui-desktop-dialog').first
                            return inner_dialog if await inner_dialog.count() else d
                except Exception:
                    continue
            await page.wait_for_timeout(250)
        tencent_logger.warning(_msg("⚠️", f"寻找弹窗 {dialog_titles} 超时，当前可见弹窗标题: {found_titles}"))
        return None

    async def confirm_thumbnail_crop(self, page: Page) -> None:
        # “编辑封面”父弹窗 DOM 内嵌了“裁剪封面图”子弹窗，因此用 has_text
        # 会误命中父弹窗，随后取到一个隐藏的“确定”按钮并卡到超时。
        crop_title = page.get_by_text("裁剪封面图", exact=True).first
        crop_dialog = crop_title.locator(
            "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' weui-desktop-dialog ')][1]"
        )
        # 新版上传器对符合目标比例的封面会直接生成 finish-wrap 预览，不再
        # 弹出“裁剪封面图”窗口。此时不是失败，应继续确认父级“编辑封面”。
        if not await crop_dialog.count() or not await crop_dialog.is_visible():
            return

        try:
            await crop_dialog.wait_for(state="visible", timeout=10000)
            crop_confirm_button = crop_dialog.locator(
                'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确定")'
            ).first
            if not await crop_confirm_button.count():
                raise RuntimeError("裁剪窗口缺少确定按钮")
            await crop_confirm_button.wait_for(state="visible", timeout=5000)
            await crop_confirm_button.click()
            await crop_dialog.wait_for(state="hidden", timeout=10000)
        except Exception as exc:
            raise RuntimeError("封面裁剪未确认，停止发布") from exc

    async def upload_thumbnail_in_dialog(self, page: Page, cover_dialog, thumbnail_path: str) -> bool:
        await cover_dialog.wait_for(state="visible", timeout=5000)
        file_input = cover_dialog.locator('.single-cover-uploader-wrap input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(thumbnail_path)
        await self.confirm_thumbnail_crop(page)

        # The Channels front end can leave the outer cover slot stuck on
        # "generating" even though the uploaded cover has already rendered in
        # the editor. Verify that editor preview against the exact source file
        # before clicking Confirm, so the fallback path still has a strict
        # image gate instead of accepting a random/generated frame.
        # Newer Channels builds render the uploaded 3:4 image in a separate
        # preview card (for example .vertical-preview-image), outside the
        # uploader wrapper. Inspect every visible image in this cover dialog
        # and accept only one that passes the exact source-image comparison.
        preview_candidates = cover_dialog.locator('img:visible')
        preview_deadline = time.monotonic() + 15
        preview_error = None
        dialog_preview_verified = False
        while time.monotonic() < preview_deadline and not dialog_preview_verified:
            for index in range(await preview_candidates.count()):
                candidate = preview_candidates.nth(index)
                try:
                    loaded = await candidate.evaluate("el => el.complete && el.naturalWidth > 0")
                    if not loaded:
                        continue
                    shot = await candidate.screenshot(timeout=1500)
                    verify_cover_preview(thumbnail_path, shot)
                    dialog_preview_verified = True
                    break
                except Exception as exc:
                    preview_error = exc
            if not dialog_preview_verified:
                await page.wait_for_timeout(300)
        if not dialog_preview_verified:
            try:
                debug_dir = Path(BASE_DIR) / "debug_cover_candidates"
                debug_dir.mkdir(parents=True, exist_ok=True)
                html = await cover_dialog.evaluate("el => el.outerHTML")
                (debug_dir / "dialog.html").write_text(html, encoding="utf-8")
                all_images = cover_dialog.locator('img')
                for index in range(await all_images.count()):
                    img = all_images.nth(index)
                    try:
                        info = await img.evaluate(
                            "el => ({src: el.src, cls: el.className, w: el.naturalWidth, h: el.naturalHeight, visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)})"
                        )
                        tencent_logger.info(_msg("🧾", f"封面弹窗图片[{index}]: {info}"))
                        if info.get("visible") and info.get("w", 0) > 0:
                            await img.screenshot(path=str(debug_dir / f"candidate_{index}.png"), timeout=1500)
                    except Exception as debug_exc:
                        tencent_logger.warning(_msg("🧾", f"封面候选[{index}]抓取失败: {debug_exc}"))
                await cover_dialog.screenshot(path=str(debug_dir / "dialog.png"))
                tencent_logger.info(_msg("📸", f"封面弹窗调试现场已保存: {debug_dir}"))
            except Exception as debug_exc:
                tencent_logger.warning(_msg("🧾", f"封面弹窗调试抓取失败: {debug_exc}"))
            raise RuntimeError("封面编辑器中的上传预览未通过原图比对") from preview_error
        tencent_logger.success(_msg("🥳", "封面编辑器上传预览已通过原图比对"))

        confirm_button = cover_dialog.locator(
            'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确认")'
        ).first
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()
        try:
            await cover_dialog.wait_for(state="hidden", timeout=15000)
            return True
        except Exception:
            # 当平台默认封面长期停在“生成中”时，我们会直接启用已经挂载在
            # DOM 里的编辑组件。这个异常分支中“确认”有时已经应用上传封面，
            # 但弹窗本身不会自动收起。先允许外层逻辑核验发布页预览；只有
            # 原图比对通过后，才会主动收起残留弹窗并继续发布。
            tencent_logger.warning(
                _msg("🖼️", "封面确认后弹窗未自动关闭，继续核验发布页封面是否已生效")
            )
            return False

    async def dismiss_thumbnail_dialog(self, page: Page, cover_dialog) -> None:
        if not await cover_dialog.count() or not await cover_dialog.is_visible():
            return

        close_button = cover_dialog.locator(
            '.weui-desktop-dialog__close, button[aria-label="关闭"], [class*="close"]'
        ).first
        try:
            if await close_button.count() and await close_button.is_visible():
                await close_button.click()
                await cover_dialog.wait_for(state="hidden", timeout=3000)
                return
        except Exception:
            pass

        # 预览已经通过原图比对，说明封面状态已写入发布页。若前端残留的是
        # 被我们强制显示的挂载容器，可仅收起该 UI 容器，避免它挡住发布按钮。
        try:
            wrapper = cover_dialog.locator("xpath=parent::div").first
            if await wrapper.count():
                await wrapper.evaluate("el => el.style.display = 'none'")
        except Exception:
            await page.keyboard.press("Escape")

    @staticmethod
    async def _cover_preview_candidate(page: Page, selector: str):
        """从封面位容器中挑出真正的封面预览图，而不是「编辑」按钮的小图标。

        封面位里除了封面预览 <img>，还渲染了编辑按钮的图标 <img>（且常排在
        前面）。固定取 .first 会命中图标，导致原图比对恒定误报。这里按可见
        且尺寸达到封面量级（>=80px）筛选。
        """
        min_side = 80
        candidates = page.locator(selector)
        for index in range(await candidates.count()):
            candidate = candidates.nth(index)
            try:
                if not await candidate.is_visible():
                    continue
                box = await candidate.bounding_box()
                if box and box["width"] >= min_side and box["height"] >= min_side:
                    return candidate
            except Exception:
                continue
        return candidates.first

    async def verify_thumbnail_preview(
        self,
        page: Page,
        thumbnail_path: str,
        label: str,
        previous_src: str | None = None,
    ) -> None:
        selector = (
            "div.vertical-cover-wrap img:visible" if label.startswith("3:4")
            else "div.horizon-cover-wrap img:visible, div.horizontal-cover-wrap img:visible"
        )
        deadline = time.monotonic() + 20
        last_error = None
        while time.monotonic() < deadline:
            try:
                # 每轮重新扫描候选：封面预览是异步渲染的，首轮可能还没出现，
                # 只混有「编辑」按钮图标等小图。
                preview = await self._cover_preview_candidate(page, selector)
                if preview is None:
                    raise ValueError("封面位未出现封面量级的预览图（可能仍在渲染）")
                await preview.wait_for(state="visible", timeout=1000)
                loaded = await preview.evaluate("el => el.complete && el.naturalWidth > 0")
                if not loaded:
                    raise ValueError("封面预览仍未加载完成")
                current_src = await preview.get_attribute("src")
                # 点击父弹窗“确认”后，页面封面图是异步替换的。若立即截图，
                # 很容易仍抓到平台自动生成的旧封面，从而把成功上传误判成失败。
                if previous_src and current_src == previous_src:
                    raise ValueError("封面预览仍是确认前的旧图，等待页面刷新")
                shot = await preview.screenshot(timeout=1500)
                try:
                    verify_cover_preview(thumbnail_path, shot)
                except Exception as ve_err:
                    debug_dir = Path(BASE_DIR) / "debug_cover_candidates"
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    await preview.screenshot(path=str(debug_dir / f"failed_{label.replace(' ', '_')}.png"))
                    tencent_logger.warning(_msg("⚠️", f"{label}比对未通过详情: {ve_err} (截图已存至 {debug_dir})"))
                    raise
                return
            except Exception as exc:
                last_error = exc
                await page.wait_for_timeout(300)
        raise RuntimeError(f"{label}封面预览未通过原图比对，停止发布") from last_error

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
            raise RuntimeError(f"当前页面没有出现{label}封面编辑入口或可见弹窗")

        try:
            preview_selector = (
                "div.vertical-cover-wrap img:visible" if label.startswith("3:4")
                else "div.horizon-cover-wrap img:visible, div.horizontal-cover-wrap img:visible"
            )
            preview_before = await self._cover_preview_candidate(page, preview_selector)
            previous_src = None
            if await preview_before.count():
                previous_src = await preview_before.get_attribute("src")
            dialog_closed = await self.upload_thumbnail_in_dialog(page, cover_dialog, thumbnail_path)
            if not dialog_closed:
                raise RuntimeError("封面编辑器点击确认后未关闭，无法证明封面已提交到发布页")
            await self.verify_thumbnail_preview(page, thumbnail_path, label, previous_src=previous_src)
            if not dialog_closed:
                await self.dismiss_thumbnail_dialog(page, cover_dialog)
            tencent_logger.success(_msg("🥳", f"{label}发布页封面预览通过原图比对，发布后结果仍需核验"))
        except Exception as exc:
            tencent_logger.error(_msg("😵", f"{label}封面设置失败，停止发布: {exc}"))
            raise

    async def set_thumbnail(self, page: Page) -> None:
        if not self.thumbnail_landscape_path and not self.thumbnail_portrait_path:
            return

        tencent_logger.info(_msg("🖼️", "小人准备设置封面"))

        landscape_selectors = [
            'div.horizon-cover-wrap:has-text("4:3")',
            'div.horizon-cover-wrap',
            'div.horizontal-cover-wrap:has-text("4:3")',
            'div[class*="cover-wrap"]:has-text("4:3"):has-text("动态")',
            'div:has-text("视频号动态"):has-text("4:3")',
            'div:has-text("横版封面"):has-text("4:3")',
        ]
        portrait_selectors = [
            'div.vertical-cover-wrap',
            'div.vertical-cover-wrap:has-text("个人主页卡片"):has-text("3:4")',
            'div.vertical-cover-wrap:has-text("3:4")',
            'div.vertical-cover-wrap:has-text("个人主页卡片")',
            'div[class*="vertical-cover"]:has-text("3:4")',
            'div:has-text("个人主页卡片")',
        ]

        # 视频号当前前端只在横屏视频（width / height > 1）时渲染独立的
        # 4:3 分享卡片封面（.horizon-cover-wrap）。竖屏视频只有一个
        # “个人主页和分享卡片(3:4)”封面位，3:4 同时用于主页与分享场景。
        # 因此以页面实际渲染的封面位为准做硬校验，避免把“不存在的 4:3 控件”
        # 误判成上传失败。
        visible_horizon_cover = False
        horizon_entries = page.locator("div.horizon-cover-wrap")
        for index in range(await horizon_entries.count()):
            try:
                if await horizon_entries.nth(index).is_visible():
                    visible_horizon_cover = True
                    break
            except Exception:
                continue

        if self.thumbnail_landscape_path and visible_horizon_cover:
            try:
                await self.set_single_thumbnail(
                    page,
                    self.thumbnail_landscape_path,
                    landscape_selectors,
                    ["编辑分享卡片", "编辑视频号动态封面", "编辑动态封面", "编辑封面", "编辑横版封面"],
                    "4:3 横版",
                )
            except Exception as e:
                tencent_logger.warning(_msg("⚠️", f"4:3 横版封面入口打开或核验异常({e})，尝试直接处理 3:4 主封面"))
        elif self.thumbnail_landscape_path:
            vertical_slot = page.locator("div.vertical-cover-wrap").filter(has_text="3:4").first
            if await vertical_slot.count() and await vertical_slot.is_visible():
                tencent_logger.info(
                    _msg("🖼️", "当前为竖屏视频：平台仅提供『个人主页和分享卡片(3:4)』封面位，不生成独立 4:3 封面位")
                )
            else:
                raise RuntimeError("既未发现 4:3 横版封面位，也未确认竖屏视频的 3:4 单封面位")
        # 视频号新版前端规则：
        # 对于横屏视频（16:9），平台主位是 4:3 横版封面；如果 4:3 封面已成功设置并核验通过，
        # 而 3:4 竖版入口未提供或为只读同步位时，可降级为仅以 4:3 封面作为有效封面发布；
        # 对于竖屏视频（9:16），3:4 是唯一核心封面，仍必须严格设置并核验。
        if self.thumbnail_portrait_path:
            try:
                await self.set_single_thumbnail(
                    page,
                    self.thumbnail_portrait_path,
                    portrait_selectors,
                    ["编辑个人主页卡片", "编辑封面", "编辑主页封面", "设置封面", "编辑分享卡片"],
                    "3:4 竖版",
                )
            except Exception as e:
                if self.thumbnail_landscape_path and visible_horizon_cover:
                    tencent_logger.warning(_msg("⚠️", f"横屏视频已成功设置 4:3 封面，3:4 封面位未单独开放弹窗({e})，按平台当前横屏模式继续发布"))
                else:
                    raise

    async def prepare_video_for_publish(self, page: Page) -> None:
        await self.wait_for_realtime_verification(page)
        await self.fill_title_and_tags(page)
        await self.fill_description(page)
        # 短标题属于发布按钮的前置校验项。必须在 wait_for_upload_complete() 之前填写，
        # 否则视频即使已经上传完成，「发表」仍会保持 disabled，旧逻辑会误等到超时。
        await self.set_short_title(page, self.title, self.short_title)
        # 合集不在这里选：此时视频还在上传，上传完成后表单会刷新，
        # 上传中选的合集会被重置/不绑定（"日志说选了、后台没加"的根因）。
        # 改到 wait_for_upload_complete 之后再选，见 upload()。

    async def upload(self, playwright: Playwright) -> None:
        require_dageju_release(self)
        tencent_logger.info(_msg("🧍", "小人先检查 cookie、视频文件和发布时间"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "上传前检查通过"))

        context = await launch_tencent_context(
            playwright=playwright,
            account_file=self.account_file,
            headless=self.headless,
            executable_path=self.local_executable_path,
        )

        modal_guard = None
        try:
            page = await context.new_page()
            # 全程弹窗守护：平台 JS 会不定期弹 #error-modal 拦截所有点击，
            # 后台任务每 1.5 秒清理一次，直到发布流程结束。
            modal_guard = asyncio.create_task(self._modal_guard_loop(page))
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}"))

            await self.upload_video_file(page, self.file_path)
            await self.prepare_video_for_publish(page)
            await self.wait_for_upload_complete(page)
            # 上传完成、表单稳定后再选合集（否则上传中选的会被重置）
            await self.apply_collection(page)
            if os.environ.get('SAU_TENCENT_DECLARE_ORIGINAL', '1') == '1':
                await self.apply_original_statement(page)
            if os.environ.get("SAU_TENCENT_AI_LABEL") == "1":
                await self.apply_ai_label(page)
            await self.set_thumbnail(page)

            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)

            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            tencent_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            if modal_guard is not None:
                modal_guard.cancel()
            await context.close()

    async def tencent_upload_video(self):
        require_dageju_release(self)
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

        context = await launch_tencent_context(
            playwright=playwright,
            account_file=self.account_file,
            headless=self.headless,
            executable_path=self.local_executable_path,
        )

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

    async def tencent_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_note()
