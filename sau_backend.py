import asyncio
from datetime import datetime, timedelta
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from queue import Queue
from flask_cors import CORS
from playwright.async_api import async_playwright
from myUtils.auth import check_cookie
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from werkzeug.utils import secure_filename
from conf import BASE_DIR, LOCAL_CHROME_PATH
from myUtils.login import (
    get_tencent_cookie,
    douyin_cookie_gen,
    get_ks_cookie,
    xiaohongshu_cookie_gen,
    baijiahao_cookie_gen,
    tiktok_cookie_gen,
    bilibili_cookie_gen
)
from myUtils.postVideo import (
    post_video_tencent,
    post_video_DouYin,
    post_video_ks,
    post_video_xhs,
    post_video_baijiahao,
    post_video_tiktok,
    post_video_bilibili
)
from uploader.douyin_uploader.main import DouYinVideo
from uploader.ks_uploader.main import KSVideo
from uploader.tencent_uploader.main import TencentVideo
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
from uploader.bilibili_uploader.main import (
    BILIBILI_PUBLISH_STRATEGY_IMMEDIATE,
    BILIBILI_PUBLISH_STRATEGY_SCHEDULED,
    BilibiliVideo,
    bilibili_setup,
    cookie_auth as bilibili_cookie_auth,
)
from uploader.tk_uploader.main import TiktokVideo
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo
from utils.base_social_media import set_init_script
from utils.runtime_config import get_runtime_config, update_runtime_config


