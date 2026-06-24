## ADDED Requirements

### Requirement: Users SHALL create custom prompt templates
The AI sidebar SHALL allow users to save, edit, and delete custom prompt templates.

#### Scenario: Save current prompt as template
- **WHEN** a user clicks "保存为模板" after entering a custom instruction
- **THEN** a dialog SHALL appear to name and save the template to localStorage

#### Scenario: Apply template
- **WHEN** a user selects a template from the template dropdown
- **THEN** the custom instruction field SHALL be populated with the template content

#### Scenario: Delete template
- **WHEN** a user clicks delete on a template
- **THEN** the template SHALL be removed from localStorage

### Requirement: Built-in templates SHALL be provided
The system SHALL include pre-built templates for common content types.

#### Scenario: Use built-in template
- **WHEN** a user opens the template selector
- **THEN** built-in templates like "美食探店", "产品测评", "旅行攻略" SHALL be available alongside custom templates
