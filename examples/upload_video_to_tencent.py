import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))

from conf import BASE_DIR
from uploader.tencent_uploader import weixin_setup, TencentVideo
from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day
from utils.log import tencent_logger


def load_video_info(json_path: Path) -> dict:
    """
    加载视频信息配置文件
    
    Args:
        json_path: json文件路径
    
    Returns:
        包含腾讯视频信息的字典
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 遍历配置数组
            for platform_config in data:
                # 检查是否存在tencent平台的配置
                if isinstance(platform_config, dict) and 'tencent' in platform_config:
                    config = platform_config['tencent']
                    # 处理发布时间
                    if 'publish_date' in config:
                        config['publish_date'] = datetime.strptime(
                            config['publish_date'], 
                            '%Y-%m-%d %H:%M:%S'
                        )
                    return config
            
            tencent_logger.warning(f"JSON文件 {json_path} 中未找到腾讯平台配置")
            return {}
    except Exception as e:
        tencent_logger.error(f"读取配置文件失败: {str(e)}")
        return {}


def find_video_assets(folder_path: Path) -> List[Tuple[Path, Optional[Path], Optional[Path]]]:
    """
    在指定文件夹中查找视频及其相关资源
    
    支持的文件结构：
    1. 直接在文件夹下：
       folder/
           ├── video.mp4
           ├── cover.jpg
           └── info.json
           
    2. 在子文件夹中：
       folder/
           └── video1/
               ├── video.mp4
               ├── cover.jpg
               └── info.json
    
    Args:
        folder_path: 视频文件夹路径
    
    Returns:
        包含(视频路径, 封面路径, 配置文件路径)的列表
    """
    video_assets = []
    
    # 首先检查主文件夹中的文件
    video_files = list(folder_path.glob("*.mp4"))
    cover_files = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.png"))
    json_files = list(folder_path.glob("*.json"))
    
    if video_files:  # 如果在主文件夹中找到视频文件
        video_path = video_files[0]
        cover_path = cover_files[0] if cover_files else None
        json_path = json_files[0] if json_files else None
        video_assets.append((video_path, cover_path, json_path))
        return video_assets
    
    # 如果主文件夹中没有找到视频，则检查子文件夹
    for item in folder_path.iterdir():
        if item.is_dir():
            # 在子文件夹中查找文件
            sub_video_files = list(item.glob("*.mp4"))
            sub_cover_files = list(item.glob("*.jpg")) + list(item.glob("*.png"))
            sub_json_files = list(item.glob("*.json"))
            
            if sub_video_files:  # 如果找到视频文件
                video_path = sub_video_files[0]
                cover_path = sub_cover_files[0] if sub_cover_files else None
                json_path = sub_json_files[0] if sub_json_files else None
                video_assets.append((video_path, cover_path, json_path))
    
    if not video_assets:
        tencent_logger.warning(f"在目录 {folder_path} 及其子目录中未找到任何视频文件")
    
    return video_assets


async def process_video(video_path: Path, cover_path: Path, json_path: Path, account_file: Path):
    """
    处理单个视频的上传
    """
    try:
        # 加载视频信息
        video_info = load_video_info(json_path) if json_path else {}
        
        # 获取视频信息，如果json中没有则使用默认值
        title = video_info.get('title', video_path.stem)
        tags = video_info.get('tags', [])
        friends = video_info.get('friends', [])
        publish_date = video_info.get('publish_date', datetime.now())
        category = TencentZoneTypes.EMOTION.value
        
        # 打印当前处理的视频信息
        tencent_logger.info(f"正在处理视频: {video_path.name}")
        tencent_logger.info(f"标题: {title}")
        tencent_logger.info(f"标签: {tags}")
        tencent_logger.info(f"好友标记: {friends}")
        tencent_logger.info(f"发布时间: {publish_date}")
        if cover_path:
            tencent_logger.info(f"封面: {cover_path.name}")
        
        # 创建上传实例
        app = TencentVideo(
            title=title,
            file_path=str(video_path),
            tags=tags,
            publish_date=publish_date,
            account_files=[str(account_file)],  # 每个实例只使用一个账号
            category=category,
            cover_path=str(cover_path) if cover_path else None,
            friends=friends
        )
        
        # 执行上传
        await app.main()
        
    except Exception as e:
        tencent_logger.error(f"处理视频 {video_path} 时出错: {str(e)}")


async def single_thread_upload(account_name: str = None):
    """
    单线程上传视频
    
    Args:
        account_name: 账号名称，用于定位cookie文件。如果为None，则尝试使用目录下的第一个cookie文件
    """
    # 设置基础路径
    videos_folder = Path(r"F:\向阳也有米\24版本\12月\1125-19-教人7")
    cookies_folder = Path(BASE_DIR) / "cookies" / "tencent_uploader"
    
    # 根据account_name获取cookie文件
    if account_name:
        account_file = cookies_folder / f"{account_name}.json"
        if not account_file.exists():
            tencent_logger.error(f"未找到账号 {account_name} 的cookie文件")
            return
    else:
        # 如果没有指定账号，尝试使用目录下的第一个cookie文件
        cookie_files = list(cookies_folder.glob("*.json"))
        if not cookie_files:
            tencent_logger.error("未找到任何cookie文件")
            return
        account_file = cookie_files[0]
        account_name = account_file.stem
        tencent_logger.info(f"使用默认账号: {account_name}")
    
    # 验证cookie
    if not await weixin_setup(account_file, handle=True):
        tencent_logger.error("Cookie设置失败")
        return
    
    # 获取所有视频资源
    video_assets = find_video_assets(videos_folder)
    if not video_assets:
        tencent_logger.warning("未找到任何视频资源")
        return
    
    # 顺序处理每个视频
    for video_path, cover_path, json_path in video_assets:
        await process_video(video_path, cover_path, json_path, account_file)


async def multi_thread_upload():
    """
    多线程上传视频 - 每个账号一个浏览器实例并发上传
    """
    # 设置基础路径
    cookies_folder = Path(BASE_DIR) / "cookies" / "tencent_uploader"
    # 获取所有账号文件
    account_files = list(cookies_folder.glob("*.json"))
    if not account_files:
        tencent_logger.error("未找到任何账号文件")
        return
    videos_folder = Path(r"F:\向阳也有米\24版本\12月\1125-19-教人7")
    # 获取所有视频资源
    video_assets = find_video_assets(videos_folder)
    if not video_assets:
        tencent_logger.warning("未找到任何视频资源")
        return
    
    # 验证所有账号的cookie
    valid_accounts = []
    for account_file in account_files:
        if await weixin_setup(str(account_file), handle=True):
            valid_accounts.append(account_file)
        else:
            tencent_logger.error(f"账号 {account_file.stem} cookie无效，已跳过")
    
    if not valid_accounts:
        tencent_logger.error("没有可用的账号")
        return
    
    # 创建上传任务
    upload_tasks = []
    for i, video_asset in enumerate(video_assets):
        video_path, cover_path, json_path = video_asset
        
        # 加载视频信息
        video_info = load_video_info(json_path) if json_path else {}
        title = video_info.get('title', video_path.stem)
        tags = video_info.get('tags', [])
        friends = video_info.get('friends', [])
        publish_date = video_info.get('publish_date', datetime.now())
        category = TencentZoneTypes.EMOTION.value
        
        # 创建上传实例 - 传入所有有效账号
        app = TencentVideo(
            title=title,
            file_path=str(video_path),
            tags=tags,
            publish_date=publish_date,
            account_files=[str(account) for account in valid_accounts],  # 传入所有有效账号
            category=category,
            cover_path=str(cover_path) if cover_path else None,
            friends=friends
        )
        
        # 添加到任务列表
        upload_tasks.append(app.main())
    
    # 并发执行所有上传任务
    tencent_logger.info(f"开始并发上传 {len(upload_tasks)} 个视频，使用 {len(valid_accounts)} 个账号")
    await asyncio.gather(*upload_tasks)


if __name__ == '__main__':
    asyncio.run(single_thread_upload(account_name="向阳很有米"))
