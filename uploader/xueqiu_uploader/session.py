"""雪球登录及账号绑定；网络故障与明确退出登录分别处理。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from patchright.async_api import Page, async_playwright, expect

from conf import LOCAL_CHROME_PATH
from uploader.xueqiu_uploader.constants import XUEQIU_HOME_URL


async def read_xueqiu_identity(page: Page) -> dict:
    """页头 data-id 是当前用户 ID；昵称用于展示，不代替身份比较。"""
    # header-user 是已登录页头固定账号区，data-id 在首页及长文编辑器均可读取。
    user = page.locator("nav .header-user[data-id]")
    await expect(user).to_have_count(1, timeout=30000)
    await expect(user).to_be_visible()
    uid = await user.get_attribute("data-id")
    # 用户区内 span 承载昵称，排除侧栏和正文中可能出现的相同名字。
    name = (await user.locator("span").inner_text()).strip()
    if not re.fullmatch(r"[1-9][0-9]*", uid or "") or not name:
        raise RuntimeError("雪球页头身份缺失，无法核验发布账号")
    return {"uid": uid, "name": name}


def load_xueqiu_identity(account_file: str | Path) -> dict:
    """恢复登录时绑定的真实用户 ID，拒绝使用未绑定账号。"""
    path = Path(account_file).with_suffix(".identity.json")
    identity = json.loads(path.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[1-9][0-9]*", identity.get("uid", "")) or not identity.get("name"):
        raise ValueError(f"雪球账号绑定不完整，请重新登录: {path}")
    return identity


async def login_xueqiu_account(account_file: str | Path, expected_name=None, timeout=600) -> dict:
    """在独立可见 Chrome 登录；账号密码、协议与验证码均由用户在网页完成。"""
    if timeout <= 0:
        raise ValueError("登录期限必须大于 0 秒")
    account_file = Path(account_file).resolve()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=False,
        )
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(XUEQIU_HOME_URL, wait_until="domcontentloaded", timeout=45000)
            print("请在 Chrome 中完成雪球登录，然后进入创作者中心；登录态将保存到本地账号文件。", flush=True)
            # 只等待已观察的创作者页头，登录表单消失或 Cookie 出现均不足以证明登录完成。
            await page.locator("nav .header-user[data-id]").wait_for(state="visible", timeout=timeout * 1000)
            identity = await read_xueqiu_identity(page)
            if expected_name is not None and identity["name"] != expected_name:
                raise RuntimeError("雪球昵称与 --expected-name 不匹配")
            binding = account_file.with_suffix(".identity.json")
            if binding.exists() and load_xueqiu_identity(account_file)["uid"] != identity["uid"]:
                raise RuntimeError("当前雪球账号与已绑定账号不同，请使用新的 --account")
            account_file.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(account_file))
            binding.write_text(json.dumps(identity, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": True, "account_file": str(account_file), "identity": identity}
        finally:
            await browser.close()


async def check_xueqiu_account(account_file: str | Path, headless=False) -> bool:
    """仅明确进入登录页时返回失效；403、网络超时和身份歧义直接报错。"""
    account_file = Path(account_file)
    if not account_file.is_file():
        return False
    expected = load_xueqiu_identity(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=headless,
        )
        try:
            context = await browser.new_context(storage_state=str(account_file))
            page = await context.new_page()
            response = await page.goto(XUEQIU_HOME_URL, wait_until="domcontentloaded", timeout=45000)
            if response is not None and response.status >= 400:
                raise RuntimeError(f"雪球访问失败，HTTP {response.status}，不能据此判断登录失效")
            target = urlsplit(page.url)
            if target.hostname in {"xueqiu.com", "www.xueqiu.com"} and target.path == "/account/login":
                return False
            actual = await read_xueqiu_identity(page)
            if actual["uid"] != expected["uid"]:
                raise RuntimeError("雪球会话主体与本地绑定不一致")
            return True
        finally:
            await browser.close()
