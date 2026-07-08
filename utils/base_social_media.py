from pathlib import Path
import random
from typing import List

from conf import BASE_DIR

SOCIAL_MEDIA_DOUYIN = "douyin"
SOCIAL_MEDIA_TENCENT = "tencent"
SOCIAL_MEDIA_TIKTOK = "tiktok"
SOCIAL_MEDIA_BILIBILI = "bilibili"
SOCIAL_MEDIA_KUAISHOU = "kuaishou"

# 模拟真人桌面分辨率
_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

_LOCALES = ["zh-CN", "zh-CN", "zh-CN", "zh-TW"]  # 偏重简中
_TIMEZONES = ["Asia/Shanghai", "Asia/Shanghai", "Asia/Shanghai", "Asia/Chongqing"]


def get_supported_social_media() -> List[str]:
    return [SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU]


def get_cli_action() -> List[str]:
    return ["upload", "login", "watch"]


async def set_init_script(context):
    stealth_js_path = Path(BASE_DIR / "utils/stealth.min.js")
    await context.add_init_script(path=stealth_js_path)
    return context


async def create_stealth_context(browser, **kwargs):
    """创建带随机指纹的 browser context，让自动化更像真人。

    - 随机 viewport 尺寸
    - 固定 timezone/locale 为中国
    - 其他 kwargs 透传给 browser.new_context()
    """
    viewport = random.choice(_VIEWPORTS)
    context = await browser.new_context(
        viewport=viewport,
        timezone_id=random.choice(_TIMEZONES),
        locale=random.choice(_LOCALES),
        **kwargs,
    )
    context = await set_init_script(context)
    return context


def human_delay(base: float, jitter: float = 0.5) -> float:
    """给固定 sleep 加随机抖动：base * (1 ± jitter)。

    human_delay(2, 0.5) → 1.0~3.0 之间的随机值。
    """
    return base * (1 + random.uniform(-jitter, jitter))


async def human_type(page, text: str, base_delay: int = 50) -> None:
    """逐字输入，每个字符间隔随机 30~120ms，模拟真人打字。"""
    for char in text:
        await page.keyboard.type(char, delay=random.randint(30, 120))
        # 每隔几个字偶尔停顿一下
        if random.random() < 0.1:
            import asyncio
            await asyncio.sleep(random.uniform(0.1, 0.4))

