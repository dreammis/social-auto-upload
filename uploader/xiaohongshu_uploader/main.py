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
from utils.log import xiaohongshu_logger
from utils.runtime_config import get_local_chrome_headless

XHS_LOGIN_URL = "https://creator.xiaohongshu.com/login"
XHS_PUBLISH_VIDEO_URL = "https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video"
XHS_PUBLISH_NOTE_URL = "https://creator.xiaohongshu.com/publish/publish?from=homepage&target=image"
XHS_PUBLISH_SUCCESS_URL_PATTERN = "**/publish/success?**"
XHS_LOGIN_BOX_SELECTOR = "div[class*='login-box']"
XHS_LOGIN_SWITCH_SELECTOR = "img.css-wemwzq"
XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


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


async def _open_xhs_qrcode_panel(page: Page) -> None:
    login_box = page.locator(XHS_LOGIN_BOX_SELECTOR).first
    await login_box.wait_for(state="visible", timeout=30000)

    scan_text = login_box.locator("div:has-text('扫一扫')").first
    if await scan_text.count():
        return

    switch_img = login_box.locator(XHS_LOGIN_SWITCH_SELECTOR).first
    await switch_img.wait_for(state="visible", timeout=10000)
    await switch_img.click()
    await login_box.locator("div:has-text('扫一扫')").first.wait_for(state="visible", timeout=10000)


async def _find_xhs_qrcode_locator(page: Page):
    await _open_xhs_qrcode_panel(page)

    qrcode_img = page.locator('.login-box-container').get_by_text("APP扫一扫登录").filter(visible=True).locator("xpath=..//following-sibling::div//img").nth(0)

    if await qrcode_img.count():
        return qrcode_img

    raise RuntimeError("未在扫一扫登录区域找到小红书二维码图片")


async def _extract_xhs_qrcode_src(page: Page) -> str:
    qrcode_img = await _find_xhs_qrcode_locator(page)
    await qrcode_img.wait_for(state="visible", timeout=30000)
    qrcode_src = await qrcode_img.get_attribute("src")
    if not qrcode_src:
        raise RuntimeError("未获取到小红书登录二维码地址")
    return qrcode_src


async def _save_xhs_qrcode(
    page: Page,
    account_file: str,
    previous_qrcode_path: Path | None = None,
    qrcode_callback=None,
) -> dict:
    qrcode_src = await _extract_xhs_qrcode_src(page)
    qrcode_path = build_login_qrcode_path(account_file, suffix="xhs_login_qrcode")
    qrcode_img = await _find_xhs_qrcode_locator(page)

    if qrcode_src.startswith("data:image/"):
        save_data_url_image(qrcode_src, qrcode_path)
    else:
        qrcode_path.parent.mkdir(parents=True, exist_ok=True)
        await qrcode_img.screenshot(path=str(qrcode_path))

    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            xiaohongshu_logger.info(_msg("🧹", f"临时二维码文件已清理: {previous_qrcode_path}"))

    xiaohongshu_logger.info(_msg("🖼️", f"二维码已经准备好啦，已保存到: {qrcode_path}"))
    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, "小红书APP")
    else:
        xiaohongshu_logger.warning(_msg("😵", f"终端没法完整显示二维码，请打开 {qrcode_path} 扫码"))

    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_xhs_login_completed(page: Page) -> bool:
    if page.url.startswith(XHS_LOGIN_URL):
        return False

    login_box = page.locator(XHS_LOGIN_BOX_SELECTOR).first
    if not await login_box.count():
        return True

    try:
        return not await login_box.is_visible()
    except Exception:
        return True


async def cookie_auth(account_file):
    if not os.path.exists(account_file):
        return False

    async with async_playwright() as playwright:
        if LOCAL_CHROME_PATH:
            browser = await playwright.chromium.launch(
                headless=get_local_chrome_headless(),
                executable_path=LOCAL_CHROME_PATH,
            )
        else:
            browser = await playwright.chromium.launch(
                headless=get_local_chrome_headless(),
                channel="chrome",
            )
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(XHS_PUBLISH_VIDEO_URL)
            await page.wait_for_timeout(3000)

            if page.url.startswith(XHS_LOGIN_URL):
                xiaohongshu_logger.info(_msg("🥹", "cookie 已失效，得重新登录一下"))
                return False

            login_box = page.locator(XHS_LOGIN_BOX_SELECTOR).first
            if await login_box.count():
                try:
                    if await login_box.is_visible():
                        xiaohongshu_logger.info(_msg("🥹", "页面仍然停留在登录二维码页，按 cookie 失效处理"))
                        return False
                except Exception:
                    return False

            xiaohongshu_logger.success(_msg("🥳", "cookie 有效"))
            return True
        except Exception as exc:
            xiaohongshu_logger.warning(_msg("😵", f"cookie 校验时出错，按失效处理: {exc}"))
            return False
        finally:
            await browser.close()


