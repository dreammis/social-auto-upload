import redis

r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)  

def add_to_bilibili_login_list(id):
  r.sadd('bilibili_login', id)

def register_bilibili_login(id: str, value: str):
  r.set(id, value)

def remove_from_bilibili_login_list(id):
  r.srem('bilibili_login', id)

def get_bilibili_login(id):
  return r.get(id)

def remove_bilibili_login(id):
  r.delete(id)

def get_all_bilibili_login_ids():
  return r.smembers('bilibili_login')

def clear_bilibili_login_list():
  r.delete('bilibili_login')