import asyncio
from pathlib import Path

from sau_backend.conf import BASE_DIR
# from tk_uploader.main import tiktok_setup, TiktokVideo
from sau_backend.uploader.tk_uploader.main_chrome import tiktok_setup, TiktokVideo
from sau_backend.utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags


if __name__ == '__main__':
    filepath = Path(BASE_DIR) / "videos"
    account_file = Path(BASE_DIR / "cookies" / "tk_uploader" / "account.json")
    folder_path = Path(filepath)
    # get video files from folder
    files = list(folder_path.glob("*.mp4"))
    file_num = len(files)
    publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
    cookie_setup = asyncio.run(tiktok_setup(account_file, handle=True))
    for index, file in enumerate(files):
        title, tags = get_title_and_hashtags(str(file))
        thumbnail_path = file.with_suffix('.png')
        print(f"video_file_name：{file}")
        print(f"video_title：{title}")
        print(f"video_hashtag：{tags}")
        if thumbnail_path.exists():
            print(f"thumbnail_file_name：{thumbnail_path}")
            app = TiktokVideo(title, file, tags, publish_datetimes[index], account_file, thumbnail_path)
        else:
            app = TiktokVideo(title, file, tags, publish_datetimes[index], account_file)
        asyncio.run(app.main(), debug=False)