async def xiaohongshu_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool | None = None,
):
    if headless is None:
        headless = get_local_chrome_headless()
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False
        xiaohongshu_logger.info(_msg("🥹", "cookie 失效了，准备打开浏览器重新登录"))
        result = await xiaohongshu_cookie_gen(
            account_file,
            qrcode_callback=qrcode_callback,
            headless=headless,
        )
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def xiaohongshu_cookie_gen(
    account_file,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
    headless: bool | None = None,
):
    if headless is None:
        headless = get_local_chrome_headless()
    if headless:
        xiaohongshu_logger.info(_msg("🖼️", "小红书登录将以无头模式运行，小人会输出终端二维码并保存本地二维码图片"))

    account_path = Path(account_file)
    account_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless, channel="chrome")
        context = await browser.new_context()
        context = await set_init_script(context)
        qrcode_path = None
        qrcode_info = None
        result = _build_login_result(False, "failed", "小红书登录失败", account_file)
        try:
            page = await context.new_page()
            await page.goto(XHS_LOGIN_URL)
            qrcode_info = await _save_xhs_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])
            xiaohongshu_logger.info(_msg("🧍", "请扫码，小人正在耐心等待登录完成"))

            for _ in range(max_checks):
                if await _is_xhs_login_completed(page):
                    await asyncio.sleep(2)
                    await context.storage_state(path=account_file)
                    if await cookie_auth(account_file):
                        xiaohongshu_logger.success(_msg("🥳", "小红书扫码登录成功，小人开心收工"))
                        result = _build_login_result(True, "success", "小红书扫码登录成功", account_file, qrcode_info, page.url)
                    else:
                        result = _build_login_result(
                            False,
                            "cookie_invalid",
                            "小红书扫码流程结束，但 cookie 校验失败",
                            account_file,
                            qrcode_info,
                            page.url,
                        )
                    return result

                await asyncio.sleep(poll_interval)

            result = _build_login_result(
                False,
                "timeout",
                "等待小红书扫码登录超时",
                account_file,
                qrcode_info,
                page.url,
            )
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                xiaohongshu_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                xiaohongshu_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()
        return result


class XiaoHongShuBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool | None = None,
    ):
        self.publish_date = publish_date
        self.account_file = str(account_file)
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.date_format = "%Y年%m月%d日 %H:%M"
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = get_local_chrome_headless() if headless is None else headless

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成小红书登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成小红书登录: {self.account_file}")

        if self.publish_strategy not in {
            XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
            XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
        }:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def set_schedule_time_xiaohongshu(self, page: Page, publish_date: datetime):
        xiaohongshu_logger.info(_msg("🕒", f"小人准备设置定时发布时间: {publish_date.strftime(self.date_format)}"))
        await page.locator('.custom-switch-card').filter(has_text="定时发布").locator('.d-switch').click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")
        time_input = page.locator('.d-datepicker-input-filter input.d-text')
        await time_input.fill(str(publish_date_hour))
        await asyncio.sleep(1)

    async def set_location(self, page: Page, location: str = "青岛市"):
        if not location:
            return True

        xiaohongshu_logger.info(_msg("📍", f"小人准备设置位置: {location}"))
        loc_ele = await page.wait_for_selector('div.d-text.d-select-placeholder.d-text-ellipsis.d-text-nowrap')
        await loc_ele.click()
        await page.wait_for_timeout(1000)
        await page.keyboard.type(location)
        dropdown_selector = 'div.d-popover.d-popover-default.d-dropdown.--size-min-width-large'
        await page.wait_for_timeout(2000)
        try:
            await page.wait_for_selector(dropdown_selector, timeout=3000)
        except Exception:
            xiaohongshu_logger.warning(_msg("😵", "位置下拉列表没按预期出现，小人继续按旧逻辑查找"))
        await page.wait_for_timeout(1000)
        flexible_xpath = (
            f'//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
            f'//div[contains(@class, "d-options-wrapper")]'
            f'//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
            f'//div[contains(@class, "name") and text()="{location}"]'
        )
        await page.wait_for_timeout(3000)
        try:
            location_option = await page.wait_for_selector(
                flexible_xpath,
                timeout=3000
            )

            if not location_option:
                location_option = await page.wait_for_selector(
                    f'//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
                    f'//div[contains(@class, "d-options-wrapper")]'
                    f'//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
                    f'/div[1]//div[contains(@class, "name") and text()="{location}"]',
                    timeout=2000
                )

            await location_option.scroll_into_view_if_needed()
            await location_option.click()
            xiaohongshu_logger.success(_msg("🥳", f"位置已经设置成 {location}"))
            return True
        except Exception as e:
            xiaohongshu_logger.error(_msg("😢", f"设置位置失败: {e}"))
            try:
                all_options = await page.query_selector_all(
                    '//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
                    '//div[contains(@class, "d-options-wrapper")]'
                    '//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
                    '/div'
                )
                xiaohongshu_logger.debug(_msg("🧍", f"位置下拉里一共找到 {len(all_options)} 个选项"))
                for i, option in enumerate(all_options[:3]):
                    option_text = await option.inner_text()
                    xiaohongshu_logger.debug(_msg("🧾", f"候选位置 {i + 1}: {option_text.strip()[:50]}"))
            except Exception as inner_e:
                xiaohongshu_logger.debug(_msg("😵", f"读取位置候选列表失败: {inner_e}"))
            return False

    async def fill_title(self, page: Page) -> None:
        title_container = page.locator('input[placeholder*="填写标题"]')
        await title_container.fill(self.title[:20])

    async def fill_desc(self, page: Page) -> None:
        if not getattr(self, "desc", ""):
            return

        xiaohongshu_logger.info(_msg("✍️", f"小人正在填写描述: {self.desc[:50]}..."))

        # 定位描述框：用 contenteditable 的 div（Tiptap 编辑器）
        desc_box = page.locator('div.tiptap[contenteditable="true"]')
        if await desc_box.count() == 0:
            desc_box = page.locator('div[contenteditable="true"][role="textbox"]')
        if await desc_box.count() == 0:
            # 降级方案：使用旧的定位方式
            desc_box = page.locator('p[data-placeholder*="输入正文描述"]')

        if await desc_box.count() == 0:
            xiaohongshu_logger.warning(_msg("⚠️", "未找到描述输入框，跳过"))
            return

        # 先点击聚焦
        await desc_box.click()
        await asyncio.sleep(0.3)

        # 尝试使用 evaluate 直接设置内容（适用于 contenteditable 的 div）
        try:
            desc_text = self.desc
            await page.evaluate(
                """([selector, text]) => {
                    const el = document.querySelector(selector);
                    if (el) {
                        el.innerText = text;
                        el.focus();
                        // 触发 input 事件让编辑器感知到内容变化
                        const event = new Event('input', { bubbles: true });
                        el.dispatchEvent(event);
                    }
                }""",
                ['div.tiptap[contenteditable="true"], div[contenteditable="true"][role="textbox"], p[data-placeholder*="输入正文描述"]', desc_text]
            )
            xiaohongshu_logger.success(_msg("✅", f"描述已填写完成: {desc_text[:30]}..."))
        except Exception as e:
            # 降级方案：使用键盘输入
            xiaohongshu_logger.warning(_msg("⚠️", f"evaluate方式失败，使用键盘输入: {e}"))
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(self.desc)
            await page.keyboard.press("Enter")
            xiaohongshu_logger.success(_msg("✅", f"描述已填写完成（键盘方式）"))

    async def fill_tags(self, page: Page) -> None:
        if not getattr(self, "tags", None):
            return

        # 小红书标签上限为 10 个，超过会导致死循环卡住发布
        max_tags = 10
        if len(self.tags) > max_tags:
            xiaohongshu_logger.warning(
                _msg("🏷️", f"标签数量 {len(self.tags)} 超过小红书上限 {max_tags}，只取前 {max_tags} 个: {self.tags[:max_tags]}")
            )
            self.tags = self.tags[:max_tags]

        if not getattr(self, "desc", ""):
            desc = page.locator('p[data-placeholder*="输入正文描述"]')
            await desc.click()

        for tag in self.tags:  # 循环处理所有 tags
            # 话题候选下拉框依赖小红书联想接口实时返回，网络抖动/无匹配时会等不到。
            # 标签是可选增强项：等不到候选框就跳过该标签继续，不让整条发布因此失败。
            try:
                await page.keyboard.type("#" + tag, delay=30)
                await page.locator('#creator-editor-topic-container').wait_for(
                    state="visible",
                    timeout=6000
                )
                first_item = page.locator('#creator-editor-topic-container .item').first
                await first_item.wait_for(state="visible", timeout=4000)
                await first_item.click()
            except Exception as exc:
                xiaohongshu_logger.warning(
                    _msg("🏷️", f"话题『{tag}』未出现候选，跳过该标签继续发布: {exc}")
                )
                # 清掉已键入但未成词的 "#tag" 文本，避免它残留进正文
                for _ in range(len("#" + tag)):
                    await page.keyboard.press("Backspace")
                continue

    async def fill_meta(self, page: Page) -> None:
        await self.fill_title(page)
        await self.fill_desc(page)
        await self.fill_tags(page)

    async def set_original_declaration(self, page: Page) -> None:
        """开启原创声明开关

        根据category参数决定是否声明原创：
        - category为None或0: 不声明原创
        - category为其他值: 声明原创

        HTML结构: div.custom-switch-wrapper 包含"原创声明"文字和 d-switch 开关
        """
        # 检查是否需要声明原创
        if not self.category:
            xiaohongshu_logger.info(_msg("🧾", "未勾选声明原创，跳过"))
            return

        try:
            xiaohongshu_logger.info(_msg("🛡️", "小人正在开启原创声明"))
            # 定位原创声明区域的 switch 开关
            original_switch = page.locator('div.custom-switch-wrapper').filter(has_text="原创声明").locator('span.d-switch-simulator').first
            if not await original_switch.count():
                xiaohongshu_logger.warning(_msg("⚠️", "未找到原创声明开关，跳过"))
                return

            # 检查开关是否可用
            is_disabled = await original_switch.evaluate('el => el.classList.contains("disabled") || el.closest(".d-switch-disabled") !== null')
            if is_disabled:
                xiaohongshu_logger.warning(_msg("⚠️", "原创声明开关当前处于禁用状态（可能视频尚未上传完成），跳过"))
                return

            # 检查是否已经开启
            is_checked = await original_switch.evaluate('el => el.classList.contains("checked")')
            if is_checked:
                xiaohongshu_logger.info(_msg("ℹ️", "原创声明已经处于开启状态"))
            else:
                await original_switch.click()
                xiaohongshu_logger.success(_msg("✅", "已开启原创声明"))

            # 处理原创声明弹窗：勾选同意条款并点击声明原创按钮
            try:
                await page.locator('div.d-modal:visible').wait_for(state="visible", timeout=3000)
                xiaohongshu_logger.info(_msg("📝", "小人正在勾选原创声明须知"))
                checkbox = page.locator('div.d-modal:visible input[type="checkbox"], div.d-modal:visible span.d-checkbox-simulator').first
                if await checkbox.count():
                    await checkbox.click()
                # 点击"声明原创"按钮
                confirm_btn = page.locator('button:has-text("声明原创")')
                if await confirm_btn.count():
                    await confirm_btn.click()
                    xiaohongshu_logger.success(_msg("✅", "已确认声明原创"))
                else:
                    xiaohongshu_logger.warning(_msg("⚠️", "未找到声明原创确认按钮"))
            except Exception:
                # 没有弹窗，说明不需要确认
                pass

        except Exception as exc:
            xiaohongshu_logger.warning(_msg("⚠️", f"勾选原创声明时出错，跳过: {exc}"))

    async def set_declaration(self, page: Page) -> None:
        """设置小红书声明（如"笔记含AI合成内容"等下拉列表声明）

        通过 declaration_info 参数控制：
        - declaration_info 为 None 或无 declaration_type: 不设置声明
        - declaration_type 如 "笔记含AI合成内容": 在下拉列表中选择对应选项

        定位方式参考：用 div.d-select-wrapper + filter(has_text="添加内容类型声明") 定位下拉框
        用 page.get_by_text(exact=True) 精确匹配选项
        """
        declaration_info = getattr(self, 'declaration_info', None)
        declaration_type = declaration_info.get("declaration_type") if declaration_info else None

        if not declaration_type:
            xiaohongshu_logger.debug(_msg("📝", "未指定声明类型，跳过声明设置"))
            return

        try:
            xiaohongshu_logger.info(_msg("🤖", f"小人正在设置声明: {declaration_type}"))

            # 定位下拉框：用 filter(has_text) 匹配"添加内容类型声明"
            dropdown = page.locator('div.d-select-wrapper').filter(has_text="添加内容类型声明")
            if await dropdown.count() == 0:
                dropdown = page.locator('div.d-select-main').filter(has_text="添加内容类型声明")
            if await dropdown.count() == 0:
                xiaohongshu_logger.warning(_msg("📝", "未找到声明下拉框，跳过声明设置"))
                return

            await dropdown.click()
            xiaohongshu_logger.debug(_msg("📝", "已点击声明下拉框，等待选项出现"))

            # 等待弹出层出现后，用文本精确匹配选项
            try:
                option = page.get_by_text(declaration_type, exact=True).first
                await option.wait_for(state="visible", timeout=3000)
                await option.click()
                xiaohongshu_logger.success(_msg("✅", f"声明已设置为: {declaration_type}"))
                await asyncio.sleep(0.3)
            except Exception:
                xiaohongshu_logger.warning(_msg("📝", f"未找到声明选项「{declaration_type}」"))
                await page.keyboard.press("Escape")

        except Exception as exc:
            xiaohongshu_logger.warning(_msg("⚠️", f"设置声明时出错，跳过: {exc}"))

    async def set_collection(self, page: Page, collection_name: str) -> None:
        """小红书「合集」选择：点击合集按钮 → 展开下拉列表 → 模糊匹配选择包含关键字的选项。

        Args:
            page: Playwright页面对象
            collection_name: 合集名称关键字（如"大学篇"），会模糊匹配包含该文字的选项
        """
        if not collection_name:
            xiaohongshu_logger.debug(_msg("📚", "未指定合集名称，跳过合集选择"))
            return

        try:
            # 定位合集插件容器
            collection_wrapper = page.locator('.collection-plugin-wrapper').first
            if not await collection_wrapper.count():
                xiaohongshu_logger.warning(_msg("📚", "未找到合集插件容器，跳过合集选择"))
                return

            # 等待合集容器可见
            await collection_wrapper.wait_for(state="visible", timeout=6000)

            # 点击合集选择按钮（.collection-plugin-button）来展开下拉列表
            collection_button = collection_wrapper.locator('.collection-plugin-button').first
            if not await collection_button.count():
                # 备用：尝试旧选择器
                collection_button = collection_wrapper.locator('.collection-plugin-choose').first

            if not await collection_button.count():
                xiaohongshu_logger.warning(_msg("📚", "未找到合集选择按钮，跳过合集选择"))
                return

            await collection_button.click()
            xiaohongshu_logger.debug(_msg("📚", "已点击合集选择按钮，等待下拉列表出现"))

            # 等待下拉列表出现
            await asyncio.sleep(1)

            # 小红书合集下拉列表通常是 d-popover 或 d-select-dropdown
            # 尝试多种选择器定位下拉选项
            option_found = False

            # 方案1：通过 d-select-dropdown 查找选项
            dropdown_selectors = [
                '.d-select-dropdown:visible',
                '.d-popover:visible',
                'div[role="listbox"]:visible',
            ]

            for selector in dropdown_selectors:
                dropdown = page.locator(selector).first
                if not await dropdown.count():
                    continue

                # 在下拉菜单中查找包含关键字的选项
                items = dropdown.locator('.d-select-option, [role="option"], li, .collection-item')
                item_count = await items.count()

                for i in range(item_count):
                    item = items.nth(i)
                    try:
                        item_text = await item.text_content()
                        if item_text and collection_name in item_text:
                            await item.click()
                            xiaohongshu_logger.info(_msg("📚", f"已选择合集：{item_text.strip()}"))
                            option_found = True
                            break
                    except Exception:
                        continue

                if option_found:
                    break

            # 方案2：通过文本内容直接定位
            if not option_found:
                xiaohongshu_logger.debug(_msg("📚", "尝试通过可见文本定位合集选项"))
                try:
                    text_option = page.get_by_text(collection_name, exact=False).first
                    if await text_option.count() and await text_option.is_visible():
                        await text_option.click()
                        xiaohongshu_logger.info(_msg("📚", f"已选择合集（文本匹配）"))
                        option_found = True
                except Exception:
                    pass

            if not option_found:
                xiaohongshu_logger.warning(_msg("📚", f"未找到包含「{collection_name}」的合集选项，关闭下拉菜单"))
                await page.keyboard.press("Escape")

        except Exception as exc:
            xiaohongshu_logger.warning(_msg("📚", f"合集设置失败，跳过该步骤继续发布：{exc}"))


