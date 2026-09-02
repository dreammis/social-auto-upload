import contextlib
import importlib
import io
import os
import sqlite3
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class WebDependencyContractTests(unittest.TestCase):
    def test_web_extra_declares_all_legacy_backend_runtime_dependencies(self):
        with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as file:
            configuration = tomllib.load(file)

        web_dependencies = configuration["project"]["optional-dependencies"]["web"]

        self.assertIn("playwright==1.52.0", web_dependencies)
        self.assertIn("xhs==0.2.13", web_dependencies)


class DatabaseBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._import_directory = tempfile.TemporaryDirectory()
        previous_directory = Path.cwd()
        try:
            os.chdir(cls._import_directory.name)
            sys.modules.pop("db.createTable", None)
            cls.create_table = importlib.import_module("db.createTable")
        finally:
            os.chdir(previous_directory)

    @classmethod
    def tearDownClass(cls):
        cls._import_directory.cleanup()

    def test_initializer_uses_an_explicit_path_and_preserves_existing_rows(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "runtime.db"
            self.create_table.initialize_database(database_path)

            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    "INSERT INTO user_info (type, filePath, userName) VALUES (?, ?, ?)",
                    (1, "fixture.json", "synthetic-account"),
                )
                connection.commit()

            self.create_table.initialize_database(database_path)

            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                account_count = connection.execute(
                    "SELECT COUNT(*) FROM user_info"
                ).fetchone()[0]

        self.assertTrue({"user_info", "file_records"}.issubset(tables))
        self.assertEqual(account_count, 1)

    def test_default_database_path_is_independent_of_current_working_directory(self):
        self.assertEqual(
            self.create_table.DEFAULT_DATABASE_PATH,
            REPOSITORY_ROOT / "db" / "database.db",
        )


class WebReadApiPrivacyTests(unittest.TestCase):
    def test_read_endpoints_use_test_database_without_printing_account_rows(self):
        marker = "synthetic-account-must-not-be-logged"
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "runtime.db"
            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE user_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type INTEGER NOT NULL,
                        filePath TEXT NOT NULL,
                        userName TEXT NOT NULL,
                        status INTEGER DEFAULT 0
                    );
                    CREATE TABLE file_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        filesize REAL,
                        upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        file_path TEXT
                    );
                    """
                )
                connection.execute(
                    "INSERT INTO user_info (type, filePath, userName) VALUES (?, ?, ?)",
                    (1, "fixture.json", marker),
                )
                connection.commit()

            sys.modules.pop("sau_backend", None)
            with patch.dict(os.environ, {"SAU_DATABASE_PATH": str(database_path)}):
                backend = importlib.import_module("sau_backend")

            output = io.StringIO()
            with (
                contextlib.redirect_stdout(output),
                backend.app.test_client() as client,
            ):
                files_response = client.get("/getFiles")
                accounts_response = client.get("/getAccounts")
                files_response.close()
                accounts_response.close()

        self.assertEqual(files_response.status_code, 200)
        self.assertEqual(accounts_response.status_code, 200)
        self.assertNotIn(marker, output.getvalue())


class LoopbackStartupContractTests(unittest.TestCase):
    def test_backend_server_config_defaults_to_loopback_and_rejects_remote_bindings(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "runtime.db"
            sys.modules.pop("sau_backend", None)
            with patch.dict(os.environ, {"SAU_DATABASE_PATH": str(database_path)}):
                backend = importlib.import_module("sau_backend")

            host, port = backend.get_web_server_config({})
            self.assertEqual((host, port), ("127.0.0.1", 5409))

            with self.assertRaisesRegex(ValueError, "loopback"):
                backend.get_web_server_config(
                    {"SAU_WEB_HOST": "192.0.2.10", "SAU_WEB_PORT": "5409"}
                )

            with self.assertRaisesRegex(ValueError, "(?i)port"):
                backend.get_web_server_config(
                    {"SAU_WEB_HOST": "127.0.0.1", "SAU_WEB_PORT": "70000"}
                )

    def test_windows_launcher_uses_locked_project_runtime_and_loopback(self):
        launcher = (REPOSITORY_ROOT / "start-win.bat").read_text(encoding="utf-8")

        self.assertIn("uv run --extra web --frozen python sau_backend.py", launcher)
        self.assertIn("--host 127.0.0.1", launcher)
        self.assertNotIn("0.0.0.0", launcher)

    def test_backend_and_vite_read_explicit_loopback_configuration(self):
        backend = (REPOSITORY_ROOT / "sau_backend.py").read_text(encoding="utf-8")
        vite = (REPOSITORY_ROOT / "sau_frontend" / "vite.config.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("SAU_WEB_HOST", backend)
        self.assertIn("SAU_WEB_PORT", backend)
        self.assertIn("VITE_API_PROXY_TARGET", vite)
        self.assertIn("127.0.0.1", vite)
        self.assertNotIn("0.0.0.0", backend)


if __name__ == "__main__":
    unittest.main()
