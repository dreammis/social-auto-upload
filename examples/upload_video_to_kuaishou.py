# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 获取项目根目录的绝对路径
BASE_DIR = Path(os.path.dirname(os.path.dirname(__file__)))
# 添加项目根目录到 Python 路径
sys.path.append(str(BASE_DIR))

from uploader.ks_uploader.modules.account import account_manager
from uploader.ks_uploader.modules.video import KSVideoUploader, KSBatchUploader
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags
from utils.log import kuaishou_logger
from utils.social_media_db import SocialMediaDB
from utils.playwright_helper import PlaywrightHelper

def find_video_and_info(folder_path: Path) -> tuple[Path, dict]:
    """
    查找视频文件和对应的info.json信息
    """
    # 查找视频文件
    video_files = list(folder_path.glob("*.mp4"))
    if not video_files:
        video_files = list(folder_path.glob("*.mov"))
    if not video_files:
        return None, None

    # 读取info.json
    info_file = folder_path / "info.json"
    if not info_file.exists():
        return None, None

    try:
        with open(info_file, 'r', encoding='utf-8') as f:
            info_data = json.load(f)
            if isinstance(info_data, list):
                info_data = info_data[0]  # 获取第一个元素
            if 'kuaishou' not in info_data:
                return None, None
            
            # 查找封面图片
            # 支持的图片格式
            image_extensions = ['.jpg', '.jpeg', '.png']
            cover_file = None
            
            # 首先查找与视频同名的图片
            video_stem = video_files[0].stem
            kuaishou_logger.info(f"正在查找与视频同名的封面图片: {video_stem}")
            for ext in image_extensions:
                potential_cover = folder_path / f"{video_stem}{ext}"
                if potential_cover.exists():
                    cover_file = potential_cover
                    kuaishou_logger.success(f"找到同名封面图片: {cover_file}")
                    break
            
            # 如果没找到同名图片，查找文件夹中的第一张图片
            if not cover_file:
                kuaishou_logger.info("未找到同名封面图片，尝试查找文件夹中的其他图片")
                for ext in image_extensions:
                    image_files = list(folder_path.glob(f"*{ext}"))
                    if image_files:
                        cover_file = image_files[0]
                        kuaishou_logger.success(f"找到封面图片: {cover_file}")
                        break
            
            # 如果找到了封面图片
            if cover_file:
                info_data['kuaishou']['cover_file'] = str(cover_file)
                kuaishou_logger.info(f"设置封面图路径: {cover_file}")
            else:
                info_data['kuaishou']['cover_file'] = None
                kuaishou_logger.warning("未找到任何可用的封面图片")
                
            return video_files[0], info_data['kuaishou']
    except Exception as e:
        kuaishou_logger.error(f"读取info.json失败: {str(e)}")
        return None, None

