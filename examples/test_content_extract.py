"""
测试视频号内容提取功能
专注于测试标签和@用户的提取
"""
import sys
import asyncio
from pathlib import Path
import re
from typing import Dict, List, Tuple

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from utils.log import tencent_logger as logger

def extract_mentions_and_tags(content: str) -> Tuple[List[str], List[str]]:
    """
    从文本中提取@用户和#标签
    
    Args:
        content: 包含@用户和#标签的文本
        
    Returns:
        Tuple[List[str], List[str]]: (@用户列表, #标签列表)
    """
    def clean_text(text: str) -> str:
        """清理文本，去除多余空格"""
        # 移除首尾空格
        text = text.strip()
        # 将多个空格替换为单个空格
        text = re.sub(r'\s+', ' ', text)
        return text
    
    # 使用正则表达式提取所有@用户
    # 1. 必须以@开头
    # 2. 用户名可以包含中文、英文、数字
    # 3. 用户名在遇到下一个@、#或空格时结束
    mentions = []
    for match in re.finditer(r'@([a-zA-Z0-9\u4e00-\u9fa5]+?)(?=[@#]|\s|$)', content):
        mention = clean_text(match.group(1))
        if mention:
            mentions.append(mention)
    
    # 使用正则表达式提取所有#标签
    # 1. 必须以#开头
    # 2. 标签可以包含中文、英文、数字
    # 3. 标签在遇到下一个@、#或空格时结束
    tags = []
    for match in re.finditer(r'#([a-zA-Z0-9\u4e00-\u9fa5]+?)(?=[@#]|\s|$)', content):
        tag = clean_text(match.group(1))
        if tag:
            tags.append(tag)
    
    return mentions, tags

def run_test_case(title: str, expected_mentions: List[str], expected_tags: List[str]) -> bool:
    """
    运行单个测试用例
    
    Args:
        title: 要测试的标题
        expected_mentions: 期望的@用户列表
        expected_tags: 期望的#标签列表
        
    Returns:
        bool: 测试是否通过
    """
    mentions, tags = extract_mentions_and_tags(title)
    
    # 检查结果
    mentions_match = set(mentions) == set(expected_mentions)
    tags_match = set(tags) == set(expected_tags)
    
    # 打印测试结果
    logger.info(f"\n测试用例: {title}")
    logger.info(f"提取到的@用户: {mentions}")
    logger.info(f"期望的@用户: {expected_mentions}")
    logger.info(f"@用户匹配: {'✓' if mentions_match else '✗'}")
    
    logger.info(f"提取到的#标签: {tags}")
    logger.info(f"期望的#标签: {expected_tags}")
    logger.info(f"#标签匹配: {'✓' if tags_match else '✗'}")
    
    return mentions_match and tags_match

def main():
    """运行所有测试用例"""
    test_cases = [
        # 基本测试
        {
            "title": "你也挑剔吗 @微信创作者@微信创作者助手@向阳也有米#向阳有米#情感共鸣#认知#女性成长#正能量",
            "expected_mentions": ["微信创作者", "微信创作者助手", "向阳也有米"],
            "expected_tags": ["向阳有米", "情感共鸣", "认知", "女性成长", "正能量"]
        },
        # 简单测试
        {
            "title": "测试标题 @用户名#标签名",
            "expected_mentions": ["用户名"],
            "expected_tags": ["标签名"]
        },
        # 混合顺序测试
        {
            "title": "#标签1@用户1#标签2@用户2",
            "expected_mentions": ["用户1", "用户2"],
            "expected_tags": ["标签1", "标签2"]
        },
        # 数字和英文测试
        {
            "title": "@user123#tag123",
            "expected_mentions": ["user123"],
            "expected_tags": ["tag123"]
        },
        # 重复测试
        {
            "title": "@用户1@用户1#标签1#标签1",
            "expected_mentions": ["用户1", "用户1"],
            "expected_tags": ["标签1", "标签1"]
        },
        # 中文测试
        {
            "title": "@微信创作者#创作技巧@短视频创作者#视频制作",
            "expected_mentions": ["微信创作者", "短视频创作者"],
            "expected_tags": ["创作技巧", "视频制作"]
        },
        # 连续标签测试
        {
            "title": "#标签1#标签2#标签3@用户1@用户2@用户3",
            "expected_mentions": ["用户1", "用户2", "用户3"],
            "expected_tags": ["标签1", "标签2", "标签3"]
        },
        # 混合内容测试
        {
            "title": "标题@用户1#标签1@用户2 some text#标签2 more@用户3 text#标签3",
            "expected_mentions": ["用户1", "用户2", "用户3"],
            "expected_tags": ["标签1", "标签2", "标签3"]
        }
    ]
    
    # 运行所有测试用例
    total_cases = len(test_cases)
    passed_cases = 0
    
    logger.info(f"开始运行 {total_cases} 个测试用例...")
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n=== 运行测试用例 {i}/{total_cases} ===")
        if run_test_case(
            test_case["title"],
            test_case["expected_mentions"],
            test_case["expected_tags"]
        ):
            passed_cases += 1
            
    # 打印总结
    logger.info(f"\n=== 测试完成 ===")
    logger.info(f"总用例数: {total_cases}")
    logger.info(f"通过用例数: {passed_cases}")
    logger.info(f"失败用例数: {total_cases - passed_cases}")
    logger.info(f"通过率: {(passed_cases / total_cases) * 100:.2f}%")

if __name__ == "__main__":
    main() 