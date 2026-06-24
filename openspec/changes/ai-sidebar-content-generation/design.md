## Context

当前 PublishPage (`/publish`) 提供视频/笔记上传表单，用户需手动填写标题、描述、标签等内容。项目使用 React 18 + TypeScript + Ant Design 5 + Zustand + TanStack Query 构建前端，Flask 提供后端 API。

本变更在 PublishPage 右侧边栏集成 AI 内容生成模块，通过 OpenRoute API 自动生成帖子文本内容。

## Goals / Non-Goals

**Goals:**
- 在 PublishPage 右侧边栏添加 AI 内容生成面板
- 集成 OpenRoute API，使用免费 API 密钥
- 实现轮询机制管理并发请求，支持无限次调用
- 提供模型选择下拉菜单
- 生成内容自动填充到发布表单

**Non-Goals:**
- 不实现 AI 图片生成
- 不实现自定义 prompt 模板编辑器
- 不在 CLI 中添加 AI 功能
- 不存储用户对话历史

## Decisions

### 1. API 密钥管理：后端代理模式

**决定**: 前端不直接调用 OpenRoute API，而是通过 Flask 后端 `/api/ai/generate` 代理请求。

**理由**: 
- 避免前端暴露 API 密钥
- 统一错误处理和日志记录
- 便于后续切换 AI 提供商

**替代方案**: 前端直接调用 OpenRoute API（拒绝：密钥暴露风险）

### 2. 轮询机制：请求队列 + 速率限制

**决定**: 后端实现请求队列，使用 `threading.Semaphore` 控制并发，每次请求完成后从队列取下一个。

**理由**:
- OpenRoute 免费 tier 有速率限制（如 20 req/min）
- 轮询机制确保不会触发限流
- 支持无限次调用，只是排队等待

**替代方案**: 前端直接重试（拒绝：无法控制全局速率）

### 3. 模型选择：配置驱动

**决定**: 在 `web_runner.py` 中定义 `AI_MODELS` 字典，前端通过 `/api/ai/models` 获取可用模型列表。

**理由**:
- 模型列表可能变化，配置驱动便于维护
- 前端无需硬编码模型 ID

### 4. 前端状态管理：Zustand store

**决定**: 创建 `useAiStore` 管理 AI 模块状态（选中模型、生成状态、队列位置）。

**理由**:
- 遵循项目现有 Zustand 模式
- 轻量级状态不需要 TanStack Query 的缓存

## Risks / Trade-offs

- **[OpenRoute 免费 tier 限制]** → 轮询机制 + 用户提示"排队中"
- **[API 不可用]** → 优雅降级：显示错误提示，不阻塞发布流程
- **[生成内容质量]** → 提供"重新生成"按钮，用户可多次尝试
- **[网络延迟]** → 显示加载状态 + 预估等待时间

## Migration Plan

无需迁移。新增功能，不影响现有发布流程。

## Open Questions

- OpenRoute 免费 API 密钥的获取方式？（需用户提供或内置测试密钥）
- 是否需要支持流式响应（SSE）以提升用户体验？
