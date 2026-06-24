# Capability: chat-persistence

## Purpose

This change adds a Dexie/IndexedDB-backed `ChatStorage` implementation as the production backend, plus the startup wiring that prunes-then-hydrates-then-listens. The existing `ChatStorage` interface, `InMemoryChatStorage` adapter, and `pruneChatStorage` contract from the prior change are unchanged; this change fills the seam with one more implementation.

## ADDED Requirements

### Requirement: Dexie-backed ChatStorage adapter SHALL be the production backend

The system SHALL provide a `DexieChatStorage` class that implements the `ChatStorage` interface and persists sessions and their messages to IndexedDB via the `dexie` library. The schema SHALL use two tables:

- `sessions` with `id` as primary key and `updatedAt` as a secondary index.
- `messages` with `id` as primary key and `[sessionId+createdAt]` as a compound secondary index.

#### Scenario: listSessions returns Dexie rows sorted by updatedAt desc

- **WHEN** `new DexieChatStorage().listSessions()` is called after seeding the adapter with three sessions of differing `updatedAt`
- **THEN** the returned array is sorted with the most-recently-updated session first
- **AND** each returned session's `messages` field is populated from the `messages` table

#### Scenario: saveSession atomically replaces a session's messages

- **WHEN** `saveSession(s)` is called for an existing `s.id` with a new `messages` array
- **THEN** the previous messages for that session are deleted
- **AND** the new messages are inserted in a single Dexie transaction covering both the session upsert AND the messages replace
- **AND** no stale messages from the prior save remain in the `messages` table for that `sessionId`

#### Scenario: deleteMany removes from both tables

- **WHEN** `deleteMany(['a', 'c'])` is called against a Dexie instance containing sessions `a, b, c` and their messages
- **THEN** the `sessions` table no longer contains rows whose `id` is in `{a, c}`
- **AND** the `messages` table no longer contains rows whose `sessionId` is in `{a, c}`
- **AND** session `b` and its messages are untouched

### Requirement: App startup SHALL prune, hydrate, and write-through between the store and Dexie

The app entry point SHALL, after the React tree mounts:

- run `pruneChatStorage(dexieAdapter, DEFAULT_PRUNE_POLICY)` so TTL-expired and over-quota sessions are removed BEFORE hydration
- call `useChatStore.getState().hydrate(persistedSessions, lastActiveSessionId)` to populate in-memory state with the surviving sessions
- register a single zustand `subscribe` listener that persists each mutated session via `DexieChatStorage.saveSession(...)`

#### Scenario: Hydrate populates the store from Dexie

- **WHEN** the app starts with Dexie containing two sessions and a persisted last-active id that matches one of them
- **THEN** after startup, `useChatStore.getState().sessions` contains both sessions by id
- **AND** `useChatStore.getState().activeSessionId` equals the persisted active id

#### Scenario: Hydrate ignores unknown active id

- **WHEN** the persisted `lastActiveSessionId` does not match any persisted session id (deleted or tampered with)
- **THEN** `useChatStore.getState().activeSessionId` is `null`
- **AND** the sessions themselves are still hydrated

#### Scenario: Prune runs before hydrate on startup

- **WHEN** Dexie contains a session with `updatedAt` older than `now - DEFAULT_PRUNE_POLICY.ttlMs`
- **THEN** that session is removed by `pruneChatStorage` BEFORE the store is hydrated
- **AND** the hydrated state contains only TTL-survivor sessions

#### Scenario: Subsequent mutations are persisted via the subscriber

- **WHEN** the store mutates after startup (e.g., `appendUserMessage`, `commitAssistantMessage`, `markApplied`, `deleteSession`)
- **THEN** the subscriber invokes `DexieChatStorage.saveSession(...)` for each session whose snapshot changed since the last write
- **AND** the next page reload reflects the mutations from the persisted state

#### Scenario: reset clears the in-memory store and all persistent tables

- **WHEN** `useChatStore.getState().reset()` is invoked
- **THEN** `sessions`, `_meta`, and the `messages` table in IndexedDB are cleared
- **AND** the in-memory store shows `sessions === {}`, `activeSessionId === null`, `streamingDraft === ""`, `jobStatus === "idle"`

### Requirement: vitest SHALL exercise DexieChatStorage against a real IndexedDB-shaped API

The vitest configuration SHALL install `fake-indexeddb/auto` so `window.indexedDB` is defined before any module that opens Dexie. A shared `chatStorageContractSuite(adapterFactory)` SHALL be defined and invoked once per adapter implementation so the same test bodies prove behaviour against `InMemoryChatStorage` AND `DexieChatStorage`.

#### Scenario: Dexie adapter passes the shared contract suite

- **WHEN** `chatStorageContractSuite(() => new DexieChatStorage())` runs in vitest
- **THEN** every assertion that holds for `InMemoryChatStorage` also holds for `DexieChatStorage`
- **AND** the pruner's TTL + quota contracts run against the Dexie adapter without modification
