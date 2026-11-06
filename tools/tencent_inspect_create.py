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
        await page.goto("https://channels.weixin.qq.com/platform/post/create", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        print("URL", page.url)
        for index, frame in enumerate(page.frames):
            try:
                bodies = frame.locator("body")
                body_count = await bodies.count()
                for body_index in range(body_count):
                    text = (await bodies.nth(body_index).inner_text()).strip()
                    lines = [
                        line.strip()
                        for line in text.splitlines()
                        if "原创" in line or "声明" in line or "标注" in line
                    ]
                    if lines:
                        print("FRAME", index, "BODY", body_index, lines[:80])
            except Exception as exc:
                print("FRAME_SKIP", index, type(exc).__name__, str(exc)[:160])
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
