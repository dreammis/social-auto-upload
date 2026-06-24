# ai-stream-multimessage Specification

## Purpose
TBD - created by archiving change ai-sidebar-multi-turn-chat. Update Purpose after archive.
## Requirements
### Requirement: Multi-turn message forwarding

When the request body contains a non-empty `messages` array, the handler SHALL forward that array directly to `_stream_openrouter(model, messages, ...)` and SHALL NOT collapse it into a single prompt.

#### Scenario: Multi-turn request forwards the messages array verbatim

- **WHEN** the client POSTs `{ model, messages: [{role:"system",...}, {role:"user",...}], platform }`
- **THEN** `_stream_openrouter` receives exactly that array
- **AND** the response SSE stream yields `event: data` / `event: done` events consistent with the existing protocol

#### Scenario: Multi-turn request bypasses the single-turn prompt/system_prompt/images path

- **WHEN** the request body contains `messages` AND also contains `prompt`, `system_prompt`, or `images`
- **THEN** the `messages` array takes precedence
- **AND** the legacy single-turn assembly code is NOT executed

### Requirement: Single-turn fallback preserved

When the request body does NOT contain a `messages` array (or contains an empty one), the handler SHALL run the existing single-turn path unchanged.

#### Scenario: Single-turn text-only request

- **WHEN** the client POSTs `{ model, prompt: "...", platform: "douyin" }` with no `messages` field
- **THEN** the handler uses `PLATFORM_PROMPTS[platform]` as `system_prompt`
- **AND** a `[system, user]` messages array is constructed from `system_prompt` + `prompt`
- **AND** the response SSE stream yields the assistant content

#### Scenario: Single-turn multimodal request still works

- **WHEN** the client POSTs `{ model, prompt: "...", images: [...] }` with no `messages` field
- **THEN** the handler uses `_build_media_content(images, prompt)` for the user message
- **AND** the multimodal OpenRouter call runs unchanged

### Requirement: Bounded message count

The handler SHALL reject requests whose `messages` array exceeds a hard cap to prevent context-window abuse and unbounded LLM cost.

#### Scenario: Oversized messages array

- **WHEN** the request body contains `messages.length > 30`
- **THEN** the handler returns an SSE `event: error` event with a `"Too many messages..."` message
- **AND** no OpenRouter call is made

