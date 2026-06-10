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


async def cookie_auth(
    account_file: str | Path,
    use_system_chrome: bool = True,
    enable_stealth: bool = False,
) -> bool:
    """
    验证 Cookie 是否有效

    Args:
        account_file: storageState 文件路径
        use_system_chrome: 是否使用系统 Chrome
        enable_stealth: 是否启用 stealth 反检测脚本

    Returns:
        bool: Cookie 是否有效
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
                return False

            await asyncio.sleep(3)

            # 检查当前 URL
            current_url = page.url
            from utils.log import taobao_guanghe_logger
            taobao_guanghe_logger.info(f"📍 当前 URL: {current_url}")

            # 如果跳转到登录页（任何包含 login 的 URL），Cookie 无效
            if "login" in current_url.lower() or "passport" in current_url.lower():
                taobao_guanghe_logger.warning(f"❌ Cookie 已失效（跳转到: {current_url[:80]}）")
                return False

            # 如果停留在 creator.guanghe.taobao.com 域，说明 Cookie 有效
            if "creator.guanghe.taobao.com" in current_url:
                taobao_guanghe_logger.info("✅ Cookie 有效")
                return True

            # 其他情况
            taobao_guanghe_logger.warning(f"⚠️ 未预期的 URL: {current_url}")
            return False

        finally:
            await browser.close()


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

            try:
                await asyncio.wait_for(url_changed_event.wait(), timeout=200)
                taobao_guanghe_logger.info("✅ 登录成功！")
            except asyncio.TimeoutError:
                taobao_guanghe_logger.error("⏱️ 登录超时")
                return _build_login_result(
                    False, "timeout", "登录超时（200秒）", account_file
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
