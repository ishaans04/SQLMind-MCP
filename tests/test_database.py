import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

from database import DatabaseConfig, MySQLDatabaseClient, PostgreSQLDatabaseClient, SQLMindDatabase, SQLiteDatabase
from reset_database import reset_database


def build_db(tmp_path: Path) -> SQLiteDatabase:
    db_path = tmp_path / "sample.db"
    log_path = tmp_path / "query.log"
    reset_database(db_path)
    return SQLiteDatabase(db_path=db_path, log_path=log_path)


def test_list_tables(tmp_path):
    db = build_db(tmp_path)

    response = db.list_tables()

    assert response["success"] is True
    assert response["tables"] == ["attendance", "courses", "fees", "marks", "students"]


def test_describe_table(tmp_path):
    db = build_db(tmp_path)

    response = db.describe_table("students")

    assert response["success"] is True
    assert response["columns"][0]["name"] == "id"


def test_invalid_table(tmp_path):
    db = build_db(tmp_path)

    response = db.describe_table("missing")

    assert response == {"success": False, "error": "Requested table does not exist."}


def test_run_select_query(tmp_path):
    db = build_db(tmp_path)

    response = db.run_select_query("SELECT name, year FROM students ORDER BY id LIMIT 2")

    assert response["success"] is True
    assert response["columns"] == ["name", "year"]
    assert response["rows"] == [["John Carter", 3], ["Alice Mehra", 2]]
    assert response["row_count"] == 2


def test_unsafe_query_is_blocked(tmp_path):
    db = build_db(tmp_path)

    response = db.run_select_query("DROP TABLE students")

    assert response == {"success": False, "error": "Unsafe SQL operation detected."}


def test_max_rows_is_enforced(tmp_path):
    db_path = tmp_path / "sample.db"
    reset_database(db_path)
    db = SQLiteDatabase(db_path=db_path, max_rows=1, log_path=tmp_path / "query.log")

    response = db.run_select_query("SELECT name FROM students ORDER BY id")

    assert response["success"] is True
    assert response["row_count"] == 1
    assert response["truncated"] is True


def make_connection(rows_by_execute):
    cursor = MagicMock()

    def execute(sql, params=()):
        cursor._last_sql = sql
        cursor._last_params = params

    def fetchall():
        return rows_by_execute["fetchall"]

    def fetchmany(limit):
        return rows_by_execute["fetchmany"][:limit]

    cursor.execute.side_effect = execute
    cursor.fetchall.side_effect = fetchall
    cursor.fetchmany.side_effect = fetchmany
    cursor.description = rows_by_execute.get("description", [])

    connection = MagicMock()
    connection.cursor.return_value = cursor
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = None
    return connection, cursor


def test_postgresql_schema_discovery_is_mocked(monkeypatch, tmp_path):
    connection, cursor = make_connection(
        {
            "fetchall": [("id", "integer", "NO", True), ("name", "text", "YES", False)],
            "fetchmany": [],
        }
    )
    psycopg2 = types.SimpleNamespace(connect=MagicMock(return_value=connection))
    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2)

    client = PostgreSQLDatabaseClient(
        DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            port=5432,
            database_name="school",
            username="user",
            password="secret",
        ),
        log_path=tmp_path / "query.log",
    )

    response = client.describe_table("students")

    assert response["success"] is True
    assert response["columns"][0] == {
        "name": "id",
        "type": "integer",
        "nullable": False,
        "primary_key": True,
    }
    assert cursor.execute.call_args.args[1] == ("students",)


def test_postgresql_select_query_is_mocked(monkeypatch, tmp_path):
    connection, _cursor = make_connection(
        {
            "fetchall": [],
            "fetchmany": [(1, "John")],
            "description": [("id",), ("name",)],
        }
    )
    psycopg2 = types.SimpleNamespace(connect=MagicMock(return_value=connection))
    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2)

    client = PostgreSQLDatabaseClient(
        DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            database_name="school",
            username="user",
            password="secret",
        ),
        log_path=tmp_path / "query.log",
    )

    response = client.run_select_query("SELECT id, name FROM students")

    assert response == {
        "success": True,
        "columns": ["id", "name"],
        "rows": [[1, "John"]],
        "row_count": 1,
        "truncated": False,
    }


def test_mysql_schema_discovery_is_mocked(monkeypatch, tmp_path):
    connection, cursor = make_connection(
        {
            "fetchall": [("id", "int", "NO", 1), ("name", "varchar", "YES", 0)],
            "fetchmany": [],
        }
    )
    pymysql = types.SimpleNamespace(connect=MagicMock(return_value=connection))
    monkeypatch.setitem(sys.modules, "pymysql", pymysql)

    client = MySQLDatabaseClient(
        DatabaseConfig(
            db_type="mysql",
            host="localhost",
            port=3306,
            database_name="school",
            username="user",
            password="secret",
        ),
        log_path=tmp_path / "query.log",
    )

    response = client.describe_table("students")

    assert response["success"] is True
    assert response["columns"][1] == {
        "name": "name",
        "type": "varchar",
        "nullable": True,
        "primary_key": False,
    }
    assert cursor.execute.call_args.args[1] == ("school", "students")


def test_connect_database_sanitizes_password(monkeypatch, tmp_path):
    connection, _cursor = make_connection({"fetchall": [("students",)], "fetchmany": []})
    pymysql = types.SimpleNamespace(connect=MagicMock(return_value=connection))
    monkeypatch.setitem(sys.modules, "pymysql", pymysql)
    manager = SQLMindDatabase(
        config=DatabaseConfig(db_type="sqlite", sqlite_file_path=str(tmp_path / "missing.db")),
        log_path=tmp_path / "query.log",
    )

    response = manager.connect_database(
        {
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database_name": "school",
            "username": "user",
            "password": "secret",
        }
    )

    assert response["success"] is True
    assert "password" not in response["database"]
