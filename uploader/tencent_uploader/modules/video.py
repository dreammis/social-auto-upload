# -*- coding: utf-8 -*-
from datetime import datetime
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright
from utils.log import tencent_logger
from utils.base_social_media import set_init_script
from conf import LOCAL_CHROME_PATH
from .account import get_account_info
from .utils import format_str_for_short_title

def format_str_for_short_title(origin_title: str) -> str:
    """
    格式化标题字符串，用于生成短标题。

    该函数会移除标题中的非字母数字字符和特定的特殊字符，然后根据长度要求进行截断或填充，
    以生成符合规范的短标题。

    参数:
    origin_title: 原始标题字符串。

    返回值:
    格式化后的短标题字符串。
    """
    # 定义允许的特殊字符
    allowed_special_chars = "《》" "+?%°"

    # 移除不允许的特殊字符
    filtered_chars = [
        (
            char
            if char.isalnum() or char in allowed_special_chars
            else " " if char == "," else ""
        )
        for char in origin_title
    ]
    formatted_string = "".join(filtered_chars)

    # 调整字符串长度
    if len(formatted_string) > 16:
        # 截断字符串
        formatted_string = formatted_string[:16]
    elif len(formatted_string) < 6:
        # 使用空格来填充字符串
        formatted_string += " " * (6 - len(formatted_string))

    return formatted_string

