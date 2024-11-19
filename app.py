from fastapi import BackgroundTasks, FastAPI, Form
from uploader.bilibili_uploader.extra import get_bilibili_login_account_ids, get_bilibili_login_info, request_login_url

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

