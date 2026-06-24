## ADDED Requirements

### Requirement: Dead code SHALL be removed from frontend
The following unused components, hooks, and exports SHALL be deleted: `useAccounts` hook, `PLATFORMS_WITH_ICONS` export, `PageTransition` component, standalone `PageLoading.tsx`, `Spinner` component, `message` API in `toast.tsx`, `uploadNote` JSON function.

#### Scenario: No dead imports in production bundle
- **WHEN** the dead code is removed
- **THEN** no existing page or component SHALL break, verified by building the frontend

### Requirement: ProposalsPage SHALL use shared API client
`ProposalsPage` SHALL import the API call from `src/api/client.ts` instead of using raw `axios`.

#### Scenario: ProposalsPage fetches via shared client
- **WHEN** ProposalsPage loads
- **THEN** it SHALL use the shared `api` instance with configured `baseURL`

### Requirement: Double ToastProvider SHALL be fixed
The duplicate `ToastProvider` wrapping in `ThemeProvider` and `App.tsx` SHALL be resolved. Only one `ToastProvider` SHALL wrap the application.

#### Scenario: Toast notifications work correctly
- **WHEN** a user triggers a toast notification
- **THEN** exactly one toast SHALL appear, not duplicated

### Requirement: PublishPage SHALL support drag-and-drop upload
The video and image upload areas SHALL implement `onDragOver`, `onDragLeave`, and `onDrop` handlers for drag-and-drop file selection.

#### Scenario: Drag video file onto upload area
- **WHEN** a user drags a video file onto the upload area
- **THEN** the file SHALL be selected and previewed as if clicked

#### Scenario: Drag invalid file type
- **WHEN** a user drags a non-video file onto the video upload area
- **THEN** the drop SHALL be rejected with a toast error message

### Requirement: Client-side file size validation SHALL be enforced
The frontend SHALL validate file sizes before upload. Maximum video size: 200MB. Maximum image size: 20MB per image.

#### Scenario: Video file exceeds size limit
- **WHEN** a user selects a video file larger than 200MB
- **THEN** a toast error SHALL be shown and the file SHALL NOT be uploaded

#### Scenario: Image file exceeds size limit
- **WHEN** a user selects an image larger than 20MB
- **THEN** a toast error SHALL be shown and the image SHALL NOT be added

### Requirement: React Error Boundary SHALL be implemented
A React Error Boundary component SHALL catch render errors and display a fallback UI with a "Reload" button.

#### Scenario: Page component throws during render
- **WHEN** a page component throws a JavaScript error during render
- **THEN** the Error Boundary SHALL display a user-friendly error message instead of a blank page

#### Scenario: Error boundary provides recovery
- **WHEN** the user clicks the "Reload" button in the error fallback
- **THEN** the page SHALL reload and attempt to render again

### Requirement: 404 route SHALL be implemented
A catch-all route SHALL display a "页面未找到" (Page Not Found) message with a link back to the home page.

#### Scenario: Navigate to unknown path
- **WHEN** a user navigates to `/unknown-path`
- **THEN** a 404 page SHALL be displayed with a link to `/`

### Requirement: LogsPage SHALL use TanStack Query
`LogsPage` SHALL use TanStack Query's `useQuery` with polling instead of manual `setInterval` for log fetching.

#### Scenario: Log fetching uses TanStack Query
- **WHEN** LogsPage is open
- **THEN** log data SHALL be fetched via TanStack Query with 2-second polling interval

#### Scenario: TanStack Query devtools visibility
- **WHEN** TanStack Query devtools are open
- **THEN** log queries SHALL be visible in the devtools panel

### Requirement: Tasks and logs SHALL support pagination
The backend SHALL accept `limit` and `offset` parameters for `/api/tasks` and `/api/logs`. The frontend SHALL implement infinite scroll using `useInfiniteQuery`.

#### Scenario: Load more tasks
- **WHEN** a user scrolls to the bottom of the tasks list
- **THEN** the next page of tasks SHALL be fetched and appended

#### Scenario: Load more logs
- **WHEN** a user scrolls to the bottom of the logs list
- **THEN** the next page of logs SHALL be fetched and appended

### Requirement: Image preview URLs SHALL be revoked
When note image previews are no longer needed (component unmount or image removal), the `URL.createObjectURL` blob URLs SHALL be revoked via `URL.revokeObjectURL()`.

#### Scenario: Remove image from note upload
- **WHEN** a user removes an image from the note upload form
- **THEN** the blob URL for that image SHALL be revoked to free memory

#### Scenario: Navigate away from PublishPage
- **WHEN** a user navigates away from PublishPage with images loaded
- **THEN** all image blob URLs SHALL be revoked on component unmount

### Requirement: Search inputs SHALL be debounced
Keyword search inputs on TasksPage and LogsPage SHALL debounce input by 300ms before filtering.

#### Scenario: Rapid typing in search
- **WHEN** a user types quickly in the task search input
- **THEN** filtering SHALL only trigger 300ms after the last keystroke

### Requirement: videoThumbnail fallback SHALL be correct
Each platform SHALL use its own thumbnail input. Cross-platform thumbnail fallback (e.g., Douyin portrait used for Kuaishou) SHALL NOT occur.

#### Scenario: Different thumbnails for different platforms
- **WHEN** a user uploads to both Douyin and Kuaishou with platform-specific thumbnails
- **THEN** each platform SHALL receive its own thumbnail, not the other's
