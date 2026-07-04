# ai-sidebar-material-search — Delivery Changelog

**Delivered**: 2026-07-04 · **Scope**: §1‒9 (code) + §13 (docs) one-shot · **Change-id**: `ai-sidebar-material-search`

---

## §1 — Backend image search routes (`web_runner/routes/ai.py`)

Closed loop: `_has_image_source()` env gate, `_search_pexels()` / `_search_pixabay()` with `ThreadPoolExecutor(max_workers=2)` and 8 s per-source timeouts, `_normalize_*()` pure-function schema mappers, `_merge_image_results()` dedup-by-`f"{source}:{id}"` + count cap. Three Blueprint endpoints: `POST /api/ai/images/search` (auth + 503-on-no-key + 30/min soft throttle returning 429), `POST /api/ai/recommend-images` (topic-only, no LLM key required thanks to the no-source 503 fallback), `GET /api/ai/images/fetch?url=...` reusing inbox's `_is_public_url` + `_resolve_is_public` SSRF gates plus a 10 MB byte cap.

## §2 — Backend env wiring

`.env.example` annotated `PEXELS_API_KEY=` + `PIXABAY_API_KEY=` placeholder block under a new 「图片搜索 (Pexels + Pixabay)」section; `conf.example.py` mirrors the same explainer pointing operators at `.env` (single source of truth for credentials).

## §3 — `FormHandle.applyMedia` interface extension (`src/lib/chat/chatFormBridge.ts`)

`FormHandle` gained the optional `applyMedia?: (m: {file?, thumbnail?, images?}) => ApplyAttempt`. `safeApplyMedia(ref, m)` helper mirrors `safeApplyAiResult`'s ref-presence + try/catch closure, with a `'no-media-slot'` reason so callers can branch uniformly. The `{file?}` key was a spec.md-required fix layered in during implementation (spec gap: tasks.md §3+§4 omitted it, but spec.md §"URL one-click fetch" requires `safeApplyMedia(formRef, {file})`).

## §4 — Per-form `applyMedia` implementation

`VideoForm` accepts `{file, thumbnail}`, rejects `{images}` → `{applied: false, reason: 'no-media-slot'}`. `NoteForm` accepts `{images}` through the existing `addImagesWithinLimit` (so future platform image-MAX changes are a single-file fix), rejects `{file, thumbnail}`. Both surfaces in-store + toast on rejection.

## §5 — Frontend API client

`src/api/ai.ts` added `searchImages({query, count})` → `POST /api/ai/images/search`, `recommendImages({topic, count})` → `POST /api/ai/recommend-images`, `fetchImageAsFile(url, filename, mime)` → `GET /api/ai/images/fetch` (Blob → `File`). `src/api/inbox.ts` plus `src/api/client.ts` barrel re-export the `inboxFetchFile()` helper that streams bytes from `/api/inbox/file/<name>` for the URL one-click path.

## §6 — State layer (`src/stores/materialPanelStore.ts`, new)

Zustand store split into two non-clobbering slots per spec §"Auto-recommend ... SHALL remain visible": `imageResults[]` (manual) and `recommendResults[]` (auto). Session-level cap `recommendCount ≤ 3` is in-memory only (resets on remount); `recentQueries[]` is LS-persisted (key `sau-material-panel-recent-queries`, LRU max 3, case-insensitive dedup). `reset()` clears the in-memory slots but preserves LS-backed `recentQueries` so the visibilitychange hidden-30s "fresh slate" path doesn't drop the user's chip history.

## §7 — UI components (`src/Components/AiRightPanel/`)

Three new components + one orchestrator: `MaterialImageGrid` is a 3×3 click-to-add grid with per-tile `addingImageIds` debounce (anti-spam on slow networks) and a hover badge `来源 · 摄影师`. `AddUrlForm` is a URL paste + 「拉取」button that orchestrates `/api/inbox/download` → `inboxFetchFile` → `safeApplyMedia({file})`. `MaterialSection` is the Radix-Accordion `type="multiple"` orchestrator (image panel ≤380 px, link panel ≤240 px, both items default-collapsed so chat viewport gets full height at panel mount). Spec invariant kept: image panel + link panel use `border-t` to keep the manual + recommend areas visually separated.

