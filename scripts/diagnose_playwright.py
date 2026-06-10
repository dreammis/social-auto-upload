#!/usr/bin/env python3
"""诊断 Playwright 网络问题"""

import asyncio
from pathlib import Path
from patchright.async_api import async_playwright


async def test_access():
    """测试各种配置的网络访问"""

    url = "https://creator.guanghe.taobao.com/"
    cookie_file = Path("cookies/taobao_guanghe_uploader/test_account.json")

    print("=" * 60)
    print("Playwright 网络诊断")
    print("=" * 60)

    # Test 1: 基础访问（无 Cookie）
    print("\n[Test 1] 基础访问（无 Cookie）")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, channel="chrome")
            page = await browser.new_page()
            response = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            print(f"✅ 成功: {page.url[:80]}")
            await asyncio.sleep(3)
            await browser.close()
    except Exception as e:
        print(f"❌ 失败: {str(e)[:100]}")

    # Test 2: 使用系统 Chrome
    print("\n[Test 2] 使用系统 Chrome（无 Cookie）")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            )
            page = await browser.new_page()
            response = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            print(f"✅ 成功: {page.url[:80]}")
            await asyncio.sleep(3)
            await browser.close()
    except Exception as e:
        print(f"❌ 失败: {str(e)[:100]}")

    # Test 3: 加载 Cookie
    if cookie_file.exists():
        print("\n[Test 3] 使用系统 Chrome + Cookie")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                )
                context = await browser.new_context(storage_state=str(cookie_file))
                page = await context.new_page()
                response = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                print(f"✅ 成功: {page.url[:80]}")

                # 检查登录状态
                if "login" in page.url.lower():
                    print("⚠️  Cookie 已失效（跳转到登录页）")
                elif "creator.guanghe.taobao.com" in page.url:
                    print("✅ Cookie 有效（停留在创作者中心）")

                await asyncio.sleep(5)
                await browser.close()
        except Exception as e:
            print(f"❌ 失败: {str(e)[:100]}")
    else:
        print(f"\n[Test 3] 跳过（Cookie 文件不存在）")

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_access())
