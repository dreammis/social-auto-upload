# browser-lifecycle-mgmt

## Summary

在 `uploader/common.py` 中提供 `managed_browser()` 异步上下文管理器，统一各 uploader 的 patchright 浏览器启动、cookie 加载、stealth JS 注入和关闭流程。

## Requirements

### Functional

- `managed_browser(account_file, headless=True)` 异步上下文管理器：
  - 启动 patchright chromium 浏览器
  - 创建 context 并加载 `account_file` cookie（`storage_state`）
  - 注入 `stealth.min.js`（通过 `set_init_script()`）
  - yield context 给调用方
  - 退出时自动 `context.close()` + `browser.close()`
- `managed_browser_for_login(headless=True)` 变体：
  - 不加载 cookie（新登录流程）
  - yield `(context, browser)` 供 login 流程在登录成功后保存 cookie
- 各 uploader 的 `upload()` 方法逐步迁移到 `async with managed_browser(...)` 模式

### Non-Functional

- 不改变 uploader 的上传逻辑和页面交互代码
- 不改变 cookie 文件格式
- 异常时保证浏览器资源清理（`finally` 块）

## Acceptance Criteria

- [ ] `uploader/common.py` 新增 `managed_browser()` 和 `managed_browser_for_login()` 函数
- [ ] 至少 2 个 uploader（douyin、kuaishou）迁移使用 `managed_browser()`
- [ ] 每个迁移的 uploader 减少约 20-30 行重复的浏览器生命周期代码
- [ ] 异常场景下浏览器正确关闭（不残留 chromium 进程）
- [ ] `pytest tests/` 全部通过
