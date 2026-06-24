# Dexie Chat Persistence — Design

## Context

`ai-sidebar-multi-turn-chat` shipped `useChatStore` together with a `ChatStorage` port and only an `InMemoryChatStorage` adapter. The port + `pruneChatStorage(adapter, policy)` already support any backend — this change fills the seam with `DexieChatStorage` so chat sessions survive across page reloads. The store, the form-bridge, and the SSE pipeline are unchanged.

## Decisions

### D1 — Dexie over raw IndexedDB

Dexie wraps the raw IndexedDB API with promises, a fluent schema declaration, and bulk operations (`bulkPut`, `bulkDelete`, `where(...).equals(...)`). The schema in D2 reads almost identically to a SQL DDL, and Dexie's transaction primitives map onto the `saveSession` + `pruneChatStorage` semantics without hand-rolling event-listener boilerplate.

**Cost**: ~25 KB gzipped runtime weight. Acceptable — chat is the primary sidebar UX in the publish flow.

### D2 — Two-table schema

```
db.version(1).stores({
  sessions:  'id, updatedAt',                                  // id PK + updatedAt idx
  messages:  'id, [sessionId+createdAt], sessionId',           // id PK + compound idx
  _meta:     'key'                                              // singleton for lastActiveSessionId
})
```

`sessions` carries the per-session envelope. `messages` carries individual messages with a compound `[sessionId+createdAt]` index so `messages.where('sessionId').equals(s.id).delete()` cleanly removes everything for a session before a fresh `messages.bulkPut(s.messages)`. `_meta` is a singleton table for the last-active-session id, chosen over localStorage so it shares the same life-cycle as the chat data (cleared by `chatDB.deleteMany` on a full reset).

**Rationale**: this schema is the minimal one that supports `listSessions` (sort by `updatedAt`), `saveSession` (replace messages atomically), `deleteMany` (cascade), and active-id persistence.

### D3 — Diff-and-write zustand subscriber

`useChatStore.subscribe(state => …)` covers all mutations (append / commit / cancel / markApplied / newSession / deleteSession / setJobStatus). The listener keeps a `lastSeen` snapshot of `{[id]: session}` against `state.sessions`, computes the diff, and persists only changed sessions. Debounced 100 ms so a flurry of mutations from a single send → commit → markApplied burst coalesces into one write.

- **D3a — Flush-on-unmount**: the listener registers a `beforeunload` + module teardown hook that drains any in-flight debounced writes synchronously, so a page reload during the debounce window cannot silently drop the most recent mutation.
- **D3b — StrictMode guard**: the listener-install path is wrapped in an `if (listenerInstalled)` flag stored outside the React effect closure so the React 18 StrictMode dev double-invoke cannot double-write. Production mounts (non-StrictMode main.tsx) hit the guard exactly once.

`reset()` (used by tests + the future "clear all chats" UI) triggers a `chatDB.sessions.clear() + chatDB.messages.clear() + chatDB._meta.clear()` and then a rehydrate of `[]`. This keeps the adapter-level reset symmetric with the store-level reset.

**Cost**: one extra map held in the listener closure. Negligible (≪ 1 KB).

### D4 — Prune-then-hydrate order on startup

```
1. chatDB.listSessions()                                    // first touch opens the DB
2. pruneChatStorage(chatDB, DEFAULT_PRUNE_POLICY)           // drop TTL-expired + over-quota BEFORE hydration
3. useChatStore.getState().hydrate(survivors, lastActiveId) // populate in-memory state
4. useChatStore.subscribe(...)                              // arm the write-through listener
```

**Rationale**: prune first so hydrated state is already bounded, avoiding "flash of stale data" on a fresh load and keeping the in-memory footprint tighter. Step 4 must come AFTER step 3 so the subscriber's first invocation doesn't redundantly re-write the hydrated state — gated with `if (JSON.stringify(state.sessions) === JSON.stringify(lastSeen)) return`.

## Non-Goals

- Cross-device sync via backend (out of scope; local-only at MVP).
- Replacing the existing `InMemoryChatStorage` — kept for vitest and a future fallback surface.
- Schema migrations between Dexie versions (MVP: single `v1`).
- Encrypted at-rest (users trust their own browser context for chat metadata).
- Auto-replay of streamed-but-uncommitted turns on reload — a half-streamed draft is intentionally discarded because there is no LLM handle to resume.
