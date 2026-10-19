"""Business Suite 原作品查询及删除，使用内容编号而非标题作为身份依据。"""

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from patchright.async_api import async_playwright, expect, TimeoutError as BrowserTimeoutError

from uploader.meta_uploader.facebook_page_uploader.main import _open_business_page


async def open_meta_post(page, *, list_url: str, page_name: str, expected_text: str,
                         content_id: str | None = None, schedule=None):
    """查询唯一配文、核对 Page 并打开详情，发布后及删除前共用此原作品核验。"""
    # 新建 Reels 已出现在列表时，平台搜索仍可能无结果；读取原始列表避免搜索索引延迟。
    # 当前仅覆盖列表已加载的作品，超时明确报错，不以同文案的其他作品代替。
    # Reels 创建响应先受理，随后才进入内容列表；首次列表可能是处理完成前的快照。
    # 只刷新查询原作品，绝不在此重发；每次读取有界且配文出现多个时立即停止。
    deadline = asyncio.get_running_loop().time() + 120
    row = page.get_by_role("row").filter(has_text=expected_text)
    while True:
        await page.goto(list_url, wait_until="domcontentloaded", timeout=90000)
        try:
            await row.wait_for(state='visible', timeout=10000)
        except BrowserTimeoutError:
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError('原作品列表未找到请求记录；结果待核实，禁止直接重发')
        else:
            await expect(row).to_have_count(1)
            break
    await expect(row).to_contain_text(page_name)
    if parse_qs(urlparse(page.url).query).get('asset_id') != parse_qs(urlparse(list_url).query).get('asset_id'):
        raise RuntimeError('列表实际 Page ID 与请求不一致；未删除')
    is_reel = 'Reels' in await row.inner_text()
    # 已发布列表的 TITLE 网格单元承载详情入口，指标也有 aria-pressed，不能混选。
    # 已定时列表仍为旧布局，标题是唯一可选中的详情按钮。
    title = row.locator('[role="gridcell"][data-surface$=":TITLE"]') if '/published_posts' in list_url else row.locator('[role="button"][aria-pressed]')
    await expect(title).to_have_count(1)
    await title.click()
    if schedule:
        await expect(row).to_contain_text(f'{schedule.month}月{schedule.day}日 {schedule:%H:%M}')
    if '/published_posts' in list_url:
        # 新版已发布列表进入成效详情，URL 的 content_id 为“复制帖子编号”对应原作品编号。
        await page.wait_for_url('**/object_insights/**', timeout=30000)
        # URL 先变化，旧列表可能仍保留多个菜单；先等成效正文挂载，再限定可见菜单。
        await page.locator('[data-surface$="BizWebObjectinsightsHeaderActionDropdown"] [aria-haspopup="menu"]').wait_for(timeout=120000)
        query = parse_qs(urlparse(page.url).query)
        ids = query.get('content_id', [])
        if len(ids) != 1 or not ids[0].isdigit() or query.get('asset_id') != parse_qs(urlparse(list_url).query).get('asset_id'):
            raise RuntimeError('成效详情缺少唯一作品编号或 Page 不匹配；未删除')
        actual_id = ids[0]
    else:
        # 旧详情面板以 aria-labelledby 关联三级标题，紧邻的 div 是原作品编号字段。
        # 读取末尾数字而非中文“编号：”；标题、配文及行内播放量不能充当编号。
        detail = page.locator('div[aria-labelledby]').filter(has=page.locator('[role="heading"][aria-level="3"] + div')).filter(visible=True)
        if await detail.count():
            await expect(detail).to_have_count(1, timeout=30000)
            number = detail.locator('[role="heading"][aria-level="3"] + div')
            await expect(number).to_have_count(1)
            number_text = await number.inner_text()
        else:
            # 受控测试页没有完整详情容器；数字字段仍须独立、唯一，不能回退到标题或行文本。
            number = page.get_by_text(re.compile(r'^编号：\d+$'))
            await expect(number).to_have_count(1, timeout=30000)
            number_text = await number.inner_text()
        match = re.search(r'(\d+)$', number_text.strip())
        if not match:
            raise RuntimeError('详情编号字段未包含原作品 ID；未删除')
        actual_id = match.group(1)
    if content_id is not None and actual_id != content_id:
        raise RuntimeError(f'原作品编号不匹配：期望 {content_id}，页面 {actual_id}；未删除')
    return row, actual_id, is_reel


