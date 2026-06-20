# Web Shell Specification

## Overview

提供一个最小可视化 Web 界面，覆盖账号状态、视频上传、图文发布、定时发布表单及运行日志。前端采用独立 React 应用；后端提供最小 Flask shell，直接调用现有 CLI 能力，不修改核心 uploader 逻辑。

## Functional Requirements

1. Accounts
   - 列出已保存Cookie账号状态（valid/invalid）
   - 触发账号登录，返回二维码/登录完成状态
   - 账号状态实时刷新
2. Publish Center
   - 支持视频上传表单（平台选择、文件、标题、描述、标签、定时时间、封面）
   - 支持图文上传表单（平台选择、图片列表、标题、正文、标签、定时时间）
   - 提交后返回任务ID、日志流端点
3. Logs/Progress
   - SSE 或轮询接口，展示后端任务进度/结果
4. Platforms to support in shell
   - douyin
   - kuaishou
   - xiaohongshu
   - bilibili

## API Requirements

- `GET /api/accounts`
  - 返回已存在 account 文件列表及验证状态
- `POST /api/accounts/login`
  - body: `{ platform, account, headed: boolean }`
  - 返回 `{ success, message, account_file }`
- `POST /api/upload/video`
  - body: `{ platform, account, fileBase64?, file?, title, desc, tags, schedule?, ... }`
- `POST /api/upload/note`
  - body: `{ platform, account, files?, title, note, tags, schedule?, ... }`

## Interface UX Requirements

- 前端运行在开发模式 `http://localhost:5173`，生产模式由 Vite 构建为静态文件
- 后端提供 `GET /` 返回前端 index.html，并在 `/api/*` 负责转调 CLI
- 账号、上传表单、日志三个页面最小可访问路径 `/accounts /publish /logs`
- 悬浮日志面板：在任何页面右下角显示实时日志，支持拖动和缩放，不遮挡主内容
  - 初始位置：右下角，尺寸约 480x300px
  - 可通过标题栏拖拽移动位置
  - 可通过右下角 resize handle 调整大小
  - 支持最小化/展开
  - 自动滚动到最新日志
  - 支持简单的文本过滤
- 全中文界面
- 移动端/H5 适配：栅格响应式，底部 Tab 导航（手机端）/侧边栏（桌面端）

## Out of Scope

- 不做用户系统、RBAC、授权
- 不集成历史 `sau_backend/`、数据库、历史 API 契约
- 不做完整打包、PyInstaller（后续迭代）

## Non-functional Requirements

- 单用户桌面场景，允许同一时间单任务串行上传
- 失败/异常消息原样展示，不做额外持久化
- 编码 utf-8；日志保留标准输出
