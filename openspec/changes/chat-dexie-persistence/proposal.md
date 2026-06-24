# Why

`ai-sidebar-multi-turn-chat` shipped `useChatStore` with a `ChatStorage` DI seam and only an `InMemoryChatStorage` adapter. Sessions therefore vanish on page reload — chat history resets to whatever survives React unmounting. With chat as the primary UX, losing prior turns breaks the multi-turn promise (no "shorten / add emoji / translate" continuity across reloads).

We add a Dexie/IndexedDB adapter that becomes the production storage backend. The `ChatStorage` port from the prior change pays off here: the store, pruner, and chat hooks are unchanged; only the adapter + a startup wiring glues make `chat-dexie-persistence` a pure addition.

## What Changes

- Add `dexie` as a runtime dependency in `sau_web/frontend/package.json`.
- Add `fake-indexeddb` as a dev dep so the adapter unit tests run under vitest without a real browser.
- Implement `DexieChatStorage implements ChatStorage` in `src/lib/chat/storage.ts` (alongside the existing `InMemoryChatStorage`). Two tables:
  - `sessions` — `id` PK, `updatedAt` secondary index (used for pruner sort + `listSessions` ordering).
  - `messages` — `id` PK, `[sessionId+createdAt]` compound secondary index (used to delete a session's messages atomically).
- On app startup, in `src/main.tsx`:
  1. Open the Dexie database (auto-creates schema on first open).
  2. Run `pruneChatStorage(dexieAdapter, DEFAULT_PRUNE_POLICY)` to drop TTL-expired / over-quota survivors before hydration.
  3. Call `useChatStore.getState().hydrate(persistedSessions, lastActiveSessionId)`.
  4. Register a single zustand `subscribe` listener that diffs session snapshots and persists changed sessions via `saveSession(...)`.

## Capabilities

### New Capabilities

- (none — extending the existing `chat-persistence` capability).

### Modified Capabilities

- `chat-persistence` — adds a Dexie-backed `ChatStorage` implementation and the startup wiring contract that hydrate-after-prune + write-through on mutation. The existing `ChatStorage` interface, `InMemoryChatStorage`, and `pruneChatStorage` rules are unchanged.

## Impact

- **Frontend**
  - New class: `DexieChatStorage` in `sau_web/frontend/src/lib/chat/storage.ts` (sibling to `InMemoryChatStorage`).
  - New tests: `sau_web/frontend/src/lib/chat/storage.dexie.test.ts` — adapter CRUD plus a shared `chatStorageContractSuite(DexieChatStorageFactory)` that mirrors the in-memory test contracts.
  - Modified: `sau_web/frontend/src/main.tsx` (or a thin `bootstrapChatPersistence()` module) — startup wiring.
  - Modified: `sau_web/frontend/vitest.config.ts` (or `src/test/setup.ts`) — load `fake-indexeddb/auto` so vitest has a real IndexedDB-shaped global.
- **Backend**: none — no API, CLI, or DB changes.
- **Dependencies**
  - Runtime (frontend): `dexie@^4` (latest stable; v3 is the prior API surface and v4 has cleaner bulk-op typing).
  - Dev (frontend): `fake-indexeddb@^6` (vitest harness; matches `dexie@4`'s API expectations).

## Verification

- Vitest: `pnpm vitest run src/lib/chat` — the new adapter tests join the existing 66-case primitive suite and all pass.
- Manual smoke: open `bash sau_web/start.sh`, visit `/publish`, run multi-turn ("shorten title / add emoji / translate"), hard-refresh the page, observe history is restored. Repeat with SessionStorage dev-tools clear to confirm prune leaves the store empty rather than broken.
