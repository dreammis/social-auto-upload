import datetime
import json
import qrcode
from time import sleep

from xhs import XhsClient

from xhs_uploader.main import sign

# pip install qrcode
if __name__ == '__main__':
    xhs_client = XhsClient(sign=sign)
    print(datetime.datetime.now())
    qr_res = xhs_client.get_qrcode()
    qr_id = qr_res["qr_id"]
    qr_code = qr_res["code"]

    qr = qrcode.QRCode(version=1, error_correction=qrcode.ERROR_CORRECT_L,
                       box_size=50,
                       border=1)
    qr.add_data(qr_res["url"])
    qr.make()
    img = qr.make_image(fill_color="black", back_color="white")
    img.save('qrcode.png')

    while True:
        check_qrcode = xhs_client.check_qrcode(qr_id, qr_code)
        print(check_qrcode)
        sleep(1)
        if check_qrcode["code_status"] == 2:
            print(json.dumps(check_qrcode["login_info"], indent=4))
            print("当前 cookie：" + xhs_client.cookie)
            break

    print(json.dumps(xhs_client.get_self_info(), indent=4))