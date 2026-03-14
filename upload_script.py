#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行视频上传脚本
使用方法:
python upload_script.py --file "视频文件路径" --account "账号名称" --title "视频标题"
"""

import sys
import os

# Windows 控制台编码修复
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import argparse
import sqlite3
from pathlib import Path
from conf import BASE_DIR
from myUtils.postVideo import post_video_xhs, post_video_tencent, post_video_DouYin, post_video_ks

# 数据库路径
DB_PATH = Path(BASE_DIR / "db" / "database.db")


def get_account_by_name(user_name):
    """通过账号名称获取账号信息"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT filePath, type FROM user_info WHERE userName = ? AND status = 1",
                (user_name,)
            )
            result = cursor.fetchone()
            if result:
                return {"filePath": result[0], "type": result[1]}
            return None
    except Exception as e:
        print(f"❌ 查询账号失败: {str(e)}")
        return None


def publish_video_direct(file_path, account_list, title, platform_type=3, enable_timer=0):
    """直接调用内部函数发布视频"""
    try:
        print(f"📤 正在发布视频...")
        print(f"   平台: {platform_type} (1=小红书, 2=视频号, 3=抖音, 4=快手)")
        print(f"   标题: {title}")
        print(f"   文件: {file_path}")
        print(f"   账号: {account_list}")
        
        declaration_info = {
            "declaration_type": "内容由AI生成",
            "declaration_location": [],
            "declaration_date": "",
            "isDraft": False
        }
        
        match platform_type:
            case 1:
                post_video_xhs(
                    title=title,
                    files=[file_path],
                    tags=[],
                    account_file=account_list,
                    category=None,
                    enableTimer=enable_timer,
                    videos_per_day=1,
                    daily_times=["10:00"],
                    start_days=0
                )
            case 2:
                post_video_tencent(
                    title=title,
                    files=[file_path],
                    tags=[],
                    account_file=account_list,
                    category=None,
                    enableTimer=enable_timer,
                    videos_per_day=1,
                    daily_times=["10:00"],
                    start_days=0,
                    is_draft=False
                )
            case 3:
                post_video_DouYin(
                    title=title,
                    files=[file_path],
                    tags=[],
                    account_file=account_list,
                    category=None,
                    enableTimer=enable_timer,
                    videos_per_day=1,
                    daily_times=["10:00"],
                    start_days=0,
                    thumbnail_path='',
                    productLink='',
                    productTitle='',
                    declaration_info=declaration_info
                )
            case 4:
                post_video_ks(
                    title=title,
                    files=[file_path],
                    tags=[],
                    account_file=account_list,
                    category=None,
                    enableTimer=enable_timer,
                    videos_per_day=1,
                    daily_times=["10:00"],
                    start_days=0
                )
        
        print("✅ 发布任务已完成！")
        return True
    except Exception as e:
        print(f"❌ 发布视频出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="命令行视频发布脚本")
    parser.add_argument('--file', type=str, required=True, help='视频文件路径')
    parser.add_argument('--account', type=str, required=True, help='账号名称')
    parser.add_argument('--title', type=str, required=True, help='视频标题')
    parser.add_argument('--platform', type=int, default=3, 
                        help='发布平台 (1=小红书, 2=视频号, 3=抖音, 4=快手)，默认抖音')
    parser.add_argument('--timer', action='store_true', help='启用定时发布 (默认立即发布)')
    
    args = parser.parse_args()
    
    # 检查视频文件是否存在
    if not os.path.exists(args.file):
        print(f"❌ 视频文件不存在: {args.file}")
        return
    
    # 获取账号信息
    print(f"🔍 查找账号: {args.account}")
    account_info = get_account_by_name(args.account)
    if not account_info:
        print(f"❌ 未找到账号或账号不可用: {args.account}")
        return
    
    print(f"✅ 找到账号: {args.account}")
    
    # 发布视频
    enable_timer = 1 if args.timer else 0
    success = publish_video_direct(
        file_path=args.file,
        account_list=[account_info["filePath"]],
        title=args.title,
        platform_type=args.platform,
        enable_timer=enable_timer
    )
    
    if success:
        print("\n🎉 所有操作完成！")
    else:
        print("\n❌ 操作失败")


if __name__ == "__main__":
    main()
