from __future__ import annotations

import sqlite3
from typing import Any

from flask import current_app, g


SCHEMA_STATEMENTS = [
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
    """,
    "CREATE INDEX IF NOT EXISTS idx_user_email ON User(email);",
    """
    CREATE TABLE IF NOT EXISTS Doctor (
        doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT NOT NULL,
        doctor_email TEXT UNIQUE NOT NULL,
        speciality TEXT NOT NULL,
        consultation_fee REAL NOT NULL CHECK (consultation_fee >= 0),
        is_active INTEGER DEFAULT 1 CHECK (is_active IN (0,1)),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_doctor_email ON Doctor(doctor_email);",
    """
    CREATE TABLE IF NOT EXISTS Patient (
        patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT NOT NULL,
        patient_email TEXT UNIQUE NOT NULL,
        date_of_birth DATE NOT NULL,
        gender TEXT CHECK (gender IN ('Male', 'Female', 'Other')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_patient_email ON Patient(patient_email);",
    """
    CREATE TABLE IF NOT EXISTS Appointment (
        appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        date_of_booking DATE NOT NULL,
        time_slot TEXT NOT NULL,
        status TEXT DEFAULT 'Scheduled' CHECK (status IN ('Scheduled', 'Completed', 'Cancelled')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY (doctor_id) REFERENCES Doctor(doctor_id) ON DELETE CASCADE ON UPDATE CASCADE,
        UNIQUE(doctor_id, date_of_booking, time_slot)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_appointment_date ON Appointment(date_of_booking);",
    "CREATE INDEX IF NOT EXISTS idx_appointment_status ON Appointment(status);",
]


def get_db() -> sqlite3.Connection:
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
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)
    conn.commit()
    conn.close()
