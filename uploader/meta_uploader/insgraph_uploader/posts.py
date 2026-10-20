"""Instagram 原作品核验及移至最近删除。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from patchright.async_api import Page, async_playwright, expect

from .main import _open_instagram_page, instagram_identity, instagram_response_payload


def instagram_post_id(post_url: str) -> str:
    """接受站点实际提供的短链接和带作者的链接，拒绝外域及非作品地址。"""
    parsed = urlparse(post_url)
    if parsed.scheme != 'https' or parsed.hostname not in {'www.instagram.com', 'instagram.com'} or parsed.username or parsed.password or parsed.port:
        raise ValueError('Instagram 原作品必须是官方 HTTPS 链接')
    match = re.fullmatch(r'/(?:[A-Za-z0-9_.]+/)?(?:p|reel)/([A-Za-z0-9_-]+)/?', parsed.path)
    if not match:
        raise ValueError('Instagram 原作品链接必须包含 /p/<编号>/ 或 /reel/<编号>/')
    return match.group(1)


async def find_instagram_post(page: Page, *, post_url: str, expected_text: str, owner_id: str) -> dict:
    """核对详情的规范链接、作者 ID 和正文，返回当前作品的数字 ID。"""
    shortcode = instagram_post_id(post_url)
    if not expected_text.strip():
        raise ValueError('expected_text 不能为空')
    # 同一作品通过 /p/ 进入详情，避免 /reel/ 路由进入带其他作品的全屏推荐播放器。
    await page.goto(f'https://www.instagram.com/p/{shortcode}/', wait_until='domcontentloaded', timeout=120_000)
    # 作品页 head 的 og:url、instapp:owner_user_id 是平台实际输出的规范链接/作者元数据，
    # 不根据主页推荐作品或同文案猜作者；正文限定 main 排除导航及其他窗口。
    canonical = page.locator('meta[property="og:url"]')
    owner = page.locator('meta[property="instapp:owner_user_id"]')
    await expect(canonical).to_have_count(1)
    await expect(owner).to_have_count(1)
    if instagram_post_id(await canonical.get_attribute('content')) != shortcode:
        raise RuntimeError('Instagram 当前原作品编号不匹配')
    if await owner.get_attribute('content') != owner_id:
        raise RuntimeError('Instagram 原作品作者与当前登录用户不匹配')
    main = page.locator('main')
    await expect(main).to_have_count(1)
    await expect(main).to_contain_text(expected_text, timeout=60_000)
    # 详情元描述包含原作品配文，评论区不进入该字段；双重核对防止同一句话只出现在评论中。
    caption_metadata = page.locator('meta[name="description"]')
    await expect(caption_metadata).to_have_count(1)
    if expected_text not in (await caption_metadata.get_attribute('content') or ''):
        raise RuntimeError('Instagram 原作品配文元数据不包含预期文字，请使用原配文中的短句核验')
    # 照片、轮播、Reel 的详情都输出同一个 App 深链元数据，包含当前作品数字 ID。
    # 使用平台作品身份字段，排除推荐作品和内部查询变量的结构差异。
    deep_link = page.locator('meta[property="al:ios:url"]')
    await expect(deep_link).to_have_count(1)
    match = re.fullmatch(r'instagram://media\?id=(\d+)', await deep_link.get_attribute('content'))
    if not match:
        raise RuntimeError('Instagram 详情页未提供当前作品数字 ID')
    return {'post_id': shortcode, 'content_id': f'{match.group(1)}_{owner_id}', 'post_url': post_url,
            'owner_id': owner_id, 'expected_text': expected_text, 'status': 'published'}


async def instagram_post_action(account_file: Path, *, post_url: str, expected_text: str, delete: bool = False,
                                proxy: str | None = None, headless: bool = False,
                                result_file: str | Path | None = None) -> dict:
    """核对原作品后执行一次删除，只接受目标 ID 的 did_delete 业务响应。"""
    instagram_post_id(post_url)
    result_file = Path(result_file) if result_file else Path('.local/instagram-results') / f'{uuid4().hex}.json'
    result = {'platform': 'instagram', 'post_url': post_url, 'status': 'not_submitted'}
    async with async_playwright() as p:
        browser, context, page = await _open_instagram_page(p, account_file, proxy=proxy, headless=headless)
        try:
            identity = await instagram_identity(page, account_file)
            result.update(await find_instagram_post(page, post_url=post_url, expected_text=expected_text, owner_id=identity['user_id']))
            if delete:
                # 当前详情唯一的三圆点菜单按钮含 aria-haspopup=dialog；评论表情菜单不含 circle，
                # 该结构已在中英文照片、轮播、Reel 详情观察，避免翻译后的 aria-label。
                menu_button = page.locator('[role="button"][aria-haspopup="dialog"]').filter(has=page.locator('svg circle'))
                await expect(menu_button).to_have_count(1)
                await menu_button.click()
                menu = page.get_by_role('dialog')
                buttons = menu.get_by_role('button')
                # 自己的作品菜单已观察固定八项，首项为删除；role 同时涵盖原生/非原生按钮。
                # 数量断言配合已核对的作者和原作品身份，结构改变即报错，不转点其他菜单。
                await expect(buttons).to_have_count(8, timeout=30_000)
                # 实测鼠标激活有时只关闭弹出菜单；该 role=button 支持 Enter，键盘激活正常进入确认框。
                await buttons.nth(0).press('Enter')
                # 确认框是带标题的模态 dialog，只有删除、取消两项，删除固定在首位。
                # 与前一菜单严格区分；不把菜单关闭当成已删除。
                confirm = page.locator('[role="dialog"][aria-modal="true"]').filter(has=page.get_by_role('heading'))
                await expect(confirm).to_have_count(1, timeout=60_000)
                confirm_buttons = confirm.get_by_role('button')
                await expect(confirm_buttons).to_have_count(2)
                result['status'] = 'deletion_unknown'
                result_file.parent.mkdir(parents=True, exist_ok=True)
                result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                target = f"/api/v1/web/create/{result['content_id']}/delete/"
                async with page.expect_response(lambda r: urlparse(r.url).path == target and r.request.method == 'POST', timeout=60_000) as event:
                    await confirm_buttons.nth(0).press('Enter')
                payload = instagram_response_payload(await (await event.value).text())
                if payload.get('payload', {}).get('did_delete') is not True:
                    raise RuntimeError('Instagram 未确认目标作品删除成功')
                result['status'] = 'deleted'
            result_file.parent.mkdir(parents=True, exist_ok=True)
            result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            await context.storage_state(path=str(account_file))
            return result
        except Exception as error:
            folder = Path('.local/instagram-errors') / uuid4().hex
            folder.mkdir(parents=True)
            result.update(error=str(error), evidence_dir=str(folder))
            result_file.parent.mkdir(parents=True, exist_ok=True)
            result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            await page.screenshot(path=str(folder/'page.png'))
            (folder/'page.html').write_text(await page.content(), encoding='utf-8')
            raise RuntimeError(f'Instagram 原作品操作未完成；结果记录: {result_file}；原因: {error}') from error
        finally:
            await browser.close()
