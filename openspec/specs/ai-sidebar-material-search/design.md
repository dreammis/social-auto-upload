## Context

`PublishAiSidebar` 当前的 `flex-1 min-h-0` 容器只装了一个 chat 面板。新增两个折叠 panel 必须不改写 chat viewport 的 overflow 边界,否则 composer 会被推到屏幕外。

`FormHandle` (chatFormBridge.ts) 当前只暴露 `applyAiResult({title,desc,tags})` 和 `getFormSnapshot`。VideoForm 用 `useState` 持有本地 title/desc/tags 和 `fileRef.current` (File 对象)。要写入图片到 NoteForm.images[] 或 URL 到 VideoForm.thumbnail,必须新增一个 imperative method,不能用 store 替代 (publishWizardStore 没有 images[] 字段)。

Pexels / Pixabay 是两个完全独立的 CDN (`images.pexels.com` vs `cdn.pixabay.com`),跨平台重复概率近乎 0。同源多次查询间才需要去重。后端用 `f"{source}:{id}"` 做去重 key。

## Goals / Non-Goals

**Goals**:

- 在 AI 助手侧栏内原地完成"搜图 → 一键填表单"和"贴 URL → 一键下载"
- Pexels + Pixabay 双源聚合,tier-1 用户 (个人开发者) 免费配额 (Pexels 200/h + Pixabay 5000/h) 够用
- 无 key 时直接 503 + 友好提示,不静默走 DuckDuckGo 图 (DuckDuckGo 图质量参差,反向伤害发布效果)
- CORS 安全: 客户端永远 fetch 自己的后端,二进制图走 `/api/ai/images/fetch?url=...` 代理
- 后端 search 端点并发聚合,前端无 loading flicker
- 自动推荐每次 session 最多 3 次,debounce 1.5s,避免 LLM/搜索调用被频繁触发

**Non-Goals**:

- 不做 OCR / 图内容理解 (LLM 视觉分析留给后续 P1)
- 不做视频封面合成 (P2 议程)
- 不做 RAG-style 长期记忆推荐 (超出本次 scope)
- 不接 Flickr / Unsplash / Bing Image Search (双源已足够,用户决策)
- 不改 inbox.py 视频下载路径 (已是生产级,直接复用)
- 不引入新 npm 包 (Accordion / Button 等已有 ui 组件)

## Decisions

### 1. PublishAiSidebar layout: 三段式弹性盒

```
┌─────────────────────────────────┐  ← PublishAiSidebar root
│ 头部 (header, 41px high)         │  flex-shrink-0
├─────────────────────────────────┤
│ Chat viewport (flex-1, min-h-0)  │  overflow-y-auto
│                                   │
│                                   │
├─────────────────────────────────┤
│ Material sections                │  flex-shrink-0
│  ▸ 图片素材 (collapsed → 0px)     │  Accordion Item, defaultValue="" 
│  ▸ 链接拉取 (collapsed → 0px)     │
├─────────────────────────────────┤
│ AI Composer (flex-shrink-0)      │  border-t
└─────────────────────────────────┘
```

要点:
- Material section 用 **Radix Accordion** `type="multiple"` 两个 Item,各 Item `collapsible`,默认关闭 (避免遮挡 chat)
- 展开时 Material section 占固定高度 (图片网格 360px / 链接拉取 200px)
- Chat viewport 拿到剩余高度,继续 `flex-1 min-h-0 overflow-y-auto`,Composer 永远锚底

### 2. 后端并发聚合: ThreadPoolExecutor(max_workers=2)

Pexels + Pixabay 各起一个线程,合计 timeout 8s (低于单源 10s 默认),任一超时不影响另一源返回。归一化过程只做 shape 转换 + 同源 dedup。

```python
def _search_images(query: str, count: int = 9) -> tuple[list[dict], dict]:
    """Returns (merged_results, debug). debug = {pexels_count, pixabay_count, merged_count, errors:[...]}"""
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_pexels = ex.submit(_search_pexels, query, count)
        f_pixabay = ex.submit(_search_pixabay, query, count)
        pexels = f_pexels.result(timeout=8) or []
        pixabay = f_pixabay.result(timeout=8) or []
    merged = _merge_image_results(pexels, pixabay, count)
    return merged, {...}
```

### 3. 归一化 schema

```ts
interface NormalizedImage {
  id: string              // f"{source}:{source_id}"
  source: 'pexels' | 'pixabay'
  thumb: string           // 200x200 缩略图
  preview: string         // 640px 中尺寸
  full: string            // 原始尺寸
  photographer: string
  photographerUrl: string|null
  pageUrl: string         // Pexels photo page / Pixabay page,可点开查看
  alt: string             // 描述/标题
}
```

归一化函数: `_normalize_pexels_photo(p) -> NormalizedImage` / `_normalize_pixabay_hit(h) -> NormalizedImage`,纯函数,pytest 覆盖。

### 4. 无 key 行为: 503 + 友好提示,不兜底

```python
if not _has_image_source():
    return jsonify({
        "success": False,
        "message": "未配置图片搜索 API key。请在 .env 设置 PEXELS_API_KEY 或 PIXABAY_API_KEY 后重启 run.py。",
        "code": "IMAGE_SOURCE_NOT_CONFIGURED",
    }), 503
```

`AI_MODELS` 类似,但 actions 不一样: 配置 image source 是 build-time / .env 控制,不是 user-managed。所以放在 operator-side 文档里。

