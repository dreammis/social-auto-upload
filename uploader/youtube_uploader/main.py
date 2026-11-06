# -*- coding: utf-8 -*-
"""YouTube uploader (browser automation via YouTube Studio).

Unlike the other platforms here, YouTube also offers an official Data API. We deliberately
use browser automation instead, because videos uploaded through an *unaudited* API project
are force-locked to private and cannot be made public without passing Google's compliance
audit (which is impractical for personal/single-channel use). Browser automation has no such
restriction and can publish public videos right away, and it matches the cookie-based pattern
used by every other uploader in this project.

Login is interactive (Google account, no QR code): the browser opens, the user signs in, and
the storage_state is saved. Reuse it afterwards for fully unattended uploads.
"""
import asyncio
from pathlib import Path

from patchright.async_api import Page, Playwright, async_playwright

from conf import DEBUG_MODE
try:
    from conf import YT_SCHEDULE_TIMEZONE  # e.g. "London"; None = Studio's "Local Time"
except ImportError:
    YT_SCHEDULE_TIMEZONE = None
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import youtube_logger

try:
    # 国内直连 youtube.com 会超时，且 patchright 启的 chromium 不吃系统代理。
    # 在 conf.py 设 YT_PROXY = "http://127.0.0.1:7890"（本地代理端口）即可；不设则不走代理。
    from conf import YT_PROXY
except Exception:
    YT_PROXY = None

STUDIO_URL = "https://studio.youtube.com"
UPLOAD_URL = "https://www.youtube.com/upload"
VISIBILITY = {"public": "PUBLIC", "unlisted": "UNLISTED", "private": "PRIVATE"}


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _build_login_result(success, status, message, account_file, current_url=""):
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "current_url": current_url,
    }


async def _normal_ua(browser) -> str:
    page = await browser.new_page()
    try:
        return (await page.evaluate("navigator.userAgent")).replace("HeadlessChrome", "Chrome")
    finally:
        await page.close()


