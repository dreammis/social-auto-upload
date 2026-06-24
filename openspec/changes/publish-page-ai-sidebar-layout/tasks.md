## 1. 组件拆分与准备

- [ ] 1.1 新建 `src/components/AiRightPanel/PublishAiSidebar.tsx` — 右侧 AI 面板容器组件，包含头部（模型信息 + 关闭按钮，仅移动端）和内容区（渲染 `AiSidebar` 子组件）
- [ ] 1.2 将 `AiPanel.tsx` 中移动端全屏 modal 逻辑提取为 `useMobileDrawer` hook（`src/hooks/useMobileDrawer.ts`），供 PublishPage 复用
- [ ] 1.3 将 `PublishPreview` 组件改造为可嵌入 AI 面板内部的折叠区域版本（添加 `compact` prop 或新建 `PublishPreviewInline`）

## 2. PublishPage 布局重构

- [ ] 2.1 移除 PublishPage 中对 `AiPanel` 底部固定面板的引用，改为 import `PublishAiSidebar`
- [ ] 2.2 将主内容区改为 `grid grid-cols-1 md:grid-cols-[2fr_3fr] gap-6` 双栏布局
- [ ] 2.3 左侧区域渲染现有表单（Tabs + GroupPublishSelector + VideoForm/NoteForm）
- [ ] 2.4 右侧区域渲染 `PublishAiSidebar`，内部包含 `AiSidebar` + 折叠式 `PublishPreview`
- [ ] 2.5 移动端（`<md`）：右侧 AI 面板隐藏，改为底部固定按钮触发抽屉展开（使用 1.2 提取的 hook）

## 3. 预览整合

- [ ] 3.1 在 `PublishAiSidebar` 内添加"内容预览"折叠区域（使用 Collapsible 组件），默认收起
- [ ] 3.2 将 `previewData` 和 `showPreview` 状态从 PublishPage 传递到 AI 面板内
- [ ] 3.3 移除 PublishPage 中独立的预览侧栏 `<aside>` 区块

## 4. 样式与响应式

- [ ] 4.1 桌面端：AI 面板内部设置 `overflow-y-auto` + `max-h-[calc(100vh-xxx)]` 确保内容可滚动
- [ ] 4.2 移动端抽屉：设置 `max-h-[85vh]` + `rounded-t-2xl` + backdrop overlay
- [ ] 4.3 验证表单区域在移除底部 AiPanel 后不再有 `pb-[48px]` 的底部预留空间
- [ ] 4.4 验证 AI 面板在窄宽度（3fr 容器）下的渲染效果，确保模型选择、输入框等组件不溢出

## 5. 清理废弃代码

- [ ] 5.1 确认 `AiPanel.tsx` 和 `AiPanelToolbar.tsx` 不再被 PublishPage 引用后，标记为废弃（添加 `@deprecated` 注释或删除）
- [ ] 5.2 清理 PublishPage 中不再需要的状态（`showPreview`、底部面板相关逻辑）
- [ ] 5.3 运行 TypeScript 编译检查（`tsc --noEmit`），确保无类型错误
