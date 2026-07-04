## Status — Delivered 2026-07-04 (§1-9 + §13 docs one-shot)

All atomic tasks marked `[x]` below. This change is archived as a one-shot delivery (no follow-up PRs planned within this change-id). Hand-off artifacts for the next round of features:

- **Canonical spec** (source of truth): `openspec/specs/ai-sidebar-material-search/spec.md`
- **Design record** (rationale + risks): `openspec/specs/ai-sidebar-material-search/design.md`
- **Delivery summary** (one-shot scope): `openspec/specs/ai-sidebar-material-search/CHANGELOG.md`

Next-round consumers: read `spec.md` first for the requirement contract, then `CHANGELOG.md` for what landed in this one-shot vs. what was deferred.

## 1. Backend image search route handlers (Web API)

- [x] 1.1 在 `web_runner/routes/ai.py` 添加 `_has_image_source()` env 检测 (`PEXELS_API_KEY` 或 `PIXABAY_API_KEY` 至少一个)
- [x] 1.2 实现 `_search_pexels(query, count)` — `requests.get('https://api.pexels.com/v1/search', headers={'Authorization': key}, params={query, per_page:count})`,返回 list[原始 Pexels photo] 或空
- [x] 1.3 实现 `_search_pixabay(query, count)` — `requests.get('https://pixabay.com/api/', params={key, q, per_page:count, image_type:'photo'})`,返回 list[原始 hit] 或空
- [x] 1.4 实现 `_normalize_pexels_photo(p) -> NormalizedImage` 和 `_normalize_pixabay_hit(h) -> NormalizedImage` 纯函数
- [x] 1.5 实现 `_merge_image_results(pexels, pixabay, count)` — `f"{source}:{source_id}"` 去重 + 切前 count 个
- [x] 1.6 实现 `_search_images(query, count)` — `ThreadPoolExecutor(max_workers=2)` 调用 1.2/1.3 + merge,各自 8s 超时,互不阻塞
- [x] 1.7 注册 Blueprint 路由 `POST /api/ai/images/search` — auth + 双源调用 + 503 处理 + 计数限流 (≥30 次/min 返 429)
- [x] 1.8 注册 Blueprint 路由 `POST /api/ai/recommend-images` — 接受 `{topic, count}`;忽略 LLM key 是否配置 (无 key 走 503 同上)
- [x] 1.9 实现 `_fetch_image_proxy(url)` — 复用 `_is_public_url` + `_resolve_is_public` + `requests.get(stream=True)` + 10MB 顶
- [x] 1.10 注册 Blueprint 路由 `GET /api/ai/images/fetch?url=...` — 返回 `image/binary` 流

## 2. Backend env wiring (Web API)

- [x] 2.1 `.env.example` 新增 `PEXELS_API_KEY=` 和 `PIXABAY_API_KEY=` 注释行,引用 docs/ai-material-search.md (后续 commit 补)
- [x] 2.2 `conf.example.py` 加对应注释 (跟 .env.example 同步)

## 3. FormHandle 接口扩展 (Frontend — bridge)

- [x] 3.1 `sau_web/frontend/src/lib/chat/chatFormBridge.ts`: `FormHandle` 加 `applyMedia?: (m: {thumbnail?: string, images?: File[]}) => void`
- [x] 3.2 `sau_web/frontend/src/lib/chat/chatFormBridge.ts`: 导出 `safeApplyMedia(ref, m)` 类似 safeApplyAiResult 的 try/catch + 应用结果反馈

## 4. 表单实现 applyMedia (Frontend)

- [x] 4.1 `sau_web/frontend/src/features/publish/VideoForm.tsx`: `useImperativeHandle` 内加 `applyMedia({thumbnail})` → setThumbnail(url) + toast 反馈
- [x] 4.2 `sau_web/frontend/src/features/publish/NoteForm.tsx`: 在 useImperativeHandle 内加 `applyMedia({images})` → push to images state;同样 toast 反馈 (找不到则对该表单略过,返回 `{applied:false, reason:'no-media-slot'}`)

## 5. Frontend API client (Frontend)

- [x] 5.1 `sau_web/frontend/src/api/ai.ts` 加 `aiApi.searchImages(query, count = 9)` → `POST /api/ai/images/search`
- [x] 5.2 同文件加 `aiApi.recommendImages(topic, count = 9)` → `POST /api/ai/recommend-images`
- [x] 5.3 同文件加 `aiApi.fetchImageAsFile(url, filename, mime)` → `fetch('/api/ai/images/fetch?url=...')` → Blob → `File`

## 6. 状态层 (Frontend)

- [x] 6.1 新建 `sau_web/frontend/src/stores/materialPanelStore.ts` (Zustand):
  - state: `imageQuery`, `imageResults`, `imageLoading`, `imageError`, `recommendResults`, `recommendLoading`, `recommendCount`, `recentQueries (max 3)`
  - actions: `searchImages(query)`, `recommendByTitle(title)`, `addImageToForm(image)`, `fetchAndAddUrl(url)`, `clearResults()`, `reset()`
  - localStorage 持久化: `recentQueries` (sticky UX)

