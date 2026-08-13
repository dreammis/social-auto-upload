# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
import json as _json
import os
import re
import time
from pathlib import Path

from playwright.async_api import Page, Playwright, TimeoutError as PWTimeoutError, async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import alipay_logger
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file

ALIPAY_HOME_URL = "https://c.alipay.com/"
ALIPAY_PORTAL_HOME = "https://c.alipay.com/page/portal/home"
# 内容创作平台入口：必须带 _appScene=CONTENT&appId=xxx，否则会跳到生活号开通页 signup
ALIPAY_LIFE_ACCOUNT_URL = "https://c.alipay.com/page/life-account/index?_appScene=CONTENT&appId=2030022469359777"
ALIPAY_POSTS_URL = "https://c.alipay.com/page/content-creation/posts"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _build_login_result(success: bool, status: str, message: str, account_file: str, qrcode: dict | None = None, current_url: str = "") -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return
    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {"headless": headless}
    if LOCAL_CHROME_PATH:
        launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
    return launch_kwargs


def _resolve_account_file(account_file: str | Path) -> str:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return str(path)

    if len(path.parts) == 1:
        return str((Path(BASE_DIR) / "cookies" / "alipay_uploader" / path).resolve())

    return str(path.resolve())


def format_title_with_tags(title: str, tags: list[str], max_length: int = 30) -> str:
    """支付宝生活号的标签是 #tag 格式，拼在标题末尾一起填入标题输入框。

    按标签边界截断：先保证标题完整，再逐个追加标签，加不下的**整个标签丢弃**，
    绝不留半个标签或裸 `#`。这避免触发支付宝"断字"优化项弹窗阻断发布。
    """
    if not tags:
        return title[:max_length]
    result = title
    for tag in tags:
        candidate = result + " #" + tag.strip("#")
        if len(candidate) > max_length:
            break
        result = candidate
    return result


async def _capture_alipay_qr(page: Page, account_file: str, previous_qrcode_path: Path | None = None) -> dict:
    """严格按支付宝登录页固定 DOM 截二维码（只认扫码 tab + barcode canvas）。"""
    login_iframe = page.locator('iframe[title="login"]')
    await login_iframe.first.wait_for(state="attached", timeout=30000)
    frame = page.frame_locator('iframe[title="login"]')

    try:
        await frame.locator("#J-loginMethod-tabs").first.wait_for(state="visible", timeout=15000)
        # 固定切到扫码 tab（若本来已是扫码，重复点击无副作用）
        await frame.locator("#J-loginMethod-tabs li[data-status='show_qr']").first.click(timeout=5000)
    except PWTimeoutError:
        # 兼容另一种渲染：直接落在扫码区（无 tabs）
        pass

    # 只认二维码容器，不认账密元素
    await frame.locator("#J-qrcode, #J-barcode-container").first.wait_for(state="visible", timeout=25000)
    await frame.locator("#J-barcode-container canvas.barcode, #J-barcode-container canvas").first.wait_for(state="visible", timeout=25000)

    # 账密区域在扫码模式下应隐藏
    try:
        login_panel = frame.locator("#J-login")
        if await login_panel.count():
            klass = (await login_panel.first.get_attribute("class") or "")
            if "fn-hide" not in klass:
                raise RuntimeError("当前仍处于账密登录面板（#J-login 未隐藏）")
    except RuntimeError:
        raise
    except Exception:
        pass

    qrcode_path = build_login_qrcode_path(account_file)
    qrcode_path.parent.mkdir(parents=True, exist_ok=True)

    qr_canvas = frame.locator("#J-barcode-container canvas.barcode, #J-barcode-container canvas").first
    await qr_canvas.screenshot(path=str(qrcode_path), timeout=15000)

    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            alipay_logger.info(_msg("🧹", f"临时二维码文件已清理: {previous_qrcode_path}"))
    alipay_logger.info(_msg("🖼️", f"二维码已保存到: {qrcode_path}"))
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, "支付宝APP")
    else:
        alipay_logger.warning(_msg("😵", f"终端没法完整显示二维码，请打开 {qrcode_path} 扫码"))
    return {"image_path": str(qrcode_path), "image_data_url": ""}


