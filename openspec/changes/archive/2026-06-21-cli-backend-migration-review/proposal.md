## Why

CLI → Web 后端迁移已基本完成，核心功能（登录、上传视频/图文、任务管理、日志查看）均可通过 Web API 和前端 UI 使用。但迁移过程中遗留了多处缺陷、不一致和未完善的功能，需要系统性审查和修复，以确保生产可用性。

## What Changes

### CLI 层
- 修复抖音/小红书/腾讯上传中的无限 `while True` 循环，添加最大重试次数
- 修复百家号定时发布随机时间选择 bug 和 `handle_upload_error` 死代码
- 修复 Bilibili 上传路径中缺少 cookie 有效性验证（仅检查文件存在）
- 修复 Bilibili note 上传后 cookie 格式覆盖问题（Playwright 格式覆盖 biliup 格式）
- 修复 `tk_uploader` 中的硬编码 React 选择器 `#:r9:` 和裸 `except:` 问题
- 提取各平台上传器中重复的 `_msg()`、`_emit_qrcode_callback()`、`_build_login_result()` 到共享模块
- 重构 `dispatch()` 为表驱动分发，消除 300 行 if/elif 链
- 修复 `async_retry` 装饰器捕获所有异常（包括 `TypeError` 等编程错误）的问题
- 清理 `xhs_uploader/`、`legacy/`、`utils/browser_hook.py` 等死代码

### Web API 层
- 修复 `_scheduled_timers` 字典的线程安全问题（添加锁保护）
- 修复 `delete_task` 允许删除 `scheduled` 状态任务但未取消 timer 的问题
- 修复 `_quick_check_cookie` 将 stale cookie 标记为 `valid: True` 的误导行为
- 修复 `_db_get_logs` 中 LIKE 注入/转义问题
- 为 `/api/upload/video` 添加 JSON Content-Type 支持（与 `/api/upload/note` 一致）
- 添加请求大小限制（`MAX_CONTENT_LENGTH`）
- 添加全局异常处理器，避免裸 500 错误
- 添加 CORS 配置选项（当前 `origins: *` 过于宽松）
- 添加 SSE 上传进度推送（当前仅登录有 SSE，上传需轮询）

### Frontend 层
- 修复 `Double ToastProvider` 嵌套问题
- 修复 `ProposalsPage` 使用 raw axios 而非共享 client 的问题
- 清理死代码：`useAccounts` hook、`PLATFORMS_WITH_ICONS`、`PageTransition`、`PageLoading`（重复定义）、`Spinner`、`message` API
- 为 `PublishPage` 添加拖拽上传支持（当前声明了拖拽但无实际处理）
- 添加客户端文件大小验证
- 修复 `videoThumbnail` 跨平台缩略图 fallback 逻辑错误
- 添加 React Error Boundary
- 添加 404 路由
- 将 `LogsPage` 迁移到 TanStack Query（当前使用手动 `setInterval`）
- 添加任务/日志分页支持
- 修复 `note image preview` 内存泄漏（`URL.createObjectURL` 未 revoke）
- 重构 `PublishPage` 的 25+ `useState` 为自定义 hook 或表单库
- 添加搜索输入防抖

## Capabilities

### New Capabilities
- `cli-hardening`: CLI 层健壮性提升——无限循环修复、错误处理改进、死代码清理、代码复用
- `api-reliability`: Web API 层可靠性——线程安全、全局异常处理、请求限制、SSE 进度推送
- `frontend-polish`: Frontend 层打磨——死代码清理、拖拽上传、错误边界、分页、内存泄漏修复

### Modified Capabilities
（无已有 spec 需要修改——这是首次系统性审查）

## Impact

- **CLI (`sau_cli.py` + `uploader/`)**: 涉及所有 7 个平台的上传器修改，提取共享模块，重构 dispatch 函数
- **Web API (`web_runner.py`)**: 线程安全修复影响定时任务系统，SSE 进度为新功能
- **Frontend (`sau_web/frontend/`)**: 涉及 5 个页面和多个共享组件的修改
- **依赖**: 可能需要添加 `flask-cors`（如未使用），前端可能需要 `react-virtuoso`（虚拟滚动）
- **数据库**: 无 schema 变更
- **部署**: 无破坏性变更，可渐进式实施