### 5. SSRF 闸门: 复用 inbox 同款

`/api/ai/images/fetch?url=...` 严格走 `_is_public_url` (句面 IP 拒绝) + `_resolve_is_public` (DNS 解析后拒绝私有 IP),与 `/api/inbox/download` 同款防御。限制单图 ≤ 10MB (图文场景合理上限)。

### 6. 自动推荐触发机制: form snapshot 轮询

`publishWizardStore` 没有实时 title (本地 useState)。两种方案:

| 方案 | 优点 | 缺点 |
|---|---|---|
| A. onFormChange 回调链 | React 自带 | 必须从 VideoForm 引出 callback 到 PublishPage 再传到 sidebar,耦合 reach 太长 |
| B. 1.5s 轮询 `formRef.getFormSnapshot()` | 完全解耦,polling cost 低 (字符串比较,毫秒级) | 有 1.5s 延迟 |

选 B。理由:

- 新增 1 个 hook,不动 VideoForm.tsx 任何代码 (避免污染 chatFormBridge 一致性)
- 1.5s 延迟对"AI 推荐配图"是可接受的 (用户写一句话的时间远高于 1.5s)
- polling cost: 一次 `formRef.current?.getFormSnapshot()` 返回 `{title,desc,tags}`,字符串比较。`setInterval` 1.5s 在 publish 页挂载期间持续 — 估算每分钟 40 次调用,纯内存操作。

防爆规则:
- title 空 → 不触发
- title 与上次相同 → 不触发
- 已触发次数 ≥ 3 (session 内累计) → 不触发
- 用户此期间手动搜过图 → 不再叠加自动推荐 (避免重复)

### 7. FormHandle.applyMedia 写入语义

VideoForm: `applyMedia({thumbnail})` → `setThumbnail(url)`。不接受 images (视频模式没有图文附件槽)。
NoteForm: `applyMedia({images})` → `images.forEach(f => pushImageIntoFilesArray(f))`。不接管 thumbnail (图文模式自定义头图不通过此通道)。

写入逻辑要在 `useImperativeHandle` 内,使用 ref-functional setter 避免触发全表单 re-render。但因为 thumbnail / images 都是状态,这是必然的 – Plan 后跟一轮 manual smoke test 确认 note 附图追加 + video 封面更新无副作用。

### 8. CORS: 后端代理而不是客户端 fetch

客户端 fetch Pexels / Pixabay 图再转 File 看似简单,但有 3 个雷:
- 部分 Pexels 图片服务器在某些地区 CORS headers 缺失
- Pixabay 偶发 origin 限制
- Add-to-form 流程中如果用户网络不稳 fetch 失败,UI 需补 loading 状态

故新增 `/api/ai/images/fetch?url=...` 服务器代理,客户端 fetch 自己后端,拿到 blob → `new File([blob], filename, {type: mime})`。代理只负责 fetch + 流式返回,不做任何 cropping/resize。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| Pexels/Pixabay 跨域图直连失败,影响"加分页 URL"数据 | 只在 `_normalize_*` 阶段记 source URL;fetch 失败时 UI 显示 placeholder + retry |
| `useImperativeHandle.applyMedia` 触发 VideoForm 全表 re-render | 只有 thumbnail 变了,合理范围;用 functional setter 不多余渲染 |
| `publishWizardStore` 没有 images 字段,刷新丢临时状态 | NoteForm 接 applyMedia 后立刻被 useImperativeHandle 同步到本地 state,refresh 行为由 usePublishDraft 现在的快照机制覆盖 |
| 1.5s 轮询在 tab 切到后台还在跑 | hook cleanup 用 `clearInterval`;visibilitychange 时 reset interval (离开 30s 后停轮询)|
| 双源 API key 滥用 (用户不小心调 5000 次) | 后端按 IP + token 做软限流 (≥30/min 返回 429);记 .sau-logs |
| Material section 展开遮住 chat viewport | 限定每个 panel max height,展开时 chat viewport 收到 `min-h-[240px]` 保护,不展开到屏幕全高 |
| LLM 在 P1 时可能被调用拆解关键词 | 当前不做,P1 阶段再做;heuristic (split-by-bigram) 已经覆盖 80% 关键词 |
| `_is_public_url` 误杀 IPv6 公网地址 | inbox 同款 v0.1 已经处理 (mapped IPv4 fallback + 2544/15 特例);直接复用即可 |

## 验收标准

- [ ] P0 全量: Pexels + Pixabay 双源聚合 + URL 一键下载
- [ ] PublishAiSidebar layout 不破坏 chat viewport 的 overflow 边界
- [ ] 无 PEXELS_API_KEY / PIXABAY_API_KEY 时返回 503 + 单句中文提示
- [ ] SSRF: 私有 IP / loopback 经 `/api/ai/images/fetch` 必须返回 400
- [ ] 图 add-to-form: VideoForm.thumbnail 字段正确更新;NoteForm.images 增加新 File (不替换旧的)
- [ ] URL add-to-form: VideoForm.file 槽被 inboxDownload 的 binary file 替换,preview 自动刷新
- [ ] 自动推荐: 1.5s debounce, session 内 ≤ 3 次, 标题变空/不变不再触发
- [ ] 测试覆盖: backend pytest merge/dedup/ssrf/no-key;vitest covers materialPanelStore + MaterialSection
- [ ] 用户已经有的所有 `/variants` / `/fullflow` / `/enhance` 魔法命令语义不变 (兼容变更)