async def meta_post_action(account_file: Path, *, page_id: str, page_name: str,
                           content_id: str, expected_text: str, scheduled: bool = False,
                           delete: bool = False, proxy: str | None = None,
                           headless: bool = False) -> dict:
    """按 Page、内容编号、配文三项核对；定时作品永久删除，已发布作品移至垃圾箱。"""
    if not page_id.isdigit() or not content_id.isdigit() or not page_name.strip() or not expected_text.strip():
        raise ValueError("需要数字 page-id/content-id、Page 名和用于核验的配文")
    async with async_playwright() as playwright:
        browser, context, page = await _open_business_page(playwright, account_file, proxy=proxy, headless=headless)
        try:
            state = "scheduled_posts" if scheduled else "published_posts"
            list_url = f"https://business.facebook.com/latest/posts/{state}?asset_id={page_id}"
            row, actual_id, is_reel = await open_meta_post(page, list_url=list_url, page_name=page_name,
                                                   expected_text=expected_text, content_id=content_id)
            result = {"platform": "facebook-page", "page_id": page_id, "page_name": page_name,
                      "content_id": content_id, "expected_text": expected_text,
                      "status": "scheduled" if scheduled else "published"}
            if delete:
                # 已发布作品详情菜单有明确的删除业务 Action 标识；标题编号已核对，
                # 不用“打开下拉菜单/删除帖子”等翻译，也不在全页查同名按钮。
                if scheduled:
                    # 旧详情的动作菜单无独立 Action surface；限定带三级标题的详情面板，
                    # 排除有 aria-label 的原帖预览菜单。实测五项依次编辑、复制、改期、移草稿、删除。
                    detail = page.locator('div[aria-labelledby]').filter(has=page.locator('[role="heading"][aria-level="3"] + div')).filter(visible=True)
                    await expect(detail).to_have_count(1)
                    menu_button = detail.locator('[role="button"][aria-haspopup="menu"]:not([aria-label])')
                    await expect(menu_button).to_have_count(1)
                    await menu_button.click()
                    items = page.get_by_role('menu').get_by_role('menuitem')
                    count = await items.count()
                    if count not in (4, 5):
                        raise RuntimeError(f'定时详情操作菜单结构未识别：{count} 项，未删除')
                    # 删除始终是该菜单最后一项；菜单本地化或权限不同会少一个“移到草稿”。
                    await items.nth(count - 1).click()
                else:
                    dropdown = page.locator('[data-surface$="BizWebObjectinsightsHeaderActionDropdown"] [aria-haspopup="menu"]')
                    await expect(dropdown).to_have_count(1)
                    await dropdown.click()
                    action = page.locator('[data-surface$="match_container:TofuObjectInsightsDeleteAction"] [role="menuitem"]')
                    await expect(action).to_have_count(1)
                    await action.click()
                # 真实确认框有 dialog/aria-labelledby/tabindex=-1；旧实现误判为无 dialog。
                # 详情面板不具备这组属性。确认框三项业务顺序为关闭、取消、主动作，
                # 数量/范围任一变化都停止，不靠中文文案或任意全页最后按钮执行破坏性操作。
                dialog = page.locator('[role="dialog"][aria-labelledby][tabindex="-1"]').filter(visible=True)
                await expect(dialog).to_have_count(1)
                actions = dialog.get_by_role('button')
                await expect(actions).to_have_count(2)
                await actions.nth(1).click()
                await expect(dialog).to_have_count(0, timeout=30000)
                await expect(row).to_have_count(0, timeout=45000)
                if not scheduled:
                    # 成效详情删除后由平台导航回列表；等这次导航结束，避免刷新与它竞争而 ERR_ABORTED。
                    await page.wait_for_url('**/posts/published_posts**', wait_until='domcontentloaded', timeout=90000)
                # 删除后重新请求服务器列表，避免仅依据前端乐观移除判定成功；只查询，不重删。
                deadline = asyncio.get_running_loop().time() + 60
                while True:
                    await page.goto(list_url, wait_until="domcontentloaded", timeout=90000)
                    # 无筛选列表有作品行或平台明确空态才算加载结束；搜索索引延迟不能证明已删除。
                    loaded = page.get_by_role('row').filter(has=page.locator('[role="button"][aria-pressed]')).or_(page.get_by_text('没有定时帖', exact=True))
                    try:
                        await expect(loaded).not_to_have_count(0, timeout=10000)
                        await expect(page.get_by_role('row').filter(has_text=expected_text)).to_have_count(0, timeout=10000)
                    except BrowserTimeoutError:
                        if asyncio.get_running_loop().time() >= deadline:
                            raise TimeoutError("已提交删除，但刷新后的列表尚未确认原作品消失；请先查询，勿重复删除")
                    else:
                        break
                result["status"] = "deleted" if scheduled else "trashed"
            result["checked_at"] = datetime.now(timezone.utc).isoformat()
            await context.storage_state(path=str(account_file))
            return result
        except Exception:
            # 保留发生异常时的真实页面，便于定位改版或结果未知，不重试远端删除。
            directory = Path('.local/meta-errors') / uuid4().hex
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'page.txt').write_text(page.url + '\n' + await page.locator('body').inner_text(), encoding='utf-8')
            await page.screenshot(path=str(directory / 'page.png'))
            raise
        finally:
            await browser.close()
