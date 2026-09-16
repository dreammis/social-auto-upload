# Kuaishou image-note submission safety

KSNote previously continued after 60 incomplete upload checks, and retried the
publish/confirmation sequence when the management-page wait failed. Both bugs
were reproduced offline against upstream `0012d2c355f88f683cc38dde2a2db209e14091bc`:
completed upload was absent yet publish was clicked once; a navigation timeout
produced two publish clicks.

## Evidence used by this change

Anonymous GETs of Kuaishou's public creator frontend on 2026-09-16 exposed:

- [API bundle](https://p66-plat.wskwai.com/kos/nlav11104/onvideo-cp/static/js/index-UlI5CibS.js)
  SHA-256 `a90a901beb5dabff2cf08d3bcab8a73a3873cdc8a9f5b75d0fded6888adbdaf5`.
- [Atlas implementation](https://p66-plat.wskwai.com/kos/nlav11104/onvideo-cp/static/js/index-Dr_99Ic3.js)
  SHA-256 `bcb28f6176623b45df8788893b34790f03dc9683fda24ec42c3c790441b3ebbb`.

The JSON POST contract (all paths start `/rest/cp/works/atlas/pc/`):

| Stage | Request/response evidence |
| --- | --- |
| `upload/pre` | Request `pictureCount`; response `result:1`, `data.fileId`, `data.atlasId`, ordered `data.uploadInfo[].blobKey` matching the image count. |
| `upload/single/finish` | Request same `fileId`, `atlasId`, one `blobKey`; `result:1` and `data.url[0].url` are consumed as that image's completion. |
| `upload/finish` | Request same IDs and full ordered `blobKey` array; frontend awaits `result:1` before submitting. |
| `publish/submit` | Request retains same IDs; frontend treats `result:1` as accepted, `result:-1` as refusal. |

The frontend sets its overall upload state to DONE even for a partial result.
Therefore neither DONE, absence of upload text, nor management navigation proves
all input images completed. The observer starts before file assignment. It
requires all unique per-image receipts for the single expected batch. At the
actual publish request, a route guard additionally checks the accepted ordered
final list and matching IDs; it allows at most one request through. It does not
construct, replay, or directly call the platform API.

This is a public-client contract, not a captured authenticated transaction.
Mocks exercise that observed contract; they do not demonstrate actual platform
acceptance. A later frontend/API change must fail closed rather than be guessed.
No evidence supports claiming a returned public post ID; `atlasId` is not
presented as one. An accepted response does **not** establish public visibility.

## Results and compatibility

`kuaishou upload-note` emits a final JSON line with schema
`sau.kuaishou.note.v1`. Existing diagnostic logs may precede it; consumers can
parse JSON objects by schema, without matching human log wording.

| Status | Exit | Meaning |
| --- | --- | --- |
| `accepted` | 0 | Correlated publish response accepted the batch; `public_visibility` remains `unverified`. |
| `not_submitted` | 1 | Validation/preparation failed before the publish-click boundary. |
| `submission_unknown` | 2 | Click/submit may have happened but no trustworthy outcome was received. Do not retry automatically. |
| `rejected` | 3 | Correlated business response refused submission. No automatic retry. |

The request object and all existing CLI arguments remain supported. The internal
`upload_kuaishou_note()` helper now returns the outcome dict rather than an account
path; repository callers were inspected. KSNote.main() also returns that outcome.
Other platforms and KSVideo keep their prior behavior.

Title still follows existing validation/defaulting; this patch does not invent
separate title filling (the old note editor path did not fill it separately).
Body and `tags[:3]` typing remain unchanged; this is not proof of final title/tag
presentation on the platform. Scheduled publishing retains its existing strategy.

Upload evidence has a 120-second deadline. A single publish/optional confirmation
sequence has a bounded result wait. Click exceptions never restart it. Known
acceptance survives cookie-save and resource-close errors; each close is attempted
independently. No debug screenshot is needed to decide submission success.

## Validation and limits

Run the focused tests using an isolated environment configured from
`conf.example.py` (no account needed):

```sh
python -m pytest tests/test_kuaishou_note_safety.py tests/test_sau_browser_cli.py tests/test_kuaishou_publish_dialog.py
```

The existing dialog tests launch a disposable unauthenticated headless Chrome.
No tests use production profiles, real cookies, business images, login, platform
upload or publish. Offline results cover upload/identity/count failures,
fast/delayed/refused/unknown responses, optional confirmation, non-replay, CLI
exit semantics, and cleanup failures. They do not replace a separately authorized
real-page and controlled submission acceptance. This change does not implement
cross-process/cross-day idempotency or claim server-side exactly-once delivery.

Recorded validation for this candidate:

- 42 non-browser note safety/CLI tests passed in independent re-review.
- 1 real Patchright localhost-only transport test passed; its origin check is
  deliberately redirected to localhost while the observer/guard run unchanged.
- 2 existing publish-confirmation browser tests passed.
- Existing `test_sau_browser_cli.py`: 14 passed, 3 failed. The same 3 failures
  reproduce when executing the unmodified upstream CLI source: stale test
  Namespaces lack `notef`/`collection` in Douyin/Tencent dispatch tests. They are
  unrelated to this patch and were not repaired here.
- AST comparison against the baseline confirms KSVideo, KSBaseUploader, the
  shared confirmation/editor helpers, and the original note preparation
  statements are unchanged.

Independent review identified a driver-exit exception that could replace an
unknown/refused submission with a generic pre-submit error. The original error
is now preserved and all four outcomes have driver-cleanup regression coverage.
Re-review passed without remaining P1/P2 findings. Real platform acceptance is
still explicitly outside this offline validation.
