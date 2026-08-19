# -*- coding: utf-8 -*-
"""百家号(headless)扫码登录 → 保存 cookie。

说明：
  - 无头浏览器打开百家号登录页并提取登录二维码，放大截图后保存为 png，
    并用终端 ASCII 二维码展示；你手机/百度APP扫码登录。
  - 扫码成功后自动把登录态写入 cookies/baijiahao_uploader/account.json。

用法：
    python examples/get_baijiahao_cookie_headless.py
"""
from pathlib import Path

from playwright.async_api import async_playwright
from conf import BASE_DIR
from utils.login_qrcode import (
    build_login_qrcode_path,
    print_terminal_qrcode,
)
from uploader.baijiahao_uploader.main import cookie_auth, baijiahao_logger


QR_SELECTOR = 'img[src^="https://passport.baidu.com/v2/api/qrcode"]'
LOGIN_BTN_TEXT = "登录"
LOGIN_URL = "https://baijiahao.baidu.com/builder/theme/bjh/login"


async def _grab_qr(page, qrcode_path: Path) -> str:
    qr = page.locator(QR_SELECTOR).first
    await qr.wait_for(state="attached", timeout=60000)
    src = await qr.get_attribute("src")
    if src and src.startswith("https://"):
        resp = await page.context.request.get(src)
        qrcode_path.parent.mkdir(parents=True, exist_ok=True)
        qrcode_path.write_bytes(await resp.body())
    else:
        await qr.screenshot(path=str(qrcode_path))

    qrcode_content = ""
    try:
        import cv2
        img = cv2.imread(str(qrcode_path))
        if img is not None:
            h, w = img.shape[:2]
            up = cv2.resize(img, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
            qrcode_content = cv2.QRCodeDetector().detectAndDecode(up)[0] or ""
    except Exception:
        pass
    return qrcode_content or ""


async def _wait_login(page, max_checks: int = 120, interval: int = 3) -> bool:
    import asyncio
    async def _logged_in():
        if "login" in page.url:
            return False
        ctx = page.context
        cookies = await ctx.cookies()
        if any(c.get("name") in ("BDUSS", "STOKEN") for c in cookies):
            return True
        return False

    for _ in range(max_checks):
        if await _logged_in():
            return True
        await asyncio.sleep(interval)
    return False


async def main():
    account_file = Path(BASE_DIR / "cookies" / "baijiahao_uploader" / "account.json")
    account_file.parent.mkdir(parents=True, exist_ok=True)

    import os
    if os.path.exists(account_file) and await cookie_auth(str(account_file)):
        baijiahao_logger.success("[+] cookie 已有效，无需重新登录")
        return

    qrcode_path = build_login_qrcode_path(str(account_file))
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        # 进入登录弹窗
        await page.get_by_text(LOGIN_BTN_TEXT, exact=True).first.click(timeout=10000)
        await page.wait_for_timeout(4000)

        qrcode_content = await _grab_qr(page, qrcode_path)
        baijiahao_logger.info(f"🖼️ 二维码已保存: {qrcode_path}")
        if qrcode_content:
            print_terminal_qrcode(qrcode_content, qrcode_path, "百度APP/手机百度")
        else:
            print(f"未能解码二维码，请直接打开文件扫码:\n  {qrcode_path}")

        if await _wait_login(page):
            baijiahao_logger.success("[+] 扫码登录成功，正在保存 cookie...")
            await context.storage_state(path=str(account_file))
            baijiahao_logger.success(f"[+] cookie 已保存: {account_file}")
        else:
            baijiahao_logger.error("[-] 等待扫码超时（约 6 分钟），未完成登录。")
        await browser.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())