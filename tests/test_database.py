from pathlib import Path

from database import SQLiteDatabase
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