class XiaoHongShuVideo(XiaoHongShuBaseUploader):
    upload_page = "https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video"

    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        thumbnail_path=None,
        desc: str | None = None,
        category=None,
        publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool | None = None,
        collection: str | None = None,  # 合集名称
        declaration_info: dict | None = None,  # 声明信息（如AI合成内容声明）
        screenshot_manager: ScreenshotManager | None = None,  # 截图管理器（无头模式调试）
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
        self.thumbnail_path = thumbnail_path
        self.desc = desc or ""
        self.category = category
        self.collection = collection  # 合集名称
        self.declaration_info = declaration_info
        self.screenshot_manager = screenshot_manager  # 截图管理器

    async def _take_screenshot(self, page: Page, step_name: str, full_page: bool = False) -> None:
        """辅助方法：在关键步骤截图"""
        if self.screenshot_manager:
            await self.screenshot_manager.take_screenshot(page, step_name, full_page)

    async def _take_error_screenshot(self, page: Page, error_msg: str = None) -> None:
        """辅助方法：错误时截图"""
        if self.screenshot_manager:
            await self.screenshot_manager.take_error_screenshot(page, error_msg)

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("视频模式下，title 是必须的")

        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_path:
            self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def handle_upload_error(self, page: Page):
        xiaohongshu_logger.warning(_msg("😵", "视频上传摔了一跤，小人马上重新上传"))
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        if not thumbnail_path:
            return

        xiaohongshu_logger.info(_msg("🖼️", "小人准备设置封面"))

        # 点击封面预览元素
        try:
            cover_preview = page.locator('div.default.column[style*="background-image"]').first
            await cover_preview.wait_for(state="visible", timeout=5000)
            await cover_preview.click(force=True)
            xiaohongshu_logger.success(_msg("✅", "已点击封面修改"))
        except Exception as e:
            xiaohongshu_logger.error(_msg("❌", f"未找到封面预览元素，尝试备用方案: {e}"))
            # 备用方案：使用旧的定位方式
            try:
                cover_plugin_title = page.locator("div.cover-plugin-title").filter(has_text="设置封面")
                cover_upload_dialog = cover_plugin_title.locator(
                    "xpath=ancestor::div[contains(@class, 'cover-plugin-preview')]"
                ).locator("div.cover > div.default:visible")
                await cover_upload_dialog.wait_for(state="visible", timeout=30000)
                await cover_upload_dialog.click(force=True)
                xiaohongshu_logger.success(_msg("✅", "已点击封面上传对话框（备用方案）"))
            except Exception as e2:
                xiaohongshu_logger.error(_msg("❌", f"备用方案也失败: {e2}"))
                return

        # 等待封面上传弹窗出现
        modal = page.locator("div.d-modal.cover-modal")
        await modal.wait_for(state="visible", timeout=30000)
        xiaohongshu_logger.info(_msg("✅", "封面编辑弹窗已打开"))

        # 点击"上传图片"按钮
        try:
            # 等待一下让弹窗内容加载完成
            await page.wait_for_timeout(1000)
            
            upload_btn = modal.locator('div.upload-btn').first
            await upload_btn.wait_for(state="visible", timeout=5000)
            await upload_btn.click()
            xiaohongshu_logger.success(_msg("✅", "已点击上传图片按钮"))
        except Exception as e:
            xiaohongshu_logger.warning(_msg("⚠️", f"点击上传图片按钮失败，尝试直接上传: {e}"))

        await page.wait_for_timeout(500)

        # 上传封面图片
        file_input = modal.locator('input[type="file"][accept*="image"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(thumbnail_path)
        await page.wait_for_timeout(2000)
        xiaohongshu_logger.info(_msg("📤", "封面图片已上传"))

        # 点击确定按钮
        confirm_button = modal.locator("button.mojito-button").filter(has_text="确定").first
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()
        xiaohongshu_logger.info(_msg("✅", "已点击确定按钮"))

        await modal.wait_for(state="hidden", timeout=30000)
        xiaohongshu_logger.success(_msg("🥳", "封面已经设置完成"))

    async def upload_video_content(self, page: Page) -> None:
        xiaohongshu_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}.mp4"))
        xiaohongshu_logger.info(_msg("🧭", "小人正在赶往视频发布页"))
        await page.goto(XHS_PUBLISH_VIDEO_URL)
        await page.wait_for_url(XHS_PUBLISH_VIDEO_URL)

        xiaohongshu_logger.info(_msg("📤", "小人正在上传视频文件"))
        await page.locator("div[class^='upload-content'] input[class='upload-input']").set_input_files(self.file_path)

        while True:
            try:
                upload_input = await page.wait_for_selector('input.upload-input', timeout=3000)
                preview_new = await upload_input.query_selector(
                    'xpath=following-sibling::div[contains(@class, "preview-new")]')
                if preview_new:
                    # 获取整个预览区域的文本，更鲁棒地判断上传状态
                    all_text = await preview_new.inner_text()
                    upload_success = any(keyword in all_text for keyword in ['上传成功', '分辨率', '重新上传', '编辑封面', '已上传', '已选择', '100%'])

                    if not upload_success:
                        # 检查是否有特定的状态码或百分比
                        stage_elements = await preview_new.query_selector_all('div.stage')
                        for stage in stage_elements:
                            text_content = await page.evaluate('(element) => element.textContent', stage)
                            if '上传成功' in text_content or '分辨率' in text_content:
                                upload_success = True
                                break

                    if upload_success:
                        xiaohongshu_logger.success(_msg("🥳", "视频已经传完啦"))
                        break

                    if self.debug:
                        normalized_text = all_text.strip().replace("\n", " ")
                        xiaohongshu_logger.debug(_msg("🧍", f"预览区域内容: {normalized_text}"))
                    xiaohongshu_logger.debug(_msg("🧍", "还没看到上传成功标识，小人继续等一会"))
                else:
                    # 尝试检查标题输入框是否已经出现，如果是，说明已经进入编辑状态
                    title_container = page.locator('input[placeholder*="填写标题"]')
                    if await title_container.count() > 0 and await title_container.is_visible():
                        xiaohongshu_logger.success(_msg("🥳", "虽然没看到预览区，但标题框出来了，小人继续"))
                        break
                    xiaohongshu_logger.debug(_msg("🧍", "还没拿到预览区域，小人继续等一会"))
            except Exception as e:
                xiaohongshu_logger.debug(_msg("😵", f"上传状态还没稳定下来，小人继续观察: {e}"))
            await asyncio.sleep(2)

        xiaohongshu_logger.info(_msg("✍️", "小人开始填标题、描述和话题"))
        await self.fill_meta(page)

        xiaohongshu_logger.info(_msg("🖼️", "小人准备设置封面"))
        await self.set_thumbnail(page, self.thumbnail_path)

        # await self.set_location(page, "青岛市")

        xiaohongshu_logger.info(_msg("🧾", "小人正在设置原创声明"))
        await self.set_original_declaration(page)

        # 设置声明（如AI合成内容声明）
        xiaohongshu_logger.info(_msg("📝", "小人正在设置声明类型"))
        await self.set_declaration(page)

        # 设置合集
        if self.collection:
            xiaohongshu_logger.info(_msg("📚", f"小人正在设置合集：{self.collection}"))
            await asyncio.sleep(1)  # 等待页面渲染合集插件
            await self.set_collection(page, self.collection)
            xiaohongshu_logger.info(_msg("🥳", "合集设置完成"))

        if self.publish_strategy == XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            xiaohongshu_logger.info(_msg("⏰", "小人正在设置定时发布"))
            await self.set_schedule_time_xiaohongshu(page, self.publish_date)

        xiaohongshu_logger.info(_msg("🚀", "小人正在点击发布按钮"))
        max_retries = 3  # 最大重试次数
        retry_count = 0
        while retry_count < max_retries:
            try:
                if self.publish_strategy == XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED:
                    await page.locator('button:has-text("定时发布")').click()
                else:
                    await page.locator('button:has-text("发布")').click()
                await page.wait_for_url(
                    "https://creator.xiaohongshu.com/publish/success?**",
                    timeout=3000
                )
                xiaohongshu_logger.success(_msg("🥳", "视频发布成功，小人开心收工"))
                break
            except Exception as e:
                retry_count += 1
                xiaohongshu_logger.info(_msg("🏃", f"小人正在冲刺发布视频，重试 {retry_count}/{max_retries}: {e}"))
                # 只在最后一次失败时截图
                if retry_count == max_retries and self.debug and self.screenshot_manager:
                    await self.screenshot_manager.take_screenshot(page, f"发布失败_重试{retry_count}次")
                await asyncio.sleep(0.5)
        
        # 如果重试3次都失败，抛出异常
        if retry_count >= max_retries:
            raise Exception(f"发布失败：已重试{max_retries}次仍未成功")

    async def upload(self, playwright: Playwright) -> None:
        xiaohongshu_logger.info(_msg("🧍", "小人先检查 cookie、视频文件、封面和发布时间"))
        await self.validate_upload_args()
        xiaohongshu_logger.info(_msg("🥳", "上传前检查通过"))
        browser = await playwright.chromium.launch(headless=self.headless, channel="chrome")
        context = await browser.new_context(
            permissions=["geolocation"],
            storage_state=self.account_file,
        )
        context = await set_init_script(context)
        page = None

        try:
            page = await context.new_page()
            await self.upload_video_content(page)
            await context.storage_state(path=self.account_file)
            xiaohongshu_logger.success(_msg("🥳", "cookie 更新完毕"))
        except Exception as e:
            xiaohongshu_logger.error(_msg("❌", f"上传过程中发生错误: {e}"))
            # 只在非发布失败的情况下截图（发布失败已在重试循环中截图）
            if page and self.screenshot_manager and not str(e).startswith("发布失败"):
                await self._take_error_screenshot(page, str(e))
            raise
        finally:
            await context.close()
            await browser.close()

    async def xiaohongshu_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.xiaohongshu_upload_video()


