# SQLite database helper for the coursework project

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple


class DatabaseManager:
    # thin wrapper around sqlite3 with convenience helpers

    def __init__(self, db_path: str = "database/platform.db") -> None:
        # determine the sqlite path and make sure the folder exists
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        # create a new connection with row access by column name
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def close(self, conn: Optional[sqlite3.Connection]) -> None:
        # close the provided connection if it exists
        if conn is not None:
            conn.close()

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[int]:
        # execute INSERT/UPDATE/DELETE statements
        conn = self.connect()
        try:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as exc:  # pragma: no cover - console log is enough
            print(f"Database execute error: {exc}")
            return None
        finally:
            self.close(conn)

    def fetch_one(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[dict]:
        # return the first row as a dict or None
        conn = self.connect()
        try:
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:  # pragma: no cover - simple logging
            print(f"Database fetch_one error: {exc}")
            return None
        finally:
            self.close(conn)

    def fetch_all(self, sql: str, params: Tuple[Any, ...] = ()) -> List[dict]:
        # return all rows as dictionaries
        conn = self.connect()
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:  # pragma: no cover
            print(f"Database fetch_all error: {exc}")
            return []
        finally:
            self.close(conn)

    def create_tables(self) -> None:
        # create the required tables when they do not already exist
        table_statements: Iterable[str] = (
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS security_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_date TEXT,
                incident_type TEXT,
                severity TEXT,
                status TEXT,
                description TEXT,
                assigned_to TEXT,
                resolved_date TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                department TEXT,
                size_mb REAL,
                rows_count INTEGER,
                quality_score INTEGER,
                source_dependency TEXT,
                upload_date TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS it_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opened_date TEXT,
                category TEXT,
                priority TEXT,
                status TEXT,
                assigned_staff TEXT,
                description TEXT,
                resolved_date TEXT
            )
            """,
        )

        for statement in table_statements:
            self.execute(statement)
