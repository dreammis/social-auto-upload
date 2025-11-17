# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import tencent_logger


def format_str_for_short_title(origin_title: str) -> str:
    # 定义允许的特殊字符
    allowed_special_chars = "《》“”:+?%°"

    # 移除不允许的特殊字符
    filtered_chars = [char if char.isalnum() or char in allowed_special_chars else ' ' if char == ',' else '' for
                      char in origin_title]
    formatted_string = ''.join(filtered_chars)

    # 调整字符串长度
    if len(formatted_string) > 16:
        # 截断字符串
        formatted_string = formatted_string[:16]
    elif len(formatted_string) < 6:
        # 使用空格来填充字符串
        formatted_string += ' ' * (6 - len(formatted_string))

    return formatted_string


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        try:
            await page.wait_for_selector('div.title-name:has-text("微信小店")', timeout=5000)  # 等待5秒
            tencent_logger.error("[+] 等待5秒 cookie 失效")
            return False
        except:
            tencent_logger.success("[+] cookie 有效")
            return True


async def get_tencent_cookie(account_file):
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


async def weixin_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, "tencent_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        tencent_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await get_tencent_cookie(account_file)
    return True


class TencentVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, category=None, is_draft=False):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.category = category
        self.headless = LOCAL_CHROME_HEADLESS
        self.is_draft = is_draft  # 是否保存为草稿
        self.local_executable_path = LOCAL_CHROME_PATH or None

    async def set_schedule_time_tencent(self, page, publish_date):
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()

        await page.click('input[placeholder="请选择发表时间"]')

        str_month = str(publish_date.month) if publish_date.month > 9 else "0" + str(publish_date.month)
        current_month = str_month + "月"
        # 获取当前的月份
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')

        # 检查当前月份是否与目标月份相同
        if page_month != current_month:
            await page.click('button.weui-desktop-btn__icon__right')

        # 获取页面元素
        elements = await page.query_selector_all('table.weui-desktop-picker__table a')

        # 遍历元素并点击匹配的元素
        for element in elements:
            if 'weui-desktop-picker__disabled' in await element.evaluate('el => el.className'):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        # 输入小时部分（假设选择11小时）
        await page.click('input[placeholder="请选择时间"]')
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date.hour))

        # 选择标题栏（令定时时间生效）
        await page.locator("div.input-editor").click()

    async def handle_upload_error(self, page):
        tencent_logger.info("视频出错了，重新上传中")
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role('button', name="删除", exact=True).click()
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium (这里使用系统内浏览器，用chromium 会造成h264错误
        browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        tencent_logger.info(f'[+]正在上传-------{self.title}.mp4')
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        await page.wait_for_url("https://channels.weixin.qq.com/platform/post/create")
        # await page.wait_for_selector('input[type="file"]', timeout=10000)
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(self.file_path)
        # 填充标题和话题
        await self.add_title_tags(page)
        # 添加商品
        # await self.add_product(page)
        # 合集功能
        await self.add_collection(page)
        # 原创选择
        await self.add_original(page)
        # 检测上传状态
        await self.detect_upload_status(page)
        if self.publish_date != 0:
            await self.set_schedule_time_tencent(page, self.publish_date)
        # 添加短标题
        await self.add_short_title(page)

        await self.click_publish(page)

        await context.storage_state(path=f"{self.account_file}")  # 保存cookie
        tencent_logger.success('  [-]cookie更新完毕！')
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()

    async def add_short_title(self, page):
        short_title_element = page.get_by_text("短标题", exact=True).locator("..").locator(
            "xpath=following-sibling::div").locator(
            'span input[type="text"]')
        if await short_title_element.count():
            short_title = format_str_for_short_title(self.title)
            await short_title_element.fill(short_title)

    async def click_publish(self, page):
        while True:
            try:
                if self.is_draft:
                    # 点击"保存草稿"按钮
                    draft_button = page.locator('div.form-btns button:has-text("保存草稿")')
                    if await draft_button.count():
                        await draft_button.click()
                    # 等待跳转到草稿箱页面或确认保存成功
                    await page.wait_for_url("**/post/list**", timeout=5000)  # 使用通配符匹配包含post/list的URL
                    tencent_logger.success("  [-]视频草稿保存成功")
                else:
                    # 点击"发表"按钮
                    publish_button = page.locator('div.form-btns button:has-text("发表")')
                    if await publish_button.count():
                        await publish_button.click()
                    await page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=5000)
                    tencent_logger.success("  [-]视频发布成功")
                break
            except Exception as e:
                current_url = page.url
                if self.is_draft:
                    # 检查是否在草稿相关的页面
                    if "post/list" in current_url or "draft" in current_url:
                        tencent_logger.success("  [-]视频草稿保存成功")
                        break
                else:
                    # 检查是否在发布列表页面
                    if "https://channels.weixin.qq.com/platform/post/list" in current_url:
                        tencent_logger.success("  [-]视频发布成功")
                        break
                tencent_logger.exception(f"  [-] Exception: {e}")
                tencent_logger.info("  [-] 视频正在发布中...")
                await asyncio.sleep(0.5)

    async def detect_upload_status(self, page):
        while True:
            # 匹配删除按钮，代表视频上传完毕，如果不存在，代表视频正在上传，则等待
            try:
                # 匹配删除按钮，代表视频上传完毕
                if "weui-desktop-btn_disabled" not in await page.get_by_role("button", name="发表").get_attribute(
                        'class'):
                    tencent_logger.info("  [-]视频上传完毕")
                    break
                else:
                    tencent_logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)
                    # 出错了视频出错
                    if await page.locator('div.status-msg.error').count() and await page.locator(
                            'div.media-status-content div.tag-inner:has-text("删除")').count():
                        tencent_logger.error("  [-] 发现上传出错了...准备重试")
                        await self.handle_upload_error(page)
            except:
                tencent_logger.info("  [-] 正在上传视频中...")
                await asyncio.sleep(2)

    async def add_title_tags(self, page):
        await page.locator("div.input-editor").click()
        await page.keyboard.type(self.title)
        await page.keyboard.press("Enter")
        for index, tag in enumerate(self.tags, start=1):
            await page.keyboard.type("#" + tag)
            await page.keyboard.press("Space")
        tencent_logger.info(f"成功添加hashtag: {len(self.tags)}")

    async def add_collection(self, page):
        collection_elements = page.get_by_text("添加到合集").locator("xpath=following-sibling::div").locator(
            '.option-list-wrap > div')
        if await collection_elements.count() > 1:
            await page.get_by_text("添加到合集").locator("xpath=following-sibling::div").click()
            await collection_elements.first.click()

    async def add_original(self, page):
        if await page.get_by_label("视频为原创").count():
            await page.get_by_label("视频为原创").check()
        # 检查 "我已阅读并同意 《视频号原创声明使用条款》" 元素是否存在
        label_locator = await page.locator('label:has-text("我已阅读并同意 《视频号原创声明使用条款》")').is_visible()
        if label_locator:
            await page.get_by_label("我已阅读并同意 《视频号原创声明使用条款》").check()
            await page.get_by_role("button", name="声明原创").click()
        # 2023年11月20日 wechat更新: 可能新账号或者改版账号，出现新的选择页面
        if await page.locator('div.label span:has-text("声明原创")').count() and self.category:
            # 因处罚无法勾选原创，故先判断是否可用
            if not await page.locator('div.declare-original-checkbox input.ant-checkbox-input').is_disabled():
                await page.locator('div.declare-original-checkbox input.ant-checkbox-input').click()
                if not await page.locator(
                        'div.declare-original-dialog label.ant-checkbox-wrapper.ant-checkbox-wrapper-checked:visible').count():
                    await page.locator('div.declare-original-dialog input.ant-checkbox-input:visible').click()
            if await page.locator('div.original-type-form > div.form-label:has-text("原创类型"):visible').count():
                await page.locator('div.form-content:visible').click()  # 下拉菜单
                await page.locator(
                    f'div.form-content:visible ul.weui-desktop-dropdown__list li.weui-desktop-dropdown__list-ele:has-text("{self.category}")').first.click()
                await page.wait_for_timeout(1000)
            if await page.locator('button:has-text("声明原创"):visible').count():
                await page.locator('button:has-text("声明原创"):visible').click()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
