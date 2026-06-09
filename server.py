from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from database import DatabaseError, SQLMindDatabase


mcp = FastMCP("SQLMind MCP Server")
db = SQLMindDatabase()


def _safe_call(operation: str, *args: Any) -> dict[str, Any]:
    try:
        method = getattr(db, operation)
        return method(*args)
    except DatabaseError as exc:
        return {"success": False, "error": str(exc)}
    except Exception:
        return {"success": False, "error": "Internal server error."}


@mcp.tool()
def list_tables() -> dict[str, Any]:
    """Return all available user-defined database tables."""
    return _safe_call("list_tables")


@mcp.tool()
def describe_table(table_name: str) -> dict[str, Any]:
    """Return column metadata for a table."""
    return _safe_call("describe_table", table_name)


@mcp.tool()
def get_database_schema() -> dict[str, Any]:
    """Return the full database schema."""
    return _safe_call("get_database_schema")


@mcp.tool()
def run_select_query(sql: str) -> dict[str, Any]:
    """Execute one safe read-only SELECT query."""
    return _safe_call("run_select_query", sql)


@mcp.tool()
def connect_database(config: dict[str, Any]) -> dict[str, Any]:
    """Connect SQLMind to a SQLite, PostgreSQL, or MySQL database."""
    return _safe_call("connect_database", config)


if __name__ == "__main__":
    mcp.run()
