import os
import sys
import asyncio
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from conf import BASE_DIR
from uploader.tencent_uploader.main import weixin_setup, TencentVideo
from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags


if __name__ == '__main__':
    filepath = Path(BASE_DIR) / "videos"
    account_file = Path(BASE_DIR / "cookies" / "tencent_uploader" / "account.json")
    # 获取视频目录
    folder_path = Path(filepath)
    # 获取文件夹中的所有文件
    files = list(folder_path.glob("*.mp4"))
    file_num = len(files)
    publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
    cookie_setup = asyncio.run(weixin_setup(account_file, handle=True))
    category = TencentZoneTypes.EMOTION.value  # 标记原创需要否则不需要传
    
    for index, file in enumerate(files):
        try:
            title, tags, mentions = get_title_and_hashtags(str(file))
            
            # 确保标题不为空，如果为空则使用文件名
            if not title.strip():
                title = Path(file).stem
            
            # 确保标签是字符串列表
            if not tags:
                tags = []
            elif isinstance(tags, str):
                tags = [tags]
            
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            print(f"mentions：{mentions}")
            # 确保使用正确的路径格式
            video_path = str(file.resolve())
            account_file_path = str(account_file.resolve())
            app = TencentVideo(title, video_path, tags, publish_datetimes[index], [account_file_path], category)
            asyncio.run(app.main(), debug=False)
        except Exception as e:
            print(f"处理文件 {file} 时出错: {str(e)}")
            continue
