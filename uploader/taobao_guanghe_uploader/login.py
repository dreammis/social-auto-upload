"""淘宝光合登录功能实现"""

import asyncio
from pathlib import Path

from patchright.async_api import async_playwright, Playwright, Page
from utils.base_social_media import set_init_script
from utils.login_qrcode import (
    build_login_qrcode_path,
    decode_qrcode_from_path,
)
from utils.log import taobao_guanghe_logger
from uploader.taobao_guanghe_uploader.selector import (
    GUANGHE_HOME_URL,
    CREATOR_CENTER_URL,
    QRCODE_CANVAS,
    QRCODE_CONTAINER,
    PASSPORT_URL_KEY,
    CAPTCHA_REQUIRED_SIGNAL,
    CAPTCHA_WAIT_TIMEOUT,
)


def _build_login_result(
    success: bool,
    status: str,
    message: str,
    account_file: str | Path,
    qrcode: dict | None = None,
    current_url: str = "",
) -> dict:
    """构建登录结果"""
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def _cookie_auth_impl(
    account_file: str | Path,
    use_system_chrome: bool = True,
    enable_stealth: bool = False,
) -> tuple[bool, str]:
    """cookie_auth 的内部实现，返回 (是否有效, 当前 URL)。

    URL 一并返回，调用方据此区分：
    - creator.guanghe.taobao.com → 有效
    - login.taobao.com / passport.taobao.com → 失效但可尝试让用户在自己浏览器里完成验证
    - 其它 → 失效
    """
    async with async_playwright() as playwright:
        # 查找系统 Chrome
        chrome_path = None
        if use_system_chrome:
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"),
            ]
            for path in possible_paths:
                if Path(path).exists():
                    chrome_path = path
                    from utils.log import taobao_guanghe_logger
                    taobao_guanghe_logger.info(f"📍 使用系统 Chrome: {chrome_path}")
                    break

                # 启动浏览器
        launch_options = {
            "headless": True,
            "args": [
                '--disable-features=AsyncDns',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        }

        if chrome_path:
            launch_options["executable_path"] = chrome_path
        else:
            launch_options["channel"] = "chrome"

        browser = await playwright.chromium.launch(**launch_options)
        try:
            # 不使用代理，避免连接问题
            context = await browser.new_context(
                storage_state=str(account_file),
            )
            if enable_stealth:
                context = await set_init_script(context)
            page = await context.new_page()

            # 访问创作者中心
            try:
                await page.goto("https://creator.guanghe.taobao.com/", timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                from utils.log import taobao_guanghe_logger
                taobao_guanghe_logger.warning(f"⚠️ 访问创作者中心失败: {str(e)}")
                return False, ""

            await asyncio.sleep(3)

            # 检查当前 URL
            current_url = page.url
            from utils.log import taobao_guanghe_logger
            taobao_guanghe_logger.info(f"📍 当前 URL: {current_url}")

            # 有效：停留在 creator.guanghe.taobao.com 域
            if "creator.guanghe.taobao.com" in current_url:
                taobao_guanghe_logger.info("✅ Cookie 有效")
                return True, current_url

            # 其它情况一律判失效（含 login.taobao.com SSO 跳板 / passport.taobao.com 风控页 / 任何重定向）
            taobao_guanghe_logger.warning(f"❌ Cookie 已失效（未落在 creator 域: {current_url[:80]}）")
            return False, current_url

        finally:
            await browser.close()


async def cookie_auth(
    account_file: str | Path,
    use_system_chrome: bool = True,
    enable_stealth: bool = False,
) -> bool:
    """
    验证 Cookie 是否有效（公开 API，保持 bool 返回以兼容现有调用方）。

    Args:
        account_file: storageState 文件路径
        use_system_chrome: 是否使用系统 Chrome
        enable_stealth: 是否启用 stealth 反检测脚本

    Returns:
        bool: Cookie 是否有效
    """
    ok, _ = await _cookie_auth_impl(account_file, use_system_chrome, enable_stealth)
    return ok


async def taobao_guanghe_setup(
    account_file: str | Path,
    handle: bool = False,
    return_detail: bool = False,
    qrcode_callback=None,
    headless: bool = True,
    use_system_chrome: bool = False,
) -> bool | dict:
    """
    设置淘宝光合账号（验证或重新登录）

    Args:
        account_file: storageState 文件路径
        handle: 是否自动处理登录失效
        return_detail: 是否返回详细信息
        qrcode_callback: 二维码回调函数
        headless: 是否无头模式
        use_system_chrome: 是否使用系统 Chrome（解决网络问题）

    Returns:
        bool | dict: 是否成功或详细结果
    """
    account_file = Path(account_file)

    if not account_file.exists() or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(
                False, "cookie_invalid", "cookie文件不存在或已失效", account_file
            )
            return result if return_detail else False

        taobao_guanghe_logger.info("🥹 cookie 失效，准备重新登录")
        result = await taobao_guanghe_cookie_gen(
            account_file,
            qrcode_callback=qrcode_callback,
            headless=headless,
            use_system_chrome=use_system_chrome,
        )
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def taobao_guanghe_cookie_gen(
    account_file: str | Path,
    qrcode_callback=None,
    headless: bool = True,
    use_system_chrome: bool = False,
) -> dict:
    """
    生成淘宝光合 Cookie（二维码登录）

    Args:
        account_file: 保存 storageState 的文件路径
        qrcode_callback: 二维码回调函数
        headless: 是否无头模式
        use_system_chrome: 是否使用系统 Chrome（解决网络问题）

    Returns:
        dict: 登录结果
    """
    account_file = Path(account_file)
    url_changed_event = asyncio.Event()
    # 出验证码时 set；主流程超时会读这个标志决定下一步是"超时"还是"继续等"
    captcha_event = asyncio.Event()
    original_url = GUANGHE_HOME_URL

    async def on_frame_navigated(frame):
        """监听页面导航事件"""
        nonlocal original_url
        if frame == page.main_frame:
            current_url = page.url
            # 登录成功会跳转到创作者中心
            if "creator.guanghe.taobao.com" in current_url:
                taobao_guanghe_logger.info(f"🎉 检测到页面跳转: {current_url}")
                url_changed_event.set()
            # 风控：跳到 passport，需要人工验证
            elif PASSPORT_URL_KEY in current_url:
                taobao_guanghe_logger.warning(
                    f"🛡️ 检测到风控页: {current_url}，需要用户在已打开的浏览器中完成验证"
                )
                captcha_event.set()

    async with async_playwright() as playwright:
        # 查找系统 Chrome
        chrome_path = None
        if use_system_chrome:
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"),
            ]
            for path in possible_paths:
                if Path(path).exists():
                    chrome_path = path
                    taobao_guanghe_logger.info(f"📍 使用系统 Chrome: {chrome_path}")
                    break

        # 启动浏览器
        launch_options = {
            "headless": headless,
            "args": [
                '--disable-blink-features=AutomationControlled',
                '--disable-features=AsyncDns',       # 强制 Chromium 使用系统 DNS（Windows 下 headless 模式必备）
                '--host-resolver-rules=MAP guanghe.taobao.com 59.82.122.140, MAP creator.guanghe.taobao.com 59.82.122.172',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
            ]
        }

        if chrome_path:
            launch_options["executable_path"] = chrome_path
        else:
            launch_options["channel"] = "chrome"

        browser = await playwright.chromium.launch(**launch_options)

        try:
            context = await browser.new_context()
            context = await set_init_script(context)
            page = await context.new_page()

            # 1. 访问淘宝光合首页（可能需要翻墙或者使用代理）
            taobao_guanghe_logger.info(f"🌐 访问淘宝光合首页: {GUANGHE_HOME_URL}")
            try:
                await page.goto(GUANGHE_HOME_URL, timeout=60000)
            except Exception as e:
                taobao_guanghe_logger.error(f"❌ 无法访问淘宝光合首页: {str(e)}")
                taobao_guanghe_logger.info("💡 提示：请检查网络连接，或确认 URL 是否正确")
                taobao_guanghe_logger.info("💡 浏览器能打开但脚本无法访问，可能是 DNS 或代理配置问题")
                return _build_login_result(
                    False, "network_error", f"无法访问淘宝光合首页: {str(e)}", account_file
                )
            original_url = page.url

            # 2. 等待二维码出现
            taobao_guanghe_logger.info("⏳ 等待二维码加载...")
            try:
                await page.locator(QRCODE_CANVAS).wait_for(state="visible", timeout=30000)
            except Exception as e:
                taobao_guanghe_logger.error(f"❌ 二维码未出现: {str(e)}")
                return _build_login_result(
                    False, "qrcode_not_found", "二维码未出现", account_file
                )

            # 3. 截取二维码 Canvas
            taobao_guanghe_logger.info("📸 正在截取二维码...")
            qrcode_path = build_login_qrcode_path("taobao_guanghe", account_file.stem)

            # 截取 Canvas 二维码
            qrcode_element = page.locator(QRCODE_CANVAS).first
            await qrcode_element.screenshot(path=str(qrcode_path))

            # 4. 解析二维码内容
            try:
                qrcode_content = decode_qrcode_from_path(qrcode_path)
            except Exception as e:
                taobao_guanghe_logger.warning(f"⚠️ 无法解析二维码内容: {str(e)}")
                qrcode_content = None

            # 5. 显示终端二维码（如果解析成功）
            if qrcode_content:
                import segno
                print()
                print("📱 请使用淘宝 App 扫描下方二维码登录：")
                qrcode = segno.make(qrcode_content, error="L", boost_error=False)
                try:
                    qrcode.terminal(compact=True, border=0)
                except Exception:
                    print(f"二维码已保存到: {qrcode_path}")
                print()
            else:
                print(f"📱 请打开浏览器扫描二维码，或查看: {qrcode_path}")
                print()

            # 6. 触发回调
            if qrcode_callback:
                try:
                    callback_result = qrcode_callback(
                        {
                            "qrcode_path": str(qrcode_path),
                            "qrcode_content": qrcode_content,
                        }
                    )
                    if asyncio.iscoroutine(callback_result):
                        await callback_result
                except Exception as e:
                    taobao_guanghe_logger.warning(f"⚠️ 二维码回调失败: {str(e)}")

            taobao_guanghe_logger.info("📱 请使用淘宝 App 扫描二维码登录")
            taobao_guanghe_logger.info("⏱️  等待扫码（最多 200 秒）...")

            # 7. 监听页面跳转
            page.on("framenavigated", on_frame_navigated)

            # 7.1 等创作者中心跳转（200s 内）
            try:
                await asyncio.wait_for(url_changed_event.wait(), timeout=200)
                taobao_guanghe_logger.info("✅ 登录成功！")
            except asyncio.TimeoutError:
                # 检查是否触发了风控
                if captcha_event.is_set():
                    # 通过回调通知前端（仅在旧后端包装里实际推送 SSE）
                    if qrcode_callback:
                        try:
                            cb_result = qrcode_callback({"status": CAPTCHA_REQUIRED_SIGNAL})
                            if asyncio.iscoroutine(cb_result):
                                await cb_result
                        except Exception as e:
                            taobao_guanghe_logger.warning(f"⚠️ 验证码回调失败: {e}")

                    # 继续等跳回创作者中心，给用户手动操作的时间
                    taobao_guanghe_logger.info(
                        f"⏳ 等待用户在浏览器中完成验证（最多 {CAPTCHA_WAIT_TIMEOUT}s）..."
                    )
                    try:
                        await asyncio.wait_for(
                            url_changed_event.wait(), timeout=CAPTCHA_WAIT_TIMEOUT
                        )
                        taobao_guanghe_logger.info("✅ 用户完成验证，登录成功！")
                    except asyncio.TimeoutError:
                        taobao_guanghe_logger.error("⏱️ 验证码等待超时")
                        return _build_login_result(
                            False, "captcha_timeout",
                            f"验证码等待超时（{CAPTCHA_WAIT_TIMEOUT}s）", account_file,
                        )
                else:
                    taobao_guanghe_logger.error("⏱️ 登录超时")
                    return _build_login_result(
                        False, "timeout", "登录超时（200s）", account_file
                    )

            # 8. 等待页面稳定
            await asyncio.sleep(2)

            # 9. 关闭可能的新手引导弹窗
            try:
                # 关闭引导弹窗
                close_button = page.locator(".guide-modal-close-icon").first
                if await close_button.count() > 0:
                    await close_button.click()
                    taobao_guanghe_logger.info("🚫 关闭引导弹窗")
            except:
                pass

            try:
                # 关闭欢迎弹窗
                welcome_close = page.get_by_role("button", name="关闭").first
                if await welcome_close.count() > 0:
                    await welcome_close.click()
                    taobao_guanghe_logger.info("🚫 关闭欢迎弹窗")
            except:
                pass

            # 10. 保存 storageState
            taobao_guanghe_logger.info("💾 保存 Cookie...")
            account_file.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(account_file))

            # 11. 验证 Cookie
            taobao_guanghe_logger.info("🔍 验证 Cookie 有效性...")
            if not await cookie_auth(account_file):
                taobao_guanghe_logger.error("❌ Cookie 验证失败")
                return _build_login_result(
                    False, "verification_failed", "Cookie 验证失败", account_file
                )

            taobao_guanghe_logger.info("🎊 登录完成并验证成功！")
            return _build_login_result(
                True, "success", "登录成功", account_file, current_url=page.url
            )

        finally:
            await browser.close()


