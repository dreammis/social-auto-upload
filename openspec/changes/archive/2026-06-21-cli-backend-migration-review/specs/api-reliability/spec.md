## ADDED Requirements

### Requirement: Scheduled timers SHALL be thread-safe
The `_scheduled_timers` dictionary in `web_runner.py` SHALL be protected by a `threading.Lock`. All read and write operations on this dictionary SHALL acquire the lock.

#### Scenario: Concurrent timer creation and deletion
- **WHEN** two requests simultaneously create and delete scheduled tasks
- **THEN** no `RuntimeError` or data corruption SHALL occur in `_scheduled_timers`

#### Scenario: Watchdog iteration during timer modification
- **WHEN** the watchdog thread iterates `_scheduled_timers` while a timer callback modifies it
- **THEN** the iteration SHALL complete without raising `RuntimeError: dictionary changed size during iteration`

### Requirement: Deleting scheduled tasks SHALL cancel timers
When a task with `scheduled` status is deleted via `POST /api/tasks/delete`, the associated `threading.Timer` SHALL be cancelled before the task record is removed.

#### Scenario: Delete a scheduled task
- **WHEN** a user deletes a task that has status `scheduled`
- **THEN** the system SHALL cancel the timer, remove the task from `_scheduled_timers`, and delete the DB record

#### Scenario: Timer fires after task deletion
- **WHEN** a scheduled task's timer fires after the task was deleted
- **THEN** the timer callback SHALL detect the missing task and exit gracefully without starting an upload

### Requirement: Stale cookies SHALL NOT be reported as valid
The `_quick_check_cookie` function SHALL return `valid: False` with `reason: "stale"` when a cookie file is older than 7 days, instead of `valid: True`.

#### Scenario: Cookie file is 8 days old
- **WHEN** a quick check is performed on a cookie file older than 7 days
- **THEN** the response SHALL be `{valid: false, reason: "stale"}`

#### Scenario: Cookie file is 2 days old and valid JSON
- **WHEN** a quick check is performed on a recent cookie file
- **THEN** the response SHALL be `{valid: true}`

### Requirement: LIKE queries SHALL escape special characters
The `_db_get_logs` function SHALL escape `%` and `_` characters in the `task_id` parameter before using it in LIKE queries.

#### Scenario: Task ID with underscore
- **WHEN** logs are queried with a task_id containing `_`
- **THEN** the LIKE query SHALL match only literal `_`, not any single character

### Requirement: API SHALL have global exception handler
`web_runner.py` SHALL register a Flask error handler for 500 errors that returns a JSON response `{success: false, message: "Internal server error"}` instead of HTML.

#### Scenario: Unhandled exception in endpoint
- **WHEN** an endpoint raises an unhandled exception
- **THEN** the response SHALL be JSON with status 500 and `{success: false, message: "..."}`

#### Scenario: Normal endpoint execution
- **WHEN** an endpoint executes successfully
- **THEN** the global handler SHALL NOT interfere with the response

### Requirement: API SHALL enforce request size limits
`web_runner.py` SHALL set `MAX_CONTENT_LENGTH` to 200MB (200 * 1024 * 1024 bytes).

#### Scenario: Upload exceeds size limit
- **WHEN** a video upload exceeds 200MB
- **THEN** Flask SHALL return 413 (Request Entity Too Large) before reading the full body

#### Scenario: Normal-sized upload
- **WHEN** a video upload is under 200MB
- **THEN** the upload SHALL proceed normally

### Requirement: Upload video endpoint SHALL accept JSON content type
`POST /api/upload/video` SHALL accept both `multipart/form-data` and `application/json` content types, consistent with `/api/upload/note`.

#### Scenario: JSON video upload request
- **WHEN** a video upload is sent as JSON with `file_data` as a data URI
- **THEN** the endpoint SHALL parse the JSON body and process the upload

#### Scenario: Multipart video upload request
- **WHEN** a video upload is sent as multipart form data
- **THEN** the endpoint SHALL process it as it does currently

### Requirement: SSE upload progress endpoint SHALL be available
A new endpoint `GET /api/upload/progress?task_id=<id>` SHALL provide real-time upload progress via Server-Sent Events.

#### Scenario: Upload progress streaming
- **WHEN** a client connects to `/api/upload/progress?task_id=<id>` for a running task
- **THEN** the endpoint SHALL stream log events and status changes in real-time

#### Scenario: Task already completed
- **WHEN** a client connects for a task with terminal status (success/failed/error)
- **THEN** the endpoint SHALL send the final status and close the connection

#### Scenario: Task not found
- **WHEN** a client connects with an invalid task_id
- **THEN** the endpoint SHALL return 404 with `{success: false, message: "Task not found"}`
