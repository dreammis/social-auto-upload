"""通过 Meta Business Suite 发布 Facebook Page 内容。"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from patchright.async_api import Page, Playwright, async_playwright, expect, TimeoutError as BrowserTimeoutError

from uploader.base_video import BaseVideoUploader


META_BUSINESS_URL = "https://business.facebook.com/latest/composer/"
META_PLATFORMS = {"facebook-page"}
# 未配置环境变量或 --proxy 时使用系统直连。
FACEBOOK_PAGE_PROXY = os.environ.get("SAU_FACEBOOK_PAGE_PROXY")


def meta_account_file(platform: str, account_name: str) -> Path:
    if platform not in META_PLATFORMS:
        raise ValueError(f"不支持的 Meta Business 平台: {platform}")
    return Path("cookies") / f"{platform}_{account_name}.json"


def _proxy_options(proxy: str | None) -> dict[str, str] | None:
    address = (FACEBOOK_PAGE_PROXY if proxy is None else proxy) or ""
    address = address.strip()
    return {"server": address} if address else None


async def _open_business_page(
    playwright: Playwright,
    account_file: Path,
    *,
    proxy: str | None,
    headless: bool,
):
    browser = await playwright.chromium.launch(
        channel="chrome", headless=headless, proxy=_proxy_options(proxy)
    )
    try:
        context = await browser.new_context(storage_state=str(account_file))
        page = await context.new_page()
        page.set_default_timeout(30_000)
        await page.goto(META_BUSINESS_URL, wait_until="domcontentloaded", timeout=120_000)
        await page.locator("body").wait_for(state="visible", timeout=30_000)
        return browser, context, page
    except Exception:
        await browser.close()
        raise


async def dismiss_guidance_cards(page: Page) -> None:
    """关闭带明确 GeoGuidanceCard 业务标识的说明卡，不处理未知弹窗。"""
    # 中英日卡片中关闭按钮无 aria-label，了解更多带 aria-label；不用 Close/关闭/閉じる 文案。
    close_buttons = page.locator('[data-surface$="lib:GeoGuidanceCard"] [role="button"]:not([aria-label]):visible')
    # data-surface 可能同时出现在包裹节点和日志节点上；直接选其后代按钮，由 CSS 去重。
    for close in await close_buttons.all():
        await close.click()
        await expect(close).to_be_hidden()


async def _is_business_logged_out(page: Page) -> bool:
    url = page.url.lower()
    if "/login" in url or "checkpoint" in url or "two_step_verification" in url:
        return True
    if await page.locator('input[name="email"]').count() and await page.locator('input[name="email"]').first.is_visible():
        return True
    # 导航 href 与页面业务 surface 均独立于显示语言；空白页不能作为已登录证据。
    navigation = page.locator('a[href*="/latest/home"]')
    return not await navigation.filter(visible=True).count()



async def meta_cookie_auth(account_file: str | Path, *, proxy: str | None = None) -> bool:
    account_file = Path(account_file)
    if not account_file.is_file():
        return False
    async with async_playwright() as playwright:
        browser, context, page = await _open_business_page(
            playwright, account_file, proxy=proxy, headless=True
        )
        try:
            return not await _is_business_logged_out(page)
        finally:
            await browser.close()


async def meta_setup(
    account_file: str | Path,
    *,
    handle: bool = False,
    proxy: str | None = None,
    headless: bool = False,
    return_detail: bool = False,
):
    account_file = Path(account_file)
    account_file.parent.mkdir(parents=True, exist_ok=True)
    if await meta_cookie_auth(account_file, proxy=proxy):
        result = {"success": True, "status": "cookie_valid", "account_file": str(account_file)}
        return result if return_detail else True
    if not handle:
        result = {"success": False, "status": "cookie_invalid", "account_file": str(account_file)}
        return result if return_detail else False

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            channel="chrome", headless=headless, proxy=_proxy_options(proxy)
        )
        try:
            # 已有 Facebook 登录态可作为 Business Suite 的初始 Cookie，避免重复登录。
            source = account_file
            context = await browser.new_context(storage_state=str(source) if source.is_file() else None)
            page = await context.new_page()
            page.set_default_timeout(30_000)
            await page.goto(META_BUSINESS_URL, wait_until="domcontentloaded", timeout=120_000)
            deadline = asyncio.get_running_loop().time() + 600
            while asyncio.get_running_loop().time() < deadline:
                if not await _is_business_logged_out(page):
                    await context.storage_state(path=str(account_file))
                    result = {
                        "success": True,
                        "status": "logged_in",
                        "account_file": str(account_file),
                        "current_url": page.url,
                    }
                    return result if return_detail else True
                await page.wait_for_timeout(1000)
            result = {"success": False, "status": "timeout", "account_file": str(account_file)}
            return result if return_detail else False
        finally:
            await browser.close()


class MetaBusinessUploader(BaseVideoUploader):
    """Business Suite 中的 Facebook Page 视频和图文发布器。"""

    def __init__(
        self,
        platform: str,
        account_file: str | Path,
        *,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        video_file: str | Path | None = None,
        image_files: list[str | Path] | None = None,
        schedule: datetime | int = 0,
        page_name: str | None = None,
        proxy: str | None = None,
        headless: bool = False,
        result_file: str | Path | None = None,
    ):
        if platform not in META_PLATFORMS:
            raise ValueError(f"不支持的 Meta Business 平台: {platform}")
        if not title.strip():
            raise ValueError("标题不能为空")
        if bool(video_file) == bool(image_files):
            raise ValueError("必须且只能传入视频或图片文件")
        self.platform = platform
        self.account_file = Path(account_file)
        self.title = title.strip()
        self.description = description.strip()
        self.tags = [tag.strip().lstrip("#") for tag in (tags or []) if tag.strip().lstrip("#")]
        self.video_file = Path(video_file) if video_file else None
        self.image_files = [Path(item) for item in (image_files or [])]
        self.schedule = self.validate_publish_date(schedule)
        self.page_name = page_name.strip() if page_name else None
        self.proxy = proxy
        self.headless = headless
        self.result_file = Path(result_file) if result_file else Path('.local/meta-results') / f'{uuid4().hex}.json'
        self.result = {"platform": platform, "title": self.title, "status": "not_submitted"}

    def _caption(self) -> str:
        parts = [self.title, self.description] if self.description else [self.title]
        if self.tags:
            parts.append(" ".join(f"#{tag}" for tag in self.tags))
        return "\n\n".join(parts)

    async def _select_publish_location(self, page: Page) -> None:
        # 发布位置的可访问名称区别于正文和 CTA 的 combobox，不依赖全页顺序。
        # 发布主体选择器带 Facebook 品牌徽标；CTA 下拉框和正文均没有该徽标。
        # 中英文实际页面均保留此品牌 alt，避免依赖“发布位置/Post to”的翻译。
        combo = page.locator('[data-surface$="bizweb_create_post:left_panel"] [role="combobox"][aria-haspopup="listbox"]').filter(has=page.locator('img[alt="Facebook"]'))
        await combo.wait_for(state="visible")
        if self.page_name and self.page_name not in await combo.inner_text():
            await combo.click()
            option = page.get_by_role("option", name=self.page_name, exact=True)
            if not await option.count():
                raise RuntimeError(f"Business Suite 未找到指定发布主体: {self.page_name}")
            await option.click()
        if self.page_name:
            await expect(combo).to_contain_text(self.page_name)
        else:
            self.page_name = (await combo.inner_text()).replace('\u200b', '').strip()
        assets = parse_qs(urlparse(page.url).query).get('asset_id', [])
        if len(assets) != 1 or not assets[0].isdigit():
            raise RuntimeError("无法核实当前 Page asset_id，未提交")
        self.result.update(page_id=assets[0], page_name=self.page_name, expected_text=self.title)

    async def _upload_files(self, page: Page) -> None:
        # 页面可能保留隐藏的响应式布局；按钮语义及 visible 限定当前实际上传入口。
        # 空媒体区的业务顺序为本地影音上传、可选 AI 生成；中英文实测分别有 1/2 个入口。
        # 仅接受空区这两种结构，上传后生成的编辑/移除动作不能混入；不按翻译或图标路径匹配。
        media = page.locator('[data-surface$="lib:bizweb_create_post:media"]')
        await expect(media.locator('img')).to_have_count(0)
        entries = media.get_by_role('button')
        if await entries.count() not in (1, 2):
            raise RuntimeError('空媒体区结构未识别，未上传')
        trigger = entries.nth(0)
        files = [str(self.video_file)] if self.video_file else [str(path) for path in self.image_files]
        async with page.expect_file_chooser() as chooser_info:
            await trigger.click()
        await (await chooser_info.value).set_files(files)
        # 视频在新版 Business Suite 会进入“创建 Reels”向导，不渲染 video 标签；
        # 图片则留在原 composer。两种状态都必须等到文件名或向导业务标题出现。
        if self.video_file:
            await page.get_by_text(self.video_file.name, exact=True).wait_for(state="visible", timeout=180_000)
            # 新版 Reel 向导有独立业务 surface；不依赖 Create reel/创建 Reels 标题。
            await page.locator('[data-surface$="lib:bizweb_create_reel"]').wait_for()
            await dismiss_guidance_cards(page)
            await page.get_by_text('100%', exact=True).wait_for(state='visible', timeout=180000)
        else:
            # 上传后媒体区生成服务端预览及像素尺寸；不以中文“移除照片”或正文框代表上传完成。
            await expect(media.locator('img')).to_have_count(len(files), timeout=180000)
            await expect(media.get_by_text(re.compile(r"^\d+ x \d+$")).filter(visible=True)).to_have_count(len(files), timeout=180000)

    async def _fill_caption(self, page: Page) -> None:
        # Reel 标题为 left_panel 中唯一普通 text input；关键词输入另有 combobox 角色。
        reels_title = page.locator('[data-surface$="bizweb_create_reel:left_panel"] input[type="text"]:not([role]):visible')
        separate_title = self.video_file and await reels_title.count() and await reels_title.is_visible()
        if separate_title:
            await reels_title.fill(self.title)
        # 实测同名隐藏 textbox 与可见 combobox 并存；只匹配当前向导可见正文，防止误填旧布局。
        # 当前可见 contenteditable 是正文；隐藏 textbox 属于旧布局，角色会随图文/Reel 改变。
        editor = page.locator('[contenteditable="true"]:visible')
        await expect(editor).to_have_count(1)
        await editor.wait_for(state="visible", timeout=30_000)
        caption = self.description if separate_title else self._caption()
        if self.tags and separate_title:
            caption = f"{caption}\n\n{' '.join(f'#{tag}' for tag in self.tags)}" if caption else " ".join(f"#{tag}" for tag in self.tags)
        if not caption and not self.video_file:
            caption = self._caption()
        await editor.fill(caption)
        if (await editor.inner_text()).strip() != caption:
            raise RuntimeError("Business Suite 正文未读回预期内容")

    async def _advance_reels(self, page: Page) -> None:
        if not self.video_file:
            return
        root = page.locator('[data-surface$="lib:bizweb_create_reel"]')
        # 向导的三个步骤有 aria-labelledby，当前步骤有 aria-current；缩略图切换没有。
        steps = root.locator('[role="button"][aria-labelledby]:not([aria-haspopup])')
        await expect(steps).to_have_count(3)
        # 两次下一步都来自 footer，不与缩略图的上/下一张混选；带 aria-label 的是反馈入口。
        # 已实测创建、编辑、分享三阶段底栏均为返回/取消 + 主动作这两个业务按钮。
        for index in (0, 1):
            await expect(steps.nth(index)).to_have_attribute('aria-current', 'step')
            actions = page.locator('[data-surface$="bizweb_create_reel:footer"] [role="button"]:not([aria-label])')
            await expect(actions).to_have_count(2)
            await expect(actions.nth(1)).to_be_enabled(timeout=180000)
            await actions.nth(1).click()
            await expect(steps.nth(index + 1)).to_have_attribute('aria-current', 'step')
        # 快拍开关与当前 Page 的 Facebook 徽标属于同一单开关业务组；其余开关没有品牌图片。
        story = page.locator('[data-surface$="bizweb_create_reel:left_panel"] input[role="switch"]').locator(
            'xpath=self::input[ancestor::div[.//img[@alt="Facebook"] and count(.//input[@role="switch"])=1]]')
        await expect(story).to_have_count(1)
        if await story.is_checked():
            await story.click()
            # Once 是平台真实选项值，只关闭本条快拍分享；Always 会改变后续默认设置。
            dialog = page.get_by_role('dialog').filter(has=page.locator('input[type="radio"][value="Once"]'))
            await expect(dialog).to_have_count(1)
            await dialog.locator('input[value="Once"]').check()
            actions = dialog.get_by_role('button')
            # 实测确认框三项为关闭、取消、确认；严格核对数量后使用该业务顺序。
            await expect(actions).to_have_count(3)
            await actions.nth(2).click()
            await expect(dialog).to_have_count(0)
            await expect(story).not_to_be_checked()

    async def _fill_schedule(self, page: Page) -> None:
        if not self.schedule:
            return
        # 此表单按浏览器本地时区解释时间，当前真实验证为 Asia/Shanghai。
        zone = await page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone")
        if zone != "Asia/Shanghai" or self.schedule.tzinfo is not None:
            raise ValueError("当前 Meta 定时要求 Asia/Shanghai 浏览器及不带时区的北京时间输入")
        if self.video_file:
            region = page.locator('[data-surface$="bizweb_create_reel:left_panel"]')
            # 分享阶段的三种发布模式是立即、定时、草稿；其 aria-pressed 表示模式，非提交。
            modes = region.locator('[role="button"][aria-pressed]').locator('xpath=self::*[not(ancestor::*[@role="grid"])]')
            await expect(modes).to_have_count(3)
            await modes.nth(1).click()
            await expect(modes.nth(1)).to_have_attribute('aria-pressed', 'true')
        else:
            region = page.locator('[data-surface$="lib:bizweb_create_post:publishing_options"]')
            await region.locator('input[role="switch"]').check()
        # 日期是定时区唯一有 placeholder 的普通 input；小时/分钟靠语义数值范围区分。
        date_input = region.locator('input[placeholder]:not([role])')
        await expect(date_input).to_have_count(1)
        await date_input.click()
        grid = region.locator('[role="grid"][aria-labelledby]')
        await expect(grid).to_have_count(1)
        # 日历 aria-labelledby 实测含月、年，前缀 js_* 随会话变化，只解析其日期后缀。
        month_id = await grid.get_attribute('aria-labelledby')
        match = re.search(r'-(\d{1,2})-(\d{4})$', month_id or '')
        if not match:
            raise RuntimeError('无法读取日历的月份/年份，未提交')
        month, year = map(int, match.groups())
        month_delta = (self.schedule.year - year) * 12 + self.schedule.month - month
        if abs(month_delta) > 12:
            raise ValueError('定时日期超出已验证日历范围')
        # 日历非 grid 内的两个按钮分别为上一月/下一月；日按钮属于 gridcell，排除它们。
        calendar = grid.locator('xpath=ancestor::div[.//*[@role="button"][@aria-busy]][1]')
        navigation = calendar.locator('[role="button"][aria-busy]')
        await expect(navigation).to_have_count(2)
        for _ in range(abs(month_delta)):
            await navigation.nth(1 if month_delta > 0 else 0).click()
        await expect(grid).to_have_attribute('aria-labelledby', re.compile(fr'-{self.schedule.month}-{self.schedule.year}$'))
        # 已核对日历年月后按日期数字选择，避免依赖 aria-label 的星期/月名翻译。
        day = grid.get_by_role('button').filter(has_text=re.compile(fr'^{self.schedule.day}$'))
        await expect(day).to_have_count(1)
        if await day.get_attribute('aria-disabled') == 'true':
            raise ValueError('平台日历不允许选定日期，未提交')
        await day.click()
        hour = region.locator('[role="spinbutton"][aria-valuemax="23"], [role="spinbutton"][aria-valuemax="12"]')
        await expect(hour).to_have_count(1)
        twelve_hour = await hour.get_attribute('aria-valuemax') == '12'
        value_hour = (self.schedule.hour % 12 or 12) if twelve_hour else self.schedule.hour
        for control, value in ((hour, value_hour), (region.locator('[role="spinbutton"][aria-valuemax="59"]'), self.schedule.minute)):
            await control.click()
            for digit in f'{value:02d}':
                await control.press(digit)
            await control.press('Tab')
            await expect(control).to_have_attribute('aria-valuenow', str(value))
        if twelve_hour:
            # AM/PM 的真实数值是 0/1；按键切换后读回，拒绝只填小时造成 12 小时偏差。
            period = region.locator('[role="spinbutton"][aria-valuemax="1"]')
            target = str(int(self.schedule.hour >= 12))
            if await period.get_attribute('aria-valuenow') != target:
                await period.press('ArrowUp')
            await expect(period).to_have_attribute('aria-valuenow', target)
        # 日期控件在中英日页面实测读回均包含年月日数字；允许分隔符本地化，不猜月份名称。
        parts = [int(part) for part in re.findall(r'\d+', await date_input.input_value())]
        if parts != [self.schedule.year, self.schedule.month, self.schedule.day]:
            raise RuntimeError(f'日期未读回请求值：{await date_input.input_value()}')

    async def _publish(self, page: Page) -> None:
        # 图文底栏的业务动作固定为取消、存草稿、最终提交；限定 footer 并严格核对三项，
        # 只在已观察的布局中采用此业务顺序，布局变化时停止，禁止用全页同名按钮或猜测翻译。
        if not self.video_file:
            actions = page.locator('[data-surface$="lib:bizweb_create_post:footer"] [role="button"]')
            await expect(actions).to_have_count(3)
            button = actions.nth(2)
        else:
            # 分享阶段仍为返回 + 最终主动作，不能选择顶部 Share 步骤导航。
            actions = page.locator('[data-surface$="bizweb_create_reel:footer"] [role="button"]:not([aria-label])')
            await expect(actions).to_have_count(2)
            button = actions.nth(1)
        await expect(button).to_be_enabled()
        self.result['status'] = 'submission_unknown'
        self.result_file.parent.mkdir(parents=True, exist_ok=True)
        self.result_file.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')
        # 只捕获本次点击触发的创建作品响应；上传素材 ID 和广告建议中的 story ID 都不能代替内容编号。
        async with page.expect_response(lambda response: '/api/graphql' in response.url and
                parse_qs(response.request.post_data or '').get('fb_api_req_friendly_name') == ['BusinessComposerStoryCreationMutation'], timeout=90000) as response_info:
            await button.click()
        payload = await (await response_info.value).json()
        if payload.get('errors'):
            raise RuntimeError('平台创建作品响应包含错误；请查原记录，勿重复提交')
        creation = payload.get('data', {}).get('xfamily_content_create', {})
        if any(creation.get('errors', {}).values()):
            raise RuntimeError('平台返回作品创建错误；请查原记录，勿重复提交')
        items = creation.get('items')
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list) or len(items) != 1:
            raise RuntimeError('已提交但未取得唯一内容编号；结果待查询')
        # 实测 Reels 响应的 pending_publish_content_id 为空，需在成功确认后查原作品详情。
        pending_id = items[0].get('pending_publish_content_id')
        if pending_id:
            self.result['content_id'] = str(pending_id)
        self.result_file.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')
        if self.video_file:
            # 创建响应后页面仍执行后续发布步骤，不能立即导航走；实测完成框带本次标题、
            # 作品预览及关闭/完成两个动作。标题是本次业务参数，非某种语言的成功文案。
            completion = page.locator('[role="dialog"][aria-labelledby][tabindex="-1"]').filter(has_text=self.title)
            await expect(completion).to_have_count(1, timeout=120000)
            await expect(completion.get_by_role('heading')).to_have_count(1)
            await expect(completion.get_by_role('button')).to_have_count(2)
            # 完成框两个动作均是关闭/完成；点击最后一个代表平台已受理本次 Reel。
            await completion.get_by_role('button').last.click()
            await expect(completion).to_have_count(0)
            if not self.schedule:
                # Reel 创建响应实测可能没有 pending_publish_content_id，作品列表也可能在视频处理期间不展示。
                # 完成弹窗和无错误的创建响应已经是“提交成功、正在处理”的业务证据；编号只用于后续核验/删除，不能阻断发布结果。
                self.result['status'] = 'processing'
                self.result['schedule'] = None
                self.result['timezone'] = 'Asia/Shanghai'
                self.result_file.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')
                return
        # 创建响应明确受理后按 Page 和原作品编号查询；不依赖任何语言的成功提示。
        # 定时作品必须读回排期；图文立即发布必须读回原作品；这两类结果不能只凭弹窗判断。
        from uploader.meta_uploader.facebook_page_uploader.posts import open_meta_post
        state = 'scheduled_posts' if self.schedule else 'published_posts'
        list_url = f'https://business.facebook.com/latest/posts/{state}?asset_id={self.result["page_id"]}'
        _, content_id, _ = await open_meta_post(page, list_url=list_url, page_name=self.page_name,
            expected_text=self.title, content_id=self.result.get('content_id'), schedule=self.schedule)
        self.result['content_id'] = content_id
        self.result['status'] = 'scheduled' if self.schedule else ('processing' if self.video_file else 'published')
        self.result['schedule'] = self.schedule.isoformat() if self.schedule else None
        self.result['timezone'] = 'Asia/Shanghai'

    async def upload(self) -> dict:
        if self.video_file:
            self.validate_video_file(self.video_file)
        for path in self.image_files:
            self.validate_image_file(path)
        async with async_playwright() as playwright:
            browser, context, page = await _open_business_page(
                playwright, self.account_file, proxy=self.proxy, headless=self.headless
            )
            try:
                if await _is_business_logged_out(page):
                    raise RuntimeError("Business Suite 登录态失效，请先执行对应平台 login")
                await dismiss_guidance_cards(page)
                await self._select_publish_location(page)
                await self._upload_files(page)
                await self._fill_caption(page)
                await self._advance_reels(page)
                await self._fill_schedule(page)
                await self._publish(page)
                await context.storage_state(path=str(self.account_file))
                return self.result
            finally:
                self.result_file.parent.mkdir(parents=True, exist_ok=True)
                self.result_file.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')
                await browser.close()
