# -*- coding: utf-8 -*-
import re
from datetime import datetime

from playwright.async_api import Playwright, async_playwright
import time
import os
import asyncio
from tk_uploader.tk_config import Tk_Locator
from utils.files_times import get_absolute_path


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://www.tiktok.com/creator-center/content")
        await page.wait_for_load_state('networkidle')
        try:
            # 选择所有的 select 元素
            select_elements = await page.query_selector_all('select')
            for element in select_elements:
                class_name = await element.get_attribute('class')
                # 使用正则表达式匹配特定模式的 class 名称
                if re.match(r'tiktok-.*-SelectFormContainer.*', class_name):
                    print("[+] cookie expired")
                    return False
            print("[+] cookie valid")
            return True
        except:
            print("[+] cookie valid")
            return True


async def tiktok_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, "tk_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            return False
        print('[+] cookie file is not existed or expired. Now open the browser auto. Please login with your way(gmail phone, whatever, the cookie file will generated after login')
        await get_tiktok_cookie(account_file)
    return True


async def get_tiktok_cookie(account_file):
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB',
            ],
            'headless': False,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.firefox.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://www.tiktok.com/creator-center/content")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


class TiktokVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file

    async def set_schedule_time(self, page, publish_date):
        print("click schedule")
        schedule_input_element = page.frame_locator(Tk_Locator.tk_iframe).locator('div.scheduled-container input')
        await schedule_input_element.wait_for(state='visible')  # 确保按钮可见

        await page.frame_locator(Tk_Locator.tk_iframe).locator('div.scheduled-container input').click()
        scheduled_picker = page.frame_locator(Tk_Locator.tk_iframe).locator('div.scheduled-picker')
        await scheduled_picker.locator('div.TUXInputBox').nth(0).click()

        calendar_month = await page.frame_locator(Tk_Locator.tk_iframe).locator('div.calendar-wrapper span.month-title').inner_text()

        n_calendar_month = datetime.strptime(calendar_month, '%B').month

        schedule_month = publish_date.month

        if n_calendar_month != schedule_month:
            if n_calendar_month < schedule_month:
                arrow = page.frame_locator(Tk_Locator.tk_iframe).locator('div.calendar-wrapper span.arrow').nth(-1)
            else:
                arrow = page.frame_locator(Tk_Locator.tk_iframe).locator('div.calendar-wrapper span.arrow').nth(0)
            await arrow.click()

        # day set
        valid_days_locator = page.frame_locator(Tk_Locator.tk_iframe).locator(
            'div.calendar-wrapper span.day.valid')
        valid_days = await valid_days_locator.count()
        for i in range(valid_days):
            day_element = valid_days_locator.nth(i)
            text = await day_element.inner_text()
            if text.strip() == str(publish_date.day):
                await day_element.click()
                break
        # time set
        await page.frame_locator(Tk_Locator.tk_iframe).locator("div.time-picker-container").click()

        hour_str = publish_date.strftime("%H")
        correct_minute = int(publish_date.minute / 5)
        minute_str = f"{correct_minute:02d}"

        hour_selector = f"span.tiktok-timepicker-left:has-text('{hour_str}')"
        minute_selector = f"span.tiktok-timepicker-right:has-text('{minute_str}')"

        # pick hour first
        await page.frame_locator(Tk_Locator.tk_iframe).locator(hour_selector).click()
        # click time button again
        # 等待某个特定的元素出现或状态变化，表明UI已更新
        await page.wait_for_timeout(1000)  # 等待500毫秒
        await page.frame_locator(Tk_Locator.tk_iframe).locator("div.time-picker-container").click()
        # pick minutes after
        await page.frame_locator(Tk_Locator.tk_iframe).locator(minute_selector).click()

        # click title to remove the focus.
        await page.frame_locator(Tk_Locator.tk_iframe).locator("h1:has-text('Upload video')").click()

    async def handle_upload_error(self, page):
        print("video upload error retrying.")
        select_file_button = page.frame_locator(Tk_Locator.tk_iframe).locator('button[aria-label="Select file"]')
        async with page.expect_file_chooser() as fc_info:
            await select_file_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        browser = await playwright.firefox.launch(headless=False)
        context = await browser.new_context(storage_state=f"{self.account_file}")

        page = await context.new_page()

        await page.goto("https://www.tiktok.com/creator-center/upload")
        print('[+]Uploading-------{}.mp4'.format(self.title))

        await page.wait_for_url("https://www.tiktok.com/creator-center/upload", timeout=1500)
        await page.wait_for_selector('iframe[data-tt="Upload_index_iframe"]')
        upload_button = page.frame_locator(Tk_Locator.tk_iframe).locator(
            'button:has-text("Select video"):visible')
        await upload_button.wait_for(state='visible')  # 确保按钮可见

        async with page.expect_file_chooser() as fc_info:
            await upload_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)

        await self.add_title_tags(page)
        # detact upload status
        await self.detact_upload_status(page)
        if self.publish_date != 0:
            await self.set_schedule_time(page, self.publish_date)

        await self.click_publish(page)

        await context.storage_state(path=f"{self.account_file}")  # save cookie
        print('  [-] update cookie！')
        await asyncio.sleep(2)  # close delay for look the video status
        # close all
        await context.close()
        await browser.close()

    async def add_title_tags(self, page):

        await page.frame_locator(Tk_Locator.tk_iframe).locator(
            'div.public-DraftEditor-content').click()
        time.sleep(2)
        await page.keyboard.press("Control+KeyA")
        time.sleep(2)
        await page.keyboard.press("Delete")

        # title part
        await page.keyboard.type(self.title)
        await page.keyboard.press("Enter")

        # tag part
        for index, tag in enumerate(self.tags, start=1):
            print("Setting the %s tag" % index)
            await page.keyboard.type("#" + tag)
            await asyncio.sleep(1)
            await page.keyboard.press("Space")
            # if await page.frame_locator(Tk_Locator.tk_iframe).locator('div.mentionSuggestions').count():
            #     await page.frame_locator(Tk_Locator.tk_iframe).locator('div.mentionSuggestions- > div').nth(0).click()

        print(f"success add hashtag: {len(self.tags)}")

    async def click_publish(self, page):
        success_flag_div = '#\\:r9\\:'
        while True:
            try:
                publish_button = page.frame_locator(Tk_Locator.tk_iframe).locator('div.btn-post')
                if await publish_button.count():
                    await publish_button.click()

                await page.frame_locator(Tk_Locator.tk_iframe).locator(success_flag_div).wait_for(state="visible", timeout=1500)
                print("  [-] video published success")
                break
            except Exception as e:
                if await page.frame_locator(Tk_Locator.tk_iframe).locator(success_flag_div).count():
                    print("  [-]video published success")
                    break
                else:
                    print(f"  [-] Exception: {e}")
                    print("  [-] video publishing")
                    await page.screenshot(full_page=True)
                    await asyncio.sleep(0.5)

    async def detact_upload_status(self, page):
        while True:
            try:
                if await page.frame_locator(Tk_Locator.tk_iframe).locator('div.btn-post > button').get_attribute("disabled") is None:
                    print("  [-]video uploaded.")
                    break
                else:
                    print("  [-] video uploading...")
                    await asyncio.sleep(2)
                    if await page.frame_locator(Tk_Locator.tk_iframe).locator('button[aria-label="Select file"]').count():
                        print("  [-] found some error while uploading now retry...")
                        await self.handle_upload_error(page)
            except:
                print("  [-] video uploading...")
                await asyncio.sleep(2)

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

