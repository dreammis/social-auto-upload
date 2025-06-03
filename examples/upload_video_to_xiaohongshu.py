import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.xiaohongshu_uploader.main import xiaohongshu_setup, XiaoHongShuVideo
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags


if __name__ == '__main__':
    filepath = Path(BASE_DIR) / "videos"
    account_file = Path(BASE_DIR / "cookies" / "xiaohongshu_uploader" / "58a391ba-4082-11f0-a321-44e51723d63c.json")
    # 获取视频目录
    folder_path = Path(filepath)
    # 获取文件夹中的所有文件
    files = list(folder_path.glob("*.mp4"))
    file_num = len(files)
    publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
    cookie_setup = asyncio.run(xiaohongshu_setup(account_file, handle=False))
    for index, file in enumerate(files):
        title, tags = get_title_and_hashtags(str(file))
        thumbnail_path = file.with_suffix('.png')
        # 打印视频文件名、标题和 hashtag
        print(f"视频文件名：{file}")
        print(f"标题：{title}")
        print(f"Hashtag：{tags}")
        # 暂时没有时间修复封面上传，故先隐藏掉该功能
        # if thumbnail_path.exists():
            # app = XiaoHongShuVideo(title, file, tags, publish_datetimes[index], account_file, thumbnail_path=thumbnail_path)
        # else:
        app = XiaoHongShuVideo(title, file, tags, 0, account_file)
        asyncio.run(app.main(), debug=False)
