from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(__file__).parent.absolute()
XHS_SERVER = "http://127.0.0.1:5005"
# 使用原始字符串(r)或正斜杠(/)来避免转义序列问题
LOCAL_CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"   # 或使用 "C:/Program Files/Google/Chrome/Application/chrome.exe"

# 可扩展为：
class TencentConfig:
    VIDEO_SETTINGS = {
        'max_retries': 5,
        'allowed_formats': ['.mp4', '.mov'],
        'default_category': '生活'
    }
    
    SCHEDULING_RULES = {
        'earliest_time': '06:00',
        'latest_time': '23:00'
    }
