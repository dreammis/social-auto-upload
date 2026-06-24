import re
from datetime import datetime
import patchright
from patchright.async_api import Playwright, async_playwright
import os
import asyncio
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from uploader.tk_uploader.tk_config import Tk_Locator
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import tiktok_logger

async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto('https://www.tiktok.com/tiktokstudio/upload?lang=en')
        await page.wait_for_load_state('networkidle')
        try:
            select_elements = await page.query_selector_all('select')
            for element in select_elements:
                class_name = await element.get_attribute('class')
                if re.match('tiktok-.*-SelectFormContainer.*', class_name):
                    tiktok_logger.error('[+] cookie expired')
                    return False
            tiktok_logger.success('[+] cookie valid')
            return True
        except (patchright.async_api.Error, OSError, asyncio.TimeoutError, RuntimeError):
            tiktok_logger.success('[+] cookie valid')
            return True

async def tiktok_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, 'tk_uploader')
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            return False
        tiktok_logger.info('[+] cookie file is not existed or expired. Now open the browser auto. Please login with your way(gmail phone, whatever, the cookie file will generated after login')
        await get_tiktok_cookie(account_file)
    return True

async def get_tiktok_cookie(account_file):
    async with async_playwright() as playwright:
        options = {'args': ['--lang en-GB'], 'headless': LOCAL_CHROME_HEADLESS}
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto('https://www.tiktok.com/login?lang=en')
        await page.pause()
        await context.storage_state(path=account_file)