def ensure_user_info_columns():
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_info'")
        if not cursor.fetchone():
            return
        cursor.execute("PRAGMA table_info(user_info)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "last_login_time" not in existing_columns:
            cursor.execute("ALTER TABLE user_info ADD COLUMN last_login_time DATETIME")
            conn.commit()
            print("✅ user_info 已补充 last_login_time 字段")


def parse_db_datetime(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


active_queues = {}
app = Flask(__name__)
ensure_user_info_columns()

CACHE_TIMEOUT = 24 * 60 * 60

UPLOAD_PAGE_CLASS_MAP = {
    1: XiaoHongShuVideo,
    2: TencentVideo,
    3: DouYinVideo,
    4: KSVideo,
    5: BilibiliVideo,
    6: TiktokVideo,
    7: BaiJiaHaoVideo
}

#允许所有来源跨域访问
CORS(app)

# 限制上传文件大小为160MB
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024

# 获取当前目录（假设 index.html 和 assets 在这里）
current_dir = os.path.dirname(os.path.abspath(__file__))

# 处理所有静态资源请求（未来打包用）
@app.route('/assets/<filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), filename)

# 处理 favicon.ico 静态资源（未来打包用）
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

@app.route('/vite.svg')
def vite_svg():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

# （未来打包用）
@app.route('/')
def index():  # put application's code here
    return send_from_directory(current_dir, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400
    try:
        uuid_v1 = uuid.uuid1()
        original_filename = file.filename
        file_ext = ''
        if '.' in original_filename:
            file_ext = '.' + original_filename.rsplit('.', 1)[-1]
        safe_name = secure_filename(original_filename)
        if safe_name and '.' in safe_name:
            # secure_filename 保留了文件名和扩展名（如 'test.mp4'）
            final_name = f"{uuid_v1}_{safe_name}"
        else:
            # 用 UUID 替代中文部分，手动拼接扩展名
            final_name = f"{uuid_v1}{file_ext}"
        filepath = Path(BASE_DIR / "videoFile" / final_name)
        file.save(filepath)
        return jsonify({"code":200,"msg": "File uploaded successfully", "data": final_name}), 200
    except Exception as e:
        return jsonify({"code":500,"msg": str(e),"data":None}), 500

@app.route('/getFile', methods=['GET'])
def get_file():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({"code": 400, "msg": "filename is required", "data": None}), 400
    # 防止路径穿越攻击
    if '..' in filename or filename.startswith('/'):
        return jsonify({"code": 400, "msg": "Invalid filename", "data": None}), 400
    # 拼接完整路径
    file_path = str(Path(BASE_DIR / "videoFile"))
    # 返回文件
    return send_from_directory(file_path,filename)


def sync_video_file_records(conn):
    """同步 videoFile 目录与数据库记录
    1. 将目录中存在但数据库中不存在的文件添加到数据库
    2. 删除数据库中存在但目录中不存在的记录
    """
    video_dir = Path(BASE_DIR / "videoFile")
    video_dir.mkdir(parents=True, exist_ok=True)

    cursor = conn.cursor()
    
    # 获取数据库中的所有记录
    cursor.execute("SELECT id, file_path FROM file_records WHERE file_path IS NOT NULL")
    db_records = cursor.fetchall()  # [(id, file_path), ...]
    db_paths = {row[1] for row in db_records}  # {file_path1, file_path2, ...}
    
    # 获取目录中的所有实际文件
    actual_files = set()
    for video_path in video_dir.iterdir():
        if video_path.is_file():
            actual_files.add(video_path.name)
    
    # 添加目录中存在但数据库中不存在的文件
    added_count = 0
    for file_name in actual_files:
        if file_name not in db_paths:
            file_path = video_dir / file_name
            cursor.execute(
                '''
                INSERT INTO file_records (filename, filesize, file_path)
                VALUES (?, ?, ?)
                ''',
                ("未命名", round(file_path.stat().st_size / (1024 * 1024), 2), file_name)
            )
            added_count += 1
    
    # 删除数据库中存在但目录中不存在的记录
    removed_count = 0
    for record_id, file_path in db_records:
        if file_path not in actual_files:
            cursor.execute("DELETE FROM file_records WHERE id = ?", (record_id,))
            removed_count += 1
    
    if added_count or removed_count:
        conn.commit()
        if added_count:
            print(f"✅ 已补录 {added_count} 个 videoFile 文件到数据库")
        if removed_count:
            print(f"🗑️ 已清理 {removed_count} 个不存在文件的数据库记录")


@app.route('/uploadSave', methods=['POST'])
def upload_save():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400

    # 获取表单中的自定义文件名（可选）
    custom_filename = request.form.get('filename', None)
    original_filename = file.filename
    # 获取文件扩展名（在 secure_filename 处理之前）
    file_ext = ''
    if '.' in original_filename:
        file_ext = '.' + original_filename.rsplit('.', 1)[-1]
    
    # 处理文件名
    if custom_filename:
        # 用户自定义文件名，使用 secure_filename 处理
        safe_custom = secure_filename(custom_filename)
        if safe_custom and '.' in safe_custom:
            # secure_filename 保留了文件名和扩展名
            filename = safe_custom
        else:
            # 自定义文件名包含非ASCII字符，使用 UUID
            import uuid as uuid_module
            filename = f"{uuid_module.uuid4().hex}{file_ext}"
    else:
        # 使用原始文件名
        safe_filename_result = secure_filename(original_filename)
        # secure_filename 对中文文件名的处理结果是只有扩展名（不包含点号）
        # 例如：'横的.jpg' -> 'jpg'
        # 检查是否是这种情况：结果不包含点号，且与扩展名相同（去掉点号后）
        if safe_filename_result and '.' in safe_filename_result:
            # secure_filename 保留了文件名和扩展名（如 'test.jpg'）
            filename = safe_filename_result
        else:
            # 文件名包含非ASCII字符（如中文），secure_filename 只返回了扩展名
            # 使用 UUID 作为文件名
            import uuid as uuid_module
            filename = f"{uuid_module.uuid4().hex}{file_ext}"
    
    if not filename:
        return jsonify({"code": 400, "data": None, "msg": "Invalid filename"}), 400

    try:
        # 生成 UUID v1
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")

        # 构造文件名和路径
        final_filename = f"{uuid_v1}_{filename}"
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{filename}")

        # 保存文件
        file.save(filepath)

        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO file_records (filename, filesize, file_path)
            VALUES (?, ?, ?)
                                ''', (filename, round(float(os.path.getsize(filepath)) / (1024 * 1024),2), final_filename))
            conn.commit()
            print("✅ 上传文件已记录")

        return jsonify({
            "code": 200,
            "msg": "File uploaded and saved successfully",
            "data": {
                "filename": filename,
                "filepath": final_filename
            }
        }), 200

    except Exception as e:
        print(f"Upload failed: {e}")
        return jsonify({
            "code": 500,
            "msg": f"upload failed: {e}",
            "data": None
        }), 500

@app.route('/getFiles', methods=['GET'])
def get_all_files():
    try:
        # 使用 with 自动管理数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row  # 允许通过列名访问结果
            sync_video_file_records(conn)
            cursor = conn.cursor()

            # 查询所有记录
            cursor.execute("SELECT * FROM file_records")
            rows = cursor.fetchall()

            # 将结果转为字典列表，并提取UUID
            data = []
            for row in rows:
                row_dict = dict(row)
                # 从 file_path 中提取 UUID (文件名的第一部分，下划线前)
                if row_dict.get('file_path'):
                    file_path_parts = row_dict['file_path'].split('_', 1)  # 只分割第一个下划线
                    if len(file_path_parts) > 0:
                        row_dict['uuid'] = file_path_parts[0]  # UUID 部分
                    else:
                        row_dict['uuid'] = ''
                else:
                    row_dict['uuid'] = ''
                data.append(row_dict)

            return jsonify({
                "code": 200,
                "msg": "success",
                "data": data
            }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("get file failed!"),
            "data": None
        }), 500


@app.route("/getConfig", methods=["GET"])
def get_config():
    try:
        return jsonify({
            "code": 200,
            "msg": "success",
            "data": get_runtime_config()
        }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e),
            "data": None
        }), 500


@app.route("/updateConfig", methods=["POST"])
def update_config():
    try:
        payload = request.get_json(silent=True) or {}
        data = update_runtime_config(payload)
        return jsonify({
            "code": 200,
            "msg": "配置更新成功",
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str(e),
            "data": None
        }), 500


@app.route("/getAccounts", methods=['GET'])
def getAccounts():
    """快速获取所有账号信息，不进行cookie验证"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM user_info''')
            rows = cursor.fetchall()
            rows_list = [list(row) for row in rows]

            print("\n📋 当前数据表内容（快速获取）：")
            for row in rows:
                print(row)

            return jsonify(
                {
                    "code": 200,
                    "msg": None,
                    "data": rows_list
                }), 200
    except Exception as e:
        print(f"获取账号列表时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"获取账号列表失败: {str(e)}",
            "data": None
        }), 500


@app.route("/getValidAccounts",methods=['GET'])
async def getValidAccounts():
    rows_list = await refresh_account_statuses()
    return jsonify(
                    {
                        "code": 200,
                        "msg": None,
                        "data": rows_list
                    }),200


async def refresh_account_statuses(force_refresh=False):
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM user_info''')
        rows = cursor.fetchall()
        rows_list = [list(row) for row in rows]
        print("\n📋 当前数据表内容：")
        for row in rows:
            print(row)
        for row in rows_list:
            last_login_time = parse_db_datetime(row[5] if len(row) > 5 else None)

            if not force_refresh and last_login_time:
                if (datetime.now() - last_login_time).total_seconds() < CACHE_TIMEOUT:
                    continue

            flag = await check_cookie(row[1],row[2])
            row[4] = 1 if flag else 0
            cursor.execute('''
            UPDATE user_info
            SET status = ?, last_login_time = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (row[4], row[0]))
        conn.commit()
        print("✅ 用户状态已更新")
        for row in rows:
            print(row)
        return rows_list


def get_seconds_until_next_midnight():
    now = datetime.now()
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, (next_midnight - now).total_seconds())


def nightly_account_status_checker():
    while True:
        sleep_seconds = get_seconds_until_next_midnight()
        print(f"⏰ 下次账号状态自动检查将在 {int(sleep_seconds)} 秒后执行")
        time.sleep(sleep_seconds)
        try:
            asyncio.run(refresh_account_statuses(force_refresh=True))
            print("✅ 半夜账号状态自动检查完成")
        except Exception as e:
            print(f"❌ 半夜账号状态自动检查失败: {str(e)}")

