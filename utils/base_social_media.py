from pathlib import Path
from typing import List
import os
import requests

from conf import BASE_DIR

SOCIAL_MEDIA_DOUYIN = "douyin"
SOCIAL_MEDIA_TENCENT = "tencent"
SOCIAL_MEDIA_TIKTOK = "tiktok"
SOCIAL_MEDIA_BILIBILI = "bilibili"
SOCIAL_MEDIA_KUAISHOU = "kuaishou"


def get_supported_social_media() -> List[str]:
    """
    获取当前支持的社交媒体平台列表。

    Returns:
        List[str]: 支持的社交媒体平台名称列表，包括抖音、腾讯、TikTok和快手。
    """
    return [SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU]


def get_cli_action() -> List[str]:
    """
    获取CLI（命令行界面）可执行的操作列表。

    Returns:
        List[str]: 包含可用CLI操作的列表，如 ['upload', 'login', 'watch']。
    """
    return ["upload", "login", "watch"]


async def set_init_script(context):
    """
    异步函数，用于在给定的上下文中设置初始化脚本。

    参数:
    - context: 上下文对象，用于执行初始化脚本的环境。

    返回:
    - 返回更新后的上下文对象。
    """
    # 获取stealth.js脚本的路径
    stealth_js_path = get_stealth_js_path()

    # 在上下文中添加初始化脚本，使用stealth.js路径
    await context.add_init_script(path=stealth_js_path)

    # 返回更新后的上下文对象
    return context


def get_stealth_js_path() -> Path:
    """
    获取或下载 stealth.min.js 文件并返回其路径

    如果 utils 目录下不存在 stealth.min.js 文件，则从指定的 URL 下载并保存到该目录中
    使用缓存的文件可以避免重复下载，提高效率

    Returns:
        Path: stealth.min.js 文件的路径
    """
    # 定义 stealth.min.js 文件的路径
    stealth_js_path = Path(BASE_DIR) / "utils" / "stealth.min.js"

    # 检查文件是否已经存在
    if not stealth_js_path.exists():
        # stealth.min.js 文件的下载 URL
        url = "https://cdn.jsdelivr.net/gh/requireCool/stealth.min.js/stealth.min.js"
        # 发起 HTTP 请求，下载文件
        response = requests.get(url)
        # 确保 utils 目录存在，如果不存在则创建
        stealth_js_path.parent.mkdir(exist_ok=True)
        # 将下载的文件内容写入到 stealth.min.js 文件中
        with open(stealth_js_path, "wb") as f:
            f.write(response.content)

    # 返回 stealth.min.js 文件的路径
    return stealth_js_path
