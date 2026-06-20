## ADDED Requirements

### Requirement: Bilibili note upload via CLI
The system SHALL provide a `sau bilibili upload-note` subcommand that accepts `--account`, `--images`, `--title`, `--note`, `--tags`, `--schedule`, and `--headless/--headed` flags, consistent with other note upload platforms.

#### Scenario: CLI accepts upload-note with valid args
- **WHEN** user runs `sau bilibili upload-note --account test --images img1.jpg --title "test" --note "content"`
- **THEN** the system creates a BilibiliNoteUploadRequest with parsed image paths and text content

#### Scenario: CLI upload-note requires --images
- **WHEN** user runs `sau bilibili upload-note --account test --title "test"` without `--images`
- **THEN** the system SHALL return an error indicating images are required

### Requirement: Browser-automation note upload
The system SHALL implement Bilibili note upload using browser automation (patchright/playwright), following the pattern established by other note uploaders (DouYinNote, KSNote, XiaoHongShuNote).

#### Scenario: Successful note upload
- **WHEN** user submits valid note data with logged-in cookie
- **THEN** the system navigates to Bilibili post creation page, uploads images, fills title/content, and submits

#### Scenario: Expired cookie handling
- **WHEN** the bilibili cookie is expired or invalid
- **THEN** the system SHALL raise a RuntimeError instructing the user to run `sau bilibili login --account <name>` first

### Requirement: Note schedule support
The system SHALL support scheduled note publishing using the same publish strategy pattern as other note uploaders, with `publish_date` controlling immediate vs timed publishing.

#### Scenario: Immediate publication
- **WHEN** no `--schedule` flag is provided
- **THEN** the note is published immediately after submission

#### Scenario: Scheduled publication
- **WHEN** `--schedule "2026-06-20 10:00"` is provided
- **THEN** the note is scheduled for the specified future time

### Requirement: Web API integration
The system SHALL update `PLATFORM_CONFIG` in `web_runner.py` to set `bilibili.note: True`, adding bilibili to `NOTE_PLATFORMS`. The frontend SHALL show Bilibili as a selectable platform in the note publish form.

#### Scenario: Web API accepts note upload for bilibili
- **WHEN** a POST request is sent to `/api/upload/note` with `platform=bilibili`
- **THEN** the system SHALL accept it (not reject with "平台 bilibili 不支持图文上传")

#### Scenario: Frontend shows Bilibili in note tab
- **WHEN** user opens the note publish form
- **THEN** Bilibili SHALL appear in the platform selector alongside douyin/kuaishou/xiaohongshu
