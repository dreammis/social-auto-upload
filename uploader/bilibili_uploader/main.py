# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
import os
from datetime import datetime
from pathlib import Path

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import DEBUG_MODE, LOCAL_CHROME_PATH
from myUtils.screenshot_manager import ScreenshotManager
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file
from utils.login_qrcode import save_data_url_image
from utils.log import bilibili_logger
from utils.runtime_config import get_local_chrome_headless

BILIBILI_UPLOAD_URL = "https://member.bilibili.com/platform/home"
BILIBILI_UPLOAD_VIDEO_URL = "https://member.bilibili.com/platform/upload/video/frame"
BILIBILI_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
BILIBILI_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


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


async def _launch_bilibili_browser(playwright: Playwright, *, headless: bool, executable_path: str | None = None):
    launch_kwargs = {"headless": headless}
    browser_path = executable_path or LOCAL_CHROME_PATH
    if browser_path:
        launch_kwargs["executable_path"] = browser_path
    else:
        launch_kwargs["channel"] = "chrome"
    return await playwright.chromium.launch(**launch_kwargs)


async def cookie_auth(account_file):
    """验证B站cookie是否有效"""
    async with async_playwright() as playwright:
        browser = await _launch_bilibili_browser(playwright, headless=get_local_chrome_headless())
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(BILIBILI_UPLOAD_URL)
            try:
                await page.wait_for_url(BILIBILI_UPLOAD_URL, timeout=5000)
            except Exception:
                # 如果URL不匹配，可能被重定向到登录页
                bilibili_logger.warning(_msg("⚠️", "URL不匹配，可能需要重新登录"))
                return False

            # 检查是否有登录按钮或扫码登录提示（如果出现说明cookie失效）
            try:
                await page.get_by_text("扫码登录").wait_for(timeout=5000)
                bilibili_logger.error(_msg("❌", "cookie失效，需要扫码登录"))
                return False
            except Exception:
                # 如果5秒内没有出现"扫码登录"，说明cookie有效
                bilibili_logger.success(_msg("✅", "cookie有效"))
                return True

        except Exception as exc:
            bilibili_logger.error(_msg("❌", f"cookie验证失败: {exc}"))
            return False
        finally:
            await browser.close()


async def bilibili_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool | None = None):
    """检查B站cookie是否有效，如果失效则重新登录"""
    if headless is None:
        headless = get_local_chrome_headless()
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False
        bilibili_logger.info(_msg("🥹", "cookie 失效了，准备打开浏览器重新登录"))
        result = await bilibili_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def _extract_bilibili_qrcode_src(page: Page) -> str:
    """提取B站登录二维码图片地址"""
    # 等待登录页面加载
    await page.wait_for_selector("div.login-scan-wp", timeout=30000)

    # 查找二维码图片
    qrcode_img = page.locator('div.login-scan-wp img.qrcode-img').first
    await qrcode_img.wait_for(state="visible", timeout=10000)

    qrcode_src = await qrcode_img.get_attribute("src")
    if not qrcode_src:
        raise RuntimeError("未获取到B站登录二维码地址")

    return qrcode_src


async def _save_bilibili_qrcode(page: Page, account_file: str, qrcode_callback=None) -> dict:
    """保存B站登录二维码"""
    qrcode_src = await _extract_bilibili_qrcode_src(page)
    qrcode_path = build_login_qrcode_path(account_file, platform="bilibili")

    # 保存二维码图片
    await save_data_url_image(qrcode_src, qrcode_path)

    # 解析二维码内容
    qrcode_content = await decode_qrcode_from_path(qrcode_path)

    qrcode_info = {
        "url": qrcode_content,
        "image_path": str(qrcode_path),
        "image_data": qrcode_src,
    }

    await _emit_qrcode_callback(
        qrcode_callback,
        {
            "status": "qrcode_generated",
            "qrcode": qrcode_info,
            "message": "请使用B站APP扫码登录",
        },
    )

    # 在终端显示二维码
    print_terminal_qrcode(qrcode_content, qrcode_path, "B站APP")

    return qrcode_info


