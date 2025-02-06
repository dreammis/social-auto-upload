from datetime import timedelta

from datetime import datetime
from pathlib import Path

from conf import BASE_DIR


def get_absolute_path(relative_path: str, base_dir: str = None) -> str:
    # Convert the relative path to an absolute path
    absolute_path = Path(BASE_DIR) / base_dir / relative_path
    return str(absolute_path)


def get_title_and_hashtags(file_path: str) -> tuple[str, list, list]:
    """
    从文件名中提取标题和标签
    
    Args:
        file_path: 文件路径
        
    Returns:
        tuple: (标题, 标签列表, @提及列表)
    """
    # 获取文件名（不含扩展名）
    filename = Path(file_path).stem
    
    # 分离标题和标签
    parts = filename.split('#')
    title = parts[0].strip()
    
    # 提取标签和@提及
    tags = []
    mentions = []
    
    if len(parts) > 1:
        # 处理标签部分
        tag_part = parts[1]
        # 分离标签和@提及
        for item in tag_part.split():
            if item.startswith('@'):
                mentions.append(item[1:])  # 去掉@符号
            else:
                tags.append(item)
    
    return title, tags, mentions


def generate_schedule_time_next_day(total_videos, videos_per_day, daily_times=None, timestamps=False, start_days=0):
    """
    生成从第二天开始的视频上传时间表。

    Args:
    - total_videos: 需要上传的视频总数。
    - videos_per_day: 每天上传的视频数量。
    - daily_times: 可选的每天发布视频的具体时间列表。
    - timestamps: 布尔值，决定是返回时间戳还是 datetime 对象。
    - start_days: 从多少天后开始。

    Returns:
    - 视频的计划时间列表，可以是时间戳或 datetime 对象。
    """
    if videos_per_day <= 0:
        raise ValueError("videos_per_day 应该是一个正整数")

    if daily_times is None:
        # 如果未提供发布时间,使用默认时间
        daily_times = [6, 11, 14, 16, 22]

    if videos_per_day > len(daily_times):
        raise ValueError("每天上传的视频数量不能超过每日发布时间点的数量")

    # 生成时间戳
    schedule = []
    current_time = datetime.now()

    for video in range(total_videos):
        day = video // videos_per_day + start_days + 1  # +1 表示从第二天开始
        daily_video_index = video % videos_per_day

        # 计算当前视频的发布时间
        hour = daily_times[daily_video_index]
        time_offset = timedelta(days=day, hours=hour - current_time.hour, minutes=-current_time.minute,
                                seconds=-current_time.second, microseconds=-current_time.microsecond)
        timestamp = current_time + time_offset

        schedule.append(timestamp)

    if timestamps:
        schedule = [int(time.timestamp()) for time in schedule]
    return schedule
