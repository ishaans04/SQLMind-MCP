# SQLMind MCP Server

SQLMind MCP Server is a Model Context Protocol server that gives AI agents safe, read-only access to SQL databases.

Phase 6A supports:

- SQLite through `data/sample.db`
- PostgreSQL through `psycopg2-binary`
- MySQL through `pymysql`
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

## Database Configuration

SQLMind reads the initial database from environment variables:

```text
SQLMIND_DB_TYPE=sqlite
SQLMIND_SQLITE_FILE_PATH=data/sample.db
SQLMIND_DB_HOST=localhost
SQLMIND_DB_PORT=
SQLMIND_DATABASE_NAME=
SQLMIND_DB_USERNAME=
SQLMIND_DB_PASSWORD=
```

Valid `SQLMIND_DB_TYPE` values are:

- `sqlite`
- `postgresql`
- `mysql`

SQLite uses `SQLMIND_SQLITE_FILE_PATH`. PostgreSQL and MySQL use `SQLMIND_DB_HOST`, `SQLMIND_DB_PORT`, `SQLMIND_DATABASE_NAME`, `SQLMIND_DB_USERNAME`, and `SQLMIND_DB_PASSWORD`.

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

### `connect_database(config)`

Connects SQLMind to a SQLite, PostgreSQL, or MySQL database at runtime.

SQLite example:

```json
{
  "db_type": "sqlite",
  "sqlite_file_path": "data/sample.db"
}
```

PostgreSQL example:

```json
{
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database_name": "school",
  "username": "postgres",
  "password": "secret"
}
```

MySQL example:

```json
{
  "db_type": "mysql",
  "host": "localhost",
  "port": 3306,
  "database_name": "school",
  "username": "root",
  "password": "secret"
}
```

Successful responses never include the password:

```json
{
  "success": true,
  "database": {
    "db_type": "mysql",
    "sqlite_file_path": null,
    "host": "localhost",
    "port": 3306,
    "database_name": "school",
    "username": "root"
  }
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
