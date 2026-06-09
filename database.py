from __future__ import annotations

import logging
import os
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for bare smoke-test environments.
    def load_dotenv() -> None:
        return None

from safety import validate_read_only_query


load_dotenv()

DEFAULT_DB_TYPE = os.getenv("SQLMIND_DB_TYPE", "sqlite")
DEFAULT_SQLITE_PATH = Path(os.getenv("SQLMIND_SQLITE_FILE_PATH", os.getenv("SQLMIND_DB_PATH", "data/sample.db")))
DEFAULT_LOG_PATH = Path(os.getenv("SQLMIND_LOG_PATH", "logs/query.log"))
MAX_ROWS = int(os.getenv("SQLMIND_MAX_ROWS", "100"))
QUERY_TIMEOUT_SECONDS = float(os.getenv("SQLMIND_QUERY_TIMEOUT_SECONDS", "5"))

SUPPORTED_DB_TYPES = {"sqlite", "postgresql", "mysql"}


class DatabaseError(Exception):
    """User-safe database error."""


@dataclass(frozen=True)
class DatabaseConfig:
    db_type: str = DEFAULT_DB_TYPE
    sqlite_file_path: str | None = str(DEFAULT_SQLITE_PATH)
    host: str | None = os.getenv("SQLMIND_DB_HOST")
    port: int | None = None
    database_name: str | None = os.getenv("SQLMIND_DATABASE_NAME")
    username: str | None = os.getenv("SQLMIND_DB_USERNAME")
    password: str | None = os.getenv("SQLMIND_DB_PASSWORD")

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        port = os.getenv("SQLMIND_DB_PORT")
        return cls(
            db_type=DEFAULT_DB_TYPE,
            sqlite_file_path=str(DEFAULT_SQLITE_PATH),
            host=os.getenv("SQLMIND_DB_HOST"),
            port=int(port) if port else None,
            database_name=os.getenv("SQLMIND_DATABASE_NAME"),
            username=os.getenv("SQLMIND_DB_USERNAME"),
            password=os.getenv("SQLMIND_DB_PASSWORD"),
        )

    @classmethod
    def from_mapping(cls, config: dict[str, Any]) -> "DatabaseConfig":
        db_type = str(config.get("db_type", DEFAULT_DB_TYPE)).lower()
        port = config.get("port")
        return cls(
            db_type=db_type,
            sqlite_file_path=config.get("sqlite_file_path") or config.get("db_path") or str(DEFAULT_SQLITE_PATH),
            host=config.get("host"),
            port=int(port) if port not in (None, "") else None,
            database_name=config.get("database_name"),
            username=config.get("username"),
            password=config.get("password"),
        )

    def sanitized(self) -> dict[str, Any]:
        return {
            "db_type": self.db_type,
            "sqlite_file_path": self.sqlite_file_path if self.db_type == "sqlite" else None,
            "host": self.host,
            "port": self.port,
            "database_name": self.database_name,
            "username": self.username,
        }


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


