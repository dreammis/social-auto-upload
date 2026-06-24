## Context

AI 内容生成基础功能已实现（`ai-sidebar-content-generation` change），包括 OpenRoute API 集成、模型选择、一键生成、请求队列。当前实现存在体验短板，需要增强。

## Goals / Non-Goals

**Goals:**
- 根据目标平台自动调整 AI 生成策略
- 保存生成历史，支持对比选择
- 支持自定义 prompt 模板
- 支持对已生成内容的部分优化
- SSE 流式响应替代同步等待

**Non-Goals:**
- 不实现 AI 图片生成
- 不实现多轮对话
- 不实现用户登录/账户体系

## Decisions

### 1. 平台感知 Prompt：配置表驱动

在 `web_runner.py` 中定义 `PLATFORM_PROMPTS` 字典，每个平台有不同的 system prompt 和风格指导。后端根据请求中的 `platform` 参数自动拼接。

### 2. 流式响应：复用现有 SSE 基础设施

后端已有 SSE 端点模式（`/api/accounts/login/sse`, `/api/upload/progress`）。新增 `/api/ai/generate/stream` SSE 端点，前端使用 `EventSource` 接收。

### 3. 生成历史：前端 localStorage 存储

历史记录存储在浏览器 localStorage，按平台+日期索引。不存后端数据库，避免隐私问题。

### 4. Prompt 模板：前端 localStorage 存储

模板同样存 localStorage，支持创建、编辑、删除、使用。

### 5. 一键优化：复用 generate 端点

优化请求本质上是新的生成请求，只是 prompt 不同（"请优化以下标题..."）。复用同一端点，前端构造优化 prompt。

## Risks / Trade-offs

- **[SSE 连接数限制]** → 流式响应完成即关闭，不保持长连接
- **[localStorage 容量]** → 历史记录限制 50 条，自动清理旧记录
- **[平台 prompt 维护]** → 配置表便于修改，但需要人工维护质量
