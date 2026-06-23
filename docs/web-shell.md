# Web Shell 可视化界面

social-auto-upload 提供了一个可选的可视化 Web 界面（Web Shell），基于 React + Flask 构建，封装 CLI 能力提供图形化管理。

## 快速启动

### 方式一：一键启动（推荐）

```bash
bash sau_web/start.sh
```

该脚本会自动检查依赖、安装缺失包、启动后端和前端开发服务器。

### 方式二：手动启动

#### 1. 安装依赖

```bash
# Python 后端依赖
uv pip install -e ".[web]"

# React 前端依赖
cd sau_web/frontend && npm install
```

#### 2. 启动后端

```bash
python web_runner.py
```

后端运行在 `http://localhost:6001`。

##### CORS 配置（必读）

后端默认 **禁用** CORS。前端跨域访问 `/api/*` 必须显式设置环境变量 `SAU_CORS_ALLOWED_ORIGINS`，值为逗号分隔的 来源 列表（包含 scheme 与端口，例如 `http://localhost:5174`）。

本地开发示例（在 shell 启动后端前设置）：

```bash
export SAU_CORS_ALLOWED_ORIGINS="http://localhost:5173,http://localhost:5174"
python web_runner.py
```

未设置（或值为空）时，后端只会记录一条 warning 并拒绝所有跨域请求，前端 API 调用会报 CORS 错误。

#### 3. 启动前端（开发模式）

```bash
cd sau_web/frontend && npm run dev
```

前端运行在 `http://localhost:5174`，自动代理 API 到后端。

#### 4. 生产构建

```bash
cd sau_web/frontend && npm run build
```

构建产物在 `sau_web/frontend/dist/`，后端会自动提供 `GET /` 服务。

## 页面功能

| 页面 | 路由 | 功能 |
|---|---|---|
| 账号管理 | `/` | 查看已保存账号、筛选平台、登录新账号、删除账号 |
| 发布中心 | `/publish` | 视频/图文表单提交，选择平台和账号，设置定时发布 |
| 运行日志 | `/logs` | 日志查看、过滤、关键字搜索、导出 |
| 任务列表 | `/tasks` | 任务状态追踪、轮询更新、筛选排序 |

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/accounts` | 列出已保存账号 |
| POST | `/api/accounts/login` | 触发账号登录 |
| POST | `/api/accounts/check` | 检查单个账号 Cookie 有效性 |
| POST | `/api/accounts/check-all` | 批量检查所有账号 Cookie |
| POST | `/api/accounts/delete` | 删除已保存账号 |
| POST | `/api/upload/video` | 视频上传（支持 headless、抖音商品、B站 tid、视频号短标题/分类/草稿） |
| POST | `/api/upload/note` | 图文上传（支持 JSON data URI 和 multipart 文件上传两种模式） |
| GET | `/api/tasks` | 任务状态列表 |
| POST | `/api/tasks/retry` | 重试失败/异常任务 |
| GET | `/api/logs` | 运行日志（支持 after / task_id 过滤） |
| GET | `/health` | 健康检查 |

## 注意事项

- Web Shell 为单用户桌面场景设计，不包含用户系统/RBAC
- 所有上传任务实际由 `sau_cli.py` 的 CLI 逻辑在后台线程中执行
- 日志存储于 SQLite 数据库，重启后端不丢失（自动清理超过 2000 条的旧日志）
- 需先登录账号（通过 CLI 或 Web Shell 的登录表单）才能发布
- 所有平台、特性已统一收敛到 `PLATFORM_CONFIG` 字典管理，不再依赖硬编码集合
