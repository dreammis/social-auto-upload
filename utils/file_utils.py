import os



# 校验视频文件的大小，入参需要视频文件绝对路径，以及需要校验的大小，单位为MB
def check_video_size(video_path, size):
    if not os.path.exists(video_path):
        return False
    if os.path.getsize(video_path) < size * 1024 * 1024:
        return False
    return True