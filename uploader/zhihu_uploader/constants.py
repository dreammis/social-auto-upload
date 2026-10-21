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
# 页面按 size > 102400 接收视频，恰好 100KB 也会被拒绝。
ZHIHU_VIDEO_MIN_BYTES = 100 * 1024
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

# 当前领域与声明菜单的完整文案；CLI 展示合法值，提交前仍与实时菜单核对。
ZHIHU_VIDEO_CATEGORIES = (
    "人文", "体育竞技", "健康医学", "其他", "军事", "动漫", "娱乐", "宠物",
    "家居生活", "家用电器", "影视", "心理学", "情感", "故事", "教育", "数码",
    "旅行", "时尚穿搭", "母婴亲子", "汽车", "法律", "游戏电竞", "社会/时政",
    "社会学", "科学工程", "科技互联网", "经济与管理", "美妆个护", "美食",
    "职场", "艺术", "运动健身", "音乐",
)
ZHIHU_VIDEO_MARKS = (
    "内容无需标注", "含 AI 生成内容", "含虚构演绎内容", "内容含营销信息",
    "内容为转载", "个人观点仅供参考",
)
