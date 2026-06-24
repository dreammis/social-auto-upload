"""Pytest conftest — prevent web_runner's module-level DB init from crashing tests."""

from unittest.mock import MagicMock, patch

# patch sqlite3.connect BEFORE web_runner is ever imported, so its
# module-level _init_db() and _migrate_legacy_key_to_pool() don't fail.
_mock_conn = MagicMock()
_mock_conn.__enter__.return_value = _mock_conn
# Return a safe row mock that supports .fetchone() and [0] indexing
_mock_row = MagicMock()
_mock_conn.execute.return_value.fetchone.return_value = _mock_row

_patch_sqlite = patch("sqlite3.connect", return_value=_mock_conn)
_patch_sqlite.start()
