# 历史 Web 版本说明

历史 Web 代码（`sau_backend.py` + `sau_backend/` + `myUtils/`）已移至 `legacy/` 目录存放。

对应的 Vue 前端 `sau_frontend/` 已从当前工作区删除。

## 当前定位

- 已移入 `legacy/` 目录作历史存档
- 作为过去 API / Web 封装思路的参考
- 不承诺当前可直接运行
- 不承诺和当前 `uploader/`、`sau_cli.py`、`web_runner.py` 的最新实现完全同步

## 当前推荐入口

如果你要使用当前主线能力，优先看：

- `uploader/` — 核心平台实现
- `sau_cli.py` — CLI 主入口
- `web_runner.py` + `sau_web/frontend` — Web Shell（React + Flask，封装 CLI）
- `skills/` — 面向 agent 的 skill

当前 Web Shell 统一通过 `web_runner.py` 提供服务，不再使用旧 `sau_backend.py`。
