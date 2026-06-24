## ADDED Requirements

### Requirement: Users SHALL optimize individual content parts
After generation, users SHALL be able to optimize title, description, or tags independently.

#### Scenario: Optimize title
- **WHEN** a user clicks "优化标题" on the generated title
- **THEN** a new generation request SHALL be sent with a title-optimization prompt, and only the title field SHALL be updated

#### Scenario: Optimize description
- **WHEN** a user clicks "优化描述" on the generated description
- **THEN** a new generation request SHALL be sent with a description-optimization prompt, and only the description field SHALL be updated

#### Scenario: Optimize tags
- **WHEN** a user clicks "优化标签" on the generated tags
- **THEN** a new generation request SHALL be sent with a tags-optimization prompt, and only the tags field SHALL be updated
