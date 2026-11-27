import asyncio

from patchright.async_api import async_playwright

from uploader.baijiahao_uploader.main import BaiJiaHaoVideo


def test_headed_upload_waits_for_baidu_security_verification_to_finish():
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, channel="chrome")
            page = await browser.new_page()
            await page.set_content('<div id="verification">百度安全验证</div>')
            uploader = BaiJiaHaoVideo("title", "video.mp4", [], "cookie.json", headless=False)

            async def finish_verification():
                await page.wait_for_timeout(100)
                await page.locator("#verification").evaluate("element => element.remove()")

            task = asyncio.create_task(finish_verification())
            waited = await uploader._wait_for_security_verification(
                page,
                timeout_seconds=2,
                poll_interval_seconds=0.05,
            )
            await task
            assert waited is True
            await browser.close()

    asyncio.run(scenario())


def test_hidden_baidu_security_verification_does_not_enter_wait_mode():
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, channel="chrome")
            page = await browser.new_page()
            await page.set_content('<div style="display:none">百度安全验证</div>')
            uploader = BaiJiaHaoVideo("title", "video.mp4", [], "cookie.json", headless=False)

            waited = await uploader._wait_for_security_verification(page)

            assert waited is False
            await browser.close()

    asyncio.run(scenario())
