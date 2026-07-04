## Why

当前 `/app/publish` 页的 AI 助手只有「模型选择 + 聊天生成 + 一键全流程」能力。用户在写图文笔记 / 视频脚本时有两个真实的痛点:

1. **配套图文找不到** — note 模式需要 1-9 张配图,目前必须离开 publish 页去 `/app/inbox` 或用外部工具自己搜,导出的图片还得手动拖回到图文附件区。短视频封面同样如此。
2. **视频素材只能拷 ID 下载** — 用户看到抖音 / B站 / 小红书 / 快手的分享链接想"直接拿来用",目前要么粘贴到 `/app/inbox` 的 URL 输入框 (得切页面),要么用外部下载工具再上传。AI 助手侧栏没有 URL 拉取通道。

这两个动作的共同诉求是: **让 AI 助手侧栏原地发起素材搜索 / 拉取,直接喂给 publish 表单**,不切页、不下载到本地再上传。

## What Changes

新增两个折叠 panel 在 `PublishAiSidebar` 内部 (位于 ChatViewPort 与 Composer 之间):

- **`图片素材` 面板** — 关键词输入 → 后端并发聚合 Pexels + Pixabay → 3×3 缩略图网格 → 单击填入图文附件 / 视频封面 URL
- **`链接拉取` 面板** — 粘贴 URL → 复用 `/api/inbox/download` 全链路 (yt-dlp + patchright + cookie) → 文件自动落到 `VideoForm.file` 槽

AI 辅助能力:
- **基于标题自动推荐图**: 标题 1.5s 静默变更时 (debounce 后) 触发 `/api/ai/recommend-images`,结果作为"基于标题"标签的子集叠加在手动搜索结果之上;用户手动搜索会清掉自动推荐集。session 内最多自动触发 3 次。

后端新增 3 个端点 + 1 个客户端 fetch proxy。

## Capabilities

### New Capabilities

- `ai-images-search` — 关键词 → Pexels + Pixabay 并发聚合 → 去重 → `{thumb,preview,full,photographer,pageUrl}` 列表
- `ai-recommend-images` — 接受 `topic` (一般从 form title 来) → 直接复用 `ai-images-search` → 同源去重
- `ai-image-fetch-proxy` — SSRF 闸门 + 后端 `requests.get` → `image/binary` 二进制流,供前端 fetch 后转 `File`
- `ai-sidebar-material-section` — PublishAiSidebar 内两个折叠 panel 的 UI 容器与状态契约

### Modified Capabilities

- `ai-content-generation` — MaterialSection 插入 + 自动推荐 useEffect 挂接 (在 chat pipeline 外、form snapshot 快照判断)
- `publish-page-ai-sidebar-layout` — PublishAiSidebar 内部 flex 布局调整: 顶部 Chat (flex-1) / 中部 Material (flex-shrink-0,折叠时 0px 高度) / 底部 Composer (flex-shrink-0)
- `chat-form-handle-bridge` — FormHandle 接口增加 `applyMedia?: (m: {thumbnail?:string, images?:File[]}) => void`,VideoForm/NoteForm 在 useImperativeHandle 中实现

## Impact

- **Web API**:
  - `web_runner/routes/ai.py` 新增私有 `_search_pexels` / `_search_pixabay` / `_merge_image_results` / `_fetch_image_proxy` + 3 个 Blueprint 路由
  - 新增环境变量读取 `PEXELS_API_KEY` / `PIXABAY_API_KEY` (无 key → 503 不走兜底)
  - 复用 `web_runner/routes/inbox.py::_is_public_url` / `_resolve_is_public` 做 SSRF 闸门
- **Frontend**:
  - `src/lib/chat/chatFormBridge.ts` — `FormHandle` 接口扩展
  - `src/features/publish/VideoForm.tsx` — `useImperativeHandle` 加 `applyMedia(thumbnail: string)` 实现
  - `src/features/publish/NoteForm.tsx` — 同样加 `applyMedia(images: File[])`
  - `src/Components/AiRightPanel/PublishAiSidebar.tsx` — 内部 layout 重排,接入 MaterialSection
  - `src/Components/AiRightPanel/MaterialSection.tsx` (新文件) — 两个折叠 Accordion 宿主
  - `src/Components/AiRightPanel/MaterialImageGrid.tsx` (新文件) — 3×3 缩略图 + 单击 add
  - `src/stores/materialPanelStore.ts` (新文件) — Zustand store (imageQuery / imageResults / recommendResults / loading / error)
  - `src/hooks/useMaterialAutoRecommend.ts` (新文件) — 1.5s form snapshot 轮询 + 会话级最多 3 次触发
  - `src/api/ai.ts` — 增 `aiApi.searchImages` / `recommendImages` / `fetchImageAsFile`
- **CLI**: 无影响 (CLI 不参与素材搜索 / 自动推荐)
- **依赖**: 后端 `requests` 已存在;前端不引入新 npm 包 (Accordion 用现有 `@/Components/ui`,不需要 Radix)
- **配置**: `.env.example` 新增 `PEXELS_API_KEY` / `PIXABAY_API_KEY` 注释行
- **Breaking change**: 无 (FormHandle 加可选方法,旧 client 不传 applyMedia 时维持现状)
- **测试**: 后端 `tests/test_ai_image_search.py` (mock Pexels/Pixabay HTTP,验证归一化 / 合并 / 去重 / 503);前端 `src/stores/materialPanelStore.test.ts` + `MaterialSection.test.tsx`
