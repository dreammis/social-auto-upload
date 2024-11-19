from multiprocessing.pool import AsyncResult
from celery import Celery, Task
from flask import Flask

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.Task = FlaskTask
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app

def check_task_status(task_id, app):
    # 创建 AsyncResult 对象
    result = AsyncResult(task_id, app=app)
    
    # 获取任务状态
    status = result.status
    print(f'Task Status: {status}')

    # 检查任务是否完成
    if result.ready():
        if result.successful():
            # 获取任务结果
            print('Task Result:', result.result)
        else:
            # 获取异常信息
            print('Task Failed:', result.result)
    else:
        print('Task is still running...')