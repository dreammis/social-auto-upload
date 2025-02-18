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
from uploader.tencent_uploader.modules.account import cookie_auth
from utils.social_media_db import SocialMediaDB
from utils.video_content_db import VideoContentDB
from utils.log import tencent_logger
from typing import Dict, Any, Optional, List

async def main() -> None:
    # 从数据库获取所有腾讯视频号账号信息
    db = SocialMediaDB()
    video_db = VideoContentDB()
    crawler = None  # 初始化crawler变量
    
    try:
        tencent_logger.info("开始获取账号信息...")
        accounts: List[Dict[str, Any]] = db.get_all_accounts("tencent")
        
        if not accounts:
            tencent_logger.error("未找到任何腾讯视频号账号")
            return
            
        tencent_logger.info(f"找到 {len(accounts)} 个腾讯视频号账号")
        
        # 遍历所有账号
        for account in accounts:
            try:
                tencent_logger.info(f"\n=== 开始处理账号: {account['nickname']} ===")
                
                # 获取最新的cookie文件路径
                cookie_paths: List[str] = account.get('cookie_paths', [])
                if not cookie_paths:
                    tencent_logger.error(f"账号 {account['nickname']} 没有可用的cookie文件，跳过")
                    continue
                    
                cookie_file: str = cookie_paths[0]  # 使用最新的cookie文件
                tencent_logger.info(f"使用cookie文件: {cookie_file}")
                
                # 检查账号上次验证时间
                from datetime import datetime, timedelta
                
                last_check = db.get_account_verification_time("tencent", account['nickname'])
                current_time = datetime.now()
                
                if last_check:
                    # 将字符串转换为datetime对象
                    last_check_time = datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S.%f")
                    time_diff = current_time - last_check_time
                    
                    if time_diff <= timedelta(hours=1):
                        tencent_logger.info(f"账号在1小时内已验证过 (上次验证时间: {last_check}), 跳过cookie验证")
                        cookie_valid = True
                    else:
                        tencent_logger.info(f"距离上次验证已超过1小时 (上次验证时间: {last_check}), 需要重新验证cookie")
                        cookie_valid = False
                else:
                    tencent_logger.info("账号未记录验证时间,需要验证cookie")
                    cookie_valid = False
                    
                # 验证cookie是否有效
                if not cookie_valid:
                    tencent_logger.info("开始验证cookie...")
                    try:
                        await cookie_auth(cookie_file)
                        tencent_logger.info("cookie验证通过")
                    except Exception as e:
                        tencent_logger.error(f"账号 {account['nickname']} cookie验证失败: {str(e)}")
                        continue
                else:
                    tencent_logger.info("cookie已验证通过，跳过验证")
                
                # 获取已爬取的视频数量
                video_count = video_db.get_video_count(account['id'])
                tencent_logger.info(f"账号 {account['nickname']} 已保存 {video_count} 个视频")
                
                tencent_logger.info("开始初始化爬虫...")
                try:
                    tencent_logger.info("=== 进入async with块 ===")
                    async with VideoContentCrawler(
                        account_file=cookie_file,
                        account_id=account['id'],
                        headless=False,  # 显示浏览器窗口，方便调试
                        save_thumb_as_base64=True,  # 保存封面图片
                        min_delay=3.0,  # 最小延迟3秒
                        max_delay=7.0,  # 最大延迟7秒
                        max_retries=3,  # 最大重试次数
                        reverse=True  # 倒序爬取，优先获取最新内容
                    ) as crawler:
                        tencent_logger.info("=== async with块初始化完成 ===")
                        tencent_logger.info("开始调用get_video_list方法...")
                        try:
                            # 获取所有未爬取的视频
                            tencent_logger.info("准备调用get_video_list...")
                            videos = await crawler.get_video_list(max_pages=-1)
                            tencent_logger.info("get_video_list方法调用完成")
                        except Exception as e:
                            tencent_logger.error(f"get_video_list方法执行失败: {str(e)}")
                            import traceback
                            tencent_logger.error(f"get_video_list错误堆栈:\n{traceback.format_exc()}")
                            continue  # 继续处理下一个账号
                        
                        tencent_logger.info("=== 开始处理get_video_list结果 ===")
                        
                        # 打印结果
                        tencent_logger.info(f"\n账号 {account['nickname']} 本次新增 {len(videos)} 个视频:")
                        tencent_logger.info("-" * 50)
                        
                        for idx, video in enumerate(videos, 1):
                            tencent_logger.info(f"\n视频 {idx}:")
                            tencent_logger.info(f"标题: {video['title']}")
                            tencent_logger.info(f"标签: #{' #'.join(video['tags'])}" if video['tags'] else "标签: 无")
                            tencent_logger.info(f"艾特用户: @{' @'.join(video['mentions'])}" if video['mentions'] else "艾特用户: 无")
                            tencent_logger.info(f"发布时间: {video['publish_time']}")
                            tencent_logger.info(f"状态: {video['status']}")
                            tencent_logger.info(f"播放量: {video['stats']['plays']}")
                            tencent_logger.info(f"点赞数: {video['stats']['likes']}")
                            tencent_logger.info(f"评论数: {video['stats']['comments']}")
                            tencent_logger.info(f"分享数: {video['stats']['shares']}")
                            tencent_logger.info(f"封面图片: {'已保存为base64' if video['thumb_base64'] else '获取失败'}")
                            tencent_logger.info("-" * 50)
                        
                        # 保存结果到文件
                        if videos:
                            output_file = Path(f"data/video_list_{account['nickname']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                            output_file.parent.mkdir(parents=True, exist_ok=True)
                            
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(videos, f, ensure_ascii=False, indent=2)
                                
                            tencent_logger.info(f"\n结果已保存到: {output_file}")
                        
                        # 显示最终统计
                        final_count = video_db.get_video_count(account['id'])
                        tencent_logger.info(f"\n账号 {account['nickname']} 统计信息:")
                        tencent_logger.info("-" * 50)
                        tencent_logger.info(f"原有视频数: {video_count}")
                        tencent_logger.info(f"新增视频数: {len(videos)}")
                        tencent_logger.info(f"当前总数: {final_count}")
                        tencent_logger.info(f"预计页数: {(final_count + crawler.VIDEOS_PER_PAGE - 1) // crawler.VIDEOS_PER_PAGE}")
                        
                except Exception as e:
                    tencent_logger.error(f"账号 {account['nickname']} 爬虫初始化或执行过程中出错: {str(e)}")
                    import traceback
                    tencent_logger.error(f"错误堆栈:\n{traceback.format_exc()}")
                    continue  # 继续处理下一个账号
                    
            except Exception as e:
                tencent_logger.error(f"处理账号 {account['nickname']} 时出现错误: {str(e)}")
                import traceback
                tencent_logger.error(f"错误堆栈:\n{traceback.format_exc()}")
                continue  # 继续处理下一个账号
                
    except Exception as e:
        tencent_logger.error(f"爬取过程中出现错误: {str(e)}")
        import traceback
        tencent_logger.error(f"错误堆栈:\n{traceback.format_exc()}")
    finally:
        # 确保资源正确关闭
        tencent_logger.info("开始清理资源...")
        if crawler:
            try:
                tencent_logger.info("关闭爬虫资源...")
                await crawler.close()
                tencent_logger.info("爬虫资源已关闭")
            except Exception as e:
                tencent_logger.error(f"关闭爬虫资源时出错: {str(e)}")
        
        tencent_logger.info("关闭数据库连接...")
        try:
            db.close()
            video_db.close()
            tencent_logger.info("数据库连接已关闭")
        except Exception as e:
            tencent_logger.error(f"关闭数据库连接时出错: {str(e)}")

if __name__ == "__main__":
    tencent_logger.info("启动视频号内容抓取程序...")
    asyncio.run(main()) 