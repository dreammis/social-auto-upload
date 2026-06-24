## ADDED Requirements

### Requirement: Route-level code splitting
The frontend SHALL use `React.lazy` to load page components on demand.

#### Scenario: Initial load
- **WHEN** a user visits the app for the first time
- **THEN** only the AccountsPage chunk is loaded (not PublishPage, TasksPage, etc.)

#### Scenario: Route navigation
- **WHEN** a user navigates to `/publish`
- **THEN** the PublishPage chunk is loaded dynamically

### Requirement: Loading states
The frontend SHALL display a loading skeleton while lazy-loaded chunks are being fetched.

#### Scenario: Chunk loading
- **WHEN** a page chunk is loading
- **THEN** a skeleton placeholder is shown instead of blank screen

### Requirement: Error boundary
The frontend SHALL have an ErrorBoundary component that catches React rendering errors.

#### Scenario: JS runtime error
- **WHEN** a component throws during render
- **THEN** the ErrorBoundary shows a user-friendly error message instead of white screen

### Requirement: Dynamic imports for non-core libraries
The frontend SHALL dynamically import heavy non-core libraries (tour, confetti).

#### Scenario: Tour library
- **WHEN** the user triggers the guided tour
- **THEN** the tour library is loaded on demand

#### Scenario: Confetti effect
- **WHEN** a confetti animation is triggered
- **THEN** the confetti library is loaded on demand
