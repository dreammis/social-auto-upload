# Capability: chat-persistence

## Purpose

Persist chat sessions across page reloads, enforce time-based and size-based capacity limits, and define a swappable storage backend so future migrations to IndexedDB don't require schema changes.

## ADDED Requirements

### Requirement: Pluggable storage port

The system SHALL define a `ChatStorage` interface with three methods: `listSessions`, `saveSession`, `deleteMany`. Initial implementation SHALL be `InMemoryChatStorage`.

#### Scenario: Listing returns all sessions sorted by updatedAt desc

- **WHEN** `listSessions` is invoked
- **THEN** every saved session is returned
- **AND** the array is sorted with the most-recently-updated session first

#### Scenario: Delete-many removes exactly the given ids

- **WHEN** `deleteMany(["a", "c"])` is called against a storage containing `a, b, c`
- **THEN** the storage afterwards contains only `b`

### Requirement: TTL prune runs before quota

`pruneChatStorage` SHALL delete sessions older than `policy.ttlMs` from `now` BEFORE running quota logic.

#### Scenario: Sessions older than the TTL cutoff are removed

- **WHEN** `now = T`, `ttlMs = D`, and a session has `updatedAt < T - D`
- **THEN** that session is removed
- **AND** its id appears in `deletedByTtl`

#### Scenario: A session exactly at the TTL cutoff is kept

- **WHEN** a session has `updatedAt === now - ttlMs`
- **THEN** it is NOT deleted
- **AND** it does NOT appear in `deletedByTtl`

### Requirement: Quota prune runs only against TTL survivors

After TTL pruning, if the combined `totalSize` of survivors exceeds `policy.maxTotalBytes`, the OLDEST survivors SHALL be deleted one at a time until the total is `<= maxTotalBytes`.

#### Scenario: Quota prune deletes oldest first

- **WHEN** survivors have `totalSize` summing to `S > maxTotalBytes`
- **THEN** the returned `deletedByQuota` list is ordered by `updatedAt` ascending
- **AND** pruning stops as soon as `remaining <= maxTotalBytes`

#### Scenario: A total exactly equal to maxTotalBytes is kept

- **WHEN** the survivors' total equals `maxTotalBytes`
- **THEN** no quota prune occurs
- **AND** `deletedByQuota` is empty

#### Scenario: TTL removes everything; quota phase is a no-op

- **WHEN** every session is TTL-expired
- **THEN** `deletedByQuota` is empty
- **AND** no negative `freedBytes` are reported

### Requirement: Default policy

The default `pruneChatStorage` policy SHALL be 7-day TTL and 50MB total cap. The policy is overridable per call.

#### Scenario: Default policy values

- **WHEN** `pruneChatStorage(storage)` is called without a policy arg
- **THEN** `ttlMs` is `7 * 24 * 60 * 60 * 1000`
- **AND** `maxTotalBytes` is `50 * 1024 * 1024`