@app.route('/deleteFile', methods=['GET'])
def delete_file():
    file_id = request.args.get('id')

    if not file_id or not file_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing file ID",
            "data": None
        }), 400

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found",
                    "data": None
                }), 404

            record = dict(record)

            # 获取文件路径并删除实际文件
            file_path = Path(BASE_DIR / "videoFile" / record['file_path'])
            if file_path.exists():
                try:
                    file_path.unlink()  # 删除文件
                    print(f"✅ 实际文件已删除: {file_path}")
                except Exception as e:
                    print(f"⚠️ 删除实际文件失败: {e}")
                    # 即使删除文件失败，也要继续删除数据库记录，避免数据不一致
            else:
                print(f"⚠️ 实际文件不存在: {file_path}")

            # 删除数据库记录
            cursor.execute("DELETE FROM file_records WHERE id = ?", (file_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "File deleted successfully",
            "data": {
                "id": record['id'],
                "filename": record['filename']
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500

@app.route('/deleteAccount', methods=['GET'])
def delete_account():
    account_id = request.args.get('id')

    if not account_id or not account_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing account ID",
            "data": None
        }), 400

    account_id = int(account_id)

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM user_info WHERE id = ?", (account_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found",
                    "data": None
                }), 404

            record = dict(record)

            # 删除关联的cookie文件
            if record.get('filePath'):
                cookie_file_path = Path(BASE_DIR / "cookiesFile" / record['filePath'])
                if cookie_file_path.exists():
                    try:
                        cookie_file_path.unlink()
                        print(f"✅ Cookie文件已删除: {cookie_file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除Cookie文件失败: {e}")

            # 删除数据库记录
            cursor.execute("DELETE FROM user_info WHERE id = ?", (account_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account deleted successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"delete failed: {str(e)}",
            "data": None
        }), 500


# SSE 登录接口
@app.route('/login')
def login():
    # 1 小红书 2 视频号 3 抖音 4 快手
    type = request.args.get('type')
    # 账号名
    user_name = request.args.get('id')
    account_id = request.args.get('accountId')
    existing_file_path = None

    if account_id:
        try:
            account_id = int(account_id)
        except (TypeError, ValueError):
            return jsonify({
                "code": 400,
                "msg": "账号ID格式错误",
                "data": None
            }), 400

        try:
            with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, type, filePath, userName FROM user_info WHERE id = ?',
                    (account_id,)
                )
                account = cursor.fetchone()
        except Exception as e:
            return jsonify({
                "code": 500,
                "msg": f"查询账号失败: {str(e)}",
                "data": None
            }), 500

        if not account:
            return jsonify({
                "code": 404,
                "msg": "账号不存在",
                "data": None
            }), 404

        type = str(account['type'])
        user_name = account['userName']
        existing_file_path = account['filePath']

    # 模拟一个用于异步通信的队列
    status_queue = Queue()
    queue_key = str(account_id) if account_id else user_name
    active_queues[queue_key] = status_queue

    def on_close():
        print(f"清理队列: {queue_key}")
        del active_queues[queue_key]
    # 启动异步任务线程
    thread = threading.Thread(
        target=run_async_function,
        args=(type, user_name, status_queue, account_id, existing_file_path),
        daemon=True
    )
    thread.start()
    response = Response(sse_stream(status_queue,), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 关键：禁用 Nginx 缓冲
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/postVideo', methods=['POST'])
def postVideo():
    # 获取JSON数据
    data = request.get_json()

    if not data:
        return jsonify({"code": 400, "msg": "请求数据不能为空", "data": None}), 400

    # 从JSON数据中提取fileList和accountList
    file_list = data.get('fileList', [])
    account_list = data.get('accountList', [])
    type = data.get('type')
    title = data.get('title')
    tags = data.get('tags')
    category = data.get('category')
    enableTimer = data.get('enableTimer')
    if category == 0:
        category = None
    productLink = data.get('productLink', '')
    productTitle = data.get('productTitle', '')
    desc = data.get('desc', '')
    thumbnail_portrait = data.get('thumbnailPortrait', '')
    is_draft = data.get('isDraft', False)  # 新增参数：是否保存为草稿
    tencent_declare_original = data.get('tencentDeclareOriginal', data.get('declareOriginal', False))
    tencent_declaration = data.get('tencentDeclaration')

    declaration_info = data.get('declaration_info', None)# 新增参数：添加声明

    videos_per_day = data.get('videosPerDay')
    daily_times = data.get('dailyTimes')
    start_days = data.get('startDays')

    # 快手特有参数
    kuaishou_declaration = data.get('kuaishouDeclaration', '内容为AI生成')
    xiaohongshu_declaration = data.get('xiaohongshuDeclaration', '')
    allow_duet = data.get('allowDuet', True)
    allow_download = data.get('allowDownload', True)
    show_in_city = data.get('showInCity', True)

    # B站特有参数
    bilibili_tid = data.get('bilibiliTid', 218)  # B站分区ID，默认218（动物圈）
    bilibili_is_original = data.get('declareOriginal', False)  # B站原创声明：默认不声明
    bilibili_ai_declaration = data.get('bilibiliAiDeclaration', False)  # B站创作声明：含AI生成内容
    bilibili_no_reprint = data.get('noReprint', 1 if bilibili_is_original else 0)  # 禁止转载

    # 合集参数
    collection = data.get('collection', None)  # 合集名称

    # 参数校验
    if not file_list:
        return jsonify({"code": 400, "msg": "文件列表不能为空", "data": None}), 400
    if not account_list:
        return jsonify({"code": 400, "msg": "账号列表不能为空", "data": None}), 400
    if not type:
        return jsonify({"code": 400, "msg": "平台类型不能为空", "data": None}), 400
    if not title:
        if type == 3 and desc:
            pass
        else:
            return jsonify({"code": 400, "msg": "标题不能为空", "data": None}), 400

    # 打印获取到的数据（仅作为示例）
    print("File List:", file_list)
    print("Account List:", account_list)

    thumbnail_path = data.get('thumbnail', '') or thumbnail_portrait

    # 封面参数（B站使用单封面）- 复用 thumbnail 字段
    bilibili_cover = thumbnail_path  # B站封面路径

    try:
        match type:
            case 1:
                declare_original = data.get('declareOriginal', False)
                xhs_category = category if category else (1 if declare_original else None)
                xhs_declaration_info = {"declaration_type": xiaohongshu_declaration} if xiaohongshu_declaration else None
                print(f"[小红书] declareOriginal={declare_original}, xhs_category={xhs_category}, xiaohongshu_declaration={xiaohongshu_declaration}, declaration_info={xhs_declaration_info}")
                post_video_xhs(title, file_list, tags, account_list, xhs_category, enableTimer, videos_per_day, daily_times,
                                   start_days, desc, thumbnail_path, collection=collection, declaration_info=xhs_declaration_info)
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days, is_draft, thumbnail_path, desc, collection=collection,
                                   declare_original=tencent_declare_original, declaration=tencent_declaration)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, thumbnail_path, thumbnail_portrait, productLink, productTitle, declaration_info, desc,
                          collection=collection)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, desc, thumbnail_path, kuaishou_declaration, allow_duet, allow_download, show_in_city,
                          collection=collection)
            case 5:
                post_video_bilibili(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, tid=bilibili_tid, desc=desc,
                          copyright_type=1 if bilibili_is_original else 2,
                          cover_path=bilibili_cover, collection=collection,
                          ai_declaration=bilibili_ai_declaration)
            case 6:
                post_video_tiktok(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
            case 7:
                post_video_baijiahao(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
            case _:
                return jsonify({"code": 400, "msg": f"不支持的平台类型: {type}", "data": None}), 400

        # 返回响应给客户端
        return jsonify(
            {
                "code": 200,
                "msg": "发布任务已提交",
                "data": None
            }), 200
    except Exception as e:
        print(f"发布视频时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"发布失败: {str(e)}",
            "data": None
        }), 500


@app.route('/updateUserinfo', methods=['POST'])
def updateUserinfo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取 type 和 userName
    user_id = data.get('id')
    type = data.get('type')
    userName = data.get('userName')
    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 更新数据库记录
            cursor.execute('''
                           UPDATE user_info
                           SET type     = ?,
                               userName = ?
                           WHERE id = ?;
                           ''', (type, userName, user_id))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account update successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("update failed!"),
            "data": None
        }), 500

