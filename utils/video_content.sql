-- Active: 1739798225423@@127.0.0.1@3306
-- 视频内容主表
CREATE TABLE IF NOT EXISTS video_contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,  -- 关联social_media_accounts表
    title TEXT NOT NULL,  -- 视频标题
    thumb_base64 TEXT,  -- 封面图片base64数据
    publish_time DATETIME,  -- 发布时间
    status VARCHAR(50),  -- 视频状态
    plays INTEGER DEFAULT 0,  -- 播放数
    likes INTEGER DEFAULT 0,  -- 点赞数
    comments INTEGER DEFAULT 0,  -- 评论数
    shares INTEGER DEFAULT 0,  -- 分享数
    tags TEXT,  -- 标签列表，JSON格式
    mentions TEXT,  -- 提及用户列表，JSON格式
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES social_media_accounts(id),
    UNIQUE(account_id, title, publish_time)
); 