## §8 — Auto-recommend hook (`src/hooks/useMaterialAutoRecommend.ts`, new)

`setInterval(1500 ms)` polls `formRef.getFormSnapshot().title`; skips on empty / unchanged / `recommendCount ≥ 3` (per spec §"Session recommendation cap"). `visibilitychange` to hidden ≥ 30 s calls `store.reset()` (in-memory wipe) — the chip history stays because the hook reads store via a ref and the LS-backed `recentQueries` is preserved by `reset()`.

## §9 — `PublishAiSidebar` layout re-arrangement

Three-band flex column: header (flex-shrink-0, 41 px) → chat viewport (flex-1 min-h-0) → `<MaterialSection />` (flex-shrink-0, both items collapsed=0 px so chat fills) → composer (flex-shrink-0 border-t). The MaterialSection is injected into `<AiAssistantPanel>` via a new `betweenViewportAndFooter?: ReactNode` slot prop, so the consumer wiring stays decoupled from the orchestrator (spec ordering: viewport → Material → composer).

## §13 — Operation / docs

`docs/ai-material-search.md` is the operator runbook: Pexels + Pixabay signup walkthroughs (URLs + cookie banner alert), 5-minute onboarding checklist, current free-tier numbers (Pexels 200 req/hour + 20 000 req/month; Pixabay 100 req / 60 s — corrected against the live docs), backend interaction rules (always go through the in-app proxy), and a 30-second e2e verify script. `docs/dev/INDEX.md` Operators table registers this runbook; Quick-reference matrix gains a `✅` glyph in the Operators column. `CLAUDE.md` Operations / on-call list gains a fourth pointer (above the cron runbooks) so operators landing at the repo root reach the onboarding doc in 1 click.

---

## What's in the archive dir (next-round hand-off)

- `openspec/specs/ai-sidebar-material-search/spec.md` — canonical requirement contract (Requirements + Scenarios).
- `openspec/specs/ai-sidebar-material-search/design.md` — rationale, risks, design alternatives rejected.
- `openspec/specs/ai-sidebar-material-search/CHANGELOG.md` — this file.

## What landed alongside §1‒9 + §13 (follow-up scope, also delivered)

- **§10** `tests/test_ai_image_search.py` + `tests/test_ai_image_fetch_proxy.py` — 14 backend pytest covering dedup, no-key 503 envelope, partial-degradation through Pixabay when Pexels 5xx's, both-5xx-empty, count-cap, SSRF private/loopback/DNS-rebinding gates, 10 MB byte cap, `Content-Type` upstream passthrough.
- **§11** `src/stores/materialPanelStore.test.tsx` (renamed from `.ts` to match vitest config include) + `src/Components/AiRightPanel/MaterialSection.test.tsx` — 29 vitest specs covering the four §11.1 store scenarios (success / envelope-failure / search-vs-recommend coexistence / `recentQueries` LRU) and the four §11.2 MaterialSection scenarios (Accordion close, image-link max-h caps at 380 / 240 px, manual + recommend coexist, click-tile → `applyMedia` + success toast).
- **§12** `.github/workflows/ci.yml` — `frontend-vitest` job's `npx vitest run` command now picks up the 2 new specs (~3 s added runtime reported in the CI comment).

## Reference contract for next round of features

- **New endpoints**: `POST /api/ai/images/search`, `POST /api/ai/recommend-images`, `GET /api/ai/images/fetch`.
- **New env vars**: `PEXELS_API_KEY`, `PIXABAY_API_KEY` (both optional; absence → 503 with `IMAGE_SOURCE_NOT_CONFIGURED` code + Chinese friendly message).
- **Interface contract**: `FormHandle.applyMedia` widened to `{file?: File, thumbnail?: string, images?: File[]}`; the `{file}` key was added during implementation per spec.md.
- **Stable offsets**: `recommendResults` is a separate slot from `imageResults` (manual search MUST NOT clobber auto-recommend). `recentQueries` caps at 3 in LS; reset preserves it.
