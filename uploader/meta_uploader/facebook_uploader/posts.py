"""查询个人主页的原作品，并按核实的作品 ID 移至垃圾箱。"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

from patchright.async_api import Page, async_playwright, expect

from uploader.meta_uploader.facebook_uploader.main import _open_facebook_page


def facebook_post_id(url: str) -> str:
    """只接受 Facebook 原作品链接，不把个人主页或外部网址当成删除对象。"""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"www.facebook.com", "facebook.com"}:
        raise ValueError("作品链接必须是 https://www.facebook.com/ 下的原作品")
    match = re.fullmatch(r"/(?:reel|posts|videos)/(\d+|pfbid[A-Za-z0-9]+)/?", parsed.path)
    if not match:
        match = re.fullmatch(r"/[A-Za-z0-9._-]+/(?:posts|videos)/(\d+|pfbid[A-Za-z0-9]+)/?", parsed.path)
    if match:
        return match.group(1)
    if parsed.path == "/permalink.php":
        ids = parse_qs(parsed.query).get("story_fbid", [])
        if len(ids) == 1 and re.fullmatch(r'\d+|pfbid[A-Za-z0-9]+', ids[0]):
            return ids[0]
    raise ValueError("无法从作品链接中读取明确的作品 ID")


async def find_facebook_post(page: Page, *, post_url: str, owner_id: str, expected_text: str):
    """在当前登录用户的个人主页中，交叉核对正文、作者和作品链接。"""
    post_id = facebook_post_id(post_url)
    if not owner_id.isdigit() or not expected_text.strip():
        raise ValueError("需要数字 owner-id 和非空 expected-text 核验原作品")
    # c_user 是本次浏览器登录主体；禁止用另一个账号对给定个人主页执行删除。
    cookies = await page.context.cookies("https://www.facebook.com/")
    users = {cookie["value"] for cookie in cookies if cookie["name"] == "c_user"}
    if users != {owner_id}:
        raise RuntimeError("当前 Facebook 登录用户与 owner-id 不一致")
    await page.goto(f"https://www.facebook.com/profile.php?id={owner_id}", wait_until="domcontentloaded", timeout=90000)
    # article 是主页作品卡片，正文只用于缩小范围；真正身份还要核对作品 ID 和作者链接。
    articles = page.get_by_role("article").filter(has_text=expected_text)
    deadline = asyncio.get_running_loop().time() + 45
    while asyncio.get_running_loop().time() < deadline:
        matches = []
        for article in await articles.all():
            links = await article.locator("a[href]").evaluate_all("els => els.map(e => e.href)")
            ids = set()
            for link in links:
                try:
                    ids.add(facebook_post_id(link))
                except ValueError:
                    continue
            if post_id not in ids:
                continue
            from urllib.parse import parse_qs, urlparse
            authors = [link for link in links if urlparse(link).path == "/profile.php"
                       and parse_qs(urlparse(link).query).get("id") == [owner_id]]
            if not authors:
                raise RuntimeError("原作品 ID 匹配，但作者身份未核实")
            matches.append(article)
        if len(matches) > 1:
            raise RuntimeError("主页中出现多个相同作品 ID，停止操作")
        if matches:
            return matches[0]
        # 只向下浏览现有主页，既不重发，也不把未找到解释为已删除。
        await page.mouse.wheel(0, 650)
        await page.wait_for_timeout(1000)
    raise RuntimeError("未在个人主页找到正文、作者及 ID 均匹配的原作品；未执行删除")


async def find_trashed_facebook_post(page: Page, *, post_url: str, owner_id: str, expected_text: str):
    """从垃圾箱原记录的查看链接核对作品，不用标题猜测身份。"""
    post_id = facebook_post_id(post_url)
    # 此地址来自个人主页“动态记录 → 垃圾箱”的实际导航，category_key 明确限定垃圾箱。
    await page.goto(f"https://www.facebook.com/{owner_id}/allactivity?activity_history=false&category_key=TRASH&manage_mode=true&should_load_landing_page=false",
                    wait_until="domcontentloaded", timeout=90000)
    # 查看链接保留原作品 ID；最近的含“更多选项”按钮的祖先就是单条活动记录。
    link = page.get_by_role('link', name='查看', exact=True).locator(f'xpath=self::a[contains(@href,"/{post_id}/") or contains(@href,"story_fbid={post_id}")]')
    await expect(link).to_have_count(1, timeout=30000)
    if facebook_post_id(await link.get_attribute('href')) != post_id:
        raise RuntimeError("垃圾箱查看链接的作品编号不一致")
    row = link.locator('xpath=ancestor::div[.//a[contains(@href,"profile.php?id=")] and .//*[@role="button" and contains(@aria-label,"的更多选项")]][1]')
    await expect(row).to_have_count(1)
    await expect(row).to_contain_text(expected_text)
    author = row.locator(f'a[href="https://www.facebook.com/profile.php?id={owner_id}"]')
    await expect(author).to_have_count(1)
    return row


async def trash_facebook_post(page: Page, article, *, post_url: str, owner_id: str, expected_text: str) -> str:
    """按已实测的帖子菜单进入垃圾箱；提交一次，等待平台明确确认。"""
    # 菜单按钮位于已核实的原作品卡片内，aria-label 包含“这篇帖子”，排除点赞/分享等操作。
    menu_button = article.get_by_role("button", name=re.compile(r"^可对.+的这篇帖子执行的操作$"))
    await expect(menu_button).to_have_count(1)
    await menu_button.click()
    menu = page.get_by_role("menu")
    await expect(menu).to_have_count(1)
    await menu.get_by_role("menuitem").filter(has_text="移至垃圾箱").click()
    # 同一确认弹窗中的“转移”才是最终提交动作，不点击全页同名按钮。
    dialog = page.get_by_role("dialog").filter(has_text="移至垃圾箱？")
    await expect(dialog).to_have_count(1)
    await dialog.get_by_role("button", name="转移", exact=True).click()
    # 实测没有成功 toast。等待确认窗及原卡片消失，再到垃圾箱查原 ID，不能猜成功文案。
    await expect(dialog).to_have_count(0, timeout=30000)
    await expect(article).to_have_count(0, timeout=30000)
    await find_trashed_facebook_post(page, post_url=post_url, owner_id=owner_id, expected_text=expected_text)
    return "trashed"


async def verify_facebook_deletion(page: Page, *, owner_id: str, post_url: str) -> None:
    """永久删除后允许后台列表短暂延迟，只轮询查询，不重复提交删除。"""
    post_id = facebook_post_id(post_url)
    deadline = asyncio.get_running_loop().time() + 90
    while asyncio.get_running_loop().time() < deadline:
        await page.goto(f"https://www.facebook.com/{owner_id}/allactivity?activity_history=false&category_key=TRASH&manage_mode=true&should_load_landing_page=false",
                        wait_until="domcontentloaded", timeout=90000)
        await page.get_by_text("只有你能看到垃圾箱里的内容。", exact=True).wait_for(timeout=30000)
        # 导航标题先出现，记录后到；必须等空列表文案或实际记录链接，不能把加载中当作已删除。
        empty = page.get_by_text("好冷清，一片落叶飘过~", exact=True)
        records = page.get_by_role("link", name="查看", exact=True)
        for _ in range(30):
            if await empty.is_visible() or await records.count():
                break
            await page.wait_for_timeout(500)
        else:
            raise RuntimeError("垃圾箱记录未加载，无法核实永久删除结果；请查询原作品，不要重复删除")
        ids = set()
        for link in await records.evaluate_all("es => es.map(e => e.href)"):
            try:
                ids.add(facebook_post_id(link))
            except ValueError:
                continue
        if post_id not in ids:
            return
        await page.wait_for_timeout(3000)
    raise TimeoutError("永久删除已提交，但垃圾箱仍有原 ID；结果待核实，禁止自动重试删除")


async def facebook_post_action(account_file: Path, *, post_url: str, owner_id: str,
                               expected_text: str, delete: bool = False,
                               permanent: bool = False, from_trash: bool = False, deleted: bool = False,
                               proxy: str | None = None, headless: bool = False) -> dict:
    """CLI 的原作品查询/删除入口；只有明确的平台反馈才返回成功。"""
    facebook_post_id(post_url)
    async with async_playwright() as playwright:
        browser, context, page = await _open_facebook_page(playwright, account_file, proxy=proxy, headless=headless)
        try:
            cookies = await context.cookies("https://www.facebook.com/")
            if {c["value"] for c in cookies if c["name"] == "c_user"} != {owner_id}:
                raise RuntimeError("当前 Facebook 登录用户与 owner-id 不一致")
            if not owner_id.isdigit() or not expected_text.strip():
                raise ValueError("owner-id 必须是数字，expected-text 不能为空")
            if deleted:
                if delete:
                    raise ValueError("核实永久删除结果不能同时执行删除")
                await verify_facebook_deletion(page, owner_id=owner_id, post_url=post_url)
            elif from_trash:
                article = await find_trashed_facebook_post(page, post_url=post_url, owner_id=owner_id, expected_text=expected_text)
            else:
                article = await find_facebook_post(page, post_url=post_url, owner_id=owner_id, expected_text=expected_text)
            result = {"platform": "facebook", "owner_id": owner_id,
                      "post_id": facebook_post_id(post_url), "post_url": post_url,
                      "expected_text": expected_text, "status": "absent_from_trash" if deleted else "trashed" if from_trash else "found"}
            if delete:
                if not from_trash:
                    result["status"] = await trash_facebook_post(page, article, post_url=post_url, owner_id=owner_id, expected_text=expected_text)
                if permanent:
                    row = await find_trashed_facebook_post(page, post_url=post_url, owner_id=owner_id, expected_text=expected_text)
                    # 垃圾箱单条记录的菜单与批量删除相隔离，禁止操作“全部”复选框。
                    await row.get_by_role("button", name=re.compile(r"^针对.+的更多选项$")).click()
                    await page.get_by_role("menu").get_by_role("menuitem", name="删除", exact=True).click()
                    dialog = page.get_by_role("dialog").filter(has_text="确定删除？")
                    await expect(dialog).to_contain_text("你删除的内容将无法恢复。")
                    await dialog.get_by_role("button", name="删除", exact=True).click()
                    await expect(dialog).to_have_count(0, timeout=30000)
                    await expect(row).to_have_count(0, timeout=30000)
                    await verify_facebook_deletion(page, owner_id=owner_id, post_url=post_url)
                    result["status"] = "deleted"
            result["checked_at"] = datetime.now(timezone.utc).isoformat()
            await context.storage_state(path=str(account_file))
            return result
        finally:
            await browser.close()
