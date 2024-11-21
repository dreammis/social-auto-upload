from datetime import datetime, timedelta
from typing import List, Optional
import json
from xhs import XhsClient

from uploader.xhs_uploader.main import beauty_print, sign_local
from utils.redis import get_all_xiaohongshu_login_ids, get_xiaohongshu_login


def upload_video_to_xiaohongshu(id: str, video_path: str, title: str, tags: List[str], timestamp: Optional[str]):
  login_info = get_xiaohongshu_login(id)
  cookies_json = login_info['client_cookie']
  cookies = json.loads(cookies_json)
  cookies_string = ";".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

  xhs_client = XhsClient(cookies_string, sign=sign_local, timeout=60)
  # auth cookie
  # 注意：该校验cookie方式可能并没那么准确
  try:
      xhs_client.get_video_first_frame_image_id("3214")
  except Exception as e:
      print(e)
      raise Exception("cookie 失效")
  
  tags_str = ' '.join(['#' + tag for tag in tags])
  hash_tags_str = ''
  hash_tags = []
  topics = []
  # 获取hashtag
  for i in tags[:3]:
      topic_official = xhs_client.get_suggest_topic(i)
      if topic_official:
          topic_official[0]['type'] = 'topic'
          topic_one = topic_official[0]
          hash_tag_name = topic_one['name']
          hash_tags.append(hash_tag_name)
          topics.append(topic_one)

  hash_tags_str = ' ' + ' '.join(['#' + tag + '[话题]#' for tag in hash_tags])

  # 模拟四小时后的时间戳
  # 获取当前的时间
  now = datetime.now()

  # 创建一个表示四小时的时间增量
  four_hours = timedelta(hours=4)

  # 计算四小时之后的时间
  future_time = now + four_hours
  
  note = xhs_client.create_video_note(title=title[:20], video_path=r"C:\Users\arcat\Develop\social-auto-upload\videos\demo.mp4",
                                      desc=title + tags_str + hash_tags_str,
                                      topics=topics,
                                      is_private=False,
                                      post_time=future_time.strftime("%Y-%m-%d %H:%M:%S"))
  
  beauty_print(note)


def get_xiaohongshu_login_account_ids():
    return get_all_xiaohongshu_login_ids()