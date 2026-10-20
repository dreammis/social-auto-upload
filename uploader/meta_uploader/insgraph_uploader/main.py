"""Instagram 独立网页会话及照片、轮播、Reels 发布。"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from patchright.async_api import Locator, Page, Playwright, TimeoutError as BrowserTimeoutError, async_playwright, expect

INSTAGRAM_HOME_URL = "https://www.instagram.com/"
# 未配置环境变量或 --proxy 时使用系统直连。
INSTAGRAM_PROXY = os.environ.get("SAU_INSTAGRAM_PROXY")
# 创建弹窗实际 accept 同时含照片与 MP4，此属性限定素材入口，排除编辑阶段的封面 input。
INSTAGRAM_MEDIA_INPUT = 'input[type="file"][accept*="video/mp4"]'
# _ac76 是已观察中/英文裁剪、编辑、配文页共用的向导标题栏组件；主动作不含 SVG，返回按钮含 SVG。
INSTAGRAM_PRIMARY_ACTION = '._ac76 [role="button"]:not(:has(svg))'


async def _dismiss_optional_prompt(guide: Locator, dismiss_button: Locator) -> bool:
    """仅关闭已识别的可选提示；缺席可继续，出现后的操作失败必须报错。"""
    try:
        await guide.wait_for(state='visible', timeout=1500)
    except BrowserTimeoutError:
        return False
    await expect(dismiss_button).to_have_count(1)
    await dismiss_button.click()
    await guide.wait_for(state='hidden')
    return True


def _proxy_options(proxy: str | None) -> dict[str, str] | None:
    """未传参数时使用显式环境配置，否则直连；空字符串可覆盖环境配置并直连。"""
    address = (INSTAGRAM_PROXY if proxy is None else proxy) or ""
    address = address.strip()
    return {"server": address} if address else None


async def _open_instagram_page(playwright: Playwright, account_file: Path, *, proxy: str | None, headless: bool):
    """使用工程 Chrome 和指定存储状态，导航失败保留原异常。"""
    browser = await playwright.chromium.launch(channel="chrome", headless=headless, proxy=_proxy_options(proxy))
    try:
        context = await browser.new_context(storage_state=str(account_file))
        page = await context.new_page()
        page.set_default_timeout(30_000)
        await page.goto(INSTAGRAM_HOME_URL, wait_until="domcontentloaded", timeout=120_000)
        return browser, context, page
    except Exception:
        await browser.close()
        raise


async def _is_instagram_logged_out(page: Page) -> bool:
    """等待明确登录/未登录业务区域；网络或未知页面超时不能解释为 Cookie 失效。"""
    # 消息入口是登录后的导航，href 前缀允许站点附加 hl 参数；登录表单字段不依赖翻译。
    outcomes = page.locator('a[href^="/direct/inbox/"], input[name="username"], a[href^="/accounts/login/"]')
    await expect(outcomes).not_to_have_count(0, timeout=60_000)
    return not await page.locator('a[href^="/direct/inbox/"]').count()


async def instagram_identity(page: Page, account_file: Path) -> dict:
    """将当前会话用户 ID 与账号文件绑定的 ID 比对，读取自己的导航主页。"""
    if await _is_instagram_logged_out(page):
        raise RuntimeError("Instagram 未登录，请执行 sau instagram login")
    state = json.loads(account_file.read_text(encoding="utf-8"))
    expected = {c['value'] for c in state['cookies'] if c['name'] == 'ds_user_id' and c['domain'].lstrip('.') == 'instagram.com'}
    current = {c['value'] for c in await page.context.cookies(INSTAGRAM_HOME_URL) if c['name'] == 'ds_user_id'}
    if len(expected) != 1 or current != expected:
        raise RuntimeError("Instagram 当前登录用户与账号文件绑定的用户 ID 不匹配")
    # 当前用户导航头像位于 aria-selected 图标容器中；动态流和推荐头像没有导航选中状态。
    own_profile = page.locator('a[href]').filter(has=page.locator('[aria-selected] img'))
    await expect(own_profile).to_have_count(1)
    href = await own_profile.get_attribute('href')
    username = urlparse(href).path.strip('/')
    if not username or '/' in username:
        raise RuntimeError("Instagram 当前用户主页链接结构不符")
    return {"user_id": next(iter(expected)), "username": username}


async def instagram_cookie_auth(account_file: str | Path, *, proxy: str | None = None) -> bool:
    """独立验证登录和账号绑定；未知页面/网络错误直接上报。"""
    account_file = Path(account_file)
    if not account_file.is_file():
        return False
    async with async_playwright() as playwright:
        browser, context, page = await _open_instagram_page(playwright, account_file, proxy=proxy, headless=True)
        try:
            if await _is_instagram_logged_out(page):
                return False
            await instagram_identity(page, account_file)
            return True
        finally:
            await browser.close()


async def instagram_setup(account_file: str | Path, *, handle: bool = False, proxy: str | None = None,
                          headless: bool = False, return_detail: bool = False, timeout_seconds: int = 900):
    """工程浏览器人工登录，导出候选状态并在新 context 验证后替换账号文件。"""
    account_file = Path(account_file)
    account_file.parent.mkdir(parents=True, exist_ok=True)
    if await instagram_cookie_auth(account_file, proxy=proxy):
        result = {"success": True, "status": "cookie_valid", "account_file": str(account_file)}
        return result if return_detail else True
    if not handle:
        result = {"success": False, "status": "cookie_invalid", "account_file": str(account_file)}
        return result if return_detail else False
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=headless, proxy=_proxy_options(proxy), args=["--start-maximized"])
        candidate = account_file.with_name(f'{account_file.stem}.{uuid4().hex}.pending.json')
        try:
            context = await browser.new_context(no_viewport=not headless)
            page = await context.new_page()
            await page.goto(INSTAGRAM_HOME_URL + 'accounts/login/', wait_until='domcontentloaded', timeout=120_000)
            # 消息入口仅在人工登录及挑战完成后出现；不按 URL 或登录表单消失宣告成功。
            await page.locator('a[href^="/direct/inbox/"]').wait_for(state='visible', timeout=timeout_seconds * 1000)
            await context.storage_state(path=str(candidate))
            if not await instagram_cookie_auth(candidate, proxy=proxy):
                raise RuntimeError('Instagram 导出的候选状态未通过新会话验证')
            candidate.replace(account_file)
            result = {"success": True, "status": "logged_in", "account_file": str(account_file)}
            return result if return_detail else True
        finally:
            candidate.unlink(missing_ok=True)
            await browser.close()


def instagram_response_payload(body: str) -> dict:
    """解析已观察的普通 JSON 以及 Meta 防 JSON 劫持前缀，其他格式直接报错。"""
    if body.startswith('for (;;);'):
        body = body[len('for (;;);'):]
    return json.loads(body)


def instagram_created_media(payload: dict, *, owner_id: str, caption: str) -> dict:
    """只接受最终创建响应中匹配用户和配文的作品；处理中和 HTTP 200 均不是成功。"""
    envelope = payload
    payload = envelope.get('payload', envelope)
    if envelope.get('error') or payload.get('status') not in (None, 'ok') or ('statusCode' in payload and payload['statusCode'] != 200):
        raise RuntimeError(f"Instagram 创建未成功: {payload.get('message', payload.get('statusCode', payload.get('status')))}")
    media = payload.get('media') or {}
    if not media.get('code') or not media.get('id'):
        raise RuntimeError('Instagram 创建响应缺少作品编号')
    if str((media.get('user') or {}).get('pk')) != owner_id:
        raise RuntimeError('Instagram 创建响应的作者 ID 不匹配')
    if (media.get('caption') or {}).get('text') != caption:
        raise RuntimeError('Instagram 创建响应的配文不匹配')
    return media


class InstagramUploader:
    """独立网页立即发布；最终创建响应确认成功后返回作品链接。"""

    def __init__(self, account_file: str | Path, *, title: str, description: str = '', tags: list[str] | None = None,
                 video_file: str | Path | None = None, image_files: list[str | Path] | None = None,
                 thumbnail: str | Path | None = None,
                 proxy: str | None = None, headless: bool = False, result_file: str | Path | None = None):
        self.account_file = Path(account_file)
        self.title, self.description = title.strip(), description.strip()
        self.tags = [t.strip().lstrip('#') for t in (tags or []) if t.strip().lstrip('#')]
        self.video_file = Path(video_file) if video_file else None
        self.image_files = [Path(p) for p in (image_files or [])]
        self.thumbnail = Path(thumbnail) if thumbnail else None
        if self.thumbnail and not self.video_file:
            raise ValueError('Instagram 自定义封面仅用于视频/Reel')
        if bool(self.video_file) == bool(self.image_files):
            raise ValueError('必须且只能传入视频或图片文件')
        if not self.title:
            raise ValueError('标题不能为空')
        self.proxy, self.headless = proxy, headless
        self.result_file = Path(result_file) if result_file else Path('.local/instagram-results') / f'{uuid4().hex}.json'
        self.result = {'platform': 'instagram', 'title': self.title, 'status': 'not_submitted'}
        self.stage = 'validation'
        if len(self._caption()) > 2200:
            raise ValueError('Instagram 配文（标题、正文、标签合计）不能超过 2200 字符')

    def _caption(self) -> str:
        """Instagram 只有配文，将 CLI 标题、正文和标签合并。"""
        parts = [p for p in (self.title, self.description) if p]
        if self.tags:
            parts.append(' '.join(f'#{t}' for t in self.tags))
        return '\n\n'.join(parts)

    async def _upload_files(self, page: Page) -> None:
        """打开创建入口并等待裁剪阶段就绪，拒绝用上传后固定延时推断完成。"""
        # 实际通知提示使用此固定图标及 _a9-z 动作区。两项依次为开启、稍后，
        # 取第二个直接子按钮；限定图标和局部动作区，避免按翻译文案或全页按钮点击。
        notifications = page.get_by_role('dialog').filter(
            has=page.locator('img[src^="/images/instagram/xig/ico/xxhdpi_launcher.png"]'))
        notification_buttons = notifications.locator('._a9-z > button')
        # 中英文首页均观察到这四个导航弹出入口，依次为通知、创建、设置、Meta。
        # 先断言完整组和各入口含 aria-selected 图标再取业务顺序第二项，避免全页任意 nth。
        navigation_popups = page.locator('a._a6hd[href="#"]').filter(has=page.locator('[aria-selected]'))
        # 实测通知可能晚于导航出现。动作检查期间处理此已知遮挡，避免先检查缺席、
        # 再点击时才弹出造成竞态；没有提示时不会执行回调，也不添加固定等待。
        await page.add_locator_handler(notifications, lambda: _dismiss_optional_prompt(notifications, notification_buttons.nth(1)))
        try:
            await expect(navigation_popups).to_have_count(4)
            await navigation_popups.nth(1).click()
        finally:
            await page.remove_locator_handler(notifications)
        dialog = page.get_by_role('dialog')
        await expect(dialog).to_have_count(1)
        file_input = dialog.locator(INSTAGRAM_MEDIA_INPUT)
        await expect(file_input).to_have_count(1)
        paths = [self.video_file] if self.video_file else self.image_files
        await file_input.set_input_files([str(p.resolve()) for p in paths])
        if self.video_file:
            # 实际 Reels 介绍使用 reels_nux_icon；动作区“了解更多”位于 span 中，
            # 确认按钮直接位于 div 中，按局部父子关系区分，不依赖语言与样式散列。
            reels_intro = page.get_by_role('dialog').filter(
                has=page.locator('img[src^="/images/instagram/clips/reels_nux_icon.png"]'))
            await _dismiss_optional_prompt(reels_intro, reels_intro.locator('._a9-z div > button'))
        # 裁剪标题栏主动作实际出现，才可推进；上传失败或未知弹窗阻断会保留现场并报错。
        await expect(dialog.locator(INSTAGRAM_PRIMARY_ACTION)).to_have_count(1, timeout=60_000)

    async def _advance_media_editor(self, page: Page) -> None:
        """裁剪、编辑两步各等待标题改变，最终以 Lexical 配文输入框确认。"""
        # 同一个创建弹窗标题栏存在于三个阶段；局部主动作不含图标，排除返回和媒体工具按钮。
        dialog = page.get_by_role('dialog')
        heading = dialog.locator('._ac76 [role="heading"]')
        for step in range(2):
            if step == 1 and self.thumbnail:
                # 实际视频编辑弹窗中，精确 JPEG/PNG accept 是独立封面入口，排除初始视频素材 input。
                cover = dialog.locator('input[type="file"][accept="image/jpeg,image/png"]')
                # 主预览的 video 紧邻封面背景层；右侧视频帧条也有背景图，不能拿帧条验证封面。
                poster = dialog.locator('video + div[style*="background-image"]')
                await expect(cover).to_have_count(1)
                await expect(poster).to_have_count(1)
                previous_style = await poster.get_attribute('style')
                await cover.set_input_files(str(self.thumbnail.resolve()))
                await expect(poster).not_to_have_attribute('style', previous_style, timeout=30_000)
                # 已观察页面直接以原图 blob 替换封面。核对实际预览字节并解码，文件选中本身不代表生效。
                preview = await asyncio.wait_for(poster.evaluate('''async element => {
                    const background = getComputedStyle(element).backgroundImage;
                    const url = background.slice(5, -2);
                    const blob = await (await fetch(url)).blob();
                    const bitmap = await createImageBitmap(blob);
                    const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
                    const result = {width: bitmap.width, height: bitmap.height,
                        sha256: Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('')};
                    bitmap.close();
                    return result;
                }'''), timeout=30)
                if not preview['width'] or not preview['height'] or preview['sha256'] != hashlib.sha256(self.thumbnail.read_bytes()).hexdigest():
                    raise RuntimeError('Instagram 封面主预览与指定图片不匹配')
            await expect(heading).to_have_count(1)
            previous = await heading.inner_text()
            action = dialog.locator(INSTAGRAM_PRIMARY_ACTION)
            await expect(action).to_have_count(1)
            await expect(action).to_be_enabled()
            await action.click()
            await expect(heading).not_to_have_text(previous, timeout=60_000)
        # data-lexical-editor 标识真实正文编辑器，限定当前创建弹窗，排除评论输入框。
        await expect(dialog.locator('[contenteditable="true"][role="textbox"][data-lexical-editor="true"]')).to_have_count(1)

    async def _publish(self, page: Page, identity: dict) -> None:
        """先登记最终响应监听再分享，响应不明时记录 unknown 且不重发。"""
        # 配文页独有 Lexical 编辑器；标题栏唯一主动作此时是分享，不使用翻译后的按钮名称。
        dialog = page.get_by_role('dialog')
        editor = dialog.locator('[contenteditable="true"][role="textbox"][data-lexical-editor="true"]')
        caption = self._caption()
        await editor.fill(caption)
        await expect(editor).to_have_text(caption)
        action = dialog.locator(INSTAGRAM_PRIMARY_ACTION)
        await expect(action).to_have_count(1)
        await expect(action).to_be_enabled()
        self.result.update(identity, status='submission_unknown')
        self.result_file.parent.mkdir(parents=True, exist_ok=True)
        self.result_file.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')
        # Reel 首次返回 202，浏览器会继续请求同一创建接口，后续才返回正式 media。
        # 提交前安装队列监听，持续消费本次创建响应；只点击一次，不将上传响应或 202 视为发表成功。
        responses = asyncio.Queue()
        def on_response(response):
            if response.request.method == 'POST' and urlparse(response.url).path.startswith('/api/v1/media/configure'):
                responses.put_nowait(response)
        page.on('response', on_response)
        try:
            await action.click()
            deadline = asyncio.get_running_loop().time() + 180
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError('Instagram 已提交，但等待最终作品创建响应超时')
                response = await asyncio.wait_for(responses.get(), timeout=remaining)
                remaining = deadline - asyncio.get_running_loop().time()
                payload = instagram_response_payload(await asyncio.wait_for(response.text(), timeout=max(remaining, 0)))
                body = payload.get('payload', payload)
                if body.get('statusCode') == 202:
                    self.result['status'] = 'processing'
                    self.result_file.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')
                    continue
                media = instagram_created_media(payload, owner_id=identity['user_id'], caption=caption)
                break
        finally:
            page.remove_listener('response', on_response)
        kind = 'reel' if self.video_file else 'p'
        self.result.update(status='published', content_id=media['id'], post_id=media['code'],
                           post_url=f"{INSTAGRAM_HOME_URL}{kind}/{media['code']}/", schedule=None,
                           media_count=len(media.get('carousel_media') or [media]))
        self.result_file.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')

    async def upload(self) -> dict:
        """在同一会话核验身份、上传并发表；失败保存阶段与本地证据。"""
        if self.thumbnail:
            if not self.thumbnail.is_file():
                raise FileNotFoundError(f'Instagram 封面不存在: {self.thumbnail}')
            if self.thumbnail.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
                raise ValueError('Instagram 封面仅支持 JPG/JPEG/PNG')
        paths = [self.video_file] if self.video_file else self.image_files
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(f'Instagram 素材不存在: {path}')
            allowed = {'.mp4', '.mov'} if self.video_file else {'.jpg', '.jpeg', '.png', '.avif', '.heic', '.heif'}
            if path.suffix.lower() not in allowed:
                raise ValueError(f'Instagram 不支持的素材类型: {path.suffix}')
        async with async_playwright() as p:
            browser, context, page = await _open_instagram_page(p, self.account_file, proxy=self.proxy, headless=self.headless)
            try:
                self.stage = 'identity'
                identity = await instagram_identity(page, self.account_file)
                self.stage = 'upload'
                await self._upload_files(page)
                self.stage = 'edit'
                await self._advance_media_editor(page)
                self.stage = 'publish'
                await self._publish(page, identity)
                self.stage = 'save_session'
                await context.storage_state(path=str(self.account_file))
                return self.result
            except Exception as error:
                folder = Path('.local/instagram-errors') / uuid4().hex
                folder.mkdir(parents=True)
                self.result.update(stage=self.stage, error=str(error), evidence_dir=str(folder))
                self.result_file.parent.mkdir(parents=True, exist_ok=True)
                self.result_file.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')
                await page.screenshot(path=str(folder/'page.png'))
                (folder/'page.html').write_text(await page.content(), encoding='utf-8')
                raise RuntimeError(f'Instagram {self.stage} 未完成；结果记录: {self.result_file}；原因: {error}') from error
            finally:
                await browser.close()
