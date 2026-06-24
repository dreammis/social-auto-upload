## ADDED Requirements

### Requirement: Desktop layout SHALL use left-right two-column grid
发布页面在桌面端（视口 ≥ 768px） SHALL 使用 CSS Grid 双栏布局，左侧为表单区域（2fr），右侧为 AI 助手面板（3fr）。

#### Scenario: Desktop user sees form and AI side by side
- **WHEN** 用户在桌面端（≥768px）访问发布页面
- **THEN** 左侧显示表单（VideoForm 或 NoteForm），右侧常驻显示 AI 助手面板
- **THEN** 左右宽度比例约为 2:3（40%:60%）

### Requirement: Mobile layout SHALL use bottom drawer for AI assistant
发布页面在移动端（视口 < 768px） SHALL 使用单栏布局，AI 助手通过底部操作栏触发从下往上的抽屉式展开。

#### Scenario: Mobile user taps AI button to open drawer
- **WHEN** 用户在移动端（<768px）点击底部 AI 助手按钮
- **THEN** AI 助手面板从屏幕底部向上滑出，覆盖部分表单区域
- **THEN** 用户可通过下滑或点击关闭按钮收起抽屉

### Requirement: Preview panel SHALL be integrated into AI sidebar
预览功能 SHALL 从独立的右侧 sticky 面板移入 AI 助手面板内部，作为可折叠区域或 Tab 页。

#### Scenario: User expands preview within AI panel
- **WHEN** 用户在 AI 面板内点击"预览"标签或展开按钮
- **THEN** 在 AI 面板内展示发布内容预览（标题、描述、标签、媒体）
- **THEN** 预览数据与表单实时同步

### Requirement: Bottom AiPanel fixed bar SHALL be removed
桌面端 SHALL 移除底部固定的 AiPanel 工具栏（48px），回收该空间给表单区域。

#### Scenario: No bottom bar on desktop
- **WHEN** 用户在桌面端访问发布页面
- **THEN** 页面底部不显示 AI 助手固定工具栏
- **THEN** 表单区域可使用完整的垂直空间
