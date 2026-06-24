## Why

用户在发布中心手动编写帖子内容（标题、描述、标签）效率低下，尤其在多平台批量发布时重复劳动严重。集成 AI 内容生成功能可以让用户一键自动生成高质量的帖子文本，显著提升发布效率。

## What Changes

- 在 PublishPage 右侧边栏新增 AI 内容生成模块
- 集成 OpenRoute API（免费 API 密钥），支持多种 AI 模型选择
- 实现轮询机制管理 API 请求，支持无限次调用无单次限制
- 用户可从下拉菜单选择不同 AI 模型（如 GPT-4o-mini、Claude-3-haiku 等）
- 一键生成标题、描述、标签等内容，自动填充到发布表单

## Capabilities

### New Capabilities

- `ai-content-generation`: AI 内容生成模块，包含 OpenRoute API 集成、模型选择、轮询请求管理、内容生成 UI

### Modified Capabilities

- `frontend-polish`: PublishPage 右侧边栏布局调整，集成 AI 模块组件

## Impact

- **Frontend**: PublishPage 新增右侧边栏 AI 模块（新组件 + API 调用）
- **Web API**: 新增 `/api/ai/generate` 端点代理 OpenRoute API 请求（避免前端暴露 API 密钥）
- **依赖**: 新增 `requests` 或复用现有 HTTP 客户端调用 OpenRoute API
- **配置**: 需要 OpenRoute API 密钥配置（环境变量或配置文件）