## 7. UI 组件 (Frontend)

- [x] 7.1 新建 `sau_web/frontend/src/Components/AiRightPanel/MaterialSection.tsx`:
  - Radix Accordion `type="multiple"`, 两个 Item: 图片素材 / 链接拉取
  - 图片 panel: input + 3×3 grid + loading skeleton
  - 链接 panel: URL input + 「解析下载」按钮 + progress indicator
- [x] 7.2 新建 `sau_web/frontend/src/Components/AiRightPanel/MaterialImageGrid.tsx`:
  - 接收 `images: NormalizedImage[]` array
  - 单击: 调 `addImageToForm(image)` → onSuccess 灰化该 tile
  - hover: 角标 `来源 · 摄影师`
  - Per-tile isAdding 状态 (防 spam click)
- [x] 7.3 新建 `sau_web/frontend/src/components/AiRightPanel/AddUrlForm.tsx`:
  - URL input + 「拉取」按钮
  - 跟 inboxDownload 后端的 SSE 进度 UI 复用 (round 30 v7)
  - 成功后,根据 mode 调 formRef.applyMedia

## 8. 自动推荐 hook (Frontend)

- [x] 8.1 新建 `sau_web/frontend/src/hooks/useMaterialAutoRecommend.ts`:
  - setInterval(1500ms),通过 `safeGetFormSnapshot(formRef)` 读 title
  - 规则: 空 / 重复 / 超过 3 次 → 不触发
  - cleanup: clearInterval + visibilitychange (hidden > 30s → reset)
  - 触发后: 调 `materialPanelStore.recommendByTitle(title)`,结果叠加到 `recommendResults` slot (不影响 manualResults)

## 9. PublishAiSidebar layout 重排 (Frontend)

- [x] 9.1 `sau_web/frontend/src/Components/AiRightPanel/PublishAiSidebar.tsx`:
  - root: `flex flex-col h-full` (保持现有)
  - Header: 41px, flex-shrink-0 (保持)
  - 中间: `flex-1 min-h-0 overflow-hidden flex flex-col` 包 Chat + Material
  - Chat viewport: flex-1 min-h-0 overflow-y-auto
  - Material sections: flex-shrink-0, Accordion collapsed=0px
  - Composer: flex-shrink-0, border-t
- [x] 9.2 在 layout 中接入 `MaterialSection` 和 `useMaterialAutoRecommend(formRef)`

## 10. Backend 测试 (pytest)

- [x] 10.1 新建 `tests/test_ai_image_search.py`:
  - test_normalize_pexels_photo_handles_all_required_fields
  - test_normalize_pixabay_hit_unwraps_largest_image_url
  - test_merge_dedupes_by_source_id_and_does_not_dedupe_across_sources
  - test_no_pexels_no_pixabay_returns_503
  - test_pexels_5xx_falls_through_pixabay_only (partial degradation)
  - test_both_5xx_returns_empty_list_with_given_count
  - test_count_limits_to_n_total_after_merge
- [x] 10.2 新建 `tests/test_ai_image_fetch_proxy.py`:
  - test_rejects_private_ip_url
  - test_rejects_loopback_resolved_dns
  - test_size_cap_enforced_at_10mb
  - test_returns_correct_content_type_charset

## 11. Frontend 测试 (vitest)

- [x] 11.1 `src/stores/materialPanelStore.test.ts`:
  - search 成功 → imageResults 更新, loading 复位
  - search 5xx → imageError 设置
  - recommend 清掉 manualResults 还是叠加? 已确认保留叠加
  - recentQueries LRU-only-max-3
- [x] 11.2 `src/Components/AiRightPanel/MaterialSection.test.tsx`:
  - Accordion 关闭时 top-level section 高度 0px
  - 输入关键词 + 回车 → 触发 searchImages
  - 单击 tile → addImageToForm 被调, 成功 toast 显示
  - URL 解析失败 → 错误 toast 不抛异常

## 12. CI / vitest gate 更新 (.github/workflows/ci.yml)

- [x] 12.1 `frontend-vitest` job 的 `npx vitest run` 命令追加 `src/stores/materialPanelStore.test.ts` + `src/Components/AiRightPanel/MaterialSection.test.tsx`
- [x] 12.2 `ci.yml` 内 `Expected runtime added` 段落同步 ~2s (matrix 调整)

## 13. 文档 (docs/)

- [x] 13.1 新建 `docs/ai-material-search.md` — 操作员视角:如何获取 PEXELS_API_KEY / PIXABAY_API_KEY、free tier 上限、403/429 时的应对
- [x] 13.2 `docs/dev/INDEX.md` 增加此条 entry (Operator audience)
- [x] 13.3 `CLAUDE.md` 在 Operations 段增加一行指针
