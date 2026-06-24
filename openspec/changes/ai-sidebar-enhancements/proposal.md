## Why

AI 内容生成基础功能已上线，但存在明显体验短板：prompt 不感知目标平台特性、不感知已上传内容、生成结果无法对比选择、用户无法自定义 prompt。需要增强这些能力以提供真正实用的 AI 辅助创作体验。

## What Changes

- 平台感知 Prompt：根据目标平台（抖音/B站/小红书等）自动调整生成策略
- 生成历史记录：保存多次生成结果，用户可对比选择最佳内容
- 自定义 Prompt 模板：用户可创建和管理常用 prompt 模板
- 一键优化：对已生成内容的特定部分（标题/描述/标签）单独优化
- 流式响应 (SSE)：实时展示生成过程，替代当前的 loading 等待
- 并发队列可见性：显示排队位置和预估等待时间

## Capabilities

### New Capabilities

- `ai-platform-prompts`: 平台感知 prompt 策略，根据目标平台自动调整生成风格
- `ai-generation-history`: 生成历史记录，支持多次结果对比选择
- `ai-prompt-templates`: 自定义 prompt 模板管理
- `ai-content-optimization`: 一键优化已生成内容的特定部分
- `ai-streaming-response`: SSE 流式响应，实时展示生成过程

### Modified Capabilities

- `ai-content-generation`: 集成平台感知、历史记录、模板、优化、流式等增强功能

## Impact

- **Web API**: 修改 `/api/ai/generate` 支持 SSE 流式响应和平台参数
- **Frontend**: 增强 AiSidebar 组件，新增历史面板、模板管理、优化按钮
- **依赖**: 无新增依赖
