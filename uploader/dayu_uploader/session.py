"""大鱼号登录状态和发布主体核验，不把网络超时当作登录失效。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from patchright.async_api import Page, async_playwright, expect

from conf import LOCAL_CHROME_PATH

DAYU_HOME_URL = "https://mp.dayu.com/dashboard/index"
DAYU_VIDEO_URL = "https://mp.dayu.com/dashboard/video/write"


async def read_dayu_identity(page: Page) -> dict:
    """从后台页头及服务端注入的 wmid 读取当前主体，拒绝缺失或歧义。"""
    # 页头账号区表达当前发布主体，限定 header-info 排除正文作者和作品列表里的同名文字。
    name = page.locator(".header-info .name")
    await expect(name).to_have_count(1)
    await expect(name).to_be_visible()
    scripts = "\n".join(await page.locator("script:not([src])").all_text_contents())
    ids = set(re.findall(r'''["']?wmid["']?\s*:\s*["']([a-f0-9]{32})["']''', scripts))
    if len(ids) != 1:
        raise RuntimeError("无法唯一识别大鱼号主体 wmid；请检查登录状态或页面结构")
    account_name = (await name.inner_text()).strip()
    if not account_name:
        raise RuntimeError("大鱼号页头账号名称为空")
    return {"wmid": ids.pop(), "name": account_name}


def load_dayu_identity(account_file: str | Path) -> dict:
    """读取登录时保存的主体绑定，不能用本地账号别名代替平台身份。"""
    identity_file = Path(account_file).with_suffix(".identity.json")
    identity = json.loads(identity_file.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-f0-9]{32}", identity.get("wmid", "")) or not identity.get("name"):
        raise ValueError(f"大鱼号主体绑定不完整，请重新登录: {identity_file}")
    return identity


async def login_dayu_account(account_file: str | Path, expected_name: str | None = None,
                             timeout: int = 600) -> dict:
    """用户在可见 Chrome 中登录，核验主体后保存状态；验证码由用户完成。"""
    account_file = Path(account_file).resolve()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=False,
        )
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://mp.dayu.com/", wait_until="domcontentloaded", timeout=45000)
            print("请在 Chrome 中完成大鱼号登录；账号密码及验证码直接在网页中输入。", flush=True)
            await page.wait_for_url("https://mp.dayu.com/dashboard/**", timeout=timeout * 1000)
            identity = await read_dayu_identity(page)
            if expected_name is not None and identity["name"] != expected_name:
                raise RuntimeError(f"登录主体不匹配，期望 {expected_name}，实际 {identity['name']}")
            identity_file = account_file.with_suffix(".identity.json")
            if identity_file.exists() and load_dayu_identity(account_file)["wmid"] != identity["wmid"]:
                raise RuntimeError("当前大鱼号与已绑定主体不同，拒绝覆盖原账号；请使用新的 --account")
            account_file.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(account_file))
            identity_file.write_text(json.dumps(identity, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": True, "account_file": str(account_file), "identity": identity}
        finally:
            await browser.close()


async def check_dayu_account(account_file: str | Path) -> bool:
    """恢复登录状态并比较 wmid；仅明确回到登录 iframe 时返回失效。"""
    account_file = Path(account_file)
    if not account_file.is_file():
        return False
    expected = load_dayu_identity(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=True,
        )
        try:
            context = await browser.new_context(storage_state=str(account_file))
            page = await context.new_page()
            await page.goto(DAYU_HOME_URL, wait_until="domcontentloaded", timeout=45000)
            # 登录 iframe 的 CAS 域名和路径标识认证页；不能用普通 iframe 的存在推断登录失效。
            if await page.locator('iframe[src*="uop.dayu.com/cas/"]').count():
                return False
            actual = await read_dayu_identity(page)
            if actual["wmid"] != expected["wmid"]:
                raise RuntimeError("大鱼号主体与账号文件绑定不一致")
            return True
        finally:
            await browser.close()
