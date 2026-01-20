import sqlite3
import json
import os

# 数据库文件路径（如果不存在会自动创建）
db_file = './database.db'

# 如果数据库已存在，则删除旧的表（可选）
# if os.path.exists(db_file):
#     os.remove(db_file)

# 连接到SQLite数据库（如果文件不存在则会自动创建）
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 创建账号记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,  -- 存储文件路径
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0
)
''')

# 创建文件记录表
cursor.execute('''CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 唯一标识每条记录
    filename TEXT NOT NULL,               -- 文件名
    filesize REAL,                     -- 文件大小（单位：MB）
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 上传时间，默认当前时间
    file_path TEXT                        -- 文件路径
)
''')

# 创建发布任务记录表
cursor.execute('''CREATE TABLE IF NOT EXISTS publish_task_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 唯一标识每条记录
    task_id TEXT NOT NULL,                -- 任务ID，用于关联批次任务
    filename TEXT NOT NULL,               -- 文件名
    file_id INTEGER,                      -- 文件ID，关联file_records表
    account_id INTEGER NOT NULL,          -- 账号ID，关联user_info表
    account_name TEXT NOT NULL,           -- 账号名
    platform_name TEXT NOT NULL,          -- 平台名称
    platform_type INTEGER NOT NULL,       -- 平台类型
    status TEXT NOT NULL DEFAULT '待发布',-- 发布状态：待发布、发布中、发布成功、发布失败
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 创建时间
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 更新时间
    error_msg TEXT                        -- 错误信息，发布失败时存储
)
''')

# 提交更改
conn.commit()
print("✅ 表创建成功")
# 关闭连接
conn.close()