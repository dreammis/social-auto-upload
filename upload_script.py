#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行视频上传脚本

示例:
# 基础用法（立即发布）
python upload_script.py --file "test.mp4" --account "我的账号" --title "测试视频"

# 定时发布（指定 daily-times 即可启用）
python upload_script.py --file "test.mp4" --account "我的账号" --title "测试视频" --daily-times 10:00 14:00

# 抖音带货视频
python upload_script.py --file "test.mp4" --account "我的账号" --title "测试视频" --platform 3 --product-link "https://..." --product-title "商品名称"

# 视频号保存草稿
python upload_script.py --file "test.mp4" --account "我的账号" --title "测试视频" --platform 2 --draft
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


def publish_video_direct(file_path, account_list, title, platform_type=3, enable_timer=0, 
                          tags=None, category=None, thumbnail='', product_link='', product_title='',
                          is_draft=False, declaration_type=None, videos_per_day=1, daily_times=None, start_days=0):
    """直接调用内部函数发布视频"""
    if tags is None:
        tags = []
    if daily_times is None:
        daily_times = ["10:00"]
    
    try:
        print(f"📤 正在发布视频...")
        print(f"   平台: {platform_type} (1=小红书, 2=视频号, 3=抖音, 4=快手)")
        print(f"   标题: {title}")
        print(f"   文件: {file_path}")
        print(f"   账号: {account_list}")
        print(f"   标签: {tags}")
        print(f"   分类: {category}")
        
        declaration_info = None
        if declaration_type:
            declaration_info = {
                "declaration_type": declaration_type,
                "declaration_location": [],
                "declaration_date": ""
            }
        
        match platform_type:
            case 1:
                post_video_xhs(
                    title=title,
                    files=[file_path],
                    tags=tags,
                    account_file=account_list,
                    category=category,
                    enableTimer=enable_timer,
                    videos_per_day=videos_per_day,
                    daily_times=daily_times,
                    start_days=start_days
                )
            case 2:
                post_video_tencent(
                    title=title,
                    files=[file_path],
                    tags=tags,
                    account_file=account_list,
                    category=category,
                    enableTimer=enable_timer,
                    videos_per_day=videos_per_day,
                    daily_times=daily_times,
                    start_days=start_days,
                    is_draft=is_draft
                )
            case 3:
                post_video_DouYin(
                    title=title,
                    files=[file_path],
                    tags=tags,
                    account_file=account_list,
                    category=category,
                    enableTimer=enable_timer,
                    videos_per_day=videos_per_day,
                    daily_times=daily_times,
                    start_days=start_days,
                    thumbnail_path=thumbnail,
                    productLink=product_link,
                    productTitle=product_title,
                    declaration_info=declaration_info
                )
            case 4:
                post_video_ks(
                    title=title,
                    files=[file_path],
                    tags=tags,
                    account_file=account_list,
                    category=category,
                    enableTimer=enable_timer,
                    videos_per_day=videos_per_day,
                    daily_times=daily_times,
                    start_days=start_days
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
    parser.add_argument('--platform', type=int, default=3, help='发布平台 (1=小红书, 2=视频号, 3=抖音, 4=快手)，默认抖音')
    parser.add_argument('--tags', type=str, nargs='*', default=[], help='视频标签列表，如: --tags 标签1 标签2')
    parser.add_argument('--category', type=int, default=None, help='视频分类ID')
    parser.add_argument('--thumbnail', type=str, default='', help='缩略图路径（抖音专用）')
    parser.add_argument('--product-link', type=str, default='', help='商品链接（抖音专用）')
    parser.add_argument('--product-title', type=str, default='', help='商品标题（抖音专用）')
    parser.add_argument('--declaration', type=str, default='内容由AI生成', help='声明类型（抖音专用），可选: 内容由AI生成, 内容取材网络, 可能引人不适, 虚构演绎仅供娱乐, 危险行为请勿模仿')
    parser.add_argument('--draft', action='store_true', help='保存为草稿（视频号专用）')
    parser.add_argument('--daily-times', type=str, nargs='*', default=None, help='每日发布时间列表（启用定时发布），如: --daily-times 10:00 14:00 18:00')
    parser.add_argument('--videos-per-day', type=int, default=1, help='每天发布视频数量')
    parser.add_argument('--start-days', type=int, default=0, help='定时发布开始天数，')
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
    enable_timer = 1 if args.daily_times else 0
    daily_times = args.daily_times if args.daily_times else ["10:00"]
    success = publish_video_direct(
        file_path=args.file,
        account_list=[account_info["filePath"]],
        title=args.title,
        platform_type=args.platform,
        enable_timer=enable_timer,
        tags=args.tags,
        category=args.category,
        thumbnail=args.thumbnail,
        product_link=args.product_link,
        product_title=args.product_title,
        is_draft=args.draft,
        declaration_type=args.declaration,
        videos_per_day=args.videos_per_day,
        daily_times=daily_times,
        start_days=args.start_days
    )
    
    if success:
        print("\n🎉 所有操作完成！")
    else:
        print("\n❌ 操作失败")


if __name__ == "__main__":
    main()
