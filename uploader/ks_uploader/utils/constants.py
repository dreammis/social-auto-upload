# -*- coding: utf-8 -*-

# 视频相关常量
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi']
MAX_VIDEO_SIZE = 4 * 1024 * 1024 * 1024  # 4GB
MAX_TITLE_LENGTH = 100
MAX_TAGS = 3
MIN_VIDEO_DURATION = 5  # 最短视频时长（秒）
MAX_VIDEO_DURATION = 900  # 最长视频时长（秒）
ALLOWED_VIDEO_CODECS = ['h264', 'h265']
ALLOWED_AUDIO_CODECS = ['aac']

# 上传相关常量
UPLOAD_TIMEOUT = 120  # 秒
MAX_RETRIES = 3
MAX_CONCURRENT_UPLOADS = 3
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
PROGRESS_UPDATE_INTERVAL = 2  # 进度更新间隔（秒）
RETRY_DELAYS = [2, 5, 10]  # 重试延迟时间（秒）

# URL常量
BASE_URL = "https://cp.kuaishou.com"
UPLOAD_URL = f"{BASE_URL}/article/publish/video"
MANAGE_URL = f"{BASE_URL}/article/manage/video"
LOGIN_URL = f"{BASE_URL}/login"
PROFILE_URL = f"{BASE_URL}/profile"  # 个人资料页面

# Cookie相关常量
COOKIE_VALID_TIME = 24 * 60 * 60  # 24小时
COOKIE_CHECK_INTERVAL = 60 * 60  # 1小时
COOKIE_REFRESH_THRESHOLD = 22 * 60 * 60  # 22小时（提前2小时刷新）

# 浏览器配置
BROWSER_ARGS = [
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-setuid-sandbox',
    '--disable-web-security',
    '--disable-features=IsolateOrigins,site-per-process'
]

BROWSER_VIEWPORT = {
    'width': 1920,
    'height': 1080
}

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'

# 错误处理配置
MAX_UPLOAD_RETRIES = 3
MAX_PUBLISH_RETRIES = 3
ERROR_SCREENSHOT_DIR = "error_screenshots"
UPLOAD_ERROR_WAIT_TIME = 5  # 上传错误等待时间（秒）

# 性能优化配置
DEFAULT_TIMEOUT = 30000  # 默认超时时间（毫秒）
NETWORK_IDLE_TIMEOUT = 5000  # 网络空闲超时时间（毫秒）
PAGE_LOAD_TIMEOUT = 30000  # 页面加载超时时间（毫秒）
ELEMENT_TIMEOUT = 10000  # 元素等待超时时间（毫秒）

# 日志配置
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'
LOG_FILE = 'kuaishou_uploader.log'

# 选择器配置
SELECTORS = {
    'upload_button': "button[class^='_upload-btn']",
    'description': "div.description",
    'publish_button': "button:text('发布')",
    'confirm_button': "button:text('确认发布')",
    'progress_text': "div.progress-text",
    'error_message': "div.error-message",
    'new_feature_button': 'button[type="button"] span:text("我知道了")',
    'schedule_time': {
        'radio': "label:text('发布时间') xpath=following-sibling::div .ant-radio-input",
        'input': 'div.ant-picker-input input[placeholder="选择日期时间"]'
    },
    'profile': {
        'info_card': "div.header-info-card",
        'avatar': "div.header-info-card img.user-image",
        'username': "div.header-info-card div.user-name",
        'kwai_id': "div.header-info-card div.user-kwai-id",
        'stats': "div.header-info-card div.user-cnt__item",
        'description': "div.header-info-card div.user-desc"
    }
} 