## Why

发布中心当前的 AI 助手位于页面底部抽屉（AiPanel），需要手动展开才能使用，与表单区域分离导致填写-生成-预览的工作流断裂。将 AI 助手移至右侧常驻面板，可实现"左侧填写表单、右侧 AI 辅助"的并行工作模式，减少上下滚动，提升发布效率。

## What Changes

- 将 AI 助手从底部固定抽屉（`AiPanel`）改为右侧常驻侧栏，替换当前的预览面板位置
- 调整主内容区与 AI 面板的宽度比例为 **2:3（40%:60%）**，AI 区域更宽以容纳生成结果、模板、历史等功能
- 预览功能整合到 AI 面板内部（作为 AI 面板的子 Tab 或折叠区域）
- 移动端（视口 < 768px）：AI 助手改为从下往上的抽屉式展开（保留现有 AiPanel 的移动端行为）
- 桌面端：维持左右双栏布局，移除底部 AiPanel 固定栏

## Capabilities

### New Capabilities

- `publish-ai-sidebar-layout`: 发布页面 AI 助手右侧常驻面板布局，包含响应式适配（桌面左右双栏 / 移动端底部抽屉）

### Modified Capabilities

- `frontend-polish`: 发布页面布局从"全宽表单 + 底部 AI 抽屉"变为"左窄表单 + 右宽 AI 面板"

## Impact

- **Frontend**: 
  - `PublishPage.tsx` — 主布局重构（grid 比例、移除 AiPanel 底部固定）
  - `AiPanel.tsx` — 可能废弃或重构为桌面端内联组件
  - `AiPanelToolbar.tsx` — 不再需要底部 toolbar，功能合并到侧栏头部
  - `PublishPreview.tsx` — 从独立侧栏移入 AI 面板内部
  - 新增 `AiRightPanel.tsx` 或类似组件承载右侧布局
  - 响应式断点：`md`（768px）以下切为底部抽屉
- **Web API**: 无变更
- **CLI**: 无变更
