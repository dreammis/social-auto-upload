# -*- coding: utf-8 -*-
from pathlib import Path

from utils.files_times import get_absolute_path
from utils.log import tencent_logger
from .modules.account import cookie_auth, batch_cookie_auth

__all__ = ['weixin_setup']

async def weixin_setup(account_file, handle=False):
    """
    设置微信登录
    Args:
        account_file: cookie文件路径
        handle: 是否允许手动处理（自动登录）
    Returns:
        bool: 设置是否成功
    """
    try:
        # 获取绝对路径
        account_file = get_absolute_path(account_file, "tencent_uploader")
        account_dir = Path(account_file).parent

        # 检查是否存在同目录下的其他账号cookie文件
        existing_cookies = list(account_dir.glob("*.json"))
        
        # 验证所有cookie（现在cookie_auth会自动处理登录）
        if handle:
            cookie_results = await batch_cookie_auth([str(f) for f in existing_cookies])
            # 只要有一个账号验证成功就返回True
            return any(valid for _, (valid, _) in cookie_results.items())
        else:
            # 如果不允许手动处理，只验证cookie有效性
            for cookie_file in existing_cookies:
                if await cookie_auth(str(cookie_file)):
                    return True
        return False

    except Exception as e:
        tencent_logger.error(f"账号设置失败: {str(e)}")
        return False