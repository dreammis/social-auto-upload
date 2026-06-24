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


async def cookie_auth(account_file) -> bool:
    """登录态是否仍有效：带 cookie 打开 Studio，没被踢到 Google 登录页且进入了频道页即有效。"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(STUDIO_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
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
        ok = False
        for _ in range(600):  # 最多等 10 分钟
            if "/channel/" in page.url:
                await page.wait_for_timeout(2000)  # 让 cookie 落定
                ok = True
                break
            await asyncio.sleep(1)
        if ok:
            await context.storage_state(path=account_file)
            youtube_logger.success(_msg("✅", f"YouTube 登录态已保存: {account_file}"))
        else:
            youtube_logger.error(_msg("😵", "等待登录超时，未保存登录态"))
        await browser.close()
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
                 visibility="public", debug=DEBUG_MODE, headless=False):
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

    async def upload(self, playwright: Playwright) -> None:
        browser = await playwright.chromium.launch(
            headless=self.headless, channel="chrome",
            proxy={"server": YT_PROXY} if YT_PROXY else None,
        )
        context = await browser.new_context(storage_state=self.account_file)
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

        # 9) 连点 Next 到“可见性”步骤
        for _ in range(5):
            vis = page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
            if await vis.count() and await vis.first.is_visible():
                break
            if not await _click_if_present(page, "#next-button", 6000):
                await page.wait_for_timeout(1200)
            await page.wait_for_timeout(1000)

        # 10) 可见性
        youtube_logger.info(_msg("🌐", f"设置可见性 = {self.visibility}"))
        await _click_if_present(page, f"tp-yt-paper-radio-button[name='{VISIBILITY[self.visibility]}']", 10000)

        # 10.5) 关键：等上传真正传完再发布。浏览器上传靠窗口开着传，
        #       传到一半就点发布+关浏览器 = 上传被掐断卡在中途（如 76%）。
        youtube_logger.info(_msg("📤", "等待上传完成（传完才发布）…"))
        await _wait_upload_complete(page)

        # 11) 发布
        await page.wait_for_timeout(1200)
        if not await _click_if_present(page, "#done-button", 15000):
            youtube_logger.warning(_msg("🤔", "未找到发布按钮，可能上传未到可发布进度；请在窗口里手动发布"))
        else:
            await page.wait_for_timeout(4000)
            video_url = ""
            try:
                link = page.locator("a[href*='youtu.be'], a[href*='watch?v=']").first
                if await link.count():
                    video_url = await link.get_attribute("href") or ""
            except Exception:
                pass
            await _click_if_present(page, "ytcp-button:has-text('Close'), ytcp-button:has-text('关闭'), #close-button", 8000)
            youtube_logger.success(_msg("🥳", f"发布完成（{self.visibility}）{(' ' + video_url) if video_url else ''}"))

        # 刷新 cookie
        try:
            await context.storage_state(path=self.account_file)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        await browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