async def upload_videos(video_files: List[Path], account_file: Path, nickname: str) -> Dict[str, Any]:
    """上传视频
    
    Args:
        video_files: 视频文件列表
        account_file: 账号cookie文件路径
        nickname: 账号昵称
        
    Returns:
        Dict[str, Any]: 上传结果
    """
    try:
        kuaishou_logger.info(f"开始上传视频 - 账号: {nickname}")
        kuaishou_logger.info(f"视频文件数量: {len(video_files)}")
        kuaishou_logger.info(f"Cookie文件: {account_file}")
        
        # 初始化数据库
        db = SocialMediaDB()
        try:
            # 检查cookie最后验证时间
            last_check = db.get_account_verification_time("kuaishou", nickname)
            if last_check:
                # 将字符串时间转换为datetime对象
                if isinstance(last_check, str):
                    last_check = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                time_diff = (datetime.now() - last_check).total_seconds() / 3600  # 转换为小时
                if time_diff < 3:
                    kuaishou_logger.info(f"Cookie在3小时内已验证过 (距上次验证: {time_diff:.1f}小时), 跳过验证")
                    result = {'success': True, 'username': nickname}
                else:
                    kuaishou_logger.info(f"Cookie最后验证时间: {last_check.strftime('%Y-%m-%d %H:%M:%S')} (已过期)")
                    # 验证账号
                    kuaishou_logger.info("正在验证账号...")
                    result = await account_manager.setup_cookie(str(account_file), expected_username=nickname)
            else:
                # 首次验证
                kuaishou_logger.info("未找到验证记录，进行首次验证")
                result = await account_manager.setup_cookie(str(account_file), expected_username=nickname)
        finally:
            db.close()

        if not result['success']:
            error_msg = result.get('message', '未知错误')
            kuaishou_logger.error(f"Cookie设置失败: {error_msg}")
            if 'error' in result:
                kuaishou_logger.error(f"错误详情: {result['error']}")
            return {
                'success': False,
                'error': error_msg
            }
        
        kuaishou_logger.success("账号验证成功！")
        kuaishou_logger.info(f"当前登录用户: {result.get('username', nickname)}")
        if 'expires_at' in result:
            expires_time = datetime.fromtimestamp(result['expires_at']).strftime('%Y-%m-%d %H:%M:%S')
            kuaishou_logger.info(f"Cookie有效期至: {expires_time}")

        # 生成发布时间
        file_num = len(video_files)
        publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
        kuaishou_logger.info(f"已生成发布时间计划，共 {file_num} 个时间点")
        for i, dt in enumerate(publish_datetimes, 1):
            kuaishou_logger.debug(f"视频 {i}: 计划发布时间 = {dt.strftime('%Y-%m-%d %H:%M:%S')}")

        if len(video_files) == 1:
            # 单个视频上传
            file = video_files[0]
            title, tags, mentions = get_title_and_hashtags(str(file))
            kuaishou_logger.info(f"准备上传视频: {title}")
            kuaishou_logger.info(f"文件路径: {file}")
            kuaishou_logger.info(f"标签: {tags}")
            if mentions:
                kuaishou_logger.info(f"提及用户: @{', @'.join(mentions)}")
            kuaishou_logger.info(f"计划发布时间: {publish_datetimes[0].strftime('%Y-%m-%d %H:%M:%S')}")

            # 获取视频信息
            video_info = None
            if file.parent.exists():
                _, video_info = find_video_and_info(file.parent)

            # 创建上传器
            publish_date = datetime.strptime(video_info['publish_date'], '%Y-%m-%d %H:%M:%S') if 'publish_date' in video_info else None
            
            # 检查封面文件路径
            cover_file = video_info.get('cover_file')
            if cover_file:
                kuaishou_logger.info(f"使用封面文件: {cover_file}")
            else:
                kuaishou_logger.warning("未设置封面文件")
            
            uploader = KSVideoUploader(
                title=title,
                file_path=str(file),
                tags=tags,
                mentions=mentions,
                publish_date=publish_date,
                account_file=str(account_file),
                cover_file=cover_file  # 传递封面文件路径
            )
            
            success = await uploader.start()
            results = {
                'success': success,
                'total': 1,
                'failed': 0 if success else 1,
                'results': {
                    title: {
                        'success': success,
                        'timestamp': datetime.now().isoformat(),
                        'file_path': str(file)
                    }
                }
            }
        else:
            # 批量上传
            uploaders = []
            for index, file in enumerate(video_files):
                title, tags, mentions = get_title_and_hashtags(str(file))
                kuaishou_logger.info(f"准备上传视频 {index + 1}/{file_num}")
                kuaishou_logger.info(f"文件路径: {file}")
                kuaishou_logger.info(f"标题: {title}")
                kuaishou_logger.info(f"标签: {tags}")
                if mentions:
                    kuaishou_logger.info(f"提及用户: @{', @'.join(mentions)}")
                kuaishou_logger.info(f"计划发布时间: {publish_datetimes[index].strftime('%Y-%m-%d %H:%M:%S')}")

                # 获取视频信息
                video_info = None
                if file.parent.exists():
                    _, video_info = find_video_and_info(file.parent)

                uploader = KSVideoUploader(
                    title=title,
                    file_path=str(file),
                    tags=tags,
                    mentions=mentions,
                    publish_date=publish_datetimes[index],
                    account_file=str(account_file),
                    cover_file=video_info.get('cover_file') if video_info else None  # 添加封面图路径
                )
                uploaders.append(uploader)

            kuaishou_logger.info("初始化批量上传器...")
            batch_uploader = KSBatchUploader(max_concurrent=2)
            kuaishou_logger.info("开始执行批量上传...")
            results = await batch_uploader.batch_upload(uploaders)

        # 处理上传结果
        if results.get('success', False):
            kuaishou_logger.success("上传完成！")
            kuaishou_logger.info(f"总数: {results.get('total', 0)}")
            kuaishou_logger.info(f"成功: {results.get('success', 0)}")
            kuaishou_logger.info(f"失败: {results.get('failed', 0)}")
            
            # 记录详细的上传结果
            if 'results' in results:
                for title, info in results['results'].items():
                    if info.get('success'):
                        kuaishou_logger.success(f"视频 '{title}' 上传成功")
                    else:
                        kuaishou_logger.error(f"视频 '{title}' 上传失败")
                        if 'error' in info:
                            kuaishou_logger.error(f"错误信息: {info['error']}")

        return results

    except Exception as e:
        kuaishou_logger.error(f"上传视频失败: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

async def main():
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
        
        if not result['success']:
            kuaishou_logger.error(f"Cookie设置失败: {result['message']}")
            if 'error' in result:
                kuaishou_logger.error(f"错误详情: {result['error']}")
            sys.exit(1)

        # 获取视频文件和信息
        videos_folder = Path(r"F:\向阳也有米\24版本\12月\1125-19-教人7")
        video_file, video_info = find_video_and_info(videos_folder)
        
        if not video_file or not video_info:
            kuaishou_logger.error("未找到视频文件或info.json信息不完整")
            sys.exit(1)

        # 创建上传器
        publish_date = datetime.strptime(video_info['publish_date'], '%Y-%m-%d %H:%M:%S') if 'publish_date' in video_info else None
        
        # 检查封面文件路径
        cover_file = video_info.get('cover_file')
        if cover_file:
            kuaishou_logger.info(f"使用封面文件: {cover_file}")
        else:
            kuaishou_logger.warning("未设置封面文件")
            
        uploader = KSVideoUploader(
            title=video_info['title'],
            file_path=str(video_file),
            tags=video_info['tags'],
            mentions=video_info.get('mentions', []),
            publish_date=publish_date,
            account_file=account_file,
            cover_file=cover_file  # 传递封面文件路径
        )

        # 开始上传
        kuaishou_logger.info(f"开始上传视频: {video_info['title']}")
        if await uploader.start():
            kuaishou_logger.success("视频上传成功！")
        else:
            kuaishou_logger.error("视频上传失败！")
            sys.exit(1)

    except Exception as e:
        kuaishou_logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)
    finally:
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    asyncio.run(main())
