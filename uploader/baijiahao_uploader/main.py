from datetime import datetime
from pathlib import Path
from patchright.async_api import Playwright, async_playwright, Page
import patchright
import os
import time
import asyncio
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from uploader.common import (
    _all_login_markers_hidden,
    _build_login_result,
    _check_login_markers,
    _emit_qrcode_callback,
    _msg,
)
from utils.base_social_media import set_init_script
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file
from utils.login_qrcode import save_data_url_image
from utils.log import baijiahao_logger
from utils.network import async_retry
BAIJIAHAO_LOGIN_URL = 'https://baijiahao.baidu.com/builder/theme/bjh/login'
BAIJIAHAO_HOME_URL = 'https://baijiahao.baidu.com/builder/rc/home'

async def _extract_baijiahao_qrcode_src(page: Page) -> str:
    qrcode_img = page.locator('div[class*="qrcode"] img, div[class*="qr"] img, .qr-code-img').first
    if not await qrcode_img.count():
        qrcode_img = page.locator('img[alt*="二维码"], img[alt*="QR"], img[alt*="qr"]').first
    if not await qrcode_img.count():
        qrcode_img = page.locator('img[src*="passport.baidu.com"], img[src*="qrcode"]').first
    await qrcode_img.wait_for(state='visible', timeout=30000)
    src = await qrcode_img.get_attribute('src')
    if not src:
        raise RuntimeError('未获取到百家号登录二维码地址')
    return src

async def _open_baijiahao_login_modal(page: Page) -> None:
    """Click to open the Baidu Passport login modal if it is not already visible."""
    login_triggers = [page.get_by_text('登录', exact=True).first, page.get_by_role('button', name='登录').first, page.locator('a:has-text("登录")').first, page.locator('button:has-text("登录")').first]
    for trigger in login_triggers:
        try:
            if await trigger.count() and await trigger.is_visible():
                await trigger.click()
                await asyncio.sleep(2)
                return
        except (patchright.async_api.Error, OSError, asyncio.TimeoutError):
            continue
    baijiahao_logger.info(_msg('🧍', '未找到登录按钮，假设二维码已在页面上'))

async def _save_baijiahao_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None=None, qrcode_callback=None) -> dict:
    qrcode_src = await _extract_baijiahao_qrcode_src(page)
    qrcode_path = save_data_url_image(qrcode_src, build_login_qrcode_path(account_file))
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            baijiahao_logger.info(_msg('🧹', f'临时二维码文件已清理: {previous_qrcode_path}'))
    baijiahao_logger.info(_msg('🖼️', f'二维码已经准备好啦，已保存到: {qrcode_path}'))
    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, '百度APP')
    else:
        baijiahao_logger.warning(_msg('😵', f'终端没法完整显示二维码，请打开 {qrcode_path} 扫码'))
    qrcode_info = {'image_path': str(qrcode_path), 'image_data_url': qrcode_src}
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info

async def _is_baijiahao_login_completed(page: Page) -> bool:
    current_url = page.url
    if 'baijiahao.baidu.com/builder/rc/home' in current_url:
        return True
    if 'baijiahao.baidu.com/builder/rc/edit' in current_url:
        return True
    # 如果页面还在 baijiahao.baidu.com 域下但没有登录文本，说明已登录
    if 'baijiahao.baidu.com' in current_url and await _all_login_markers_hidden(page, ['注册/登录百家号']):
        return True
    return False

async def _wait_for_baijiahao_login(page: Page, account_file: str, qrcode_info: dict, qrcode_callback=None, poll_interval: int=3, max_checks: int=100) -> dict:
    qrcode_path = Path(qrcode_info['image_path'])
    for _ in range(max_checks):
        if await _is_baijiahao_login_completed(page):
            baijiahao_logger.info(_msg('🥳', f'扫码成功，已经跳转到登录后页面: {page.url}'))
            return _build_login_result(True, 'success', '百家号扫码登录成功', account_file, qrcode_info, page.url)
        await asyncio.sleep(poll_interval)
    return _build_login_result(False, 'timeout', '等待百家号扫码登录超时', account_file, qrcode_info, page.url)

