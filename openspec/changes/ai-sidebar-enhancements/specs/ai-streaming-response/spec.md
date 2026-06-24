## ADDED Requirements

### Requirement: Generate endpoint SHALL support SSE streaming
The backend SHALL provide `/api/ai/generate/stream` that returns Server-Sent Events for real-time content delivery.

#### Scenario: Stream generation response
- **WHEN** the frontend connects to `/api/ai/generate/stream` with a POST body
- **THEN** the backend SHALL proxy the OpenRoute streaming response as SSE events, sending text chunks as they arrive

#### Scenario: Stream completion
- **WHEN** the generation is complete
- **THEN** the backend SHALL send a `done` event with the full content

#### Scenario: Stream error
- **WHEN** an error occurs during streaming
- **THEN** the backend SHALL send an `error` event with the error message

### Requirement: Frontend SHALL display streaming text in real-time
The AI sidebar SHALL show generated text appearing character by character during streaming.

#### Scenario: Real-time text display
- **WHEN** a streaming generation is in progress
- **THEN** the generate button SHALL show "生成中..." and the output area SHALL display text as it arrives

#### Scenario: Streaming completes
- **WHEN** the stream sends the `done` event
- **THEN** the final content SHALL be parsed and applied to form fields
