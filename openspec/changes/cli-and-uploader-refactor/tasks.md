## 1. CLI 模型基类 (CLI)

- [ ] 1.1 在 `cli/models.py` 顶部添加 `BaseUploadRequest` dataclass，包含 `account_name`、`publish_date`、`debug`、`headless` 四个公共字段
- [ ] 1.2 将 `DouyinVideoUploadRequest`、`DouyinNoteUploadRequest`、`KuaishouVideoUploadRequest`、`KuaishouNoteUploadRequest`、`XiaohongshuVideoUploadRequest`、`XiaohongshuNoteUploadRequest`、`BilibiliNoteUploadRequest`、`TencentVideoUploadRequest`、`TencentNoteUploadRequest`、`TiktokVideoUploadRequest`、`BaijiahaoVideoUploadRequest` 改为继承 `BaseUploadRequest`，移除重复字段定义
- [ ] 1.3 `BilibiliVideoUploadRequest` 保留独立（无 `debug`/`headless` 字段），不继承基类
- [ ] 1.4 验证 `cli/dispatchers.py` 和 `cli/platforms/*.py` 中的 import 和实例化仍然正常工作

## 2. 通用 CLI 分发器 (CLI)

- [ ] 2.1 在 `cli/dispatchers.py` 中定义 `PlatformHandler` dataclass，包含 `login_fn`、`check_fn`、`upload_video_fn`、`upload_note_fn`、`video_request_cls`、`note_request_cls`、`publish_strategy_map`、`extra_argv_builders`
- [ ] 2.2 创建 `PLATFORM_HANDLERS` 字典，包含 7 个平台的配置
- [ ] 2.3 实现 `_dispatch_platform(args, handler)` 通用函数，处理 login/check/upload-video/upload-note 四种 action
- [ ] 2.4 为 douyin 提取 `_build_douyin_extra_argv()` 函数（product-link、product-title、thumbnail-landscape、thumbnail-portrait）
- [ ] 2.5 为 bilibili 提取 `_build_bilibili_extra_argv()` 函数（tid）
- [ ] 2.6 为 tencent 提取 `_build_tencent_extra_argv()` 函数（short-title、category、draft、thumbnail 双版）
- [ ] 2.7 为 xiaohongshu 提取 `_build_xiaohongshu_argv()` 函数（标签数量上限校验）
- [ ] 2.8 将 `dispatch()` 函数改为查找 `PLATFORM_HANDLERS` + 调用 `_dispatch_platform`
- [ ] 2.9 删除旧的 7 个 `_dispatch_*` 函数
- [ ] 2.10 运行 `pytest tests/` 验证所有 CLI 命令行为不变

## 3. 浏览器上下文管理器 (Uploader)

- [ ] 3.1 在 `uploader/common.py` 中添加 `managed_browser(account_file, headless=True)` 异步上下文管理器
- [ ] 3.2 在 `uploader/common.py` 中添加 `managed_browser_for_login(headless=True)` 变体（不加载 cookie）
- [ ] 3.3 为 `managed_browser()` 添加单元测试：验证上下文退出时 browser 正确关闭

## 4. Uploader 迁移到 managed_browser (Uploader)

- [ ] 4.1 迁移 `uploader/douyin_uploader/main.py` 的 `DouYinVideo.upload()` 使用 `managed_browser()`
- [ ] 4.2 迁移 `uploader/douyin_uploader/main.py` 的 `DouYinNote.upload()` 使用 `managed_browser()`
- [ ] 4.3 迁移 `uploader/douyin_uploader/main.py` 的 `douyin_cookie_gen()` 使用 `managed_browser_for_login()`
- [ ] 4.4 迁移 `uploader/ks_uploader/main.py` 的上传方法使用 `managed_browser()`
- [ ] 4.5 迁移 `uploader/xiaohongshu_uploader/main.py` 的上传方法使用 `managed_browser()`
- [ ] 4.6 迁移 `uploader/bilibili_uploader/main.py` 的上传方法使用 `managed_browser()`
- [ ] 4.7 运行 `pytest tests/` 验证所有 uploader 行为不变

## 5. web_runner.py 子模块提取 (Web API)

- [ ] 5.1 创建 `web_runner/ai_worker.py`，迁移 AI 模型配置（`AI_MODELS`、`PLATFORM_PROMPTS`）、`_build_media_content()`、key 池管理函数、`_ai_request_semaphore`
- [ ] 5.2 创建 `web_runner/scheduler.py`，迁移 `_schedule_task()`、`_scheduled_timers`、`_timer_lock`、`_normalise_schedule()`
- [ ] 5.3 创建 `web_runner/error_events.py`，迁移 `_log_error_event()`、`_db_get_error_events()`、相关常量
- [ ] 5.4 更新 `web_runner/routes/upload.py`、`web_runner/routes/tasks.py` 等路由模块的 import
- [ ] 5.5 更新 `web_runner/utils.py` 重新导出新模块的符号（保持向后兼容）
- [ ] 5.6 运行 `pytest tests/` 验证 Web API 行为不变

## 6. 日志统一 (Web API)

- [ ] 6.1 将 `web_runner.py` 中的 `print()` 调用替换为 `_task_logger.info()` 或 `_task_logger.warning()`
- [ ] 6.2 将 `web_runner/routes/*.py` 中的 `print()` 调用替换为 logger 调用
