## Context

当前发布中心（`PublishPage`）的布局为：
- 上方：PageHeader + Overview stats
- 中间：全宽表单（VideoForm / NoteForm）
- 底部：固定 AI 抽屉面板（`AiPanel`，48px toolbar + 可展开 drawer）
- 右侧预览：仅在 `lg` 断点以上以 sticky 侧栏显示（`PublishPreview`）

问题：
1. AI 助手需要手动展开底部抽屉才能使用，与表单填写流程断裂
2. 预览面板占据右侧但功能单一，空间利用率低
3. 底部 AiPanel 固定 48px 高度，压缩了表单的可视区域

## Goals / Non-Goals

**Goals:**
- AI 助手在桌面端常驻右侧，与表单并行显示
- 左右比例 2:3（40%:60%），AI 区域更宽
- 移动端（<768px）保留底部抽屉行为
- 预览功能整合到 AI 面板内
- 移除底部 AiPanel 固定栏，回收屏幕空间

**Non-Goals:**
- 不改变 AI 助手的内部功能（模型选择、生成、模板等）
- 不改变 VideoForm / NoteForm 的字段逻辑
- 不涉及后端 API 变更
- 不改变其他页面的布局

## Decisions

### 1. 布局方案：CSS Grid 双栏

桌面端使用 `grid grid-cols-1 md:grid-cols-[2fr_3fr]`，移动端回退为单栏 + 底部抽屉。

```
桌面端 (≥768px):
┌─────────────────────────────────────────────┐
│  PageHeader + Stats                         │
├──────────────────┬──────────────────────────┤
│  表单区域 (2fr)   │  AI 助手面板 (3fr)       │
│  VideoForm /     │  - 模型选择              │
│  NoteForm        │  - 输入/生成             │
│                  │  - 结果展示              │
│                  │  - 预览 (折叠)           │
│                  │  - 模板/历史             │
└──────────────────┴──────────────────────────┘

移动端 (<768px):
┌──────────────────┐
│  PageHeader      │
│  Stats           │
│  表单区域        │
│  ─────────────── │
│  [AI 助手按钮]   │ → 点击后从下往上抽屉展开
└──────────────────┘
```

### 2. 组件拆分

- **新建 `PublishAiSidebar.tsx`**：右侧 AI 面板的容器组件，包含头部（模型信息 + 收起按钮）和内容区（AiSidebar 的内容）
- **改造 `PublishPage.tsx`**：移除 `AiPanel` 底部固定引用，改为 grid 双栏布局
- **保留 `AiSidebar.tsx`**：AI 功能组件不变，但被 `PublishAiSidebar` 包裹
- **整合 `PublishPreview`**：作为 AI 面板内的一个折叠区域（Tab 或 Collapsible）
- **废弃 `AiPanel.tsx` + `AiPanelToolbar.tsx`**：桌面端不再需要底部固定面板逻辑

### 3. 响应式策略

- `< 768px`（`md` 断点以下）：单栏布局，AI 助手通过底部按钮触发抽屉（复用现有 AiPanel 的移动端 modal 逻辑）
- `≥ 768px`：双栏 grid 布局
- AI 面板在桌面端始终可见，无需展开/收起切换

### 4. 状态管理

- AI 相关状态继续使用 `useAiStore`（Zustand）
- 面板展开/收起状态（仅移动端）使用组件本地 `useState`
- 表单 → AI 的数据流（`onPlatformChange`, `onFormChange`）保持不变

## Risks / Trade-offs

- **AiSidebar 内部依赖**：`AiSidebar` 当前可能有对 `AiPanel` 宽度/高度的隐式假设，迁移时需要验证
- **预览整合**：将预览从独立面板移入 AI 面板内可能降低可发现性，需要设计合适的入口（Tab 或默认展开）
- **移动端抽屉复用**：需要将 AiPanel 的移动端 modal 逻辑提取为独立 hook 或保留条件渲染
