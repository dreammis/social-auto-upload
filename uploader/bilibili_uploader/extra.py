from celery import shared_task
from utils.redis import register_bilibili_login, remove_bilibili_login
from concurrent.futures import ProcessPoolExecutor
import qrcode
import asyncio

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

async def login_by_qrcode(id, value):
    with BiliBili('test') as bili:
        try:
            print("login ", id)
            login_value = await bili.login_by_qrcode(value)
            print(login_value)
            login_value_str = json.dumps(login_value)
            if (login_value['code'] == 0):
                register_bilibili_login(id, login_value_str)
            else:
                remove_bilibili_login(id)
        except Exception as e:
            remove_bilibili_login(id)
    

@shared_task()
def login_by_qrcode_task(id, value):
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(login_by_qrcode(id, value))
    return result

def request_login_url():
    with BiliBili('test') as bili:
        res = bili.get_qrcode()
        return res
        