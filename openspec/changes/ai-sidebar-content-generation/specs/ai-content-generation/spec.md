## ADDED Requirements

### Requirement: AI content generation module SHALL be available in PublishPage sidebar
The PublishPage SHALL display an AI content generation panel in the right sidebar when the user is composing a video or note upload.

#### Scenario: AI panel visible on PublishPage
- **WHEN** a user navigates to `/publish`
- **THEN** the right sidebar SHALL display an AI content generation panel with model selection and generate button

### Requirement: OpenRoute API integration SHALL be proxied through backend
The system SHALL provide a `/api/ai/generate` endpoint that proxies requests to OpenRoute API, keeping the API key secure on the server side.

#### Scenario: Frontend requests content generation
- **WHEN** the frontend sends a POST request to `/api/ai/generate` with `{ prompt, model }`
- **THEN** the backend SHALL forward the request to OpenRoute API using the configured API key and return the generated content

#### Scenario: API key not configured
- **WHEN** the OpenRoute API key is not set in environment variables
- **THEN** the endpoint SHALL return `{ success: false, message: "AI service not configured" }`

### Requirement: Model selection dropdown SHALL be provided
The AI panel SHALL display a dropdown menu allowing users to select from available AI models.

#### Scenario: Load available models
- **WHEN** the AI panel mounts
- **THEN** it SHALL fetch the model list from `/api/ai/models` and populate the dropdown

#### Scenario: Select a model
- **WHEN** a user selects a model from the dropdown
- **THEN** the selected model SHALL be stored in state and used for subsequent generation requests

### Requirement: One-click content generation SHALL populate form fields
When the user clicks the "一键生成" (Generate) button, the system SHALL generate title, description, and tags and auto-fill them into the publish form.

#### Scenario: Generate content for video upload
- **WHEN** a user clicks "一键生成" on the video upload form
- **THEN** the system SHALL generate and fill the title, description, and tags fields

#### Scenario: Generate content for note upload
- **WHEN** a user clicks "一键生成" on the note upload form
- **THEN** the system SHALL generate and fill the title and note content fields

### Requirement: Request queue SHALL manage API call concurrency
The backend SHALL implement a request queue with rate limiting to support unlimited API calls without hitting OpenRoute rate limits.

#### Scenario: Multiple concurrent generation requests
- **WHEN** multiple users request content generation simultaneously
- **THEN** the backend SHALL queue requests and process them according to the rate limit (e.g., 20 requests per minute)

#### Scenario: Queue position feedback
- **WHEN** a user's request is queued
- **THEN** the frontend SHALL display the queue position or estimated wait time

### Requirement: Generation status SHALL be displayed
The AI panel SHALL show real-time generation status including loading, success, and error states.

#### Scenario: Content generation in progress
- **WHEN** a generation request is submitted
- **THEN** the generate button SHALL show a loading spinner and "生成中..." text

#### Scenario: Content generation succeeds
- **WHEN** the API returns generated content
- **THEN** the form fields SHALL be populated and a success toast SHALL appear

#### Scenario: Content generation fails
- **WHEN** the API returns an error
- **THEN** an error toast SHALL appear with the error message and the form fields SHALL remain unchanged

### Requirement: Re-generate functionality SHALL be available
Users SHALL be able to click "重新生成" to get new content, overwriting previously generated content.

#### Scenario: Re-generate after successful generation
- **WHEN** a user clicks "重新生成" after a successful generation
- **THEN** a new generation request SHALL be sent and the form fields SHALL be updated with new content
