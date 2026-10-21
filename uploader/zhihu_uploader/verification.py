"""知乎作品提交后的只读核验。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from patchright.async_api import async_playwright, expect

from conf import LOCAL_CHROME_PATH
from uploader.zhihu_uploader.session import load_zhihu_identity, read_zhihu_identity


async def verify_zhihu_result(account_file, result_file, headless=False) -> dict:
    """只读打开结果文件保存的作品 URL；缺 URL 时要求先查询创作中心原作品。"""
    account_file = Path(account_file).resolve()
    result_file = Path(result_file).resolve()
    result = json.loads(result_file.read_text(encoding="utf-8"))
    expected = load_zhihu_identity(account_file)
    if result.get("identity") != expected:
        raise ValueError("结果文件与当前知乎账号绑定不一致")
    url = result.get("url")
    if not url:
        raise ValueError(
            "结果文件没有知乎作品 URL；请在创作中心的内容管理中按标题和提交时间核对原作品，勿重新上传"
        )
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"www.zhihu.com", "zhuanlan.zhihu.com"}:
        raise ValueError("结果文件中的知乎作品 URL 不受支持")
    if not re.search(r"/(?:p|pin|zvideo|video)/\d+/?$", parsed.path):
        raise ValueError("结果文件 URL 未包含知乎文章或视频作品 ID")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=headless,
        )
        try:
            context = await browser.new_context(storage_state=str(account_file), timezone_id="Asia/Shanghai")
            page = await context.new_page()
            response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            if response is not None and response.status >= 400:
                raise RuntimeError(f"知乎原作品 URL 访问失败，HTTP {response.status}")
            if await read_zhihu_identity(page) != expected:
                raise RuntimeError("知乎核验页头与本地账号绑定不一致")
            title = result.get("title")
            if not title:
                raise ValueError("结果文件缺少标题，无法核对原作品")
            # 新版视频详情把标题与简介放在同一正文区，标题后还带分隔符。
            await expect(page.locator("main")).to_contain_text(title, timeout=30000)
            result.update(success=True, status="published", verified=True)
            result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return result
        finally:
            await browser.close()
