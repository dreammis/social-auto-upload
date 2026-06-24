## ADDED Requirements

### Requirement: Tasks table index
The system SHALL have an index on the `tasks` table for the `created` column to optimize sorting.

#### Scenario: Index exists
- **WHEN** querying tasks with `ORDER BY created DESC`
- **THEN** the query uses the index instead of full table scan

### Requirement: Unified DB initialization
The system SHALL have a single DB initialization entry point in `web_runner/db.py`.

#### Scenario: Single source of truth
- **WHEN** the application starts
- **THEN** all table creation and index management happens in `db.py`

### Requirement: Remove deprecated createTable.py
The `db/createTable.py` file SHALL be removed or marked as deprecated.

#### Scenario: File removal
- **WHEN** a developer looks for DB initialization
- **THEN** they find it in `web_runner/db.py`, not `db/createTable.py`
