import asyncio
import sqlite3

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
from utils.runtime_config import get_login_browser_headless
import uuid
from pathlib import Path
from conf import BASE_DIR, LOCAL_CHROME_PATH

# 统一获取浏览器启动配置（防风控+引入本地浏览器）
def get_browser_options(douyin=False):
    options = {
        'headless': get_login_browser_headless(),
        'args': [
            '--lang=en-GB'
        ]
    }
    if douyin:
        options['args'] = [
            '--disable-blink-features=AutomationControlled',  # 核心防爬屏蔽：去掉 window.navigator.webdriver 标签
            '--lang=zh-CN',
            '--disable-infobars',
            '--start-maximized'
        ]
    # 如果用户在 conf.py 里配置了本地 Chrome，就用本地的，这样成功率极高
    if LOCAL_CHROME_PATH:
        options['executable_path'] = LOCAL_CHROME_PATH

    return options


def resolve_cookie_target(existing_file_path=None):
    cookies_dir = Path(BASE_DIR / "cookiesFile")
    cookies_dir.mkdir(exist_ok=True)

    if existing_file_path:
        return cookies_dir / existing_file_path, existing_file_path

    filename = f"{uuid.uuid1()}.json"
    return cookies_dir / filename, filename


def persist_account_login(account_type, file_name, user_name, account_id=None):
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        if account_id:
            cursor.execute(
                '''
                UPDATE user_info
                SET type = ?, filePath = ?, userName = ?, status = ?, last_login_time = CURRENT_TIMESTAMP
                WHERE id = ?
                ''',
                (account_type, file_name, user_name, 1, account_id)
            )
        else:
            cursor.execute(
                '''
                INSERT INTO user_info (type, filePath, userName, status, last_login_time)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (account_type, file_name, user_name, 1)
            )
        conn.commit()

# 抖音登录
async def douyin_cookie_gen(id, status_queue, account_id=None, existing_file_path=None):
    url_changed_event = asyncio.Event()
    verification_code_received = False

    async def on_url_change():
        if page.url != original_url: 
            url_changed_event.set()
    
    async def check_verification_page():
        """检查是否出现身份验证页面，如果出现则自动点击发送短信验证码"""
        global pending_verification_code
        nonlocal verification_code_received
        try:
            # 检查页面是否已关闭或跳转
            try:
                if page.is_closed():
                    print("🔍 页面已关闭，停止检查")
                    return False
            except:
                print("🔍 页面检查失败，可能已关闭")
                return False
                
            print("🔍 正在检查身份验证页面...")

            # 先检查是否出现身份验证相关的文本
            verification_page_found = False
            try:
                text_element = page.get_by_text("为保障账号安全")
                if await text_element.is_visible(timeout=60):
                    print(f"✅ 检测到身份验证页面")
                    verification_page_found = True
            except:
                pass
            
            if not verification_page_found:
                return False
            
            # 点击"接收短信验证码"
            sms_button = page.get_by_text("接收短信验证码")
            if await sms_button.is_visible(timeout=60):
                print("🔍 正在点击接收短信验证码按钮...")
                await sms_button.click()
                print("✅ 已点击接收短信验证码按钮")
                status_queue.put("NEED_VERIFICATION")
            
            # 开始循环处理验证码输入和验证
            max_retry = 5  # 最多重试5次
            for retry in range(max_retry):
                # 等待用户输入验证码
                print(f"⏳ 等待用户输入验证码 (第{retry+1}次)...")
                
                # 清除之前的验证码
                pending_verification_code = None
                
                # 轮询检查 pending_verification_code
                verification_code_received = False
                for _ in range(60):  # 最多等待1分钟
                    if pending_verification_code:
                        print(f"✅ 收到验证码: {pending_verification_code}")
                        verification_code_received = True
                        break
                    await asyncio.sleep(1)
                
                if not verification_code_received:
                    print("❌ 等待验证码超时")
                    break
                
                if pending_verification_code:
                    print(f"✅ 正在输入验证码: {pending_verification_code}")
                    try:
                        verify_panel = page.locator('#uc-second-verify')
                        if await verify_panel.count() > 0:
                            input_box = verify_panel.locator('#button-input').first
                            await input_box.fill(pending_verification_code)
                            print("✅ 在弹窗中输入验证码成功")
                    except Exception as e:
                        print(f"❌ 输入验证码失败: {e}")

                    # 等待一下，然后点击验证按钮
                    await asyncio.sleep(0.5)
                    
                    # 在uc-second-verify弹窗内找“验证”按钮
                    try:
                        verify_panel = page.locator('#uc-second-verify')
                        if await verify_panel.count() > 0:
                            verify_button = verify_panel.get_by_text("验证", exact=True)
                            if await verify_button.count() > 0:
                                btn = verify_button.first
                                if await btn.is_visible(timeout=60):
                                    print(f"✅ 在弹窗内找到验证按钮")
                                    await btn.click()
                                    print(f"✅ 成功点击验证按钮")
                    except Exception as e:
                        print(f"⚠️ 点击验证按钮失败: {e}")

                    # 等待2秒，看是否出现验证码错误提示
                    await asyncio.sleep(2)

                    code_error = False
                    try:
                        # 检查两种可能的错误提示
                        error_texts = ["验证码错误，请重新输入", "错误次数过多或验证码过期，请稍后重试"]
                        for error_text in error_texts:
                            error_element = page.get_by_text(error_text)
                            if await error_element.is_visible(timeout=60):
                                print(f"❌ 检测到错误: {error_text}")
                                code_error = True
                                status_queue.put("VERIFICATION_ERROR")
                                break
                    except:
                        pass
                    
                    if not code_error:
                        # 没有错误，可能验证成功了，退出循环
                        print("✅ 没有检测到验证码错误，继续等待页面跳转")
                        break
                    else:
                        # 验证码错误，清除验证码，等待重新输入
                        pending_verification_code = None
                        print("🔄 准备等待用户重新输入验证码...")
                        continue
        
            return True
        except Exception as e:
            print(f"❌ 检查验证码页面出错: {e}")
            return False
    
    async with async_playwright() as playwright:
        options = get_browser_options(True)
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        original_url = page.url
        
        # 保存page对象到全局变量，清除旧的验证码
        global active_login_page
        global pending_verification_code
        active_login_page = page
        pending_verification_code = None
        
        img_locator = page.get_by_role("img", name="二维码")
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)
        
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)
        
        # 标记二维码是否消失（表示用户已经扫描）
        qr_disappeared = False
        
        try:
            start_time = asyncio.get_event_loop().time()
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > 200:
                    raise asyncio.TimeoutError()
                
                if url_changed_event.is_set():
                    print("✅ 监听页面跳转成功")
                    break
                
                # 检查二维码是否还存在
                if not qr_disappeared:
                    try:
                        qr_exists = await img_locator.is_visible(timeout=500)
                        if not qr_exists:
                            print("✅ 二维码已消失，用户可能已扫描")
                            qr_disappeared = True
                    except:
                        # 如果检查二维码出错，可能是二维码已经消失
                        print("🔍 二维码检查出错，可能已消失")
                        qr_disappeared = True
                
                # 只有二维码消失后且还没跳转才检查身份验证页面
                if qr_disappeared and not url_changed_event.is_set():
                    await check_verification_page()
                
                await asyncio.sleep(0.5)  # 减少sleep时间，提高响应速度
                
        except asyncio.TimeoutError:
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None
        finally:
            active_login_page = None
            pending_verification_code = None
        
        cookie_path, file_name = resolve_cookie_target(existing_file_path)
        await context.storage_state(path=cookie_path)
        result = await check_cookie(3, file_name)
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()
        persist_account_login(3, file_name, id, account_id)
        print("✅ 用户状态已记录")
        status_queue.put("200")

# 全局变量
active_login_page = None
pending_verification_code = None

async def submit_verification_code(code):
    """提交验证码"""
    global pending_verification_code
    global active_login_page
    print(f"📨 收到验证码提交请求: {code}")
    print(f"   active_login_page: {active_login_page}")
    print(f"   当前pending_verification_code: {pending_verification_code}")
    
    if active_login_page:
        # 检查页面是否已关闭
        try:
            if active_login_page.is_closed():
                print(f"❌ 页面已关闭，不处理验证码")
                return False
        except:
            print(f"❌ 页面检查失败，不处理验证码")
            return False
            
        pending_verification_code = code
        print(f"✅ 设置验证码: {pending_verification_code}")
        return True
    else:
        print(f"❌ 当前没有待验证的登录流程")
    return False


# 视频号登录
async def get_tencent_cookie(id, status_queue, account_id=None, existing_file_path=None):
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
        cookie_path, file_name = resolve_cookie_target(existing_file_path)
        await context.storage_state(path=cookie_path)
        result = await check_cookie(2, file_name)
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        persist_account_login(2, file_name, id, account_id)
        print("✅ 用户状态已记录")
        status_queue.put("200")

# 快手登录
async def get_ks_cookie(id, status_queue, account_id=None, existing_file_path=None):
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
        cookie_path, file_name = resolve_cookie_target(existing_file_path)
        await context.storage_state(path=cookie_path)
        result = await check_cookie(4, file_name)
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        persist_account_login(4, file_name, id, account_id)
        print("✅ 用户状态已记录")
        status_queue.put("200")

# 小红书登录
async def xiaohongshu_cookie_gen(id, status_queue, account_id=None, existing_file_path=None):
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
        cookie_path, file_name = resolve_cookie_target(existing_file_path)
        await context.storage_state(path=cookie_path)
        result = await check_cookie(1, file_name)
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        persist_account_login(1, file_name, id, account_id)
        print("✅ 用户状态已记录")
        status_queue.put("200")


async def baijiahao_cookie_gen(id, status_queue, account_id=None, existing_file_path=None):
    """百家号登录"""
    url_changed_event = asyncio.Event()

    async def on_url_change():
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**get_browser_options())
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        page.on("framenavigated", lambda frame: asyncio.create_task(on_url_change()))

        original_url = "https://baijiahao.baidu.com/"
        await page.goto(original_url)
        status_queue.put("200")

        try:
            await asyncio.wait_for(url_changed_event.wait(), timeout=300)
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None

        cookie_path, file_name = resolve_cookie_target(existing_file_path)
        await context.storage_state(path=cookie_path)

        await page.close()
        await context.close()
        await browser.close()

        persist_account_login(7, file_name, id, account_id)
        print("✅ 百家号用户状态已记录")
        status_queue.put("200")


async def tiktok_cookie_gen(id, status_queue, account_id=None, existing_file_path=None):
    """TikTok登录（复用抖音登录逻辑）"""
    url_changed_event = asyncio.Event()

    async def on_url_change():
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**get_browser_options())
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        page.on("framenavigated", lambda frame: asyncio.create_task(on_url_change()))

        original_url = "https://www.tiktok.com/"
        await page.goto(original_url)
        status_queue.put("200")

        try:
            await asyncio.wait_for(url_changed_event.wait(), timeout=300)
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None

        cookie_path, file_name = resolve_cookie_target(existing_file_path)
        await context.storage_state(path=cookie_path)

        await page.close()
        await context.close()
        await browser.close()

        persist_account_login(6, file_name, id, account_id)
        print("✅ TikTok用户状态已记录")
        status_queue.put("200")


async def bilibili_cookie_gen(id, status_queue, account_id=None, existing_file_path=None):
    """B站登录（使用 playwright，和其他平台保持一致）"""
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

        # 直接访问B站登录页
        original_url = "https://passport.bilibili.com/login"
        await page.goto(original_url)

        # 等待页面加载完成
        await page.wait_for_load_state('networkidle')

        # 获取登录二维码图片
        try:
            img_locator = page.get_by_role("img", name="Scan me!")
            await img_locator.wait_for(state="visible", timeout=10000)
            src = await img_locator.get_attribute("src")
            print("✅ B站二维码地址:", src)
            status_queue.put(src)
            status_queue.put("MESSAGE:请使用B站APP扫码登录...")
        except Exception as e:
            print(f"❌ 获取二维码失败: {e}")
            status_queue.put("500:获取二维码失败，请重试")
            await page.close()
            await context.close()
            await browser.close()
            return None

        # 监听页面跳转
        page.on('framenavigated',
                lambda frame: asyncio.create_task(on_url_change()) if frame == page.main_frame else None)

        try:
            # 等待 URL 变化或超时（最多等待200秒）
            await asyncio.wait_for(url_changed_event.wait(), timeout=200)
            print("✅ 监听页面跳转成功，登录完成")
            print(f"当前URL: {page.url}")

            # 扫码成功后，访问上传页以获取完整的cookie
            print("正在访问B站上传页以获取完整cookie...")
            await page.goto("https://member.bilibili.com/platform/upload/video/frame")
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
                print(f"上传页加载完成，当前URL: {page.url}")
            except Exception as e:
                print(f"上传页加载超时: {e}")

            # 检查是否成功进入上传页
            if "passport.bilibili.com" in page.url:
                print("❌ 访问上传页失败，跳转到登录页")
                status_queue.put("500:登录成功但访问上传页失败，请重试")
                await page.close()
                await context.close()
                await browser.close()
                return None

        except asyncio.TimeoutError:
            status_queue.put("500:登录超时，请重试")
            print("❌ 监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None

        # 保存cookie
        cookie_path, file_name = resolve_cookie_target(existing_file_path)
        await context.storage_state(path=cookie_path)
        print(f"✅ Cookie已保存到: {cookie_path}")

        # 验证cookie是否有效
        result = await check_cookie(5, file_name)
        if not result:
            status_queue.put("500:登录成功但cookie验证失败，请重试")
            print("❌ B站登录成功但cookie验证失败")
            await page.close()
            await context.close()
            await browser.close()
            return None

        await page.close()
        await context.close()
        await browser.close()

        # 保存账号信息到数据库
        persist_account_login(5, file_name, id, account_id)
        print("✅ B站用户状态已记录")
        status_queue.put("MESSAGE:B站登录成功！")
        status_queue.put("200")


