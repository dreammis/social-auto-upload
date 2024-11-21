import json
import redis

r = redis.Redis(host='127.0.0.1', port=6666, decode_responses=True)  

def add_to_bilibili_login_list(id):
  r.sadd('bilibili_login', id)

def register_bilibili_login(id: str, value: str):
  r.set(id, value)

def remove_from_bilibili_login_list(id):
  r.srem('bilibili_login', id)

def get_bilibili_login(id) -> dict:
  return json.loads(r.get(id))

def remove_bilibili_login(id):
  r.delete(id)

def get_all_bilibili_login_ids():
  return r.smembers('bilibili_login')

def clear_bilibili_login_list():
  r.delete('bilibili_login')


# xiaohongshu
def add_to_xiaohongshu_login_list(id):
  r.sadd('xiaohongshu_login', id)

def register_xiaohongshu_login(id: str, value: str):
  r.set(id, value)

def remove_from_xiaohongshu_login_list(id):
  r.srem('xiaohongshu_login', id)

def get_xiaohongshu_login(id) -> dict:
  return json.loads(r.get(id))

def remove_xiaohongshu_login(id):
  r.delete(id)

def get_all_xiaohongshu_login_ids():
  return r.smembers('xiaohongshu_login')

def clear_xiaohongshu_login_list():
  r.delete('xiaohongshu_login')

