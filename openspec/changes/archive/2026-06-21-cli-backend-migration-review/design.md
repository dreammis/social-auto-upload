## Context

social-auto-upload 项目已完成从纯 CLI 到 Web 后端 + 前端 UI 的迁移。当前架构：
- **CLI 层** (`sau_cli.py` + `uploader/`): 7 个平台的 Playwright 浏览器自动化上传
- **Web API 层** (`web_runner.py`): Flask 后端，通过 `_run_sau()` 调用 CLI 逻辑
- **Frontend 层** (`sau_web/frontend/`): React 18 + TypeScript + Ant Design 5

迁移后核心功能可用，但审查发现 28 个 CLI 问题、12 个 API 问题、30 个前端问题。本设计文档定义修复和优化的技术方案。

## Goals / Non-Goals

**Goals:**
- 修复所有已知 bug（无限循环、线程安全、死代码、内存泄漏）
- 提升 CLI 代码质量和可维护性（提取共享模块、表驱动分发）
- 增强 API 可靠性（线程安全、异常处理、请求限制）
- 打磨前端体验（拖拽上传、错误边界、分页、性能优化）
- 保持向后兼容，不破坏现有功能

**Non-Goals:**
- 不添加新的平台支持
- 不重构数据库 schema
- 不添加用户认证/权限系统（当前为单用户本地工具）
- 不重写前端 UI 框架或组件库
- 不修改 Bilibili 的 `biliup` 二进制调用方式

## Decisions

### D1: CLI 共享模块提取方案

**决策**: 在 `uploader/` 下创建 `uploader/common.py`，提取重复的 `_msg()`、`_emit_qrcode_callback()`、`_build_login_result()` 函数。

**替代方案**:
- A) 在 `utils/` 下创建共享模块 → 路径过深，`uploader/` 内的模块更直观
- B) 创建基类 `BasePlatformUploader` → 过度设计，这些是独立函数而非类方法

**理由**: 函数级提取最小化侵入性，各平台上传器只需修改 import。

### D2: dispatch() 重构为表驱动

**决策**: 创建 `PLATFORM_REGISTRY` 字典，将平台→动作→处理函数的映射关系数据化。dispatch() 变为查找表 + 统一调用。

```python
PLATFORM_REGISTRY = {
    "douyin": {
        "login": login_douyin_account,
        "check": check_douyin_account,
        "upload-video": upload_douyin_video,
        "upload-note": upload_douyin_note,
    },
    # ...
}
```

**替代方案**:
- A) 使用插件系统（importlib 动态加载）→ 过度复杂，当前不需要插件化
- B) 使用装饰器注册 → 需要修改所有平台函数签名，侵入性大

**理由**: 表驱动是最小改动方案，保持现有函数签名不变。

### D3: 无限循环修复策略

**决策**: 为所有 `while True` 循环添加 `max_retries` 参数，使用指数退避（从 0.5s 起，最大 5s）。

各平台当前状态：
- Douyin: 已有 `max_publish_attempts = 30` ✓
- Kuaishou: 已有 `max_retries = 60` ✓
- TikTok: 已有 `max_retries = 180` ✓
- Xiaohongshu: 4 处无限循环需修复
- Tencent: 2 处无限循环需修复
- Baijiahao: 使用 `@async_retry(timeout=300)` ✓

**理由**: 统一重试模式，避免浏览器进程泄漏。

### D4: API 线程安全方案

**决策**: 为 `_scheduled_timers` 添加 `threading.Lock` 保护。所有对字典的读写操作都在 `with _timer_lock:` 块中执行。

**替代方案**:
- A) 使用 `concurrent.futures.ThreadPoolExecutor` 替代手动 Timer → 需要重构调度逻辑
- B) 使用 `asyncio` 替代线程 → Flask 同步框架不适用

**理由**: 最小改动，`threading.Lock` 是 Python 标准库，无额外依赖。

### D5: SSE 上传进度推送

**决策**: 复用现有 SSE 模式（`login_account_sse` 的 `queue.Queue` + Flask generator），为上传任务添加 `/api/upload/progress?task_id=<id>` SSE 端点。

**替代方案**:
- A) WebSocket → 需要额外依赖（flask-sock），当前轮询方案可用
- B) Server-Sent Events with Redis → 过度复杂，单进程不需要 Redis

**理由**: 复用现有模式，最小化新代码。

### D6: 前端死代码清理策略

**决策**: 一次性删除所有已识别的死代码，不保留兼容层。

删除清单：
- `useAccounts` hook（未使用）
- `PLATFORMS_WITH_ICONS`（空别名）
- `PageTransition`（未使用）
- `PageLoading.tsx`（重复定义）
- `Spinner`（未使用）
- `message` API in `toast.tsx`（死事件）
- `uploadNote` JSON 版本（未使用）

**理由**: 这些代码从未被引用，删除不影响任何功能。

### D7: PublishPage 表单状态管理

**决策**: 提取 `usePublishForm` 自定义 hook，将 25+ `useState` 合并为结构化状态对象 + reducer。

**替代方案**:
- A) 使用 react-hook-form → 需要新依赖，且当前表单逻辑与 UI 紧耦合
- B) 使用 Zustand store → 跨页面共享不需要，表单状态是页面级的

**理由**: 自定义 hook 无新依赖，保持现有架构模式。

### D8: 日志分页方案

**决策**: 后端添加 `limit` 和 `offset` 参数，前端使用 TanStack Query 的 `useInfiniteQuery` 实现无限滚动。

**替代方案**:
- A) 传统分页（页码 + 每页数量）→ 日志是时间序列数据，无限滚动更自然
- B) 虚拟滚动（react-virtuoso）→ 可选增强，但分页是前提

**理由**: 无限滚动匹配日志查看习惯，TanStack Query 原生支持。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| CLI dispatch 重构可能引入回归 | 保持现有函数签名不变，仅修改分发逻辑；逐平台测试 |
| SSE 进度端点增加连接数 | 限制最大并发 SSE 连接数（5），添加超时（5min） |
| 删除死代码可能遗漏隐藏依赖 | 使用 IDE 的 "Find Usages" 逐一确认，CI 跑全量测试 |
| 分页参数可能影响 FloatingLogs | FloatingLogs 使用 `after` 时间戳过滤，与 limit/offset 独立 |
| 表单 hook 重构可能破坏 UI 行为 | 保持相同的 state 结构和 setter 行为，逐步迁移 |

## Migration Plan

1. **Phase 1 - CLI 硬化** (低风险): 无限循环修复、死代码清理、共享模块提取
2. **Phase 2 - API 可靠性** (中风险): 线程安全、异常处理、请求限制
3. **Phase 3 - dispatch 重构** (中风险): 表驱动分发，需要逐平台验证
4. **Phase 4 - 前端打磨** (低风险): 死代码清理、错误边界、404 路由
5. **Phase 5 - 前端增强** (中风险): 拖拽上传、表单重构、分页

每个 Phase 独立可部署，可按优先级调整顺序。

## Open Questions

- Bilibili cookie 格式覆盖问题（note 上传后覆盖 video 的 biliup 格式）是否需要统一 cookie 格式？
- 前端是否需要添加文件大小限制的配置项（通过环境变量或 API 返回）？
- SSE 上传进度是否需要包含百分比（需要上传器配合报告进度）？
