"""大鱼号表单的固定选项；CLI、视频和图文共用同一份定义。"""
from datetime import timedelta, timezone

# 视频与图文实测使用同一定时控件：北京时间，最早两小时后、最晚七天内，五分钟一档。
DAYU_TIMEZONE = timezone(timedelta(hours=8), "Asia/Shanghai")
DAYU_SCHEDULE_MIN_HOURS = 2
DAYU_SCHEDULE_MAX_DAYS = 7
DAYU_SCHEDULE_STEP_MINUTES = 5
DAYU_MONTH_NAMES = ("一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月")

# 2026-10-17 当前账号视频表单的完整分类；入口和直接调用共用，上传前拒绝无效值。
DAYU_VIDEO_CATEGORIES = (
    "其他", "社会", "国内", "国际", "体育", "科技", "娱乐", "军事", "财经", "汽车",
    "房产", "时尚", "健康", "两性情感", "游戏", "动漫", "旅游", "美食", "历史", "奇闻",
    "科学探索", "星座", "育儿", "教育", "美女", "搞笑", "演讲", "萌娃", "萌宠", "音乐",
    "语言类", "记录短片", "涨姿势", "劲爆体育", "幽默", "综艺", "电视剧", "电影", "纪录片",
    "少儿", "文化", "三农", "生活方式",
)
# 转载参与条件必填校验，独立命名避免各调用处重复写业务值。
DAYU_SOURCE_REPRINT = "转载"
DAYU_SOURCE_TYPES = ("无需标注", "AI生成", "虚构演绎", "营销信息", DAYU_SOURCE_REPRINT, "个人观点", "不适宜未成年人")

# 管理页实测：1 为已公开，3 为提交后审核中；二者都能确认已提交发表，草稿不在其中。
DAYU_CONTENT_PUBLIC = 1
DAYU_CONTENT_REVIEWING = 3
# 真实定时提交后管理页显示“待发布”，作品接口 status=5，_app_extra 包含已保存的时间。
DAYU_CONTENT_SCHEDULED = 5
