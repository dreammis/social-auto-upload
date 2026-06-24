## 1. CLI — 无限循环修复

- [x] 1.1 为小红书上传器的 4 处 `while True` 循环添加 `max_retries` 参数（publish button click, upload complete check）
- [x] 1.2 为腾讯上传器的 2 处 `while True` 循环添加 `max_retries` 参数（wait_for_upload_complete, submit_publish）
- [x] 1.3 统一所有平台的重试日志格式，在达到 max_retries 时抛出 `TimeoutError`

## 2. CLI — 共享模块提取

- [x] 2.1 创建 `uploader/common.py`，从各平台上传器提取 `_msg()`, `_emit_qrcode_callback()`, `_build_login_result()`
- [x] 2.2 修改 douyin, kuaishou, xiaohongshu, bilibili, tencent 上传器 import 共享模块
- [x] 2.3 删除各平台上传器中重复的本地函数定义

## 3. CLI — dispatch() 表驱动重构

- [x] 3.1 在 `sau_cli.py` 中创建 `PLATFORM_REGISTRY` 字典，映射 platform → action → handler
- [x] 3.2 重构 `dispatch()` 函数使用查找表替代 if/elif 链
- [x] 3.3 验证所有 7 个平台的所有 action 路由正确

## 4. CLI — Bilibili cookie 修复

- [x] 4.1 为 Bilibili video upload 添加 `bilibili_cookie_auth()` 调用（替代仅检查文件存在）
- [x] 4.2 为 Bilibili note upload 添加 `bilibili_cookie_auth()` 调用
- [x] 4.3 修复 Bilibili note 上传后 cookie 格式覆盖问题（保存前检查/保留 biliup 格式）

## 5. CLI — 其他 bug 修复

- [x] 5.1 修复百家号 `handle_upload_error` 死代码（移除 return 前的死代码，实现正确错误处理）
- [x] 5.2 修复百家号定时发布随机时间选择（替换 `random.randint` 为正确的小时选择逻辑）
- [x] 5.3 修复 TikTok 硬编码 React 选择器 `#:r9:`，改用稳定的选择器
- [x] 5.4 修复 `async_retry` 装饰器捕获所有异常的问题（限制为 RuntimeError, IOError, TimeoutError）
- [x] 5.5 修复各平台上传器中的裸 `except:` 子句（tk_uploader:36, baijiahao 多处）

## 6. CLI — 死代码清理

- [x] 6.1 删除 `xhs_uploader/` 目录（legacy sync API，未被 CLI 使用）
- [x] 6.2 删除 `legacy/` 目录（旧版 sau_backend.py 和 myUtils/）
- [x] 6.3 删除 `utils/browser_hook.py`（未被任何模块导入）
- [x] 6.4 删除 `utils/log.py` 中未使用的 `xhs_logger`

## 7. Web API — 线程安全修复

- [x] 7.1 为 `_scheduled_timers` 字典添加 `threading.Lock` 保护
- [x] 7.2 在所有 `_scheduled_timers` 读写操作处使用 `with _timer_lock:` 块
- [x] 7.3 修复 `delete_task`：删除 scheduled 任务前先取消关联的 timer

## 8. Web API — 可靠性增强

- [x] 8.1 修复 `_quick_check_cookie`：stale cookie (>7天) 返回 `valid: false` 而非 `valid: true`
- [x] 8.2 修复 `_db_get_logs` LIKE 转义：对 task_id 中的 `%` 和 `_` 进行转义
- [x] 8.3 添加 Flask 全局 500 异常处理器，返回 JSON 格式错误响应
- [x] 8.4 添加 `MAX_CONTENT_LENGTH = 200MB` 请求大小限制
- [x] 8.5 为 `/api/upload/video` 添加 JSON Content-Type 支持（与 `/api/upload/note` 一致）

## 9. Web API — SSE 上传进度

- [x] 9.1 添加 `GET /api/upload/progress?task_id=<id>` SSE 端点
- [x] 9.2 复用 `_qrcode_callback` 模式，为上传任务创建 log event queue
- [x] 9.3 添加最大并发 SSE 连接数限制（5）和超时（5min）

## 10. Frontend — 死代码清理

- [x] 10.1 删除 `useAccounts` hook（未使用）
- [x] 10.2 删除 `PLATFORMS_WITH_ICONS` 空别名
- [x] 10.3 删除 `PageTransition` 组件
- [x] 10.4 删除重复的 `PageLoading.tsx` 独立文件
- [x] 10.5 删除未使用的 `Spinner` 组件
- [x] 10.6 删除 `toast.tsx` 中的 `message` 死事件 API
- [x] 10.7 删除 `uploadNote` JSON 版本函数（未使用）
- [x] 10.8 修复 `ProposalsPage` 使用 raw axios 的问题，改用共享 API client

## 11. Frontend — 基础设施修复

- [x] 11.1 修复 Double ToastProvider 嵌套（移除 ThemeProvider 中的 ToastProvider）
- [x] 11.2 实现 React Error Boundary 组件，包裹主要路由
- [x] 11.3 添加 404 catch-all 路由，显示"页面未找到"页面

## 12. Frontend — 功能增强

- [x] 12.1 为 PublishPage 视频上传区域添加拖拽上传支持（onDragOver/onDragLeave/onDrop）
- [x] 12.2 为 PublishPage 图片上传区域添加拖拽上传支持
- [x] 12.3 添加客户端文件大小验证（视频 200MB，图片 20MB）
- [x] 12.4 修复 `videoThumbnail` 跨平台 fallback 逻辑（各平台使用各自缩略图）

## 13. Frontend — 性能优化

- [x] 13.1 将 LogsPage 从手动 `setInterval` 迁移到 TanStack Query
- [x] 13.2 为 TasksPage 和 LogsPage 的搜索输入添加 300ms 防抖
- [x] 13.3 修复 note image preview 内存泄漏（component unmount 时 revoke blob URLs）
- [x] 13.4 重构 PublishPage 的 25+ useState 为 `usePublishForm` 自定义 hook

## 14. Frontend — 分页支持

- [x] 14.1 后端 `/api/tasks` 添加 `limit` 和 `offset` 参数
- [x] 14.2 后端 `/api/logs` 添加 `limit` 和 `offset` 参数
- [x] 14.3 前端 TasksPage 使用 `useInfiniteQuery` 实现无限滚动
- [x] 14.4 前端 LogsPage 使用 `useInfiniteQuery` 实现无限滚动