# 用于 CLI 和测试
async def main():
    """测试登录功能"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python login.py <account_name>")
        sys.exit(1)

    account_name = sys.argv[1]
    account_file = Path(f"cookies/taobao_guanghe_uploader/{account_name}.json")

    result = await taobao_guanghe_setup(
        account_file=account_file,
        handle=True,
        return_detail=True,
        headless=False,  # 显示浏览器窗口
    )

    print("\n" + "=" * 50)
    print("登录结果:")
    print(f"成功: {result['success']}")
    print(f"状态: {result['status']}")
    print(f"消息: {result['message']}")
    print(f"账号文件: {result['account_file']}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())


# ============================================================
# 旧版后端 (sau_backend.py) 兼容入口
# ============================================================
# 旧版后端使用 (id, status_queue) 协议，账号 cookie 保存到
# cookiesFile/{uuid}.json，并通过 user_info(type=5) 记录。
# 这里在 taobao_guanghe_cookie_gen 之上做一次轻量包装，复用其扫码流程。

import base64
import sqlite3
import uuid as _uuid

from conf import BASE_DIR as _BASE_DIR
from myUtils.auth import check_cookie as _check_cookie


def _read_qrcode_as_base64(qrcode_path: Path) -> str:
    """读取二维码图片文件并编码为 base64 字符串，供 SSE 推送给前端展示。"""
    return base64.b64encode(qrcode_path.read_bytes()).decode("ascii")


async def get_taobao_guanghe_cookie(id, status_queue):
    """淘宝光合扫码登录（旧版后端 SSE 协议）

    Args:
        id: 用户自定义账号名
        status_queue: 后端传入的 Queue；先 put 二维码 base64，再 put "200"/"500"
    """
    try:
        cookies_dir = Path(_BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(parents=True, exist_ok=True)
        target_file = cookies_dir / f"{_uuid.uuid1()}.json"

        qrcode_callback_done = {"ok": False}

        def _cb(info):
            # info 可能包含 "qrcode_path"（二维码 base64）或 "status"（验证码信号）
            try:
                if "qrcode_path" in info:
                    b64 = _read_qrcode_as_base64(Path(info["qrcode_path"]))
                    status_queue.put(b64)
                    qrcode_callback_done["ok"] = True
                if info.get("status") == CAPTCHA_REQUIRED_SIGNAL:
                    status_queue.put(CAPTCHA_REQUIRED_SIGNAL)
            except Exception as e:
                taobao_guanghe_logger.warning(f"⚠️ 二维码/验证码回调失败: {e}")

        result = await taobao_guanghe_cookie_gen(
            target_file,
            qrcode_callback=_cb,
            headless=False,        # 淘宝二维码 canvas 在 headless 下可能不渲染，使用有头模式
            use_system_chrome=True, # 优先找本地已安装的 Chrome，绕过 headless 检测
        )

        if not qrcode_callback_done["ok"]:
            # 二维码都没拿到，直接告诉前端失败
            status_queue.put("500")
            return None

        if not result.get("success"):
            taobao_guanghe_logger.error(f"❌ 登录失败: {result.get('message')}")
            status_queue.put("500")
            return None

        # 用 legacy 路径下的相对文件名做 cookie 验证
        rel_path = target_file.name
        verified, current_url = await _cookie_auth_impl(target_file)
        if not verified:
            # 看是否是被风控/SSO 跳板 — 这种情况下用户可以在自己浏览器里完成验证
            captcha_url = _extract_captcha_url(current_url)
            if captcha_url is not None:
                taobao_guanghe_logger.warning(
                    f"🛡️ cookie 被风控/SSO 跳板: {current_url}，等待用户在自己浏览器里完成验证"
                )
                # 推 SSE 信号：captcha_required||URL
                try:
                    status_queue.put(f"{CAPTCHA_REQUIRED_SIGNAL}||{captcha_url}")
                except Exception as e:
                    taobao_guanghe_logger.warning(f"⚠️ 验证码信号推送失败: {e}")

                # 等待用户在自己浏览器里完成验证（前端 POST /taobaoCaptchaDone 唤醒）
                done = await _wait_for_captcha_done(id, timeout=600)
                if not done:
                    taobao_guanghe_logger.error("⏱️ 等待用户完成验证超时（600s）")
                    status_queue.put("500")
                    return None

                # 用户说完成了——重试 cookie_auth，10 分钟内每 5s 一次
                verified = False
                for attempt in range(120):
                    await asyncio.sleep(5)
                    verified, current_url = await _cookie_auth_impl(target_file)
                    if verified:
                        taobao_guanghe_logger.success(
                            f"✅ 用户完成验证，cookie 有效（第 {attempt + 1} 次重试）"
                        )
                        break
                if not verified:
                    taobao_guanghe_logger.error(
                        f"❌ 用户完成验证后 cookie 仍无效: {current_url}"
                    )
                    status_queue.put("500")
                    return None
            else:
                taobao_guanghe_logger.error(
                    f"❌ cookie 验证失败（非风控 URL）: {current_url}"
                )
                status_queue.put("500")
                return None

        # 写入 user_info(type=5)
        db_path = Path(_BASE_DIR / "db" / "database.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_info (type, filePath, userName, status) VALUES (?, ?, ?, ?)",
                (5, rel_path, id, 1),
            )
            conn.commit()
            taobao_guanghe_logger.success(f"✅ 淘宝账号已入库: {id}")

        status_queue.put("200")
        return rel_path
    except Exception as exc:
        taobao_guanghe_logger.error(f"❌ 淘宝登录异常: {exc}", exc_info=True)
        status_queue.put("500")
        return None


# ============================================================
# 风控验证等待机制
# ============================================================
# 后端推送 captcha_required 信号给前端 → 前端展示 URL 给用户 → 用户在自己
# 浏览器里完成验证 → 前端 POST /taobaoCaptchaDone → 后端 signal_captcha_done
# 唤醒对应账号的等待。后端是 asyncio 协程，但前端 POST 走的是 Flask 同步线
# 程，所以用 threading.Event 在两边桥接。

import threading
import asyncio as _asyncio  # noqa: E402  # 用于在协程里 wait 事件


_captcha_wait_events: dict[str, threading.Event] = {}
_captcha_wait_lock = threading.Lock()


def _extract_captcha_url(current_url: str) -> str | None:
    """从 cookie_auth 返回的 URL 里判断是否需要用户介入验证。

    只匹配两类：passport.taobao.com（扫码风控/滑块/短信）和 login.taobao.com
    （SSO 重定向跳板）。其它 URL 一律判 False，由调用方走"真失效"分支。
    """
    url_lower = current_url.lower()
    if PASSPORT_URL_KEY in url_lower or "login.taobao.com" in url_lower:
        return current_url
    return None


async def _wait_for_captcha_done(account_id: str, timeout: float = 600) -> bool:
    """等待前端 POST /taobaoCaptchaDone 唤醒。

    Returns:
        True  用户在 timeout 内点了"我已完成"
        False 超时未响应
    """
    ev = threading.Event()
    with _captcha_wait_lock:
        _captcha_wait_events[account_id] = ev

    loop = _asyncio.get_event_loop()

    def _wait():
        return ev.wait(timeout=timeout)

    try:
        taobao_guanghe_logger.info(
            f"⏳ 等待用户在前端确认完成验证（最多 {timeout:.0f}s）..."
        )
        done = await loop.run_in_executor(None, _wait)
        return done
    finally:
        with _captcha_wait_lock:
            _captcha_wait_events.pop(account_id, None)


def signal_captcha_done(account_id: str) -> bool:
    """前端 POST /taobaoCaptchaDone 时调用，唤醒对应账号的等待协程。

    Returns:
        True  唤醒成功
        False 当前没有等待中的账号（可能超时了或重复点击）
    """
    with _captcha_wait_lock:
        ev = _captcha_wait_events.get(account_id)
        if ev is None:
            return False
        ev.set()
        return True
