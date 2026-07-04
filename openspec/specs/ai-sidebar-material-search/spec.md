# ai-sidebar-material-search Specification

## Purpose

Enable the AI assistant sidebar at `/app/publish` to discover image material (auto-recommended by current title or manually searched) and to fetch videos from share URLs — completing the workflow without leaving the publish page.

## Requirements

### Requirement: Keyword image search aggregates Pexels + Pixabay

When the user submits a keyword via the MaterialSection image panel, the backend SHALL call both Pexels (`https://api.pexels.com/v1/search`) and Pixabay (`https://pixabay.com/api/`) concurrently, merge the results into a normalized schema, deduplicate within the same source, and return up to `count` images (default 9).

#### Scenario: Both sources respond successfully

- **WHEN** the user issues `POST /api/ai/images/search { query: "周末咖啡", count: 9 }` AND `PEXELS_API_KEY` and `PIXABAY_API_KEY` are both set
- **THEN** the backend SHALL call both APIs within 8 seconds timeouts (each)
- **AND** merge results into [`NormalizedImage`], capped at 9 entries
- **AND** dedupe within Pexels by photo id, within Pixabay by hit id
- **AND** return `{success: true, data: [...], debug: {pexels_count, pixabay_count, merged_count}}`

#### Scenario: One source fails, the other succeeds

- **WHEN** Pexels returns 5xx OR raises timeout
- **THEN** the backend SHALL still return Pixabay results in `data`
- **AND** include the failing source's error in `debug.errors`
- **AND** `merged_count` reflects only the successful source(s)

#### Scenario: Neither API key is configured

- **WHEN** `PEXELS_API_KEY` and `PIXABAY_API_KEY` are both unset or empty
- **THEN** the backend SHALL return HTTP 503 with `{success: false, message: "未配置图片搜索 API key。请在 .env 设置 PEXELS_API_KEY 或 PIXABAY_API_KEY 后重启 run.py。", code: "IMAGE_SOURCE_NOT_CONFIGURED"}`
- **AND** the response SHALL NOT fall back to DuckDuckGo image search (which is opt-out by design — quality is too low for publishing)

### Requirement: Normalized image schema

The backend SHALL normalize Pexels photos and Pixabay hits into a single schema before returning.

#### Scenario: Pexels photo normalization

- **WHEN** a Pexels photo is received
- **THEN** the normalized object SHALL include `source="pexels"`, `source_id=photo.id`, `thumb=src.medium`, `preview=src.large2x`, `full=src.original`, `photographer`, `pageUrl=url`, `alt`
- **AND** the response id SHALL be `"pexels:<photo.id>"`

#### Scenario: Pixabay hit normalization

- **WHEN** a Pixabay hit is received
- **THEN** the normalized object SHALL include `source="pixabay"`, `source_id=hit.id`, `thumb=webformatURL`, `preview=largeImageURL`, `full=hit.fullHDURL OR largeImageURL`, `user` mapped to `photographer`, `pageUrl=hit.pageURL`, `alt=hit.tags`
- **AND** the response id SHALL be `"pixabay:<hit.id>"`

### Requirement: Auto-recommend images by form title

