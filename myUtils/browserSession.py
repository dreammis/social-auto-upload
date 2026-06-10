"""常驻浏览器会话管理。

用账号 cookie（storage_state）启动一个非 headless 浏览器窗口，打开淘宝光合
创作者中心，供用户直接操作。每个账号独立 browser 实例 + 独立 context，
天然隔离：不同账号可同时打开、互不干扰；同一账号不重复打开，关窗后可重开。
"""

import asyncio
import sqlite3
import threading
from pathlib import Path

from playwright.async_api import async_playwright

from conf import BASE_DIR
from myUtils.login import get_browser_options, _grab_platform_username, _safe_close
from utils.base_social_media import set_init_script
from utils.log import taobao_guanghe_logger

TAOBAO_GUANGHE_URL = "https://creator.guanghe.taobao.com/"

# 各平台创作者中心 URL（与 myUtils/auth.cookie_auth_* 一致，用 cookie 打开后可抓昵称）
_CREATOR_URLS = {
    1: "https://creator.xiaohongshu.com/creator-micro/content/upload",
    2: "https://channels.weixin.qq.com/platform/post/create",
    3: "https://creator.douyin.com/creator-micro/content/upload",
    4: "https://cp.kuaishou.com/article/publish/video",
    5: TAOBAO_GUANGHE_URL,
}

# key = cookie 文件名（filePath），value = {"thread": Thread}
# 以 filePath 去重，保证同一账号同时只有一个窗口。
_active_browsers = {}
_lock = threading.Lock()


def open_taobao_browser(file_path: str):
    """用指定账号 cookie 打开淘宝光合平台浏览器窗口。

    Returns:
        (ok: bool, msg: str)
    """
    # 防路径穿越：只接受纯文件名
    if not file_path or Path(file_path).name != file_path:
        return False, "非法的 filePath"

    cookie_file = Path(BASE_DIR / "cookiesFile" / file_path)
    if not cookie_file.exists():
        return False, "cookie文件不存在"

    with _lock:
        existing = _active_browsers.get(file_path)
        if existing is not None:
            # 仅当登记的线程仍存活才算「已打开」。线程已死说明窗口早已关闭
            # （或后端重启过），属于残留登记，清掉后放行重新打开。
            thread = existing.get("thread")
            if thread is not None and thread.is_alive():
                return False, "该账号已打开"
            _active_browsers.pop(file_path, None)

        thread = threading.Thread(
            target=_browser_thread, args=(file_path,), daemon=True
        )
        _active_browsers[file_path] = {"thread": thread}
        thread.start()

    taobao_guanghe_logger.info(f"🚀 打开光合平台窗口: {file_path}")
    return True, "已打开"


def _browser_thread(file_path: str):
    """后台线程入口：独立事件循环跑浏览器，直到窗口关闭。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_browser(file_path))
    except Exception as e:
        taobao_guanghe_logger.error(f"❌ 光合平台窗口异常 [{file_path}]: {e}")
    finally:
        loop.close()
        with _lock:
            _active_browsers.pop(file_path, None)
        taobao_guanghe_logger.info(f"🧹 光合平台窗口已清理: {file_path}")


async def _run_browser(file_path: str):
    """启动浏览器并保持打开，直到用户手动关窗（browser disconnected）。"""
    cookie_file = Path(BASE_DIR / "cookiesFile" / file_path)

    # 复用登录流程的浏览器配置（系统 Chrome / channel / 防自动化检测），
    # 但强制非 headless，让用户能看到并操作窗口。
    options = get_browser_options()
    options["headless"] = False

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**options)

        context = await browser.new_context(storage_state=str(cookie_file))
        page = await context.new_page()
        try:
            await page.goto(TAOBAO_GUANGHE_URL, timeout=60000,
                            wait_until="domcontentloaded")
        except Exception as e:
            taobao_guanghe_logger.warning(f"⚠️ 打开光合平台页面失败 [{file_path}]: {e}")

        # 轮询浏览器连接状态保持存活，直到用户关闭窗口（进程退出）。
        # 不依赖 browser.on("disconnected") 事件——用系统 Chrome 启动时该事件
        # 常常不触发，会导致线程永久卡住、_active_browsers 永不清理，
        # 后续再点「进入」就会误报「该账号已打开」。
        while browser.is_connected():
            await asyncio.sleep(1)


def _get_account(account_id):
    """按 id 查账号，返回 (type, filePath) 或 None。"""
    db_path = Path(BASE_DIR / "db" / "database.db")
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT type, filePath FROM user_info WHERE id = ?", (account_id,)
        ).fetchone()
    return row


async def _fetch_username(account_id):
    """用已存 cookie 在 headless 浏览器打开创作者中心抓昵称并回写 DB。

    Returns (ok: bool, name: str|None)。全程容错，不抛异常。
    """
    row = _get_account(account_id)
    if not row:
        return False, None
    account_type, file_path = row
    cookie_file = Path(BASE_DIR / "cookiesFile" / file_path)
    if not cookie_file.exists():
        return False, None
    url = _CREATOR_URLS.get(account_type)
    if not url:
        return False, None

    options = get_browser_options()
    options["headless"] = True

    page = context = browser = None
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**options)
            context = await browser.new_context(storage_state=str(cookie_file))
            context = await set_init_script(context)
            page = await context.new_page()
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                # 给前端框架渲染昵称留点时间
                await asyncio.sleep(2)
            except Exception as e:
                taobao_guanghe_logger.warning(f"⚠️ 获取用户名打开页面失败 [{account_id}]: {e}")
            name = await _grab_platform_username(page, account_type)
            await _safe_close(page, context, browser)
    except Exception as e:
        taobao_guanghe_logger.error(f"❌ 获取用户名异常 [{account_id}]: {e}")
        return False, None

    if name:
        db_path = Path(BASE_DIR / "db" / "database.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE user_info SET platformUserName = ? WHERE id = ?",
                (name, account_id),
            )
            conn.commit()
        return True, name
    return False, None


def fetch_username_sync(account_id):
    """同步包装：在独立事件循环里跑 _fetch_username，供 Flask 路由调用。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_fetch_username(account_id))
    finally:
        loop.close()
