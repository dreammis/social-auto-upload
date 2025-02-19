# -*- coding: utf-8 -*-
import asyncio
import sys
from pathlib import Path
import os
from datetime import datetime

# 获取项目根目录的绝对路径
BASE_DIR = Path(os.path.dirname(os.path.dirname(__file__)))
# 添加项目根目录到 Python 路径
sys.path.append(str(BASE_DIR))

from utils.log import kuaishou_logger
from utils.playwright_helper import PlaywrightHelper
from uploader.ks_uploader.modules.account import account_manager
from utils.social_media_db import SocialMediaDB

async def main() -> None:
    """主函数"""
    try:
        # 安装浏览器
        if not PlaywrightHelper.install_browser():
            sys.exit(1)

        # 初始化数据库
        db = SocialMediaDB()
        platform = "kuaishou"
        nickname = "向阳也有米"
        
        # 查询账号信息
        accounts = db.get_all_accounts(platform)
        target_account = next((acc for acc in accounts if acc['nickname'] == nickname), None)
        
        # 根据昵称生成cookie文件名
        cookie_filename = f"{nickname}.json"
        default_cookie_path = str(BASE_DIR / "cookies" / "ks_uploader" / cookie_filename)
        
        # 获取cookie路径
        account_file = default_cookie_path
        if target_account:
            cookies = db.get_valid_cookies(platform, target_account['account_id'])
            if cookies:
                account_file = cookies[0]  # 使用最新的cookie
        
        # 设置Cookie
        result = await account_manager.setup_cookie(account_file, expected_username=nickname)
        
        # 处理结果
        if result['success']:
            kuaishou_logger.success(f"Cookie设置成功！")
            kuaishou_logger.info(f"Cookie文件: {result['cookie_file']}")
            kuaishou_logger.info(f"过期时间: {datetime.fromtimestamp(result['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 更新数据库
            if not target_account:
                # 新账号
                if db.add_account(platform, nickname, nickname):
                    kuaishou_logger.success(f"成功添加账号: {nickname}")
                    db.add_cookie(platform, nickname, account_file)
                else:
                    kuaishou_logger.error(f"添加账号失败: {nickname}")
                    sys.exit(1)
            else:
                # 更新现有账号
                db.add_cookie(platform, target_account['account_id'], account_file)
        else:
            kuaishou_logger.error(f"Cookie设置失败: {result['message']}")
            if 'error' in result:
                kuaishou_logger.error(f"错误详情: {result['error']}")
            sys.exit(1)

    except Exception as e:
        kuaishou_logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)
    finally:
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    asyncio.run(main())
