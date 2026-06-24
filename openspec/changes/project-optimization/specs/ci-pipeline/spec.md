## ADDED Requirements

### Requirement: GitHub Actions workflow
The system SHALL have a `.github/workflows/ci.yml` file that runs on push and pull request events.

#### Scenario: Trigger on push
- **WHEN** code is pushed to `main` branch
- **THEN** the CI workflow runs automatically

#### Scenario: Trigger on PR
- **WHEN** a pull request is opened against `main`
- **THEN** the CI workflow runs and reports status

### Requirement: Python lint check
The CI pipeline SHALL run Python linting using ruff.

#### Scenario: Lint passes
- **WHEN** Python code follows project style rules
- **THEN** the lint check passes with exit code 0

#### Scenario: Lint fails
- **WHEN** Python code has style violations
- **THEN** the lint check fails with descriptive error messages

### Requirement: Frontend build check
The CI pipeline SHALL verify the frontend builds successfully.

#### Scenario: Build succeeds
- **WHEN** `npm run build` completes without errors
- **THEN** the build check passes

#### Scenario: Build fails
- **WHEN** TypeScript errors or build errors occur
- **THEN** the build check fails with error details

### Requirement: Test execution
The CI pipeline SHALL run the Python test suite.

#### Scenario: Tests pass
- **WHEN** all tests pass
- **THEN** the test check passes

#### Scenario: Tests fail
- **WHEN** any test fails
- **THEN** the test check fails with failure details