@app.route('/postVideoBatch', methods=['POST'])
def postVideoBatch():
    data_list = request.get_json()

    if not isinstance(data_list, list):
        return jsonify({"code": 400, "msg": "Expected a JSON array", "data": None}), 400
    for data in data_list:
        # 从JSON数据中提取fileList和accountList
        file_list = data.get('fileList', [])
        account_list = data.get('accountList', [])
        type = data.get('type')
        title = data.get('title')
        tags = data.get('tags')
        category = data.get('category')
        enableTimer = data.get('enableTimer')
        if category == 0:
            category = None
        productLink = data.get('productLink', '')
        productTitle = data.get('productTitle', '')
        desc = data.get('desc', '')
        is_draft = data.get('isDraft', False)
        tencent_declare_original = data.get('tencentDeclareOriginal', data.get('declareOriginal', False))
        tencent_declaration = data.get('tencentDeclaration')
        declaration_info = data.get('declaration_info', None)# 新增参数：添加声明

        videos_per_day = data.get('videosPerDay')
        daily_times = data.get('dailyTimes')
        start_days = data.get('startDays')
        # 打印获取到的数据（仅作为示例）
        print("File List:", file_list)
        print("Account List:", account_list)

        # 平台特有参数
        thumbnail_portrait = data.get('thumbnailPortrait', '')
        thumbnail_path = data.get('thumbnail', '') or thumbnail_portrait
        bilibili_tid = data.get('bilibiliTid', 218)
        kuaishou_declaration = data.get('kuaishouDeclaration', None)
        xiaohongshu_declaration = data.get('xiaohongshuDeclaration', '')
        allow_duet = data.get('allowDuet', True)
        allow_download = data.get('allowDownload', True)
        show_in_city = data.get('showInCity', True)

        # B站特有参数（批量发布）
        bilibili_is_original = data.get('declareOriginal', False)  # B站原创声明：默认不声明
        bilibili_ai_declaration = data.get('bilibiliAiDeclaration', False)  # B站创作声明：含AI生成内容
        bilibili_no_reprint = data.get('noReprint', 1 if bilibili_is_original else 0)  # 禁止转载
        bilibili_cover = thumbnail_path  # B站封面

        collection = data.get('collection', None)  # 合集名称

        match type:
            case 1:
                declare_original = data.get('declareOriginal', False)
                xhs_category = category if category else (1 if declare_original else None)
                xhs_declaration_info = {"declaration_type": xiaohongshu_declaration} if xiaohongshu_declaration else None
                print(f"[小红书] declareOriginal={declare_original}, xhs_category={xhs_category}, xiaohongshu_declaration={xiaohongshu_declaration}, declaration_info={xhs_declaration_info}")
                post_video_xhs(title, file_list, tags, account_list, xhs_category, enableTimer, videos_per_day, daily_times,
                               start_days, desc, thumbnail_path, collection=collection, declaration_info=xhs_declaration_info)
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days, is_draft, thumbnail_path, desc, collection=collection,
                                   declare_original=tencent_declare_original, declaration=tencent_declaration)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, thumbnail_path, thumbnail_portrait, productLink, productTitle, declaration_info, desc,
                          collection=collection)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, desc, thumbnail_path, kuaishou_declaration, allow_duet, allow_download, show_in_city,
                          collection=collection)
            case 5:
                post_video_bilibili(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days, tid=bilibili_tid, desc=desc,
                          copyright_type=1 if bilibili_is_original else 2,
                          cover_path=bilibili_cover, collection=collection,
                          ai_declaration=bilibili_ai_declaration)
            case 6:
                post_video_tiktok(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
            case 7:
                post_video_baijiahao(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
    # 返回响应给客户端
    return jsonify(
        {
            "code": 200,
            "msg": None,
            "data": None
        }), 200

# ==================== 统一发布（一键发布）API ====================
@app.route('/batchUnifiedPublish', methods=['POST'])
def batchUnifiedPublish():
    """
    统一发布API - 一次填写信息，批量发布到多平台
    
    请求格式:
    {
        files: [视频路径列表],
        coverPath: 封面路径,
        title: 标题,
        desc: 描述,
        
        platforms: [平台ID列表],  // 如 [1,3,5] 表示小红书、抖音、B站
        accounts: {
            1: [账号ID],
            3: [账号ID],
            5: [账号ID]
        },
        
        config: {  // 各平台差异化配置（每个平台独立标签）
            xiaohongshu: { tags: [], declaration, isOriginal },
            channels: { tags: [], isDraft, isOriginal },
            douyin: { tags: [], collection, productTitle, productLink, declaration_type },
            kuaishou: { tags: [], declaration },
            bilibili: { tags: [], tid, aiDeclaration, isOriginal },
            tiktok: { tags: [] },
            baijiahao: { tags: [] }
        }
    }
    
    响应格式:
    {
        code: 200,
        msg: None,
        data: {
            results: [
                { platform: "B站", status: "success", message: "发布成功" },
                { platform: "抖音", status: "error", message: "错误信息" }
            ]
        }
    }
    """
    try:
        data = request.get_json()

        # 提取公共参数
        files = data.get('files', [])
        title = data.get('title', '')
        desc = data.get('desc', '')

        # 提取2种尺寸封面
        covers = data.get('covers', {})
        cover_portrait = covers.get('portrait')   # 竖版 (3:4)
        cover_square = covers.get('square')        # 方形 (4:3)

        # 提取平台配置（标签在各平台的config中）
        platforms = data.get('platforms', [])  # 平台ID列表
        accounts = data.get('accounts', {})   # 各平台账号
        config = data.get('config', {})       # 各平台差异化配置

        if not files:
            return jsonify({
                "code": 400,
                "msg": "请上传视频文件",
                "data": None
            }), 400
            
        if not title:
            return jsonify({
                "code": 400,
                "msg": "请输入标题",
                "data": None
            }), 400
            
        if not platforms:
            return jsonify({
                "code": 400,
                "msg": "请选择至少一个平台",
                "data": None
            }), 400
        
        results = []  # 存储每个平台的发布结果
        
        # 按顺序发布到各平台
        for platform_id in platforms:
            platform_name = get_platform_name(platform_id)

            try:
                print(f"\n{'='*50}")
                print(f"[统一发布] 开始发布到: {platform_name} (平台ID: {platform_id})")
                print(f"{'='*50}\n")

                # 获取该平台的账号
                platform_accounts = accounts.get(str(platform_id), accounts.get(platform_id, []))

                if not platform_accounts:
                    raise ValueError("未选择该平台的账号")

                # 将账号ID转换为账号文件路径
                account_file_paths = []
                for account_id in platform_accounts:
                    file_path = get_account_file_path(account_id)
                    if file_path:
                        account_file_paths.append(file_path)
                    else:
                        print(f"警告: 无法找到账号ID {account_id} 的文件路径")

                if not account_file_paths:
                    raise ValueError("无法获取该平台的账号文件路径")

                # 根据平台获取对应的封面
                coverPath = get_cover_for_platform(
                    platform_id,
                    cover_portrait=cover_portrait,
                    cover_square=cover_square
                )

                # 根据平台调用对应的发布函数（标签从config中读取）
                publish_to_platform(
                    platform_id=platform_id,
                    title=title,
                    files=files,
                    coverPath=coverPath,
                    tags=[],  # 已废弃，标签从config中读取
                    accounts=account_file_paths,
                    desc=desc,
                    config=config
                )
                
                # 发布成功
                results.append({
                    "platform": platform_name,
                    "status": "success",
                    "message": "发布成功"
                })
                print(f"[统一发布] ✅ {platform_name} 发布成功\n")
                
            except Exception as e:
                error_msg = str(e)
                print(f"[统一发布] ❌ {platform_name} 发布失败: {error_msg}\n")
                
                # 获取最新截图路径
                screenshot_url = get_latest_screenshot_for_platform(platform_name)
                
                results.append({
                    "platform": platform_name,
                    "status": "error",
                    "message": error_msg,
                    "screenshot": screenshot_url
                })
        
        # 统计结果
        success_count = sum(1 for r in results if r['status'] == 'success')
        fail_count = sum(1 for r in results if r['status'] == 'error')
        
        return jsonify({
            "code": 200,
            "msg": f"发布完成：{success_count} 成功，{fail_count} 失败",
            "data": {
                "results": results,
                "summary": {
                    "total": len(results),
                    "success": success_count,
                    "failed": fail_count
                }
            }
        }), 200
        
    except Exception as e:
        print(f"[统一发布] 致命错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "code": 500,
            "msg": f"统一发布出错: {str(e)}",
            "data": None
        }), 500


def get_account_file_path(account_id):
    """根据账号ID获取账号文件路径"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT filePath FROM user_info WHERE id = ?', (account_id,))
            row = cursor.fetchone()
            if row:
                return row['filePath']
            return None
    except Exception as e:
        print(f"获取账号文件路径失败: {str(e)}")
        return None


def get_platform_name(platform_id):
    """获取平台名称"""
    platform_map = {
        1: "小红书",
        2: "视频号",
        3: "抖音",
        4: "快手",
        5: "B站",
        6: "TikTok",
        7: "百家号"
    }
    return platform_map.get(platform_id, f"未知平台({platform_id})")


def get_cover_for_platform(platform_id, cover_portrait=None, cover_square=None):
    """
    根据平台ID获取对应的封面路径

    封面分配规则:
    - 小红书 (1): 竖版 (3:4)
    - 视频号 (2): 竖版 (3:4)
    - 抖音 (3): 竖版 (3:4) + 方形 (4:3) [双封面]
    - 快手 (4): 竖版 (3:4)
    - B站 (5): 方形 (4:3)

    注意：
    - 抖音的横封面是4:3比例，使用cover_square
    - B站目前只需要方形封面（4:3）
    """
    cover_mapping = {
        # 小红书 → 竖版
        1: cover_portrait,
        # 视频号 → 竖版
        2: cover_portrait,
        # 抖音 → 竖版（主封面）
        3: cover_portrait,
        # 快手 → 竖版
        4: cover_portrait,
        # B站 → 方形
        5: cover_square,
    }

    main_cover = cover_mapping.get(platform_id)

    # 对于需要双封面的平台（抖音），返回字典
    if platform_id == 3:  # 抖音
        return {
            'main': main_cover or cover_portrait,
            'portrait': cover_portrait,
            'square': cover_square
        }

    return main_cover


def publish_to_platform(platform_id, title, files, coverPath, tags, accounts, desc, config):
    """
    根据平台ID发布视频（核心分发逻辑）

    参数:
        platform_id: 平台ID (1-7)
        title: 标题
        files: 视频文件路径列表
        coverPath: 封面路径
        tags: 标签列表
        accounts: 账号ID列表
        desc: 描述/简介
        config: 差异化配置字典
    """
    # 提取公共设置
    common_config = config.get('common', {})
    collection = common_config.get('collection', '')  # 合集

    # 提取各平台特有配置（包括独立标签）
    douyin_config = config.get('douyin', {})
    bilibili_config = config.get('bilibili', {})
    channels_config = config.get('channels', {})
    xiaohongshu_config = config.get('xiaohongshu', {})
    kuaishou_config = config.get('kuaishou', {})
    tiktok_config = config.get('tiktok', {})
    baijiahao_config = config.get('baijiahao', {})

    match platform_id:
        case 1:  # 小红书
            xhs_tags = xiaohongshu_config.get('tags', [])  # 小红书独立标签
            xhs_declaration = xiaohongshu_config.get('declaration', '')
            xhs_is_original = xiaohongshu_config.get('isOriginal', False)
            xhs_category = 1 if xhs_is_original else None
            declaration_info = {"declaration_type": xhs_declaration} if xhs_declaration else None

            post_video_xhs(
                title=title,
                files=files,
                tags=xhs_tags,  # 使用小红书独立标签
                account_file=accounts,
                category=xhs_category,
                enableTimer=False,
                videos_per_day=1,
                daily_times=[10],
                start_days=0,
                desc=desc,
                thumbnail_path=coverPath,
                collection=collection,
                declaration_info=declaration_info
            )

        case 2:  # 视频号
            channels_tags = channels_config.get('tags', [])  # 视频号独立标签
            is_draft = channels_config.get('isDraft', False)
            is_original = channels_config.get('isOriginal', False)
            declaration = channels_config.get('declaration')

            post_video_tencent(
                title=title,
                files=files,
                tags=channels_tags,  # 使用视频号独立标签
                account_file=accounts,
                category=None,
                enableTimer=False,
                videos_per_day=1,
                daily_times=[10],
                start_days=0,
                is_draft=is_draft,
                thumbnail_path=coverPath,
                desc=desc,
                collection=collection,
                declare_original=is_original,
                declaration=declaration
            )

        case 3:  # 抖音
            douyin_tags = douyin_config.get('tags', [])  # 抖音独立标签
            declaration_type = douyin_config.get('declaration_type', '')
            declaration_info = {"declaration_type": declaration_type} if declaration_type else None

            # 处理抖音双封面（竖版3:4 + 方形4:3）
            if isinstance(coverPath, dict):
                douyin_portrait = coverPath.get('portrait')
                douyin_square = coverPath.get('square')
            else:
                douyin_portrait = coverPath
                douyin_square = coverPath

            post_video_DouYin(
                title=title,
                files=files,
                tags=douyin_tags,  # 使用抖音独立标签
                account_file=accounts,
                category=None,
                enableTimer=False,
                videos_per_day=1,
                daily_times=[10],
                start_days=0,
                thumbnail_landscape_path=douyin_square,
                thumbnail_portrait_path=douyin_portrait,
                productLink=douyin_config.get('productLink', ''),
                productTitle=douyin_config.get('productTitle', ''),
                declaration_info=declaration_info,
                desc=desc,
                collection=collection
            )

        case 4:  # 快手
            kuaishou_tags = kuaishou_config.get('tags', [])  # 快手独立标签
            kuaishou_declaration = kuaishou_config.get('declaration', '内容为AI生成')

            post_video_ks(
                title=title,
                files=files,
                tags=kuaishou_tags,  # 使用快手独立标签
                account_file=accounts,
                category=None,
                enableTimer=False,
                videos_per_day=1,
                daily_times=[10],
                start_days=0,
                desc=desc,
                thumbnail_path=coverPath,
                kuaishou_declaration=kuaishou_declaration,
                allow_duet=True,
                allow_download=True,
                show_in_city=True,
                collection=collection
            )
            
        case 5:  # B站
            bilibili_tags = bilibili_config.get('tags', [])  # B站独立标签
            bilibili_tid = bilibili_config.get('tid', 218)
            bilibili_ai_decl = bilibili_config.get('aiDeclaration', False)
            bilibili_orig = bilibili_config.get('isOriginal', False)

            # 处理B站封面（只需要方形4:3）
            if isinstance(coverPath, dict):
                bilibili_cover = coverPath.get('square')
            else:
                bilibili_cover = coverPath

            post_video_bilibili(
                title=title,
                files=files,
                tags=bilibili_tags,  # 使用B站独立标签
                account_file=accounts,
                category=None,
                enableTimer=False,
                videos_per_day=1,
                daily_times=[10],
                start_days=0,
                tid=bilibili_tid,
                desc=desc,
                copyright_type=1 if bilibili_orig else 2,
                cover_path=bilibili_cover,
                collection=collection,
                ai_declaration=bilibili_ai_decl
            )
            
        case 6:  # TikTok
            tiktok_tags = tiktok_config.get('tags', [])  # TikTok独立标签
            
            post_video_tiktok(
                title=title,
                files=files,
                tags=tiktok_tags,  # 使用TikTok独立标签
                account_file=accounts,
                category=None,
                enableTimer=False,
                videos_per_day=1,
                daily_times=[10],
                start_days=0
            )
            
        case 7:  # 百家号
            baijiahao_tags = baijiahao_config.get('tags', [])  # 百家号独立标签
            
            post_video_baijiahao(
                title=title,
                files=files,
                tags=baijiahao_tags,  # 使用百家号独立标签
                account_file=accounts,
                category=None,
                enableTimer=False,
                videos_per_day=1,
                daily_times=[10],
                start_days=0
            )
            
        case _:
            raise ValueError(f"不支持的平台ID: {platform_id}")

# Cookie文件上传API
@app.route('/uploadCookie', methods=['POST'])
def upload_cookie():
    try:
        if 'file' not in request.files:
            return jsonify({
                "code": 400,
                "msg": "没有找到Cookie文件",
                "data": None
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "code": 400,
                "msg": "Cookie文件名不能为空",
                "data": None
            }), 400

        if not file.filename.endswith('.json'):
            return jsonify({
                "code": 400,
                "msg": "Cookie文件必须是JSON格式",
                "data": None
            }), 400

        # 获取账号信息
        account_id = request.form.get('id')
        platform = request.form.get('platform')

        if not account_id or not platform:
            return jsonify({
                "code": 400,
                "msg": "缺少账号ID或平台信息",
                "data": None
            }), 400

        # 从数据库获取账号的文件路径
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT filePath FROM user_info WHERE id = ?', (account_id,))
            result = cursor.fetchone()

        if not result:
            return jsonify({
                "code": 500,
                "msg": "账号不存在",
                "data": None
            }), 404

        # 保存上传的Cookie文件到对应路径
        cookie_file_path = Path(BASE_DIR / "cookiesFile" / result['filePath'])
        cookie_file_path.parent.mkdir(parents=True, exist_ok=True)

        file.save(str(cookie_file_path))

        # 更新数据库中的账号信息（可选，比如更新更新时间）
        # 这里可以根据需要添加额外的处理逻辑

        return jsonify({
            "code": 200,
            "msg": "Cookie文件上传成功",
            "data": None
        }), 200

    except Exception as e:
        print(f"上传Cookie文件时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"上传Cookie文件失败: {str(e)}",
            "data": None
        }), 500


# Cookie文件下载API
@app.route('/downloadCookie', methods=['GET'])
def download_cookie():
    try:
        file_path = request.args.get('filePath')
        if not file_path:
            return jsonify({
                "code": 500,
                "msg": "缺少文件路径参数",
                "data": None
            }), 400

        # 验证文件路径的安全性，防止路径遍历攻击
        cookie_file_path = Path(BASE_DIR / "cookiesFile" / file_path).resolve()
        base_path = Path(BASE_DIR / "cookiesFile").resolve()

        if not cookie_file_path.is_relative_to(base_path):
            return jsonify({
                "code": 500,
                "msg": "非法文件路径",
                "data": None
            }), 400

        if not cookie_file_path.exists():
            return jsonify({
                "code": 500,
                "msg": "Cookie文件不存在",
                "data": None
            }), 404

        # 返回文件
        return send_from_directory(
            directory=str(cookie_file_path.parent),
            path=cookie_file_path.name,
            as_attachment=True
        )

    except Exception as e:
        print(f"下载Cookie文件时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"下载Cookie文件失败: {str(e)}",
            "data": None
        }), 500


@app.route('/openUploadPage', methods=['POST'])
def open_upload_page():
    data = request.get_json() or {}
    account_id = data.get('id')

    if not account_id:
        return jsonify({
            "code": 400,
            "msg": "缺少账号ID",
            "data": None
        }), 400

    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return jsonify({
            "code": 400,
            "msg": "账号ID格式错误",
            "data": None
        }), 400

    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT id, type, filePath, userName FROM user_info WHERE id = ?', (account_id,))
            account = cursor.fetchone()

        if not account:
            return jsonify({
                "code": 404,
                "msg": "账号不存在",
                "data": None
            }), 404

        account_type = int(account['type'])
        uploader_cls = UPLOAD_PAGE_CLASS_MAP.get(account_type)
        if not uploader_cls:
            return jsonify({
                "code": 400,
                "msg": "当前账号平台不支持打开上传页",
                "data": None
            }), 400

        cookie_file_path = Path(BASE_DIR / "cookiesFile" / account['filePath']).resolve()
        cookie_base_path = Path(BASE_DIR / "cookiesFile").resolve()
        if not cookie_file_path.is_relative_to(cookie_base_path):
            return jsonify({
                "code": 400,
                "msg": "Cookie文件路径非法",
                "data": None
            }), 400

        if not cookie_file_path.exists():
            return jsonify({
                "code": 404,
                "msg": "Cookie文件不存在，请先重新登录账号",
                "data": None
            }), 404

        actual_cookie_path = str(cookie_file_path)

        thread = threading.Thread(
            target=run_open_upload_page,
            args=(actual_cookie_path, uploader_cls.upload_page, account['userName']),
            daemon=True
        )
        thread.start()

        return jsonify({
            "code": 200,
            "msg": "上传页已打开",
            "data": {
                "id": account_id,
                "uploadPage": uploader_cls.upload_page
            }
        }), 200
    except Exception as e:
        print(f"打开上传页失败: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"打开上传页失败: {str(e)}",
            "data": None
        }), 500


# 包装函数：在线程中运行异步函数
def run_async_function(type, id, status_queue, account_id=None, existing_file_path=None):
    match type:
        case '1':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(xiaohongshu_cookie_gen(id, status_queue, account_id, existing_file_path))
            loop.close()
        case '2':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_tencent_cookie(id, status_queue, account_id, existing_file_path))
            loop.close()
        case '3':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(douyin_cookie_gen(id, status_queue, account_id, existing_file_path))
            loop.close()
        case '4':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_ks_cookie(id, status_queue, account_id, existing_file_path))
            loop.close()
        case '5':
            # B站登录（使用biliup工具）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bilibili_cookie_gen(id, status_queue, account_id, existing_file_path))
            loop.close()
        case '6':
            # TikTok登录（复用抖音登录逻辑）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(tiktok_cookie_gen(id, status_queue, account_id, existing_file_path))
            loop.close()
        case '7':
            # 百家号登录（复用抖音登录逻辑）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(baijiahao_cookie_gen(id, status_queue, account_id, existing_file_path))
            loop.close()


def run_open_upload_page(account_file, upload_page, account_name):
    try:
        asyncio.run(open_upload_page_with_cookie(account_file, upload_page, account_name))
    except Exception as e:
        print(f"打开上传页线程执行失败: {account_name}, {str(e)}")


async def open_upload_page_with_cookie(account_file, upload_page, account_name):
    print(f"正在打开上传页: {account_name} -> {upload_page}")
    async with async_playwright() as playwright:
        launch_options = {
            "headless": False
        }
        if LOCAL_CHROME_PATH:
            launch_options["executable_path"] = LOCAL_CHROME_PATH

        browser = await playwright.chromium.launch(**launch_options)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto(upload_page)

        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
        except Exception:
            pass

        try:
            while not page.is_closed():
                await asyncio.sleep(1)
        finally:
            try:
                await context.storage_state(path=account_file)
            except Exception as e:
                print(f"保存Cookie失败: {account_name}, {str(e)}")
            try:
                await context.close()
            except Exception:
                pass
            try:
                await browser.close()
            except Exception:
                pass

# SSE 流生成器函数
def sse_stream(status_queue):
    while True:
        if not status_queue.empty():
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
        else:
            # 避免 CPU 占满
            time.sleep(0.1)

# 验证码提交API
@app.route('/submitVerification', methods=['POST'])
def submit_verification():
    data = request.get_json()
    code = data.get('code')
    if not code:
        return jsonify({
            "code": 400,
            "msg": "验证码不能为空",
            "data": None
        }), 400
    
    try:
        from myUtils.login import submit_verification_code
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(submit_verification_code(code))
        loop.close()
        
        if success:
            return jsonify({
                "code": 200,
                "msg": "验证码已提交",
                "data": None
            }), 200
        else:
            return jsonify({
                "code": 500,
                "msg": "当前没有待验证的登录",
                "data": None
            }), 500
    except Exception as e:
        print(f"提交验证码时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"提交验证码失败: {str(e)}",
            "data": None
        }), 500


# ==================== 截图管理接口 ====================

import os
from pathlib import Path

SCREENSHOTS_DIR = Path("screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def get_latest_screenshot_for_platform(platform_name):
    """
    获取指定平台的最新截图路径
    
    Args:
        platform_name: 平台名称（如 'B站', '抖音', '小红书'）
        
    Returns:
        截图URL路径（如 '/screenshots/view/bilibili/20260618_123456_account/001_ERROR.png'）
        如果没有截图则返回 None
    """
    # 平台名称映射到目录名
    platform_map = {
        'B站': 'bilibili',
        '抖音': 'douyin',
        '小红书': 'xiaohongshu',
        '快手': 'kuaishou',
        '视频号': 'tencent',
        'TikTok': 'tiktok',
        '百家号': 'baijiahao'
    }
    
    platform_dir_name = platform_map.get(platform_name, platform_name.lower())
    platform_dir = SCREENSHOTS_DIR / platform_dir_name
    
    if not platform_dir.exists():
        return None
    
    # 获取最新的session目录
    session_dirs = sorted(
        platform_dir.iterdir(),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not session_dirs:
        return None
    
    latest_session = session_dirs[0]
    
    # 获取该session中包含ERROR的截图（优先）
    error_screenshots = sorted(latest_session.glob("*ERROR*.png"), reverse=True)
    if error_screenshots:
        screenshot = error_screenshots[0]
        return f"/screenshots/view/{platform_dir_name}/{latest_session.name}/{screenshot.name}"
    
    # 如果没有ERROR截图，获取最新的截图
    all_screenshots = sorted(latest_session.glob("*.png"), reverse=True)
    if all_screenshots:
        screenshot = all_screenshots[0]
        return f"/screenshots/view/{platform_dir_name}/{latest_session.name}/{screenshot.name}"
    
    return None


@app.route('/screenshots/list', methods=['GET'])
def list_screenshots():
    """获取截图列表

    Query params:
        platform: 平台名称（可选，如 'douyin', 'xiaohongshu'）
        limit: 返回数量限制（默认20）
    """
    platform = request.args.get('platform')
    limit = int(request.args.get('limit', 20))

    screenshots = []

    try:
        if platform:
            # 指定平台的截图
            platform_dir = SCREENSHOTS_DIR / platform
            if platform_dir.exists():
                for session_dir in sorted(platform_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
                    for screenshot in sorted(session_dir.glob("*.png")):
                        screenshots.append({
                            "path": str(screenshot),
                            "platform": platform,
                            "session": session_dir.name,
                            "filename": screenshot.name,
                            "mtime": screenshot.stat().st_mtime
                        })
        else:
            # 所有平台的截图
            for platform_dir in SCREENSHOTS_DIR.iterdir():
                if platform_dir.is_dir():
                    for session_dir in sorted(platform_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
                        for screenshot in sorted(session_dir.glob("*.png")):
                            screenshots.append({
                                "path": str(screenshot),
                                "platform": platform_dir.name,
                                "session": session_dir.name,
                                "filename": screenshot.name,
                                "mtime": screenshot.stat().st_mtime
                            })

        # 按时间排序
        screenshots.sort(key=lambda x: x['mtime'], reverse=True)
        screenshots = screenshots[:limit]

        return jsonify({
            "code": 200,
            "msg": "获取截图列表成功",
            "data": screenshots
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"获取截图列表失败: {str(e)}",
            "data": []
        }), 500


@app.route('/screenshots/view/<platform>/<session>/<filename>', methods=['GET'])
def view_screenshot(platform, session, filename):
    """查看单个截图

    Args:
        platform: 平台名称
        session: 会话目录名
        filename: 截图文件名
    """
    try:
        screenshot_path = SCREENSHOTS_DIR / platform / session / filename

        if not screenshot_path.exists():
            return jsonify({
                "code": 404,
                "msg": "截图文件不存在",
                "data": None
            }), 404

        return send_from_directory(
            str(SCREENSHOTS_DIR / platform / session),
            filename,
            mimetype='image/png'
        )

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"查看截图失败: {str(e)}",
            "data": None
        }), 500


@app.route('/screenshots/latest', methods=['GET'])
def get_latest_screenshots():
    """获取最新上传的截图目录

    Query params:
        platform: 平台名称（可选）
    """
    platform = request.args.get('platform')

    try:
        latest_sessions = []

        if platform:
            platform_dir = SCREENSHOTS_DIR / platform
            if platform_dir.exists():
                sessions = sorted(platform_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
                for session in sessions:
                    screenshots = [s.name for s in sorted(session.glob("*.png"))]
                    latest_sessions.append({
                        "platform": platform,
                        "session": session.name,
                        "screenshots": screenshots,
                        "mtime": session.stat().st_mtime
                    })
        else:
            for platform_dir in SCREENSHOTS_DIR.iterdir():
                if platform_dir.is_dir():
                    sessions = sorted(platform_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:2]
                    for session in sessions:
                        screenshots = [s.name for s in sorted(session.glob("*.png"))]
                        latest_sessions.append({
                            "platform": platform_dir.name,
                            "session": session.name,
                            "screenshots": screenshots,
                            "mtime": session.stat().st_mtime
                        })

        latest_sessions.sort(key=lambda x: x['mtime'], reverse=True)

        return jsonify({
            "code": 200,
            "msg": "获取最新截图成功",
            "data": latest_sessions
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"获取最新截图失败: {str(e)}",
            "data": []
        }), 500


@app.route('/screenshots/cleanup', methods=['POST'])
def cleanup_screenshots():
    """清理旧截图

    Body params:
        days: 保留天数（默认7天）
    """
    days = request.json.get('days', 7)

    try:
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        deleted_count = 0

        for platform_dir in SCREENSHOTS_DIR.iterdir():
            if platform_dir.is_dir():
                for session_dir in platform_dir.iterdir():
                    if session_dir.is_dir():
                        dir_time = session_dir.stat().st_mtime
                        if dir_time < cutoff_time:
                            for file in session_dir.glob("*"):
                                file.unlink()
                            session_dir.rmdir()
                            deleted_count += 1

        return jsonify({
            "code": 200,
            "msg": f"清理完成，删除了 {deleted_count} 个旧截图目录",
            "data": {"deleted_count": deleted_count}
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"清理截图失败: {str(e)}",
            "data": None
        }), 500


if __name__ == '__main__':
    threading.Thread(target=nightly_account_status_checker, daemon=True).start()
    app.run(host='0.0.0.0' ,port=5409)
