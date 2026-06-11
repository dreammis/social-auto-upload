from conf import LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH

def get_browser_options():
    options = {
        'headless': LOCAL_CHROME_HEADLESS,
        'args': [
            '--disable-blink-features=AutomationControlled',
            '--lang=zh-CN',
            '--disable-infobars',
            # 不加 --start-maximized：context 默认 viewport 是 1280×720，
            # 加了会让窗口最大化但页面仍按 1280×720 渲染后被拉伸，
            # 导致窗口尺寸和实际显示内容不一致。
            '--no-sandbox',
            '--disable-web-security'
        ]
    }
    if LOCAL_CHROME_PATH:
        options['executable_path'] = LOCAL_CHROME_PATH
    return options