async def alipay_cookie_gen(account_file, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 100, headless: bool = LOCAL_CHROME_HEADLESS):
    """打开浏览器，用户扫码登录支付宝生活号，登录成功后保存 cookie（镜像 douyin_cookie_gen）。

    二维码 png 落 cookies 目录（*login_qrcode*.png）供终端显示/告知位置；qrcode_callback 可选（如 relogin 推飞书）。
    headless=False 时也可直接在弹出的浏览器里扫码。
    返回 _build_login_result 结果 dict。
    """
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)
    qrcode_path = None
    result = _build_login_result(False, "failed", "支付宝登录失败", account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        try:
            page = await context.new_page()
            # 注意：不能用 set_init_script(stealth) —— 实验证明 stealth 会阻止支付宝登录 iframe 注入
            # 先进受保护的后台页，未登录会触发登录弹窗（iframe[title="login"]，异步注入约 2~4s）
            await page.goto(ALIPAY_PORTAL_HOME, timeout=60000, wait_until="domcontentloaded")
            if headless:
                alipay_logger.info(_msg("🧍", "无头登录中：二维码已存为图片，请在终端扫或打开图片扫码（或由发布进程推送到飞书）"))
            else:
                alipay_logger.info(_msg("🧍", "请在打开的浏览器中扫码登录支付宝生活号（登录完成后请勿手动关闭浏览器）"))

            # 等登录 iframe 出现
            login_iframe = page.locator('iframe[title="login"]')
            for _ in range(30):
                try:
                    if await login_iframe.count():
                        break
                except Exception:
                    pass
                await page.wait_for_timeout(1000)
            else:
                await context.close()
                await browser.close()
                return _build_login_result(False, "timeout", "等待登录弹窗超时（30s），放弃保存", account_file, current_url=page.url)

            # 截图二维码（无头时给终端/飞书；有头时也截一份备用，不致命）
            qrcode_info = await _capture_alipay_qr(page, account_file)
            qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None
            await _emit_qrcode_callback(qrcode_callback, qrcode_info)
            alipay_logger.info(_msg("🧍", "请扫码，正在耐心等待登录完成"))

            # 轮询等待登录完成：登录 iframe 消失（登录成功后 auth 页会跳走）
            for _i in range(max_checks):  # 最多等 3~5 分钟
                if await _is_alipay_login_completed(page, login_iframe):
                    alipay_logger.info(_msg("🥳", f"扫码成功，已经跳转到登录后页面: {page.url}"))
                    result = _build_login_result(True, "success", "支付宝扫码登录成功", account_file, qrcode_info, page.url)
                    break
                await page.wait_for_timeout(poll_interval * 1000)
            else:
                result = _build_login_result(False, "timeout", "等待支付宝扫码登录超时", account_file, qrcode_info, page.url)

            if result["success"]:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                # 登录结束，轻量确认 cookie 文件里有点东西
                try:
                    _d = _json.load(open(account_file))
                    _has_cookie = any(c.get("value") for c in _d.get("cookies", []))
                    if not _has_cookie:
                        result = _build_login_result(False, "cookie_invalid", "支付宝扫码流程结束，但 cookie 为空", account_file, qrcode_info, page.url)
                except Exception as _e:
                    alipay_logger.warning(_msg("⚠️", f"cookie 文件校验异常（忽略，按成功处理）: {_e}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                alipay_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                alipay_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()
    return result


async def _is_alipay_login_completed(page: Page, login_iframe) -> bool:
    # 登录成功判定：登录 iframe 消失（登录成功后 auth 页会跳走），且 URL 回到 c.alipay.com 后台不算登录页
    try:
        if await login_iframe.count() != 0:
            return False
        url = page.url
        if url.startswith("https://c.alipay.com/") and "login" not in url.lower():
            return True
    except Exception:
        return False
    return False


async def cookie_auth(account_file):
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            page = await context.new_page()
            await page.goto(ALIPAY_LIFE_ACCOUNT_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # 登录会整页跳 auth.alipay.com；仍停留在 c.alipay.com 且不在 login 页才算有效
            url = page.url
            if url.startswith("https://auth.alipay.com/") or "login" in url.lower():
                alipay_logger.info(_msg("🥹", "cookie 已失效（跳转到登录页）"))
                return False
            if await page.locator('iframe[title="login"]').count():
                alipay_logger.info(_msg("🥹", "cookie 已失效（出现登录弹窗）"))
                return False

            alipay_logger.success(_msg("🥳", "cookie 有效"))
            return True
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"cookie 校验时出错，按失效处理: {exc}"))
            return False
        finally:
            await browser.close()


async def alipay_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie 文件不存在或已失效", account_file)
            return result if return_detail else False
        alipay_logger.info(_msg("🥹", "cookie 文件不存在或已失效，自动打开浏览器请扫码登录"))
        result = await alipay_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie 有效", account_file)
    return result if return_detail else True


class AlipayVideo(BaseVideoUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        account_file,
        desc: str | None = None,
        thumbnail_path: str | None = None,
        collection_name: str | None = None,
        debug: bool = True,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.account_file = _resolve_account_file(account_file)
        self.desc = desc or ""
        self.thumbnail_path = thumbnail_path
        self.collection_name = collection_name
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH
        self.max_title_length = 30

    async def validate_upload_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成支付宝生活号登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成支付宝生活号登录: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("视频模式下，title 是必须的")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_path:
            self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def open_upload_page(self, page: Page) -> None:
        # 进内容创作平台首页，点"发布视频"卡片（JS 跳转）进入短视频发布表单
        await page.goto(ALIPAY_LIFE_ACCOUNT_URL, timeout=120000, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        publish_entry = page.locator('a:has-text("发布视频推荐分辨率720p及以上，建议1080p")').first
        try:
            await publish_entry.wait_for(state="visible", timeout=30000)
            await publish_entry.click()
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"点击「发布视频」入口失败: {exc}"))
            raise

        await page.wait_for_url("**/content-creation/publish/short-video**", timeout=60000)

    async def upload_video_file(self, page: Page, file_path: str) -> None:
        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=30000)
        await file_input.set_input_files(file_path)
        alipay_logger.info(_msg("🏃", f"已选择视频文件: {file_path}"))

    async def fill_title_and_tags(self, page: Page) -> None:
        title_field = page.get_by_placeholder("一个好的标题，能获得更多人的喜欢哦").first
        await title_field.wait_for(state="visible", timeout=30000)
        value = format_title_with_tags(self.title, self.tags, max_length=self.max_title_length)
        await title_field.fill(value)
        alipay_logger.info(_msg("🏷️", f"标题已填写（含标签共 {len(value)} 字）: {value}"))

    async def fill_description(self, page: Page) -> None:
        if not self.desc:
            return
        desc_field = page.get_by_placeholder("填写作品描述，让你的作品更容易被看到").first
        await desc_field.fill(self.desc)
        alipay_logger.info(_msg("🏷️", f"作品描述已填写: {self.desc[:40]}"))

    async def upload_thumbnail(self, page: Page) -> None:
        if not self.thumbnail_path:
            return
        try:
            # 1) 点发布表单的"上传封面"入口，弹出"截取封面"弹窗
            cover_el = page.get_by_text("上传封面", exact=True).first
            await cover_el.scroll_into_view_if_needed()
            await cover_el.click(timeout=10000)
            await page.wait_for_timeout(2000)

            modal_body = page.locator(".antd5-modal-body").last

            # 2) 弹窗首次是"截取封面/上传封面"两入口；点"上传封面"展开图片上传区
            inner = modal_body.get_by_text("上传封面", exact=True).first
            if await inner.count():
                await inner.click(timeout=8000)
                await page.wait_for_timeout(1500)

            # 3) 点"上传图片"打开图片选择器
            upload_img_btn = modal_body.get_by_role("button", name="上传图片").first
            await upload_img_btn.wait_for(state="visible", timeout=10000)
            await upload_img_btn.click()
            await page.wait_for_timeout(1500)

            # 4) 设置图片到新出现的图片 file input
            img_input = page.locator('input[type="file"][accept*="jpg"], input[type="file"][accept*="png"]').first
            await img_input.wait_for(state="attached", timeout=10000)
            await img_input.set_input_files(self.thumbnail_path)
            await page.wait_for_timeout(3000)

            # 5) 裁剪弹窗里点"完 成"
            done_btn = page.get_by_role("button", name="完 成").first
            if not await done_btn.count():
                done_btn = page.get_by_role("button", name="完成").first
            await done_btn.wait_for(state="visible", timeout=15000)
            await done_btn.click()
            await page.wait_for_timeout(800)
            alipay_logger.success(_msg("🖼️", "封面已上传"))
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"封面上传失败，跳过继续: {exc}"))

    async def apply_collection(self, page: Page) -> None:
        if not self.collection_name:
            return
        try:
            # antd5-select：点击合集下拉的可点开关（compilation input 的父容器），展开选项
            compilation = page.locator('input[id*="_compilationInfo"]').first
            await compilation.scroll_into_view_if_needed()
            select = compilation.locator("xpath=../../..").first
            if not await select.count():
                select = page.locator(
                    '.antd5-select:has(.antd5-select-selection-placeholder)'
                ).first
            await select.click(timeout=8000)
            await page.wait_for_timeout(2000)

            # 只在选项里精确找映射合集名；找不到就不归集（用户后续手工建合集后会自动选中）
            options = page.locator('[role="option"]')
            target = options.filter(has_text=self.collection_name).first
            if await target.count():
                try:
                    await target.click(timeout=5000, force=True)
                except Exception:
                    await target.scroll_into_view_if_needed()
                    await target.click(timeout=5000)
                await page.wait_for_timeout(800)
                alipay_logger.success(_msg("🥳", f"已选择合集：{self.collection_name}"))
                return

            alipay_logger.warning(_msg("😵", f"账号中无「{self.collection_name}」合集，跳过归集"))
            await page.keyboard.press("Escape")
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"选择合集失败，跳过归集继续发布: {exc}"))

    async def check_ai_label(self, page: Page) -> None:
        # 作者声明是 radio 组（默认"内容无需标注"NO_STATEMENT），用 radio.check() 选中"内容由AI生成"(A_AG3)
        ai_label = page.locator('label.antd5-radio-wrapper', has_text="内容由AI生成").first
        try:
            if await ai_label.count():
                radio = ai_label.locator('input[type="radio"]').first
                await radio.scroll_into_view_if_needed()
                await radio.check(timeout=5000)
                await page.wait_for_timeout(500)
                alipay_logger.success(_msg("🏷️", "已勾选「内容由AI生成」"))
        except Exception as exc:
            alipay_logger.warning(_msg("😵", f"勾选「内容由AI生成」失败: {exc}"))

    async def wait_for_upload_complete(self, page: Page, timeout: int = 1800) -> None:
        # 等待"确认发布"按钮变为可点击（视频上传+转码完成）
        publish_btn = page.get_by_role("button", name="确认发布").first
        start = time.monotonic()
        while True:
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"等待视频上传/转码超时（>{timeout}s），确认发布按钮始终不可用")
            try:
                if not await publish_btn.count():
                    await asyncio.sleep(2)
                    continue
                if await publish_btn.is_disabled():
                    alipay_logger.info(_msg("🏃", "正在上传/转码视频中..."))
                    await asyncio.sleep(2)
                    continue
                alipay_logger.success(_msg("🥳", "视频上传完毕"))
                return
            except Exception:
                alipay_logger.info(_msg("🏃", "正在上传/转码视频中..."))
                await asyncio.sleep(2)

    async def submit_publish(self, page: Page) -> None:
        publish_btn = page.get_by_role("button", name="确认发布").first
        await publish_btn.wait_for(state="visible", timeout=30000)
        # 某些账号下点击后不会立即跳 posts，需同时观察成功提示文案
        if await publish_btn.is_disabled():
            raise RuntimeError("确认发布按钮仍不可点击，无法提交")

        # 只抓提交发布阶段的关键请求，失败时用于定位根因
        net_events: list[tuple[str, str, int | None, str]] = []
        req_events: list[tuple[str, str, str]] = []
        net_tasks: list[asyncio.Task] = []

        async def _collect_click_diag(tag: str):
            try:
                diag = await page.evaluate(
                    """
                    () => {
                      const btns = Array.from(document.querySelectorAll('button')).filter(b => (b.innerText || '').includes('确认发布'));
                      const confirmButtons = btns.map((b, i) => {
                        const r = b.getBoundingClientRect();
                        const cx = r.left + r.width / 2;
                        const cy = r.top + r.height / 2;
                        const topEl = document.elementFromPoint(cx, cy);
                        return {
                          i,
                          text: (b.innerText || '').trim(),
                          disabled: !!b.disabled,
                          ariaDisabled: b.getAttribute('aria-disabled'),
                          className: b.className,
                          rect: { x: r.x, y: r.y, w: r.width, h: r.height },
                          topElement: topEl ? `${topEl.tagName}.${topEl.className || ''}` : null,
                        };
                      });

                      const visibleModals = Array.from(document.querySelectorAll('.antd5-modal-wrap, .antd5-message, .antd5-notification')).filter(el => {
                        const st = window.getComputedStyle(el);
                        const r = el.getBoundingClientRect();
                        return st.display !== 'none' && st.visibility !== 'hidden' && r.width > 0 && r.height > 0;
                      }).slice(0, 5).map(el => ({
                        cls: el.className,
                        text: (el.textContent || '').trim().slice(0, 120),
                      }));

                      const errorHints = Array.from(document.querySelectorAll('.antd5-form-item-explain-error, .ant-form-item-explain-error, [class*="error"]')).map(el => (el.textContent || '').trim()).filter(Boolean).slice(0, 8);

                      return {
                        url: location.href,
                        title: document.title,
                        readyState: document.readyState,
                        confirmButtons,
                        visibleModals,
                        errorHints,
                        activeElement: document.activeElement ? `${document.activeElement.tagName}.${document.activeElement.className || ''}` : null,
                      };
                    }
                    """
                )
                alipay_logger.info(_msg("🔍", f"{tag}: {_json.dumps(diag, ensure_ascii=False)[:1000]}"))
            except Exception as exc:
                alipay_logger.warning(_msg("🔍", f"{tag}: 诊断采集失败: {exc}"))

        def _watch_url(url: str) -> bool:
            u = (url or "").lower()
            return any(k in u for k in (
                "publish",
                "publishshortvideo",
                "content-creation",
                "posts",
                "submit",
                "short-video",
                "captcha.alipay.com/api/v1/captcha/verify",
            ))

        async def _collect_response(resp):
            try:
                if not _watch_url(resp.url):
                    return
                status = resp.status
                text = ""
                req_body = ""
                try:
                    req_body = (resp.request.post_data or "").strip().replace("\n", " ")
                except Exception:
                    req_body = ""
                ct = (resp.headers or {}).get("content-type", "").lower()
                if "json" in ct or "text" in ct:
                    try:
                        text = (await resp.text() or "").strip().replace("\n", " ")
                    except Exception:
                        text = ""
                merged = f"req={req_body[:180]} resp={text[:180]}".strip()
                net_events.append((resp.request.method, resp.url, status, merged[:380]))
            except Exception:
                pass

        def _on_response(resp):
            try:
                net_tasks.append(asyncio.create_task(_collect_response(resp)))
            except Exception:
                pass

        def _on_request(req):
            try:
                if not _watch_url(req.url):
                    return
                body = (req.post_data or "").strip().replace("\n", " ")
                req_events.append((req.method, req.url, body[:220]))
            except Exception:
                pass

        page.on("response", _on_response)
        page.on("request", _on_request)
        async def _dismiss_quality_modal() -> bool:
            """点"确认发布"后支付宝可能弹「发现N个优化项」质量提示弹窗（封面断字/
            标题断字等），拦截真正提交导致 90s 超时。弹窗里「继续发布」才是放行，
            「返回更换」虽是主按钮样式却会退回修改，必须按文案点「继续发布」。
            返回是否点了「继续发布」。"""
            try:
                btn = page.locator(
                    '.antd5-modal-wrap button:has-text("继续发布"), '
                    '.antd5-modal button:has-text("继续发布")'
                ).first
                if await btn.count() and await btn.is_visible():
                    await btn.click(timeout=3000)
                    alipay_logger.info(_msg("✅", "已点击优化项弹窗「继续发布」放行提交"))
                    await page.wait_for_timeout(500)
                    return True
            except Exception as exc:
                alipay_logger.warning(_msg("😵", f"点击「继续发布」失败: {exc}"))
            return False

        await _collect_click_diag("点击前")
        await publish_btn.click()
        await page.wait_for_timeout(600)
        await _collect_click_diag("首次点击后")
        # 首次点击后可能立即弹出优化项拦截弹窗，先放行一次
        await _dismiss_quality_modal()

        start = time.monotonic()
        timeout = 90
        success_toast = page.locator('.antd5-message-notice-content:has-text("发布成功"), .antd5-message-notice-content:has-text("提交成功"), .antd5-message-notice-content:has-text("提交审核"), .antd5-message-notice-content:has-text("审核中")').first
        fail_toast = page.locator('.antd5-message-notice-content:has-text("发布失败"), .antd5-message-notice-content:has-text("提交失败"), .antd5-message-notice-content:has-text("请稍后重试")').first

        retried_after_aigc = False
        submit_click_retries = 0
        last_click_ts = start
        try:
            while time.monotonic() - start <= timeout:
                if "/content-creation/posts" in page.url:
                    alipay_logger.success(_msg("🥳", "视频发布成功"))
                    return

                # 优化项弹窗可能延迟出现，随时拦截提交，随见随点「继续发布」放行
                await _dismiss_quality_modal()

                # 命中 AIGC 预处理链路后，页面通常仍停留在发布页，需要再点一次确认发布才真正提交
                try:
                    saw_aigc_done = any(
                        ("querylooptask" in u.lower() and '"done":true' in (b or "").lower())
                        for _, u, _, b in net_events
                    )
                    if saw_aigc_done and not retried_after_aigc:
                        if await publish_btn.count() and not await publish_btn.is_disabled():
                            await publish_btn.click()
                            retried_after_aigc = True
                            alipay_logger.info(_msg("🔁", "检测到 AIGC 预处理完成，已二次点击确认发布"))
                            await page.wait_for_timeout(500)
                            await _collect_click_diag("AIGC后二次点击后")
                except Exception:
                    pass

                # 核心判据：必须至少看到一次 captcha verify / publishShortVideo 请求
                saw_captcha_verify = any("captcha.alipay.com/api/v1/captcha/verify" in u.lower() for _, u, _, _ in net_events)
                saw_publish_submit = any("publishshortvideo.json" in u.lower() for _, u, _, _ in net_events)
                no_submit_signal = not (saw_captcha_verify or saw_publish_submit)
                if no_submit_signal and submit_click_retries < 3 and (time.monotonic() - last_click_ts) >= 8:
                    try:
                        if await publish_btn.count() and not await publish_btn.is_disabled():
                            await publish_btn.click()
                            submit_click_retries += 1
                            last_click_ts = time.monotonic()
                            alipay_logger.info(_msg("🔁", f"未检测到提交请求信号，重试点击确认发布（{submit_click_retries}/3）"))
                            await page.wait_for_timeout(500)
                            await _collect_click_diag(f"重试点击后#{submit_click_retries}")
                    except Exception:
                        pass

                try:
                    if await success_toast.count() and await success_toast.is_visible():
                        alipay_logger.success(_msg("🥳", "视频发布成功（toast 命中）"))
                        return
                except Exception:
                    pass
                try:
                    if await fail_toast.count() and await fail_toast.is_visible():
                        raise RuntimeError("发布失败（页面返回失败提示）")
                except RuntimeError:
                    raise
                except Exception:
                    pass
                await page.wait_for_timeout(1000)

            raise RuntimeError(
                f"发布后未检测到成功信号（90s），当前地址: {page.url}"
            )
        finally:
            page.remove_listener("response", _on_response)
            page.remove_listener("request", _on_request)
            if net_tasks:
                try:
                    await asyncio.wait(net_tasks, timeout=3)
                except Exception:
                    pass
            if req_events:
                alipay_logger.info(_msg("🧾", f"提交阶段请求事件 {len(req_events)} 条（最近10条）"))
                for m, u, b in req_events[-10:]:
                    alipay_logger.info(_msg("🧾", f"REQ {m} {u} | {b}"))
            if net_events:
                alipay_logger.info(_msg("🧾", f"提交阶段网络事件 {len(net_events)} 条（最近10条）"))
                for m, u, s, b in net_events[-10:]:
                    alipay_logger.info(_msg("🧾", f"{m} {s} {u} | {b}"))

    async def upload(self, playwright: Playwright) -> None:
        alipay_logger.info(_msg("🧍", "先检查 cookie 和视频文件"))
        await self.validate_upload_args()
        alipay_logger.info(_msg("🥳", "上传前检查通过"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)
        await context.grant_permissions(["geolocation"])
        # 注意：不能用 set_init_script(stealth) —— 会阻止支付宝内容创作平台(qiankun 微应用)渲染

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            alipay_logger.info(_msg("🏃", f"开始上传视频: {self.title}"))

            await self.upload_video_file(page, self.file_path)
            await self.fill_title_and_tags(page)
            await self.fill_description(page)
            await self.upload_thumbnail(page)
            await self.apply_collection(page)
            await self.check_ai_label(page)
            await self.wait_for_upload_complete(page)
            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            alipay_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            await browser.close()

    async def alipay_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.alipay_upload_video()
