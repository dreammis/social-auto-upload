import asyncio
import base64
import os
import sqlite3
import subprocess
import time

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from uploader.bilibili_uploader.runtime import ensure_biliup_binary
from utils.base_social_media import set_init_script
import uuid
from pathlib import Path
from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH


LOGIN_TIMEOUT_SECONDS = 300


def _image_data_url(image_bytes):
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _image_file_data_url(image_path):
    return _image_data_url(Path(image_path).read_bytes())


def _record_login_success(platform_type, file_name, user_name):
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO user_info (type, filePath, userName, status)
            VALUES (?, ?, ?, ?)
            ''',
            (platform_type, file_name, user_name, 1),
        )
        conn.commit()


def _hidden_process_kwargs():
    kwargs = {}
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _interactive_process_kwargs():
    kwargs = {}
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_CONSOLE"):
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    return kwargs


def _log_login_event(message):
    print(f"[login] {message}", flush=True)


def _tail_text_file(path, max_chars=4000):
    path = Path(path)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


async def _visible_qr_data_url(page):
    preferred_selectors = [
        "img[src*='qr']",
        "img[src*='qrcode']",
        "img[class*='qr']",
        "img[class*='qrcode']",
        "canvas[class*='qr']",
        "canvas[class*='qrcode']",
    ]
    fallback_selectors = ["canvas", "img"]
    deadline = time.monotonic() + 45

    while time.monotonic() < deadline:
        for frame in page.frames:
            for selector in preferred_selectors:
                locator = frame.locator(selector).first
                try:
                    if await locator.count() and await locator.is_visible():
                        return _image_data_url(await locator.screenshot())
                except Exception:
                    continue

            for selector in fallback_selectors:
                elements = frame.locator(selector)
                try:
                    count = min(await elements.count(), 20)
                except Exception:
                    continue
                for index in range(count):
                    locator = elements.nth(index)
                    try:
                        if not await locator.is_visible():
                            continue
                        box = await locator.bounding_box()
                        if not box:
                            continue
                        width = box.get("width", 0)
                        height = box.get("height", 0)
                        if width >= 120 and height >= 120 and abs(width - height) <= max(width, height) * 0.4:
                            return _image_data_url(await locator.screenshot())
                    except Exception:
                        continue

        await asyncio.sleep(0.5)

    return None


async def _wait_for_baijiahao_login(page):
    try:
        await page.wait_for_url("**/builder/rc/**", timeout=LOGIN_TIMEOUT_SECONDS * 1000)
        return True
    except Exception:
        pass

    try:
        await page.goto("https://baijiahao.baidu.com/builder/rc/home", timeout=15000)
        await page.wait_for_timeout(3000)
        return "builder/rc" in page.url
    except Exception:
        return False


async def _try_enable_tiktok_qr_login(page):
    qr_entry_texts = [
        "Use QR code",
        "Log in with QR code",
        "QR code",
        "使用二维码",
        "二维码登录",
        "扫码登录",
    ]
    for text in qr_entry_texts:
        try:
            locator = page.get_by_text(text, exact=False).first
            if await locator.count() and await locator.is_visible():
                await locator.click()
                await page.wait_for_timeout(1500)
                return
        except Exception:
            continue


async def _wait_for_tiktok_login(page):
    deadline = time.monotonic() + LOGIN_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if "tiktokstudio" in page.url or "creator-center" in page.url:
            return True
        try:
            login_controls = await page.locator("text=/Log in|Sign up|登录|注册/i").count()
            if login_controls == 0:
                await page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=en", timeout=15000)
                await page.wait_for_timeout(3000)
                if "login" not in page.url:
                    return True
        except Exception:
            pass
        await asyncio.sleep(2)
    return False

# 统一获取浏览器启动配置（防风控+引入本地浏览器）
def get_browser_options():
    options = {
        'headless': LOCAL_CHROME_HEADLESS,
        'args': [
            '--disable-blink-features=AutomationControlled',  # 核心防爬屏蔽：去掉 window.navigator.webdriver 标签
            '--lang=zh-CN',
            '--disable-infobars',
            '--start-maximized'
        ]
    }
    # 如果用户在 conf.py 里配置了本地 Chrome，就用本地的，这样成功率极高
    if LOCAL_CHROME_PATH:
        options['executable_path'] = LOCAL_CHROME_PATH

    return options


async def bilibili_cookie_gen(id, status_queue):
    uuid_v1 = uuid.uuid1()
    file_name = f"{uuid_v1}.json"
    cookies_dir = Path(BASE_DIR / "cookiesFile")
    cookies_dir.mkdir(exist_ok=True)
    account_file = cookies_dir / file_name
    work_dir = Path(BASE_DIR / "tmp" / "bilibili_login" / str(uuid_v1))
    work_dir.mkdir(parents=True, exist_ok=True)
    qrcode_path = work_dir / "qrcode.png"
    biliup_stdout_path = work_dir / "biliup.out.log"
    biliup_stderr_path = work_dir / "biliup.err.log"
    process = None

    try:
        _log_login_event(f"Bilibili login started, account={id}, work_dir={work_dir}")
        binary_path = ensure_biliup_binary(force_check=False)
        _log_login_event(f"Bilibili biliup binary={binary_path}")
        command = [str(binary_path), "-u", str(account_file), "login"]
        if os.name == "nt":
            _log_login_event("Bilibili login requires a real terminal; opening a biliup console window")
            process = subprocess.Popen(
                command,
                cwd=str(work_dir),
                **_interactive_process_kwargs(),
            )
        else:
            with biliup_stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_file:
                with biliup_stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_file:
                    process = subprocess.Popen(
                        command,
                        cwd=str(work_dir),
                        stdin=subprocess.DEVNULL,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        text=True,
                        **_hidden_process_kwargs(),
                    )

        deadline = time.monotonic() + LOGIN_TIMEOUT_SECONDS
        qrcode_sent = False
        while process.poll() is None:
            if not qrcode_sent and qrcode_path.exists() and qrcode_path.stat().st_size > 0:
                _log_login_event(f"Bilibili QR code ready: {qrcode_path}")
                status_queue.put(_image_file_data_url(qrcode_path))
                qrcode_sent = True

            if time.monotonic() > deadline:
                _log_login_event("Bilibili login timed out")
                process.kill()
                status_queue.put("500")
                return None

            await asyncio.sleep(0.5)

        if not qrcode_sent and qrcode_path.exists() and qrcode_path.stat().st_size > 0:
            _log_login_event(f"Bilibili QR code ready after process exit: {qrcode_path}")
            status_queue.put(_image_file_data_url(qrcode_path))

        if process.returncode != 0:
            _log_login_event(f"Bilibili login process failed with code={process.returncode}")
            _log_login_event(f"Bilibili stdout tail:\n{_tail_text_file(biliup_stdout_path)}")
            _log_login_event(f"Bilibili stderr tail:\n{_tail_text_file(biliup_stderr_path)}")
            status_queue.put("500")
            return None

        result = await check_cookie(5, file_name)
        if not result:
            _log_login_event("Bilibili cookie check failed after login")
            _log_login_event(f"Bilibili stdout tail:\n{_tail_text_file(biliup_stdout_path)}")
            _log_login_event(f"Bilibili stderr tail:\n{_tail_text_file(biliup_stderr_path)}")
            status_queue.put("500")
            return None

        _record_login_success(5, file_name, id)
        _log_login_event(f"Bilibili login succeeded, cookie={account_file}")
        status_queue.put("200")
    except Exception as e:
        _log_login_event(f"Bilibili login failed: {e}")
        if process and process.poll() is None:
            process.kill()
        status_queue.put("500")


async def baijiahao_cookie_gen_for_frontend(id, status_queue):
    uuid_v1 = uuid.uuid1()
    file_name = f"{uuid_v1}.json"
    cookies_dir = Path(BASE_DIR / "cookiesFile")
    cookies_dir.mkdir(exist_ok=True)
    account_file = cookies_dir / file_name
    browser = None
    context = None

    try:
        async with async_playwright() as playwright:
            options = get_browser_options()
            browser = await playwright.chromium.launch(**options)
            context = await browser.new_context()
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto("https://baijiahao.baidu.com/builder/theme/bjh/login", timeout=60000)

            qr_data = await _visible_qr_data_url(page)
            if not qr_data:
                status_queue.put("500")
                return None
            status_queue.put(qr_data)

            logged_in = await _wait_for_baijiahao_login(page)
            if not logged_in:
                status_queue.put("500")
                return None

            await context.storage_state(path=account_file)
            result = await check_cookie(6, file_name)
            if not result:
                status_queue.put("500")
                return None

            _record_login_success(6, file_name, id)
            status_queue.put("200")
    except Exception as e:
        print(f"Baijiahao login failed: {e}")
        status_queue.put("500")
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()

# 抖音登录
async def tiktok_cookie_gen_for_frontend(id, status_queue):
    uuid_v1 = uuid.uuid1()
    file_name = f"{uuid_v1}.json"
    cookies_dir = Path(BASE_DIR / "cookiesFile")
    cookies_dir.mkdir(exist_ok=True)
    account_file = cookies_dir / file_name
    browser = None
    context = None

    try:
        async with async_playwright() as playwright:
            options = get_browser_options()
            browser = await playwright.chromium.launch(**options)
            context = await browser.new_context()
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto("https://www.tiktok.com/login?lang=en", timeout=60000)
            await _try_enable_tiktok_qr_login(page)

            qr_data = await _visible_qr_data_url(page)
            if not qr_data:
                status_queue.put("500")
                return None
            status_queue.put(qr_data)

            logged_in = await _wait_for_tiktok_login(page)
            if not logged_in:
                status_queue.put("500")
                return None

            await context.storage_state(path=account_file)
            result = await check_cookie(7, str(account_file))
            if not result:
                status_queue.put("500")
                return None

            _record_login_success(7, file_name, id)
            status_queue.put("200")
    except Exception as e:
        print(f"TikTok login failed: {e}")
        status_queue.put("500")
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()


async def douyin_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = get_browser_options()
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        original_url = page.url
        img_locator = page.get_by_role("img", name="二维码")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)
        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(3, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status)
                                VALUES (?, ?, ?, ?)
                                ''', (3, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")


# 视频号登录
async def get_tencent_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        original_url = page.url

        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        # 等待 iframe 出现（最多等 60 秒）
        iframe_locator = page.frame_locator("iframe").first

        # 获取 iframe 中的第一个 img 元素
        img_locator = iframe_locator.get_by_role("img").first

        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(2,f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO user_info (type, filePath, userName, status)
                                VALUES (?, ?, ?, ?)
                                ''', (2, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# 快手登录
async def get_ks_cookie(id,status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com")

        # 定位并点击“立即登录”按钮（类型为 link）
        await page.get_by_role("link", name="立即登录").click()
        await page.get_by_text("扫码登录").click()
        img_locator = page.get_by_role("img", name="qrcode")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(4, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                        INSERT INTO user_info (type, filePath, userName, status)
                                        VALUES (?, ?, ?, ?)
                                        ''', (4, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# 小红书登录
async def xiaohongshu_cookie_gen(id,status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.xiaohongshu.com/")
        await page.locator('img.css-wemwzq').click()

        img_locator = page.get_by_role("img").nth(2)
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(1, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           INSERT INTO user_info (type, filePath, userName, status)
                           VALUES (?, ?, ?, ?)
                           ''', (1, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")

# a = asyncio.run(xiaohongshu_cookie_gen(4,None))
# print(a)
