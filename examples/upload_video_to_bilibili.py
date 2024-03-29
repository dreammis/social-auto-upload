import time
from pathlib import Path

from bilibili_uploader.main import read_cookie_json_file, extract_keys_from_json, random_emoji, BilibiliUploader
from conf import BASE_DIR
from utils.constant import VideoZoneTypes
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags

if __name__ == '__main__':
    filepath = Path(BASE_DIR) / "videos"
    # how to get cookie, see the file of get_bilibili_cookie.py.
    account_file = Path(BASE_DIR / "bilibili_uploader" / "account.json")
    if not account_file.exists():
        print(f"{account_file.name} 配置文件不存在")
        exit()
    cookie_data = read_cookie_json_file(account_file)
    cookie_data = extract_keys_from_json(cookie_data)

    tid = VideoZoneTypes.SPORTS_FOOTBALL.value  # 设置分区id
    # 获取视频目录
    folder_path = Path(filepath)
    # 获取文件夹中的所有文件
    files = list(folder_path.glob("*.mp4"))
    file_num = len(files)
    timestamps = generate_schedule_time_next_day(file_num, 1, daily_times=[16], timestamps=True)

    for index, file in enumerate(files):
        title, tags = get_title_and_hashtags(str(file))
        # just avoid error, bilibili don't allow same title of video.
        title += random_emoji()
        tags_str = ','.join([tag for tag in tags])
        # 打印视频文件名、标题和 hashtag
        print(f"视频文件名：{file}")
        print(f"标题：{title}")
        print(f"Hashtag：{tags}")
        # I set desc same as title, do what u like.
        desc = title
        bili_uploader = BilibiliUploader(cookie_data, file, title, desc, tid, tags, timestamps[index])
        bili_uploader.upload()

        # life is beautiful don't so rush. be kind be patience
        time.sleep(30)
