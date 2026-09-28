import asyncio

from patchright.async_api import async_playwright

from uploader.ks_uploader.main import _click_visible_publish_confirm


def test_click_visible_publish_confirm_uses_modal_primary_button():
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, channel="chrome")
            page = await browser.new_page()
            await page.set_content(
                """
                <div class="ant-modal-confirm-centered">
                  <button type="button">取消</button>
                  <button type="button" class="ant-btn-primary">确认发布</button>
                </div>
                """
            )
            await page.locator("button.ant-btn-primary").evaluate(
                "button => button.addEventListener('click', () => window.publishConfirmed = true)"
            )

            assert await _click_visible_publish_confirm(page) is True
            assert await page.evaluate("window.publishConfirmed") is True
            await browser.close()

    asyncio.run(scenario())


def test_click_visible_publish_confirm_is_noop_without_modal():
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, channel="chrome")
            page = await browser.new_page()
            await page.set_content("<button>发布</button>")

            assert await _click_visible_publish_confirm(page) is False
            await browser.close()

    asyncio.run(scenario())
