## 1. Backend Flask Shell

- [x] 1.1 Create `web_runner.py` Flask app factory with CORS + task/log endpoints
- [x] 1.2 Add `web` optional dependency group in `pyproject.toml`: Flask + flask-cors (already present)
- [x] 1.3 Implement `/api/accounts` endpoints: list + login triggering `sau_cli.dispatch` via asyncio/subprocess
- [x] 1.4 Implement `/api/upload/video` and `/api/upload/note` endpoints calling into `sau_cli` for supported platforms
- [x] 1.5 Add basic `/` route that serves built frontend asset or index.html in production
- [x] 1.6 Add `/api/logs` endpoint returning in-memory ring buffer
- [x] 1.7 Add `/api/tasks` endpoint to list current/latest task status and progress

## 2. Frontend React App

- [x] 2.1 Scaffold React + Vite + TS project under `sau_web/frontend`
- [x] 2.2 Add a top-level layout: responsive sidebar (desktop) / bottom Tab (mobile)
- [x] 2.3 Implement `Accounts` page: table of saved accounts + login button per platform
- [x] 2.4 Implement `Publish` page: platform selector, upload-video form, upload-note form, schedule input, submit actions
- [x] 2.5 Implement floating log panel: draggable, resizable, auto-scroll, filter, minimize/expand
- [x] 2.6 Implement `Tasks` page: show current/latest task name, status badge, progress indicator
- [x] 2.7 Add environment config for API base URL and proxy to Flask backend
- [x] 2.8 Make full UI Chinese (zh-CN) with consistent terminology

## 3. New Features

- [x] 3.1 Add task state tracking: backend records running/success/failed tasks with timestamps
- [x] 3.2 Add log streaming: capture subprocess stdout/stderr into a bounded ring buffer; frontend fetches tail
- [x] 3.3 Add platform filter in Accounts and Publish pages (douyin/kuaishou/xiaohongshu/bilibili)
- [x] 3.4 Add account deletion action in Accounts page

## 4. Integration & Documentation

- [x] 4.1 Add backend run command docs and `python web_runner.py` startup example
- [x] 4.2 Add frontend install/build/dev docs (npm install, npm run dev, npm run build)
- [x] 4.3 Add README section mapping `uv pip install -e ".[web]"` and starting the shell
- [x] 4.4 Verify end-to-end: open frontend, login one platform, submit a test video upload, view logs

## 5. Testing

- [x] 5.1 Add pytest cases for `/api/accounts`, `/api/logs`, `/api/tasks`
- [x] 5.2 Add frontend smoke test: Accounts page loads, Submit upload returns task id from API
- [x] 5.3 Add README test commands and expected outputs
- [x] 5.4 Validate log output shows proper upload success/error messages
