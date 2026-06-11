from conf import LOCAL_CHROME_PATH
from utils.runtime_config import get_local_chrome_headless

def get_browser_options():
    options = {
        'headless': get_local_chrome_headless(),
        'args': [
            '--disable-blink-features=AutomationControlled',
            '--lang=zh-CN',
            '--disable-infobars',
            '--start-maximized',
            '--no-sandbox',
            '--disable-web-security'
        ]
    }
    if LOCAL_CHROME_PATH:
        options['executable_path'] = LOCAL_CHROME_PATH
    return options
