# multi-turn-chat Specification

## Purpose
TBD - created by archiving change ai-sidebar-multi-turn-chat. Update Purpose after archive.
## Requirements
### Requirement: Chat session lifecycle

The system SHALL support creating, switching, and deleting chat sessions; each session is identified by a stable UUID and binds to a (formMode, platform) pair.

#### Scenario: User creates a new chat session

- **WHEN** the AI sidebar opens with `formMode = "video"` and `platform = "douyin"`
- **THEN** a new `ChatSession` is created with a UUID
- **AND** `activeSessionId` is set to that UUID
- **AND** the session's `title` is initially `"新对话"`, `messages` is `[]`, `formMode = "video"`, `platform = "douyin"`, `totalSize = 0`

#### Scenario: User switches to a previously-created session

- **WHEN** the user opens the session list and selects a session with id `S`
- **AND** session `S` exists in the store
- **THEN** `activeSessionId` is updated to `S`
- **AND** `switchSession` returns `true`

#### Scenario: Switching to a non-existent session is a no-op

- **WHEN** `switchSession` is called with an id not present in `sessions`
- **THEN** `activeSessionId` does not change
- **AND** `switchSession` returns `false`

#### Scenario: User deletes the active session

- **WHEN** the user deletes the session with id `S` and `S === activeSessionId`
- **THEN** `sessions[S]` is removed
- **AND** `activeSessionId` is set to `null`

#### Scenario: User deletes a non-active session

- **WHEN** the user deletes the session with id `S` and `S !== activeSessionId`
- **THEN** `sessions[S]` is removed
- **AND** `activeSessionId` is unchanged

### Requirement: User message append

The system SHALL accept user-typed messages and attach them to the active session, deriving the session title from the first message when the session is empty.

#### Scenario: Append succeeds for an existing session

- **WHEN** `appendUserMessage(sid, { content: "一份文案" })` is called
- **AND** session `sid` exists
- **THEN** a new `ChatMessage` with `role: "user"`, `content: "一份文案"`, and a fresh UUID is appended to `sessions[sid].messages`
- **AND** `sessions[sid].totalSize` increases by the byte size of the message content + attachments
- **AND** `sessions[sid].updatedAt` is updated to the current timestamp
- **AND** if `sessions[sid].messages` was empty, `sessions[sid].title` is derived from the content (truncated to 24 chars + ellipsis if longer)

#### Scenario: Append on a missing session is a no-op

- **WHEN** `appendUserMessage(missing_sid, ...)` is called
- **THEN** no state change occurs
- **AND** `appendUserMessage` returns `false`

#### Scenario: Title is not overwritten on subsequent messages

- **WHEN** the user appends a second message after the first
- **THEN** `sessions[sid].title` keeps the value derived from the first message

### Requirement: Streaming assistant message assembly

The system SHALL accumulate streamed SSE chunks into a transient `streamingDraft` and SHALL finalize it as an immutable assistant `ChatMessage` on `commitAssistantMessage`.

#### Scenario: Streaming chunks accumulate in order

- **WHEN** `appendStreamingChunk("标题")`, `appendStreamingChunk(": ")`, `appendStreamingChunk("炸鸡")` are called in sequence
- **THEN** `streamingDraft` becomes `"标题: 炸鸡"`
- **AND** `jobStatus` becomes `"generating"`

#### Scenario: Empty chunk is a no-op

- **WHEN** `appendStreamingChunk("")` is called
- **THEN** no state change occurs

#### Scenario: Commit finalizes the draft as the last assistant message

- **WHEN** `appendStreamingChunk("full reply")` was just called
- **AND** `commitAssistantMessage(sid)` is called for an existing session
- **THEN** `sessions[sid].messages` ends with a `ChatMessage` of `role: "assistant"`, `content: "full reply"`
- **AND** `streamingDraft` is reset to `""`
- **AND** `jobStatus` is set to `"idle"`
- **AND** `error` is cleared

#### Scenario: Commit on empty draft is a no-op

- **WHEN** `commitAssistantMessage(sid)` is called with `streamingDraft === ""`
- **THEN** no message is appended
- **AND** the returned value is `null`

#### Scenario: Commit on missing session preserves the draft

- **WHEN** `commitAssistantMessage(missing_sid)` is called with a non-empty draft
- **THEN** no message is appended
- **AND** `streamingDraft` is preserved (so the caller can retry)

### Requirement: Stream cancellation preserves committed history

The system SHALL support cancelling an in-flight stream while keeping all already-committed messages intact.

#### Scenario: Cancel during an active stream clears the draft

- **WHEN** `appendStreamingChunk("halfway")` has been called and `jobStatus === "generating"`
- **AND** `cancelStream()` is called
- **THEN** `streamingDraft` becomes `""`
- **AND** `jobStatus` becomes `"idle"`
- **AND** `cancelStream` returns `true`

#### Scenario: Cancel preserves previously committed messages

- **WHEN** the session already contains a completed turn `[user, assistant]`
- **AND** a new stream was started but cancelled
- **THEN** the session still contains the original `[user, assistant]` messages in order

#### Scenario: Cancel on idle is a no-op

- **WHEN** `jobStatus === "idle"`
- **AND** `cancelStream()` is called
- **THEN** no state change occurs
- **AND** `cancelStream` returns `false`

#### Scenario: Cancel from "enhancing" status also resets

- **WHEN** `jobStatus === "enhancing"`
- **AND** `cancelStream()` is called
- **THEN** `jobStatus` becomes `"idle"`
- **AND** `cancelStream` returns `true`

### Requirement: Applied-field audit

The system SHALL record which form fields a chat message has been applied to, deduplicating entries across multiple marks.

#### Scenario: First mark records the field set

- **WHEN** `markApplied(sid, msgId, ["title"])` is called and the message has no `appliedTo`
- **THEN** `sessions[sid].messages[*msgId*].appliedTo` becomes `["title"]`

#### Scenario: Subsequent marks are merged and deduplicated

- **WHEN** `markApplied(sid, msgId, ["title"])` is called twice
- **AND** then `markApplied(sid, msgId, ["desc", "tags"])` is called
- **THEN** `appliedTo` becomes `["title", "desc", "tags"]` (no duplicates, all fields present)

#### Scenario: Empty fields array is a no-op

- **WHEN** `markApplied(sid, msgId, [])` is called
- **THEN** no state mutation occurs

### Requirement: Hydrate and reset

The system SHALL support hydrating the store from an external list of `ChatSession` records, and SHALL support resetting its state for tests.

#### Scenario: Hydrate populates sessions and active

- **WHEN** `hydrate([sessionA, sessionB], "sessionB")` is called
- **THEN** `sessions` contains both A and B by id
- **AND** `activeSessionId` is `sessionB.id`

#### Scenario: Hydrate ignores unknown activeId

- **WHEN** `hydrate([sessionA], "missing-id")` is called
- **THEN** `activeSessionId` is `null`
- **AND** `sessions` still contains `sessionA`

#### Scenario: Reset zeroes everything

- **WHEN** `reset()` is called from a populated state
- **THEN** `sessions` is `{}`, `activeSessionId` is `null`, `jobStatus` is `"idle"`, `streamingDraft` is `""`, `error` is `null`

