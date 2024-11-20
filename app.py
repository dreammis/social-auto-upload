from fastapi import BackgroundTasks, FastAPI, Form
from type.upload_video_by_url_request import UploadVideoByUrlRequest
from uploader.bilibili_uploader.extra import get_bilibili_login_account_ids, get_bilibili_login_info, request_login_url
from uploader.uploader import run_upload_task

app = FastAPI()

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

@app.post("/upload_video_by_url")
async def upload_video_by_url(upload_video_by_url_request: UploadVideoByUrlRequest, background_tasks: BackgroundTasks):
    request = upload_video_by_url_request
    background_tasks.add_task(run_upload_task,video_url=request.video_url,video_file_name=request.video_file_name,title=request.title,description=request.description,tags=request.tags,tid=request.tid,timestamp=request.timestamp,platforms=request.platforms)
    return {"message": "Video upload task ran"}
