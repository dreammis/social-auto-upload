import redis
from celery import shared_task

r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)  

def add_bilibili_login(id):
  r.sadd('bilibili_login', id)

@shared_task()
def add_bilibili_login_task(id):
  return add_bilibili_login(id)

def register_bilibili_login(id, value):
  r.set(id, value)

def remove_bilibili_login(id):
  r.srem('bilibili_login', id)

def get_bilibili_login(id):
  return r.get(id)

def set_celery_task(id):
  r.set('running_celery_task', id)

def remove_celery_task(id):
  r.delete('running_celery_task')

def get_celery_task():
  return r.get('running_celery_task')
