"""微信公众号登录会话、账号绑定与动态 token 读取。

微信公众号后台的 token 属于会话级参数，每次登录都不同；发布前必须从当前会话
的后台首页 URL 重新读取，不能复用登录时保存的旧值。账号绑定只校验昵称，
避免把会变化的 token 当作账号身份。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from patchright.async_api import Page, async_playwright, expect

from conf import LOCAL_CHROME_PATH
try:
    from conf import BROWSER_LAUNCH_ARGS
except ImportError:  # 兼容尚未配置该可选项的旧 conf.py
    BROWSER_LAUNCH_ARGS = []
from uploader.wechat_uploader.constants import (
    WECHAT_HOME_PATH, WECHAT_HOME_URL, WECHAT_LOGIN_HINTS,
)


def browser_launch_kwargs(headless: bool) -> dict:
    """统一的浏览器启动参数；可选项来自 conf，默认不改变平台行为。"""
    kwargs = {
        "executable_path": LOCAL_CHROME_PATH or None,
        "channel": "chrome",
        "headless": headless,
    }
    if BROWSER_LAUNCH_ARGS:
        kwargs["args"] = list(BROWSER_LAUNCH_ARGS)
    return kwargs


# 后台首页右上角账号昵称；多个候选避免小程序/多账号后台的容器差异。
NICKNAME_SELECTORS = (
    ".weui-desktop-account__nickname",
    ".account_nickname",
    "#account_nickname",
    ".weui-desktop-dropdown__button .weui-desktop-account__nickname",
)


def wechat_is_login_url(url: str) -> bool:
    """后台首页之外的登录/扫码路径均视为未登录。"""
    target = urlsplit(url)
    path = target.path.lower()
    return any(hint in path for hint in WECHAT_LOGIN_HINTS) or path in {"/", ""}


def wechat_token_from_url(url: str) -> str | None:
    """从当前后台 URL 读取会话 token；缺失或格式异常返回 None。"""
    token = parse_qs(urlsplit(url).query).get("token", [""])[0]
    return token if re.fullmatch(r"\d{5,15}", token or "") else None


async def read_wechat_identity(page: Page) -> dict:
    """读取后台当前账号昵称，作为本地会话绑定信息。"""
    for selector in NICKNAME_SELECTORS:
        locator = page.locator(selector)
        if await locator.count() < 1:
            continue
        try:
            name = (await locator.first.inner_text(timeout=3000)).strip()
        except Exception:
            continue
        if name:
            return {"nickname": name}
    # 部分后台把昵称放在 title 里，例如「公众号后台 - 昵称」。
    title = (await page.title()).strip()
    match = re.search(r"后台\s*[-－—]\s*(.+)$", title)
    if match and match.group(1).strip():
        return {"nickname": match.group(1).strip()}
    raise RuntimeError("微信公众号后台没有可读取的账号昵称，无法绑定当前会话")


def load_wechat_identity(account_file: str | Path) -> dict:
    """读取登录时绑定的账号昵称。"""
    path = Path(account_file).with_suffix(".identity.json")
    identity = json.loads(path.read_text(encoding="utf-8"))
    if not identity.get("nickname"):
        raise ValueError(f"微信公众号账号绑定不完整，请重新登录: {path}")
    return identity


async def login_wechat_account(account_file: str | Path, timeout: int = 600) -> dict:
    """在可见 Chrome 扫码登录，核对账号昵称后保存本地 storage state。"""
    if timeout <= 0:
        raise ValueError("登录期限必须大于 0 秒")
    account_file = Path(account_file).resolve()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**browser_launch_kwargs(False))
        try:
            context = await browser.new_context(timezone_id="Asia/Shanghai")
            page = await context.new_page()
            await page.goto(WECHAT_HOME_URL, wait_until="domcontentloaded", timeout=45000)
            print("请在打开的 Chrome 中用管理员微信扫码登录公众号后台；账号密码与二维码都在网页上。", flush=True)
            # 登录完成后后台会带 token 跳到 /cgi-bin/home；只等昵称元素不足以证明会话可用。
            await expect(page).to_have_url(
                re.compile(rf"https://mp\.weixin\.qq\.com{re.escape(WECHAT_HOME_PATH)}.*token=\d+"),
                timeout=timeout * 1000,
            )
            token = wechat_token_from_url(page.url)
            if token is None:
                raise RuntimeError("微信公众号后台 URL 缺少有效 token，请重新登录")
            identity = await read_wechat_identity(page)
            binding = account_file.with_suffix(".identity.json")
            if binding.exists() and load_wechat_identity(account_file)["nickname"] != identity["nickname"]:
                raise RuntimeError("当前公众号账号与已绑定账号不同，请使用新的 --account")
            account_file.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(account_file))
            binding.write_text(json.dumps(identity, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": True, "account_file": str(account_file),
                    "identity": identity, "token_obtained": True}
        finally:
            await browser.close()


async def check_wechat_account(account_file: str | Path, headless: bool = True) -> bool:
    """仅明确回到登录页时返回失效；网络错误或昵称不一致直接报告。"""
    account_file = Path(account_file)
    if not account_file.is_file():
        return False
    expected = load_wechat_identity(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**browser_launch_kwargs(headless))
        try:
            context = await browser.new_context(storage_state=str(account_file), timezone_id="Asia/Shanghai")
            page = await context.new_page()
            response = await page.goto(WECHAT_HOME_URL, wait_until="domcontentloaded", timeout=45000)
            if response is not None and response.status >= 400:
                raise RuntimeError(f"微信公众号后台访问失败，HTTP {response.status}")
            await page.wait_for_load_state("domcontentloaded")
            if wechat_is_login_url(page.url) or wechat_token_from_url(page.url) is None:
                return False
            actual = await read_wechat_identity(page)
            if actual["nickname"] != expected["nickname"]:
                raise RuntimeError("微信公众号当前账号与本地绑定不一致")
            return True
        finally:
            await browser.close()


async def read_wechat_token(page: Page) -> str:
    """打开后台首页并返回当前会话 token；失效则明确报错。"""
    response = await page.goto(WECHAT_HOME_URL, wait_until="domcontentloaded", timeout=45000)
    if response is not None and response.status >= 400:
        raise RuntimeError(f"微信公众号后台访问失败，HTTP {response.status}")
    if wechat_is_login_url(page.url):
        raise RuntimeError("微信公众号登录态已失效，请重新执行 sau wechat login")
    token = wechat_token_from_url(page.url)
    if token is None:
        raise RuntimeError("微信公众号后台 URL 缺少有效 token，请重新登录")
    return token
