#!/usr/bin/env bash
set -e

# 数据库初始化：必须在容器启动时执行（而非构建时），
# 因为 /app/db 可能被持久卷挂载覆盖，构建时写入的数据会丢失。
# 建表 SQL 直接内联，不依赖可能被卷覆盖的 createTable.py 文件位置。
DB_DIR="/app/db"
DB_FILE="$DB_DIR/database.db"

# 确保目录存在
mkdir -p "$DB_DIR"

echo "初始化数据库: $DB_FILE"
python - "$DB_FILE" <<'PYEOF'
import sqlite3
import sys

db_file = sys.argv[1]

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 创建账号记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0
)
''')

# 创建文件记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filesize REAL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT
)
''')

conn.commit()
print("✅ 数据库表初始化完成")
conn.close()
PYEOF

# 启动 Flask 后端
exec "$@"
