# -*- coding: utf-8 -*-
"""虎扑视频上传 + 手动登录保存 cookie。

功能：
  - hupu_cookie_gen: 打开浏览器让用户手动登录（QQ/手机号等），保存 storage_state
  - cookie_auth: 验证 cookie 是否有效
  - hupu_setup: 统一入口（检查/触发登录）
  - HuPuVideo: 视频上传类

基于 playwright codegen 录制脚本改写。
发布页：https://bbs.hupu.com/newpost?tabkey=2（视频发布标签页）
专区：固定选择「步行街 → 步行街主干道」

注意：虎扑有 headless 检测，需配合反检测参数才能正常操作。
"""
from __future__ import annotations

import asyncio
import inspect
import os
import re
import time
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.log import hupu_logger


HUPU_HOME_URL = "https://www.hupu.com/"
HUPU_LOGIN_URL = "https://passport.hupu.com/v2/login?pcPhone=1&jumpurl=https://www.hupu.com&from=https://www.hupu.com"
HUPU_PUBLISH_URL = "https://bbs.hupu.com/newpost?tabkey=2"

# 虎扑发布成功后跳转的帖子 URL 模式
HUPU_POST_URL_PATTERN = re.compile(r"bbs\.hupu\.com/\d+\.html")

# 反检测 UA
_CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

