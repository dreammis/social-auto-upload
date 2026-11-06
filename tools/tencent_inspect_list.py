import asyncio
from pathlib import Path

from patchright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
COOKIE = ROOT / "cookies" / "tencent_dagaju.json"


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(storage_state=str(COOKIE))
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com/platform", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        content = page.get_by_text("内容管理", exact=True).first
        if await content.count():
            await content.click()
            await page.wait_for_timeout(3000)
        video = page.get_by_text("视频", exact=True).first
        if await video.count():
            await video.click()
            await page.wait_for_timeout(5000)
        print("URL", page.url)
        print("FRAMES", len(page.frames))
        for index, frame in enumerate(page.frames):
            print("FRAME", index, frame.url)
            try:
                bodies = frame.locator("body")
                for body_index in range(await bodies.count()):
                    text = (await bodies.nth(body_index).inner_text()).strip()
                    if text:
                        print("BODY", index, body_index, text[:6000].replace("\x00", ""))
            except Exception as exc:
                print("FRAME_ERROR", index, type(exc).__name__, str(exc)[:200])
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
