## Why

当前项目主要依赖 `sau` CLI 和 `skills/`，没有可用的可视化界面。项目仓库里虽有遗留 Web 版本，但已明确标注为 legacy，不再同步维护。为了最快速实现可视化，需要新增一个最小 Web 壳：前端用 Vue + Vite，后端用 Flask，直接复用现有 `sau_cli.py` 的核心能力，不需要重复实现业务逻辑。

## What Changes

- 新增轻量 Flask 后端入口 `web_runner.py`（或同级类似入口）
- 基于现有 `sau_frontend/` 源码调整并接入后端接口
- 实现最小页面：账号登录、查看账号状态、上传视频、上传图文、定时发布表单、日志/进度展示
- 保留绕过遗留 `sau_backend/`，不依赖其运行态
- 最终可继续走 PyInstaller / Briefcase 打成桌面 App，当前阶段先以本地 Web 形态跑通

## Capabilities

### New Capabilities
- `web-shell`: 可视化前端壳，账号管理 + AI Agent 调度 + 定时发布 + 日志流

### Modified Capabilities
- 无（本变更不修改现有 uploader 的核心行为，只新增外壳）

## Impact

Affected code/files:
- 新增：`web_runner.py`
- 复用/调整：`sau_frontend/`（Vue 3 + Vite）
- 新建：`web_app/` 结构或平级新入口
- 不修改现有 `sau_cli.py` / `uploader/` 主流程（只调用）

Dependencies:
- Python 3.10+（现有）
- Flask（用于最小后端，可选以 [`project.optional-dependencies.web`](pyproject.toml:23) 中的 asgiref / flask-cors 兼容方式安装）