class TiktokVideo(object):

    def __init__(self, title, file_path, tags, publish_date, account_file, thumbnail_path=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.thumbnail_path = thumbnail_path
        self.account_file = account_file
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.locator_base = None

    async def set_schedule_time(self, page, publish_date):
        schedule_input_element = self.locator_base.get_by_label('Schedule')
        await schedule_input_element.wait_for(state='visible')
        await schedule_input_element.click(force=True)
        if await self.locator_base.locator('div.TUXButton-content >> text=Allow').count():
            await self.locator_base.locator('div.TUXButton-content >> text=Allow').click()
        scheduled_picker = self.locator_base.locator('div.scheduled-picker')
        await scheduled_picker.locator('div.TUXInputBox').nth(1).click()
        calendar_month = await self.locator_base.locator('div.calendar-wrapper span.month-title').inner_text()
        n_calendar_month = datetime.strptime(calendar_month, '%B').month
        schedule_month = publish_date.month
        if n_calendar_month != schedule_month:
            if n_calendar_month < schedule_month:
                arrow = self.locator_base.locator('div.calendar-wrapper span.arrow').nth(-1)
            else:
                arrow = self.locator_base.locator('div.calendar-wrapper span.arrow').nth(0)
            await arrow.click()
        valid_days_locator = self.locator_base.locator('div.calendar-wrapper span.day.valid')
        valid_days = await valid_days_locator.count()
        for i in range(valid_days):
            day_element = valid_days_locator.nth(i)
            text = await day_element.inner_text()
            if text.strip() == str(publish_date.day):
                await day_element.click()
                break
        await scheduled_picker.locator('div.TUXInputBox').nth(0).click()
        hour_str = publish_date.strftime('%H')
        correct_minute = int(publish_date.minute / 5)
        minute_str = f'{correct_minute:02d}'
        hour_selector = f"span.tiktok-timepicker-left:has-text('{hour_str}')"
        minute_selector = f"span.tiktok-timepicker-right:has-text('{minute_str}')"
        await page.wait_for_timeout(1000)
        await self.locator_base.locator(hour_selector).click()
        await page.wait_for_timeout(1000)
        await self.locator_base.locator(minute_selector).click()

    async def handle_upload_error(self, page):
        tiktok_logger.info('video upload error retrying.')
        select_file_button = self.locator_base.locator('button[aria-label="Select file"]')
        async with page.expect_file_chooser() as fc_info:
            await select_file_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path)
        context = await browser.new_context(storage_state=f'{self.account_file}')
        page = await context.new_page()
        await self.change_language(page)
        await page.goto('https://www.tiktok.com/tiktokstudio/upload')
        tiktok_logger.info(f'[+]Uploading-------{self.title}.mp4')
        await page.wait_for_url('https://www.tiktok.com/tiktokstudio/upload', timeout=10000)
        try:
            await page.wait_for_selector('iframe[data-tt="Upload_index_iframe"], div.upload-container', timeout=10000)
            tiktok_logger.info('Either iframe or div appeared.')
        except (patchright.async_api.Error, OSError, asyncio.TimeoutError) as e:
            tiktok_logger.error('Neither iframe nor div appeared within the timeout.')
        await self.choose_base_locator(page)
        upload_button = self.locator_base.locator('button:has-text("Select video"):visible')
        await upload_button.wait_for(state='visible')
        async with page.expect_file_chooser() as fc_info:
            await upload_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)
        await self.add_title_tags(page)
        await self.detect_upload_status(page)
        if self.thumbnail_path:
            tiktok_logger.info(f'[+] Uploading thumbnail file {self.title}.png')
            await self.upload_thumbnails(page)
        if self.publish_date != 0:
            await self.set_schedule_time(page, self.publish_date)
        await self.click_publish(page)
        tiktok_logger.success(f'video_id: {await self.get_last_video_id(page)}')
        await context.storage_state(path=f'{self.account_file}')
        tiktok_logger.info('  [-] update cookie！')
        await asyncio.sleep(2)
        await context.close()
        await browser.close()

    async def add_title_tags(self, page):
        editor_locator = self.locator_base.locator('div.public-DraftEditor-content')
        await editor_locator.click()
        await page.keyboard.press('End')
        await page.keyboard.press('Control+A')
        await page.keyboard.press('Delete')
        await page.keyboard.press('End')
        await page.wait_for_timeout(1000)
        await page.keyboard.insert_text(self.title)
        await page.wait_for_timeout(1000)
        await page.keyboard.press('End')
        await page.keyboard.press('Enter')
        for index, tag in enumerate(self.tags, start=1):
            tiktok_logger.info('Setting the %s tag' % index)
            await page.keyboard.press('End')
            await page.wait_for_timeout(1000)
            await page.keyboard.insert_text('#' + tag + ' ')
            await page.keyboard.press('Space')
            await page.wait_for_timeout(1000)
            await page.keyboard.press('Backspace')
            await page.keyboard.press('End')

    async def upload_thumbnails(self, page):
        await self.locator_base.locator('.cover-container').click()
        await self.locator_base.locator('.cover-edit-container >> text=Upload cover').click()
        async with page.expect_file_chooser() as fc_info:
            await self.locator_base.locator('.upload-image-upload-area').click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(self.thumbnail_path)
        await self.locator_base.locator('div.cover-edit-panel:not(.hide-panel)').get_by_role('button', name='Confirm').click()
        await page.wait_for_timeout(3000)

    async def change_language(self, page):
        await page.goto('https://www.tiktok.com')
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_selector('[data-e2e="nav-more-menu"]')
        if await page.locator('[data-e2e="nav-more-menu"]').text_content() == 'More':
            return
        await page.locator('[data-e2e="nav-more-menu"]').click()
        await page.locator('[data-e2e="language-select"]').click()
        await page.locator('#creator-tools-selection-menu-header >> text=English (US)').click()

    async def click_publish(self, page):
        success_flag_div = 'div.common-modal-confirm-modal'
        while True:
            try:
                publish_button = self.locator_base.locator('div.button-group button').nth(0)
                if await publish_button.count():
                    await publish_button.click()
                await page.wait_for_url('https://www.tiktok.com/tiktokstudio/content', timeout=3000)
                tiktok_logger.success('  [-] video published success')
                break
            except (patchright.async_api.Error, OSError, asyncio.TimeoutError) as e:
                tiktok_logger.exception(f'  [-] Exception: {e}')
                tiktok_logger.info('  [-] video publishing')
                await asyncio.sleep(0.5)

    async def get_last_video_id(self, page):
        await page.wait_for_selector('div[data-tt="components_PostTable_Container"]')
        video_list_locator = self.locator_base.locator('div[data-tt="components_PostTable_Container"] div[data-tt="components_PostInfoCell_Container"] a')
        if await video_list_locator.count():
            first_video_obj = await video_list_locator.nth(0).get_attribute('href')
            video_id = re.search('video/(\\d+)', first_video_obj).group(1) if first_video_obj else None
            return video_id

    async def detect_upload_status(self, page):
        while True:
            try:
                if await self.locator_base.locator('div.button-group > button >> text=Post').get_attribute('disabled') is None:
                    tiktok_logger.info('  [-]video uploaded.')
                    break
                else:
                    tiktok_logger.info('  [-] video uploading...')
                    await asyncio.sleep(2)
                    if await self.locator_base.locator('button[aria-label="Select file"]').count():
                        tiktok_logger.info('  [-] found some error while uploading now retry...')
                        await self.handle_upload_error(page)
            except (patchright.async_api.Error, OSError, asyncio.TimeoutError):
                tiktok_logger.info('  [-] video uploading...')
                await asyncio.sleep(2)

    async def choose_base_locator(self, page):
        if await page.locator('iframe[data-tt="Upload_index_iframe"]').count():
            self.locator_base = page.frame_locator(Tk_Locator.tk_iframe)
        else:
            self.locator_base = page.locator(Tk_Locator.default)

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)