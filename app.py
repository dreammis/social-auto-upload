from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, FastAPI, Form
from type.upload_video_by_url_request import UploadVideoByUrlRequest
from uploader.bilibili_uploader.extra import get_bilibili_login_account_ids, get_bilibili_login_info, request_login_url
from uploader.uploader import run_upload_task
from uploader.xhs_uploader.extra import get_xiaohongshu_login_account_ids
from uploader.xhs_uploader.login import xhs_login_client, xhs_login_creator
from playwright.async_api import async_playwright, Browser


browser_instances = {
    "firefox": Browser
}  # 用于存储浏览器实例的全局变量

@asynccontextmanager
async def lifespan(app: FastAPI):
    playwright = await async_playwright().start()
    browser_instances['firefox'] = await playwright.firefox.launch(headless=False)
    yield
    browser_instances["firefox"].close()

app = FastAPI(lifespan=lifespan)


@app.get("/bilibili/get_login_url")
def bilibili_login(background_tasks:BackgroundTasks):
    res = request_login_url(background_tasks)
    return res

@app.get("/bilibili/get_login_info")
async def bili_get_login_info(
    id: str = Form(...),
):
    response = get_bilibili_login_info(id)
    return response

@app.get("/bilibili/get_login_account")
async def bili_get_login_account():
    ids = get_bilibili_login_account_ids()
    response = {
        "code": 0,
        "data": ids
    }
    return response

@app.get("/xhs/get_login_client_qrcode_blob")
async def xhs_get_login_qrcode_blob(background_tasks: BackgroundTasks):
    qrcode_image_src = await xhs_login_client(background_tasks, browser=browser_instances["firefox"])

    return {
        "code": 0,
        "data": qrcode_image_src
    }


# @app.get("/xhs/get_login_creator_qrcode_blob")
# async def xhs_get_login_creator_qrcode_blob(background_tasks: BackgroundTasks, id: str = Form(...)):
#     qrcode_image_src = await xhs_login_creator(background_tasks, browser=browser_instances["firefox"], id=id)

#     return {
#         "code": 0,
#         "data": qrcode_image_src
#     }

@app.get("/xhs/get_login_account")
async def xiaohongshu_get_login_account():
    ids = get_xiaohongshu_login_account_ids()
    response = {
        "code": 0,
        "data": ids
    }
    return response

@app.post("/upload_video_by_url")
async def upload_video_by_url(upload_video_by_url_request: UploadVideoByUrlRequest, background_tasks: BackgroundTasks):
    request = upload_video_by_url_request
    background_tasks.add_task(run_upload_task,video_url=request.video_url,video_file_name=request.video_file_name,title=request.title,description=request.description,tags=request.tags,tid=request.tid,timestamp=request.timestamp,platforms=request.platforms)
    return {"message": "Video upload task ran"}

@app.get("/screenshot")
async def take_screenshot():
    async with async_playwright() as p:
        page = await browser_instances["firefox"].new_page()
        await page.goto("https://www.baidu.com")
        await page.screenshot(path="example.png")
        await page.context.clear_cookies()
        await page.close()
    return {"message": "Screenshot taken successfully"}
