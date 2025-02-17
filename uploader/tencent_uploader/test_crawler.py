"""
测试视频号内容抓取功能
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT_DIR))

from uploader.tencent_uploader.modules.content_crawler import VideoContentCrawler
from utils.social_media_db import SocialMediaDB
from utils.video_content_db import VideoContentDB
from utils.log import tencent_logger
from typing import Dict, Any, Optional, List

async def main() -> None:
    # 从数据库获取向阳也有米账号信息
    db = SocialMediaDB()
    video_db = VideoContentDB()
    try:
        accounts: List[Dict[str, Any]] = db.get_all_accounts("tencent")
        target_account: Optional[Dict[str, Any]] = None
        
        # 查找目标账号
        for account in accounts:
            if account.get('nickname') == "向阳也有米":
                target_account = account
                break
        
        if not target_account:
            tencent_logger.error("未找到向阳也有米账号")
            return
            
        # 获取最新的cookie文件路径
        cookie_paths: List[str] = target_account.get('cookie_paths', [])
        if not cookie_paths:
            tencent_logger.error("账号没有可用的cookie文件")
            return
            
        cookie_file: str = cookie_paths[0]  # 使用最新的cookie文件
        tencent_logger.info(f"使用cookie文件: {cookie_file}")
        
        # 获取已爬取的视频数量
        video_count = video_db.get_video_count(target_account['id'])
        tencent_logger.info(f"账号 {target_account['nickname']} 已保存 {video_count} 个视频")
        
        print(f"开始抓取 {target_account['nickname']} 的视频号内容...")
        async with VideoContentCrawler(
            account_file=cookie_file,
            account_id=target_account['id'],
            headless=False,  # 显示浏览器窗口，方便调试
            save_thumb_as_base64=True,  # 保存封面图片
            min_delay=3.0,  # 最小延迟3秒
            max_delay=7.0,  # 最大延迟7秒
            max_retries=3,  # 最大重试次数
            reverse=True  # 倒序爬取，优先获取最新内容
        ) as crawler:
            # 获取所有未爬取的视频
            videos = await crawler.get_video_list(max_pages=-1)
            
            # 打印结果
            print(f"\n本次新增 {len(videos)} 个视频:")
            print("-" * 50)
            
            for idx, video in enumerate(videos, 1):
                print(f"\n视频 {idx}:")
                print(f"标题: {video['title']}")
                print(f"标签: #{' #'.join(video['tags'])}" if video['tags'] else "标签: 无")
                print(f"艾特用户: @{' @'.join(video['mentions'])}" if video['mentions'] else "艾特用户: 无")
                print(f"发布时间: {video['publish_time']}")
                print(f"状态: {video['status']}")
                print(f"播放量: {video['stats']['plays']}")
                print(f"点赞数: {video['stats']['likes']}")
                print(f"评论数: {video['stats']['comments']}")
                print(f"分享数: {video['stats']['shares']}")
                print(f"封面图片: {'已保存为base64' if video['thumb_base64'] else '获取失败'}")
                print("-" * 50)
            
            # 保存结果到文件
            if videos:
                output_file = Path("data/video_list.json")
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(videos, f, ensure_ascii=False, indent=2)
                    
                print(f"\n结果已保存到: {output_file}")
            
            # 显示最终统计
            final_count = video_db.get_video_count(target_account['id'])
            print(f"\n统计信息:")
            print("-" * 50)
            print(f"原有视频数: {video_count}")
            print(f"新增视频数: {len(videos)}")
            print(f"当前总数: {final_count}")
            print(f"预计页数: {(final_count + crawler.VIDEOS_PER_PAGE - 1) // crawler.VIDEOS_PER_PAGE}")
            
    finally:
        db.close()
        video_db.close()

if __name__ == "__main__":
    asyncio.run(main()) 