## 1. DB 模块化 (Web API)

- [x] 1.1 创建 `web_runner/db.py`，包含 `init_db()`、`get_connection()`、`db_lock`
- [x] 1.2 为 `tasks` 表添加 `created` 列索引
- [x] 1.3 将 web_runner.py 中的 DB 初始化逻辑迁移到 `db.py`
- [x] 1.4 标记 `db/createTable.py` 为废弃（添加 deprecation 注释）

## 2. Flask App Factory (Web API)

- [x] 2.1 创建 `web_runner/__init__.py`，实现 `create_app()` 工厂函数
- [x] 2.2 创建 `web_runner/routes/__init__.py`，注册所有蓝图
- [x] 2.3 创建 `web_runner/routes/accounts.py`，迁移账号管理路由
- [x] 2.4 创建 `web_runner/routes/upload.py`，迁移上传路由
- [x] 2.5 创建 `web_runner/routes/tasks.py`，迁移任务管理路由
- [x] 2.6 创建 `web_runner/routes/ai.py`，迁移 AI 生成路由
- [x] 2.7 创建 `web_runner/routes/account_groups.py`，迁移分组路由
- [x] 2.8 更新 `web_runner.py` 为 thin wrapper，调用 `create_app()`

## 3. 调度器和 Worker 模块化 (Web API)

- [x] 3.1 创建 `web_runner/scheduler.py`，迁移定时任务调度逻辑
- [x] 3.2 创建 `web_runner/ai_worker.py`，迁移 AI 队列 worker 逻辑
- [x] 3.3 更新路由模块导入新模块

## 4. 前端路由懒加载 (Frontend)

- [x] 4.1 在 `App.tsx` 中使用 `React.lazy` 包装页面组件
- [x] 4.2 添加 `Suspense` 包装器和 loading skeleton
- [x] 4.3 创建 `ErrorBoundary` 组件
- [x] 4.4 动态导入 `@reactour/tour` 和 `canvas-confetti`

## 5. 环境变量文档 (Cross-layer)

- [x] 5.1 扫描代码中所有 `os.environ.get()` 和 `os.getenv()` 调用
- [x] 5.2 创建 `.env.example` 文件，包含所有变量及说明
- [x] 5.3 在 README 中添加环境变量配置说明

## 6. CI/CD 流水线 (Cross-layer)

- [x] 6.1 创建 `.github/workflows/ci.yml` 基础配置
- [x] 6.2 添加 Python lint 步骤（ruff）
- [x] 6.3 添加 Python test 步骤（pytest）
- [x] 6.4 添加 Frontend build 步骤（npm run build）
