import asyncio
from pathlib import Path

from patchright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
COOKIE = ROOT / "cookies" / "tencent_dagaju.json"
TITLE = "AI算力真正的新瓶颈，为什么开始从芯片转向“电”？"


async def dump_visible_text(page, label: str, limit: int = 18000) -> None:
    bodies = page.locator("body")
    print(label, "BODY_COUNT", await bodies.count())
    for index in range(await bodies.count()):
        body = bodies.nth(index)
        try:
            visible = await body.is_visible()
            text = (await body.inner_text()).strip()
            print(label, "BODY", index, "VISIBLE", visible, text[:limit])
        except Exception as exc:
            print(label, "BODY_ERROR", index, type(exc).__name__, str(exc)[:300])


async def first_visible(locator):
    for index in range(await locator.count()):
        item = locator.nth(index)
        try:
            if await item.is_visible():
                return item
        except Exception:
            continue
    return None


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(storage_state=str(COOKIE))
        page = await context.new_page()
        await page.goto(
            "https://channels.weixin.qq.com/platform",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        page.set_default_timeout(3000)
        await page.wait_for_timeout(7000)

        print("HOME_URL", page.url)
        print("HOME_TITLE", await page.title())
        print("CONTENT_MENU_COUNT", await page.get_by_text("内容管理", exact=True).count())
        await page.screenshot(path="/tmp/tencent-home-inspect.png", full_page=True)

        content = await first_visible(page.get_by_text("内容管理", exact=True))
        if content is not None:
            await content.click()
            await page.wait_for_timeout(3000)
            print("AFTER_CONTENT_URL", page.url)
            print("VIDEO_MENU_COUNT", await page.get_by_text("视频", exact=True).count())
            await dump_visible_text(page, "AFTER_CONTENT", 12000)
            await page.screenshot(path="/tmp/tencent-content-inspect.png", full_page=True)

        video = await first_visible(page.get_by_text("视频", exact=True))
        if video is not None:
            await video.click()
            await page.wait_for_timeout(12000)
            print("AFTER_VIDEO_URL", page.url)
            await dump_visible_text(page, "AFTER_VIDEO", 18000)
            await page.screenshot(path="/tmp/tencent-video-list-inspect.png", full_page=True)

        title_matches = page.get_by_text(TITLE, exact=False)
        print("PAGE_TITLE_MATCHES", await title_matches.count())
        for match_index in range(min(await title_matches.count(), 5)):
            match = title_matches.nth(match_index)
            try:
                if not await match.is_visible():
                    continue
                html = await match.evaluate(
                    "el => { const rows=[]; let n=el; for(let i=0;i<8 && n;i++,n=n.parentElement){rows.push(n.outerHTML.slice(0,7000));} return rows.join(' ---PARENT--- '); }"
                )
                print("PAGE_MATCH", match_index, html[:40000])
            except Exception as exc:
                print("PAGE_MATCH_ERROR", match_index, type(exc).__name__, str(exc)[:300])
        print("EDIT_BUTTON_COUNT", await page.get_by_text("修改描述和封面", exact=True).count())

        print("PAGE", page.url)
        print("FRAMES", len(page.frames))
        for frame_index, frame in enumerate(page.frames):
            print("FRAME", frame_index, frame.url)
            try:
                body = frame.locator("body")
                if not await body.count():
                    continue
                text = (await body.first.inner_text()).strip()
                print("FRAME_TEXT", frame_index, text[:20000])
                if TITLE in text or "AI算力真正的新瓶颈" in text:
                    print("FOUND_TITLE_IN_FRAME", frame_index)
                    print(text[:10000])
                    matches = frame.get_by_text(TITLE, exact=True)
                    if not await matches.count():
                        matches = frame.get_by_text("AI算力真正的新瓶颈", exact=False)
                    for match_index in range(min(await matches.count(), 5)):
                        match = matches.nth(match_index)
                        try:
                            html = await match.evaluate(
                                "el => { const rows=[]; let n=el; for(let i=0;i<7 && n;i++,n=n.parentElement){rows.push(n.outerHTML.slice(0,5000));} return rows.join(' ---PARENT--- '); }"
                            )
                            print("MATCH", match_index, html[:20000])
                        except Exception as exc:
                            print("MATCH_ERROR", match_index, type(exc).__name__, str(exc)[:300])
            except Exception as exc:
                print("FRAME_ERROR", frame_index, type(exc).__name__, str(exc)[:300])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
