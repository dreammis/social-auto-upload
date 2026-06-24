## Why

项目经过快速迭代，积累了多处技术债务：`web_runner.py` 膨胀到 2808 行，成为难以维护的巨型文件；`db/createTable.py` 与实际表结构脱节；前端主 chunk 690KB 影响加载性能；缺少 CI/CD 和环境配置文档。这些问题随着功能增加会持续恶化，需要系统性优化。

## What Changes

**后端重构**
- 拆分 `web_runner.py` 为模块化结构（routes、db、scheduler、ai_worker）
- 统一 DB 初始化逻辑，移除废弃的 `createTable.py`
- 为 `tasks` 表添加索引
- 添加 `.env.example` 文档化所有环境变量

**前端优化**
- 路由级懒加载减少首屏 bundle 体积
- 添加 ErrorBoundary 组件防止白屏
- 非核心库（tour、confetti）动态导入

**工程化改进**
- 添加 GitHub Actions CI/CD（lint + test + build）
- 结构化日志（JSON 格式）
- API 版本化（`/api/v1/`）

## Capabilities

### New Capabilities
- `modular-backend`: web_runner.py 模块化拆分，包含 Flask app factory、路由蓝图、DB 管理层
- `ci-pipeline`: GitHub Actions 工作流，自动运行 Python lint、前端 build、测试
- `env-documentation`: .env.example 文件，列出所有可配置环境变量及说明

### Modified Capabilities
- `database-schema`: tasks 表添加索引，统一 DB 初始化入口
- `frontend-bundle`: 路由懒加载 + ErrorBoundary + 动态导入

## Impact

**受影响的文件**
- `web_runner.py` → 拆分为 `web_runner/` 包
- `db/createTable.py` → 废弃，逻辑合并到 `web_runner/db.py`
- `sau_web/frontend/src/App.tsx` → 添加 React.lazy
- `sau_web/frontend/src/Pages/*.tsx` → 导出方式调整
- `pyproject.toml` → 可能需要更新包配置

**CLI/API/Frontend 三层影响**
- CLI: 无直接影响（CLI 入口 `sau_cli.py` 不变）
- Web API: 路由路径可能添加 `/api/v1/` 前缀（可选，向后兼容）
- Frontend: 需要适配新的 API 路径（如果版本化），添加 ErrorBoundary