class TencentVideo:
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime,
        account_files: list,
        category=None,
        cover_path=None,
        friends=None,
        location=None,
    ):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_files = account_files
        self.category = category
        self.cover_path = cover_path  # 添加封面路径
        self.friends = friends or []  # 添加好友列表
        self.location = location  # 添加位置信息
        self.local_executable_path = LOCAL_CHROME_PATH

    async def set_schedule_time_tencent(self, page, publish_date):
        """设置腾讯视频的定时发布时间"""
        # 点击定时发布
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()

        await page.click('input[placeholder="请选择发表时间"]')

        str_month = (
            str(publish_date.month)
            if publish_date.month > 9
            else "0" + str(publish_date.month)
        )
        current_month = str_month + "月"
        # 获取当前的月份
        page_month = await page.inner_text(
            'span.weui-desktop-picker__panel__label:has-text("月")'
        )

        # 检查当前月份是否与目标月份相同
        if page_month != current_month:
            await page.click("button.weui-desktop-btn__icon__right")

        # 获取页面元素
        elements = await page.query_selector_all("table.weui-desktop-picker__table a")

        # 遍历元素并点击匹配的元素
        for element in elements:
            if "weui-desktop-picker__disabled" in await element.evaluate(
                "el => el.className"
            ):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        # 输入小时部分
        await page.click('input[placeholder="请选择时间"]')
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date.hour))

        # 选择标题栏（令定时时间生效）
        await page.locator("div.input-editor").click()

    async def handle_upload_error(self, page):
        """处理视频上传错误"""
        tencent_logger.info("视频出错了，重新上传中")
        await page.locator(
            'div.media-status-content div.tag-inner:has-text("删除")'
        ).click()
        await page.get_by_role("button", name="删除", exact=True).click()
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(self.file_path)

    async def detect_upload_status(self, page, account_name: str):
        """检测视频上传状态"""
        max_retries = 180  # 最大等待时间30分钟 (180 * 10秒)
        retry_count = 0

        while retry_count < max_retries:
            try:
                # 检查是否出现错误状态
                error_msg = page.locator("div.status-msg.error")
                delete_button = page.locator(
                    'div.media-opr div.finder-tag-wrap div.tag-inner:has-text("删除")'
                )

                if await error_msg.count() and await delete_button.count():
                    tencent_logger.error(f"[{account_name}] 发现上传出错了...准备重试")
                    await self.handle_upload_error(page)
                    return False

                # 检查发表按钮是否可用
                publish_button = page.get_by_role("button", name="发表")
                if await publish_button.count():
                    button_class = await publish_button.get_attribute("class")
                    if "weui-desktop-btn_disabled" not in button_class:
                        # 检查封面更换按钮是否可用
                        cover_button = page.locator(
                            'div.finder-tag-wrap.btn:not(.disabled) div.tag-inner:has-text("更换封面")'
                        )
                        if await cover_button.count():
                            tencent_logger.info(
                                f"[{account_name}] 视频上传完毕，封面按钮可用"
                            )
                            return True

                tencent_logger.info(f"[{account_name}] 正在上传视频中...")
                await asyncio.sleep(5)  # 每5秒检查一次
                retry_count += 1

            except Exception as e:
                tencent_logger.error(f"  [-]检测上传状态出错: {str(e)}")
                await asyncio.sleep(10)
                retry_count += 1

        tencent_logger.error(f"  [-]视频上传超时")
        return False

    async def upload_cover(self, page, account_name: str) -> None:
        """上传视频封面"""
        if not self.cover_path:
            return

        try:
            # 等待封面上传按钮出现，使用更精确的定位器
            cover_button = page.locator(
                'div.finder-tag-wrap.btn:not(.disabled) div.tag-inner:has-text("更换封面")'
            )
            if await cover_button.count():
                await cover_button.click()

                # 等待编辑视频封面对话框出现
                edit_cover_dialog = page.locator(
                    'h3.weui-desktop-dialog__title:has-text("编辑视频封面")'
                )
                await edit_cover_dialog.wait_for()

                # 等待并点击上传封面按钮
                upload_button = page.locator(
                    "div[data-v-5fa289d1].img-wrap.initial-wrap"
                )
                await upload_button.wait_for()

                # 使用新的文件选择器API
                async with page.expect_file_chooser() as fc_info:
                    await upload_button.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(self.cover_path)

                # 等待裁剪对话框出现
                crop_dialog = page.locator(
                    'h3.weui-desktop-dialog__title:has-text("裁剪封面图")'
                )
                await crop_dialog.wait_for()

                # 点击裁剪对话框的确定按钮
                confirm_button = page.locator(
                    'div.weui-desktop-btn_wrp button.weui-desktop-btn_primary:has-text("确定")'
                )
                await confirm_button.click()

                # 等待编辑封面对话框的确认按钮出现
                await page.wait_for_selector("div.cover-set-footer")

                # 点击最终的确认按钮
                final_confirm = page.locator(
                    "div.cover-set-footer button.weui-desktop-btn_primary"
                )
                await final_confirm.click()

                tencent_logger.info(f"[{account_name}] 封面上传成功")
                # 等待封面上传完成
                await asyncio.sleep(2)

        except Exception as e:
            tencent_logger.error(f"[{account_name}] 封面上传失败: {str(e)}")

    async def upload_single(self, account_file: str) -> None:
        """单个账号的上传流程"""
        async with async_playwright() as playwright:
            try:
                # 启动浏览器
                browser = await playwright.chromium.launch(
                    headless=False, executable_path=self.local_executable_path
                )
                context = await browser.new_context(storage_state=str(account_file))
                context = await set_init_script(context)
                page = await context.new_page()

                # 先访问主页获取账号信息
                await page.goto("https://channels.weixin.qq.com/platform/home")
                await page.wait_for_load_state("networkidle")

                # 获取账号信息
                account_info = await get_account_info(page)
                if not account_info:
                    raise Exception("无法获取账号信息")

                account_name = account_info["nickname"]

                # 访问发布页面
                await page.goto("https://channels.weixin.qq.com/platform/post/create")
                tencent_logger.info(f"[+][{account_name}] 开始上传视频-------{self.title}")
                await page.wait_for_url("https://channels.weixin.qq.com/platform/post/create")

                # 上传视频文件
                file_input = page.locator('input[type="file"]')
                await file_input.set_input_files(self.file_path)

                # 填充标题和话题
                await self.add_title_tags(page, account_name)
                # 添加位置信息
                await self.add_location(page, self.location, account_name)
                # 设置定时发布时间
                if self.publish_date != 0:
                    await self.set_schedule_time_tencent(page, self.publish_date)
                # 添加短标题
                await self.add_short_title(page)
                # 原创选择
                await self.add_original(page)

                # 等待视频上传完成
                upload_success = await self.detect_upload_status(page, account_name)

                if upload_success:
                    await self.upload_cover(page, account_name)
                    await self.click_publish(page, account_name)
                    # 直接更新原cookie文件
                    await context.storage_state(path=str(account_file))
                    tencent_logger.success(f"  [-]账号 {account_name} cookie已更新！")

                await asyncio.sleep(2)
                await context.close()

            except Exception as e:
                tencent_logger.error(f"账号 {Path(account_file).stem} 上传失败: {str(e)}")
            finally:
                if "browser" in locals():
                    await browser.close()

    async def main(self):
        """主入口方法，并发处理多个账号的上传"""
        tasks = []
        for account_file in self.account_files:
            task = asyncio.create_task(self.upload_single(account_file))
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def add_short_title(self, page):
        """添加短标题"""
        short_title_element = (
            page.get_by_text("短标题", exact=True)
            .locator("..")
            .locator("xpath=following-sibling::div")
            .locator('span input[type="text"]')
        )

        if await short_title_element.count():
            short_title = format_str_for_short_title(self.title)
            await short_title_element.fill(short_title)

    async def click_publish(self, page, account_name: str):
        """点击发表"""
        max_retries = 30  # 最多尝试30次
        retry_count = 0

        while retry_count < max_retries:
            try:
                publish_button = page.locator('div.form-btns button:has-text("发表")')
                if await publish_button.count():
                    await publish_button.click()

                    # 等待页面跳转，增加超时时间到30秒
                    try:
                        await page.wait_for_url(
                            "https://channels.weixin.qq.com/platform/post/list",
                            timeout=30000,  # 30秒超时
                            wait_until="networkidle",  # 等待网络请求完成
                        )
                        tencent_logger.success(f"  [-]账号 {account_name} 视频发布成功")
                        return
                    except Exception as e:
                        # 检查当前URL，即使超时也可能已经成功
                        if (
                            "https://channels.weixin.qq.com/platform/post/list"
                            in page.url
                        ):
                            tencent_logger.success(
                                f"  [-]账号 {account_name} 视频发布成功"
                            )
                            return

                        tencent_logger.info(
                            f"  [-]账号 {account_name} 视频正在发布中..."
                        )
                        await asyncio.sleep(2)  # 增加等待时间
                        retry_count += 1

            except Exception as e:
                tencent_logger.error(f"  [-]账号 {account_name} 发布出错: {str(e)}")
                await asyncio.sleep(2)
                retry_count += 1

        tencent_logger.error(f"  [-]账号 {account_name} 发布超时")

    async def add_title_tags(self, page, account_name: str):
        """添加标题、话题和好友标记"""
        # 步骤1: 添加标题
        await page.locator("div.input-editor").click()
        await page.keyboard.type(self.title)
        await page.keyboard.press("Enter")

        # 步骤2: 添加标签
        if self.tags:
            for tag in self.tags:
                await page.keyboard.type("#" + tag)
                await page.keyboard.press("Space")
            tencent_logger.info(f"[{account_name}] 成功添加话题: {len(self.tags)}")

        # 步骤3: 添加好友标记
        if self.friends:
            for friend in self.friends:
                await page.keyboard.type("@" + friend)
                await page.keyboard.press("Space")
            tencent_logger.info(f"[{account_name}] 成功@好友: {len(self.friends)}")

    async def add_collection(self, page):
        """添加合集"""
        collection_elements = (
            page.get_by_text("添加到合集")
            .locator("xpath=following-sibling::div")
            .locator(".option-list-wrap > div")
        )

        if await collection_elements.count() > 1:
            await page.get_by_text("添加到合集").locator(
                "xpath=following-sibling::div"
            ).click()
            await collection_elements.first.click()

    async def add_original(self, page):
        """添加原创"""
        if await page.get_by_label("视频为原创").count():
            await page.get_by_label("视频为原创").check()

        # 检查 "我已阅读并同意 《视频号原创声明使用条款》" 元素是否存在
        label_locator = await page.locator(
            'label:has-text("我已阅读并同意 《视频号原创声明使用条款》")'
        ).is_visible()
        if label_locator:
            await page.get_by_label("我已阅读并同意 《视频号原创声明使用条款》").check()
            await page.get_by_role("button", name="声明原创").click()
        # 2023年11月20日 wechat更新: 可能新账号或者改版账号，出现新的选择页面
        if (
            await page.locator('div.label span:has-text("声明原创")').count()
            and self.category
        ):
            # 因处罚无法勾选原创，故先判断是否可用
            if not await page.locator(
                "div.declare-original-checkbox input.ant-checkbox-input"
            ).is_disabled():
                await page.locator(
                    "div.declare-original-checkbox input.ant-checkbox-input"
                ).click()
                if not await page.locator(
                    "div.declare-original-dialog label.ant-checkbox-wrapper.ant-checkbox-wrapper-checked:visible"
                ).count():
                    await page.locator(
                        "div.declare-original-dialog input.ant-checkbox-input:visible"
                    ).click()
            if await page.locator(
                'div.original-type-form > div.form-label:has-text("原创类型"):visible'
            ).count():
                await page.locator("div.form-content:visible").click()  # 下拉菜单
                await page.locator(
                    f'div.form-content:visible ul.weui-desktop-dropdown__list li.weui-desktop-dropdown__list-ele:has-text("{self.category}")'
                ).first.click()
                await page.wait_for_timeout(1000)
            if await page.locator('button:has-text("声明原创"):visible').count():
                await page.locator('button:has-text("声明原创"):visible').click()

    async def add_location(
        self, page, location: str = None, account_name: str = None
    ) -> None:
        """添加位置信息"""
        try:
            # 点击位置选择区域
            position_display = page.locator("div.position-display-wrap")
            if await position_display.count():
                await position_display.click()

                if location is None:
                    # 选择"不显示位置"选项
                    no_location = page.locator(
                        'div.location-item:has-text("不显示位置")'
                    )
                    if await no_location.count():
                        await no_location.click()
                        tencent_logger.info(f"[{account_name}] 已设置为不显示位置")
                else:
                    # 等待位置搜索框出现
                    search_input = page.locator(
                        'input.weui-desktop-form__input[placeholder*="搜索"]'
                    )
                    await search_input.wait_for()

                    # 输入位置并等待
                    await search_input.fill(location)
                    await asyncio.sleep(1)  # 等待搜索结果

                    # 选择第一个搜索结果
                    first_result = page.locator("div.location-item").first
                    if await first_result.count():
                        await first_result.click()
                        tencent_logger.info(
                            f"[{account_name}] 成功添加位置: {location}"
                        )
                    else:
                        tencent_logger.warning(
                            f"[{account_name}] 未找到位置: {location}"
                        )

        except Exception as e:
            tencent_logger.error(f"[{account_name}] 添加位置失败: {str(e)}")

    @staticmethod
    async def get_account_info(page) -> dict:
        """代理到全局get_account_info函数"""
        return await get_account_info(page) 