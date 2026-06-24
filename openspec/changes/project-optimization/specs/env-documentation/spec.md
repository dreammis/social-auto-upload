## ADDED Requirements

### Requirement: Environment example file
The project SHALL include a `.env.example` file at the repository root documenting all configurable environment variables.

#### Scenario: File exists
- **WHEN** a developer clones the repository
- **THEN** they find `.env.example` with all documented variables

#### Scenario: Variable coverage
- **WHEN** the codebase uses `os.environ.get()` or `os.getenv()`
- **THEN** each variable appears in `.env.example` with a description

### Requirement: Variable documentation format
Each variable in `.env.example` SHALL include a comment explaining its purpose, default value, and example.

#### Scenario: Variable format
- **WHEN** a developer reads `.env.example`
- **THEN** each variable has format: `# Description (default: value)` followed by `# VAR_NAME=example_value`

### Requirement: Required vs optional distinction
The documentation SHALL clearly distinguish required variables from optional ones.

#### Scenario: Required variables
- **WHEN** a variable has no default and is needed for core functionality
- **THEN** it is marked with `# REQUIRED` in the comment

#### Scenario: Optional variables
- **WHEN** a variable has a sensible default
- **THEN** the default value is documented
