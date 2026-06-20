# 性能优化清单

> 最后更新：2026-06-19

---

## 📊 当前性能基线

数据采集于 `npm run build` 生产构建 + Playwright / Chrome Canary 测试。

### 构建产物体积

| 文件 | 大小 | 说明 |
|------|------|------|
| `dist/assets/` (总计) | **1.4 MB** | |
| `index-xxx.js` (主入口) | **768 KB** | 包含 React、antd、路由等核心库 |
| `PublishPage-xxx.js` | **88 KB** | 发布页面 |
| `AccountsPage-xxx.js` | 代码分割后独立 chunk | |
| `TasksPage-xxx.js` | 代码分割后独立 chunk | |
| `LogsPage-xxx.js` | 代码分割后独立 chunk | |
| `index-xxx.css` | **14 KB** | 全局样式 |

### 首屏加载性能

| 指标 | 耗时 |
|------|------|
| DOM Interactive | **12ms** |
| DOM Content Loaded | **316ms** |
| Load Complete | **317ms** |
| First Contentful Paint | **832ms** |
| 首屏 JS 传输量 | ~6 KB (后续增量加载) |

### 路由切换性能

| 路由 | 耗时 |
|------|------|
| `/publish` (首次) | **611ms** (含 antd 组件加载) |
| `/publish` (后续) | ~440ms |
| `/logs` | **439ms** |
| `/tasks` | **443ms** |
| `/` (账号管理) | **444ms** |

### 内存使用

| 指标 | 值 |
|------|-----|
| JS Heap (used) | **~102 MB** |
| JS Heap (total) | **~154 MB** |
| 请求资源数 | **39 个** |

---

## ✅ 已完成优化

- [x] **代码分割** — 4 个页面组件使用 `React.lazy()` + Suspense，每个页面生成独立 JS chunk
- [x] **页面过渡动画** — 轻量 `motion` 动画（120ms tween），替代了原始 spring 动画
- [x] **响应式布局** — 桌面/平板/手机三套布局，侧边栏自动折叠
- [x] **暗色模式** — 所有新 UI 元素均有 dark mode CSS 覆盖
- [x] **Layout transitions** — CSS transition 用于侧边栏折叠、暗色模式切换等

---

## 🔜 待优化项目

### 1. 生产构建体积优化

**目标：** 将主 JS bundle 从 768 KB 降到 500 KB 以下。

- [ ] **Tree Shaking** — 确保 `package.json` 中设置 `"sideEffects": false`（如果适用）
- [ ] **Ant Design 按需引入** — 目前每个页面 import 了整棵 antd 组件树。验证构建工具是否已自动 tree-shake。Webpack 时代需要 `babel-plugin-import`，Vite 基于 ESM 通常自动处理，但可检查 `vite.config.ts` 是否有优化配置。
- [ ] **@ant-design/icons 分包** — 图标库体积较大。考虑使用 `IconProvider` + 按需 icon 组件，或分析哪些 icon 实际被使用。
- [ ] **moment.js 替换** — antd v5+ 已移除 moment 依赖，但需确认项目中无直接 moment 引用。
- [ ] **dayjs 替代** — 若需日期处理，使用 dayjs（~6KB）替代 moment.js（~230KB）。

### 2. 代码分割深化

- [ ] **FloatingLogs 懒加载** — 该组件仅在用户点击浮动按钮时显示，可改为 `React.lazy()`，减少首屏 30+ KB
- [ ] **路由级 chunk 命名** — 在 `vite.config.ts` 中配置 `rollupOptions.output.chunkFileNames` 使 chunk 名称更可读
- [ ] **Ant Design 组件级懒加载** — 大体积组件如 `Table`、`Upload.Dragger` 可进一步拆分为异步 chunk

### 3. 运行时性能

- [ ] **组件重渲染优化** — 检查 `useTasks` hook 中的轮询（每 3 秒），确认不会导致不必要的大范围重渲染
- [ ] **FloatingLogs 虚拟列表** — 当日志条目超过 500+ 时，考虑使用虚拟滚动
- [ ] **debounce 搜索输入** — 日志页和任务页的搜索输入框可添加 debounce（当前每次输入立即触发过滤）
- [ ] **图片懒加载** — 发布页面的图片预览网格可添加 `loading="lazy"` 属性

### 4. 网络优化

- [ ] **字体预加载** — 添加 `<link rel="preload">` 加载关键字体
- [ ] **关键 CSS 内联** — 将首屏关键 CSS 内联到 `index.html` 头部
- [ ] **Service Worker** — 为静态资源添加缓存策略

### 5. 构建配置

- [ ] **手动 chunk 拆分** — 在 `vite.config.ts` 中配置 `manualChunks`:
  ```ts
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          antd: ['antd', '@ant-design/icons'],
          motion: ['motion'],
        },
      },
    },
  }
  ```
- [ ] **Gzip / Brotli 压缩** — 配置 nginx 或 CDN 层开启 Brotli 压缩
- [x] **代码分割** — 已完成 `React.lazy()` 基本分割

### 6. 监控与持续优化

- [ ] **添加性能 CI 检查** — 在 CI 中运行 Lighthouse CI，设置体积阈值
- [ ] **定期重新测量基线** — 每次大版本更新后更新本文件的性能数据
- [ ] **Lighthouse 预算** — 在 `package.json` 或 CI 配置中设置 `"performance-budget"` 约束

---

## 🔧 快速参考命令

```bash
# 生产构建
npm run build

# 查看构建产物
ls -lh dist/assets/

# 统计各 chunk 大小
du -sh dist/assets/

# 分析 bundle 构成（安装 visualizer）
npx vite-bundle-analyzer  # 或使用 rollup-plugin-visualizer
```

---

> 📝 **说明：** 本文件记录了 `sau_web/frontend` 前端的性能优化状态。优化项目按优先级从高到低排列，✅ 为已完成，[ ] 为待做。
