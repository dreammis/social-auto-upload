# -*- coding: utf-8 -*-
import traceback
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
from playwright._impl._errors import TimeoutError
import os
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


async def douyin_setup(account_file, handle=False, phone_number=None):
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
        if not phone_number:
            douyin_logger.error('需要提供电话号码以生成新的cookie')
            return False
        douyin_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await douyin_cookie_gen(account_file, phone_number)
    return True


async def douyin_cookie_gen(account_file, phone_number):
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
            send_message("请扫码登录")
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
                            douyin_logger.info("开始读取验证码")
                            if redis_client.ping():
                                vcode = get_douyin_verification_code(phone_number)
                                if vcode:
                                    douyin_logger.info(f"从redis读取到验证码: {vcode}")
                                    break
                            await asyncio.sleep(5)  # 等待5秒后重试
                        douyin_logger.info("退出vcode循环")
                        if vcode:
                            douyin_logger.info("准备开始输入")
                            # 等待"获取验证码"按钮出现并点击
                            await page.wait_for_selector(""" //*[@id="uc-second-verify"]/div/div/article/div[2]/div/div/div[1]/input """, timeout=500)
                            await page.click(""" //*[@id="uc-second-verify"]/div/div/article/div[2]/div/div/div[1]/input """)
                            douyin_logger.info("已点击'请输入验证码'")

                            # 定位验证码输入框并输入验证码
                            vcode_input = await page.wait_for_selector(""" //*[@id="uc-second-verify"]/div/div/article/div[2]/div/div/div[1]/input """)
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
                            verify_button = await page.wait_for_selector('//*[@id="uc-second-verify"]/div/div/article/div[3]/div/div[2]')
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
            except TimeoutError:
                douyin_logger.info(" [-] 不需要身份验证")
                # 检查是否已经登录成功
                if await page.wait_for_selector("text=发布作品"):
                    douyin_logger.info("检测到'发布作品'，登录成功")
                    login_success = True
                    break
                else:
                    # 如果没有检测到"发布作品"，则增加重试次数
                    retry_count += 1
                    douyin_logger.info("未检测到'发布作品'，重试中...")
                    await asyncio.sleep(1)  # 等待1秒后重试
            except Exception as e:
                print(traceback.format_exc())
                douyin_logger.error(f"发生错误: {str(e)}")
                retry_count += 1
                await asyncio.sleep(1)  # 等待1秒后重试
        
        if login_success:
            # 登录成功后保存cookie
            await context.storage_state(path=account_file)
            douyin_logger.info(f'Cookie已保存至：{account_file}')
        else:
            douyin_logger.error("登录失败，请手动完成登录操作")
        
        await browser.close()


class DouYinVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, thumbnail_path=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.thumbnail_path = thumbnail_path

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

    async def handle_upload_error(self, page):
        douyin_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        if self.local_executable_path:
            browser = await playwright.chromium.launch(headless=False, executable_path=self.local_executable_path)
        else:
            browser = await playwright.chromium.launch(headless=False)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        douyin_logger.info(f'[+]正在上传-------{self.title}.mp4')
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        douyin_logger.info(f'[-] 正在打开主页...')
        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")
        # 点击 "上传视频" 按钮
        await page.locator("div[class^='container'] input").set_input_files(self.file_path)

        # 等待页面跳转到指定的 URL
        while True:
            # 判断是是否进入视频发布页面，没进入，则自动等待到超时
            try:
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page")
                break
            except:
                douyin_logger.info(f'  [-] 正在等待进入视频发布页面...')
                await asyncio.sleep(0.1)

        # 填充标题和话题
        # 检查是否存在包含输入框的元素
        # 这里为了避免页面变化，故使用相对位置定位：作标题父级右侧第一个元素的input子元素
        await asyncio.sleep(1)
        douyin_logger.info(f'  [-] 正在填充标题和话题...')
        title_container = page.get_by_text('作品标题').locator("..").locator("xpath=following-sibling::div[1]").locator("input")
        if await title_container.count():
            await title_container.fill(self.title[:30])
        else:
            titlecontainer = page.locator(".notranslate")
            await titlecontainer.click()
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(self.title)
            await page.keyboard.press("Enter")
        css_selector = ".zone-container"
        for index, tag in enumerate(self.tags, start=1):
            await page.type(css_selector, "#" + tag)
            await page.press(css_selector, "Space")
        douyin_logger.info(f'总共添加{len(self.tags)}个话题')

        while True:
            # 判断重新上传按钮是否存在，如果不存在，代表视频正在上传，则等待
            try:
                #  新版：定位重新上传
                number = await page.locator('div label+div:has-text("重新上传")').count()
                if number > 0:
                    douyin_logger.success("  [-]视频上传完毕")
                    break
                else:
                    douyin_logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)

                    if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                        douyin_logger.error("  [-] 发现上传出错了... 准备重试")
                        await self.handle_upload_error(page)
            except:
                douyin_logger.info("  [-] 正上传视频中...")
                await asyncio.sleep(2)
        
        #上传视频封面
        await self.set_thumbnail(page, self.thumbnail_path)

        # 更换可见元素
        await self.set_location(page, "杭州市")

        # 頭條/西瓜
        third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
        # 定位是否有第三方平台
        if await page.locator(third_part_element).count():
            # 检测是否是已选中状态
            if 'semi-switch-checked' not in await page.eval_on_selector(third_part_element, 'div => div.className'):
                await page.locator(third_part_element).locator('input.semi-switch-native-control').click()

        if self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        # 判断视频是否发布成功
        while True:
            # 判断视频是否发布成功
            try:
                publish_button = page.get_by_role('button', name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage**",
                                        timeout=3000)  # 如果自动跳转到作品页面，则代表发布成功
                douyin_logger.success("  [-]视频发布成功")
                break
            except:
                douyin_logger.info("  [-] 视频正在发布中...")
                await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

        await context.storage_state(path=self.account_file)  # 保存cookie
        douyin_logger.success('  [-]cookie更新完毕！')
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览上下文和浏览器实例
        await context.close()
        await browser.close()
    
    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        if thumbnail_path:
            await page.click('text="选择封面"')
            await page.wait_for_selector("div.semi-modal-content:visible")
            await page.click('text="上传封面"')
            # 定位到上传区域并点击
            await page.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input").set_input_files(thumbnail_path)
            await page.wait_for_timeout(2000)  # 等2秒
            await page.locator("div[class^='uploadCrop'] button:has-text('完成')").click()

    async def set_location(self, page: Page, location: str = "杭州市"):
        # todo supoort location later
        # await page.get_by_text('添加标签').locator("..").locator("..").locator("xpath=following-sibling::div").locator(
        #     "div.semi-select-single").nth(0).click()
        await page.locator('div.semi-select span:has-text("输入地理位置")').click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)



























