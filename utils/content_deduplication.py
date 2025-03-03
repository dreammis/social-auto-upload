"""
内容去重工具
专注于视频内容的多维度去重判断
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ContentDeduplication:
    """内容去重工具类"""
    
    @staticmethod
    def is_content_duplicate(
        new_content: Dict[str, Any],
        existing_content: Optional[Dict[str, Any]]
    ) -> bool:
        """
        判断内容是否重复
        
        Args:
            new_content: 新抓取的内容，包含:
                - account_id: 账号ID
                - title: 标题
                - tags: 标签列表
                - mentions: @用户列表
            existing_content: 数据库中已存在的内容，包含相同的字段
                如果为None，表示数据库中不存在该内容
                
        Returns:
            bool: 是否重复
        """
        # 如果数据库中不存在，则一定不重复
        if not existing_content:
            return False
            
        try:
            # 1. 检查账号ID
            if new_content['account_id'] != existing_content['account_id']:
                return False
                
            # 2. 检查标题、标签列表、@用户列表和发布时间是否都匹配
            # 将标题、标签、@用户都转换为小写进行比较，避免大小写差异
            new_title = new_content['title'].lower().strip()
            existing_title = existing_content['title'].lower().strip()
            
            # 检查发布时间
            new_publish_time = new_content.get('publish_time', '').strip()
            existing_publish_time = existing_content.get('publish_time', '').strip()
            
            # 确保 tags 和 mentions 字段存在且为列表
            new_tags = set(tag.lower().strip() for tag in (new_content.get('tags') or []))
            existing_tags = set(tag.lower().strip() for tag in (existing_content.get('tags') or []))
            
            new_mentions = set(mention.lower().strip() for mention in (new_content.get('mentions') or []))
            existing_mentions = set(mention.lower().strip() for mention in (existing_content.get('mentions') or []))
            
            # 所有字段都必须匹配
            title_match = new_title == existing_title
            publish_time_match = new_publish_time == existing_publish_time
            tags_match = new_tags == existing_tags
            mentions_match = new_mentions == existing_mentions
            
            is_duplicate = title_match and publish_time_match and tags_match and mentions_match
            
            if is_duplicate:
                logger.info(f"检测到完全重复内容:")
                logger.info(f"- 标题匹配: {new_title}")
                logger.info(f"- 发布时间匹配: {new_publish_time}")
                logger.info(f"- 标签匹配: {new_tags}")
                logger.info(f"- @用户匹配: {new_mentions}")
            else:
                # 记录不匹配的原因
                if not title_match:
                    logger.info(f"标题不匹配: 新标题[{new_title}] != 已存在标题[{existing_title}]")
                if not publish_time_match:
                    logger.info(f"发布时间不匹配: 新发布时间[{new_publish_time}] != 已存在发布时间[{existing_publish_time}]")
                if not tags_match:
                    logger.info(f"标签不匹配: 新标签{new_tags} != 已存在标签{existing_tags}")
                if not mentions_match:
                    logger.info(f"@用户不匹配: 新@用户{new_mentions} != 已存在@用户{existing_mentions}")
                    
            logger.debug(f"新内容: {new_content}")
            logger.debug(f"已存在内容: {existing_content}")
            
            return is_duplicate
            
        except KeyError as e:
            logger.error(f"内容格式错误，缺少必要字段: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"去重判断过程出错: {str(e)}")
            return False
    
    @staticmethod
    def should_update_content(
        new_content: Dict[str, Any],
        existing_content: Dict[str, Any]
    ) -> bool:
        """
        判断是否需要更新内容
        
        Args:
            new_content: 新抓取的内容
            existing_content: 数据库中已存在的内容
            
        Returns:
            bool: 是否需要更新
        """
        try:
            # 检查统计数据是否有变化
            if 'stats' in new_content and 'stats' in existing_content:
                new_stats = new_content['stats']
                existing_stats = existing_content['stats']
                
                # 任何一个统计数据变化，都需要更新
                if (new_stats.get('plays', 0) != existing_stats.get('plays', 0) or
                    new_stats.get('likes', 0) != existing_stats.get('likes', 0) or
                    new_stats.get('comments', 0) != existing_stats.get('comments', 0) or
                    new_stats.get('shares', 0) != existing_stats.get('shares', 0)):
                    logger.info(f"检测到统计数据变化，需要更新: {new_content['title']}")
                    return True
            
            # 检查状态是否变化
            if new_content.get('status') != existing_content.get('status'):
                logger.info(f"检测到状态变化，需要更新: {new_content['title']}")
                return True
            
            logger.info(f"内容无需更新: {new_content['title']}")
            return False
            
        except Exception as e:
            logger.error(f"更新判断过程出错: {str(e)}")
            return False 