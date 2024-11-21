import os
from typing import List, Optional
from type.upload_video_by_url_request import Platforms
from uploader.bilibili_uploader.extra import upload_video_to_bilibili
from uploader.xhs_uploader.extra import upload_video_to_xiaohongshu
from utils.video_file_manager import download_file, remove_file

current_working_directory = os.getcwd()

def run_upload_task(description: str, platforms: Platforms, tags: List[str], tid: str, 
                    title: str, video_url: str, video_file_name: str, 
                    timestamp: Optional[str] = None):
  try:
    download_file_path = download_file(video_url,save_folder=f'{current_working_directory}/cache/', filename=video_file_name)
    print(f'下载视频成功，文件路径：{download_file_path}')
    try:
      dict_platforms = platforms.model_dump()
      print(dict_platforms)
      for platform in dict_platforms.keys():
        if dict_platforms[platform] == []: 
          print(f'{platform} 没有配置账号，跳过该平台')
        if platform == 'bilibili':
          for id in dict_platforms[platform]:
            upload_video_to_bilibili(id=id, video_path=download_file_path, title=title, description=description, tags=tags, tid=int(tid), timestamp=timestamp)
            print(f'上传视频到Bilibili成功，ID：{id}')
        elif platform == 'xiaohongshu':
          for id in dict_platforms[platform]:
            print(f'正在上传ID：{id}')
            upload_video_to_xiaohongshu(id=id, video_path=download_file_path, title=title, tags=tags, timestamp=timestamp)
            print(f'上传视频到小红书成功，ID：{id}')

        else:
          print(f'不支持的平台：{platform}')
    except Exception as e:
      print(f'上传视频失败，错误信息：{str(e)}')
    # finally:
    #   remove_file(download_file_path)

  except Exception as e:
    print(f'内部出错，错误信息：{str(e)}')