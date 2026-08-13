# -*- coding: utf-8 -*-
"""微博视频上传 + 扫码登录。

功能：
  - weibo_cookie_gen: headless 扫码登录（微博 passport 二维码）
  - cookie_auth: 验证 cookie 是否有效
  - weibo_setup: 统一入口（检查/触发登录）
  - WeiBoVideo: 视频上传类

基于 playwright codegen 录制脚本改写。
入口页：https://weibo.com/
发布页：点击首页「视频」入口弹出新窗口（视频发布页）
"""
from __future__ import annotations

import asyncio
import inspect
import os
import re
import time
from pathlib import Path

from playwright.async_api import Page, Playwright, TimeoutError as PWTimeoutError, async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.log import weibo_logger
from utils.login_qrcode import build_login_qrcode_path, remove_qrcode_file


WEIBO_HOME_URL = "https://weibo.com/"
WEIBO_LOGIN_URL = "https://weibo.com/newlogin?tabtype=weibo&gid=102803&openLoginLayer=0&url=https://weibo.com/"
# 微博 passport 扫码登录页（直接跳这里，绕过首页 popup）
WEIBO_PASSPORT_QR_URL = "https://passport.weibo.com/sso/signin?entry=miniblog&source=miniblog&url=https%3A%2F%2Fweibo.com%2F"

# 微博 passport 二维码选择器（扫码登录页中的二维码图片）
QR_SELECTOR = 'img[src*="qrcode"], img[src*="qr"]'


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
        return str((Path(BASE_DIR) / "cookies" / "weibo_uploader" / path).resolve())
    return str(path.resolve())


async def _grab_qr(page: Page, account_file: str) -> dict:
    """截取微博 passport 扫码登录二维码。

    微博 passport 登录页的二维码可能是 img 或 canvas，尝试多种选择器。
    """
    # 多种可能的二维码选择器（passport 页面结构可能变化）
    selectors = [
        'img[src*="qrcode"]',
        'img[src*="qr"]',
        'img[node-type="qrcode_img"]',
        '.qrcode img',
        'canvas',  # 部分版本用 canvas 绘制二维码
    ]

    qr = None
    for sel in selectors:
        loc = page.locator(sel).first
        if await loc.count():
            qr = loc
            weibo_logger.info(_msg("🔍", f"找到二维码元素: {sel}"))
            break

    if not qr:
        # 最后兜底：截取整个页面中心区域
        weibo_logger.warning(_msg("⚠️", "未找到二维码元素，截取页面截图"))
        qrcode_path = build_login_qrcode_path(account_file)
        qrcode_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(qrcode_path))
        weibo_logger.info(_msg("🖼️", f"页面截图已保存到: {qrcode_path}"))
        return {"image_path": str(qrcode_path), "image_data_url": ""}

    await qr.wait_for(state="visible", timeout=30000)

    qrcode_path = build_login_qrcode_path(account_file)
    qrcode_path.parent.mkdir(parents=True, exist_ok=True)

    # 优先直接下载高清图片 URL（img 元素）
    tag = await qr.evaluate("el => el.tagName.toLowerCase()")
    if tag == "img":
        src = await qr.get_attribute("src")
        if src and src.startswith("http"):
            try:
                resp = await page.context.request.get(src)
                qrcode_path.write_bytes(await resp.body())
            except Exception:
                await qr.screenshot(path=str(qrcode_path))
        else:
            await qr.screenshot(path=str(qrcode_path))
    else:
        # canvas 或其他元素：直接截图
        await qr.screenshot(path=str(qrcode_path))

    weibo_logger.info(_msg("🖼️", f"二维码已保存到: {qrcode_path}"))
    # 终端不渲染二维码，只给出文件位置，用微博APP打开图片扫码
    print(f"请打开 {qrcode_path}，用微博APP扫描该二维码登录")
    return {"image_path": str(qrcode_path), "image_data_url": ""}


async def _is_login_completed(page: Page) -> bool:
    """判断微博登录是否完成：URL 回到首页 且 出现用户头像/feed 流。"""
    url = page.url
    # 还在 login/passport 页面
    if "newlogin" in url or "passport" in url:
        return False
    # 检查是否回到首页且有用户态
    if "weibo.com" in url and "login" not in url:
        # 出现 feed 流或头像说明登录成功
        has_user = await page.locator('[class*="Nav_avatar"], [class*="woo-avatar"]').count()
        if has_user:
            return True
        # cookies 中有 SUB 说明登录成功
        cookies = await page.context.cookies()
        if any(c.get("name") == "SUB" for c in cookies):
            return True
    return False


