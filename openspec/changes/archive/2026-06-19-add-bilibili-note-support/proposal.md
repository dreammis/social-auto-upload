## Why

Bilibili is the only major video platform in this project that lacks note (图文) upload support. Douyin, kuaishou, and xiaohongshu all support `upload-note`. Adding Bilibili note support completes the picture for content creators who publish image-based posts alongside videos.

## What Changes

- Add `bilibili upload-note` subcommand in the CLI (`sau_cli.py`)
- Add an uploader module for Bilibili notes (browser-automation based, or extend biliup if supported)
- Add `bilibili` to `NOTE_PLATFORMS` in `web_runner.py`
- Enable note tab for Bilibili in the frontend PublishPage (`NOTE_PLATFORMS` in `api/client.ts`)
- Update `PLATFORM_CONFIG` to set `bilibili.note: True`

## Capabilities

### New Capabilities

- `bilibili-note-upload`: Bilibili image-text note upload via browser automation, supporting `--images`, `--title`, `--note`, `--tags`, `--schedule`, `--headless/--headed`

### Modified Capabilities

- (none — existing video upload behavior is unchanged)

## Impact

- **CLI** (`sau_cli.py`): Add `bilibili upload-note` parser in `build_parser()`, add dispatch handler, add `BilibiliNoteUploadRequest` dataclass and `upload_bilibili_note()` function
- **Uploader** (`uploader/bilibili_uploader/`): Add `note.py` (or extend `main.py`) with browser-automation note upload class, similar to douyin/xiaohongshu note uploaders
- **Web API** (`web_runner.py`): Update `PLATFORM_CONFIG` — set `bilibili.note: True`; update `NOTE_PLATFORMS` set accordingly
- **Frontend** (`sau_web/frontend/`): Already uses `NOTE_PLATFORMS` from `api/client.ts` for the note publish form — add `bilibili` to that list
- **No new dependencies** — reuses existing `patchright`/browser setup