# 反 webdriver 检测脚本
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _build_login_result(success: bool, status: str, message: str, account_file: str, current_url: str = "") -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "current_url": current_url,
    }


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return
    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {
        "headless": headless,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if LOCAL_CHROME_PATH:
        launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
    return launch_kwargs


def _resolve_account_file(account_file: str | Path) -> str:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return str(path)
    if len(path.parts) == 1:
        return str((Path(BASE_DIR) / "cookies" / path).resolve())
    return str(path.resolve())


async def _create_stealth_context(browser, account_file: str | None = None) -> BrowserContext:
    """创建带反检测的 context。"""
    kwargs = {
        "user_agent": _CHROME_UA,
        "viewport": {"width": 1920, "height": 1080},
    }
    if account_file and os.path.exists(account_file):
        kwargs["storage_state"] = account_file
    context = await browser.new_context(**kwargs)
    return context


async def _new_stealth_page(context: BrowserContext) -> Page:
    """创建带反检测 init script 的 page。"""
    page = await context.new_page()
    await page.add_init_script(_STEALTH_SCRIPT)
    return page


async def hupu_cookie_gen(account_file, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 120, headless: bool = False):
    """QQ 扫码登录虎扑，保存 cookie。

    流程：打开虎扑登录页 → 点击 QQ 登录 → 截取 QQ 二维码 → 等待扫码完成 → 保存 storage_state。
    支持 headless 模式（终端显示二维码）。
    """
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)
    result = _build_login_result(False, "failed", "虎扑登录失败", account_file)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await _create_stealth_context(browser)
        try:
            page = await _new_stealth_page(context)
            await page.goto(HUPU_LOGIN_URL, timeout=60000, wait_until="load")
            await page.wait_for_timeout(3000)

            # 点击 QQ 登录按钮
            qq_btn = page.get_by_role("button", name="qq QQ登录")
            if not await qq_btn.count():
                hupu_logger.error(_msg("😢", "未找到 QQ 登录按钮"))
                result = _build_login_result(False, "failed", "未找到 QQ 登录按钮", account_file, page.url)
                return result

            await qq_btn.click()
            await page.wait_for_timeout(5000)
            hupu_logger.info(_msg("🏃", "已跳转到 QQ 登录页"))

            # 从 QQ iframe 中获取二维码
            qrcode_info = await _grab_qq_qrcode(page, context, account_file)

            if qrcode_info:
                await _emit_qrcode_callback(qrcode_callback, qrcode_info)
                hupu_logger.info(_msg("🧍", "请用 QQ 手机版扫码登录"))
            else:
                hupu_logger.warning(_msg("⚠️", "未能获取 QQ 二维码，请在浏览器中手动扫码"))

            # 轮询等待登录完成
            for _ in range(max_checks):
                current_url = page.url
                # QQ 授权成功后会跳回虎扑首页
                if "www.hupu.com" in current_url and "passport" not in current_url and "graph.qq.com" not in current_url:
                    hupu_logger.info(_msg("🥳", f"登录成功，跳转到: {current_url}"))
                    result = _build_login_result(True, "success", "虎扑 QQ 扫码登录成功", account_file, current_url)
                    break
                # 检查是否实际跳转到虎扑 passport 回调页（不是 redirect_uri 参数中包含）
                if current_url.startswith("https://passport.hupu.com/pc/qqcallback"):
                    await page.wait_for_timeout(5000)
                    current_url = page.url
                    hupu_logger.info(_msg("🥳", f"QQ 回调成功，当前: {current_url}"))
                    result = _build_login_result(True, "success", "虎扑 QQ 扫码登录成功", account_file, current_url)
                    break
                # 检查 cookies 中是否出现 u（核心登录态）
                cookies = await context.cookies()
                if any(c.get("name") == "u" and c.get("value") for c in cookies):
                    hupu_logger.info(_msg("🥳", f"登录成功（检测到 u cookie），当前: {current_url}"))
                    result = _build_login_result(True, "success", "虎扑 QQ 扫码登录成功", account_file, current_url)
                    break
                await page.wait_for_timeout(poll_interval * 1000)
            else:
                result = _build_login_result(False, "timeout", "等待 QQ 扫码登录超时", account_file, page.url)

            if result["success"]:
                await asyncio.sleep(2)
                # 确保跳转到首页加载完 cookie
                if "www.hupu.com" not in page.url:
                    await page.goto(HUPU_HOME_URL, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)
                await context.storage_state(path=account_file)
                hupu_logger.success(_msg("🥳", f"cookie 已保存: {account_file}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            # 清理临时二维码文件
            qr_path = Path(account_file).parent / f"{Path(account_file).stem}_qq_qrcode.png"
            if qr_path.exists():
                qr_path.unlink()
            if not result["success"]:
                hupu_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()
    return result


async def _grab_qq_qrcode(page: Page, context: BrowserContext, account_file: str) -> dict | None:
    """从 QQ 登录 iframe 中获取二维码。"""
    from utils.login_qrcode import decode_qrcode_from_path, print_terminal_qrcode

    # 等待 QQ iframe 加载（最多 15 秒）
    qq_frame = None
    for _ in range(5):
        for frame in page.frames:
            if "xui.ptlogin2.qq.com" in frame.url or "ptlogin2.qq.com" in frame.url:
                qq_frame = frame
                break
        if qq_frame:
            break
        await asyncio.sleep(3)

    if not qq_frame:
        return None

    await asyncio.sleep(3)

    # 获取二维码图片（id="qrlogin_img"）
    qr_selectors = ["#qrlogin_img", 'img[src*="ptqrshow"]', 'img[id*="qr"]']
    for sel in qr_selectors:
        qr_loc = qq_frame.locator(sel).first
        if await qr_loc.count():
            src = await qr_loc.get_attribute("src")
            if src and src.startswith("http"):
                # 下载二维码图片
                try:
                    resp = await context.request.get(src)
                    qr_path = Path(account_file).parent / f"{Path(account_file).stem}_qq_qrcode.png"
                    qr_path.parent.mkdir(parents=True, exist_ok=True)
                    qr_path.write_bytes(await resp.body())

                    # 尝试解码并在终端显示
                    qrcode_content = decode_qrcode_from_path(qr_path)
                    if qrcode_content:
                        print_terminal_qrcode(qrcode_content, qr_path, "QQ手机版")
                    else:
                        hupu_logger.warning(_msg("😵", f"终端无法显示二维码，请打开 {qr_path} 扫码"))

                    return {"image_path": str(qr_path), "image_data_url": ""}
                except Exception as exc:
                    hupu_logger.warning(_msg("⚠️", f"下载 QQ 二维码失败: {exc}"))
                    continue

    return None


async def cookie_auth(account_file):
    """验证虎扑 cookie 是否有效。访问发布页，检测是否能正常加载。"""
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await _create_stealth_context(browser, account_file)
            page = await _new_stealth_page(context)
            await page.goto(HUPU_PUBLISH_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # 检查是否被跳转到登录页
            if "passport" in page.url or "login" in page.url:
                hupu_logger.info(_msg("🥹", "cookie 已失效（跳转到登录页）"))
                return False

            # 检查发布页是否出现「上传视频」按钮（登录后才有）
            upload_btn = page.get_by_role("button", name="上传视频")
            if await upload_btn.count():
                hupu_logger.success(_msg("🥳", "cookie 有效"))
                return True

            # 兜底：检查 cookie 中是否有 u 字段
            cookies = await context.cookies()
            if any(c.get("name") == "u" and c.get("value") for c in cookies):
                hupu_logger.success(_msg("🥳", "cookie 有效（u cookie 存在）"))
                return True

            hupu_logger.info(_msg("🥹", "cookie 已失效（未检测到登录态）"))
            return False
        except Exception as exc:
            hupu_logger.warning(_msg("😵", f"cookie 校验出错，按失效处理: {exc}"))
            return False
        finally:
            await browser.close()


async def hupu_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = False):
    """统一入口：检查 cookie → 如无效且 handle=True 则触发手动登录。"""
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie 文件不存在或已失效", account_file)
            return result if return_detail else False
        hupu_logger.info(_msg("🥹", "cookie 文件不存在或已失效，打开浏览器请手动登录"))
        result = await hupu_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie 有效", account_file)
    return result if return_detail else True


class HuPuVideo(BaseVideoUploader):
    """虎扑视频上传。

    流程：直接跳转发布页 → 上传视频文件 → 填标题 → 填简介 →
         上传封面 → 选专区（步行街主干道）→ 选原创/二创 → 选 AI 声明 →
         点击「确定发布」→ 等待跳转到帖子页面。
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
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH
        self.max_title_length = 40
        self.min_title_length = 4

    async def validate_upload_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成虎扑登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成虎扑登录: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("视频标题不能为空")
        if len(self.title) < self.min_title_length:
            raise ValueError(f"视频标题至少{self.min_title_length}个字")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_path:
            self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def upload(self, playwright: Playwright) -> None:
        hupu_logger.info(_msg("🧍", "先检查 cookie 和视频文件"))
        await self.validate_upload_args()
        hupu_logger.info(_msg("🥳", "上传前检查通过"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await _create_stealth_context(browser, self.account_file)

        try:
            page = await _new_stealth_page(context)
            # 直接跳转到视频发布页（绕过首页点击）
            await page.goto(HUPU_PUBLISH_URL, timeout=60000, wait_until="load")
            await page.wait_for_timeout(5000)
            hupu_logger.info(_msg("🏃", f"开始上传视频: {self.title}"))

            # 1) 上传视频文件
            await self._upload_video_file(page)

            # 2) 填写标题
            await self._fill_title(page)

            # 3) 填写简介
            await self._fill_description(page)

            # 4) 上传封面（如有）
            if self.thumbnail_path:
                await self._upload_thumbnail(page)

            # 5) 选择专区（步行街 → 步行街主干道）
            await self._select_zone(page)

            # 6) 选择原创/二创 + AI 声明
            await self._check_declarations(page)

            # 7) 点击发布
            await self._submit_publish(page)

            # 保存 cookie
            await context.storage_state(path=self.account_file)
            hupu_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            await browser.close()

    async def _upload_video_file(self, page: Page) -> None:
        """点击「上传视频」按钮并设置文件。"""
        upload_btn = page.get_by_role("button", name="上传视频")
        await upload_btn.wait_for(state="visible", timeout=15000)

        # 通过 file chooser 设置文件
        async with page.expect_file_chooser(timeout=10000) as fc_info:
            await upload_btn.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)
        hupu_logger.info(_msg("🏃", f"已选择视频文件: {self.file_path}"))

        # 等待视频上传就绪（标题输入框出现即可填写）
        title_field = page.get_by_placeholder("请输入标题（最少4个字，最多40个字）")
        await title_field.wait_for(state="visible", timeout=300000)
        hupu_logger.info(_msg("🥳", "视频已就绪"))

    async def _fill_title(self, page: Page) -> None:
        """填写标题（4-40字）。"""
        title_field = page.get_by_placeholder("请输入标题（最少4个字，最多40个字）")
        await title_field.wait_for(state="visible", timeout=15000)
        title = self.title[:self.max_title_length]
        await title_field.click()
        await title_field.fill(title)
        hupu_logger.info(_msg("🏷️", f"标题已填写: {title}"))

    async def _fill_description(self, page: Page) -> None:
        """填写简介。"""
        desc_field = page.get_by_placeholder("请输入简介")
        if not await desc_field.count():
            hupu_logger.warning(_msg("⚠️", "未找到简介输入框"))
            return

        # 组装描述：正文 + 标签
        content = self.desc
        if self.tags:
            tag_str = " ".join(f"#{t}#" for t in self.tags)
            content = f"{content}\n{tag_str}" if content else tag_str

        if content:
            await desc_field.click()
            await desc_field.fill(content)
            hupu_logger.info(_msg("📝", f"简介已填写（{len(content)}字）"))

    async def _upload_thumbnail(self, page: Page) -> None:
        """上传封面：点击「更换封面」→ 设置文件。"""
        try:
            cover_span = page.locator("span").filter(has_text="更换封面")
            await cover_span.wait_for(state="visible", timeout=10000)

            # 通过 file chooser 设置封面图片
            async with page.expect_file_chooser(timeout=10000) as fc_info:
                await cover_span.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(self.thumbnail_path)
            hupu_logger.info(_msg("🏃", f"已选择封面图片: {self.thumbnail_path}"))
            await page.wait_for_timeout(3000)
            hupu_logger.success(_msg("🖼️", "封面已上传"))
        except Exception as exc:
            hupu_logger.warning(_msg("⚠️", f"封面上传失败: {exc}，继续发布（使用默认封面）"))

    async def _select_zone(self, page: Page) -> None:
        """选择专区：步行街 → 步行街主干道。"""
        try:
            # 录制脚本：page.get_by_label("发视频").get_by_text("添加专区").click()
            add_zone_btn = page.get_by_label("发视频").get_by_text("添加专区")
            await add_zone_btn.wait_for(state="visible", timeout=10000)
            await add_zone_btn.click()
            await page.wait_for_timeout(1500)

            # 选择「步行街」分类
            zone_dialog = page.get_by_label("添加专区")
            step_street = zone_dialog.locator("div").filter(has_text=re.compile(r"^步行街$"))
            await step_street.click()
            await page.wait_for_timeout(1000)

            # 选择「步行街主干道」子分类
            main_road = page.get_by_text("步行街主干道")
            await main_road.click()
            await page.wait_for_timeout(500)

            # 点击确定
            confirm_btn = page.get_by_role("button", name="确 定")
            await confirm_btn.click()
            await page.wait_for_timeout(1000)
            hupu_logger.info(_msg("🏷️", "已选择专区：步行街主干道"))
        except Exception as exc:
            hupu_logger.warning(_msg("⚠️", f"选择专区失败: {exc}"))

    async def _check_declarations(self, page: Page) -> None:
        """选择原创/二创声明 + AI 声明。"""
        try:
            # 1) 点击「原创/二创」按钮
            declaration_btn = page.get_by_role("button", name="原创/二创")
            if await declaration_btn.count():
                await declaration_btn.click(timeout=5000)
                await page.wait_for_timeout(1000)
                hupu_logger.info(_msg("🏷️", "已点击「原创/二创」"))
        except Exception as exc:
            hupu_logger.warning(_msg("⚠️", f"点击原创/二创失败: {exc}"))

        try:
            # 2) 选择「含AI生成内容」
            combobox = page.get_by_role("combobox")
            if await combobox.count():
                await combobox.click(timeout=5000)
                await page.wait_for_timeout(1000)

                ai_option = page.get_by_text("含AI生成内容")
                if await ai_option.count():
                    await ai_option.click(timeout=5000)
                    await page.wait_for_timeout(500)
                    hupu_logger.info(_msg("🏷️", "已选择「含AI生成内容」"))
        except Exception as exc:
            hupu_logger.warning(_msg("⚠️", f"选择 AI 声明失败: {exc}"))

    async def _submit_publish(self, page: Page) -> None:
        """点击「确定发布」并等待跳转到帖子页面。"""
        # 录制脚本：page.get_by_label("发视频").get_by_text("确定发布").click()
        publish_btn = page.get_by_label("发视频").get_by_text("确定发布")
        await publish_btn.wait_for(state="visible", timeout=15000)
        await publish_btn.click()
        hupu_logger.info(_msg("🏃", "已点击「确定发布」"))

        # 等待跳转到帖子详情页（URL 匹配 bbs.hupu.com/{数字}.html）
        start = time.monotonic()
        while time.monotonic() - start < 60:
            current_url = page.url
            if HUPU_POST_URL_PATTERN.search(current_url):
                hupu_logger.success(_msg("🥳", f"视频发布成功: {current_url}"))
                return

            await page.wait_for_timeout(2000)

        # 超时 - 可能已成功但检测不到
        hupu_logger.warning(_msg("⚠️", f"发布后 60s 未检测到帖子页面跳转，当前 URL: {page.url}"))

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
