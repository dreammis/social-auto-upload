import asyncio
import json
import uuid
from fastapi import BackgroundTasks
from playwright.async_api import async_playwright, Browser

import base64

from utils.redis import add_to_xiaohongshu_login_list, get_xiaohongshu_login, register_xiaohongshu_login

def save_blob_as_image(blob_string, output_image_path):
    # 假设 blob_string 中包含的是 base64 编码的图片数据
    # 去掉data:image/png;base64,之类的前缀（如果有的话）
    if ',' in blob_string:
        blob_string = blob_string.split(',', 1)[1]

    # 解码 base64 数据
    image_data = base64.b64decode(blob_string)

    # 将二进制数据写入文件
    with open(output_image_path, 'wb') as image_file:
        image_file.write(image_data)


async def xhs_login_client(background_tasks: BackgroundTasks, browser: Browser):
    
    generated_login_uuid = uuid.uuid4()
    generated_login_uuid_str = str(generated_login_uuid)
    async with async_playwright() as p:
        
        try: 
          # 启动浏览器并打开新的页面
          context = await browser.new_context(
              viewport={'width': 1280, 'height': 720}  # 设置视口宽度和高度
          )
          page = await context.new_page()
          await page.context.clear_cookies()

          # 导航到目标网页
          await page.goto("https://www.xiaohongshu.com/explore")

          # 等待2s
          await page.wait_for_timeout(2000)

          # 获取二维码图像的 src 属性
          qr_code_image = page.locator(".qrcode-img")
          qr_code_image_src = await qr_code_image.get_attribute("src")

          async def get_cookie():
              try:
                for i in range(0, 180):
                  await asyncio.sleep(1) #一秒检测一次，最多三分钟
                  # 检查是否成功登录
                  user_link = page.get_by_role('link', name='我', exact=True)
                  if await user_link.is_visible():
                    break
                  if i == 180:
                    raise Exception("Login timeout")
                
                # 成功登录
                account_page_path = await page.get_attribute('li.user div.link-wrapper a.link-wrapper', 'href')
                parts = account_page_path.split('/')
                user_id = parts[-1]  # 获取最后一个部分
                if user_id is not None and user_id != '':
                    await page.get_by_role('link', name='我', exact=True).click()
                    await asyncio.sleep(5) # 等待页面加载
                    redId_text = await page.inner_text('span.user-redId')
                    redId = redId_text.split('：')[-1].strip()  # 提取冒号后面的内容并去除空白字符

                    await page.get_by_role('link', name='发布').click(); # 跳转创作者页面
                    await asyncio.sleep(10)
                    cookies = await context.cookies()
                    cookies_json = json.dumps(cookies)
                    await asyncio.sleep(10)

                    login_info = {
                      'redId': redId,
                      'client_cookie': cookies_json
                    }
                    register_xiaohongshu_login(generated_login_uuid_str, json.dumps(login_info))
                    return
                else:
                  raise Exception("Login failed, user_id is None or empty")
              except Exception as e:
                print("Login failed:", str(e))
              finally:
                await page.context.clear_cookies()
                await page.close()
                await context.close()

          background_tasks.add_task(get_cookie)

          return {
            'id': generated_login_uuid_str,
            'qr_code_image_src': qr_code_image_src

          }
        except Exception as e:
          print("An error occurred:", str(e))
          if page: 
            await page.context.clear_cookies()
            await page.close()

async def xhs_login_creator(background_tasks: BackgroundTasks, browser: Browser, id: str):
    async with async_playwright() as p:
        try: 
          client_cookie_json = get_xiaohongshu_login(id)['client_cookie']
          client_cookies = json.loads(client_cookie_json)

          # 启动浏览器并打开新的页面
          context = await browser.new_context(
              viewport={'width': 1280, 'height': 720}  # 设置视口宽度和高度
          )
          await context.add_cookies(client_cookies) # 写入小红书 Web 客户端的 Cookie
          page1 = await context.new_page()

          current_cookie = await page1.context.cookies()
          print('current_cookie', current_cookie)

          print('goto xiaohongshu')
          # 导航到目标网页
          await page1.goto("https://www.xiaohongshu.com")
          print('load success')

          # 等待2s
          await page1.wait_for_timeout(1000)

          await page1.get_by_role('button', name='创作中心').click();
          page_coro = page1.wait_for_event('popup') # 等待新标签页弹出
          await page1.get_by_role('link', name='创作服务').click();
          page = await page_coro
          # 等待页面加载完成
          await page.wait_for_load_state('networkidle', timeout=2000)

          # 获取二维码图像的 src 属性
          await page.locator('img').click();
          qr_code_image_element = page.get_by_role('img').nth(2)
          qr_code_image_src = await qr_code_image_element.get_attribute("src")

          async def get_cookie():
              try:
                for i in range(0, 180):
                  await asyncio.sleep(1) #一秒检测一次，最多三分钟
                  # 检查是否成功登录
                  redId = page.get_by_text('小红书账号:')
                  if await redId.is_visible():
                    break
                  if i == 180:
                    raise Exception("Login timeout")
                
                # 成功登录
                await asyncio.sleep(5)
                redId_text_element = page.get_by_text('小红书账号:')
                redId_text = await redId_text_element.inner_text()
                redId = redId_text.split(': ')[-1].strip()  # 提取冒号后面的内容并去除空白字符
                cookies = await context.cookies()
                cookies_json = json.dumps(cookies)

                login_info = {
                  'redId': redId,
                  'client_cookie': client_cookie_json,
                  'creator_cookie': cookies_json
                }
                register_xiaohongshu_login(id, json.dumps(login_info))
                add_to_xiaohongshu_login_list(id)
                return
              except Exception as e:
                print("Login failed:", str(e))
              finally:
                await page.context.clear_cookies()
                await page.close()

          background_tasks.add_task(get_cookie)

          return {
            'id': id,
            'qr_code_image_src': qr_code_image_src

          }
        except Exception as e:
          print("An error occurred:", str(e))
          if page: 
            await page.context.clear_cookies()
            await page.close()
