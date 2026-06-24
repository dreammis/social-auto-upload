## MODIFIED Requirements

### Requirement: One-click content generation SHALL populate form fields
When the user clicks the "一键生成" (Generate) button, the system SHALL generate title, description, and tags and auto-fill them into the publish form. The generation SHALL use SSE streaming for real-time feedback.

#### Scenario: Generate content for video upload
- **WHEN** a user clicks "一键生成" on the video upload form
- **THEN** the system SHALL stream the generation and fill the title, description, and tags fields as content arrives

#### Scenario: Generate content for note upload
- **WHEN** a user clicks "一键生成" on the note upload form
- **THEN** the system SHALL stream the generation and fill the title and note content fields as content arrives

### Requirement: Generation status SHALL be displayed
The AI panel SHALL show real-time generation status including streaming text preview, loading, success, and error states.

#### Scenario: Content generation in progress
- **WHEN** a generation request is submitted
- **THEN** the output area SHALL display streaming text in real-time with a typing cursor effect

#### Scenario: Content generation succeeds
- **WHEN** the stream completes
- **THEN** the form fields SHALL be populated and a success toast SHALL appear

#### Scenario: Content generation fails
- **WHEN** the API returns an error
- **THEN** an error toast SHALL appear with the error message and the form fields SHALL remain unchanged
