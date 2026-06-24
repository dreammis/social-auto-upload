## Why

当前 AI 内容生成面板以右侧固定 sidebar（`xl:col-span-1`）的形式嵌入在发布中心页面中。随着功能不断堆叠（API Key 管理、模型选择、输入区、附件上传、模板库、生成按钮、进度条、流式输出、结果展示、历史记录等），1/3 宽度的垂直空间信息密度过高，模块之间缺乏呼吸感，用户每步操作都可能导致页面纵向剧烈跳动，视觉体验拥挤不堪。

需要将 AI 面板从右侧 sidebar 迁移到底部抽屉面板（Bottom Panel / Drawer），赋予 AI 内容生成专属的全宽舞台，彻底解决拥挤问题。

## What Changes

- **布局重构**：移除 PublishPage 右侧 AI sidebar 占位，改为底部可展开/收起的抽屉面板
- **AiSidebar 组件重构**：将当前 `Card` 容器改为底部固定面板，支持 `collapsed` / `expanded` 两种状态
- **表单区域扩展**：PublishPage 主表单区域从 `xl:col-span-2` 恢复为全宽布局
- **结果展示优化**：底部全宽空间允许结果区以多列或更舒展的方式展示
- **动画过渡**：面板展开/收起使用 Framer Motion `animatePresence` 实现平滑高度过渡
- **触发入口**：在表单区域底部（或顶部工具栏）放置一个常驻的 "AI 助手" 触发按钮

## Capabilities

### New Capabilities

- `ai-bottom-panel`: 底部抽屉式 AI 面板，支持展开/收起/拖拽调整高度
- `ai-panel-resize`: 用户可拖拽面板顶部边缘调整面板高度
- `ai-panel-pin`: 支持固定/取消固定面板状态

### Modified Capabilities

- `ai-content-generation`: 从右侧 sidebar 迁移到底部面板，交互流程不变
- `publish-page-layout`: 发布中心页面布局从 2+1 列改为全宽表单 + 底部面板

## Impact

- **Frontend**: 大幅重构 `PublishPage.tsx` 布局、`AiSidebar.tsx` 容器结构
- **依赖**: 无新增依赖（已使用 Framer Motion）
- **Break Change**: 右侧 `PublishOverview` / `PublishPreview` 组件需要重新安置（移至表单内或底部面板内嵌区域）
