# SQLMind MCP Server

SQLMind MCP Server is a Model Context Protocol server that gives AI agents safe, read-only access to SQLite databases.

Version 1 implements:

- SQLite connection through `data/sample.db`
- MCP tools for table listing, table description, full schema retrieval, and safe SELECT execution
- SQL safety checks that block destructive statements
- Maximum 100 returned rows by default
- Query logging to `logs/query.log`
- A reset script for a realistic sample database

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python reset_database.py
```

Copy `.env.example` to `.env` if you want to override defaults.

## Run the MCP server

```powershell
python server.py
```

The server uses stdio transport through the official MCP Python SDK.

## Tools

### `list_tables()`

Returns all user-defined tables.

### `describe_table(table_name)`

Returns column metadata for one table.

### `get_database_schema()`

Returns all table schemas.

### `run_select_query(sql)`

Executes one read-only `SELECT` statement and returns:

```json
{
  "success": true,
  "columns": ["name", "year"],
  "rows": [["John Carter", 3]],
  "row_count": 1,
  "truncated": false
}
```

Unsafe SQL returns:

```json
{
  "success": false,
  "error": "Unsafe SQL operation detected."
}
```

## Safety Rules

Allowed:

- One `SELECT` statement

Blocked:

- `DROP`
- `DELETE`
- `UPDATE`
- `INSERT`
- `ALTER`
- `TRUNCATE`
- `CREATE`
- `REPLACE`
- `ATTACH`
- `DETACH`
- `VACUUM`
- `PRAGMA`
- semicolon chaining

## Test

```powershell
pytest
```

## MCP Client Configuration Example

```json
{
  "mcpServers": {
    "sqlmind": {
      "command": "python",
      "args": ["C:\\Users\\inder\\OneDrive\\Desktop\\SQLMind-MCP\\server.py"]
    }
  }
}
```