async def baijiahao_cookie_gen(account_file, qrcode_callback=None, headless: bool=LOCAL_CHROME_HEADLESS, poll_interval: int=3, max_checks: int=100):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless, args=['--lang en-GB'])
        context = await browser.new_context()
        context = await set_init_script(context)
        qrcode_path = None
        result = _build_login_result(False, 'failed', '百家号登录失败', account_file)
        try:
            page = await context.new_page()
            await page.goto(BAIJIAHAO_LOGIN_URL)
            await page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(2)
            await _open_baijiahao_login_modal(page)
            qrcode_info = await _save_baijiahao_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info['image_path'])
            baijiahao_logger.info(_msg('🧍', '请扫码，正在等待百家号登录完成'))
            result = await _wait_for_baijiahao_login(page, account_file, qrcode_info, qrcode_callback=qrcode_callback, poll_interval=poll_interval, max_checks=max_checks)
            if result['success']:
                await asyncio.sleep(2)
                await context.storage_state(path=account_file)
                if not await cookie_auth(account_file):
                    result = _build_login_result(False, 'cookie_invalid', '百家号扫码流程结束，但 cookie 校验失败', account_file, qrcode_info, page.url)
        except (patchright.async_api.Error, OSError, asyncio.TimeoutError, RuntimeError) as exc:
            result = _build_login_result(False, 'failed', str(exc), account_file, current_url=page.url if 'page' in locals() else '')
        finally:
            if remove_qrcode_file(qrcode_path):
                baijiahao_logger.info(_msg('🧹', f'临时二维码文件已清理: {qrcode_path}'))
            if not result['success']:
                baijiahao_logger.error(_msg('😢', f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()
        return result

async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto('https://baijiahao.baidu.com/builder/rc/home')
        await page.wait_for_timeout(timeout=5000)
        if await _check_login_markers(page, ['注册/登录百家号']):
            baijiahao_logger.error('等待5秒 cookie 失效')
            return False
        else:
            baijiahao_logger.success('[+] cookie 有效')
            return True

async def baijiahao_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool=LOCAL_CHROME_HEADLESS):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, 'cookie_invalid', 'cookie文件不存在或已失效', account_file)
            return result if return_detail else False
        baijiahao_logger.info(_msg('🥹', 'cookie失效，准备打开浏览器扫码登录百家号'))
        result = await baijiahao_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result['success']
    result = _build_login_result(True, 'cookie_valid', 'cookie有效', account_file)
    return result if return_detail else True

