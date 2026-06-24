## ADDED Requirements

### Requirement: PublishPage SHALL have a right sidebar for AI module
The PublishPage layout SHALL be split into a main content area and a right sidebar. The sidebar SHALL be 320px wide and contain the AI content generation panel.

#### Scenario: PublishPage layout with sidebar
- **WHEN** a user navigates to `/publish`
- **THEN** the page SHALL display a two-column layout with the upload form on the left and AI panel on the right

#### Scenario: Responsive sidebar behavior
- **WHEN** the viewport width is less than 1200px
- **THEN** the sidebar SHALL collapse into a drawer that can be toggled via a button
