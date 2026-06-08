from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("data/sample.db")


def reset_database(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                year INTEGER NOT NULL
            );

            CREATE TABLE courses (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                credits INTEGER NOT NULL
            );

            CREATE TABLE marks (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                score REAL NOT NULL,
                exam TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );

            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                attended INTEGER NOT NULL,
                total INTEGER NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (course_id) REFERENCES courses(id)
            );

            CREATE TABLE fees (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                amount_due REAL NOT NULL,
                amount_paid REAL NOT NULL,
                due_date TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
            """
        )
        connection.executemany(
            "INSERT INTO students (id, name, email, year) VALUES (?, ?, ?, ?)",
            [
                (1, "John Carter", "john.carter@example.edu", 3),
                (2, "Alice Mehra", "alice.mehra@example.edu", 2),
                (3, "Riya Sharma", "riya.sharma@example.edu", 1),
                (4, "Omar Khan", "omar.khan@example.edu", 4),
                (5, "Nina Patel", "nina.patel@example.edu", 2),
            ],
        )
        connection.executemany(
            "INSERT INTO courses (id, code, name, credits) VALUES (?, ?, ?, ?)",
            [
                (1, "CS101", "Introduction to Computer Science", 4),
                (2, "MATH201", "Linear Algebra", 3),
                (3, "DB301", "Database Systems", 4),
            ],
        )
        connection.executemany(
            "INSERT INTO marks (student_id, course_id, score, exam) VALUES (?, ?, ?, ?)",
            [
                (1, 1, 86.5, "midterm"),
                (1, 3, 91.0, "final"),
                (2, 2, 78.0, "midterm"),
                (3, 1, 88.0, "quiz"),
                (4, 3, 94.5, "final"),
                (5, 2, 81.0, "final"),
            ],
        )
        connection.executemany(
            "INSERT INTO attendance (student_id, course_id, attended, total) VALUES (?, ?, ?, ?)",
            [
                (1, 1, 24, 26),
                (1, 3, 22, 24),
                (2, 2, 19, 24),
                (3, 1, 25, 26),
                (4, 3, 23, 24),
                (5, 2, 21, 24),
            ],
        )
        connection.executemany(
            "INSERT INTO fees (student_id, amount_due, amount_paid, due_date) VALUES (?, ?, ?, ?)",
            [
                (1, 1200.0, 1200.0, "2026-07-15"),
                (2, 950.0, 500.0, "2026-07-15"),
                (3, 1100.0, 1100.0, "2026-08-01"),
                (4, 1500.0, 1000.0, "2026-07-20"),
                (5, 950.0, 950.0, "2026-07-15"),
            ],
        )


if __name__ == "__main__":
    reset_database()
    print(f"Reset database at {DB_PATH}")
