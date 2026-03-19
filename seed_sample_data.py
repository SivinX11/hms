from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta

import hashlib
import secrets


DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "hospital_management.db"))
PASSWORD = "Password@123"


def generate_password_hash_compatible(password: str, iterations: int = 1000000) -> str:
    salt = secrets.token_hex(8)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2:sha256:{iterations}${salt}${hash_bytes.hex()}"




def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON;")
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Doctor (
            doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_name TEXT NOT NULL,
            doctor_email TEXT NOT NULL UNIQUE,
            speciality TEXT NOT NULL,
            consultation_fee REAL NOT NULL DEFAULT 0,
            is_active INTEGER DEFAULT 1 CHECK (is_active IN (0,1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Patient (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            patient_email TEXT NOT NULL UNIQUE,
            date_of_birth TEXT,
            gender TEXT CHECK (gender IN ('Male','Female','Other')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Appointment (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            date_of_booking TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled' CHECK (status IN ('Scheduled','Completed','Cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES Patient(patient_id) ON DELETE CASCADE,
            FOREIGN KEY(doctor_id) REFERENCES Doctor(doctor_id) ON DELETE CASCADE,
            UNIQUE(doctor_id, date_of_booking, time_slot)
        );
        """
    )



def upsert_user(conn: sqlite3.Connection, full_name: str, email: str, role: str) -> None:
    conn.execute(
        """
        INSERT INTO User (full_name, email, password_hash, role, is_active)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(email) DO UPDATE SET
            full_name = excluded.full_name,
            password_hash = excluded.password_hash,
            role = excluded.role,
            is_active = 1
        """,
        (full_name, email, generate_password_hash_compatible(PASSWORD), role),
    )



def seed() -> None:
    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)

    users = [
        ("Admin User", "admin@hms.com", "Admin"),
        ("Dr. Priya Sharma", "priya.sharma@hms.com", "Doctor"),
        ("Dr. Arjun Mehta", "arjun.mehta@hms.com", "Doctor"),
        ("Aisha Khan", "aisha.khan@hms.com", "Patient"),
        ("Rohan Das", "rohan.das@hms.com", "Patient"),
        ("Neha Iyer", "neha.iyer@hms.com", "Patient"),
    ]

    for full_name, email, role in users:
        upsert_user(conn, full_name, email, role)

    conn.execute("DELETE FROM Appointment")
    conn.execute("DELETE FROM Doctor")
    conn.execute("DELETE FROM Patient")

    doctors = [
        ("Dr. Priya Sharma", "priya.sharma@hms.com", "Cardiology", 1200.0, 1),
        ("Dr. Arjun Mehta", "arjun.mehta@hms.com", "Dermatology", 900.0, 1),
    ]
    for doctor in doctors:
        conn.execute(
            "INSERT INTO Doctor (doctor_name, doctor_email, speciality, consultation_fee, is_active) VALUES (?, ?, ?, ?, ?)",
            doctor,
        )

    patients = [
        ("Aisha Khan", "aisha.khan@hms.com", "1998-04-11", "Female"),
        ("Rohan Das", "rohan.das@hms.com", "1994-09-23", "Male"),
        ("Neha Iyer", "neha.iyer@hms.com", "2000-01-15", "Female"),
    ]
    for patient in patients:
        conn.execute(
            "INSERT INTO Patient (patient_name, patient_email, date_of_birth, gender) VALUES (?, ?, ?, ?)",
            patient,
        )

    doctors_by_email = {
        row[1]: row[0]
        for row in conn.execute("SELECT doctor_id, doctor_email FROM Doctor").fetchall()
    }
    patients_by_email = {
        row[1]: row[0]
        for row in conn.execute("SELECT patient_id, patient_email FROM Patient").fetchall()
    }

    today = date.today()
    appointments = [
        (patients_by_email["aisha.khan@hms.com"], doctors_by_email["priya.sharma@hms.com"], str(today + timedelta(days=1)), "10:00 AM", "Scheduled"),
        (patients_by_email["rohan.das@hms.com"], doctors_by_email["priya.sharma@hms.com"], str(today + timedelta(days=2)), "11:00 AM", "Scheduled"),
        (patients_by_email["neha.iyer@hms.com"], doctors_by_email["arjun.mehta@hms.com"], str(today + timedelta(days=3)), "03:00 PM", "Scheduled"),
        (patients_by_email["aisha.khan@hms.com"], doctors_by_email["arjun.mehta@hms.com"], str(today + timedelta(days=4)), "09:00 AM", "Completed"),
        (patients_by_email["rohan.das@hms.com"], doctors_by_email["arjun.mehta@hms.com"], str(today + timedelta(days=5)), "04:00 PM", "Cancelled"),
    ]
    for appointment in appointments:
        conn.execute(
            "INSERT INTO Appointment (patient_id, doctor_id, date_of_booking, time_slot, status) VALUES (?, ?, ?, ?, ?)",
            appointment,
        )

    conn.commit()
    conn.close()
    print(f"Seeded sample data into: {DB_PATH}")
    print("Default password for all sample users: Password@123")
    print("Admin login: admin@hms.com / Password@123")


if __name__ == "__main__":
    seed()
