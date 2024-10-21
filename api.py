from fastapi import FastAPI, HTTPException, BackgroundTasks, Form, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import asyncio
import uvicorn
import tempfile
import os

from conf import BASE_DIR
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
from uploader.douyin_img_uploader.main import DouYinImage
from uploader.ks_uploader.main import ks_setup, KSVideo
from uploader.tencent_uploader.main import weixin_setup, TencentVideo
from uploader.tk_uploader.main_chrome import tiktok_setup, TiktokVideo
from utils.base_social_media import SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU
from utils.constant import TencentZoneTypes
from utils.files_times import get_title_and_hashtags, get_title_and_hashtags_from_content

app = FastAPI()

class LoginRequest(BaseModel):
    platform: str
    account_name: str
    phone_number: str  # 新增字段

class UploadRequest(BaseModel):
    platform: str
    account_name: str
    file_paths: List[str]
    upload_type: str = 'video'
    publish_type: int = 0
    schedule: Optional[str] = None
    location: str = '成都市'
    text_file_content: Optional[str] = None  # 修改为存储文件内容

async def perform_login(platform: str, account_name: str, phone_number: str):
    """
    执行登录操作的异步函数
    
    :param platform: 社交媒体平台
    :param account_name: 账户名称
    :param phone_number: 电话号码
    """
    account_file = Path(BASE_DIR / "cookies" / f"{platform}_{account_name}.json")
    account_file.parent.mkdir(exist_ok=True)

    if platform == SOCIAL_MEDIA_DOUYIN:
        await douyin_setup(str(account_file), handle=True, phone_number=phone_number)
    elif platform == SOCIAL_MEDIA_TIKTOK:
        await tiktok_setup(str(account_file), handle=True)
    elif platform == SOCIAL_MEDIA_TENCENT:
        await weixin_setup(str(account_file), handle=True)
    elif platform == SOCIAL_MEDIA_KUAISHOU:
        await ks_setup(str(account_file), handle=True)
    else:
        raise HTTPException(status_code=400, detail="不支持的平台")

async def perform_upload(upload_request: UploadRequest):
    """
    执行上传操作的异步函数
    
    :param upload_request: 上传请求对象
    """
    account_file = Path(BASE_DIR / "cookies" / f"{upload_request.platform}_{upload_request.account_name}.json")
    
    if upload_request.text_file_content:
        title, tags = get_title_and_hashtags_from_content(upload_request.text_file_content)
    else:
        title, tags = '', []

    if upload_request.publish_type == 0:
        publish_date = 0
    else:
        publish_date = datetime.strptime(upload_request.schedule, '%Y-%m-%d %H:%M')

    if upload_request.platform == SOCIAL_MEDIA_DOUYIN:
        await douyin_setup(account_file, handle=False)
        if upload_request.upload_type == 'video':
            app = DouYinVideo(title, upload_request.file_paths[0], tags, publish_date, account_file)
        else:
            app = DouYinImage(title, upload_request.file_paths, tags, publish_date, account_file, location=upload_request.location)
    elif upload_request.platform == SOCIAL_MEDIA_TIKTOK:
        await tiktok_setup(account_file, handle=True)
        app = TiktokVideo(title, upload_request.file_paths[0], tags, publish_date, account_file)
    elif upload_request.platform == SOCIAL_MEDIA_TENCENT:
        await weixin_setup(account_file, handle=True)
        category = TencentZoneTypes.LIFESTYLE.value
        app = TencentVideo(title, upload_request.file_paths[0], tags, publish_date, account_file, category)
    elif upload_request.platform == SOCIAL_MEDIA_KUAISHOU:
        await ks_setup(account_file, handle=True)
        app = KSVideo(title, upload_request.file_paths[0], tags, publish_date, account_file)
    else:
        raise HTTPException(status_code=400, detail="不支持的平台")

    await app.main()

@app.post("/login")
async def login(login_request: LoginRequest, background_tasks: BackgroundTasks):
    """
    登录接口
    
    :param login_request: 登录请求对象
    :param background_tasks: 后台任务对象
    :return: 包含操作信息的字典
    """
    background_tasks.add_task(perform_login, login_request.platform, login_request.account_name, login_request.phone_number)
    return {"message": f"正在为 {login_request.platform} 平台的 {login_request.account_name} 账号执行登录操作"}

@app.post("/upload")
async def upload(
    platform: str = Form(...),
    account_name: str = Form(...),
    upload_type: str = Form(default='video'),
    publish_type: int = Form(default=0),
    schedule: Optional[str] = Form(default=None),
    location: str = Form(default='成都市'),
    text_file: Optional[UploadFile] = File(default=None),
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    with tempfile.TemporaryDirectory() as temp_dir:
        file_paths = []
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
            file_paths.append(file_path)
        
        text_file_content = None
        if text_file:
            text_file_content = (await text_file.read()).decode('utf-8')
        
        upload_request = UploadRequest(
            platform=platform,
            account_name=account_name,
            file_paths=file_paths,
            upload_type=upload_type,
            publish_type=publish_type,
            schedule=schedule,
            location=location,
            text_file_content=text_file_content
        )
        
        await perform_upload(upload_request)
    
    return {"message": f"正在为 {platform} 平台的 {account_name} 账号执行上传操作"}

def main():
    """
    应用程序入口函数
    """
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
