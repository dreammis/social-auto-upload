from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
XHS_SERVER = "http://127.0.0.1:11901"  # only used by xhs-related flows
LOCAL_CHROME_PATH = ""  # optional, e.g. C:/Program Files/Google/Chrome/Application/chrome.exe
LOCAL_CHROME_HEADLESS = True  # default headless behavior for uploader/examples
DEBUG_MODE = True  # default debug behavior
# Optional proxy for the YouTube uploader. Where youtube.com is blocked, direct
# connections time out and the (patchright) chromium does NOT use the system proxy.
# Point this at your local proxy port, e.g. "http://127.0.0.1:7890". None = no proxy.
YT_PROXY = None

# Upload-Post (https://upload-post.com) — optional, API-based publishing for the
# international platforms (TikTok / Instagram / YouTube / X / LinkedIn / ...).
# No cookie file and no browser: connect the accounts once in the dashboard, then
# set the API key and the profile name here. Leave empty to keep using the
# browser uploaders.
UPLOAD_POST_API_KEY = ""
UPLOAD_POST_USER = ""
