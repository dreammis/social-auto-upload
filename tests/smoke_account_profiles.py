"""Offline real-Chromium profile isolation check; run explicitly as a module."""
import asyncio
import json
import tempfile
import sys
from pathlib import Path

from patchright.async_api import async_playwright
from utils.account_browser import account_browser


async def main():
    options = {'executable_path': sys.argv[1]} if len(sys.argv) > 1 else {}
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / 'a.json', Path(tmp) / 'b.json'
        a.write_text(json.dumps({'cookies': [], 'origins': [{'origin': 'https://example.test', 'localStorage': [{'name': 'owner', 'value': 'legacy-a'}]}]}))
        b.write_text(json.dumps({'cookies': [], 'origins': []}))
        async with async_playwright() as pw:
            async def read(context):
                page = await context.new_page()
                async def serve(route):
                    await route.fulfill(body='<!doctype html>', content_type='text/html')
                await page.route('**/*', serve)
                await page.goto('https://example.test')
                return page, await page.evaluate("localStorage.getItem('owner')")
            async with account_browser(pw, a, 'douyin', headless=True, **options) as context:
                page, value = await read(context)
                assert value == 'legacy-a', value
                await page.evaluate("localStorage.setItem('owner', 'saved-a')")
            async with account_browser(pw, b, 'douyin', headless=True, **options) as context:
                _, value = await read(context)
                assert value is None, value
            async with account_browser(pw, a, 'douyin', headless=True, **options) as context:
                _, value = await read(context)
                assert value == 'saved-a', value
        print('PASS: legacy import, independent accounts, persistence after restart')


if __name__ == '__main__':
    asyncio.run(main())
