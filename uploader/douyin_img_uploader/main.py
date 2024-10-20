# -*- coding: utf-8 -*-
from datetime import datetime
from playwright.async_api import Playwright, async_playwright, Page
import re
import asyncio

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import douyin_logger
from utils.send_wechat import *
from utils.redis_tools import *


async def cookie_auth(account_file):
    """
    功能：验证存储在account_file中的cookie是否有效。
    执行步骤：
    1. 使用async_playwright启动一个无头（headless）Chromium浏览器。
    2. 创建一个新的浏览器上下文，并加载account_file中的cookie。
    3. 设置初始脚本（通过set_init_script函数）。
    4. 打开一个新页面并访问抖音创作者中心的上传页面。
    5. 等待页面加载完成，检查是否成功进入上传页面。
    6. 如果页面上出现“手机号登录”字样，说明cookie无效，返回False。
    7. 如果没有出现，说明cookie有效，返回True。
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True


async def douyin_setup(account_file, handle=False):
    """
    功能：检查cookie文件是否存在或有效，并在必要时生成新的cookie。
    执行步骤：
    1. 检查account_file是否存在，或者调用cookie_auth验证cookie是否有效。
    2. 如果cookie无效且handle为True，则调用douyin_cookie_gen生成新的cookie。
    3. 如果cookie有效或成功生成新的cookie，返回True。
    """
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        douyin_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await douyin_cookie_gen(account_file)
    return True


async def douyin_cookie_gen(account_file):
    async with async_playwright() as playwright:
        browser_options = {
            'headless': False
        }
        browser = await playwright.chromium.launch(**browser_options)

        context_options = {
            'viewport': {'width': 1280, 'height': 720}
        }
        context = await browser.new_context(**context_options)
        context = await set_init_script(context)
        page = await context.new_page()

        await page.goto("https://creator.douyin.com/")

        await page.wait_for_load_state('networkidle')

        # 尝试定位二维码
        qr_code_selectors = ['.login-scan-code', 'canvas.qrcode', 'img[alt="二维码"]', '[class*="qrcode"]']
        qr_code_element = None
        for selector in qr_code_selectors:
            try:
                qr_code_element = await page.wait_for_selector(selector, state='visible', timeout=1000)
                if qr_code_element:
                    break
            except:
                continue

        if qr_code_element:
            await qr_code_element.scroll_into_view_if_needed()
            qr_code_path = os.path.join(os.path.dirname(account_file), 'douyin_login_qr.png')
            await qr_code_element.screenshot(path=qr_code_path)
            douyin_logger.info(f'登录二维码已保存至：{qr_code_path}')
            # 定位到二维码将二维码发送到wx
            send_image_file(qr_code_path)
        else:
            douyin_logger.warning('未能自动定位到登录二维码，请手动查看浏览器窗口')
            full_page_path = os.path.join(os.path.dirname(account_file), 'douyin_full_page.png')
            await page.screenshot(path=full_page_path, full_page=True)
            douyin_logger.info(f'已保存完整页面截图：{full_page_path}')

        douyin_logger.info('请在浏览器中完成登录操作')

        login_success = False
        retry_count = 0
        max_retries = 30  # 最多等待5分钟（30 * 10秒）

        while not login_success and retry_count < max_retries:
            try:
                # 检查是否出现身份验证
                if await page.wait_for_selector("text=身份验证"):
                    douyin_logger.info("检测到身份验证")

                    # 点击"接收短信验证"按钮
                    await page.click("text=接收短信验证")
                    douyin_logger.info("已点击'接收短信验证'")

                    # 检查是否存在"接收短信验证"按钮
                    if await page.wait_for_selector("text=接收短信验证"):
                        douyin_logger.info("检测到'接收短信验证'标题")

                        # 等待"获取验证码"按钮出现并点击
                        await page.wait_for_selector("text=获取验证码")
                        await page.click("text=获取验证码")
                        douyin_logger.info("已点击'获取验证码'")

                        # 读取验证码文件
                        # vcode_file = 'cookies/vcode.txt'
                        max_wait = 60  # 最多等待60秒
                        vcode = ''
                        start_time = asyncio.get_event_loop().time()

                        while asyncio.get_event_loop().time() - start_time < max_wait:
                            if redis_client.ping():
                                # with open(vcode_file, 'r') as f:
                                #     vcode = f.read().strip()
                                vcode = get_douyin_verification_code("18282513893")
                                if vcode:
                                    douyin_logger.info(f"从redis读取到验证码: {vcode}")
                                    break
                            await asyncio.sleep(5)  # 等待5秒后重试
                        douyin_logger.info("退出vcode循环")
                        if vcode:
                            douyin_logger.info("准备开始输入")
                            # 等待"获取验证码"按钮出现并点击
                            await page.wait_for_selector(
                                """ //*[@id="uc-second-verify"]/div/div/article/div[2]/div/div/div[1]/input """,
                                timeout=500)
                            await page.click(
                                """ //*[@id="uc-second-verify"]/div/div/article/div[2]/div/div/div[1]/input """)
                            douyin_logger.info("已点击'请输入验证码'")

                            # 定位验证码输入框并输入验证码
                            vcode_input = await page.wait_for_selector(
                                """ //*[@id="uc-second-verify"]/div/div/article/div[2]/div/div/div[1]/input """)
                            await vcode_input.fill(vcode)

                            # 检查验证码是否成功填入
                            input_value = await vcode_input.input_value()
                            if input_value != vcode:
                                douyin_logger.warning(f"验证码填入失败，尝试重新填入。预期：{vcode}，实际：{input_value}")
                                await vcode_input.fill("")  # 清空输入框
                                await vcode_input.type(vcode, delay=100)  # 使用 type 方法慢速输入

                            # 再次检查
                            input_value = await vcode_input.input_value()
                            if input_value == vcode:
                                douyin_logger.info("验证码已成功填入")
                            else:
                                douyin_logger.error(f"验证码填入失败。预期：{vcode}，实际：{input_value}")
                                continue  # 跳过本次循环，重新尝试

                            # 点击验证按钮
                            verify_button = await page.wait_for_selector(
                                '//*[@id="uc-second-verify"]/div/div/article/div[3]/div/div[2]')
                            await verify_button.click()
                            douyin_logger.info("已点击验证按钮")

                            # 等待验证结果
                            await asyncio.sleep(5)

                            # # 删除验证码文件
                            # os.remove(vcode_file)
                        else:
                            douyin_logger.error("未能读取到有效的验证码")
                    else:
                        douyin_logger.info("未检测到'接收短信验证'按钮，可能不需要短信验证")

                # 检查是否已经登录成功
                if await page.wait_for_selector("text=发布作品"):
                    douyin_logger.info("检测到'发布作品'，登录成功")
                    login_success = True
                    break
            except Exception as e:
                douyin_logger.error(f"发生错误: {str(e)}")
                retry_count += 1
                await asyncio.sleep(10)  # 等待10秒后重试

        if login_success:
            # 登录成功后保存cookie
            await context.storage_state(path=account_file)
            douyin_logger.info(f'Cookie已保存至：{account_file}')
        else:
            douyin_logger.error("登录失败，请手动完成登录操作")

        await browser.close()


