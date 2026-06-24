## ADDED Requirements

### Requirement: Generation history SHALL be stored locally
The frontend SHALL store generation results in localStorage, indexed by timestamp and platform.

#### Scenario: Save generation result
- **WHEN** a generation request succeeds
- **THEN** the result SHALL be saved to localStorage with timestamp, platform, model, prompt, and generated content

#### Scenario: History limit
- **WHEN** the history exceeds 50 entries
- **THEN** the oldest entries SHALL be automatically removed

### Requirement: History panel SHALL display past generations
The AI sidebar SHALL include a collapsible history panel showing past generation results.

#### Scenario: View history
- **WHEN** a user clicks the history tab
- **THEN** a list of past generations SHALL be displayed with timestamp and platform badges

#### Scenario: Apply historical result
- **WHEN** a user clicks a history entry
- **THEN** its content SHALL be applied to the current form fields

#### Scenario: Delete history entry
- **WHEN** a user clicks the delete button on a history entry
- **THEN** the entry SHALL be removed from localStorage
