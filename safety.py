from __future__ import annotations

import re
from dataclasses import dataclass

try:
    import sqlparse
    from sqlparse import tokens as T
except ImportError:  # pragma: no cover - fallback for bare smoke-test environments.
    sqlparse = None
    T = None


BLOCKED_KEYWORDS = {
    "ALTER",
    "ATTACH",
    "CREATE",
    "DELETE",
    "DETACH",
    "DROP",
    "INSERT",
    "PRAGMA",
    "REPLACE",
    "TRUNCATE",
    "UPDATE",
    "VACUUM",
}


@dataclass(frozen=True)
class SafetyResult:
    is_safe: bool
    message: str = ""


def validate_read_only_query(sql: str) -> SafetyResult:
    if not sql or not sql.strip():
        return SafetyResult(False, "Invalid SQL syntax.")

    if sqlparse is None:
        return _validate_without_sqlparse(sql)

    statements = [statement for statement in sqlparse.parse(sql) if str(statement).strip()]
    if len(statements) != 1:
        return SafetyResult(False, "Only one SQL statement is allowed.")

    stripped = sql.strip()
    if ";" in stripped.rstrip(";"):
        return SafetyResult(False, "Semicolon chaining is not allowed.")

    statement = statements[0]
    if statement.get_type() != "SELECT":
        return SafetyResult(False, "Unsafe SQL operation detected.")

    for token in statement.flatten():
        value = token.value.upper()
        if token.ttype in T.Comment:
            continue
        if token.ttype in T.Keyword and value in BLOCKED_KEYWORDS:
            return SafetyResult(False, "Unsafe SQL operation detected.")

    return SafetyResult(True)


def _validate_without_sqlparse(sql: str) -> SafetyResult:
    stripped = sql.strip()
    statement_count = len([part for part in stripped.split(";") if part.strip()])
    if statement_count != 1:
        return SafetyResult(False, "Only one SQL statement is allowed.")

    if ";" in stripped.rstrip(";"):
        return SafetyResult(False, "Semicolon chaining is not allowed.")

    first_word = re.match(r"^\s*([A-Za-z]+)", stripped)
    if not first_word or first_word.group(1).upper() != "SELECT":
        return SafetyResult(False, "Unsafe SQL operation detected.")

    without_strings = re.sub(r"'([^']|'')*'|\"([^\"]|\"\")*\"", " ", stripped)
    words = {word.upper() for word in re.findall(r"\b[A-Za-z_]+\b", without_strings)}
    if words & BLOCKED_KEYWORDS:
        return SafetyResult(False, "Unsafe SQL operation detected.")

    return SafetyResult(True)