async def _wait_for_bilibili_login(
    page: Page,
    account_file: str,
    qrcode_info: dict,
    qrcode_callback=None,
    poll_interval: float = 2.0,
    max_checks: int = 60,
) -> dict:
    """等待B站扫码登录完成"""
    for check_index in range(max_checks):
        await asyncio.sleep(poll_interval)

        # 检查是否已经登录成功（跳转到创作者中心）
        current_url = page.url
        if "member.bilibili.com" in current_url and "login" not in current_url:
            bilibili_logger.info(_msg("🎉", "扫码登录成功"))
            await _emit_qrcode_callback(
                qrcode_callback,
                {
                    "status": "login_success",
                    "qrcode": qrcode_info,
                    "message": "B站扫码登录成功",
                    "current_url": current_url,
                },
            )
            return _build_login_result(True, "login_success", "登录成功", account_file, qrcode_info, current_url)

        # 检查二维码是否过期
        qrcode_status = page.locator('div.login-scan-wp')
        if await qrcode_status.count():
            expired_text = await qrcode_status.get_by_text("二维码已失效").count()
            if expired_text:
                bilibili_logger.warning(_msg("⏰", "二维码已过期"))
                await _emit_qrcode_callback(
                    qrcode_callback,
                    {
                        "status": "qrcode_expired",
                        "qrcode": qrcode_info,
                        "message": "B站登录二维码已过期",
                    },
                )
                return _build_login_result(False, "qrcode_expired", "二维码已过期", account_file, qrcode_info, current_url)

        bilibili_logger.debug(_msg("🧍", f"等待扫码登录... ({check_index + 1}/{max_checks})"))

    bilibili_logger.warning(_msg("⏰", "等待扫码超时"))
    await _emit_qrcode_callback(
        qrcode_callback,
        {
            "status": "timeout",
            "qrcode": qrcode_info,
            "message": "等待B站扫码登录超时",
        },
    )
    return _build_login_result(False, "timeout", "等待扫码超时", account_file, qrcode_info, current_url)


async def bilibili_cookie_gen(account_file, qrcode_callback=None, headless: bool | None = None, poll_interval: float = 2.0, max_checks: int = 60):
    """生成B站登录cookie"""
    if headless is None:
        headless = get_local_chrome_headless()

    result = _build_login_result(False, "failed", "未知错误", account_file)
    qrcode_path = None

    async with async_playwright() as playwright:
        browser = await _launch_bilibili_browser(playwright, headless=headless)
        try:
            context = await browser.new_context()
            context = await set_init_script(context)
            page = await context.new_page()

            # 打开B站登录页面
            await page.goto("https://passport.bilibili.com/")
            await page.wait_for_selector("div.login-scan-wp", timeout=30000)

            # 保存并显示二维码
            qrcode_info = await _save_bilibili_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])

            bilibili_logger.info(_msg("🧍", "请扫码，小人正在耐心等待登录完成"))

            # 等待扫码登录
            result = await _wait_for_bilibili_login(
                page,
                account_file,
                qrcode_info,
                qrcode_callback=qrcode_callback,
                poll_interval=poll_interval,
                max_checks=max_checks,
            )

            if result["success"]:
                await asyncio.sleep(2)
                # 保存cookie
                await context.storage_state(path=account_file)

                # 验证cookie是否有效
                if not await cookie_auth(account_file):
                    result = _build_login_result(
                        False,
                        "cookie_invalid",
                        "B站扫码流程结束，但 cookie 校验失败",
                        account_file,
                        qrcode_info,
                        page.url,
                    )

        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if qrcode_path and remove_qrcode_file(qrcode_path):
                bilibili_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                bilibili_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()

    return result


