# Capability: chat-form-bridge

## Purpose

Read the publish form's current field values into the chat pipeline (snapshot at send time) and apply assistant outputs back to the form (one-shot on demand). All interactions degrade gracefully when the form is unmounted.

## ADDED Requirements

### Requirement: Safe form snapshot read

`safeGetFormSnapshot(ref)` SHALL return the current form snapshot OR `null` if the form is unmounted OR the form throws during the read.

#### Scenario: Form mounted, returns verbatim snapshot

- **WHEN** the form is mounted and `getFormSnapshot` returns `{ title: "X", desc: "Y", tags: "Z" }`
- **THEN** `safeGetFormSnapshot` returns the same object

#### Scenario: Form unmounted, returns null

- **WHEN** `ref.current === null`
- **THEN** `safeGetFormSnapshot` returns `null`

#### Scenario: Form throws, returns null without propagating

- **WHEN** `ref.current.getFormSnapshot()` throws
- **THEN** `safeGetFormSnapshot` returns `null`
- **AND** the throw is not propagated out of the wrapper

### Requirement: Safe form apply with structured result

`safeApplyAiResult(ref, result)` SHALL call `applyAiResult` on the live form and SHALL return a structured outcome indicating success or the failure cause.

#### Scenario: Apply on mounted form succeeds

- **WHEN** the form is mounted and `applyAiResult` is callable
- **THEN** `safeApplyAiResult` invokes the form's `applyAiResult` with the given result
- **AND** returns `{ applied: true }`

#### Scenario: Apply on unmounted form is a structured no-op

- **WHEN** `ref.current === null`
- **THEN** `safeApplyAiResult` does not call any form method
- **AND** returns `{ applied: false, reason: "unmounted" }`

#### Scenario: Apply that throws is caught

- **WHEN** `ref.current.applyAiResult` throws an exception
- **THEN** `safeApplyAiResult` returns `{ applied: false, reason: "threw" }`
- **AND** the exception does not propagate out of the wrapper

### Requirement: LLM message payload assembly

`buildChatPayload({ ref, history, text, recentTurns? })` SHALL produce the messages array sent to the LLM for the next turn, with the form snapshot injected as a transient system message when the form is mounted.

#### Scenario: Form mounted → snapshot injected as system message

- **WHEN** the form is mounted and `history.length > 0`
- **THEN** messages begin with the history slice
- **AND** a system message describing the snapshot (`标题: ...; 描述: ...; 标签: ...`) is inserted immediately before the new user turn
- **AND** the returned `formAttached` is `true`

#### Scenario: Form unmounted → no system message, response still works

- **WHEN** `ref.current === null`
- **THEN** messages contain only the history slice and the new user turn
- **AND** no system message is inserted
- **AND** the returned `formAttached` is `false`
- **AND** the returned `formSnapshot` is `null`

#### Scenario: `recentTurns: 0` keeps none of the history

- **WHEN** `recentTurns: 0` is passed
- **THEN** the history slice passed to the LLM is empty
- **AND** only the (optional) form snapshot and the new user turn are sent

#### Scenario: Description snapshot is truncated to 200 characters

- **WHEN** the form snapshot has `desc.length > 200`
- **THEN** the injected system message contains only the first 200 characters of `desc`

#### Scenario: Empty fields render (空) placeholders

- **WHEN** the snapshot has `title`, `desc`, and `tags` all empty
- **THEN** the injected system message uses `"(空)"` placeholders for each