class DouYinImage(object):
    def __init__(self, title, file_paths, tags, publish_date: datetime, account_file):
        self.title = title
        self.file_paths = file_paths  # 改为 file_paths，以保持与 DouYinVideo 一致
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH

    async def upload(self, playwright: Playwright) -> None:
        browser_options = {}
        if self.local_executable_path:
            browser_options['executable_path'] = self.local_executable_path
        
        try:
            browser = await playwright.chromium.launch(headless=False, **browser_options)
        except Exception as e:
            douyin_logger.error(f"Failed to launch Chromium: {e}")
            douyin_logger.info("Attempting to launch Chrome...")
            browser = await playwright.chromium.launch(channel="chrome", headless=False)

        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)

        page = await context.new_page()
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")

        await page.click("text=发布图文")
        # page.get_by_text("发布图文").click()
        await page.locator("div").filter(has_text=re.compile(
            r"^点击上传 或直接将图片文件拖入此区域最多支持上传35张图片，图片格式不支持gif格式$")).first.click()
        await page.goto(
            "https://creator.douyin.com/creator-micro/content/publish-media/image-text?enter_from=publish_page&media_type=image&type=new")
        await page.get_by_placeholder("添加作品标题").click()
        await page.get_by_placeholder("添加作品标题").fill("这是一段标题")
        await page.locator(".zone-container").click()
        await page.locator(".zone-container").fill("这是简要描述​")
        await page.get_by_text("#添加话题").click()
        await page.get_by_text("重新检测").click()
        await page.locator("div").filter(has_text=re.compile(r"^未见异常检测通过，暂未发现异常重新检测$")).get_by_role(
            "img").click()
        await page.get_by_text("输入相关位置，让更多人看到你的作品").click()
        await page.locator("#douyin_creator_pc_anchor_jump").get_by_role("textbox").fill("射洪")
        await page.get_by_text("窝子凉粉(射洪总店)").click()
        await page.get_by_role("button", name="发布", exact=True).click()

        # 暂停页面
        # await page.pause()

        # douyin_logger.info(f'[+]正在上传图文-------{self.title}')
        #
        # # 点击"发布图文"按钮
        # await page.click("text=发布图文")
        #
        # # 等待图片上传输入元素出现
        # await page.wait_for_selector('//*[@id="root"]/div/div/div[3]/div/div[2]/div/div/div[1]/div/div[3]')
        #
        # # 上传多张图片
        # for file_path in self.file_paths:
        #     await page.locator('input[type="file"][accept="image/png,image/jpeg,image/jpg,image/bmp,image/webp,image/tif"]').set_input_files(file_path)
        #     await asyncio.sleep(1)  # 等待每张图片上传
        #
        # # 等待进入图文发布页面
        # await page.wait_for_url("https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page")
        #
        # # 填充标题和话题
        # await self.fill_title_and_tags(page)
        #
        # # 设置地理位置
        # await self.set_location(page, "杭州市")
        #
        # # 设置第三方平台分享
        # await self.set_third_party_sharing(page)
        #
        # # 设置定时发布（如果需要）
        # if self.publish_date != 0:
        #     await self.set_schedule_time_douyin(page, self.publish_date)
        #
        # # 发布图文
        # await self.publish_content(page)

        await context.storage_state(path=self.account_file)
        douyin_logger.success('  [-]cookie更新完毕！')
        await asyncio.sleep(2)
        await context.close()
        await browser.close()

    async def fill_title_and_tags(self, page):
        # 填充标题
        await page.locator(".notranslate").click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.press("Delete")
        await page.keyboard.type(self.title[:30])  # 限制标题长度为30个字符

        # 填充标签
        tag_input = page.locator(".zone-container")
        for tag in self.tags:
            await tag_input.type("#" + tag)
            await page.keyboard.press("Space")
        douyin_logger.info(f'总共添加{len(self.tags)}个话题')

    async def set_location(self, page, location):
        await page.locator('div.semi-select span:has-text("输入地理位置")').click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    async def set_third_party_sharing(self, page):
        third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
        if await page.locator(third_part_element).count():
            if 'semi-switch-checked' not in await page.eval_on_selector(third_part_element, 'div => div.className'):
                await page.locator(third_part_element).locator('input.semi-switch-native-control').click()

    async def set_schedule_time_douyin(self, page, publish_date):
        # 选择包含特定文本内容的 label 元素
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        # 在选中的 label 元素下点击 checkbox
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await asyncio.sleep(1)
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

        await asyncio.sleep(1)

    async def publish_content(self, page):
        while True:
            try:
                publish_button = page.get_by_role('button', name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage**", timeout=3000)
                douyin_logger.success("  [-]图文发布成功")
                break
            except:
                douyin_logger.info("  [-] 图文正在发布中...")
                await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

async def main(title, file_paths, tags, publish_date, account_file):
    await douyin_setup(account_file, handle=True)
    app = DouYinImage(title, file_paths, tags, publish_date, account_file)
    await app.main()