class BilibiliBaseUploader(BaseVideoUploader):
    """B站上传基类"""

    def __init__(
        self,
        title: str,
        file_path: str,
        tags: list[str],
        publish_date: datetime | int,
        account_file: str,
        tid: int = 171,  # 默认分区：电子竞技
        desc: str = "",
        cover_path: str | None = None,
        copyright_type: int = 1,  # 1=自制，2=转载
        no_reprint: int = 0,
        ai_declaration: bool = False,
        publish_strategy: str = BILIBILI_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool | None = None,
        screenshot_manager = None,  # 截图管理器
    ):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.tid = tid
        self.desc = desc or title
        self.cover_path = cover_path
        self.copyright_type = copyright_type
        self.no_reprint = no_reprint
        self.ai_declaration = ai_declaration
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = get_local_chrome_headless() if headless is None else headless
        self.screenshot_manager = screenshot_manager  # 截图管理器

    async def validate_base_args(self):
        """验证基本参数"""
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成B站登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成B站登录: {self.account_file}")

        self.file_path = self.validate_video_file(self.file_path)
        if self.cover_path:
            self.cover_path = self.validate_image_file(self.cover_path)

        if self.publish_strategy not in {BILIBILI_PUBLISH_STRATEGY_IMMEDIATE, BILIBILI_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == BILIBILI_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0


class BilibiliVideo(BilibiliBaseUploader):
    """B站视频上传"""
    
    upload_page = "https://member.bilibili.com/platform/upload/video/frame"

    async def main(self):
        """主上传流程"""
        await self.validate_base_args()

        async with async_playwright() as playwright:
            browser = await _launch_bilibili_browser(playwright, headless=self.headless, executable_path=self.local_executable_path)
            try:
                context = await browser.new_context(storage_state=self.account_file)
                context = await set_init_script(context)
                page = await context.new_page()

                # 打开B站创作者中心
                await page.goto(BILIBILI_UPLOAD_VIDEO_URL)
                bilibili_logger.info(_msg("🎬", f"开始上传视频: {self.file_path}"))

                # 上传视频文件
                await self._upload_video_file(page)

                # 填写视频信息
                await self._fill_video_info(page)

                # 提交发布
                await self._submit_video(page)

                bilibili_logger.info(_msg("🎉", "视频上传成功"))

            finally:
                await context.close()
                await browser.close()

    async def _upload_video_file(self, page: Page):
        """上传视频文件"""
        # 等待上传页面加载
        await page.wait_for_load_state('networkidle', timeout=30000)
        
        # 使用更具体的定位器，避免匹配到多个input
        # 第一个input是视频上传的input（#video-up-app input[type="file"]）
        file_input = page.locator('#video-up-app input[type="file"]')
        await file_input.set_input_files(str(self.file_path))

        bilibili_logger.info(_msg("📤", "视频文件已选择，等待上传完成"))

        # 等待上传完成（检查进度条或状态）
        await page.wait_for_timeout(5000)
        await self._wait_for_upload_complete(page)

    async def _wait_for_upload_complete(self, page: Page):
        """等待视频上传完成"""
        # 检查上传进度
        max_wait_time = 300  # 最多等待5分钟
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < max_wait_time:
            # 检查是否有上传成功的提示
            if await page.get_by_text("上传成功").count() or await page.get_by_text("上传完成").count():
                bilibili_logger.info(_msg("✅", "视频上传完成"))
                return

            # 检查是否有上传失败的提示
            if await page.get_by_text("上传失败").count():
                raise RuntimeError("视频上传失败")

            await page.wait_for_timeout(2000)

        raise RuntimeError("视频上传超时")

    async def _fill_video_info(self, page: Page):
        """填写视频信息"""
        # 等待视频上传完成后，页面会跳转到编辑页面
        bilibili_logger.info(_msg("⏳", "等待页面跳转到编辑页面"))
        
        # 等待编辑页面加载
        await page.wait_for_load_state('networkidle', timeout=30000)
        
        # 等待标题输入框出现
        await page.wait_for_timeout(5000)
        
        bilibili_logger.info(_msg("📝", "开始填写视频信息"))
        
        # 1. 填写标题
        await self._fill_title(page)
        
        # 2. 填写简介
        await self._fill_description(page)
        
        # 3. 填写标签
        await self._fill_tags(page)
        
        # 4. 选择分区
        await self._select_category(page, self.tid)
        
        # 5. 上传封面
        if self.cover_path:
            await self._upload_cover(page)
        
        # 6. 设置原创声明（禁止转载）
        if self.no_reprint == 1:
            await self._set_original_declaration(page)
        
        # 7. 设置AI创作声明
        if self.ai_declaration:
            await self._set_ai_declaration(page)
        
        bilibili_logger.info(_msg("🎉", "所有视频信息已填写完成"))

    async def _fill_title(self, page: Page):
        """填写标题（只保留#前面的内容）"""
        # 处理标题：只保留#前面的部分
        title_text = self.title
        if '#' in title_text:
            title_text = title_text.split('#')[0].strip()
        
        # 限制长度（B站最多80字）
        final_title = title_text[:80]
        # 方式1: 使用placeholder定位器
        title_input = page.locator('input[placeholder="请输入稿件标题"]').first
        try:
            await title_input.wait_for(state="visible", timeout=15000)
            await title_input.click()
            await page.wait_for_timeout(300)
            
            # 先全选再删除，确保清空原有内容
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.wait_for_timeout(200)
            
            # 再填入新标题
            await title_input.fill(final_title)
            bilibili_logger.info(_msg("✅", f"标题已填写 [方式1-placeholder]: {final_title}"))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"方式1(placeholder)失败: {e}，尝试方式2"))
            
            # 方式2: 备用定位器 - 通用text input
            try:
                title_input_alt = page.locator('input[type="text"]').first
                if await title_input_alt.count():
                    await title_input_alt.click()
                    await title_input_alt.fill(final_title)
                    bilibili_logger.info(_msg("✅", f"标题已填写 [方式2-通用input]: {final_title}"))
                else:
                    bilibili_logger.error(_msg("❌", "所有标题输入方式均失败"))
            except Exception as e2:
                bilibili_logger.error(_msg("❌", f"方式2也失败: {e2}"))

    async def _fill_description(self, page: Page):
        """填写简介（使用Quill富文本编辑器）"""
        # 方式1: 查找ql-editor（可能为空白或已有内容）
        desc_editor = page.locator('div.ql-editor').first
        try:
            await desc_editor.wait_for(state="visible", timeout=10000)
            # 点击编辑器使其聚焦
            await desc_editor.click()
            await page.wait_for_timeout(500)
            # 填写简介内容
            await desc_editor.fill(self.desc[:2000])  # B站简介最多2000字
            bilibili_logger.info(_msg("✅", f"简介已填写 [方式1-Quill编辑器]: {self.desc[:100]}..."))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"方式1(Quill)失败: {e}，尝试方式2"))
            
            # 方式2: 备用 - 查找textarea或其他编辑器
            try:
                desc_textarea = page.locator('textarea').first
                if await desc_textarea.count():
                    await desc_textarea.click()
                    await desc_textarea.fill(self.desc[:2000])
                    bilibili_logger.info(_msg("✅", f"简介已填写 [方式2-textarea]: {self.desc[:100]}..."))
                else:
                    bilibili_logger.error(_msg("❌", "所有简介填写方式均失败"))
            except Exception as e2:
                bilibili_logger.error(_msg("❌", f"方式2也失败: {e2}"))

    async def _fill_tags(self, page: Page):
        """填写标签（需要按回车键创建标签）"""
        if not self.tags:
            bilibili_logger.info(_msg("ℹ️", "没有标签需要填写"))
            return
        
        # 方式1: 使用 #tag-container 内的 input.input-val（精确定位标签输入框）
        tags_input = page.locator('#tag-container input.input-val').first
        try:
            await tags_input.wait_for(state="visible", timeout=10000)
            bilibili_logger.info(_msg("📝", f"开始填写标签 [tag-container]: {','.join(self.tags)}"))

            # 清空输入框（如果有残留）
            current_value = await tags_input.input_value() or ""
            while current_value:
                await page.keyboard.press("Backspace")
                await page.keyboard.press("Backspace")
                await page.keyboard.press("Backspace")
                await page.wait_for_timeout(200)
                current_value = await tags_input.input_value() or ""
            
            for tag in self.tags:
                # 点击输入框确保聚焦
                await tags_input.click()
                await page.wait_for_timeout(500)
                
                # 输入标签文本（使用type模拟真实键盘输入）
                await tags_input.type(tag, delay=80)  # 每个字符间隔80ms，更稳定
                await page.wait_for_timeout(300)
                
                # 按回车键创建标签
                await page.keyboard.press("Enter")
                bilibili_logger.info(_msg("✅", f"标签已添加 [回车确认]: {tag}"))
                
                # 等待标签创建完成（检查是否成功）
                await page.wait_for_timeout(1000)
            
            bilibili_logger.info(_msg("🎉", f"所有标签已填写完成: {','.join(self.tags)}"))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"方式1(input.val)失败: {e}，尝试方式2"))
            
            # 方式2: 使用placeholder精确定位标签输入框
            try:
                tags_input_alt = page.locator('input[placeholder="按回车键Enter创建标签"]').first
                if await tags_input_alt.count():
                    bilibili_logger.info(_msg("📝", f"开始填写标签 [placeholder定位]"))
                    
                    for tag in self.tags:
                        await tags_input_alt.click()
                        await tags_input_alt.type(tag, delay=50)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(800)
                        bilibili_logger.info(_msg("✅", f"标签已添加 [方式2]: {tag}"))
                    
                    bilibili_logger.info(_msg("🎉", f"所有标签已填写完成 [方式2]"))
                else:
                    bilibili_logger.error(_msg("❌", "所有标签填写方式均失败"))
            except Exception as e2:
                bilibili_logger.error(_msg("❌", f"方式2也失败: {e2}"))

    async def _select_category(self, page: Page, tid: int):
        """选择分区（下拉列表：点击展开 → 选择选项）"""
        # tid到名称映射
        tid_names = {
            21: "动画", 22: "音乐", 47: "游戏", 75: "知识",
            76: "科技", 77: "数码", 83: "生活", 94: "美食",
            95: "动物圈", 96: "鬼畜", 98: "时尚", 160: "资讯",
            161: "娱乐", 162: "影视", 167: "纪录片", 177: "舞蹈",
            202: "VLOG", 211: "搞笑", 213: "评测", 217: "野生厨艺",
            218: "动物", 219: "汽车", 220: "运动", 234: "更多",
        }
        
        target_name = tid_names.get(tid, str(tid))
        bilibili_logger.info(_msg("📁", f"开始选择分区: {target_name}(tid={tid})"))
        
        try:
            # 查找所有可见的下拉框组件
            all_selects = page.locator('div[class*="select"], div.bcc-select, [role="listbox"]')
            select_count = await all_selects.count()
            
            target_found = False
            
            # 遍历每个下拉框查找目标选项
            for i in range(select_count):
                select_elem = all_selects.nth(i)
                if not await select_elem.is_visible():
                    continue
                
                try:
                    # 点击展开下拉框
                    await select_elem.click()
                    await page.wait_for_timeout(800)
                    
                    # 查找目标选项（文本匹配）
                    option = page.get_by_text(target_name).first
                    if await option.count() and await option.is_visible():
                        await option.click()
                        bilibili_logger.info(_msg("✅", f"分区已选择: {target_name}"))
                        target_found = True
                        break
                    
                    # 关闭继续下一个
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(300)
                    
                except Exception as e:
                    bilibili_logger.debug(_msg("📝", f"第{i+1}个失败: {e}"))
                    continue
            
            if not target_found:
                bilibili_logger.warning(_msg("⚠️", f"未找到分区选项: {target_name}(tid={tid})"))
        
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"分区选择失败: {e}"))

    async def _upload_cover(self, page: Page):
        """上传封面（封面设置 → 勾选双比例同步 → 上传图片 → 完成）"""
        bilibili_logger.info(_msg("🖼️", "开始上传封面"))
        
        # 步骤1：点击"封面设置"按钮，打开弹窗
        cover_setting_btn = page.locator('span.edit-text:has-text("封面设置")').first
        try:
            await cover_setting_btn.wait_for(state="visible", timeout=10000)
            await cover_setting_btn.click()
            bilibili_logger.info(_msg("👆", "步骤1✓ 已点击'封面设置'按钮 [span.edit-text]"))
        except Exception as e:
            bilibili_logger.error(_msg("❌", f"步骤1失败: 未找到'封面设置'按钮: {e}"))
            raise RuntimeError("未找到'封面设置'按钮")
        
        # 步骤2：等待弹窗出现
        await page.wait_for_timeout(2000)
        
        # 步骤3：勾选"双比例同步改动"
        sync_checkbox = page.locator('div.sync.ratio_4_3 .bcc-checkbox').first
        try:
            if await sync_checkbox.count():
                class_attr = await sync_checkbox.get_attribute("class")
                if "bcc-checkbox-checked" not in (class_attr or ""):
                    await sync_checkbox.click()
                    bilibili_logger.info(_msg("✅", "步骤3✓ 已勾选'双比例同步改动' [div.sync.ratio_4_3 .bcc-checkbox]"))
                else:
                    bilibili_logger.info(_msg("ℹ️", "步骤3ℹ '双比例同步改动'已勾选，跳过"))
                await page.wait_for_timeout(500)
            else:
                bilibili_logger.warning(_msg("⚠️", f"步骤3警告: 未找到'双比例同步改动'复选框"))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"步骤3警告: '双比例同步改动'勾选失败: {e}"))
        
        # 步骤4：直接使用隐藏的file input上传文件
        cover_input = page.locator('input[type="file"][accept*="image"]').first
        try:
            await cover_input.set_input_files(str(self.cover_path))
            bilibili_logger.info(_msg("✅", "步骤4✓ 封面文件已上传 [input[type=file][accept*=image]]"))
        except Exception as e:
            bilibili_logger.error(_msg("❌", f"步骤4失败: 封面上传失败: {e}"))
            raise RuntimeError(f"封面上传失败: {e}")
        
        # 步骤5：等待上传完成
        await page.wait_for_timeout(3000)
        
        # 步骤6：点击"完成"按钮关闭弹窗
        finish_btn = page.locator('div.button.submit:has-text("完成")').first
        try:
            if await finish_btn.count():
                await finish_btn.wait_for(state="visible", timeout=5000)
                await finish_btn.click()
                bilibili_logger.info(_msg("✅", "步骤6✓ 已点击'完成'按钮 [div.button.submit]"))
            else:
                finish_btn_alt = page.get_by_role("button", name="完成").first
                if await finish_btn_alt.count():
                    await finish_btn_alt.click()
                    bilibili_logger.info(_msg("✅", "步骤6✓ 已点击'完成'按钮 [方式2-role=button]"))
                else:
                    bilibili_logger.warning(_msg("⚠️", "步骤6警告: 未找到'完成'按钮，封面上传已完成但未关闭弹窗"))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"步骤6警告: 点击完成按钮失败: {e}"))

    async def _set_original_declaration(self, page: Page):
        """设置原创声明（下拉列表：点击bcc-select → 选择"内容为自制：未经作者允许禁止转载"）"""
        bilibili_logger.info(_msg("🔒", "开始设置原创声明（禁止转载）"))
        
        try:
            # 查找所有bcc-select下拉框
            all_selects = page.locator('div.bcc-select')
            select_count = await all_selects.count()
            bilibili_logger.info(_msg("🔍", f"页面共找到 {select_count} 个bcc-select下拉框"))
            
            # 遍历每个下拉框查找原创声明选项
            for i in range(select_count):
                select_elem = all_selects.nth(i)
                if not await select_elem.is_visible():
                    continue
                
                try:
                    # 点击展开下拉框
                    await select_elem.click()
                    bilibili_logger.info(_msg("👆", f"已点击第{i+1}个bcc-select下拉框"))
                    await page.wait_for_timeout(800)
                    
                    # 查找"内容为自制：未经作者允许，禁止转载"选项
                    # 该选项在 div.auth-content > span.option-text 中
                    original_option = page.locator('span.option-text:has-text("内容为自制")').first
                    if await original_option.count() and await original_option.is_visible():
                        await original_option.scroll_into_view_if_needed()
                        await page.wait_for_timeout(300)
                        await original_option.click()
                        bilibili_logger.info(_msg("✅", f"原创声明已勾选 [span.option-text]: 内容为自制：未经作者允许，禁止转载"))
                        return
                    
                    # 备用：通过完整文本查找
                    alt_texts = ["内容为自制：未经作者允许，禁止转载", "内容为自制", "自制"]
                    for text in alt_texts:
                        option = page.get_by_text(text).first
                        if await option.count() and await option.is_visible():
                            class_attr = await option.get_attribute("class") or ""
                            if "option-text" in class_attr or "auth-content" in class_attr or "selected" in class_attr:
                                await option.click()
                                bilibili_logger.info(_msg("✅", f"原创声明已勾选 [文本]: {text}"))
                                return
                    
                    # 没找到目标选项，关闭继续下一个
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(300)
                    
                except Exception as e:
                    bilibili_logger.warning(_msg("⚠️", f"第{i+1}个下拉框操作失败: {e}"))
                    continue
            
            bilibili_logger.warning(_msg("⚠️", "未找到'内容为自制'声明选项"))
                    
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"原创声明设置失败: {e}"))

    async def _set_ai_declaration(self, page: Page):
        """设置AI创作声明（下拉列表：点击bcc-select → 选择"含AI生成内容"）"""
        bilibili_logger.info(_msg("🤖", "开始设置AI创作声明"))
        
        try:
            # 查找所有bcc-select下拉框
            all_selects = page.locator('div.bcc-select')
            select_count = await all_selects.count()
            bilibili_logger.info(_msg("🔍", f"页面共找到 {select_count} 个bcc-select下拉框"))
            
            # 遍历每个下拉框
            target_found = False
            for i in range(select_count):
                select_elem = all_selects.nth(i)
                if not await select_elem.is_visible():
                    continue
                
                try:
                    # 点击展开下拉框
                    await select_elem.click()
                    bilibili_logger.info(_msg("👆", f"已点击第{i+1}个bcc-select下拉框"))
                    
                    # 等待下拉列表完全展开
                    await page.wait_for_timeout(2000)
                    
                    # 直接点击第2个选项（含AI生成内容，固定位置）
                    ai_option = page.locator('li.bcc-option').nth(1)
                    
                    # 检查是否已选中
                    class_attr = (await ai_option.get_attribute("class") or "")
                    is_selected = "selected" in class_attr
                    
                    if is_selected:
                        bilibili_logger.info(_msg("✅", f"'含AI生成内容'已选中，无需操作"))
                        target_found = True
                        break
                    else:
                        # 未选中，使用JS点击（绕过可见性限制）
                        bilibili_logger.info(_msg("👆", "准备点击'含AI生成内容'选项2"))
                        
                        # 方式1: 标准click
                        try:
                            await ai_option.click(timeout=2000)
                            bilibili_logger.info(_msg("✅", "AI声明已勾选 [标准click]"))
                            target_found = True
                            break
                        except:
                            pass
                        
                        # 方式2: evaluate JS原生click
                        result = await page.evaluate("""() => {
                            const options = document.querySelectorAll('li.bcc-option');
                            const span = options[1].querySelector('span');
                            if (span && span.textContent.includes('含AI生成内容')) {
                                span.click();
                                return true;
                            }
                            return false;
                        }""")
                        if result:
                            bilibili_logger.info(_msg("✅", "AI声明已勾选 [JS click]"))
                            target_found = True
                            break
                    
                    bilibili_logger.warning(_msg("⚠️", f"第{i+1}个下拉框未找到目标，继续下一个"))
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)
                    
                except Exception as e:
                    bilibili_logger.warning(_msg("⚠️", f"第{i+1}个下拉框操作失败: {e}"))
                    continue
            
            if not target_found:
                bilibili_logger.warning(_msg("⚠️", "未找到'含AI生成内容'声明选项"))
        
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"AI创作声明设置失败: {e}"))

    async def _set_schedule_time(self, page: Page, publish_date: datetime):
        """设置定时发布"""
        # 点击定时发布选项
        schedule_radio = page.locator('input[type="radio"][value="scheduled"]').first
        await schedule_radio.click()

        # 设置发布时间
        time_input = page.locator('input[type="datetime-local"]').first
        await time_input.fill(publish_date.strftime("%Y-%m-%dT%H:%M"))

        bilibili_logger.info(_msg("⏰", f"设置定时发布: {publish_date}"))

    async def _submit_video(self, page: Page):
        """提交视频"""
        bilibili_logger.info(_msg("🚀", "小人正在点击发布按钮"))
        
        # 点击"立即投稿"按钮（B站发布页面的最终提交按钮）
        submit_selectors = [
            'span.submit-add:has-text("立即投稿")',  # B站实际HTML：span元素
            'button:has-text("立即投稿")',            # 备用button形式
            'div:has-text("立即投稿")',               # 备用div形式
        ]
        
        submit_button = None
        for selector in submit_selectors:
            btn = page.locator(selector).first
            if await btn.count():
                submit_button = btn
                bilibili_logger.info(_msg("🔍", f"找到提交按钮 [{selector}]"))
                break
        
        if not submit_button:
            raise RuntimeError("未找到'立即投稿/提交'按钮")
        
        await submit_button.wait_for(state="visible", timeout=10000)
        await submit_button.click()
        bilibili_logger.info(_msg("🚀", "已点击'立即投稿'按钮"))

        # 等待提交成功（检查多种成功标志）
        max_wait_time = 15  # 最大等待15秒
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < max_wait_time:
            try:
                # 检查URL是否跳转到稿件管理页面
                current_url = page.url
                if "member.bilibili.com/platform/home" in current_url or \
                   "member.bilibili.com/platform/upload/video/frame" in current_url and "submit" not in current_url:
                    bilibili_logger.success(_msg("🎉", "视频提交成功（页面已跳转）"))
                    return
                
                # 检查成功提示文本
                success_texts = ["提交成功", "发布成功", "稿件发布成功", "投稿成功"]
                for text in success_texts:
                    if await page.get_by_text(text).count():
                        bilibili_logger.success(_msg("🎉", f"视频{text}"))
                        await page.wait_for_timeout(5000)
                        return
                
                # 检查按钮是否消失（说明已经提交）
                if not await submit_button.count():
                    # 等待一下再检查成功标志
                    await page.wait_for_timeout(2000)
                    current_url = page.url
                    if "member.bilibili.com/platform/home" in current_url or \
                       "upload/video/frame" in current_url and "submit" not in current_url:
                        bilibili_logger.success(_msg("�", "视频提交成功（按钮已消失）"))
                        await page.wait_for_timeout(5000)
                        return
                
                await asyncio.sleep(1)
                
            except Exception as e:
                bilibili_logger.info(_msg("🏃", f"检查发布状态时出现异常: {e}"))
                await asyncio.sleep(1)
        
        # 如果等待超时，截图并抛出异常
        if self.debug and self.screenshot_manager:
            await self.screenshot_manager.take_screenshot(page, "发布超时")
        
        raise RuntimeError("视频提交失败：等待超时，未检测到成功标志")
