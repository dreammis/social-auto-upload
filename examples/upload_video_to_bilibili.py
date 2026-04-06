import subprocess
import sys
from pathlib import Path

from conf import BASE_DIR
from utils.constant import VideoZoneTypes
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags

if __name__ == '__main__':
    filepath = Path(BASE_DIR) / "videos"
    folder_path = Path(filepath)
    files = list(folder_path.glob("*.mp4"))
    file_num = len(files)
    publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
    cli_path = Path(BASE_DIR) / "sau_cli.py"

    for index, file in enumerate(files):
        title, tags = get_title_and_hashtags(str(file))
        print(f"视频文件名：{file}")
        print(f"标题：{title}")
        print(f"Hashtag：{tags}")
        desc = title
        schedule_text = publish_datetimes[index].strftime("%Y-%m-%d %H:%M")
        command = [
            sys.executable,
            str(cli_path),
            "bilibili",
            "upload-video",
            "--account",
            "creator",
            "--file",
            str(file),
            "--title",
            title,
            "--desc",
            desc,
            "--tid",
            str(VideoZoneTypes.SPORTS_FOOTBALL.value),
            "--tags",
            ",".join(tags),
            "--schedule",
            schedule_text,
        ]
        subprocess.run(command, check=True)
