## Context

`web_runner.py` 是项目的 Web 后端入口，当前 2808 行，包含 Flask 路由、DB 初始化、SSE 流、AI 生成、任务调度等所有逻辑。随着功能增加，维护成本线性增长。

前端 bundle 主 chunk 690KB（gzip 211KB），首屏加载较慢。无 CI/CD，无环境变量文档。

## Goals / Non-Goals

**Goals:**
- 将 web_runner.py 拆分为可维护的模块结构
- 减少前端首屏加载体积 30%+
- 建立自动化 CI 流程
- 文档化所有环境变量

**Non-Goals:**
- 不改变现有 API 行业（保持向后兼容）
- 不重构 uploader 模块（已有 cli/ 拆分）
- 不迁移到其他数据库（保持 SQLite）
- 不重写前端 UI

## Decisions

### D1: Flask App Factory 模式

**决策**: 使用 `create_app()` 工厂函数，将路由注册为 Blueprint。

**理由**: Flask 官方推荐模式，便于测试和多实例。Blueprint 按功能域分组（accounts、upload、tasks、ai）。

**替代方案**: 直接在 `__init__.py` 中 import 所有路由 — 简单但不解决循环依赖问题。

### D2: DB 管理独立模块

**决策**: 创建 `web_runner/db.py`，统一 DB 连接、表创建、索引管理。

**理由**: 当前 DB 逻辑散落在 web_runner.py 多处（初始化、连接、锁管理）。统一后便于添加迁移。

**替代方案**: 使用 SQLAlchemy — 过度工程，SQLite 单文件场景不需要 ORM。

### D3: 前端路由级懒加载

**决策**: 使用 `React.lazy` + `Suspense` 按路由拆分 chunk。

**理由**: 首屏只需要 AccountsPage，其他页面按需加载。Vite 原生支持动态 import。

**替代方案**: 手动 `import()` — 等价，但 React.lazy 提供更好的错误边界集成。

### D4: CI 用 GitHub Actions

**决策**: 添加 `.github/workflows/ci.yml`，运行 Python lint + test + frontend build。

**理由**: 零成本、与 GitHub 深度集成。覆盖最关键的三个检查点。

**替代方案**: GitLab CI / Jenkins — 项目托管在 GitHub，Actions 最自然。

### D5: 不做 API 版本化

**决策**: 本轮不添加 `/api/v1/` 前缀。

**理由**: 当前 API 只有一个前端客户端，版本化增加复杂度但无实际收益。未来有第三方集成需求时再加。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 拆分过程中引入回归 bug | 先补充测试覆盖关键路径，再拆分 |
| 懒加载增加路由切换延迟 | 添加 loading skeleton，预加载相邻路由 |
| SQLite 并发写入冲突 | 保持现有 db_lock 机制，后续可考虑 WAL 模式 |
| 环境变量遗漏 | .env.example 从代码中自动提取所有 `os.environ.get()` 调用 |

## Migration Plan

1. **Phase 1**: 拆分 web_runner.py（不影响外部 API）
2. **Phase 2**: 前端懒加载（纯前端改动）
3. **Phase 3**: 添加 CI + .env.example（新增文件，零破坏性）

每个 Phase 独立可部署，可随时暂停回滚。

## Open Questions

- 是否需要将 Flask 开发服务器替换为 Gunicorn？（生产部署相关，本轮不处理）
- 前端是否需要 PWA 支持？（独立 feature，不在本次范围）
