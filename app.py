import asyncio
from flask import Flask, jsonify, request
from uploader.bilibili_uploader.extra import login_by_qrcode, login_by_qrcode_task, request_login_url
from utils.redis import add_bilibili_login, get_bilibili_login, get_celery_task
import uuid
from utils.celery import celery_init_app

import qrcode

app = Flask(__name__)
app.config.from_mapping(
    CELERY=dict(
        broker_url="redis://127.0.0.1:6379",
        result_backend="redis://127.0.0.1:6379",
        task_ignore_result=True,
    ),
)
celery_app = celery_init_app(app)

@app.route("/bilibili/get_login_url", methods=["GET"])
def bilibili_login():
    res = request_login_url()
    prev_login_task = get_celery_task()
    if (prev_login_task is not None):
        return {
            "code": 2,
            "message": "Previous login task is still running",
            "id": prev_login_task
        }

    generated_login_uuid = uuid.uuid4()
    generated_login_uuid_str = str(generated_login_uuid)
    add_bilibili_login(generated_login_uuid_str)

    login_by_qrcode_task.delay(generated_login_uuid_str, res, task_id = generated_login_uuid_str)
    
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
    return jsonify(response)

@app.route("/bilibili/check_login", methods=["POST"])
def bilibili_check_login():
    id = request.form.get("id")
    login_information = get_bilibili_login(id)
    if (login_information is None):
        response = {
            "code": 1,
            "message": "Login information not found"
        }
        return jsonify(response), 403
    response = login_information;
    return jsonify(response)