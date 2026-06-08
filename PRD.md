# Product Requirements Document (PRD)

# SQLMind MCP Server

### Version 1.0

---

# 1. Executive Summary

SQLMind MCP Server is a Model Context Protocol (MCP) compliant server that allows AI agents to securely interact with SQL databases through standardized tools.

The MCP server acts as an intermediary layer between AI systems and databases, ensuring database operations remain safe, controlled, and observable.

The server will expose database-related tools that can be called by AI agents while enforcing strict security rules that prevent destructive database actions.

This MCP server will later become the backend foundation of the SQLMind AI Database Analyst platform.

---

# 2. Vision

Enable AI agents to safely query and understand SQL databases through MCP-compliant tools.

The MCP server should be reusable across:

* Streamlit applications
* Claude Desktop
* Cursor
* OpenAI Codex
* LangChain agents
* LangGraph workflows
* Future MCP-compatible systems

---

# 3. Problem Statement

AI models cannot safely access databases directly.

Common risks include:

* SQL injection
* Accidental deletion of records
* Unauthorized schema modifications
* Credential exposure
* Lack of standardized database tooling

The solution is an MCP server exposing only approved database tools.

---

# 4. Goals

## Primary Goals

* Build a fully functional MCP server.
* Connect securely to SQLite databases.
* Expose database tools through MCP.
* Enforce read-only access.
* Provide structured responses.
* Allow schema discovery.

## Secondary Goals

* Support PostgreSQL in future versions.
* Add authentication.
* Add query monitoring.
* Add analytics.

---

# 5. Non-Goals (Version 1)

The following are intentionally excluded:

* INSERT queries
* UPDATE queries
* DELETE queries
* DROP statements
* Database administration
* Multi-user support
* Cloud deployment
* Role-based access control
* Query optimization

---

# 6. Users

## Primary User

AI Agent

Examples:

* Claude
* GPT
* Gemini
* OpenRouter models
* LangChain Agents
* LangGraph Agents

## Secondary User

Developer testing the MCP server.

---

# 7. Architecture

## High-Level Architecture

AI Agent
↓
MCP Client
↓
SQLMind MCP Server
↓
SQLite Database

---

## Future Architecture

User
↓
Web Application
↓
AI Agent
↓
MCP Client
↓
SQLMind MCP Server
↓
Database

---

# 8. Technology Stack

## Programming Language

Python 3.11+

---

## MCP Framework

Official MCP Python SDK

---

## Database

SQLite

Future:

* PostgreSQL
* MySQL

---

## Validation

sqlparse

---

## Data Processing

pandas

---

## Environment Management

python-dotenv

---

## Logging

Python logging module

---

# 9. Folder Structure

sqlmind-mcp/

├── server.py

├── database.py

├── safety.py

├── reset_database.py

├── requirements.txt

├── README.md

├── .env.example

├── logs/

│ └── query.log

├── data/

│ └── sample.db

└── tests/

---

# 10. Database

## Initial Database

SQLite

File:

data/sample.db

---

## Sample Tables

students

courses

marks

attendance

fees

---

Purpose:

Provide realistic data for MCP testing.

---

# 11. MCP Tool Definitions

## Tool 1

### list_tables()

Purpose:

Return all available database tables.

Response Example:

[
"students",
"courses",
"marks",
"attendance",
"fees"
]

---

## Tool 2

### describe_table(table_name)

Purpose:

Return metadata for a table.

Response:

* column names
* data types

Example:

students

id INTEGER

name TEXT

email TEXT

year INTEGER

---

## Tool 3

### get_database_schema()

Purpose:

Return full database schema.

Response:

All tables with all columns.

---

## Tool 4

### run_select_query(sql)

Purpose:

Execute read-only SQL queries.

Input Example:

SELECT * FROM students LIMIT 10

Output:

{
"columns": [...],
"rows": [...],
"row_count": 10
}

---

# 12. Query Safety Engine

Every SQL query must pass safety validation before execution.

---

## Allowed

SELECT

---

## Blocked Keywords

DROP

DELETE

UPDATE

INSERT

ALTER

TRUNCATE

CREATE

REPLACE

ATTACH

DETACH

VACUUM

PRAGMA

---

## Additional Restrictions

Only one statement allowed.

No semicolon chaining.

Maximum rows returned:

100

Maximum execution time:

5 seconds

---

# 13. Error Handling

## Unsafe Query

Response:

Unsafe SQL operation detected.

---

## Invalid Table

Response:

Requested table does not exist.

---

## SQL Syntax Error

Response:

Invalid SQL syntax.

---

## Timeout

Response:

Query execution exceeded allowed time.

---

# 14. Logging

Every query execution must be logged.

Log fields:

* timestamp
* query
* execution time
* success/failure
* rows returned

Storage:

logs/query.log

---

# 15. Response Format

All tool responses must return structured JSON.

Example:

{
"success": true,
"columns": ["name", "year"],
"rows": [
["John", 3],
["Alice", 2]
],
"row_count": 2
}

---

# 16. Security Requirements

Database credentials must never be exposed.

Stack traces must never be returned to the AI.

Only read-only operations permitted.

Input validation required on every request.

SQL safety checks required before execution.

---

# 17. Testing Requirements

The MCP server must be testable through:

* MCP Inspector
* Claude Desktop
* Local Python MCP Client

---

## Test Cases

### Schema Retrieval

Input:

get_database_schema()

Expected:

Full schema returned.

---

### Table Listing

Input:

list_tables()

Expected:

All tables returned.

---

### Safe Query

Input:

SELECT * FROM students LIMIT 5

Expected:

Rows returned successfully.

---

### Unsafe Query

Input:

DROP TABLE students

Expected:

Blocked by safety engine.

---

# 18. Performance Requirements

Tool response time:

< 3 seconds

Query execution:

< 5 seconds

Server startup:

< 2 seconds

---

# 19. Deliverables

Version 1 Deliverables:

✓ Working MCP Server

✓ SQLite Integration

✓ Query Safety Layer

✓ Schema Discovery Tools

✓ Query Execution Tool

✓ Logging System

✓ README Documentation

✓ Local Testing Support

---

# 20. Success Criteria

The project is successful when:

1. MCP server starts successfully.

2. Tools are discoverable by MCP clients.

3. Database schema can be retrieved.

4. SELECT queries execute successfully.

5. Unsafe SQL is blocked.

6. Responses are structured and predictable.

7. The server is ready to be integrated into the SQLMind AI Agent web application.
