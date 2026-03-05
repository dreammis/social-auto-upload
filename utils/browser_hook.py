from conf import LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH

def get_browser_options():
    options = {
        'headless': LOCAL_CHROME_HEADLESS,
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
