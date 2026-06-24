from __future__ import annotations
import asyncio
import json
from datetime import datetime
from pathlib import Path
from patchright.async_api import Page, Playwright, async_playwright
import patchright
from conf import DEBUG_MODE, LOCAL_CHROME_HEADLESS
from uploader.common import _msg
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger
BILIBILI_NOTE_PUBLISH_STRATEGY_IMMEDIATE = 'immediate'
BILIBILI_NOTE_PUBLISH_STRATEGY_SCHEDULED = 'scheduled'
BILIBILI_NOTE_UPLOAD_PAGE = 'https://member.bilibili.com/platform/upload/text/edit'
MAX_IMAGES = 20
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

def _convert_biliup_cookies_to_storage_state(biliup_cookie_path: str) -> dict:
    raw = json.loads(Path(biliup_cookie_path).read_text(encoding='utf-8'))
    cookies = []
    for c in raw if isinstance(raw, list) else raw.get('cookies', []):
        cookie: dict = {'name': c.get('name', ''), 'value': c.get('value', ''), 'domain': c.get('domain', '.bilibili.com'), 'path': c.get('path', '/')}
        if c.get('expires', -1) > 0:
            cookie['expires'] = c['expires']
        cookies.append(cookie)
    return {'cookies': cookies, 'origins': [{'origin': 'https://member.bilibili.com', 'localStorage': []}]}

def _convert_storage_state_to_biliup_cookies(storage_state: dict) -> list[dict]:
    """Convert Playwright storage_state cookies back to biliup format."""
    cookies = []
    for c in storage_state.get('cookies', []):
        cookie: dict = {'name': c.get('name', ''), 'value': c.get('value', ''), 'domain': c.get('domain', '.bilibili.com'), 'path': c.get('path', '/')}
        if c.get('expires', -1) > 0:
            cookie['expires'] = c['expires']
        cookies.append(cookie)
    return cookies

class BilibiliNote:

    def __init__(self, image_paths: list[str], title: str, note: str, tags: list[str], publish_date: datetime | int, account_file: str, publish_strategy: str=BILIBILI_NOTE_PUBLISH_STRATEGY_IMMEDIATE, debug: bool=DEBUG_MODE, headless: bool=LOCAL_CHROME_HEADLESS):
        self.image_paths = image_paths
        self.title = title or ''
        self.note = note or ''
        self.tags = tags or []
        self.publish_date = publish_date
        self.account_file = account_file
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.headless = headless

    def _validate_image(self, file_path: str | Path) -> Path:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f'图片文件不存在: {path}')
        if not path.is_file():
            raise ValueError(f'图片路径不是文件: {path}')
        if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            raise ValueError(f"不支持的图片格式: {path.suffix}，当前支持: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}")
        return path

    async def validate_upload_args(self):
        if not self.title.strip():
            raise ValueError('Bilibili 图文上传时，title 是必须的')
        if not self.image_paths:
            raise ValueError('Bilibili 图文上传时，图片是必须的')
        if len(self.image_paths) > MAX_IMAGES:
            raise ValueError(f'Bilibili 图文上传最多支持 {MAX_IMAGES} 张图片')
        if self.publish_date not in (None, 0) and (not isinstance(self.publish_date, datetime)):
            raise TypeError('publish_date 必须是 datetime 类型或 0')
        normalized = []
        for image_path in self.image_paths:
            normalized.append(str(self._validate_image(image_path)))
        self.image_paths = normalized

    async def upload_note_content(self, page: Page) -> None:
        bilibili_logger.info(_msg('🏃', f'开始上传 Bilibili 图文，共 {len(self.image_paths)} 张图片'))
        bilibili_logger.info(_msg('🧭', '正在前往 Bilibili 图文发布页'))
        await page.goto(BILIBILI_NOTE_UPLOAD_PAGE)
        await page.wait_for_load_state('domcontentloaded')
        await asyncio.sleep(2)
        bilibili_logger.info(_msg('📤', '正在上传图片'))
        file_input = page.locator("input[type='file'][accept*='image']").first
        await file_input.set_input_files(self.image_paths)
        await asyncio.sleep(3)
        bilibili_logger.info(_msg('✍️', '正在填写标题'))
        title_input = page.locator("input[placeholder*='标题'], input[class*='title']").first
        if await title_input.count():
            await title_input.click()
            await title_input.fill(self.title)
        else:
            await page.keyboard.type(self.title)
        await asyncio.sleep(0.5)
        bilibili_logger.info(_msg('✍️', '正在填写正文'))
        content_area = page.locator("div[class*='editor'], div[contenteditable='true']").first
        if await content_area.count():
            await content_area.click()
            await page.keyboard.type(self.note)
        await asyncio.sleep(0.5)
        if self.tags:
            bilibili_logger.info(_msg('🏷️', f'正在添加 {len(self.tags)} 个标签'))
            tag_input = page.locator("input[placeholder*='标签'], input[placeholder*='tag']").first
            if await tag_input.count():
                for tag in self.tags:
                    await tag_input.fill(tag)
                    await asyncio.sleep(0.5)
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(0.5)
        await asyncio.sleep(1)
        if self.publish_strategy == BILIBILI_NOTE_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            bilibili_logger.info(_msg('⏰', '正在设置定时发布'))
            schedule_button = page.locator("button:has-text('定时'), div:has-text('定时发布')").first
            if await schedule_button.count():
                await schedule_button.click()
                await asyncio.sleep(0.5)
        bilibili_logger.info(_msg('🚀', '正在发布图文'))
        publish_button = page.locator("button:has-text('发布')").first
        if await publish_button.count():
            await publish_button.click()
            await asyncio.sleep(3)
        bilibili_logger.success(_msg('🥳', 'Bilibili 图文发布成功'))

    async def upload(self, playwright: Playwright) -> None:
        bilibili_logger.info(_msg('🧍', '正在检查 cookie、图片和发布时间'))
        await self.validate_upload_args()
        bilibili_logger.info(_msg('🥳', '图文上传前检查通过'))
        storage_state = _convert_biliup_cookies_to_storage_state(self.account_file)
        browser = await playwright.chromium.launch(headless=self.headless)
        context = await browser.new_context(storage_state=storage_state, permissions=['geolocation'])
        context = await set_init_script(context)
        upload_success = False
        try:
            page = await context.new_page()
            await page.goto(BILIBILI_NOTE_UPLOAD_PAGE)
            await page.wait_for_load_state('domcontentloaded')
            await self.upload_note_content(page)
            upload_success = True
        finally:
            if upload_success:
                try:
                    bilibili_logger.info(_msg('💾', '正在保存 cookie（保持 biliup 格式）'))
                    state = await context.storage_state()
                    biliup_cookies = _convert_storage_state_to_biliup_cookies(state)
                    Path(self.account_file).write_text(json.dumps(biliup_cookies, ensure_ascii=False, indent=2), encoding='utf-8')
                except (patchright.async_api.Error, OSError, asyncio.TimeoutError):
                    pass
                bilibili_logger.success(_msg('🥳', 'cookie 更新完毕'))
                await asyncio.sleep(2)
            await context.close()
            await browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)