class DatabaseClient(ABC):
    def __init__(
        self,
        config: DatabaseConfig,
        max_rows: int = MAX_ROWS,
        timeout_seconds: float = QUERY_TIMEOUT_SECONDS,
        log_path: str | Path = DEFAULT_LOG_PATH,
    ) -> None:
        self.config = config
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.logger = _configure_logger(Path(log_path))

    @abstractmethod
    def list_tables(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def describe_table(self, table_name: str) -> dict[str, Any]:
        raise NotImplementedError

    def get_database_schema(self) -> dict[str, Any]:
        tables_response = self.list_tables()
        if not tables_response.get("success"):
            return tables_response

        return {
            "success": True,
            "schema": {
                table: self.describe_table(table).get("columns", [])
                for table in tables_response["tables"]
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
                self._prepare_connection(connection, started)
                cursor = connection.cursor()
                cursor.execute(sql)
                rows = cursor.fetchmany(self.max_rows + 1)
                columns = [description[0] for description in cursor.description or []]
                cursor.close()
        except DatabaseError as exc:
            elapsed = time.monotonic() - started
            self._log_query(sql, elapsed, False, 0)
            return {"success": False, "error": str(exc)}
        except TimeoutError:
            elapsed = time.monotonic() - started
            self._log_query(sql, elapsed, False, 0)
            return {"success": False, "error": "Query execution exceeded allowed time."}
        except Exception:
            elapsed = time.monotonic() - started
            self._log_query(sql, elapsed, False, 0)
            return {"success": False, "error": "Invalid SQL syntax."}

        limited_rows = rows[: self.max_rows]
        elapsed = time.monotonic() - started
        self._log_query(sql, elapsed, True, len(limited_rows))
        return {
            "success": True,
            "columns": columns,
            "rows": [self._row_to_list(row) for row in limited_rows],
            "row_count": len(limited_rows),
            "truncated": len(rows) > self.max_rows,
        }

    @abstractmethod
    def _connect(self) -> Any:
        raise NotImplementedError

    def _prepare_connection(self, connection: Any, started: float) -> None:
        return None

    @staticmethod
    def _row_to_list(row: Any) -> list[Any]:
        return list(row)

    def _execute_fetchall(self, sql: str, params: Iterable[Any] | None = None) -> list[Any]:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, tuple(params or ()))
            rows = cursor.fetchall()
            cursor.close()
            return rows

    def _log_query(self, sql: str, elapsed: float, success: bool, rows_returned: int) -> None:
        safe_sql = " ".join(sql.split())
        self.logger.info(
            "timestamp=%s db_type=%s query=%r execution_time=%.4f success=%s rows_returned=%s",
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            self.config.db_type,
            safe_sql,
            elapsed,
            success,
            rows_returned,
        )


class SQLiteDatabaseClient(DatabaseClient):
    def __init__(
        self,
        db_path: str | Path | None = None,
        max_rows: int = MAX_ROWS,
        timeout_seconds: float = QUERY_TIMEOUT_SECONDS,
        log_path: str | Path = DEFAULT_LOG_PATH,
        config: DatabaseConfig | None = None,
    ) -> None:
        sqlite_path = str(db_path or (config.sqlite_file_path if config else DEFAULT_SQLITE_PATH))
        super().__init__(
            config or DatabaseConfig(db_type="sqlite", sqlite_file_path=sqlite_path),
            max_rows=max_rows,
            timeout_seconds=timeout_seconds,
            log_path=log_path,
        )
        self.db_path = Path(sqlite_path)

    def list_tables(self) -> dict[str, Any]:
        rows = self._execute_fetchall(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        return {"success": True, "tables": [row["name"] for row in rows]}

    def describe_table(self, table_name: str) -> dict[str, Any]:
        if not self._table_exists(table_name):
            return {"success": False, "error": "Requested table does not exist."}

        rows = self._execute_fetchall(f"PRAGMA table_info({self._quote_identifier(table_name)})")
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

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise DatabaseError(f"Database file not found: {self.db_path}")

        db_uri_path = self.db_path.resolve().as_posix()
        connection = sqlite3.connect(f"file:{db_uri_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _prepare_connection(self, connection: sqlite3.Connection, started: float) -> None:
        def guard() -> int:
            if time.monotonic() - started > self.timeout_seconds:
                return 1
            return 0

        connection.set_progress_handler(guard, 1000)

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def _table_exists(self, table_name: str) -> bool:
        rows = self._execute_fetchall(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
              AND name NOT LIKE 'sqlite_%'
            """,
            (table_name,),
        )
        return bool(rows)


class PostgreSQLDatabaseClient(DatabaseClient):
    def list_tables(self) -> dict[str, Any]:
        rows = self._execute_fetchall(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        return {"success": True, "tables": [row[0] for row in rows]}

    def describe_table(self, table_name: str) -> dict[str, Any]:
        rows = self._execute_fetchall(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN true ELSE false END AS primary_key
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
              ON c.table_schema = kcu.table_schema
             AND c.table_name = kcu.table_name
             AND c.column_name = kcu.column_name
            LEFT JOIN information_schema.table_constraints tc
              ON kcu.constraint_schema = tc.constraint_schema
             AND kcu.constraint_name = tc.constraint_name
             AND tc.constraint_type = 'PRIMARY KEY'
            WHERE c.table_schema = 'public'
              AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            (table_name,),
        )
        if not rows:
            return {"success": False, "error": "Requested table does not exist."}

        return {"success": True, "table": table_name, "columns": _column_metadata(rows)}

    def _connect(self) -> Any:
        try:
            import psycopg2
        except ImportError as exc:
            raise DatabaseError("PostgreSQL support requires psycopg2-binary.") from exc

        _require_fields(self.config, ["host", "database_name", "username", "password"])
        return psycopg2.connect(
            host=self.config.host,
            port=self.config.port or 5432,
            dbname=self.config.database_name,
            user=self.config.username,
            password=self.config.password,
            connect_timeout=int(self.timeout_seconds),
        )

    def _prepare_connection(self, connection: Any, started: float) -> None:
        cursor = connection.cursor()
        cursor.execute("SET statement_timeout = %s", (int(self.timeout_seconds * 1000),))
        cursor.close()


class MySQLDatabaseClient(DatabaseClient):
    def list_tables(self) -> dict[str, Any]:
        rows = self._execute_fetchall(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (self.config.database_name,),
        )
        return {"success": True, "tables": [row[0] for row in rows]}

    def describe_table(self, table_name: str) -> dict[str, Any]:
        rows = self._execute_fetchall(
            """
            SELECT
                column_name,
                data_type,
                is_nullable,
                CASE WHEN column_key = 'PRI' THEN 1 ELSE 0 END AS primary_key
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (self.config.database_name, table_name),
        )
        if not rows:
            return {"success": False, "error": "Requested table does not exist."}

        return {"success": True, "table": table_name, "columns": _column_metadata(rows)}

    def _connect(self) -> Any:
        try:
            import pymysql
        except ImportError as exc:
            raise DatabaseError("MySQL support requires pymysql.") from exc

        _require_fields(self.config, ["host", "database_name", "username", "password"])
        return pymysql.connect(
            host=self.config.host,
            port=self.config.port or 3306,
            database=self.config.database_name,
            user=self.config.username,
            password=self.config.password,
            connect_timeout=int(self.timeout_seconds),
            read_timeout=int(self.timeout_seconds),
            write_timeout=int(self.timeout_seconds),
        )


class SQLMindDatabase:
    def __init__(
        self,
        config: DatabaseConfig | None = None,
        max_rows: int = MAX_ROWS,
        timeout_seconds: float = QUERY_TIMEOUT_SECONDS,
        log_path: str | Path = DEFAULT_LOG_PATH,
    ) -> None:
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.log_path = log_path
        self.client = create_database_client(config or DatabaseConfig.from_env(), max_rows, timeout_seconds, log_path)

    def connect_database(self, config: dict[str, Any]) -> dict[str, Any]:
        try:
            next_config = DatabaseConfig.from_mapping(config)
            next_client = create_database_client(next_config, self.max_rows, self.timeout_seconds, self.log_path)
            next_client.list_tables()
        except DatabaseError as exc:
            return {"success": False, "error": str(exc)}
        except Exception:
            return {"success": False, "error": "Unable to connect to database."}

        self.client = next_client
        return {"success": True, "database": next_config.sanitized()}

    def list_tables(self) -> dict[str, Any]:
        return self.client.list_tables()

    def describe_table(self, table_name: str) -> dict[str, Any]:
        return self.client.describe_table(table_name)

    def get_database_schema(self) -> dict[str, Any]:
        return self.client.get_database_schema()

    def run_select_query(self, sql: str) -> dict[str, Any]:
        return self.client.run_select_query(sql)


def create_database_client(
    config: DatabaseConfig,
    max_rows: int = MAX_ROWS,
    timeout_seconds: float = QUERY_TIMEOUT_SECONDS,
    log_path: str | Path = DEFAULT_LOG_PATH,
) -> DatabaseClient:
    db_type = config.db_type.lower()
    if db_type not in SUPPORTED_DB_TYPES:
        raise DatabaseError("Unsupported database type.")

    if db_type == "sqlite":
        return SQLiteDatabaseClient(config=config, max_rows=max_rows, timeout_seconds=timeout_seconds, log_path=log_path)
    if db_type == "postgresql":
        return PostgreSQLDatabaseClient(config, max_rows=max_rows, timeout_seconds=timeout_seconds, log_path=log_path)
    return MySQLDatabaseClient(config, max_rows=max_rows, timeout_seconds=timeout_seconds, log_path=log_path)


def _require_fields(config: DatabaseConfig, fields: list[str]) -> None:
    missing = [field for field in fields if not getattr(config, field)]
    if missing:
        raise DatabaseError(f"Missing database configuration: {', '.join(missing)}.")


def _column_metadata(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": row[0],
            "type": row[1],
            "nullable": str(row[2]).upper() == "YES",
            "primary_key": bool(row[3]),
        }
        for row in rows
    ]


SQLiteDatabase = SQLiteDatabaseClient
