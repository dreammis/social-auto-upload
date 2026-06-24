## MODIFIED Requirements

### Requirement: PublishPage layout structure
PublishPage 的布局 SHALL 从"全宽表单 + 底部 AI 抽屉"变为"左窄表单 + 右宽 AI 面板"双栏结构。

#### Scenario: Desktop two-column layout
- **WHEN** 视口宽度 ≥ 768px
- **THEN** 页面使用 `grid-cols-[2fr_3fr]` 双栏布局
- **THEN** 左侧渲染表单，右侧渲染 AI 助手面板

#### Scenario: Mobile single-column with drawer
- **WHEN** 视口宽度 < 768px
- **THEN** 页面使用单栏布局，AI 助手通过底部抽屉访问
