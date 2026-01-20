from pathlib import Path

# BASE_DIR 指向项目根目录
base_dir = Path(__file__).parent.resolve()
BASE_DIR = base_dir.parent.resolve()

XHS_SERVER = "http://127.0.0.1:11901"
LOCAL_CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"   # change me necessary！ for example C:/Program Files/Google/Chrome/Application/chrome.exe
LOCAL_CHROME_HEADLESS = False
