## Context

当前项目以 `sau` CLI 为主入口，已有 `sau_cli.py` 和 `uploader/` 核心能力。可视化需求只追问“怎么最快看到界面”，并把体验收敛到可打包的用法。技术前提是 Mac 开发环境已有 Python、Node.js 和前端目录，因此优先复用现有前端生态，避免从零开始。

操作第一步已确认可用：
- 生成 `conf.py` 解缺模块
- 修复 Chrome 通道依赖，`patchright install chromium` 成功
- 抖音登录 CLI 成功，cookie 已写出到 `cookies/douyin_xiandnahuang.json`
- Node 版本 14 可用，`sau_frontend/` 依赖未安装，`npm run dev` 当前不可直接使用

## Goals / Non-Goals

**Goals**
- 在现有 `sau_frontend/` 上最小改动，补出可跑通的 Flask 后端，支撑账号登录和上传流程可视化
- 让前端能直接触发调用，并看到最小可用页面
- 若后续需要，可演进到桌面 App 打包，但当前阶段只做本地 Web

**Non-Goals**
- 不重启或修改 `sau_cli.py` / `uploader/` 核心逻辑
- 不依赖已废弃的 `sau_backend/`、数据库初始化、SSE 等历史机制
- 不做移动端适配、高级权限、完整工作流引擎

## Decisions

**1. 前端采用 React 技术栈，新建独立前端工程**
- 使用 Vite + React + TypeScript 脚手架新建前端应用，放到 `sau_web/frontend` 目录
- UI 组件库选 Ant Design（Element Plus 是 Vue 栈，避免混栈）
- 路由使用 `react-router-dom`
- HTTP 请求使用 `axios`，自建统一拦截器
- 不再沿用不适配的 `sau_frontend/`（Vue 壳），避免混栈增加复杂度

**2. 后端 Flask 最小壳，直接调用 `sau_cli.dispatch`**
- 采用子进程方式调用 `sau_cli.main`，提供以下接口：
  - `POST /api/accounts/login`
  - `GET /api/accounts`
  - `POST /api/upload/video`
  - `POST /api/upload/note`
- 账号数据直接从现有 `cookies/` 目录读取
- 任务/日志在内存 ring buffer 中维护，仅 Web 发起的任务进入

**3. 任务发起边界：B1 模式（CLI 与 Web 分离）**
- **Web 发起**：任务进入 ring buffer，`/api/tasks` 和 `/api/logs` 可见，Web 实时展示
- **CLI 发起**：用户在终端直接运行 `sau ...`，stdout 仅在终端可见，Web 端不可见
- **共享层**：双方都读写 `cookies/*.json`，账号状态天然一致
- **不引入**：`tasks/` 状态文件、CLI→Web 的状态同步、Redis/数据库

**4. 前端新增一个 `WebShellAPI` 层，映射到后端接口**
- 账号状态、任务列表、日志流通过统一 response shape `{ success, data, message }` 返回

## Risks / Trade-offs

- **R1: 后端通过子进程调用 CLI，没有完善的并发并发控制，多并发上传可能异常**
  - 先接受单操作串行限制；
  - 后续可加简单的后端运行队列；
  - 当前在个人使用场景下风险可控。

- **R2: 前端页面默认期望的是 `localhost:5409`，与改壳端口可能不一致**
  - 把 Flask 端口直接固定到 `5409`，或在 `.env.development` 里改为 `http://localhost:5000`；
  - 推荐前端环境变量配置为 `VITE_API_BASE_URL=http://localhost:5409`，与 `requests.js` 保持一致。

- **R3: 浏览器自动化（`patchright`）依赖本机 GUI 环境，打包成单文件后可能丢失浏览器运行时**
  - 后续 PyInstaller 打包阶段再处理 `patchright` 二进制路径和缓存目录。

## Context (Extension)

- `pyproject.toml` 的 `[project.optional-dependencies]` 里已有 `web = [Flask[async], flask-cors]`，可直接 `pip install ".[web]"`。
- 当前 `uv pip install -e .` 已把核心包装好；再加 `.[web]` 支起后端即可。
- 前端目录 `sau_frontend/` 与后端 protcol 的联系点只有 `utils/request.js` 的 baseURL。
