import sqlite3
from pathlib import Path


def create_tables(db_path="./database.db"):
    """在指定路径建好所有表（IF NOT EXISTS，幂等）。

    打包后后端启动时调用，确保 %APPDATA% 下的库文件存在且表结构就绪。
    """
    db_path = str(db_path)
    # 确保父目录存在（%APPDATA%/social-auto-upload/db 首次运行时可能不存在）
    parent = Path(db_path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # 创建账号记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type INTEGER NOT NULL,
            filePath TEXT NOT NULL,  -- 存储文件路径
            userName TEXT NOT NULL,
            status INTEGER DEFAULT 0,
            platformUserName TEXT,           -- 登录后抓取的平台真实昵称（可空）
            statusDetail TEXT                -- 异常详情：淘宝页面 .error-desc-- 的文本
                                             -- 例如 "账号违规: 原创性不足"；正常行为 NULL
        )
        ''')

        # 迁移：旧库可能缺列，缺则补加（幂等，不影响旧数据）
        cursor.execute("PRAGMA table_info(user_info)")
        cols = [r[1] for r in cursor.fetchall()]
        if "platformUserName" not in cols:
            cursor.execute("ALTER TABLE user_info ADD COLUMN platformUserName TEXT")
        if "statusDetail" not in cols:
            cursor.execute("ALTER TABLE user_info ADD COLUMN statusDetail TEXT")

        # 创建文件记录表
        cursor.execute('''CREATE TABLE IF NOT EXISTS file_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- 唯一标识每条记录
            filename TEXT NOT NULL,               -- 文件名
            filesize REAL,                     -- 文件大小（单位：MB）
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 上传时间，默认当前时间
            file_path TEXT                        -- 文件路径
        )
        ''')

        conn.commit()
        print("[db] tables ready")
    finally:
        conn.close()


if __name__ == '__main__':
    # 直接运行时在当前目录建库（保持原脚本行为）
    create_tables('./database.db')
