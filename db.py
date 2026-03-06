from __future__ import annotations

import sqlite3
from typing import Any

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Get a per-request SQLite connection using the app's DB_PATH config."""
    if "db" not in g:
        db_path = current_app.config.get("DB_PATH")
        if not db_path:
            raise RuntimeError("DB_PATH not configured in app.config")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db

def close_db(_: Any = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(db_path: str) -> None:
    """Create auth tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Basic user table for authentication
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS User (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('Patient', 'Doctor', 'Admin')),
            is_active INTEGER DEFAULT 1 CHECK (is_active IN (0,1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON User(email);")

    conn.commit()
    conn.close()
