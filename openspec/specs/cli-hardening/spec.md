## ADDED Requirements

### Requirement: All upload loops SHALL have max retry limits
Each platform uploader's `while True` loop SHALL have a configurable `max_retries` parameter with a default value. When max retries are reached, the uploader SHALL raise a `TimeoutError` with a descriptive message.

#### Scenario: Xiaohongshu publish button never becomes clickable
- **WHEN** the Xiaohongshu upload loop retries clicking the publish button for `max_retries` times without success
- **THEN** the uploader SHALL raise `TimeoutError("Xiaohongshu publish button not clickable after N attempts")`

#### Scenario: Tencent upload progress never completes
- **WHEN** the Tencent `wait_for_upload_complete` loop runs for `max_retries` iterations without detecting completion
- **THEN** the uploader SHALL raise `TimeoutError("Tencent upload did not complete after N seconds")`

#### Scenario: Normal operation completes within limits
- **WHEN** the publish button becomes clickable within retry limits
- **THEN** the uploader SHALL proceed normally without raising any exception

### Requirement: Shared utility functions SHALL be extracted to common module
The functions `_msg()`, `_emit_qrcode_callback()`, and `_build_login_result()` SHALL be extracted from individual platform uploaders to `uploader/common.py`. All platform uploaders SHALL import from this shared module.

#### Scenario: All platforms use shared _msg function
- **WHEN** any platform uploader calls `_msg()`
- **THEN** it SHALL import from `uploader/common.py` rather than defining a local copy

#### Scenario: Shared module has no platform-specific dependencies
- **WHEN** `uploader/common.py` is imported
- **THEN** it SHALL NOT import from any platform-specific module (douyin, kuaishou, etc.)

### Requirement: dispatch() SHALL use table-driven dispatch
The `dispatch()` function in `sau_cli.py` SHALL use a `PLATFORM_REGISTRY` dictionary mapping `platform -> action -> handler_function` instead of a 300-line if/elif chain.

#### Scenario: Adding a new platform
- **WHEN** a new platform is added to the registry
- **THEN** `dispatch()` SHALL route to the new handler without modifying the dispatch function body

#### Scenario: Unknown platform or action
- **WHEN** an unknown platform or action is provided
- **THEN** `dispatch()` SHALL raise `SystemExit` with a message listing valid platforms and actions

### Requirement: Bilibili uploads SHALL validate cookie content
Bilibili video and note uploads SHALL call `bilibili_cookie_auth()` to validate cookie content before proceeding, not just check file existence.

#### Scenario: Bilibili cookie file exists but is expired
- **WHEN** a Bilibili upload is attempted with an expired cookie file
- **THEN** the upload SHALL fail with a clear "cookie expired" error before launching the browser

#### Scenario: Bilibili cookie is valid
- **WHEN** a Bilibili upload is attempted with a valid cookie
- **THEN** the upload SHALL proceed normally

### Requirement: Bilibili note upload SHALL NOT overwrite cookie format
After Bilibili note upload, the cookie save operation SHALL preserve the biliup-format cookie file. It SHALL NOT overwrite it with Playwright's `storage_state` format.

#### Scenario: Bilibili note then video upload
- **WHEN** a user uploads a Bilibili note and then a video
- **THEN** the video upload SHALL succeed because the cookie file format was preserved

### Requirement: async_retry SHALL catch only expected exceptions
The `@async_retry` decorator SHALL only catch specific exception types (e.g., `RuntimeError`, `IOError`, `TimeoutError`) rather than all `Exception` subclasses. It SHALL NOT catch `TypeError`, `ValueError`, `KeyboardInterrupt`, or `SystemExit`.

#### Scenario: async_retry retries on network error
- **WHEN** a decorated function raises `IOError`
- **THEN** the decorator SHALL retry until timeout

#### Scenario: async_retry does not catch programming errors
- **WHEN** a decorated function raises `TypeError`
- **THEN** the decorator SHALL NOT catch it and let it propagate immediately

### Requirement: TikTok selectors SHALL use stable identifiers
TikTok uploader SHALL NOT use React-generated IDs (e.g., `#:r9:`) as CSS selectors. It SHALL use data attributes, ARIA attributes, or text content selectors instead.

#### Scenario: TikTok success detection across deployments
- **WHEN** the TikTok web app is redeployed with new React component IDs
- **THEN** the success detection SHALL still work because it uses stable selectors

### Requirement: Dead code SHALL be removed
The following unused code SHALL be removed: `xhs_uploader/` directory, `legacy/` directory, `utils/browser_hook.py`, unused `xhs_logger` in `utils/log.py`.

#### Scenario: Codebase has no dead imports
- **WHEN** the dead code is removed
- **THEN** no existing functionality SHALL break, verified by running all upload actions

### Requirement: handle_upload_error SHALL function correctly
Baijiahao's `handle_upload_error()` SHALL remove the dead `return` statement before `print()` and implement proper error handling.

#### Scenario: Upload error is handled
- **WHEN** a Baijiahao upload encounters an error
- **THEN** `handle_upload_error()` SHALL log the error details and re-raise with context
