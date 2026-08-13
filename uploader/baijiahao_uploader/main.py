# -*- coding: utf-8 -*-
"""百家号（百度百家号）视频上传 + 扫码登录。

功能：
  - baijiahao_cookie_gen: headless 扫码登录（百度 passport 二维码）
  - cookie_auth: 验证 cookie 是否有效
  - baijiahao_setup: 统一入口（检查/触发登录）
  - BaiJiaHaoVideo: 视频上传类
"""
from __future__ import annotations

import asyncio
import inspect
import json as _json
import os
import time
from pathlib import Path

from playwright.async_api import Page, Playwright, TimeoutError as PWTimeoutError, async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.log import baijiahao_logger
from utils.login_qrcode import build_login_qrcode_path, decode_qrcode_from_path, print_terminal_qrcode, remove_qrcode_file


BAIJIAHAO_LOGIN_URL = "https://baijiahao.baidu.com/builder/theme/bjh/login"
BAIJIAHAO_HOME_URL = "https://baijiahao.baidu.com/builder/rc/home"
BAIJIAHAO_PUBLISH_URL = "https://baijiahao.baidu.com/builder/rc/edit?type=videoV2"
# 发布成功后跳转到的 URL 前缀
BAIJIAHAO_SUCCESS_URL_PREFIX = "https://baijiahao.baidu.com/builder/rc/clue"

# 百度 passport 二维码图片选择器
QR_SELECTOR = 'img[src^="https://passport.baidu.com/v2/api/qrcode"]'


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
        return str((Path(BASE_DIR) / "cookies" / "baijiahao_uploader" / path).resolve())
    return str(path.resolve())


async def _grab_qr(page: Page, account_file: str) -> dict:
    """截取百度 passport 扫码登录二维码。

    百家号登录页点「登录」后弹出百度统一登录框，其中二维码是 img[src] 指向
    passport.baidu.com 的图片 URL，可以直接下载或截图。
    """
    qr = page.locator(QR_SELECTOR).first
    await qr.wait_for(state="attached", timeout=60000)

    qrcode_path = build_login_qrcode_path(account_file)
    qrcode_path.parent.mkdir(parents=True, exist_ok=True)

    # 优先直接下载高清图片 URL
    src = await qr.get_attribute("src")
    if src and src.startswith("https://"):
        try:
            resp = await page.context.request.get(src)
            qrcode_path.write_bytes(await resp.body())
        except Exception:
            await qr.screenshot(path=str(qrcode_path))
    else:
        await qr.screenshot(path=str(qrcode_path))

    qrcode_content = decode_qrcode_from_path(qrcode_path)
    baijiahao_logger.info(_msg("🖼️", f"二维码已保存到: {qrcode_path}"))
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, "百度APP/手机百度")
    else:
        baijiahao_logger.warning(_msg("😵", f"终端没法完整显示二维码，请打开 {qrcode_path} 扫码"))
    return {"image_path": str(qrcode_path), "image_data_url": ""}


async def _is_login_completed(page: Page) -> bool:
    """判断百度登录是否完成：URL 离开 login 页 或 出现 BDUSS cookie。"""
    if "login" in page.url.lower():
        # 还在登录页，检查 cookies
        cookies = await page.context.cookies()
        if any(c.get("name") in ("BDUSS", "STOKEN") for c in cookies):
            return True
        return False
    # 跳走了说明登录成功
    return True


