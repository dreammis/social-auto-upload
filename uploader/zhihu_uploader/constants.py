"""知乎创作中心页面与上传限制。"""
from datetime import timedelta, timezone


ZHIHU_CREATOR_URL = "https://www.zhihu.com/creator"
ZHIHU_ARTICLE_URL = "https://zhuanlan.zhihu.com/write"
ZHIHU_VIDEO_URL = "https://www.zhihu.com/upload-video"
ZHIHU_MANAGE_URL = "https://www.zhihu.com/creator/manage/creation"

ZHIHU_TIMEZONE = timezone(timedelta(hours=8), "Asia/Shanghai")
ZHIHU_SCHEDULE_MINUTES = 30
ZHIHU_SCHEDULE_MAX_HOURS = 48

ZHIHU_ARTICLE_TITLE_MAX = 100
ZHIHU_VIDEO_TITLE_MIN = 5
ZHIHU_VIDEO_TITLE_MAX = 50
ZHIHU_VIDEO_DESCRIPTION_MAX = 300
ZHIHU_VIDEO_TOPICS_MAX = 10
ZHIHU_VIDEO_MAX_BYTES = 20 * 1024**3
ZHIHU_VIDEO_MAX_SECONDS = 4 * 60 * 60
ZHIHU_VIDEO_EXTENSIONS = {
    ".3gp", ".asf", ".avi", ".dat", ".f4v", ".flv", ".m4v", ".mkv", ".mov",
    ".mp4", ".mp4v", ".mpe", ".mpeg", ".mpg", ".ra", ".ram", ".rm", ".rmvb",
    ".vob", ".webm", ".wm", ".wmv",
}
ZHIHU_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".heic", ".heif", ".gif"}

# 原创声明使用提交值；CLI 与上传校验共用，避免两处枚举漂移。
ZHIHU_ORIGINALITY = ("original", "reprint")