async def cookie_auth(account_file) -> bool:
    """登录态是否仍有效：带 cookie 打开 Studio，没被踢到 Google 登录页且进入了频道页即有效。"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        try:
            # Studio won't redirect a "HeadlessChrome" UA to /channel/, so the
            # check always failed. Present the normal Chrome UA instead.
            context = await browser.new_context(storage_state=account_file,
                                                user_agent=await _normal_ua(browser))
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(STUDIO_URL, wait_until="domcontentloaded")
            # was a fixed 3s wait, which sometimes reported a valid login as expired.
            for _ in range(15):
                await page.wait_for_timeout(1000)
                if "/channel/" in page.url or "accounts.google.com" in page.url:
                    break
            url = page.url
            if "accounts.google.com" in url or "/signin" in url.lower():
                return False
            return "/channel/" in url
        except Exception:
            return False
        finally:
            await browser.close()


async def youtube_cookie_gen(account_file, headless: bool = False):
    """交互式登录：开浏览器让用户登录 Google/YouTube，进入频道页后保存 storage_state。"""
    async with async_playwright() as playwright:
        # 登录必须显形，让用户输账号密码/二步验证
        browser = await playwright.chromium.launch(headless=False, channel="chrome")
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto(STUDIO_URL, wait_until="domcontentloaded")
        youtube_logger.info(_msg("🔐", "请在弹出的浏览器里登录 Google / YouTube 账号，登录后会自动保存"))
        # Don't save on the first /channel/ page. Keep the window open so the
        # user can switch to the right brand channel, saving the latest state every few
        # seconds; finish when the user closes the window (or after 15 minutes).
        youtube_logger.info("Sign in, switch to the channel you want in Studio, then CLOSE the window to save.")
        ok = False
        last_channel = ""
        for _ in range(450):  # 15 minutes at 2s
            try:
                if page.is_closed():
                    break
                url = page.url
                if "/channel/" in url:
                    await context.storage_state(path=account_file)
                    ok = True
                    ch = url.split("/channel/")[1].split("/")[0].split("?")[0]
                    if ch != last_channel:
                        last_channel = ch
                        youtube_logger.info(f"Current channel: {ch} (saved)")
            except Exception:
                break
            await asyncio.sleep(2)
        if ok:
            youtube_logger.success(_msg("✅", f"YouTube 登录态已保存: {account_file} channel={last_channel}"))
        else:
            youtube_logger.error(_msg("😵", "等待登录超时，未保存登录态"))
        try:
            await browser.close()
        except Exception:
            pass
        return _build_login_result(ok, "logged_in" if ok else "timeout",
                                   "登录成功" if ok else "登录超时", account_file, page.url)


async def youtube_setup(account_file, handle: bool = False, return_detail: bool = False, headless: bool = False):
    """校验登录态，失效且 handle=True 时拉起交互式登录。"""
    if not Path(account_file).exists() or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "登录态不存在或已失效", account_file)
            return result if return_detail else False
        youtube_logger.info(_msg("🥹", "YouTube 登录态不存在或失效，准备打开浏览器登录"))
        result = await youtube_cookie_gen(account_file, headless=headless)
        return result if return_detail else result["success"]
    result = _build_login_result(True, "cookie_valid", "登录态有效", account_file)
    return result if return_detail else True


async def _dismiss_autocomplete(page: Page):
    """关掉 # 话题 / @ 提及 自动补全下拉浮层（会挡住后续“继续/发布”按钮）。

    先 blur 失焦；若浮层仍可见再补一次 Escape——仅在检测到浮层时才按，
    避免在没有浮层时误关掉整个上传对话框。"""
    try:
        await page.evaluate("() => { const a = document.activeElement; if (a && a.blur) a.blur(); }")
    except Exception:
        pass
    try:
        dropdown = page.locator("tp-yt-iron-dropdown:visible")
        if await dropdown.count() > 0:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(200)
    except Exception:
        pass


async def _fill_editable(page: Page, selector: str, text: str):
    """填 YouTube Studio 的 contenteditable 富文本框（标题/简介），先清空再输入。

    用 fill() 一次性灌入而非逐字 type()：标题/简介里的 # 字符（如 #Shorts）会触发
    YouTube 的话题自动补全下拉浮层；逐字输入会让浮层持续跟随光标弹出、盖住输入框与
    后续“继续/发布”按钮，导致上传流程卡死。fill() 一次性写入不会逐字触发补全。"""
    box = page.locator(selector).first
    await box.wait_for(state="visible", timeout=30000)
    await box.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Delete")
    try:
        await box.fill(text)            # 一次性灌入，不逐字触发 # 话题自动补全
    except Exception:
        await box.type(text, delay=6)   # 个别 contenteditable 不支持 fill 时退回逐字输入
    await page.wait_for_timeout(400)
    await _dismiss_autocomplete(page)   # 收尾关掉可能弹出的补全浮层


async def _click_if_present(page: Page, selector: str, timeout: int = 4000) -> bool:
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=timeout)
        await el.click()
        return True
    except Exception:
        return False


async def _wait_upload_complete(page: Page, max_polls: int = 360) -> bool:
    """等网页上传从 X% 跑到 100% 再发布。浏览器上传靠窗口开着才传得完，
    若上传到一半就点发布并关闭浏览器，上传会被掐断卡在中途（如 76%）。
    出现“处理/检查/上传完成”或不再“正在上传”即视为传完。max_polls*5s=30min 上限。"""
    last = ""
    for _ in range(max_polls):
        txt = ""
        for sel in (".progress-label", "span.progress-label", "ytcp-video-upload-progress"):
            loc = page.locator(sel).first
            try:
                if await loc.count():
                    txt = (await loc.inner_text()).strip()
                    if txt:
                        break
            except Exception:
                pass
        if txt:
            if any(k in txt for k in ("处理", "检查", "上传完成", "已上传", "Processing", "complete", "Checks", "Finished")):
                youtube_logger.info(_msg("✅", f"上传完成: {txt[:40]}"))
                return True
            if txt != last:
                youtube_logger.info(_msg("⏳", f"上传中: {txt[:40]}"))
                last = txt
        await page.wait_for_timeout(5000)
    youtube_logger.warning(_msg("⚠️", "等上传超时(30min)，仍尝试发布"))
    return False


class YouTubeVideo(BaseVideoUploader):
    def __init__(self, title, file_path, tags, account_file, *,
                 description="", thumbnail_path=None, playlist=None,
                 visibility="public", ai_content=None, paid_promotion=None, debug=DEBUG_MODE, headless=False):
        self.ai_content = ai_content          # "yes" / "no" / None (leave default)
        self.paid_promotion = paid_promotion  # "yes" / "no" / None (leave default)
        self.publish_date = None              # datetime for real Studio scheduling
        self.title = title
        self.file_path = str(file_path)
        self.tags = tags or []
        self.account_file = str(account_file)
        self.description = description or ""
        self.thumbnail_path = str(thumbnail_path) if thumbnail_path else None
        self.playlist = playlist
        self.visibility = visibility if visibility in VISIBILITY else "public"
        self.debug = debug
        self.headless = headless

    async def _set_schedule(self, page, browser):
        """Fill Studio's Schedule box (date, time, optional time zone) and verify what Studio shows."""
        d = self.publish_date
        date_text = f"{d.day} {d.strftime('%b')} {d.year}"     # Studio shows e.g. "7 Nov 2026"
        time_text = d.strftime("%H:%M")
        youtube_logger.info(f"Scheduling for {date_text} {time_text} (time zone: {YT_SCHEDULE_TIMEZONE or 'Local Time'})")
        trig = page.locator("#datepicker-trigger").first
        if not (await trig.count() and await trig.is_visible()):
            await _click_if_present(page, "#second-container-expand-button", 8000)
            await page.wait_for_timeout(1200)
        await trig.click()
        await page.wait_for_timeout(800)
        date_in = page.locator("ytcp-date-picker tp-yt-paper-input[aria-label='Enter date'] input, ytcp-date-picker input").first
        await date_in.fill(date_text)
        await date_in.press("Enter")
        await page.wait_for_timeout(800)
        time_in = page.locator("#time-of-day-container input").first
        await time_in.click()
        await time_in.fill(time_text)
        await time_in.press("Enter")
        await page.wait_for_timeout(800)
        if YT_SCHEDULE_TIMEZONE and await _click_if_present(page, "#timezone-select-button", 4000):
            await page.wait_for_timeout(1000)
            tz_item = page.locator(f"tp-yt-paper-item:has-text('{YT_SCHEDULE_TIMEZONE}')").first
            if await tz_item.count():
                await tz_item.scroll_into_view_if_needed()
                await tz_item.click()
            else:
                await page.keyboard.press("Escape")
                await browser.close()
                raise RuntimeError(f"Time zone '{YT_SCHEDULE_TIMEZONE}' not found in Studio's list; nothing was published.")
            await page.wait_for_timeout(800)
        shown_date = (await trig.inner_text()).strip()
        shown_time = await time_in.input_value()
        if shown_date != date_text or shown_time != time_text:
            await browser.close()
            raise RuntimeError(f"Schedule not set correctly (Studio shows {shown_date} {shown_time}, wanted {date_text} {time_text}); nothing was published.")
        youtube_logger.info(f"Studio schedule confirmed: {shown_date} {shown_time}")

    async def upload(self, playwright: Playwright) -> None:
        browser = await playwright.chromium.launch(
            headless=self.headless, channel="chrome",
            proxy={"server": YT_PROXY} if YT_PROXY else None,
        )
        context = await browser.new_context(storage_state=self.account_file,
                                            user_agent=await _normal_ua(browser))
        context = await set_init_script(context)
        page = await context.new_page()
        page.set_default_timeout(60000)

        youtube_logger.info(_msg("🎬", f"开始上传: {Path(self.file_path).name}"))
        await page.goto(UPLOAD_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        if "accounts.google.com" in page.url or "signin" in page.url.lower():
            await browser.close()
            raise RuntimeError("YouTube 登录态失效，请重新执行 login")

        # 1) 选择视频文件
        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=60000)
        await file_input.set_input_files(self.file_path)

        # 2) 等详情对话框
        await page.locator("#title-textarea").wait_for(state="visible", timeout=120000)

        # 3) 标题
        youtube_logger.info(_msg("✍️", "填写标题"))
        await _fill_editable(page, "#title-textarea #textbox", self.title[:100])

        # 4) 简介
        if self.description.strip():
            youtube_logger.info(_msg("✍️", "填写简介"))
            await _fill_editable(page, "#description-textarea #textbox", self.description)

        # 5) 封面（处理到一定进度才允许传，失败不致命）
        if self.thumbnail_path and Path(self.thumbnail_path).exists():
            try:
                thumb_input = page.locator(
                    "#file-loader input[type='file'], ytcp-thumbnail-uploader input[type='file']"
                ).first
                await thumb_input.wait_for(state="attached", timeout=20000)
                await thumb_input.set_input_files(self.thumbnail_path)
                await page.wait_for_timeout(2000)
                youtube_logger.info(_msg("🖼️", "封面已上传"))
            except Exception as exc:
                youtube_logger.warning(_msg("⚠️", f"封面上传跳过（不影响发布）: {exc}"))

        # 6) 加入播放列表（连载/系列追更）。弹窗务必关闭，否则挡住后续步骤。
        if self.playlist:
            try:
                await _click_if_present(
                    page, "#basics ytcp-text-dropdown-trigger, ytcp-video-metadata-playlists ytcp-dropdown-trigger", 8000)
                await page.wait_for_timeout(1200)
                existing = page.locator(
                    f"tp-yt-paper-checkbox:has-text('{self.playlist}'), "
                    f"ytcp-checkbox-group:has-text('{self.playlist}')").first
                if await existing.count():
                    await existing.click()
                else:
                    if await _click_if_present(page, "ytcp-button:has-text('New playlist'), ytcp-button:has-text('创建播放列表')", 4000):
                        await page.wait_for_timeout(800)
                        await _click_if_present(page, "tp-yt-paper-item:has-text('New playlist'), tp-yt-paper-item:has-text('新建播放列表')", 3000)
                        title_box = page.locator("ytcp-playlist-metadata-editor #textbox, #create-playlist-form #textbox").first
                        if await title_box.count():
                            await title_box.click()
                            await title_box.type(self.playlist, delay=6)
                            await _click_if_present(page, "ytcp-button#create-button, tp-yt-paper-dialog ytcp-button:has-text('Create'), tp-yt-paper-dialog ytcp-button:has-text('创建')", 4000)
            except Exception as exc:
                youtube_logger.warning(_msg("⚠️", f"播放列表处理跳过（不影响发布）: {exc}"))
            finally:
                await _click_if_present(page, "ytcp-playlist-dialog #save-button, ytcp-button:has-text('Done'), ytcp-button:has-text('完成')", 3000)
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(600)

        # 7) 受众：非儿童向（必填）
        if not await _click_if_present(page, "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']", 10000):
            await _click_if_present(page, "tp-yt-paper-radio-button:has-text('not made for kids'), tp-yt-paper-radio-button:has-text('不是面向儿童')", 6000)

        # 8) 标签（“显示更多”里）
        if self.tags:
            try:
                await _click_if_present(page, "#toggle-button", 6000)
                await page.wait_for_timeout(800)
                tag_input = page.locator("#tags-container #text-input, ytcp-form-input-container#tags-container input").first
                await tag_input.click()
                await tag_input.type(",".join(self.tags)[:500] + ",", delay=4)
            except Exception as exc:
                youtube_logger.warning(_msg("⚠️", f"标签填写跳过（不影响发布）: {exc}"))

        # 8.4) paid promotion question, under "Show more"
        if self.paid_promotion in ("yes", "no"):
            name = "VIDEO_PAID_PRODUCT_PLACEMENT_NOTIFY" if self.paid_promotion == "yes" else "VIDEO_PAID_PRODUCT_PLACEMENT_NO"
            radio = page.locator(f"tp-yt-paper-radio-button[name='{name}']").first
            if not (await radio.count() and await radio.is_visible()):
                await _click_if_present(page, "#toggle-button", 6000)
                await page.wait_for_timeout(1000)
            await radio.scroll_into_view_if_needed()
            await radio.click()
            await page.wait_for_timeout(500)
            if await radio.get_attribute("aria-checked") != "true" and await radio.get_attribute("checked") is None:
                await browser.close()
                raise RuntimeError("Could not set the paid promotion answer; nothing was published.")
            youtube_logger.info(f"Paid promotion = {self.paid_promotion}")

        # 8.5) altered or synthetic content (AI) question, under "Show more"
        if self.ai_content in ("yes", "no"):
            name = "VIDEO_HAS_ALTERED_CONTENT_YES" if self.ai_content == "yes" else "VIDEO_HAS_ALTERED_CONTENT_NO"
            radio = page.locator(f"tp-yt-paper-radio-button[name='{name}']").first
            if not (await radio.count() and await radio.is_visible()):
                await _click_if_present(page, "#toggle-button", 6000)
                await page.wait_for_timeout(1000)
            await radio.scroll_into_view_if_needed()
            await radio.click()
            await page.wait_for_timeout(500)
            if await radio.get_attribute("aria-checked") != "true" and await radio.get_attribute("checked") is None:
                await browser.close()
                raise RuntimeError("Could not set the Altered content (AI) answer; nothing was published.")
            youtube_logger.info(f"Altered/AI content = {self.ai_content}")

        # 9) 连点 Next 到“可见性”步骤
        for _ in range(5):
            vis = page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
            if await vis.count() and await vis.first.is_visible():
                break
            if not await _click_if_present(page, "#next-button", 6000):
                await page.wait_for_timeout(1200)
            await page.wait_for_timeout(1000)

        # 10) 可见性
        if self.publish_date:
            await self._set_schedule(page, browser)
        else:
            youtube_logger.info(_msg("🌐", f"设置可见性 = {self.visibility}"))
            await _click_if_present(page, f"tp-yt-paper-radio-button[name='{VISIBILITY[self.visibility]}']", 10000)

        # 10.5) 关键：等上传真正传完再发布。浏览器上传靠窗口开着传，
        #       传到一半就点发布+关浏览器 = 上传被掐断卡在中途（如 76%）。
        youtube_logger.info(_msg("📤", "等待上传完成（传完才发布）…"))
        await _wait_upload_complete(page)

        # 11) 发布  (the original clicked #done-button even while disabled and
        #     then closed the dialog, leaving the video as a Draft while reporting success.)
        await page.wait_for_timeout(1200)
        done = page.locator("#done-button").first
        enabled = False
        for _ in range(120):  # up to ~10 min for the button to become enabled
            try:
                if await done.count() and await done.is_visible():
                    dis = await done.get_attribute("aria-disabled")
                    if dis != "true" and await done.is_enabled():
                        enabled = True
                        break
            except Exception:
                pass
            await page.wait_for_timeout(5000)
        confirmed = False
        acked = False
        if enabled:
            await page.wait_for_timeout(1500)
            await done.click()
            for _ in range(30):  # up to 60s for the confirmation dialog
                # after Schedule, YouTube shows "We're still checking your content" with
                # only a "Got it" button; acknowledging it completes the schedule.
                gotit = page.locator("ytcp-button:has-text('Got it')").first
                try:
                    if await gotit.count() and await gotit.is_visible():
                        youtube_logger.info("Acknowledging 'still checking' notice (Got it)")
                        await gotit.click()
                        await page.wait_for_timeout(3000)
                        acked = True
                        continue
                except Exception:
                    pass
                try:
                    if acked and not await page.locator("#done-button").first.is_visible():
                        confirmed = True   # upload dialog closed after the notice = saved
                        break
                except Exception:
                    pass
                # YouTube's "checks still running" warning: press "Publish anyway", never "Go back".
                anyway = page.locator("ytcp-button#secondary-action-button:has-text('Publish anyway'), ytcp-button:has-text('Publish anyway')").first
                try:
                    if await anyway.count() and await anyway.is_visible():
                        youtube_logger.info("Checks still running - clicking 'Publish anyway'")
                        await anyway.click()
                        await page.wait_for_timeout(2500)
                        continue
                except Exception:
                    pass
                # Success state seen 2026-11-06: Save/Back greyed out and a "Close" button shown.
                try:
                    closeb = page.locator("ytcp-button#close-button").first
                    if (await closeb.count() and await closeb.is_visible()
                            and await done.get_attribute("aria-disabled") == "true"):
                        confirmed = True
                        break
                except Exception:
                    pass
                dlg = page.locator("ytcp-video-share-dialog, ytcp-uploads-still-processing-dialog, ytcp-prechecks-warning-dialog").first
                if await dlg.count() and await dlg.is_visible():
                    tag = await dlg.evaluate("e => e.tagName.toLowerCase()")
                    if tag == "ytcp-prechecks-warning-dialog":
                        # "checks still running" warning: confirm publishing anyway
                        await _click_if_present(page, "ytcp-prechecks-warning-dialog #primary-action-button, ytcp-prechecks-warning-dialog ytcp-button:has-text('Publish'), ytcp-prechecks-warning-dialog ytcp-button:has-text('Save')", 5000)
                        await page.wait_for_timeout(2000)
                        continue
                    confirmed = True
                    break
                await page.wait_for_timeout(2000)
        if not confirmed:
            try:
                Path("Local_debug").mkdir(exist_ok=True)
                await page.screenshot(path="Local_debug/youtube_publish_not_confirmed.png", full_page=True)
                btns = await page.evaluate("""() => [...document.querySelectorAll('ytcp-button, tp-yt-paper-radio-button, [role=dialog]')]
                    .filter(e => e.offsetParent).map(e => e.tagName.toLowerCase() + '#' + (e.id||'') + ' ' + (e.getAttribute('aria-disabled')||'') + ' | ' + (e.innerText||'').trim().slice(0,40))""")
                youtube_logger.warning("Visible controls: " + " || ".join(btns[:60]))
            except Exception as exc:
                youtube_logger.warning(f"diagnostics failed: {exc}")
            await browser.close()
            raise RuntimeError("YouTube did not confirm the publish/save; the video is probably a Draft in Studio. Screenshot: Local_debug/youtube_publish_not_confirmed.png")
        video_url = ""
        try:
            link = page.locator("ytcp-video-share-dialog a[href*='youtu'], a[href*='youtu.be'], a[href*='/shorts/']").first
            if await link.count():
                video_url = await link.get_attribute("href") or ""
        except Exception:
            pass
        await _click_if_present(page, "ytcp-video-share-dialog #close-button, ytcp-uploads-still-processing-dialog #close-button, ytcp-button:has-text('Close')", 8000)
        youtube_logger.success(_msg("🥳", f"发布完成（{self.visibility}）{(' ' + video_url) if video_url else ''}"))

        # 刷新 cookie
        try:
            await context.storage_state(path=self.account_file)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        await browser.close()

    def set_publish_date(self, publish_date):
        """Schedule in Studio (local time, or YT_SCHEDULE_TIMEZONE). 0/None = publish now."""
        if not publish_date:
            self.publish_date = None
            return
        import datetime as _dt
        if publish_date <= _dt.datetime.now() + _dt.timedelta(minutes=15):
            raise RuntimeError("Schedule time must be at least 15 minutes in the future.")
        self.publish_date = publish_date

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
