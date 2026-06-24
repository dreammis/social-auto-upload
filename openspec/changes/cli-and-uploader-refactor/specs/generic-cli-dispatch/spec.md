# generic-cli-dispatch

## Summary

配置驱动的通用 CLI 平台分发机制，通过 `PLATFORM_HANDLERS` 字典和 `_dispatch_platform()` 通用函数替代 7 个重复的 `_dispatch_*` 函数。

## Requirements

### Functional

- `PLATFORM_HANDLERS` 字典包含所有 7 个平台的配置：login/check/upload_video/upload_note 函数引用、请求类、发布策略映射、平台特有参数构建器
- `_dispatch_platform(args, handler)` 通用函数处理所有平台的 login/check/upload-video/upload-note 分发逻辑
- 平台特有参数（如 douyin 的 `--product-link`、bilibili 的 `--tid`、tencent 的 `--draft`）通过 `extra_argv_builders` 回调注入
- `dispatch(args)` 函数保持不变，内部改为查找 `PLATFORM_HANDLERS` 并调用 `_dispatch_platform`
- 新增平台只需：(1) 创建 `cli/platforms/<platform>.py` (2) 在 `PLATFORM_HANDLERS` 中添加一行配置

### Non-Functional

- 外部 CLI 接口不变（`sau <platform> <action>` 命令行语法不变）
- 不改变 `cli/parser.py` 的参数解析逻辑
- 不改变各 `cli/platforms/*.py` 模块的函数签名

## Acceptance Criteria

- [ ] `cli/dispatchers.py` 行数从 378 行减少到 <200 行
- [ ] 7 个 `_dispatch_*` 函数合并为 1 个 `_dispatch_platform` 函数
- [ ] 所有现有 CLI 命令（`sau douyin login`、`sau bilibili upload-video` 等）行为不变
- [ ] 平台特有参数（`--product-link`、`--tid`、`--draft`、`--short-title` 等）仍然正常工作
- [ ] `pytest tests/` 全部通过
