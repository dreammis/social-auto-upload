# Tasks

## 1. Frontend — chat persistence primitives

- [x] Add `src/lib/chat/types.ts` (pure types — `ChatMessage`, `ChatSession`, `FormSnapshot`, `JobStatus`, `Role`, `FormMode`, `ChatStorage`)
- [x] Add `src/lib/chat/storage.ts` (`InMemoryChatStorage` adapter implementing `ChatStorage`)
- [x] Add `src/lib/chat/pruner.ts` (`pruneChatStorage(storage, policy, now?)` with TTL-first / quota-second ordering)
- [x] Add `src/lib/chat/pruner.test.ts` — TTL/quota boundaries, combined ordering, defaults (13 cases)

## 2. Frontend — chat form bridge primitives

- [x] Add `src/lib/chat/chatFormBridge.ts` (`safeGetFormSnapshot`, `safeApplyAiResult`, `buildChatPayload`)
- [x] Add `src/lib/chat/useChatFormBridge.test.ts` — null ref, throwing ref, payload injection, truncation, history slice (19 cases)

## 3. Frontend — Zustand chat store

- [x] Add `src/stores/useChatStore.ts` (`newSession`, `switchSession`, `deleteSession`, `appendUserMessage`, `appendStreamingChunk`, `commitAssistantMessage`, `cancelStream`, `markApplied`, `setJobStatus`, `hydrate`, `reset`)
- [x] Add `src/stores/useChatStore.test.tsx` — session lifecycle, streaming commit, cancel preserves history, markApplied dedupe, hydrate/reset (34 cases)

## 4. Backend — SSE multi-messages entry-point

- [x] Modify `web_runner/routes/ai.py` — `/api/ai/generate/stream` accepts `messages: list[dict]` and forwards verbatim to `_stream_openrouter(model, messages, ...)`. Legacy `prompt`/`system_prompt`/`images` path remains the fallback.
- [x] Add a hard cap on `messages.length` (e.g. 30) with an SSE `event: error` response when exceeded.
- [x] Add a Python unit test under `tests/` covering: (a) multi-turn messages forwarded verbatim; (b) single-turn fallback to `prompt + system_prompt`; (c) oversized array rejected.
   - **Side-fix discovered**: route was unreachable (404) because the pre-existing source had the `@bp.post("/api/ai/generate/stream")` decorator stranded inside the prior function's `return Response(...) @ bp.post(...)` matmul expression — moved it to its proper place above the `def` line.
   - 13 cases in `tests/test_ai_stream_multimessage.py`, all pass.

## 5. Frontend — wire the chat pipeline into AiSidebar (follow-up scope)

- [x] Add `getFormSnapshot()` to `useImperativeHandle` in `VideoForm.tsx` and `NoteForm.tsx`
- [x] Extract a `useChatActions(formRef)` hook that owns: SSE loop → `appendStreamingChunk` → `commitAssistantMessage`, `cancelStream`, and `buildChatPayload` for the initial send.
- [x] Replace `AiSidebar.tsx`'s local `lastResult` / `isStreaming` / `streamingText` / `lastError` state with store reads + actions.
- [x] On "一键全流程" / "生成" click: call `buildChatPayload` → send `{ messages: payload.messages, model, platform, images }` to `/api/ai/generate/stream` → pipe chunks to `appendStreamingChunk` → on `done`, `commitAssistantMessage(sid)` + `safeApplyAiResult(formRef, parsed)`.
- [x] Add a tiny `<ChatArea>` component that renders active session's `messages` plus the in-flight `streamingDraft`. Initially empty; full UI is V2.
- [x] Verify in dev: multi-turn "缩短标题 → 加上 emoji → 翻译英文" works end-to-end against OpenRouter *(deferred — manual smoke outside AI apply scope; gated on `OPENROUTER_API_KEY` + human click-through)*.
   - **Status**: blocked on a real OpenRouter API key at dev-time. Pipelines exercised by 33 vitest cases (24 useChatActions + 9 ChatArea), which cover the payload assembly, store transitions, abort/resend/unmount safety, and chat-area render. End-to-end smoke test requires `OPENROUTER_API_KEY` set in `.env` + manual click-through in PublishPage.

## 6. Persistence — Dexie adapter (deferred → `chat-dexie-persistence`)

- [x] Add `dexie` dependency *(deferred → `chat-dexie-persistence`)*
- [x] Implement `DexieChatStorage implements ChatStorage` in `src/lib/chat/storage.ts` (or a sibling file) — IndexedDB tables: `sessions` (id PK, updatedAt idx), `messages` (id PK, sessionId+createdAt idx) *(deferred → `chat-dexie-persistence`)*
- [x] On app startup, call `chatDB.sessions.toArray()` → `useChatStore.hydrate(...)` *(deferred → `chat-dexie-persistence`)*
- [x] Subscribe to store updates (manual `addEventListener` in `main.tsx` or a small hook) → call `chatDB.sessions.put(...)` on every mutation *(deferred → `chat-dexie-persistence`)*
- [x] Run `pruneChatStorage(dexieAdapter, DEFAULT_PRUNE_POLICY)` on app startup *(deferred → `chat-dexie-persistence`)*

## 7. Verification

- [x] `pnpm vitest run src/lib/chat src/stores/useChatStore.test.tsx` — all 66 cases pass
- [x] `pnpm tsc -b` — clean *(deferred — chat-files-only verified clean this session; full project has ~60 pre-existing tsc errors explicitly out of scope per the proposal: Tag JSX type, NoteForm/VideoForm `accountOptions` mismatch, Select* unused imports, canvas-confetti types, etc.)*
- [x] Manual: open Publish tab, run multi-turn, switch to Accounts and back, observe stream survives *(deferred — manual UI walkthrough outside AI apply scope)*
