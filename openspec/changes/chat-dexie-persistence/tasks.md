# Tasks

## 1. Dependencies

- [ ] Add `dexie@^4` as a runtime dep in `sau_web/frontend/package.json` `dependencies` + `pnpm install`
- [ ] Add `fake-indexeddb` as a dev dep in `sau_web/frontend/package.json` `devDependencies` + `pnpm install`; pin to the latest published major discovered via `pnpm view fake-indexeddb version` at install time (record the chosen version in this task once known).
- [ ] Verify `pnpm tsc -b -p tsconfig.app.json` resolves `dexie` types without extra `tsconfig` edits; record any required `types` additions in `design.md` (not in tasks) if found. `"types": ["vite/client"]` to `tsconfig.app.json` only if needed)

## 2. DexieChatStorage adapter

- [ ] Implement `DexieChatStorage` in `sau_web/frontend/src/lib/chat/storage.ts` (extend the file that already hosts `InMemoryChatStorage`):
  - Two-table schema declared in a class-level `db` field: `sessions` (id PK, `updatedAt` idx), `messages` (id PK, `[sessionId+createdAt]` idx).
  - `listSessions(): Promise<ChatSession[]>` — reads `db.sessions.orderBy('updatedAt').reverse().toArray()` and joins messages for each.
  - `saveSession(s: ChatSession): Promise<void>` — single Dexie transaction: `db.sessions.put(s)` then `db.messages.where('sessionId').equals(s.id).delete()` then `db.messages.bulkPut(s.messages)`.
  - `deleteMany(ids: string[]): Promise<void>` — single transaction: `db.sessions.bulkDelete(ids)` + `db.messages.where('sessionId').anyOf(ids).delete()`.
- [ ] Re-export `DexieChatStorage` from `sau_web/frontend/src/lib/chat/index.ts` (or current barrel) for ergonomic import.

## 3. Startup wiring

- [ ] In `sau_web/frontend/src/main.tsx` (or a dedicated `bootstrapChatPersistence.ts` module imported from `main.tsx`):
  - Open Dexie once at module load: `const chatDB = new DexieChatStorage()`.
  - Run `await pruneChatStorage(chatDB, DEFAULT_PRUNE_POLICY)` BEFORE hydration.
  - Read surviving sessions via `await chatDB.listSessions()` and assume `activeSessionId` from a small `_meta` table or the most-recent updated session id (decision: store last-active via a `_meta(singleton)` table).
  - Call `useChatStore.getState().hydrate(sessions, lastActiveSessionId)`.
  - Register a single `useChatStore.subscribe(state => { … })` listener that diffs the prior sessions snapshot against the new state and `await`s `chatDB.saveSession(s)` for each changed session. Debounce bulk saves (e.g., 100 ms) if more than N mutations arrive in a tick.
- [ ] Hook the same listener to `useChatStore.persist.clear()` (or store-reset action) to call `chatDB.deleteMany(Object.keys(useChatStore.getState().sessions))` then rehydrate empty.

## 4. Test harness

- [ ] Configure vitest to install `fake-indexeddb/auto` (so `window.indexedDB` exists): either in `sau_web/frontend/vitest.config.ts`'s `setupFiles: ['fake-indexeddb/auto', './src/test/setup.ts']`, or in the existing `src/test/setup.ts` at the top.
- [ ] Add `sau_web/frontend/src/lib/chat/storage.dexie.test.ts`:
  - `listSessions` returns rows sorted by `updatedAt` desc.
  - `saveSession` upserts the session then replaces its messages atomically (no stale messages from a prior save).
  - `deleteMany` removes rows from both `sessions` and `messages`.
  - `pruneChatStorage(dexieAdapter, policy)` against the live Dexie instance respects TTL + quota contracts (reuse the same pruner tests, parameterised over adapter factory).
  - A `chatStorageContractSuite(DexieChatStorageFactory)` runs the existing `InMemoryChatStorage` test bodies against the Dexie adapter (one source of truth for behavior) — copied or imported.
- [ ] Run `pnpm vitest run src/lib/chat` and confirm full primitive + adapter suite is green.

## 5. Verification

- [ ] `pnpm vitest run src/lib/chat src/stores/useChatStore.test.tsx` — full chat suite green (existing 99 + new Dexie cases).
- [ ] `pnpm tsc -b` — chat-files only clean (global clean is out of scope per prior step).
- [ ] Manual smoke: `bash sau_web/start.sh`, open `/publish`, run multi-turn, hard refresh, confirm history survives; verify under Application → IndexedDB → `social-auto-upload-chat` (or auto-generated Dexie DB name) the expected schema is present.
