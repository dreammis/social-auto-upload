# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path
import time
import shutil

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import tencent_logger
from ai_module import generate_hashtags  # 改回绝对导入


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
    allowed_special_chars = "《》""+?%°"

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
    """
    使用 account_file 中的 cookie 进行微信渠道平台的登录验证。

    Args:
        account_file (str): 包含 cookie 信息的文件路径。

    Returns:
        bool: 如果 cookie 有效，返回 True；否则返回 False。
    """
    account_name = Path(account_file).stem
    
    # 启动一个无头的 Chromium 浏览器实例。
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        # 创建一个新的浏览器上下文，并加载账户文件中的存储状态（cookie）。
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面。
        page = await context.new_page()
        # 访问指定的 URL。
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        try:
            # 等待页面上出现特定的元素，以验证 cookie 是否有效。
            await page.wait_for_selector('div.title-name:has-text("微信小店")', timeout=5000)  # 等待5秒
            # 如果元素出现，说明 cookie 失效。
            tencent_logger.error(f"[+][{account_name}] 等待5秒 cookie 失效")
            return False
        except:
            # 如果元素未出现，说明 cookie 有效。
            tencent_logger.success(f"[+][{account_name}] cookie 有效")
            return True


async def get_tencent_cookie(account_file):
    """
    异步获取腾讯的cookie，通过启动浏览器并手动登录实现。
    """
    try:
        async with async_playwright() as playwright:
            options = {
                'args': ['--lang en-GB'],
                'headless': False,
            }
            browser = await playwright.chromium.launch(**options)
            context = await browser.new_context()
            context = await set_init_script(context)
            page = await context.new_page()
            
            # 访问登录页面
            await page.goto("https://channels.weixin.qq.com")
            
            # 等待登录成功
            tencent_logger.info("[+]等待扫码登录...")
            try:
                # 等待登录成功后的重定向
                await page.wait_for_url("https://channels.weixin.qq.com/platform", timeout=120000)  # 2分钟超时
            except Exception as e:
                tencent_logger.error("[+]登录超时，请在2分钟内完成扫码")
                return None
            
            # 确保页面完全加载
            await page.wait_for_load_state('networkidle')
            
            # 获取账号信息
            account_info = await TencentVideo.get_account_info(page)
            if account_info:
                # 创建以账号昵称命名的cookie文件
                cookie_dir = Path(account_file).parent
                cookie_file = cookie_dir / f"{account_info['nickname']}.json"
                
                # 保存cookie
                await context.storage_state(path=str(cookie_file))
                tencent_logger.success(f'[+]成功获取账号 {account_info["nickname"]} 的cookie')
                tencent_logger.info(f'   [-]视频数: {account_info["video_count"]}')
                tencent_logger.info(f'   [-]粉丝数: {account_info["follower_count"]}')
                tencent_logger.info(f'   [-]视频号ID: {account_info["id"]}')
                return str(cookie_file)
            else:
                tencent_logger.error("[+]未能获取账号信息")
                return None
                
    except Exception as e:
        tencent_logger.error(f"获取cookie失败: {str(e)}")
        return None
    finally:
        try:
            await browser.close()
        except:
            pass


async def weixin_setup(account_file, handle=False):
    """
    设置微信登录
    Args:
        account_file: cookie文件路径
        handle: 是否手动处理
    Returns:
        bool: 设置是否成功
    """
    try:
        # 获取绝对路径
        account_file = get_absolute_path(account_file, "tencent_uploader")
        account_dir = Path(account_file).parent
        
        # 检查是否存在同目录下的其他账号cookie文件
        existing_cookies = list(account_dir.glob("*.json"))
        
        # 验证现有cookie
        for cookie_file in existing_cookies:
            if await cookie_auth(str(cookie_file)):
                return True
        
        # 如果所有cookie都无效且允许手动处理
        if handle:
            tencent_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录')
            if new_cookie_file := await get_tencent_cookie(account_file):
                return True
        
        return False
        
    except Exception as e:
        tencent_logger.error(f"账号设置失败: {str(e)}")
        return False


class TencentVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_files: list, 
                 category=None, cover_path=None, friends=None, location=None):
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
        """
        设置腾讯视频的定时发布时间
        Args:
            page: 浏览器页面
            publish_date: 发布时间
        """
        # 点击定时发布
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
        """
        处理视频上传错误
        Args:
            page: 浏览器页面
        """
        tencent_logger.info("视频出错了，重新上传中")
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role('button', name="删除", exact=True).click()
        file_input = page.locator('input[type="file"]')

        await file_input.set_input_files(self.file_path)

    async def detect_upload_status(self, page, account_name: str):
        """
        检测视频上传状态
        Args:
            page: 浏览器页面
            account_name: 账号名称
        Returns:
            bool: 上传是否成功
        """
        max_retries = 180  # 最大等待时间30分钟 (180 * 10秒)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 检查是否出现错误状态
                error_msg = page.locator('div.status-msg.error')
                delete_button = page.locator('div.media-opr div.finder-tag-wrap div.tag-inner:has-text("删除")')
                
                if await error_msg.count() and await delete_button.count():
                    tencent_logger.error(f"[{account_name}] 发现上传出错了...准备重试")
                    await self.handle_upload_error(page)
                    return False
                
                # 检查发表按钮是否可用
                publish_button = page.get_by_role("button", name="发表")
                if await publish_button.count():
                    button_class = await publish_button.get_attribute('class')
                    if "weui-desktop-btn_disabled" not in button_class:
                        # 检查封面更换按钮是否可用
                        cover_button = page.locator('div.finder-tag-wrap.btn:not(.disabled) div.tag-inner:has-text("更换封面")')
                        if await cover_button.count():
                            tencent_logger.info(f"[{account_name}] 视频上传完毕，封面按钮可用")
                            return True
                
                tencent_logger.info(f"[{account_name}] 正在上传视频中...")
                await asyncio.sleep(5)  # 每10秒检查一次
                retry_count += 1
                
            except Exception as e:
                tencent_logger.error(f"  [-]检测上传状态出错: {str(e)}")
                await asyncio.sleep(10)
                retry_count += 1
        
        tencent_logger.error(f"  [-]视频上传超时")
        return False

    async def upload_cover(self, page, account_name: str) -> None:
        """
        上传视频封面
        Args:
            page: playwright页面对象
            account_name: 账号名称
        """
        if not self.cover_path:
            return
            
        try:
            # 等待封面上传按钮出现，使用更精确的定位器
            cover_button = page.locator('div.finder-tag-wrap.btn:not(.disabled) div.tag-inner:has-text("更换封面")')
            if await cover_button.count():
                await cover_button.click()
                
                # 等待编辑视频封面对话框出现
                edit_cover_dialog = page.locator('h3.weui-desktop-dialog__title:has-text("编辑视频封面")')
                await edit_cover_dialog.wait_for()
                
                # 等待并点击上传封面按钮
                upload_button = page.locator('div[data-v-5fa289d1].img-wrap.initial-wrap')
                await upload_button.wait_for()
                
                # 使用新的文件选择器API
                async with page.expect_file_chooser() as fc_info:
                    await upload_button.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(self.cover_path)
                
                # 等待裁剪对话框出现
                crop_dialog = page.locator('h3.weui-desktop-dialog__title:has-text("裁剪封面图")')
                await crop_dialog.wait_for()
                
                # 点击裁剪对话框的确定按钮
                confirm_button = page.locator('div.weui-desktop-btn_wrp button.weui-desktop-btn_primary:has-text("确定")')
                await confirm_button.click()
                
                # 等待编辑封面对话框的确认按钮出现
                await page.wait_for_selector('div.cover-set-footer')
                
                # 点击最终的确认按钮
                final_confirm = page.locator('div.cover-set-footer button.weui-desktop-btn_primary')
                await final_confirm.click()
                
                tencent_logger.info(f"[{account_name}] 封面上传成功")
                # 等待封面上传完成
                await asyncio.sleep(2)
                
        except Exception as e:
            tencent_logger.error(f"[{account_name}] 封面上传失败: {str(e)}")

    async def upload_single(self, account_file: str) -> None:
        """
        单个账号的上传流程
        Args:
            account_file: 账号cookie文件路径
        """
        async with async_playwright() as playwright:
            try:
                # 启动浏览器
                browser = await playwright.chromium.launch(
                    headless=False, 
                    executable_path=self.local_executable_path
                )
                context = await browser.new_context(storage_state=account_file)
                context = await set_init_script(context)
                page = await context.new_page()

                # 先访问主页获取账号信息
                await page.goto("https://channels.weixin.qq.com/platform/home")
                await page.wait_for_load_state('networkidle')
                
                # 获取账号信息
                account_info = await self.get_account_info(page)
                if not account_info:
                    raise Exception("无法获取账号信息")
                
                account_name = account_info['nickname']
                cookie_file = Path(account_file).parent / f"{account_name}_{int(time.time())}.json"
                
                # 访问发布页面
                await page.goto("https://channels.weixin.qq.com/platform/post/create")
                tencent_logger.info(f'[+][{account_name}] 开始上传视频-------{self.title}')
                tencent_logger.info(f'   [-][{account_name}] 当前视频数: {account_info["video_count"]}')
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
                    # 保存cookie到新文件
                    await context.storage_state(path=str(cookie_file))
                    tencent_logger.success(f'  [-]账号 {account_name} cookie已更新！')
                    
                    # 成功后，替换原cookie文件
                    if cookie_file.exists():
                        shutil.copy2(cookie_file, account_file)
                        cookie_file.unlink()  # 删除临时cookie文件
                
                await asyncio.sleep(2)
                await context.close()
                
            except Exception as e:
                tencent_logger.error(f"账号 {Path(account_file).stem} 上传失败: {str(e)}")
            finally:
                if 'browser' in locals():
                    await browser.close()

    async def main(self):
        """
        主入口方法，并发处理多个账号的上传
        """
        # 为每个账号创建独立的上传任务
        tasks = []
        for account_file in self.account_files:
            task = asyncio.create_task(self.upload_single(account_file))
            tasks.append(task)
        
        # 并发执行所有上传任务
        await asyncio.gather(*tasks)

    async def add_short_title(self, page):
        """
        添加短标题
        Args:
            page: 浏览器页面
        """
        short_title_element = page.get_by_text("短标题", exact=True).locator("..").locator(
            "xpath=following-sibling::div").locator(
            'span input[type="text"]')

        if await short_title_element.count():
            short_title = format_str_for_short_title(self.title)
            await short_title_element.fill(short_title)

    async def click_publish(self, page, account_name: str):
        """
        点击发表
        Args:
            page: 浏览器页面
            account_name: 账号名称
        """
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
                            wait_until='networkidle'  # 等待网络请求完成
                        )
                        tencent_logger.success(f"  [-]账号 {account_name} 视频发布成功")
                        return
                    except Exception as e:
                        # 检查当前URL，即使超时也可能已经成功
                        if "https://channels.weixin.qq.com/platform/post/list" in page.url:
                            tencent_logger.success(f"  [-]账号 {account_name} 视频发布成功")
                            return
                        
                        tencent_logger.info(f"  [-]账号 {account_name} 视频正在发布中...")
                        await asyncio.sleep(2)  # 增加等待时间
                        retry_count += 1
                        
            except Exception as e:
                tencent_logger.error(f"  [-]账号 {account_name} 发布出错: {str(e)}")
                await asyncio.sleep(2)
                retry_count += 1
        
        tencent_logger.error(f"  [-]账号 {account_name} 发布超时")

    async def add_title_tags(self, page, account_name: str):
        """
        添加标题、话题和好友标记
        Args:
            page: 浏览器页面
            account_name: 账号名称
        """
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
        """
        添加合集
        Args:
            page: 浏览器页面
        """
        collection_elements = page.get_by_text("添加到合集").locator("xpath=following-sibling::div").locator(
            '.option-list-wrap > div')

        if await collection_elements.count() > 1:
            await page.get_by_text("添加到合集").locator("xpath=following-sibling::div").click()
            await collection_elements.first.click()

    async def add_original(self, page):
        """
        添加原创
        Args:
            page: 浏览器页面
        """
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
    
    async def add_location(self, page, location: str = None, account_name: str = None) -> None:
        """
        添加位置信息
        
        Args:
            page: playwright页面对象
            location: 位置名称，如果为None则选择不显示位置
            account_name: 账号名称
        """
        try:
            # 点击位置选择区域
            position_display = page.locator('div.position-display-wrap')
            if await position_display.count():
                await position_display.click()
                
                if location is None:
                    # 选择"不显示位置"选项
                    no_location = page.locator('div.location-item:has-text("不显示位置")')
                    if await no_location.count():
                        await no_location.click()
                        tencent_logger.info(f"[{account_name}] 已设置为不显示位置")
                else:
                    # 等待位置搜索框出现
                    search_input = page.locator('input.weui-desktop-form__input[placeholder*="搜索"]')
                    await search_input.wait_for()
                    
                    # 输入位置并等待
                    await search_input.fill(location)
                    await asyncio.sleep(1)  # 等待搜索结果
                    
                    # 选择第一个搜索结果
                    first_result = page.locator('div.location-item').first
                    if await first_result.count():
                        await first_result.click()
                        tencent_logger.info(f"[{account_name}] 成功添加位置: {location}")
                    else:
                        tencent_logger.warning(f"[{account_name}] 未找到位置: {location}")
                
        except Exception as e:
            tencent_logger.error(f"[{account_name}] 添加位置失败: {str(e)}")

    @staticmethod
    async def get_account_info(page) -> dict:
        """
        获取账号信息的通用方法，使用多重备选策略
        
        Args:
            page: playwright页面对象
        
        Returns:
            dict: 包含账号信息的字典
        """
        try:
            # 多重备选选择器，按优先级排序
            nickname_selectors = [
                'h2.finder-nickname',  # 基础类选择器
                '.finder-nickname',    # 简单类选择器
                'div:has-text("视频号ID") >> xpath=../h2',  # 使用相邻元素定位
                'h2:has-text("视频号")',  # 使用文本内容定位
            ]
            
            # 尝试所有选择器直到找到元素
            nickname = None
            for selector in nickname_selectors:
                element = page.locator(selector).first
                if await element.count():
                    nickname = await element.inner_text()
                    break
            
            if not nickname:
                raise Exception("无法获取账号昵称")
            
            # 获取其他账号信息（可选）
            info = {
                'nickname': nickname,
                'id': await page.locator('#finder-uid-copy').get_attribute('data-clipboard-text') or '',
                'video_count': await page.locator('.finder-content-info .finder-info-num').first.inner_text() or '0',
                'follower_count': await page.locator('.second-info .finder-info-num').inner_text() or '0'
            }
            
            return info
            
        except Exception as e:
            tencent_logger.error(f"获取账号信息失败: {str(e)}")
            return None


async def batch_cookie_auth(cookie_files: list) -> dict:
    """
    并发验证多个账号的cookie有效性
    
    Args:
        cookie_files: cookie文件路径列表
    
    Returns:
        dict: {cookie_file: (is_valid, account_name)}
        例如：{
            'path/to/cookie1.json': (True, '账号1'),
            'path/to/cookie2.json': (False, '账号2')
        }
    """
    async def verify_single_cookie(cookie_file):
        account_name = Path(cookie_file).stem
        is_valid = await cookie_auth(cookie_file)
        return cookie_file, (is_valid, account_name)
    
    # 创建所有cookie验证任务
    tasks = [verify_single_cookie(file) for file in cookie_files]
    
    # 并发执行所有验证任务
    results = await asyncio.gather(*tasks)
    
    # 转换为字典格式返回
    return dict(results)
