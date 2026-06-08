from __future__ import annotations

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for bare smoke-test environments.
    def load_dotenv() -> None:
        return None

from safety import validate_read_only_query


load_dotenv()

DEFAULT_DB_PATH = Path(os.getenv("SQLMIND_DB_PATH", "data/sample.db"))
DEFAULT_LOG_PATH = Path(os.getenv("SQLMIND_LOG_PATH", "logs/query.log"))
MAX_ROWS = int(os.getenv("SQLMIND_MAX_ROWS", "100"))
QUERY_TIMEOUT_SECONDS = float(os.getenv("SQLMIND_QUERY_TIMEOUT_SECONDS", "5"))


class DatabaseError(Exception):
    """User-safe database error."""


def _configure_logger(log_path: Path = DEFAULT_LOG_PATH) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sqlmind.query")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger


class SQLiteDatabase:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        max_rows: int = MAX_ROWS,
        timeout_seconds: float = QUERY_TIMEOUT_SECONDS,
        log_path: str | Path = DEFAULT_LOG_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.logger = _configure_logger(Path(log_path))

    def list_tables(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return {"success": True, "tables": [row["name"] for row in rows]}

    def describe_table(self, table_name: str) -> dict[str, Any]:
        if not self._table_exists(table_name):
            return {"success": False, "error": "Requested table does not exist."}

        with self._connect() as connection:
            rows = connection.execute(f"PRAGMA table_info({self._quote_identifier(table_name)})").fetchall()

        columns = [
            {
                "name": row["name"],
                "type": row["type"],
                "nullable": not bool(row["notnull"]),
                "primary_key": bool(row["pk"]),
            }
            for row in rows
        ]
        return {"success": True, "table": table_name, "columns": columns}

    def get_database_schema(self) -> dict[str, Any]:
        tables = self.list_tables()["tables"]
        return {
            "success": True,
            "schema": {
                table: self.describe_table(table)["columns"]
                for table in tables
            },
        }

    def run_select_query(self, sql: str) -> dict[str, Any]:
        safety = validate_read_only_query(sql)
        if not safety.is_safe:
            self._log_query(sql, 0.0, False, 0)
            return {"success": False, "error": safety.message}

        started = time.monotonic()
        try:
            with self._connect() as connection:
                self._install_timeout_guard(connection, started)
                cursor = connection.execute(sql)
                rows = cursor.fetchmany(self.max_rows + 1)
                columns = [description[0] for description in cursor.description or []]
        except TimeoutError:
            elapsed = time.monotonic() - started
            self._log_query(sql, elapsed, False, 0)
            return {"success": False, "error": "Query execution exceeded allowed time."}
        except sqlite3.Error:
            elapsed = time.monotonic() - started
            self._log_query(sql, elapsed, False, 0)
            return {"success": False, "error": "Invalid SQL syntax."}

        limited_rows = rows[: self.max_rows]
        elapsed = time.monotonic() - started
        self._log_query(sql, elapsed, True, len(limited_rows))
        return {
            "success": True,
            "columns": columns,
            "rows": [list(row) for row in limited_rows],
            "row_count": len(limited_rows),
            "truncated": len(rows) > self.max_rows,
        }

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise DatabaseError(f"Database file not found: {self.db_path}")

        db_uri_path = self.db_path.resolve().as_posix()
        connection = sqlite3.connect(f"file:{db_uri_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def _table_exists(self, table_name: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                  AND name NOT LIKE 'sqlite_%'
                """,
                (table_name,),
            ).fetchone()
        return row is not None

    def _install_timeout_guard(self, connection: sqlite3.Connection, started: float) -> None:
        def guard() -> int:
            if time.monotonic() - started > self.timeout_seconds:
                return 1
            return 0

        connection.set_progress_handler(guard, 1000)

    def _log_query(self, sql: str, elapsed: float, success: bool, rows_returned: int) -> None:
        safe_sql = " ".join(sql.split())
        self.logger.info(
            "timestamp=%s query=%r execution_time=%.4f success=%s rows_returned=%s",
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            safe_sql,
            elapsed,
            success,
            rows_returned,
        )
