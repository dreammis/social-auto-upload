# Multi-Turn Chat Design

## Context

The current AI sidebar runs a single-turn pipeline: the user composes an instruction, optionally with attachments; on click, an SSE stream populates a result, which is one-shot applied to the publish form. The same model selector / API key / template UX applies, but iteration requires manually re-doing the whole flow.

This change establishes a multi-turn chat layer underneath the sidebar, so iteration becomes natural (user says "shorten that title" → AI rewrites the already-displayed output). It is the prerequisite for future skill expansion (Rewriter, A/B-Title, SEO-Tool) and per-feature operations chips.

V0 ships the underlying primitive (`useChatStore` + bridge + persistence interface + backend SSE multi-messages) plus its unit-test suite. Wiring the existing `AiSidebar.tsx` (1061 lines) onto this primitive is left as a follow-up so the change remains reviewable in one pass.

## Goals

- **G1** Multi-turn iteration over the same chat session, with stable context across page navigation.
- **G2** Form-aware grounding — the LLM sees the user's *current* form edits just before each turn (snapshot at send time).
- **G3** Graceful degradation when the publish form is unmounted (e.g. user navigated to Accounts/Tasks tabs).
- **G4** Bounded persistence — sessions don't blow past quota; stale ones are auto-pruned.
- **G5** Testable in isolation — store + bridge + pruner are pure and unit-covered.

## Non-Goals

- Skill marketplace or custom-skill editor (deferred to follow-up spec).
- Quality scoring (per the original plan §7) — the AI-as-judge pattern is misleading and is deferred.
- Mobile-first layout refactor of the sidebar.
- Cross-device sync via backend persistence — local-only at MVP.
- SSE protocol redesign — `event: data | event: done | event: error` stays as-is; multi-turn runs through the same endpoint with the new `messages` parameter.

## Decisions

### D1 — Zustand store + thin DI persistence interface

```ts
interface ChatStorage {
  listSessions(): Promise<ChatSession[]>
  saveSession(s: ChatSession): Promise<void>
  deleteMany(ids: string[]): Promise<void>
}
```

`useChatStore` owns runtime state (messages, streaming draft, active session, error). Persistence runs *outside* the store, calling `storage.saveSession` after each append. This keeps the store unit-testable without IndexedDB.

**Rationale**: avoids the "test against real Dexie" anti-pattern; isolates the choice of persistence backend.

**Cost**: every save is a separate write call. Acceptable — `appendUserMessage` and `commitAssistantMessage` are user-initiated, not high-frequency.

### D2 — Streaming command trio, not a single setter

```
appendStreamingChunk(chunk)   → mutates `streamingDraft`, flips status to 'generating'
commitAssistantMessage(sid)  → promotes `streamingDraft` into a final `ChatMessage`
cancelStream()                → discards `streamingDraft`, preserves `sessions`
```

**Rationale**: caller (the SSE loop in `api.generateAiContentStream`) has discrete, idempotent commands. No mid-draft mutation that needs reconciliation.

**Alternative rejected**: a single "streamed message" object with a `status: 'pending'|'complete'|'cancelled'`. Rejected because it dumped too much logic into the store action.

### D3 — Form bridge goes through the existing imperative ref

`VideoFormHandle` and `NoteFormHandle` already expose `applyAiResult` via `useImperativeHandle`. We add a sibling `getFormSnapshot: () => { title, desc, tags }` (follow-up scope).

`buildChatPayload({ ref, history, text })`:
- Reads `ref.current?.getFormSnapshot()` at send time (user-edits-wins).
- Injects a system message ONLY when the snapshot is non-null AND the form is mounted.
- Slices `history` to the last N turns (configurable, default full) to bound token usage.

**Rationale**: keeps the form components unchanged in shape; avoids dragging the publish form's state into the chat store.

**Alternative rejected**: shared store where both chat and form read/write the same fields. Rejected because form state has dozens of fields not relevant to chat; coupling is high-risk.

### D4 — Unmounted degradation contract

Every cross-boundary call goes through a safe wrapper:

| Wrapper | When ref is non-null | When ref is null |
|---|---|---|
| `safeGetFormSnapshot` | FormSnapshot | null |
| `safeApplyAiResult` | `{ applied: true }` | `{ applied: false, reason: 'unmounted' }` |
| `buildChatPayload` | payload w/ form context | payload w/o form context, `formAttached: false` |

**Rationale**: a user switching tabs must not break the chat pipeline. Errors propagate nowhere; callers explicitly downgrade by checking the return type.

### D5 — Two-phase pruner (TTL → quota)

`pruneChatStorage(storage, policy, now)`:
1. **TTL**: delete sessions where `updatedAt < now - ttlMs`. Default 7 days.
2. **Quota**: against survivors only, delete oldest until `sum(totalSize) <= maxTotalBytes`. Default 50MB.

Both phases use strict inequalities at the boundary: a session exactly at `now - ttlMs` is kept; a session set whose total exactly equals `maxTotalBytes` is kept.

**Rationale**: TTL is the cheap time-based decision; quota is the size-based decision. Running them in this order makes quota math cheaper and avoids "resurrecting" TTL-stale data.

### D6 — Backend uses a "messages array" entry-point, not a new endpoint

`/api/ai/generate/stream` gains `messages?: ChatMessageForApi[]`. When present and non-empty, the existing `_stream_openrouter(model, messages, ...)` is used *unchanged* — it already accepted arbitrary `messages` arrays from the OpenAI-compatible API. The single-turn prompt path remains as the legacy fallback.

**Rationale**: zero new endpoints, zero new SSE protocols, zero new client surface. The frontend just sends `messages` instead of `prompt`.

### D7 — `InMemoryChatStorage` as production fallback for now

The runtime injection is `new InMemoryChatStorage()` until the Dexie adapter ships. Sessions live only for the page session today — acceptable for the MVP because the user flow is short (single publish event).

**Rationale**: YAGNI. Shipping a `ChatStorage` seam is enough integration surface; we can plug Dexie in a ≈30-line follow-up without touching the store, bridge, or specs.

## Risks / Trade-offs

- **R1 — IndexedDB overflow risk if images pile up**
  Mitigation: `buildChatPayload` keeps only the *last* user message's attachments; `pruneChatStorage` total-size check acts as a final backstop.
- **R2 — Context window overflow on free-tier models (4k–8k)**
  Mitigation: `buildChatPayload({ recentTurns: N })` bounds the history slice. Future UI can expose a "压缩上下文" chip that lowers N.
- **R3 — Cross-platform context pollution**
  Mitigation: `ChatSession.formMode + platform` is enforced at session-creation time. Switching modes in the UI will explicitly `newSession()` rather than reuse.
- **R4 — Existing `AiSidebar.tsx` (1061 lines) still uses local state**
  Mitigation: V0 ships the primitive only. The `applyAiResult → sdk chat` migration is a follow-up spec that swaps local `lastResult`/`isStreaming` for the store.
- **R5 — Pre-existing test failures in `AiPanelToolbar` / `TaskDrawer` / `TaskTableRow` / `NoteForm.test` / `VideoForm.test`**
  Unrelated to this change. The 66 new cases all pass; the previous failures remain on the radar for a separate cleanup.
