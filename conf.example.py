import os
import sys
from pathlib import Path

# 源码目录：始终指向项目根，用于读取打包进去的只读资源
SOURCE_DIR = Path(__file__).parent.resolve()

# 数据目录（db / cookiesFile / videoFile 等可写数据的锚点）：
# - 冻结态（PyInstaller 打包后）：写 %APPDATA%/social-auto-upload
# - 源码态：保持项目根
if getattr(sys, "frozen", False):
    _appdata = Path(os.environ.get("APPDATA") or Path.home())
    BASE_DIR = _appdata / "social-auto-upload"
    BASE_DIR.mkdir(parents=True, exist_ok=True)
else:
    BASE_DIR = SOURCE_DIR

XHS_SERVER = "http://127.0.0.1:11901"  # only used by xhs-related flows
LOCAL_CHROME_PATH = ""  # optional, e.g. C:/Program Files/Google/Chrome/Application/chrome.exe
LOCAL_CHROME_HEADLESS = True  # default headless behavior for uploader/examples
DEBUG_MODE = True  # default debug behavior
