import asyncio
import sqlite3
import base64

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
from utils.log import taobao_guanghe_logger
import uuid
from pathlib import Path
from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH

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
    # 浏览器选择优先级：
    # 1. conf.py 配了 LOCAL_CHROME_PATH → 用指定路径
    # 2. 否则用系统安装的 Chrome（channel=chrome）
    # 关键：打包后（PyInstaller）不带 playwright 自带的 chromium，
    # 必须走系统 Chrome，否则 launch 会报 "Executable doesn't exist ... .local-browsers"。
    if LOCAL_CHROME_PATH:
        options['executable_path'] = LOCAL_CHROME_PATH
    else:
        options['channel'] = 'chrome'

    return options

# 抖音登录
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

# 淘宝光合登录（type=5）
# 使用 playwright（与抖音/快手/小红书/视频号一致），不用 patchright
async def get_taobao_guanghe_cookie(id, status_queue):
    url_changed_event = asyncio.Event()
    async def on_url_change():
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = get_browser_options()
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()

        # 访问淘宝光合创作者中心
        taobao_guanghe_logger.info("🌐 访问淘宝光合创作者中心: https://creator.guanghe.taobao.com/")
        await page.goto("https://creator.guanghe.taobao.com/", timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        original_url = page.url
        taobao_guanghe_logger.info(f"📍 当前 URL: {original_url}")

        # 调试：保存页面 HTML 和截图，分析二维码结构
        debug_path = Path(BASE_DIR) / "logs" / "taobao_login_debug.png"
        debug_html_path = Path(BASE_DIR) / "logs" / "taobao_login_debug.html"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(debug_path), full_page=True)
        html_content = await page.content()
        debug_html_path.write_text(html_content, encoding="utf-8")
        taobao_guanghe_logger.info(f"📸 调试截图: {debug_path}")
        taobao_guanghe_logger.info(f"📄 调试 HTML: {debug_html_path}")

        # 分析页面上的二维码相关元素
        all_imgs = await page.locator("img").all()
        taobao_guanghe_logger.info(f"🔍 页面共有 {len(all_imgs)} 个 img 标签")
        for i, img in enumerate(all_imgs[:10]):
            try:
                src = await img.get_attribute("src") or ""
                alt = await img.get_attribute("alt") or ""
                visible = await img.is_visible()
                w = await img.get_attribute("width") or ""
                h = await img.get_attribute("height") or ""
                taobao_guanghe_logger.info(f"  img[{i}] visible={visible} {w}x{h} alt={alt[:30]} src={src[:80]}")
            except Exception:
                pass

        all_canvas = await page.locator("canvas").all()
        taobao_guanghe_logger.info(f"🔍 页面共有 {len(all_canvas)} 个 canvas 标签")
        for i, cvs in enumerate(all_canvas[:5]):
            try:
                visible = await cvs.is_visible()
                box = await cvs.bounding_box()
                taobao_guanghe_logger.info(f"  canvas[{i}] visible={visible} box={box}")
            except Exception:
                pass

        # 等待二维码出现 — 尝试多种选择器
        taobao_guanghe_logger.info("⏳ 等待二维码加载...")
        qrcode_src = None

        # 尝试1: canvas 二维码
        try:
            qrcode_canvas = page.locator("#qrcode-img canvas").first
            await qrcode_canvas.wait_for(state="visible", timeout=10000)
            taobao_guanghe_logger.info("📸 截取二维码 Canvas...")
            screenshot_bytes = await qrcode_canvas.screenshot()
            b64 = base64.b64encode(screenshot_bytes).decode("ascii")
            print("✅ 二维码已截图(base64)")
            status_queue.put(b64)
            qrcode_src = "canvas"
        except Exception as e:
            taobao_guanghe_logger.warning(f"⚠️ canvas 二维码未找到: {e}")

        # 尝试2: img 标签二维码
        if not qrcode_src:
            try:
                qrcode_img = page.locator("#qrcode-img img").first
                await qrcode_img.wait_for(state="visible", timeout=5000)
                src = await qrcode_img.get_attribute("src")
                if src:
                    print("✅ 图片地址(img):", src)
                    status_queue.put(src)
                    qrcode_src = "img"
            except Exception as e:
                taobao_guanghe_logger.warning(f"⚠️ img 二维码未找到: {e}")

        # 尝试3: 页面上任意含二维码特征的 img
        if not qrcode_src:
            try:
                # 淘宝登录页二维码通常是页面上的大图
                qrcode_img = page.locator("img[src*='qrcode'], img[src*='qr'], img[alt*='二维码']").first
                await qrcode_img.wait_for(state="visible", timeout=5000)
                src = await qrcode_img.get_attribute("src")
                if src:
                    print("✅ 图片地址(generic):", src[:80])
                    status_queue.put(src)
                    qrcode_src = "generic_img"
            except Exception as e:
                taobao_guanghe_logger.warning(f"⚠️ 通用 img 二维码未找到: {e}")

        # 尝试4: 整页截图作为二维码区域
        if not qrcode_src:
            try:
                # 淘宝登录可能整个页面就是扫码页，截整个可见区域
                taobao_guanghe_logger.info("📸 尝试整页截图作为二维码...")
                screenshot_bytes = await page.screenshot()
                b64 = base64.b64encode(screenshot_bytes).decode("ascii")
                print("✅ 整页截图(base64)")
                status_queue.put(b64)
                qrcode_src = "fullpage"
            except Exception as e:
                taobao_guanghe_logger.error(f"❌ 整页截图也失败: {e}")

        if not qrcode_src:
            taobao_guanghe_logger.error("❌ 无法获取二维码")
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None

        # 监听页面跳转（扫码成功后跳到创作者中心）
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        taobao_guanghe_logger.info("📱 请使用淘宝 App 扫描二维码登录")
        taobao_guanghe_logger.info("⏱️  等待扫码（最多 200 秒）...")

        try:
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)
            taobao_guanghe_logger.info("✅ 登录成功！")
        except asyncio.TimeoutError:
            taobao_guanghe_logger.error("⏱️ 登录超时")
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None

        # 等待页面稳定
        await asyncio.sleep(2)

        # 关闭可能的新手引导弹窗
        try:
            close_btn = page.locator(".guide-modal-close-icon").first
            if await close_btn.count() > 0:
                await close_btn.click()
        except Exception:
            pass

        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(5, f"{uuid_v1}.json")
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
                               ''', (5, f"{uuid_v1}.json", id, 1))
            conn.commit()
            print("✅ 用户状态已记录")
        status_queue.put("200")