When the user has filled the title field (in VideoForm's local state, exposed via `formRef.getFormSnapshot()`) and stays idle for at least 1.5 seconds, the sidebar SHALL trigger a non-blocking image recommendation request.

#### Scenario: Title changes from empty to non-empty

- **WHEN** the previous `formRef.getFormSnapshot().title` is empty AND the next snapshot is non-empty AND the recommendation count is below 3 (session-level cap)
- **THEN** the sidebar SHALL fire `POST /api/ai/recommend-images {topic: <title>}`
- **AND** results SHALL be added to a separate `recommendResults[]` slot distinct from manual `imageResults[]`

#### Scenario: Title stays the same across polls

- **WHEN** two consecutive polls read the same title
- **THEN** the sidebar SHALL NOT fire a new recommendation

#### Scenario: Session recommendation cap

- **WHEN** the user has already received 3 auto-recommendations in the current AiAssistantPanel lifetime
- **THEN** the sidebar SHALL NOT fire a fourth, even if the title changes again
- **AND** the cap SHALL reset on full panel remount (which is what happens after the publish page is destroyed + recreated)

#### Scenario: User manually searches images after auto-recommend

- **WHEN** the user fires a manual `searchImages(query)`
- **THEN** the manual results SHALL REPLACE `imageResults[]`
- **AND** `recommendResults[]` SHALL remain visible (toggled separate, NOT cleared) so the user can still apply a recommended image

### Requirement: FormHandle.applyMedia contract

`FormHandle` SHALL expose an `applyMedia` method for MediaSection to call when the user picks an image or finishes a URL fetch, distinct from the existing `applyAiResult`.

#### Scenario: VideoForm.applyMedia(thumbnail)

- **WHEN** `applyMedia({thumbnail: "https://..."})` is called on a VideoForm ref
- **THEN** the form SHALL update its `thumbnail` state to the URL
- **AND** SHALL NOT touch the `file` slot (videos are linked separately)
- **AND** a success toast SHALL surface

#### Scenario: NoteForm.applyMedia(images)

- **WHEN** `applyMedia({images: [File, File]})` is called on a NoteForm ref
- **THEN** the form SHALL APPEND the new files to its `files.images[]` array (NOT replace)
- **AND** SHALL NOT touch its own thumbnail state (NoteForm's thumbnail slot is owned by useAuxiliary)

#### Scenario: applyMedia on a form that has no media slot

- **WHEN** `applyMedia` is called on a ref whose form does not support the requested key (e.g. `applyMedia({images})` on VideoForm)
- **THEN** the helper SHALL return `{applied: false, reason: 'no-media-slot'}`
- **AND** the caller SHALL surface a toast: "当前表单不支持此类型素材"

### Requirement: Image binary fetch proxy

To avoid browser CORS restrictions against Pexels / Pixabay binary hosts, the backend SHALL expose a proxy endpoint that streams the image bytes back as the original content type.

#### Scenario: Fetch a public image URL

- **WHEN** `GET /api/ai/images/fetch?url=<public-image-url>` is called AND the URL passes `_is_public_url` AND `_resolve_is_public`
- **THEN** the backend SHALL `requests.get(url, stream=True)` and pipe the bytes back to the client with the upstream `Content-Type` and a 24-hour `Cache-Control`
- **AND** the response SHALL abort if cumulative bytes exceed 10 MB (图文场景合理上限)

#### Scenario: SSRF block on URL with literal private IP

- **WHEN** the URL host is a literal IPv4 private IP (e.g. `10.0.0.1`) OR is in the loopback range
- **THEN** the backend SHALL return HTTP 400 with `{success: false, message: "url rejected (private/loopback)"}`
- **AND** no request is made

#### Scenario: SSRF block on DNS rebinding target

- **WHEN** the URL hostname resolves to a private / loopback / link-local IP at request time
- **THEN** the backend SHALL return HTTP 400 with `{success: false, message: "url rejected (dns private/loopback)"}`
- **AND** no request is made

### Requirement: URL one-click fetch routes to inbox download

When the user pastes a video share URL (e.g. `https://v.douyin.com/...`) into the link panel, the backend SHALL reuse the existing `/api/inbox/download` pipeline (yt-dlp + patchright + cookies) to retrieve the file.

#### Scenario: Link fetch resolves to a downloaded video

- **WHEN** the user submits a valid share URL through `AddUrlForm`
- **THEN** the backend SHALL invoke `/api/inbox/download` end-to-end (including SSRF gates from inbox.py) and return the same `{success, filename, engine}` shape
- **AND** the sidebar SHALL call `safeApplyMedia(formRef, {file: <blob-file>})` once the download lands — VideoForm's `file` slot SHALL be replaced (not appended, since this is the main media)

#### Scenario: Link fetch fails (cookie-stale or unsupported URL)

- **WHEN** `/api/inbox/download` returns `{success: false}`
- **THEN** the sidebar SHALL show the inbox error message verbatim (capped 500 chars per inbox convention)
- **AND** form state SHALL NOT be mutated

### Requirement: Soft rate limiting on image endpoints

To guard against accidental client bursts that would burn through Pexels's 200/hour and Pixabay's 5000/hour free tiers, the backend SHALL apply a soft rate limit per authenticated user on `/api/ai/images/search` and `/api/ai/recommend-images`.

#### Scenario: User exceeds 30 calls per minute

- **WHEN** the user has called either endpoint ≥ 30 times in the last 60 seconds
- **THEN** the backend SHALL return HTTP 429 with `{success: false, message: "image search rate-limited; retry after 60s", retry_after_sec: 60}`
- **AND** the user's counter SHALL decay on a sliding window

### Requirement: PublishAiSidebar layout preserves chat viewport

The MaterialSection SHALL be inserted as a flex-shrink-0 sibling between the chat viewport and the composer without breaking chat scroll behavior.

#### Scenario: Material section collapsed

- **WHEN** both Accordion items are collapsed (`value=""` set on each)
- **THEN** the height of the Material sections SHALL be 0px (only disclosure triggers visible)
- **AND** the chat viewport SHALL occupy the full flex-1 height between header and composer

#### Scenario: Material section expanded (image panel open)

- **WHEN** the image panel Accordion Item is open
- **THEN** the panel SHALL occupy ≤ 380px of fixed height
- **AND** the chat viewport SHALL retain at least 240px of `min-h-[240px]`
- **AND** the composer SHALL remain anchored to the bottom
