# -*- coding: utf-8 -*-
import random
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import time
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.log import baijiahao_logger
from utils.network import async_retry


async def baijiahao_cookie_gen(account_file):
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
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://baijiahao.baidu.com/builder/theme/bjh/login")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)
        baijiahao_logger.success("cookie saved")


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://baijiahao.baidu.com/builder/rc/home")
        await page.wait_for_timeout(timeout=5000)

        if await page.get_by_text('注册/登录百家号').count():
            baijiahao_logger.error("等待5秒 cookie 失效")
            return False
        else:
            baijiahao_logger.success("[+] cookie 有效")
            return True


async def baijiahao_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            return False
        baijiahao_logger.error("cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件")
        await baijiahao_cookie_gen(account_file)
    return True

class BaiJiaHaoVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, proxy_setting=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.proxy_setting = proxy_setting

    async def set_schedule_time(self, page, publish_date):
        """
        todo 时间选择，日后在处理 百家号的时间选择不准确，目前是随机
        """
        publish_date_day = f"{publish_date.month}月{publish_date.day}日" if publish_date.day >9  else f"{publish_date.month}月0{publish_date.day}日"
        publish_date_hour = f"{publish_date.hour}点"
        publish_date_min = f"{publish_date.minute}分"
        await page.wait_for_selector('div.select-wrap', timeout=5000)
        for _ in range(3):
            try:
                await page.locator('div.select-wrap').nth(0).click()
                await page.wait_for_selector('div.rc-virtual-list  div.cheetah-select-item', timeout=5000)
                break
            except:
                await page.locator('div.select-wrap').nth(0).click()
        # page.locator(f'div.rc-virtual-list-holder-inner >> text={publish_date_day}').click()
        await page.wait_for_timeout(2000)
        await page.locator(f'div.rc-virtual-list  div.cheetah-select-item >> text={publish_date_day}').click()
        await page.wait_for_timeout(2000)

        # 改为随机点击一个 hour
        for _ in range(3):
            try:
                await page.locator('div.select-wrap').nth(1).click()
                await page.wait_for_selector('div.rc-virtual-list div.rc-virtual-list-holder-inner:visible', timeout=5000)
                break
            except:
                await page.locator('div.select-wrap').nth(1).click()
        await page.wait_for_timeout(2000)
        current_choice_hour = await page.locator('div.rc-virtual-list:visible div.cheetah-select-item-option').count()
        await page.wait_for_timeout(2000)
        await page.locator('div.rc-virtual-list:visible div.cheetah-select-item-option').nth(
            random.randint(1, current_choice_hour-3)).click()
        # 2024.08.05 current_choice_hour的获取可能有问题，页面有7，这里获取了10，暂时硬编码至6

        await page.wait_for_timeout(2000)
        await page.locator("button >> text=定时发布").click()


    async def handle_upload_error(self, page):
        # 日后实现，目前没遇到
        return
        print("视频出错了，重新上传中")

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path, proxy=self.proxy_setting)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(storage_state=f"{self.account_file}", user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.4324.150 Safari/537.36')
        # context = await set_init_script(context)
        await context.grant_permissions(['geolocation'])

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://baijiahao.baidu.com/builder/rc/edit?type=videoV2", timeout=60000)
        baijiahao_logger.info(f"正在上传-------{self.title}.mp4")
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        baijiahao_logger.info('正在打开主页...')
        await page.wait_for_url("https://baijiahao.baidu.com/builder/rc/edit?type=videoV2", timeout=60000)

        # 点击 "上传视频" 按钮
        await page.locator("div[class^='video-main-container'] input").set_input_files(self.file_path)

        # 等待页面跳转到指定的 URL
        while True:
            # 判断是是否进入视频发布页面，没进入，则自动等待到超时
            try:
                await page.wait_for_selector("div#formMain:visible")
                break
            except:
                baijiahao_logger.info("正在等待进入视频发布页面...")
                await asyncio.sleep(0.1)

        # 填充标题和话题
        # 这里为了避免页面变化，故使用相对位置定位：作品标题父级右侧第一个元素的input子元素
        await asyncio.sleep(1)
        baijiahao_logger.info("正在填充标题和话题...")
        await self.add_title_tags(page)

        upload_status = await self.uploading_video(page)
        if not upload_status:
            baijiahao_logger.error(f"发现上传出错了... 文件:{self.file_path}")
            raise

        # 判断视频封面图是否生成成功
        while True:
            baijiahao_logger.info("正在确认封面完成, 准备去点击定时/发布...")
            if await page.locator("div.cheetah-spin-container img").count():
                baijiahao_logger.info("封面已完成，点击定时/发布...")
                break
            else:
                baijiahao_logger.info("等待封面生成...")
                await asyncio.sleep(3)

        await self.publish_video(page, self.publish_date)
        await page.wait_for_timeout(2000)
        if await page.locator('div.passMod_dialog-container >> text=百度安全验证:visible').count():
            baijiahao_logger.error("出现验证，退出")
            raise Exception("出现验证，退出")
        await page.wait_for_url("https://baijiahao.baidu.com/builder/rc/clue**", timeout=5000)
        baijiahao_logger.success("视频发布成功")

        await context.storage_state(path=self.account_file)  # 保存cookie
        baijiahao_logger.info('cookie更新完毕！')
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()


    @async_retry(timeout=300)  # 例如，最多重试3次，超时时间为180秒
    async def uploading_video(self, page):
        while True:
            upload_failed = await page.locator('div .cover-overlay:has-text("上传失败")').count()
            if upload_failed:
                baijiahao_logger.error("发现上传出错了...")
                # await self.handle_upload_error(page)  # 假设这是处理上传错误的函数
                return False

            uploading = await page.locator('div .cover-overlay:has-text("上传中")').count()
            if uploading:
                baijiahao_logger.info("正在上传视频中...")
                await asyncio.sleep(2)  # 等待2秒再次检查
                continue

            # 检查上传是否成功
            if not uploading and not upload_failed:
                baijiahao_logger.success("视频上传完毕")
                return True

    async def set_schedule_publish(self, page, publish_date):
        while True:
            schedule_element = page.locator("div.op-btn-outter-content >> text=定时发布").locator("..").locator(
                'button')
            try:
                await schedule_element.click()
                await page.wait_for_selector('div.select-wrap:visible', timeout=3000)
                await page.wait_for_timeout(timeout=2000)
                baijiahao_logger.info("开始点击发布定时...")
                await self.set_schedule_time(page, publish_date)
                break
            except Exception as e:
                baijiahao_logger.error(f"定时发布失败: {e}")
                raise  # 重新抛出异常，让重试装饰器捕获

    @async_retry(timeout=300)  # 例如，最多重试3次，超时时间为180秒
    async def publish_video(self, page: Page, publish_date):
        if publish_date != 0:
            # 定时发布
            await self.set_schedule_publish(page, publish_date)
        else:
            # 立即发布
            await self.direct_publish(page)

    async def direct_publish(self, page):
        try:
            publish_button = page.locator("button >> text=发布")
            if await publish_button.count():
                await publish_button.click()
        except Exception as e:
            baijiahao_logger.error(f"直接发布视频失败: {e}")
            raise  # 重新抛出异常，让重试装饰器捕获

    async def add_title_tags(self, page):
        title_container = page.get_by_placeholder('添加标题获得更多推荐')
        if len(self.title) <= 8:
            self.title += " 你不知道的"
        await title_container.fill(self.title[:30])

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)



    # 使用 AI成片 功能
    async def ai2video(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path, proxy=self.proxy_setting)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(
            viewport={"width": 1600, "height": 900},
            storage_state=f"{self.account_file}",
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.4324.150 Safari/537.36'
        )
        # context = await set_init_script(context)
        await context.grant_permissions(['geolocation'])

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://aigc.baidu.com/make", timeout=60000)
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        baijiahao_logger.info('正在打开主页...')
        await page.wait_for_url("https://aigc.baidu.com/make", timeout=60000)

        # 点击"全网"标签
        await page.locator('div.rounded-lg.border:has-text("全网")').click()
        await asyncio.sleep(1)  # 这里延迟是为了方便眼睛直观的观看

        # 点击 "上传视频" 按钮
        # await page.locator("div[class^='video-main-container'] input").set_input_files(self.file_path)

        # region 操作处

        # 生成日期时间键名（格式：ai2video_YYYYMMDDHHMM）
        now = datetime.now()
        datetime_str = now.strftime("%Y%m%d%H%M")
        processed_key = "ai2video_processed_titles"
        batch_key = f"ai2video_{datetime_str}"

        # 初始化LocalStorage
        await page.evaluate(f"""
                   if (!localStorage.getItem("{processed_key}")) {{
                       localStorage.setItem("{processed_key}", JSON.stringify([]));                   
                   }}
                   if (!localStorage.getItem("{batch_key}")) {{
                       localStorage.setItem("{batch_key}", JSON.stringify([]));                   
                   }}
               """)

        # 定位新闻列表容器（转义特殊CSS字符）
        container_selector = '.overflow-auto.flex-grow.h-0.saas-scrollbar.mt\-\[-4px\].pl\-\[24px\].pr\-\[10px\].pb\-\[18px\]'
        news_items = await page.locator(container_selector).locator('div.py\-\[6px\].group.cursor-pointer').all()

        for item in news_items:
            try:
                # 获取新闻标题
                title_elem = item.locator('div.flex.text-gray-darker.items-center.relative.pr\-\[56px\] > span')
                title = await title_elem.text_content()
                if not title:
                    continue

                # 检查是否已处理过
                is_processed = await page.evaluate(
                    f"""title => {{
                               const processedList = JSON.parse(localStorage.getItem("{processed_key}") || "[]");
                               return processedList.includes(title);
                           }}""",
                    title
                )

                if is_processed:
                    print(f"[跳过] {title}")
                    continue

                # 悬停显示按钮（根据HTML结构，按钮在悬停时显示）
                await item.hover()

                # 点击生成文案按钮
                button = item.locator('button:has-text("生成文案")')
                await button.click()
                print(f"[点击] {title}")

                # 等待30秒
                # await page.wait_for_timeout(30000)
                print(f"[等待完成] {title}")
                
                # 监听"一键成片"按钮
                print(f"[开始监听] 一键成片按钮")
                should_exit_while_loop = False  # 添加标志变量
                while True:
                    # 定位"一键成片"按钮
                    one_key_button = page.locator("button:has-text('一键成片')")
                    
                    # 检查按钮是否存在
                    if await one_key_button.count() > 0:
                        # 检查按钮是否有disabled属性
                        is_disabled = await one_key_button.get_attribute("disabled")
                        
                        if is_disabled is None:
                            # 按钮不再被禁用，点击它
                            print(f"[发现可点击按钮] 一键成片")
                            await one_key_button.click()  # 先点击一键成片按钮
                            
                            # 等待可能出现的"温馨提示"窗口
                            print(f"[检查] 是否出现温馨提示窗口")
                            await page.wait_for_timeout(2000)  # 等待2秒，让窗口有时间显示
                            
                            try:
                                # 检查是否存在"温馨提示"窗口，设置较短的超时时间
                                tip_window = page.locator("div:has-text('温馨提示') >> visible=true")
                                if await tip_window.count() > 0:
                                    print(f"[发现] 温馨提示窗口")
                                    
                                    # 定位并点击"知道了"按钮，设置较短的超时时间
                                    know_button = page.locator("button:has-text('知道了')")
                                    if await know_button.count() > 0:
                                        try:
                                            # 设置较短的超时时间进行点击
                                            await know_button.click(timeout=5000)
                                            print(f"[已点击] 知道了按钮")
                                        except Exception as e:
                                            print(f"[警告] 点击知道了按钮时出错: {str(e)}")
                                    else:
                                        print(f"[警告] 未找到知道了按钮")
                                else:
                                    print(f"[信息] 未出现温馨提示窗口，继续执行")
                            except Exception as e:
                                print(f"[警告] 处理温馨提示窗口时出错: {str(e)}")
                                # 继续执行，不要因为这个错误中断流程
                                
                            # 记录到LocalStorage前打印日志
                            print(f"[开始记录] 准备将标题 '{title}' 记录到LocalStorage")
                            
                            # 记录到LocalStorage
                            await page.evaluate(
                                f"""
                                        (title, processedKey, batchKey) => {{
                                            // 更新已处理列表
                                            const processedList = JSON.parse(localStorage.getItem(processedKey) || "[]");
                                            if (!processedList.includes(title)) {{
                                                processedList.push(title);
                                                localStorage.setItem(processedKey, JSON.stringify(processedList));
                                            }}

                                            // 更新当前批次记录
                                            const batchList = JSON.parse(localStorage.getItem(batchKey) || "[]");
                                            if (!batchList.includes(title)) {{
                                                batchList.push(title);
                                                localStorage.setItem(batchKey, JSON.stringify(batchList));
                                            }}
                                        }}
                                        """,
                                title, processed_key, batch_key
                            )
                            
                            # 记录完成后打印日志
                            print(f"[记录完成] 标题 '{title}' 已成功记录到LocalStorage")

                            print(f"[记录完成] {title}")
                            
                            # 监听新打开的标签页
                            print(f"[监听] 等待新标签页打开")
                            # 获取当前所有页面
                            current_pages = context.pages
                            current_page_count = len(current_pages)
                            
                            # 等待新标签页打开（最多等待10秒）
                            new_page = None
                            max_wait_time = 10  # 最大等待时间（秒）
                            start_time = time.time()
                            
                            while time.time() - start_time < max_wait_time:
                                # 获取最新的页面列表
                                pages = context.pages
                                # 如果页面数量增加，说明新标签页已打开
                                if len(pages) > current_page_count:
                                    # 获取最新打开的页面（通常是列表中的最后一个）
                                    new_page = pages[-1]
                                    print(f"[发现] 新标签页已打开")
                                    break
                                # 短暂等待后再次检查
                                await asyncio.sleep(0.5)
                            
                            # 如果找到新标签页，获取其标题和URL并保存
                            if new_page:
                                # 等待页面加载完成
                                try:
                                    await new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                                    # 获取页面标题和URL
                                    page_title = await new_page.title()
                                    page_url = new_page.url
                                    
                                    print(f"[获取] 标题: {page_title}")
                                    print(f"[获取] URL: {page_url}")
                                    
                                    # 将标题和URL保存到url.txt文件
                                    with open("url.txt", "a", encoding="utf-8") as f:
                                        f.write(f"{page_title}\n{page_url}\n\n")
                                    
                                    print(f"[保存] 标题和URL已保存到url.txt")
                                    
                                    # 等待5秒后关闭新标签页
                                    print(f"[等待] 5秒后将关闭新标签页")
                                    await asyncio.sleep(5)
                                    await new_page.close()
                                    print(f"[关闭] 新标签页已关闭")
                                except Exception as e:
                                    print(f"[错误] 处理新标签页时出错: {str(e)}")
                                    try:
                                        # 尝试关闭页面，即使出错
                                        await new_page.close()
                                        print(f"[关闭] 新标签页已关闭（出错后）")
                                    except:
                                        pass
                            else:
                                print(f"[警告] 未检测到新标签页打开")
                            
                            # 跳出整个while循环
                            print(f"[操作] 跳出所有循环，不再处理其他新闻")
                            should_exit_while_loop = True  # 设置标志变量
                            break  # 跳出while循环
                    
                    # 检查是否需要跳出while循环
                    if should_exit_while_loop:
                        break
                        
                    # 每秒检查一次按钮状态
                    await page.wait_for_timeout(1000)
                
                # 检查是否需要跳出for循环
                if should_exit_while_loop:
                    print(f"[操作] 跳出for循环，完全结束处理")
                    break  # 跳出for循环
            except Exception as e:
                print(f"处理新闻时出错: {str(e)}")
                continue


        # endregion 操作处

        print(f"[循环完成] 准备关闭浏览器")

        # 暂停 1000s
        await asyncio.sleep(1000)  # 这里延迟是为了方便眼睛直观的观看

        # 退出前保存 storage 信息
        await context.storage_state(path=self.account_file)  # 保存cookie
        baijiahao_logger.info('cookie更新完毕！')
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()


    async def mainAi(self):
        async with async_playwright() as playwright:
            await self.ai2video(playwright)
