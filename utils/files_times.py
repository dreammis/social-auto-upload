from datetime import timedelta

from datetime import datetime
from pathlib import Path
import os
import re

from conf import BASE_DIR


def get_absolute_path(relative_path: str, base_dir: str = None) -> str:
    # Convert the relative path to an absolute path
    absolute_path = Path(BASE_DIR) / base_dir / relative_path
    return str(absolute_path)


def get_title_and_hashtags(file_path):
    # 获取文件名（不包括扩展名）
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # 将文件名中的下划线和连字符替换为空格
    title = re.sub(r'[_-]', ' ', file_name)
    
    # 将标题中的每个单词首字母大写
    title = title.title()
    
    # 从标题中提取可能的标签（假设标签是以#开头的单词）
    tags = re.findall(r'#(\w+)', title)
    
    # 从标题中移除标签
    title = re.sub(r'#\w+', '', title).strip()
    
    # 如果没有找到标签，可以根据标题生成一些默认标签
    if not tags:
        words = title.split()
        tags = words[:3]  # 使用标题的前三个单词作为标签
    
    return title, tags


def generate_schedule_time_next_day(total_videos, videos_per_day, daily_times=None, timestamps=False, start_days=0):
    """
    Generate a schedule for video uploads, starting from the next day.

    Args:
    - total_videos: Total number of videos to be uploaded.
    - videos_per_day: Number of videos to be uploaded each day.
    - daily_times: Optional list of specific times of the day to publish the videos.
    - timestamps: Boolean to decide whether to return timestamps or datetime objects.
    - start_days: Start from after start_days.

    Returns:
    - A list of scheduling times for the videos, either as timestamps or datetime objects.
    """
    if videos_per_day <= 0:
        raise ValueError("videos_per_day should be a positive integer")

    if daily_times is None:
        # Default times to publish videos if not provided
        daily_times = [6, 11, 14, 16, 22]

    if videos_per_day > len(daily_times):
        raise ValueError("videos_per_day should not exceed the length of daily_times")

    # Generate timestamps
    schedule = []
    current_time = datetime.now()

    for video in range(total_videos):
        day = video // videos_per_day + start_days + 1  # +1 to start from the next day
        daily_video_index = video % videos_per_day

        # Calculate the time for the current video
        hour = daily_times[daily_video_index]
        time_offset = timedelta(days=day, hours=hour - current_time.hour, minutes=-current_time.minute,
                                seconds=-current_time.second, microseconds=-current_time.microsecond)
        timestamp = current_time + time_offset

        schedule.append(timestamp)

    if timestamps:
        schedule = [int(time.timestamp()) for time in schedule]
    return schedule
