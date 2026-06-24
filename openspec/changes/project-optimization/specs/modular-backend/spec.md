## ADDED Requirements

### Requirement: Flask app factory
The system SHALL provide a `create_app()` function that initializes and returns a configured Flask application instance.

#### Scenario: App creation
- **WHEN** `create_app()` is called
- **THEN** it returns a Flask app with all blueprints registered, CORS configured, and DB initialized

#### Scenario: Testing isolation
- **WHEN** `create_app()` is called with test config
- **THEN** it creates an isolated app instance with separate DB path

### Requirement: Route blueprints
The system SHALL organize API routes into Flask Blueprints by functional domain.

#### Scenario: Blueprint registration
- **WHEN** the app starts
- **THEN** the following blueprints are registered: `accounts` (账号管理), `upload` (上传), `tasks` (任务), `ai` (AI 生成), `account_groups` (分组)

#### Scenario: URL prefix preservation
- **WHEN** a client calls any existing API endpoint
- **THEN** the URL path remains unchanged (e.g., `/api/accounts` not `/api/v1/accounts`)

### Requirement: Module structure
The web_runner package SHALL contain the following modules: `__init__.py` (app factory), `routes/` (blueprints), `db.py` (database), `scheduler.py` (task scheduling), `ai_worker.py` (AI queue).

#### Scenario: Import structure
- **WHEN** a developer imports `web_runner`
- **THEN** the import chain is clean with no circular dependencies

### Requirement: Backward compatibility
The system SHALL maintain 100% API backward compatibility during and after the refactoring.

#### Scenario: Existing API calls
- **WHEN** the frontend or CLI calls any existing endpoint
- **THEN** the response format, status codes, and behavior remain identical