class BaiJiaHaoVideo(object):

    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, proxy_setting=None):
        self.title = title
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
        publish_date_day = f'{publish_date.month}月{publish_date.day}日' if publish_date.day > 9 else f'{publish_date.month}月0{publish_date.day}日'
        publish_date_hour = f'{publish_date.hour}点'
        publish_date_min = f'{publish_date.minute}分'
        await page.wait_for_selector('div.select-wrap', timeout=5000)
        for _ in range(3):
            try:
                await page.locator('div.select-wrap').nth(0).click()
                await page.wait_for_selector('div.rc-virtual-list  div.cheetah-select-item', timeout=5000)
                break
            except (patchright.async_api.Error, OSError, asyncio.TimeoutError):
                await page.locator('div.select-wrap').nth(0).click()
        await page.wait_for_timeout(2000)
        await page.locator(f'div.rc-virtual-list  div.cheetah-select-item >> text={publish_date_day}').click()
        await page.wait_for_timeout(2000)
        for _ in range(3):
            try:
                await page.locator('div.select-wrap').nth(1).click()
                await page.wait_for_selector('div.rc-virtual-list div.rc-virtual-list-holder-inner:visible', timeout=5000)
                break
            except (patchright.async_api.Error, OSError, asyncio.TimeoutError):
                await page.locator('div.select-wrap').nth(1).click()
        await page.wait_for_timeout(2000)
        current_choice_hour = await page.locator('div.rc-virtual-list:visible div.cheetah-select-item-option').count()
        await page.wait_for_timeout(2000)
        target_hour_index = min(publish_date.hour, current_choice_hour - 1)
        await page.locator('div.rc-virtual-list:visible div.cheetah-select-item-option').nth(target_hour_index).click()
        await page.wait_for_timeout(2000)
        await page.locator('button >> text=定时发布').click()

    async def handle_upload_error(self, page):
        baijiahao_logger.error('视频出错了，重新上传中')
        await page.locator("div[class^='video-main-container'] input").set_input_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path, proxy=self.proxy_setting)
        context = await browser.new_context(storage_state=f'{self.account_file}', user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.4324.150 Safari/537.36')
        await context.grant_permissions(['geolocation'])
        page = await context.new_page()
        await page.goto('https://baijiahao.baidu.com/builder/rc/edit?type=videoV2', timeout=60000)
        baijiahao_logger.info(f'正在上传-------{self.title}.mp4')
        baijiahao_logger.info('正在打开主页...')
        await page.wait_for_url('https://baijiahao.baidu.com/builder/rc/edit?type=videoV2', timeout=60000)
        await page.locator("div[class^='video-main-container'] input").set_input_files(self.file_path)
        while True:
            try:
                await page.wait_for_selector('div#formMain:visible')
                break
            except (patchright.async_api.Error, OSError, asyncio.TimeoutError):
                baijiahao_logger.info('正在等待进入视频发布页面...')
                await asyncio.sleep(0.1)
        await asyncio.sleep(1)
        baijiahao_logger.info('正在填充标题和话题...')
        await self.add_title_tags(page)
        upload_status = await self.uploading_video(page)
        if not upload_status:
            baijiahao_logger.error(f'发现上传出错了... 文件:{self.file_path}')
            raise
        while True:
            baijiahao_logger.info('正在确认封面完成, 准备去点击定时/发布...')
            if await page.locator('div.cheetah-spin-container img').count():
                baijiahao_logger.info('封面已完成，点击定时/发布...')
                break
            else:
                baijiahao_logger.info('等待封面生成...')
                await asyncio.sleep(3)
        await self.publish_video(page, self.publish_date)
        await page.wait_for_timeout(2000)
        if await page.locator('div.passMod_dialog-container >> text=百度安全验证:visible').count():
            baijiahao_logger.error('出现验证，退出')
            raise Exception('出现验证，退出')
        await page.wait_for_url('https://baijiahao.baidu.com/builder/rc/clue**', timeout=5000)
        baijiahao_logger.success('视频发布成功')
        await context.storage_state(path=self.account_file)
        baijiahao_logger.info('cookie更新完毕！')
        await asyncio.sleep(2)
        await context.close()
        await browser.close()

    @async_retry(timeout=300)
    async def uploading_video(self, page):
        while True:
            upload_failed = await page.locator('div .cover-overlay:has-text("上传失败")').count()
            if upload_failed:
                baijiahao_logger.error('发现上传出错了...')
                return False
            uploading = await page.locator('div .cover-overlay:has-text("上传中")').count()
            if uploading:
                baijiahao_logger.info('正在上传视频中...')
                await asyncio.sleep(2)
                continue
            if not uploading and (not upload_failed):
                baijiahao_logger.success('视频上传完毕')
                return True

    async def set_schedule_publish(self, page, publish_date):
        while True:
            schedule_element = page.locator('div.op-btn-outter-content >> text=定时发布').locator('..').locator('button')
            try:
                await schedule_element.click()
                await page.wait_for_selector('div.select-wrap:visible', timeout=3000)
                await page.wait_for_timeout(timeout=2000)
                baijiahao_logger.info('开始点击发布定时...')
                await self.set_schedule_time(page, publish_date)
                break
            except (patchright.async_api.Error, OSError, asyncio.TimeoutError) as e:
                baijiahao_logger.error(f'定时发布失败: {e}')
                raise

    @async_retry(timeout=300)
    async def publish_video(self, page: Page, publish_date):
        if publish_date != 0:
            await self.set_schedule_publish(page, publish_date)
        else:
            await self.direct_publish(page)

    async def direct_publish(self, page):
        try:
            publish_button = page.locator('button >> text=发布')
            if await publish_button.count():
                await publish_button.click()
        except (patchright.async_api.Error, OSError, asyncio.TimeoutError) as e:
            baijiahao_logger.error(f'直接发布视频失败: {e}')
            raise

    async def add_title_tags(self, page):
        title_container = page.get_by_placeholder('添加标题获得更多推荐')
        if len(self.title) <= 8:
            self.title += ' 你不知道的'
        await title_container.fill(self.title[:30])

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def ai2video(self, playwright: Playwright) -> None:
        browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path, proxy=self.proxy_setting)
        context = await browser.new_context(viewport={'width': 1600, 'height': 900}, storage_state=f'{self.account_file}', user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.4324.150 Safari/537.36')
        await context.grant_permissions(['geolocation'])
        page = await context.new_page()
        await page.goto('https://aigc.baidu.com/make', timeout=60000)
        baijiahao_logger.info('正在打开主页...')
        await page.wait_for_url('https://aigc.baidu.com/make', timeout=60000)
        await page.locator('div.rounded-lg.border:has-text("全网")').click()
        await asyncio.sleep(1)
        now = datetime.now()
        datetime_str = now.strftime('%Y%m%d%H%M')
        processed_key = 'ai2video_processed_titles'
        batch_key = f'ai2video_{datetime_str}'
        await page.evaluate(f'\n                   if (!localStorage.getItem("{processed_key}")) {{\n                       localStorage.setItem("{processed_key}", JSON.stringify([]));                   \n                   }}\n                   if (!localStorage.getItem("{batch_key}")) {{\n                       localStorage.setItem("{batch_key}", JSON.stringify([]));                   \n                   }}\n               ')
        container_selector = '.overflow-auto.flex-grow.h-0.saas-scrollbar.mt\\-\\[-4px\\].pl\\-\\[24px\\].pr\\-\\[10px\\].pb\\-\\[18px\\]'
        news_items = await page.locator(container_selector).locator('div.py\\-\\[6px\\].group.cursor-pointer').all()
        for item in news_items:
            try:
                title_elem = item.locator('div.flex.text-gray-darker.items-center.relative.pr\\-\\[56px\\] > span')
                title = await title_elem.text_content()
                if not title:
                    continue
                is_processed = await page.evaluate(f'title => {{\n                               const processedList = JSON.parse(localStorage.getItem("{processed_key}") || "[]");\n                               return processedList.includes(title);\n                           }}', title)
                if is_processed:
                    print(f'[跳过] {title}')
                    continue
                await item.hover()
                button = item.locator('button:has-text("生成文案")')
                await button.click()
                print(f'[点击] {title}')
                print(f'[等待完成] {title}')
                print(f'[开始监听] 一键成片按钮')
                should_exit_while_loop = False
                while True:
                    one_key_button = page.locator("button:has-text('一键成片')")
                    if await one_key_button.count() > 0:
                        is_disabled = await one_key_button.get_attribute('disabled')
                        if is_disabled is None:
                            print(f'[发现可点击按钮] 一键成片')
                            await one_key_button.click()
                            print(f'[检查] 是否出现温馨提示窗口')
                            await page.wait_for_timeout(2000)
                            try:
                                tip_window = page.locator("div:has-text('温馨提示') >> visible=true")
                                if await tip_window.count() > 0:
                                    print(f'[发现] 温馨提示窗口')
                                    know_button = page.locator("button:has-text('知道了')")
                                    if await know_button.count() > 0:
                                        try:
                                            await know_button.click(timeout=5000)
                                            print(f'[已点击] 知道了按钮')
                                        except (patchright.async_api.Error, OSError, asyncio.TimeoutError) as e:
                                            print(f'[警告] 点击知道了按钮时出错: {str(e)}')
                                    else:
                                        print(f'[警告] 未找到知道了按钮')
                                else:
                                    print(f'[信息] 未出现温馨提示窗口，继续执行')
                            except (patchright.async_api.Error, OSError, asyncio.TimeoutError) as e:
                                print(f'[警告] 处理温馨提示窗口时出错: {str(e)}')
                            print(f"[开始记录] 准备将标题 '{title}' 记录到LocalStorage")
                            await page.evaluate(f'\n                                        (title, processedKey, batchKey) => {{\n                                            // 更新已处理列表\n                                            const processedList = JSON.parse(localStorage.getItem(processedKey) || "[]");\n                                            if (!processedList.includes(title)) {{\n                                                processedList.push(title);\n                                                localStorage.setItem(processedKey, JSON.stringify(processedList));\n                                            }}\n\n                                            // 更新当前批次记录\n                                            const batchList = JSON.parse(localStorage.getItem(batchKey) || "[]");\n                                            if (!batchList.includes(title)) {{\n                                                batchList.push(title);\n                                                localStorage.setItem(batchKey, JSON.stringify(batchList));\n                                            }}\n                                        }}\n                                        ', title, processed_key, batch_key)
                            print(f"[记录完成] 标题 '{title}' 已成功记录到LocalStorage")
                            print(f'[记录完成] {title}')
                            print(f'[监听] 等待新标签页打开')
                            current_pages = context.pages
                            current_page_count = len(current_pages)
                            new_page = None
                            max_wait_time = 10
                            start_time = time.time()
                            while time.time() - start_time < max_wait_time:
                                pages = context.pages
                                if len(pages) > current_page_count:
                                    new_page = pages[-1]
                                    print(f'[发现] 新标签页已打开')
                                    break
                                await asyncio.sleep(0.5)
                            if new_page:
                                try:
                                    await new_page.wait_for_load_state('domcontentloaded', timeout=5000)
                                    page_title = await new_page.title()
                                    page_url = new_page.url
                                    print(f'[获取] 标题: {page_title}')
                                    print(f'[获取] URL: {page_url}')
                                    with open('url.txt', 'a', encoding='utf-8') as f:
                                        f.write(f'{page_title}\n{page_url}\n\n')
                                    print(f'[保存] 标题和URL已保存到url.txt')
                                    print(f'[等待] 5秒后将关闭新标签页')
                                    await asyncio.sleep(5)
                                    await new_page.close()
                                    print(f'[关闭] 新标签页已关闭')
                                except (patchright.async_api.Error, OSError, asyncio.TimeoutError) as e:
                                    print(f'[错误] 处理新标签页时出错: {str(e)}')
                                    try:
                                        await new_page.close()
                                        print(f'[关闭] 新标签页已关闭（出错后）')
                                    except (patchright.async_api.Error, OSError, asyncio.TimeoutError):
                                        pass
                            else:
                                print(f'[警告] 未检测到新标签页打开')
                            print(f'[操作] 跳出所有循环，不再处理其他新闻')
                            should_exit_while_loop = True
                            break
                    if should_exit_while_loop:
                        break
                    await page.wait_for_timeout(1000)
                if should_exit_while_loop:
                    print(f'[操作] 跳出for循环，完全结束处理')
                    break
            except (patchright.async_api.Error, OSError, asyncio.TimeoutError) as e:
                print(f'处理新闻时出错: {str(e)}')
                continue
        print(f'[循环完成] 准备关闭浏览器')
        await asyncio.sleep(1000)
        await context.storage_state(path=self.account_file)
        baijiahao_logger.info('cookie更新完毕！')
        await asyncio.sleep(2)
        await context.close()
        await browser.close()

    async def mainAi(self):
        async with async_playwright() as playwright:
            await self.ai2video(playwright)