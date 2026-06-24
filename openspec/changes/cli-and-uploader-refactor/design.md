## Context

项目 CLI 层（`cli/`）和 Uploader 层（`uploader/`）经过前期重构已形成清晰的模块边界，但存在大量重复代码：

- `cli/dispatchers.py`：7 个 `_dispatch_*` 函数结构完全一致（login → check → upload-video → upload-note），仅平台名、请求类、常量不同，共 378 行
- `cli/models.py`：12 个 dataclass 中 `account_name`、`publish_date`、`debug`、`headless` 等字段重复出现 12 次，共 187 行
- 各 uploader：浏览器启动 → cookie 加载 → stealth 注入 → 上传 → 关闭的生命周期代码在每个 uploader 中重复约 30-50 行
- `web_runner.py`：虽已拆出路由蓝图，但 AI 生成（~200 行）、调度器（~50 行）、错误事件（~80 行）仍混在主文件中

## Goals / Non-Goals

**Goals:**
- 消除 CLI 分发层重复代码，新增平台只需添加一个配置条目 + 平台模块
- 消除 CLI 模型层重复字段定义，通过继承复用
- 提供 Uploader 浏览器上下文管理器，统一 playwright 生命周期
- 将 web_runner.py 中 AI/调度/错误处理逻辑提取为独立模块
- 统一日志使用 loguru，移除 print() 调用

**Non-Goals:**
- 不改变 CLI 外部命令行接口（`sau <platform> <action>` 保持不变）
- 不改变 Web API 路由路径和请求/响应格式
- 不改变前端代码
- 不改变数据库 schema
- 不迁移到其他浏览器自动化框架（保持 patchright）

## Decisions

### D1: 配置驱动的通用 CLI 分发器

**决策**: 用 `PLATFORM_HANDLERS` 字典替代 7 个独立的 `_dispatch_*` 函数。字典键为平台名，值为包含 `login_fn`、`check_fn`、`upload_video_fn`、`upload_note_fn`、`request_classes` 的配置对象。

```python
PLATFORM_HANDLERS = {
    "douyin": PlatformHandler(
        login_fn=douyin.login,
        check_fn=douyin.check,
        upload_video_fn=douyin.upload_video,
        upload_note_fn=douyin.upload_note,
        video_request_cls=DouyinVideoUploadRequest,
        note_request_cls=DouyinNoteUploadRequest,
        publish_strategy_map={"scheduled": DOUYIN_PUBLISH_STRATEGY_SCHEDULED, "immediate": DOUYIN_PUBLISH_STRATEGY_IMMEDIATE},
        extra_argv_builders=[_build_douyin_argv],
    ),
    ...
}
```

通用 `_dispatch_platform(args, handler)` 函数处理 login/check/upload 逻辑，平台特有参数通过 `extra_argv_builders` 回调注入。

**替代方案**: 用抽象基类 + 多态 — 需要为每个平台创建子类，文件数更多，不如字典直观。

### D2: CLI 模型继承

**决策**: 提取 `BaseUploadRequest` dataclass，包含 4 个公共字段。各平台请求类通过 `@dataclass(slots=True)` 继承。

```python
@dataclass(slots=True)
class BaseUploadRequest:
    account_name: str
    publish_date: datetime | int
    debug: bool = True
    headless: bool = True

@dataclass(slots=True)
class DouyinVideoUploadRequest(BaseUploadRequest):
    video_file: Path
    title: str
    # ... 平台特有字段
```

**替代方案**: 用 TypedDict 或 Pydantic — dataclass 是项目现有约定，保持一致。

### D3: 浏览器上下文管理器

**决策**: 在 `uploader/common.py` 中添加 `@asynccontextmanager` 的 `managed_browser()` 函数：

```python
@asynccontextmanager
async def managed_browser(account_file, headless=True):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        try:
            yield context
        finally:
            await context.close()
            await browser.close()
```

各 uploader 的 `upload()` 方法改为 `async with managed_browser(...) as context:` 模式。

**替代方案**: 基类方法 — 需要继承关系，不如上下文管理器灵活（uploader 可以组合使用）。

### D4: web_runner.py 子模块提取

**决策**: 按功能域提取三个模块：
- `web_runner/ai_worker.py`：AI 模型配置、请求队列、key 池管理、内容生成
- `web_runner/scheduler.py`：`_schedule_task()`、`_scheduled_timers`、`_normalise_schedule()`
- `web_runner/error_events.py`：`_log_error_event()`、`_db_get_error_events()`

使用延迟导入避免循环依赖。

**替代方案**: 全部保留在 web_runner.py — 当前 1332 行仍在可管理范围，但继续增长会恶化可维护性。

### D5: 日志统一

**决策**: 将 `web_runner.py` 中的 `print()` 调用替换为 `_task_logger.info()`。不改变 CLI 层的 print 输出（CLI 的 print 是面向用户的 stdout 输出，非日志）。

**替代方案**: 全部用 print — 不利于日志文件持久化和级别过滤。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 通用分发器丢失平台特有逻辑 | 通过 `extra_argv_builders` 回调保留平台特化路径 |
| 上下文管理器改变异常传播 | `try/finally` 保证清理，异常正常向上传播 |
| 模块提取引入循环依赖 | 使用延迟导入（函数内 import）|
| 重构过程引入回归 bug | 先补充 dispatcher 和 uploader 的单元测试，再重构 |

## Migration Plan

1. **Phase 1**: 添加 `BaseUploadRequest` 基类（纯新增，零破坏性）
2. **Phase 2**: 重构 dispatcher 为配置驱动（修改 `cli/dispatchers.py`）
3. **Phase 3**: 添加 `managed_browser()` 上下文管理器（纯新增）
4. **Phase 4**: 逐步迁移各 uploader 使用 `managed_browser()`
5. **Phase 5**: 提取 web_runner.py 子模块
6. **Phase 6**: 统一日志

每个 Phase 独立可提交，可随时暂停。

## Open Questions

- `managed_browser()` 是否需要支持 `return_detail` 模式（login 流程需要返回详细结果）？可能需要一个变体 `managed_browser_for_login()`。
- web_runner.py 中的 `_sync_cookie_files_to_db()` 等启动时执行的函数，是否也应提取到独立模块？
