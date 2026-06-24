## ADDED Requirements

### Requirement: System prompt SHALL vary by target platform
The backend SHALL use platform-specific system prompts when generating content. Each platform SHALL have a tailored prompt that reflects its content style and audience.

#### Scenario: Generate content for Douyin
- **WHEN** the frontend sends a generate request with `platform: "douyin"`
- **THEN** the backend SHALL use a Douyin-optimized system prompt emphasizing short, catchy, trend-aware content

#### Scenario: Generate content for Bilibili
- **WHEN** the frontend sends a generate request with `platform: "bilibili"`
- **THEN** the backend SHALL use a Bilibili-optimized system prompt emphasizing detailed, knowledge-rich content

#### Scenario: Generate content for Xiaohongshu
- **WHEN** the frontend sends a generate request with `platform: "xiaohongshu"`
- **THEN** the backend SHALL use a Xiaohongshu-optimized system prompt emphasizing lifestyle, experience-sharing, and emoji-rich content

#### Scenario: No platform specified
- **WHEN** the frontend sends a generate request without `platform`
- **THEN** the backend SHALL use a generic social media system prompt as fallback
