# AI Sidebar Multi-Turn Chat

## Why

The current AI sidebar in `PublishPage` is a single-shot generator: input → enhance → generate → fill. Users who need iteration (regenerate title, tweak tone, translate) must re-enter the whole prompt and re-trigger. This makes the AI feel like a vending machine rather than a co-pilot.

We add multi-turn chat so users can:
- Refine an output across multiple turns (rewrite, shorten, expand, translate).
- Persist the conversation across page navigation and reloads.
- Continuously ground the AI in the publish form's current state without explicit re-paste.

This is the foundation of the broader AI-assistant improvements in `.kilo/plans/improve-ai-assistant.md` (P0 多轮对话 + P3 代码拆分). Skill expansion, marketplace, and quality scoring are explicitly listed in the original plan as **deferred** to follow-up changes.

## What Changes

- **New: `useChatStore`** — Zustand state machine for multi-turn sessions, streamed drafts, commit/cancel lifecycle, applied-field audit, hydrate/reset. Independent of any persistence adapter.
- **New: chat form bridge** — Three pure helpers (`safeGetFormSnapshot`, `safeApplyAiResult`, `buildChatPayload`) that read/write the publish form via its imperative ref. Every cross-domain interaction degrades gracefully: a `null` ref (form unmounted) returns structured outcomes instead of throwing.
- **New: chat persistence layer** — A `ChatStorage` interface + `InMemoryChatStorage` adapter. `pruneChatStorage(storage, policy)` enforces a 7-day TTL followed by a 50MB quota, run oldest-first. Persistence is swappable; a Dexie/IndexedDB adapter ships later as a follow-up.
- **New: 66 vitest cases** covering streaming commit, `cancelStream` (preserves committed history), `pruneChatStorage` (TTL/quota boundaries, combined ordering), and form-bridge degradation (null ref, throwing handle).
- **Modified: `/api/ai/generate/stream`** — Accepts an optional `messages` array and forwards it directly to OpenRouter. When `messages` is provided, the legacy single-turn `prompt`/`system_prompt`/`images` path is bypassed. Existing single-turn clients are unaffected.

## Capabilities

### New Capabilities

- `multi-turn-chat` — session lifecycle, streaming commit, cancellation, applied-field audit, hydrate/reset.
- `chat-form-bridge` — safe snapshot read, safe apply with structured result, message-payload assembly for LLM calls.
- `chat-persistence` — `ChatStorage` port + `pruneChatStorage` policy + `InMemoryChatStorage` adapter for fallback/testing.

### Modified Capabilities

- `ai-stream-multimessage` — the existing `/api/ai/generate/stream` endpoint gains a `messages` array entry-point for multi-turn conversation. Existing single-turn behavior preserved.

## Impact

- **Frontend**
  - New: `sau_web/frontend/src/stores/useChatStore.ts`
  - New: `sau_web/frontend/src/lib/chat/{types,storage,pruner,chatFormBridge}.ts`
  - New tests: `sau_web/frontend/src/lib/chat/{pruner,useChatFormBridge}.test.ts`, `sau_web/frontend/src/stores/useChatStore.test.tsx`
  - **Follow-up scope (out of this change):** `sau_web/frontend/src/components/AiSidebar/AiSidebar.tsx` — replace local `lastResult`/`isStreaming`/`streamingText` with store-driven state, wire `buildChatPayload` into the send path, route streamed chunks via `appendStreamingChunk`, commit/cancel via store actions.
  - **Follow-up scope (out of this change):** `sau_web/frontend/src/features/publish/{VideoForm,NoteForm}.tsx` — extend their `useImperativeHandle` to also expose `getFormSnapshot: () => { title, desc, tags }`. The bridge already has `applyAiResult` consumers.
- **Web API**
  - Modified: `web_runner/routes/ai.py` — `/api/ai/generate/stream` handler accepts `messages: [{role, content}]` and forwards it directly to `_stream_openrouter(model, messages, ...)` when present and non-empty. The single-turn `prompt`/`system_prompt`/`images` path remains the legacy fallback.
- **Dependencies**: none new. `zustand@5` already covers the store. We deliberately do NOT yet add `dexie` / `fake-indexeddb` — the `ChatStorage` interface is the DI seam to fill in a later change.
- **Configuration**: none new.
- **Tests**: 66 new cases pass; pre-existing failures in `AiPanelToolbar` / `TaskDrawer` / `TaskTableRow` / `NoteForm.test` / `VideoForm.test` are unrelated to this change and remain on the radar.
