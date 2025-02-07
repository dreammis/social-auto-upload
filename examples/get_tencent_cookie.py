import asyncio
from pathlib import Path
import sys
import argparse

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))

from conf import BASE_DIR
from uploader.tencent_uploader.main import weixin_setup, batch_cookie_auth, get_tencent_cookie
from utils.log import tencent_logger
from utils.social_media_db import SocialMediaDB


async def add_new_account():
    """
    添加新账号并获取cookie
    通过扫码登录自动获取账号信息
    """
    cookies_folder = Path(BASE_DIR) / "cookies" / "tencent_uploader"
    cookies_folder.mkdir(parents=True, exist_ok=True)
    
    tencent_logger.info("[+]请扫码登录新账号")
    if new_cookie_file := await get_tencent_cookie(str(cookies_folder / "temp.json")):
        account_name = Path(new_cookie_file).stem
        tencent_logger.success(f"[+]成功添加账号: {account_name}")


async def update_cookie(account_name: str = None):
    """
    更新现有账号的cookie
    
    Args:
        account_name: 指定的账号名称，如果为None则更新所有账号的cookie
    """
    db = SocialMediaDB()
    try:
        if account_name:
            # 获取指定账号的信息
            accounts = db.get_all_accounts("tencent")
            account = next((acc for acc in accounts if acc['nickname'] == account_name), None)
            if not account:
                tencent_logger.error(f"[+]账号 {account_name} 不存在")
                return
                
            # 获取账号的cookie文件
            cookie_paths = account.get('cookie_paths', [])
            if not cookie_paths:
                tencent_logger.error(f"[+]账号 {account_name} 没有cookie记录")
                return
                
            # 使用最新的cookie文件
            cookie_file = cookie_paths[0]
            tencent_logger.info(f"[+]开始更新账号 {account_name} 的cookie")
            if await weixin_setup(cookie_file, handle=True):
                tencent_logger.success(f"[+]账号 {account_name} cookie更新成功")
            else:
                tencent_logger.error(f"[+]账号 {account_name} cookie更新失败")
        else:
            # 获取所有账号信息
            accounts = db.get_all_accounts("tencent")
            if not accounts:
                tencent_logger.warning("[+]未找到任何账号记录")
                tencent_logger.info("[+]请使用 -n 参数添加新账号")
                return
            
            # 获取所有有效的cookie文件
            cookie_files = []
            for account in accounts:
                if account.get('cookie_paths'):
                    cookie_files.append(account['cookie_paths'][0])  # 使用最新的cookie文件
            
            if not cookie_files:
                tencent_logger.warning("[+]未找到任何cookie文件")
                tencent_logger.info("[+]请使用 -n 参数添加新账号")
                return
            
            # 使用并发验证
            tencent_logger.info(f"[+]开始并发验证 {len(cookie_files)} 个账号的cookie")
            auth_results = await batch_cookie_auth(cookie_files)
            
            # 处理验证结果
            need_update = []
            for cookie_file, (is_valid, account_name) in auth_results.items():
                if not is_valid:
                    need_update.append((cookie_file, account_name))
            
            # 更新无效的cookie
            if need_update:
                tencent_logger.info(f"[+]发现 {len(need_update)} 个账号需要更新cookie")
                for cookie_file, account_name in need_update:
                    tencent_logger.info(f"[+]开始更新账号 【{account_name}】 的cookie")
                    if await weixin_setup(cookie_file, handle=True):
                        tencent_logger.success(f"[+]账号 【{account_name}】 cookie更新成功")
                    else:
                        tencent_logger.error(f"[+]账号 【{account_name}】 cookie更新失败")
            else:
                tencent_logger.success("[+]所有账号cookie均有效")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='视频号账号cookie管理工具')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-n', '--new', action='store_true', help='添加新账号')
    group.add_argument('-u', '--update', help='更新指定账号的cookie')
    group.add_argument('-a', '--all', action='store_true', help='更新所有账号的cookie')
    args = parser.parse_args()
    
    if args.new:
        asyncio.run(add_new_account())
    elif args.update:
        asyncio.run(update_cookie(args.update))
    elif args.all:
        asyncio.run(update_cookie())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
