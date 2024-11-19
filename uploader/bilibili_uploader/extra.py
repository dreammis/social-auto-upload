import json
import uuid
from celery import shared_task
from fastapi import BackgroundTasks
from utils.redis import add_to_bilibili_login_list, get_all_bilibili_login_ids, get_bilibili_login, register_bilibili_login
import qrcode
from biliup.plugins.bili_webup import BiliBili, Data

async def test_login_by_qrcode():
    with BiliBili('test') as bili:
        res = bili.get_qrcode()
        print(res)
        url = res['data']['url']
        qr = qrcode.QRCode(version=1, error_correction=qrcode.ERROR_CORRECT_L,
                          box_size=10,
                          border=1)
        qr.add_data(url)
        qr.make()
        qr.print_ascii()
        login_value = await bili.login_by_qrcode(res)
        print(login_value)

async def login_by_qrcode(id: str, value):
    with BiliBili('test') as bili:
        try:
            login_value: dict = await bili.login_by_qrcode(value)
            if (login_value['code'] == 0):
                register_bilibili_login(id, json.dumps(login_value))
                add_to_bilibili_login_list(id)
        except Exception as e:
            print(e)
            return

def request_login_url(background_tasks: BackgroundTasks):
    with BiliBili('test') as bili:
        res = bili.get_qrcode()
        
        generated_login_uuid = uuid.uuid4()
        generated_login_uuid_str = str(generated_login_uuid)

        background_tasks.add_task(login_by_qrcode, generated_login_uuid_str, res)
        
        url = res['data']['url']
        qr = qrcode.QRCode(version=1, error_correction=qrcode.ERROR_CORRECT_L,
                            box_size=10,
                            border=1)
        qr.add_data(url)
        qr.make()
        qr.print_ascii()
        response = {
            "code": res["code"],
            "url": res["data"]["url"],
            "id": generated_login_uuid
        }
        return response
        

def get_bilibili_login_info(id: str):
    login_information = get_bilibili_login(id)
    if (login_information is None):
        response = {
            "code": 1,
            "message": "Login information not found"
        }
        return response, 403
    response = json.loads(login_information);
    return response

def get_bilibili_login_account_ids():
    return get_all_bilibili_login_ids()