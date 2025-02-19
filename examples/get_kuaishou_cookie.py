# -*- coding: utf-8 -*-
import asyncio
import sys
from pathlib import Path
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

# 获取项目根目录的绝对路径
BASE_DIR = Path(os.path.dirname(os.path.dirname(__file__)))
# 添加项目根目录到 Python 路径
sys.path.append(str(BASE_DIR))

from utils.log import kuaishou_logger
from uploader.ks_uploader.modules.account import account_manager
from uploader.ks_uploader.utils.constants import (
    BROWSER_ARGS, BROWSER_VIEWPORT, USER_AGENT,
    LOGIN_URL, COOKIE_VALID_TIME
)

# 确保错误截图目录存在
ERROR_SCREENSHOT_DIR = BASE_DIR / "error_screenshots"
ERROR_SCREENSHOT_DIR.mkdir(exist_ok=True)

class CookieSetupError(Exception):
    """Cookie设置错误"""
    pass

def install_playwright_browser() -> None:
    """安装 Playwright 浏览器"""
    kuaishou_logger.info("正在安装 Playwright 浏览器...")
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        kuaishou_logger.success("Playwright 浏览器安装成功！")
    except subprocess.CalledProcessError as e:
        kuaishou_logger.error(f"安装失败: {str(e)}")
        raise CookieSetupError("Playwright 浏览器安装失败")

async def verify_cookie(account_file: str) -> Dict[str, Any]:
    """验证Cookie有效性"""
    try:
        is_valid = await account_manager.validate_cookie(account_file)
        return {
            'valid': is_valid,
            'checked_at': datetime.now().isoformat(),
            'expires_at': (datetime.now().timestamp() + COOKIE_VALID_TIME) if is_valid else None
        }
    except Exception as e:
        kuaishou_logger.error(f"Cookie验证失败: {str(e)}")
        return {
            'valid': False,
            'error': str(e),
            'checked_at': datetime.now().isoformat()
        }

async def refresh_cookie(account_file: str) -> bool:
    """刷新Cookie"""
    try:
        return await account_manager.refresh_cookie(account_file)
    except Exception as e:
        kuaishou_logger.error(f"Cookie刷新失败: {str(e)}")
        return False

async def setup_cookie(account_file: str, force_refresh: bool = False) -> Dict[str, Any]:
    """设置和验证Cookie"""
    try:
        account_file = Path(account_file)
        result = {
            'success': False,
            'message': '',
            'cookie_file': str(account_file),
            'timestamp': datetime.now().isoformat()
        }

        # 确保目录存在
        account_file.parent.mkdir(parents=True, exist_ok=True)

        # 检查Cookie文件是否存在
        if not force_refresh and account_file.exists():
            # 验证现有Cookie
            verification = await verify_cookie(str(account_file))
            if verification['valid']:
                result.update({
                    'success': True,
                    'message': 'Cookie有效',
                    'expires_at': verification['expires_at']
                })
                return result

        # 需要刷新或重新获取Cookie
        kuaishou_logger.info('正在获取新的Cookie...')
        if await refresh_cookie(str(account_file)):
            # 验证新Cookie
            verification = await verify_cookie(str(account_file))
            if verification['valid']:
                result.update({
                    'success': True,
                    'message': 'Cookie已更新并验证成功',
                    'expires_at': verification['expires_at']
                })
            else:
                result.update({
                    'message': 'Cookie更新成功但验证失败',
                    'error': verification.get('error', '未知错误')
                })
        else:
            result.update({
                'message': 'Cookie获取失败'
            })

        return result

    except Exception as e:
        kuaishou_logger.error(f"Cookie设置失败: {str(e)}")
        # 保存错误截图
        error_screenshot = ERROR_SCREENSHOT_DIR / f"cookie_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        try:
            # 如果有页面实例，保存截图
            if 'page' in locals():
                await page.screenshot(path=str(error_screenshot))
                kuaishou_logger.info(f"错误截图已保存: {error_screenshot}")
        except:
            pass
            
        return {
            'success': False,
            'message': f'Cookie设置过程出错: {str(e)}',
            'cookie_file': str(account_file),
            'timestamp': datetime.now().isoformat()
        }

async def main() -> None:
    """主函数"""
    try:
        # 安装浏览器
        install_playwright_browser()

        # 设置Cookie文件路径
        account_file = Path(BASE_DIR / "cookies" / "ks_uploader" / "account.json")
        
        # 设置Cookie
        result = await setup_cookie(account_file)
        
        # 输出结果
        if result['success']:
            kuaishou_logger.success(f"Cookie设置成功！")
            kuaishou_logger.info(f"Cookie文件: {result['cookie_file']}")
            kuaishou_logger.info(f"过期时间: {datetime.fromtimestamp(result['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            kuaishou_logger.error(f"Cookie设置失败: {result['message']}")
            if 'error' in result:
                kuaishou_logger.error(f"错误详情: {result['error']}")
            sys.exit(1)

    except Exception as e:
        kuaishou_logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