class XiaoHongShuNote(XiaoHongShuBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        desc: str | None = None,
        publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
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
        self.tags = tags or []
        self.desc = desc if desc is not None else self.note
        self.title = title or ((self.desc or self.note)[:20] if (self.desc or self.note) else "")

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.image_paths:
            raise ValueError("图文模式下，图片是必须的")
        if not self.title or not str(self.title).strip():
            raise ValueError("图文模式下，title 是必须的")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def upload_note_content(self, page: Page) -> None:
        xiaohongshu_logger.info(_msg("🏃", f"小人开始搬运图文，共 {len(self.image_paths)} 张图片"))
        xiaohongshu_logger.info(_msg("🧭", "小人正在赶往图文发布页"))
        await page.goto(XHS_PUBLISH_NOTE_URL)
        await page.wait_for_url(XHS_PUBLISH_NOTE_URL)

        upload_input = page.locator('input[type="file"][accept*="image"]').first
        if not await upload_input.count():
            upload_input = page.locator("div[class^='upload-content'] input[class='upload-input']").first

        await upload_input.wait_for(state="attached", timeout=30000)
        xiaohongshu_logger.info(_msg("📤", "小人正在上传图片"))
        await upload_input.set_input_files(self.image_paths)

        while True:
            try:
                title_container = page.locator('input[placeholder*="填写标题"]').first
                await title_container.wait_for(state="visible", timeout=3000)
                xiaohongshu_logger.success(_msg("🥳", "图文素材已经传完，可以开始填写内容了"))
                break
            except Exception:
                xiaohongshu_logger.debug(_msg("🧍", "图文素材还在上传，小人继续等一会"))
                await asyncio.sleep(1)

        xiaohongshu_logger.info(_msg("✍️", "小人开始填标题、描述和话题"))
        await self.fill_meta(page)

        await self.set_original_declaration(page)

        # 设置声明（如AI合成内容声明）
        await self.set_declaration(page)

        if self.publish_strategy == XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            await self.set_schedule_time_xiaohongshu(page, self.publish_date)

        xiaohongshu_logger.info(_msg("🚀", "小人正在点击发布按钮"))
        max_retries = 3  # 最大重试次数
        retry_count = 0
        while retry_count < max_retries:
            try:
                if self.publish_strategy == XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED:
                    await page.locator('button:has-text("定时发布")').click()
                else:
                    await page.locator('button:has-text("发布")').click()
                await page.wait_for_url(
                    XHS_PUBLISH_SUCCESS_URL_PATTERN,
                    timeout=3000
                )
                xiaohongshu_logger.success(_msg("🥳", "图文发布成功，小人开心收工"))
                break
            except Exception as e:
                retry_count += 1
                xiaohongshu_logger.info(_msg("🏃", f"小人正在冲刺发布图文，重试 {retry_count}/{max_retries}: {e}"))
                # 只在最后一次失败时截图
                if retry_count == max_retries and self.debug and self.screenshot_manager:
                    await self.screenshot_manager.take_screenshot(page, f"图文发布失败_重试{retry_count}次")
                await asyncio.sleep(0.5)
        
        # 如果重试3次都失败，抛出异常
        if retry_count >= max_retries:
            raise Exception(f"图文发布失败：已重试{max_retries}次仍未成功")

    async def upload(self, playwright: Playwright) -> None:
        xiaohongshu_logger.info(_msg("🧍", "小人先检查 cookie、图片和发布时间"))
        await self.validate_upload_args()
        xiaohongshu_logger.info(_msg("🥳", "图文上传前检查通过"))
        browser = await playwright.chromium.launch(headless=self.headless, channel="chrome")
        context = await browser.new_context(
            permissions=["geolocation"],
            storage_state=self.account_file,
        )
        context = await set_init_script(context)

        try:
            page = await context.new_page()
            await self.upload_note_content(page)
            await context.storage_state(path=self.account_file)
            xiaohongshu_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            await browser.close()

    async def xiaohongshu_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.xiaohongshu_upload_note()
