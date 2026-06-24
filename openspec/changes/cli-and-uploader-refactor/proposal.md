## Why

CLI 层和 Uploader 层存在大量重复代码：`cli/dispatchers.py` 中 7 个 `_dispatch_*` 函数结构几乎相同（378 行），`cli/models.py` 中 12 个 dataclass 重复定义 `account_name`、`publish_date`、`debug`、`headless` 等字段（187 行），各 uploader 的浏览器生命周期管理（启动、cookie 验证、关闭）也高度雷同。随着平台数量增加（当前 7 个），每新增一个平台需要复制粘贴约 100+ 行样板代码，维护成本和出错风险线性增长。

此外，`web_runner.py` 虽已拆出路由蓝图，但仍有 1332 行，AI 生成逻辑、调度器、错误事件处理等仍混杂其中；日志系统混用 `print()` 和 loguru，不一致。

## What Changes

**CLI Dispatcher 重构**
- 将 7 个 `_dispatch_*` 函数合并为一个通用 `dispatch_platform()` 函数，通过平台配置字典驱动
- 消除 `cli/dispatchers.py` 中约 200 行重复代码

**CLI Models 重构**
- 提取 `BaseUploadRequest` 基类，包含 `account_name`、`publish_date`、`debug`、`headless` 等公共字段
- 各平台请求类继承基类，只定义平台特有字段
- 消除 `cli/models.py` 中约 80 行重复定义

**Uploader 浏览器生命周期抽象**
- 在 `uploader/common.py` 中添加 `managed_browser()` 上下文管理器，统一浏览器启动、cookie 加载、stealth 注入、关闭流程
- 各 uploader 的 `upload()` 方法使用上下文管理器，减少重复的 try/finally 清理代码

**web_runner.py 继续瘦身**
- 将 AI 生成逻辑（约 200 行）提取到 `web_runner/ai_worker.py`
- 将调度器逻辑（约 50 行）提取到 `web_runner/scheduler.py`
- 将错误事件处理提取到 `web_runner/error_events.py`

**日志一致性**
- 将 `web_runner.py` 和路由中的 `print()` 调用替换为 loguru logger

## Capabilities

### New Capabilities
- `generic-cli-dispatch`: 通用 CLI 平台分发机制，通过配置字典驱动，消除逐平台样板代码
- `browser-lifecycle-mgmt`: Uploader 浏览器上下文管理器，统一 playwright 启动/关闭/cookie 加载流程

### Modified Capabilities
- `cli-models`: 提取基类，各平台请求模型继承
- `web-runner-modules`: web_runner.py 中 AI/调度/错误处理逻辑进一步模块化

## Impact

**受影响的文件**
- `cli/dispatchers.py` → 重写为通用分发逻辑
- `cli/models.py` → 提取基类，重构继承关系
- `cli/parser.py` → 小幅调整（解析逻辑不变，分发调用方式变化）
- `uploader/common.py` → 新增 `managed_browser()` 上下文管理器
- `uploader/douyin_uploader/main.py` → 使用 `managed_browser()` 简化上传流程
- `uploader/ks_uploader/main.py` → 同上
- `uploader/xiaohongshu_uploader/main.py` → 同上
- `uploader/bilibili_uploader/main.py` → 同上
- `web_runner.py` → 继续抽取 AI/调度/错误处理到子模块
- `web_runner/ai_worker.py` → 新建
- `web_runner/scheduler.py` → 新建
- `web_runner/error_events.py` → 新建

**CLI/API/Frontend 三层影响**
- CLI: 内部重构，外部命令行接口不变（`sau <platform> <action>` 不受影响）
- Web API: 无影响（Flask 路由不变）
- Frontend: 无影响
