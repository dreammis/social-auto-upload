"""常驻浏览器会话管理。

用账号 cookie（storage_state）启动一个非 headless 浏览器窗口，打开淘宝光合
创作者中心，供用户直接操作。每个账号独立 browser 实例 + 独立 context，
天然隔离：不同账号可同时打开、互不干扰；同一账号不重复打开，关窗后可重开。
"""

import asyncio
import threading
from pathlib import Path

from playwright.async_api import async_playwright

from conf import BASE_DIR
from myUtils.login import get_browser_options
from utils.log import taobao_guanghe_logger

TAOBAO_GUANGHE_URL = "https://creator.guanghe.taobao.com/"

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
        if file_path in _active_browsers:
            return False, "该账号已打开"
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

        closed_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        browser.on(
            "disconnected",
            lambda _b: loop.call_soon_threadsafe(closed_event.set),
        )

        context = await browser.new_context(storage_state=str(cookie_file))
        page = await context.new_page()
        try:
            await page.goto(TAOBAO_GUANGHE_URL, timeout=60000,
                            wait_until="domcontentloaded")
        except Exception as e:
            taobao_guanghe_logger.warning(f"⚠️ 打开光合平台页面失败 [{file_path}]: {e}")

        # 保持存活，直到用户关闭浏览器窗口
        await closed_event.wait()