async def baijiahao_cookie_gen(account_file, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 120, headless: bool = LOCAL_CHROME_HEADLESS):
    """无头/有头扫码登录百家号，保存 cookie。

    流程：打开登录页 → 点「登录」按钮弹出百度 passport 登录框 → 截取二维码 → 等待扫码完成 → 保存 storage_state。
    返回标准 login result dict。
    """
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)
    qrcode_path = None
    result = _build_login_result(False, "failed", "百家号登录失败", account_file)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.goto(BAIJIAHAO_LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)

            # 点击「登录」按钮触发百度 passport 弹窗
            login_btn = page.get_by_text("登录", exact=True).first
            try:
                await login_btn.click(timeout=10000)
            except Exception:
                # 有些情况直接就在登录状态
                pass
            await page.wait_for_timeout(4000)

            if headless:
                baijiahao_logger.info(_msg("🧍", "无头登录中：二维码已存为图片，请用百度APP扫码"))
            else:
                baijiahao_logger.info(_msg("🧍", "请在打开的浏览器中扫码登录百家号"))

            # 截取二维码
            qrcode_info = await _grab_qr(page, account_file)
            qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None
            await _emit_qrcode_callback(qrcode_callback, qrcode_info)

            baijiahao_logger.info(_msg("🧍", "请扫码，正在耐心等待登录完成"))

            # 轮询等待登录完成
            for _ in range(max_checks):
                if await _is_login_completed(page):
                    baijiahao_logger.info(_msg("🥳", f"扫码成功，当前页面: {page.url}"))
                    result = _build_login_result(True, "success", "百家号扫码登录成功", account_file, qrcode_info, page.url)
                    break
                await page.wait_for_timeout(poll_interval * 1000)
            else:
                result = _build_login_result(False, "timeout", "等待百家号扫码登录超时", account_file, qrcode_info, page.url)

            if result["success"]:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                baijiahao_logger.success(_msg("🥳", f"cookie 已保存: {account_file}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                baijiahao_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                baijiahao_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()
    return result


async def cookie_auth(account_file):
    """验证百家号 cookie 是否有效。访问后台首页，检测是否出现登录提示。"""
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            page = await context.new_page()
            await page.goto(BAIJIAHAO_HOME_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            if await page.get_by_text("注册/登录百家号").count():
                baijiahao_logger.info(_msg("🥹", "cookie 已失效"))
                return False
            else:
                baijiahao_logger.success(_msg("🥳", "cookie 有效"))
                return True
        except Exception as exc:
            baijiahao_logger.warning(_msg("😵", f"cookie 校验出错，按失效处理: {exc}"))
            return False
        finally:
            await browser.close()


async def baijiahao_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    """统一入口：检查 cookie → 如无效且 handle=True 则触发扫码登录。"""
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie 文件不存在或已失效", account_file)
            return result if return_detail else False
        baijiahao_logger.info(_msg("🥹", "cookie 文件不存在或已失效，自动打开浏览器请扫码登录"))
        result = await baijiahao_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie 有效", account_file)
    return result if return_detail else True


class BaiJiaHaoVideo(BaseVideoUploader):
    """百家号视频上传。

    流程：打开发布页 → 上传视频文件 → 填标题 → 等待上传/转码完成 → 等封面生成 → 点击发布。
    """

    def __init__(
        self,
        title,
        file_path,
        tags,
        account_file,
        publish_date=0,
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
        self.publish_date = publish_date
        self.desc = desc or ""
        self.thumbnail_path = thumbnail_path
        self.collection_name = collection_name
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH
        self.max_title_length = 30

    async def validate_upload_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成百家号登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成百家号登录: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("视频标题不能为空")
        if not self.thumbnail_path:
            raise ValueError("百家号视频发布必须提供横版封面图（--thumbnail）")
        self.file_path = str(self.validate_video_file(self.file_path))
        self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def upload(self, playwright: Playwright) -> None:
        baijiahao_logger.info(_msg("🧍", "先检查 cookie 和视频文件"))
        await self.validate_upload_args()
        baijiahao_logger.info(_msg("🥳", "上传前检查通过"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)
        await context.grant_permissions(["geolocation"])

        try:
            page = await context.new_page()
            await page.goto(BAIJIAHAO_PUBLISH_URL, timeout=120000, wait_until="domcontentloaded")
            baijiahao_logger.info(_msg("🏃", f"开始上传视频: {self.title}"))

            # 等待发布页加载
            await page.wait_for_timeout(3000)

            # 1) 上传视频文件
            file_input = page.locator('input[type="file"][accept*="video"], input[type="file"][accept*="mp4"]').first
            if not await file_input.count():
                file_input = page.locator("div[class^='video-main-container'] input[type='file']").first
            if not await file_input.count():
                file_input = page.locator('input[type="file"]').first
            await file_input.wait_for(state="attached", timeout=30000)
            await file_input.set_input_files(self.file_path)
            baijiahao_logger.info(_msg("🏃", f"已选择视频文件: {self.file_path}"))

            # 2) 等待进入表单页面（contenteditable 标题区出现即表单渲染完毕）
            title_editor = page.locator('div[class*="contentEditable"]').first
            await title_editor.wait_for(state="visible", timeout=180000)
            await page.wait_for_timeout(1000)

            # 3) 填写标题
            await self._fill_title(page)

            # 4) 等待视频上传完成
            await self._wait_upload_complete(page)

            # 5) 上传横版封面（必填）
            await self._upload_thumbnail(page)

            # 6) 勾选「含AI生成内容」
            await self._check_ai_declaration(page)

            # 7) 选择合集（如有配置）
            await self._apply_collection(page)

            # 8) 点击发布
            await self._submit_publish(page)

            # 保存 cookie
            await context.storage_state(path=self.account_file)
            baijiahao_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            await browser.close()

    async def _fill_title(self, page: Page) -> None:
        title_field = page.locator('div[class*="contentEditable"]').first
        await title_field.wait_for(state="visible", timeout=15000)
        title = self.title
        # 百家号标题最少9字
        if len(title) <= 8:
            title += " 你不知道的"
        title = title[: self.max_title_length]
        # 清空原有内容（可能自动填了文件名），再输入标题
        await title_field.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Backspace")
        await title_field.fill(title)
        baijiahao_logger.info(_msg("🏷️", f"标题已填写: {title}"))

    async def _wait_upload_complete(self, page: Page, timeout: int = 600) -> None:
        """等待视频真正上传完成。

        百度真实上传进度是一段百分比文字（9%…99%，上传完成后消失，本文件实测约 35s）。
        旧实现用 'div .cover-overlay:has-text("上传中")' 判断——经实测该元素恒不存在，
        导致选完文件立即误判"上传完毕"（约 4s）。大文件此时其实还在后台上传，随后点
        发布会被百度以"确保视频已经上传完毕"拒绝（产出 0 作品）。改为跟踪百分比进度：
        出现过进度且进度消失/达 100% 才算真正上传完成。
        """
        import re as _re
        start = time.monotonic()
        seen_progress = False
        gone_count = 0
        while True:
            if time.monotonic() - start > timeout:
                baijiahao_logger.warning(_msg("⚠️", f"等待上传超时（>{timeout}s），继续后续步骤"))
                return

            body = ""
            try:
                body = await page.inner_text("body")
            except Exception:
                pass

            if "上传失败" in body:
                raise RuntimeError("视频上传失败")

            m = _re.search(r'(\d{1,3})\s*%', body)
            pct = int(m.group(1)) if m else None

            if pct is not None and pct < 100:
                seen_progress = True
                gone_count = 0
                baijiahao_logger.info(_msg("🏃", f"上传中 {pct}%"))
                await asyncio.sleep(2)
                continue

            if seen_progress:
                # 进度百分比已消失/到 100%，连续两次确认后判为上传完成
                gone_count += 1
                if gone_count >= 2:
                    baijiahao_logger.success(_msg("🥳", "视频上传完毕"))
                    return
                await asyncio.sleep(2)
                continue

            # 一直没出现过进度：小文件可能秒传完成；给 15s 窗口后放行
            if time.monotonic() - start > 15:
                baijiahao_logger.success(_msg("🥳", "视频上传完毕"))
                return
            await asyncio.sleep(2)

    async def _upload_thumbnail(self, page: Page) -> None:
        """上传横版封面（必填）。

        流程：点击「选择封面」→ 弹窗中点「上传」按钮 → 设置图片文件 → 等待上传完成 → 确认。
        如果没有提供 thumbnail_path，等待系统自动生成封面即可。
        """
        if not self.thumbnail_path:
            # 没有自定义封面，等系统自动生成
            await self._wait_cover_ready(page)
            return

        try:
            # 1) 点击「选择封面」入口
            cover_entry = page.locator('[data-testid="select-cover"]').first
            if not await cover_entry.count():
                # 备选：通过文本定位
                cover_entry = page.get_by_text("选择封面", exact=True).first
            await cover_entry.scroll_into_view_if_needed()
            await cover_entry.click(timeout=10000)
            baijiahao_logger.info(_msg("🏃", "已点击「选择封面」"))
            await page.wait_for_timeout(2000)

            # 2) 弹窗中找「上传」按钮并点击
            # 百家号封面弹窗通常有「上传」tab/按钮
            upload_btn = page.locator('button:has-text("上传"), div:has-text("上传"):not(:has(*)):visible').first
            if not await upload_btn.count():
                upload_btn = page.get_by_text("上传", exact=True).first
            await upload_btn.click(timeout=8000)
            await page.wait_for_timeout(1500)

            # 3) 设置图片文件到 file input
            # 弹窗中会出现 input[type=file]
            img_input = page.locator('input[type="file"][accept*="image"], input[type="file"][accept*="jpg"], input[type="file"][accept*="png"]').first
            if not await img_input.count():
                # 通用 fallback：弹窗内最新出现的 file input
                img_input = page.locator('input[type="file"]').last
            await img_input.set_input_files(self.thumbnail_path)
            baijiahao_logger.info(_msg("🏃", f"已选择封面图片: {self.thumbnail_path}"))

            # 4) 等待并点击确认/完成按钮（如有裁剪弹窗）。
            #    裁剪弹窗渲染有延迟（图片上传+服务端处理），之前用固定 sleep(3s) 后
            #    一次性检查 confirm_btn，弹窗还没渲染出来时会被误判为"无需确认"而跳过点击，
            #    导致封面选择实际未提交，但日志仍打「封面已上传」成功——这是本次线上
            #    百家号视频没有封面、日志却显示成功的根因。改为轮询等待（不放大超时时长本身
            #    不算错误：裁剪弹窗本就是可选的，等不到也可能是流程本身没有该弹窗）。
            confirm_btn = page.locator('button:has-text("确定"), button:has-text("完成"), button:has-text("确认")').first
            confirmed = False
            try:
                await confirm_btn.wait_for(state="visible", timeout=15000)
                await confirm_btn.click(timeout=8000)
                await page.wait_for_timeout(1000)
                confirmed = True
            except PWTimeoutError:
                baijiahao_logger.debug("封面确认按钮未出现，可能本次流程无需裁剪确认")

            if confirmed:
                baijiahao_logger.success(_msg("🖼️", "封面已上传"))
            else:
                # 没有等到确认按钮：不确定封面是否真正生效，不再冒充成功，
                # 交给下方 except 分支同一套"等待系统自动封面"兜底逻辑核实/兜底。
                raise RuntimeError("封面确认按钮未出现，无法确认封面是否生效")
        except Exception as exc:
            baijiahao_logger.warning(_msg("⚠️", f"封面上传失败: {exc}，尝试等待系统自动封面"))
            # fallback：等系统自动生成
            await self._wait_cover_ready(page)

    async def _check_ai_declaration(self, page: Page) -> None:
        """选择「含AI生成内容」创作声明。

        点击「请选择创作声明」input → 弹出 modal 弹窗 → 点选「含AI生成内容」→ 点「确定」。
        """
        try:
            # 点击创作声明输入框触发弹窗
            trigger = page.locator('input[placeholder="请选择创作声明"]').first
            await trigger.scroll_into_view_if_needed()
            await trigger.click(force=True, timeout=8000)
            await page.wait_for_timeout(3000)

            # 弹窗内点选「含AI生成内容」
            ai_option = page.locator('.cheetah-modal-wrap :text("含AI生成内容")').first
            if not await ai_option.count():
                ai_option = page.locator('text="含AI生成内容"').first
            await ai_option.wait_for(state="visible", timeout=10000)
            await ai_option.click(timeout=5000)
            await page.wait_for_timeout(1000)

            # 点「确定」按钮关闭弹窗（弹窗可能在点选后仍存在）
            modal = page.locator('.cheetah-modal-wrap:visible').first
            if await modal.count():
                confirm_btn = modal.locator('button:has-text("确定")').first
                if await confirm_btn.count() and await confirm_btn.is_visible():
                    await confirm_btn.click(timeout=5000)
                    await page.wait_for_timeout(500)
                else:
                    # 确定按钮不可见，尝试 force click 或按 Escape 关闭
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)

            baijiahao_logger.success(_msg("🏷️", "已选择「含AI生成内容」"))
        except Exception as exc:
            # 如果失败，尝试关闭可能残留的弹窗
            try:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            except Exception:
                pass
            baijiahao_logger.warning(_msg("⚠️", f"选择 AI 声明失败: {exc}"))

    async def _apply_collection(self, page: Page) -> None:
        """选择合集（cheetah-select 下拉搜索框）。

        placeholder: "选择同主题的合集，可获得更多播放机会"
        有 collection_name 时点开下拉 → 搜索/选中目标合集；没有则跳过。
        """
        if not self.collection_name:
            return
        try:
            # 定位合集下拉框（通过 placeholder 文案）
            select_box = page.locator('.cheetah-select:has(.cheetah-select-selection-placeholder:has-text("选择同主题的合集"))').first
            if not await select_box.count():
                select_box = page.locator('.cheetah-select-selection-placeholder:has-text("合集")').locator('xpath=ancestor::div[contains(@class,"cheetah-select")]').first
            if not await select_box.count():
                baijiahao_logger.warning(_msg("⚠️", "未找到合集选择器，跳过"))
                return

            await select_box.scroll_into_view_if_needed()
            await select_box.click(timeout=8000)
            await page.wait_for_timeout(1500)

            # 在搜索框中输入合集名（触发搜索过滤）
            search_input = select_box.locator('input.cheetah-select-selection-search-input').first
            if await search_input.count():
                await search_input.fill(self.collection_name)
                await page.wait_for_timeout(1500)

            # 从下拉选项中选中目标合集
            option = page.locator(f'[role="option"]:has-text("{self.collection_name}"), .cheetah-select-item:has-text("{self.collection_name}")').first
            if await option.count():
                await option.click(timeout=5000)
                await page.wait_for_timeout(500)
                baijiahao_logger.success(_msg("🥳", f"已选择合集：{self.collection_name}"))
            else:
                baijiahao_logger.warning(_msg("⚠️", f"账号中无「{self.collection_name}」合集，跳过"))
                await page.keyboard.press("Escape")
        except Exception as exc:
            baijiahao_logger.warning(_msg("⚠️", f"选择合集失败，跳过: {exc}"))

    async def _wait_cover_ready(self, page: Page, timeout: int = 120) -> None:
        """等待百家号自动生成封面图。"""
        start = time.monotonic()
        while True:
            if time.monotonic() - start > timeout:
                baijiahao_logger.warning(_msg("⚠️", "等待封面生成超时，继续发布"))
                return
            if await page.locator("div.cheetah-spin-container img").count():
                baijiahao_logger.info(_msg("🖼️", "封面已生成"))
                return
            baijiahao_logger.info(_msg("🏃", "等待封面生成..."))
            await asyncio.sleep(3)

    async def _submit_publish(self, page: Page) -> None:
        """点击发布按钮并确认成功。"""
        # 确保没有残留弹窗遮挡
        modal = page.locator('.cheetah-modal-wrap:visible').first
        if await modal.count():
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

        # 百家号发布按钮有 data-testid="publish-btn"
        publish_btn = page.locator('[data-testid="publish-btn"]').first
        if not await publish_btn.count():
            publish_btn = page.locator('button:text-is("发布")').first
        if not await publish_btn.count():
            publish_btn = page.locator('button:has-text("发布")').last
        await publish_btn.wait_for(state="visible", timeout=15000)
        await publish_btn.click(force=True)
        baijiahao_logger.info(_msg("🏃", "已点击发布按钮"))

        # 等待跳转或成功提示（最多30s）
        start = time.monotonic()
        while time.monotonic() - start < 30:
            url = page.url
            # 发布成功跳转
            if BAIJIAHAO_SUCCESS_URL_PREFIX in url or "/rc/content" in url or "/rc/home" in url:
                baijiahao_logger.success(_msg("🥳", "视频发布成功"))
                return
            # 检查是否出现百度安全验证
            if await page.locator('text="百度安全验证"').count():
                raise RuntimeError("出现百度安全验证，需人工处理")
            # 检查是否有错误提示阻止发布
            error_toast = page.locator('.cheetah-message-error, .cheetah-message-warning').first
            if await error_toast.count() and await error_toast.is_visible():
                err_text = await error_toast.inner_text()
                baijiahao_logger.warning(_msg("⚠️", f"发布提示: {err_text}"))
            await page.wait_for_timeout(1000)

        # 超时后再检查一次
        if BAIJIAHAO_SUCCESS_URL_PREFIX in page.url or "/rc/content" in page.url:
            baijiahao_logger.success(_msg("🥳", "视频发布成功"))
        else:
            raise RuntimeError(f"发布后未跳转到成功页面（30s），当前 URL: {page.url}")

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
