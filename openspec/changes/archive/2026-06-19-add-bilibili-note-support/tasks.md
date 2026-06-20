## 1. Uploader Module (Python)

- [x] 1.1 Create `uploader/bilibili_uploader/note.py` with `BilibiliNote` class extending base pattern (cookie load, browser launch, headless support)
- [x] 1.2 Implement `validate_upload_args()` — validate images exist, image count ≤20, title non-empty
- [x] 1.3 Implement `upload_note_content(page)` — navigate to Bilibili 图文发布页, upload images, fill title/content/tags, submit
- [x] 1.4 Implement schedule handling via `publish_strategy` parameter (immediate vs timed)
- [x] 1.5 Add `BilibiliNoteUploadRequest` dataclass to `sau_cli.py` (account_name, image_paths, note, title, tags, publish_date)
- [x] 1.6 Add `upload_bilibili_note()` async function in `sau_cli.py` dispatch section

## 2. CLI Parser (sau_cli.py)

- [x] 2.1 Add `bilibili upload-note` subparser in `build_parser()` with required args: `--account`, `--images` (nargs="+"), `--title`; optional: `--note`, `--tags`, `--schedule`, `--headless/--headed`
- [x] 2.2 Add dispatch handler for `bilibili upload-note` in `dispatch()` function
- [x] 2.3 Add `upload-note` to the `for action_name in ("login", "check")` action list (currently only login/check exist)

## 3. Web API (web_runner.py)

- [x] 3.1 Update `PLATFORM_CONFIG["bilibili"]` — set `"note": True`
- [x] 3.2 Add `"bilibili"` to `NOTE_PLATFORMS` set
- [x] 3.3 Verify `/api/upload/note` endpoint now accepts `platform=bilibili` requests

## 4. Frontend (sau_web/frontend)

- [x] 4.1 Add `{ label: "Bilibili", value: "bilibili", color: "blue" }` to `NOTE_PLATFORMS` array in `api/client.ts`
- [x] 4.2 Verify PublishPage note form shows Bilibili in platform selector