async def weibo_cookie_gen(account_file, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 120, headless: bool = LOCAL_CHROME_HEADLESS):
    """无头/有头扫码登录微博，保存 cookie。

    流程：直接打开微博 passport 扫码页 → 截取二维码 → 等待扫码完成（跳转回首页）→ 保存 storage_state。
    返回标准 login result dict。
    """
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)
    qrcode_path = None
    result = _build_login_result(False, "failed", "微博登录失败", account_file)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        try:
            page = await context.new_page()
            # 直接导航到 passport 扫码登录页，绕过首页的"登录"按钮（headless 下不可见）
            await page.goto(WEIBO_PASSPORT_QR_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            if headless:
                weibo_logger.info(_msg("🧍", "无头登录中：二维码已存为图片，请用微博APP扫码"))
            else:
                weibo_logger.info(_msg("🧍", "请在打开的浏览器中扫码登录微博"))

            # 截取二维码
            qrcode_info = await _grab_qr(page, account_file)
            qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info.get("image_path") else None
            await _emit_qrcode_callback(qrcode_callback, qrcode_info)

            weibo_logger.info(_msg("🧍", "请扫码，正在耐心等待登录完成"))

            # 轮询等待登录完成（页面跳转离开 passport 或出现用户态 cookie）
            for _ in range(max_checks):
                current_url = page.url
                # 跳转离开 passport 页面说明登录成功
                if "passport" not in current_url and "weibo.com" in current_url:
                    weibo_logger.info(_msg("🥳", f"扫码成功，跳转到: {current_url}"))
                    result = _build_login_result(True, "success", "微博扫码登录成功", account_file, qrcode_info, current_url)
                    break
                # 检查 cookies 中是否出现 SUB（部分情况页面不跳转但 cookie 已写入）
                cookies = await context.cookies()
                if any(c.get("name") == "SUB" and c.get("value") for c in cookies):
                    weibo_logger.info(_msg("🥳", f"扫码成功（检测到 SUB cookie），当前: {current_url}"))
                    result = _build_login_result(True, "success", "微博扫码登录成功", account_file, qrcode_info, current_url)
                    break
                await page.wait_for_timeout(poll_interval * 1000)
            else:
                result = _build_login_result(False, "timeout", "等待微博扫码登录超时", account_file, qrcode_info, page.url)

            if result["success"]:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                weibo_logger.success(_msg("🥳", f"cookie 已保存: {account_file}"))
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                weibo_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                weibo_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()
    return result


async def cookie_auth(account_file):
    """验证微博 cookie 是否有效。访问首页，检测是否出现登录提示。"""
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            page = await context.new_page()
            await page.goto(WEIBO_HOME_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # 检查是否被跳转到登录页
            if "newlogin" in page.url or "passport" in page.url:
                weibo_logger.info(_msg("🥹", "cookie 已失效（跳转到登录页）"))
                return False

            # 检查是否有「登录」按钮（未登录态会显示）
            login_btn = page.get_by_text("登录", exact=True).first
            if await login_btn.count() and await login_btn.is_visible():
                weibo_logger.info(_msg("🥹", "cookie 已失效（出现登录按钮）"))
                return False

            weibo_logger.success(_msg("🥳", "cookie 有效"))
            return True
        except Exception as exc:
            weibo_logger.warning(_msg("😵", f"cookie 校验出错，按失效处理: {exc}"))
            return False
        finally:
            await browser.close()


async def weibo_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    """统一入口：检查 cookie → 如无效且 handle=True 则触发扫码登录。"""
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie 文件不存在或已失效", account_file)
            return result if return_detail else False
        weibo_logger.info(_msg("🥹", "cookie 文件不存在或已失效，自动打开浏览器请扫码登录"))
        result = await weibo_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie 有效", account_file)
    return result if return_detail else True


class WeiBoVideo(BaseVideoUploader):
    """微博视频上传。

    流程：打开首页 → 点「视频」入口弹出发布窗口 → 上传视频文件 →
         等待上传完成 → 填标题 → 上传封面 → 勾选二创 + AI声明 →
         填描述 → 点击发布。
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
            raise RuntimeError(f"cookie文件不存在，请先完成微博登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成微博登录: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("视频标题不能为空")
        if not self.thumbnail_path:
            raise ValueError("微博视频发布必须提供封面图（--thumbnail）")
        self.file_path = str(self.validate_video_file(self.file_path))
        self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))
        # 封面文件 < 5MB
        thumb_size = Path(self.thumbnail_path).stat().st_size
        if thumb_size > 5 * 1024 * 1024:
            raise ValueError(f"封面文件过大（{thumb_size / 1024 / 1024:.1f}MB），微博要求 < 5MB")

    async def upload(self, playwright: Playwright) -> None:
        weibo_logger.info(_msg("🧍", "先检查 cookie 和视频文件"))
        await self.validate_upload_args()
        weibo_logger.info(_msg("🥳", "上传前检查通过"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(
            storage_state=self.account_file,
            viewport={"width": 1280, "height": 2000},  # 高视口，确保发布按钮等在可视区
        )

        try:
            page = await context.new_page()
            await page.goto(WEIBO_HOME_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            weibo_logger.info(_msg("🏃", f"开始上传视频: {self.title}"))

            # 1) 点击首页「视频」入口，弹出发布窗口（popup）
            publish_page = await self._open_video_publish_page(page)

            # 2) 上传视频文件
            await self._upload_video_file(publish_page)

            # 3) 等待视频真正上传完成（"上传完成"块可见）
            await self._wait_upload_complete(publish_page)

            # 4) 类型 = 二创（必选）
            await self._select_type(publish_page)

            # 5) 内容声明 = 含AI生成内容（必选）
            await self._select_declaration(publish_page)

            # 6) 填写标题（必填）
            await self._fill_title(publish_page)

            # 7) 上传封面（必填）
            await self._upload_thumbnail(publish_page)

            # 8) 合集：选已有，没有则新建（配置了 collection_name 时）
            if self.collection_name:
                await self._apply_collection(publish_page)

            # 9) 填写描述（包含标签）
            await self._fill_description(publish_page)

            # 10) 点击发布并校验真成功
            await self._submit_publish(publish_page)

            # 保存 cookie
            await context.storage_state(path=self.account_file)
            weibo_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            await browser.close()

    async def _open_video_publish_page(self, page: Page) -> Page:
        """点击首页「视频」入口，等待 popup 视频发布页。"""
        async with page.expect_popup(timeout=30000) as popup_info:
            # 录制脚本：page.locator("span").filter(has_text="视频").click()
            video_btn = page.locator("span").filter(has_text="视频").first
            await video_btn.wait_for(state="visible", timeout=15000)
            await video_btn.click()
        publish_page = await popup_info.value
        await publish_page.wait_for_timeout(3000)
        weibo_logger.info(_msg("🏃", "已打开视频发布页"))
        return publish_page

    async def _upload_video_file(self, page: Page) -> None:
        """点击「上传视频」按钮并设置文件。"""
        # 录制脚本：page2.get_by_role("button", name="上传视频").click()
        upload_btn = page.get_by_role("button", name="上传视频")
        await upload_btn.wait_for(state="visible", timeout=15000)

        # 通过 file chooser 设置文件
        async with page.expect_file_chooser(timeout=10000) as fc_info:
            await upload_btn.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)
        weibo_logger.info(_msg("🏃", f"已选择视频文件: {self.file_path}"))

    async def _wait_upload_complete(self, page: Page, timeout: int = 900) -> None:
        """等待视频真正上传完成。

        真实 DOM：上传区有三个并列的 `_info` 块（上传中 / 暂停中 / 上传完成），未到的
        状态用 `display:none` 隐藏，只有当前状态那块可见：
          - 上传中：`<span>上传中</span>` + `269.61MB/269.61MB`
          - 上传完成：`<i class="woo-font woo-font--check">` + `<span>上传完成</span>`
        以"上传完成"块**变为可见**作为唯一完成判据（三块文字都恒在 DOM 里，不能用文字存在与否判断）。
        """
        start = time.monotonic()
        done = page.locator('div:has(> i.woo-font--check) span:text-is("上传完成")').first
        uploading = page.locator('span:text-is("上传中")').first
        last_log = 0.0
        while True:
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"视频上传超时（>{timeout}s）")

            body = ""
            try:
                body = await page.inner_text("body")
            except Exception:
                pass
            if "上传失败" in body:
                raise RuntimeError("视频上传失败")

            try:
                if await done.is_visible():
                    weibo_logger.success(_msg("🥳", "视频上传完毕（'上传完成' 可见）"))
                    return
            except Exception:
                pass

            if time.monotonic() - last_log > 5:
                try:
                    if await uploading.is_visible():
                        m = re.search(r"上传中[\s\S]{0,60}?([\d.]+)\s*MB\s*/\s*([\d.]+)\s*MB", body)
                        if m:
                            weibo_logger.info(_msg("🏃", f"上传中 {m.group(1)}/{m.group(2)}MB"))
                        else:
                            weibo_logger.info(_msg("🏃", "上传中…"))
                except Exception:
                    pass
                last_log = time.monotonic()
            await asyncio.sleep(2)

    async def _fill_title(self, page: Page) -> None:
        """填写标题（最长30字）。"""
        title_field = page.get_by_placeholder("填写标题（0～30个字）")
        await title_field.wait_for(state="visible", timeout=15000)
        title = self.title[:self.max_title_length]
        await title_field.click()
        await title_field.fill(title)
        weibo_logger.info(_msg("🏷️", f"标题已填写: {title}"))

    async def _upload_thumbnail(self, page: Page) -> None:
        """上传封面（必填）。

        真实 DOM/坑位：
          - 主表单 `<a>上传封面</a>` → 弹出「编辑封面」层 `_layer_1mhd8_153`（层内有
            `input[type=file]._file_1mhd8_65`，可直接 set_input_files）。
          - **关键坑**：选图后封面要走**服务端裁切**，期间层内显示"裁切处理中/处理中请稍后…"，
            "完成"按钮此时点了也不生效；而「编辑封面」层开着时，微博会把**主表单层
            `_layer_19x8d_246` 置为 display:none** → 之后的合集开关/发布按钮全部 0 尺寸点不动。
          - 因此必须：等裁切处理结束(cropper 出 blob 图且无"处理中"字样) → 点"完成" →
            **确认编辑封面层已关闭**（否则重试/抛错），主表单才会恢复可见。
        """
        # 打开「上传封面」
        upload_link = page.get_by_role("link", name="上传封面").first
        if not await upload_link.count():
            upload_link = page.locator('a:has-text("上传封面")').first
        await upload_link.wait_for(state="visible", timeout=20000)
        await upload_link.click()
        await page.wait_for_timeout(1200)

        # 「编辑封面」层
        cover_layer = page.locator('div.wbpro-layer:has(div:text-is("编辑封面"))').first
        await cover_layer.wait_for(state="visible", timeout=15000)

        # 塞封面文件（用 .first 命中可见主输入；.last 会命中隐藏面板里 0 尺寸的裁切器，
        # 导致"裁切处理中"永久卡住、发不出 picupload 请求）
        file_input = page.locator('input[type="file"][accept*="jpg"]').first
        await file_input.wait_for(state="attached", timeout=15000)
        await file_input.set_input_files(self.thumbnail_path)
        weibo_logger.info(_msg("🏃", f"已选择封面图片: {self.thumbnail_path}"))

        # cropper 本地出图（秒级）
        blob_img = page.locator('.cropper-container img[src^="blob:"], .wb_cropper img[src^="blob:"]').first
        try:
            await blob_img.wait_for(state="attached", timeout=20000)
        except PWTimeoutError:
            weibo_logger.warning(_msg("⚠️", "cropper 未见 blob 图，仍尝试点完成"))
        await page.wait_for_timeout(500)

        # 高容错收尾：裁切时长因图/网络而异，不赌固定时长、不赌某个请求。
        # 只认**真实结果**——「编辑封面」层是否关闭；期间**周期性重复点"完成"**
        # （裁切处理中点了无害，处理完的那次点击就会关闭层），并识别裁切/上传报错。
        finish_btn = cover_layer.locator('div.wbpro-layer-btn button:has(span:text-is("完成"))').first
        if not await finish_btn.count():
            finish_btn = cover_layer.locator('button:has(span:text-is("完成"))').first
        closed = False
        last_click = 0.0
        start = time.monotonic()
        while time.monotonic() - start < 300:  # 宽松 5 分钟
            # 结果判定：编辑封面层不再可见 → 成功
            try:
                if not await cover_layer.is_visible():
                    closed = True
                    break
            except Exception:
                closed = True
                break
            # 报错识别（裁切/格式/上传失败）
            try:
                layer_txt = await cover_layer.inner_text()
            except Exception:
                layer_txt = ""
            for err in ("裁切失败", "上传失败", "图片格式", "封面上传失败", "重新上传", "格式不支持"):
                if err in layer_txt:
                    raise RuntimeError(f"封面裁切/上传失败：{err}")
            # 周期性点"完成"（每 4s 一次；跳过明确 disabled）
            if time.monotonic() - last_click > 4:
                try:
                    if await finish_btn.count() and await finish_btn.is_visible():
                        if (await finish_btn.get_attribute("aria-disabled")) != "true":
                            await finish_btn.click(timeout=3000)
                except Exception:
                    pass
                last_click = time.monotonic()
            await asyncio.sleep(2)
        if not closed:
            raise RuntimeError("封面「完成」后编辑封面层长时间(>300s)未关闭，疑似裁切服务异常")

        # 确认主表单层已恢复可见（display 从 none 变回）
        main_form = page.locator('div.wbpro-layer[class*="_layer_19x8d"]').first
        try:
            await main_form.wait_for(state="visible", timeout=10000)
        except PWTimeoutError:
            weibo_logger.warning(_msg("⚠️", "封面关闭后主表单未确认可见，继续尝试"))
        weibo_logger.success(_msg("🖼️", "封面已上传并完成"))

    async def _select_type(self, page: Page) -> None:
        """类型（必选）：选择「二创」。

        真实 DOM：`<div class="_type_1vpmt_29">` 下两个
        `<label class="woo-radio-main"><input type=radio><span class="woo-radio-shadow"><span class="woo-radio-text">二创</span></label>`，
        选中后对应 `woo-radio-shadow` 追加 `woo-radio-checked`。
        """
        label = page.locator('label.woo-radio-main:has(span.woo-radio-text:text-is("二创"))').first
        await label.wait_for(state="visible", timeout=20000)
        await label.click()
        await page.wait_for_timeout(500)

        checked_sel = 'label.woo-radio-main:has(span.woo-radio-text:text-is("二创")) span.woo-radio-checked'
        if not await page.locator(checked_sel).count():
            # 兜底：直接勾选 radio input
            try:
                await label.locator('input.woo-radio-input').check()
                await page.wait_for_timeout(300)
            except Exception:
                pass
        if not await page.locator(checked_sel).count():
            raise RuntimeError("类型「二创」未选中")
        weibo_logger.info(_msg("🏷️", "类型已选：二创"))

    async def _select_declaration(self, page: Page) -> None:
        """内容声明（必选）：选择「含AI生成内容」。

        真实 DOM：
          - 触发下拉：`<div class="_gap1_nsgmr_26">` 内 `.woo-pop-ctrl`（带 caretDown 的 wbpro-select）
          - 弹层：`<div class="_panel_nsgmr_114">`，选项 `<button class="_option..."><span class="_optionLabel...">含AI生成内容</span></button>`
          - 选中后该 button 内 `._check_nsgmr_237` 追加 `_checkActive_nsgmr_251`（带 _checkMark）
          - 底部 `._footer_nsgmr_270 button`（"确定"）关闭弹层
        """
        # 打开下拉
        trigger = page.locator('div[class*="_gap1_nsgmr"] .woo-pop-ctrl').first
        if not await trigger.count():
            trigger = page.locator('div:has(> div[class*="_tit1_nsgmr"]) .woo-pop-ctrl').first
        await trigger.wait_for(state="visible", timeout=15000)
        await trigger.click()
        await page.wait_for_timeout(1000)

        panel = page.locator('div[class*="_panel_nsgmr"]').first
        if await panel.count():
            try:
                await panel.wait_for(state="visible", timeout=8000)
            except PWTimeoutError:
                panel = None
        else:
            panel = None

        scope = panel if panel is not None else page
        ai_opt = scope.locator('button:has(span:text-is("含AI生成内容"))').first
        await ai_opt.wait_for(state="visible", timeout=8000)
        await ai_opt.click()
        await page.wait_for_timeout(500)

        # 校验选中态
        if not await ai_opt.locator('[class*="_checkActive"]').count():
            weibo_logger.warning(_msg("⚠️", "内容声明「含AI生成内容」疑似未激活，仍尝试点确定"))

        # 点确定关闭弹层
        confirm = scope.locator('div[class*="_footer_nsgmr"] button:has(span:text-is("确定"))').first
        if not await confirm.count():
            confirm = scope.locator('button:has(span:text-is("确定"))').last
        if await confirm.count():
            await confirm.click()
            await page.wait_for_timeout(500)
        weibo_logger.info(_msg("🏷️", "内容声明已选：含AI生成内容"))

    async def _fill_description(self, page: Page) -> None:
        """填写描述区域（正文 + 标签）。

        微博描述区 placeholder: "有什么新鲜事想分享给大家？"
        标签用 #话题# 格式插入到描述末尾。
        """
        desc_field = page.get_by_placeholder("有什么新鲜事想分享给大家？")
        if not await desc_field.count():
            weibo_logger.warning(_msg("⚠️", "未找到描述输入框"))
            return

        # 组装描述内容：正文 + 标签
        content = self.desc
        if self.tags:
            tag_str = " ".join(f"#{t}#" for t in self.tags)
            content = f"{content}\n{tag_str}" if content else tag_str

        if content:
            await desc_field.click()
            await desc_field.fill(content)
            weibo_logger.info(_msg("📝", f"描述已填写（{len(content)}字）"))

    async def _apply_collection(self, page: Page) -> None:
        """合集：选已有，没有则新建。

        真实 DOM：打开「合集」开关后出现合集面板 `._scroll_19x8d_143`——已有合集每行一个
        `woo-checkbox` + 只读 `input value="名字(共N集)"`；末尾 `._add_19x8d_63`（「新建合集」）。
          - 已有：勾选名字匹配（去掉"(共N集)"后缀后）那一行的 checkbox。
          - 没有：点「新建合集」→ 新增一行(自动勾选)且带可编辑 input → 填合集名(≤12)。
        """
        target = (self.collection_name or "").strip()
        if not target:
            return

        # 1) 打开合集开关
        block = page.locator('div[class*="_switch_"]:has(div[class*="_tit1_"]:text-is("合集"))').first
        if not await block.count():
            block = page.locator('div:has(> div:text-is("合集")):has(label.woo-switch-main)').first
        try:
            switch_input = block.locator('label.woo-switch-main input.woo-switch-input').first
            try:
                already = await switch_input.is_checked()
            except Exception:
                already = False
            if not already:
                for sw in (
                    block.locator('label.woo-switch-main span[role="switch"]').first,
                    block.locator('label.woo-switch-main').first,
                ):
                    try:
                        await sw.click(timeout=6000)
                    except Exception:
                        try:
                            await sw.click(timeout=4000, force=True)
                        except Exception:
                            continue
                    await page.wait_for_timeout(1000)
                    try:
                        if await switch_input.is_checked():
                            break
                    except Exception:
                        break
        except Exception as exc:
            weibo_logger.warning(_msg("⚠️", f"打开合集开关异常，仍尝试找面板: {exc}"))

        # 2) 合集面板
        panel = page.locator('div[class*="_scroll_"]:has(div[class*="_add_"])').first
        if not await panel.count():
            panel = page.locator('div:has(> div[class*="_add_"]:has-text("新建合集"))').first
        try:
            await panel.wait_for(state="visible", timeout=8000)
        except PWTimeoutError:
            weibo_logger.warning(_msg("⚠️", "未见合集面板，跳过合集"))
            return

        # 3) 匹配已有合集（去掉"(共N集)"后缀）
        rows = panel.locator('div[class*="_top2_"]')
        n = await rows.count()
        matched = False
        for i in range(n):
            row = rows.nth(i)
            inp = row.locator('input[type="text"]').first
            if not await inp.count():
                continue
            val = (await inp.get_attribute("value")) or ""
            name = re.sub(r"\(共\d+集\)\s*$", "", val).strip()
            if name and name == target:
                await row.locator('label.woo-checkbox-main').first.click()
                await page.wait_for_timeout(400)
                matched = True
                weibo_logger.info(_msg("🥳", f"已选已有合集：{target}"))
                break

        # 4) 没有则新建（best-effort：新建失败只跳过合集，绝不中断发布）
        if not matched:
            try:
                add_btn = panel.locator('div[class*="_add_"]:has-text("新建合集")').first
                if not await add_btn.count():
                    add_btn = page.locator('div:has-text("新建合集")').last
                # 「新建合集」整行 598px 宽、可点的"＋新建合集"文字在左侧；点整行几何中心会落到
                # 右侧空白、不触发。改为点内部"新建合集"文字 span（在左侧、必命中 onClick）。
                add_target = add_btn.get_by_text("新建合集", exact=True).first
                if not await add_target.count():
                    add_target = add_btn
                # 新建行的可编辑 input（已有行的 input 都带 disabled，新建行的没有）
                new_inp = panel.locator('div[class*="_top2_"] input[type="text"]:not([disabled])').last
                created = False
                for _ in range(3):
                    try:
                        await add_target.scroll_into_view_if_needed(timeout=2000)
                    except Exception:
                        pass
                    try:
                        await add_target.click(timeout=4000)
                    except Exception:
                        try:
                            await add_target.click(timeout=3000, force=True)
                        except Exception:
                            try:
                                await add_target.evaluate("el => el.click()")
                            except Exception:
                                pass
                    await page.wait_for_timeout(800)
                    if await new_inp.count() and await new_inp.is_visible():
                        created = True
                        break
                if not created:
                    weibo_logger.warning(_msg("⚠️", f"「新建合集」未出现输入行，跳过合集继续发布：{target[:12]}"))
                    return
                await new_inp.click()
                await new_inp.fill(target[:12])
                await page.wait_for_timeout(500)
                weibo_logger.info(_msg("🥳", f"已新建合集：{target[:12]}"))
            except Exception as exc:
                weibo_logger.warning(_msg("⚠️", f"新建合集失败，跳过合集继续发布：{exc}"))
                return

    async def _submit_publish(self, page: Page) -> None:
        """点击发布并校验真成功。

        真实 DOM：
          - 发布按钮：`._check_2z30i_81 button`（内容"发布"）。按钮中心可能被空 div 覆盖，
            用 JS 触发按钮自身 click 绕过遮罩。
          - 成功唯一可靠判据：隐藏成功层 `_layer1_9a8j7_2` 由 `display:none` 变**可见**，
            其中含"再发一条视频"按钮 → 用它/该按钮可见判定真成功。
            （"视频已上传成功，将在转码后发布"文字是恒存在的隐藏模板，不能作判据。）
          - 60s 内判不到成功 → 抛错（不再冒充成功），交由上层记失败。
        """
        # 关掉可能残留的下拉/弹层
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
        except Exception:
            pass

        publish_btn = page.locator('div[class*="_check_2z30i"] button:has(span:text-is("发布"))').first
        if not await publish_btn.count():
            publish_btn = page.get_by_role("button", name="发布").first
        await publish_btn.wait_for(state="visible", timeout=15000)
        await publish_btn.evaluate("el => el.click()")
        weibo_logger.info(_msg("🏃", "已点击发布按钮(JS)"))

        success_layer = page.locator('div[class*="_layer1_9a8j7"]').first
        again_btn = page.locator('button:has(span:text-is("再发一条视频"))').first
        start = time.monotonic()
        while time.monotonic() - start < 60:
            try:
                if await again_btn.is_visible():
                    weibo_logger.success(_msg("🥳", "视频发布成功（出现「再发一条视频」）"))
                    return
            except Exception:
                pass
            try:
                if await success_layer.is_visible():
                    weibo_logger.success(_msg("🥳", "视频发布成功（成功层可见）"))
                    return
            except Exception:
                pass
            # 处理可能的二次确认对话框
            try:
                dialog = page.locator('.woo-dialog-main, .woo-modal-wrap, [class*="Dialog"]').first
                if await dialog.count() and await dialog.is_visible():
                    for name in ("确定", "确认", "继续", "仍然发布", "发布"):
                        cb = dialog.locator(f'button:has(span:text-is("{name}"))').first
                        if await cb.count() and await cb.is_visible():
                            await cb.evaluate("el => el.click()")
                            weibo_logger.info(_msg("🏃", f"已确认对话框：{name}"))
                            break
            except Exception:
                pass
            await page.wait_for_timeout(1500)

        raise RuntimeError("发布后 60s 未见成功层/「再发一条视频」，判定发布未成功（未入库）")

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
