import sqlite3

conn = sqlite3.connect("hospital_management.db")
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON;")

# =========================
# DOCTOR TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS Doctor (
    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_name TEXT NOT NULL,
    doctor_email TEXT UNIQUE NOT NULL,
    speciality TEXT NOT NULL,
    consultation_fee REAL NOT NULL CHECK (consultation_fee >= 0),
    is_active INTEGER DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# =========================
# PATIENT TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS Patient (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT NOT NULL,
    patient_email TEXT UNIQUE NOT NULL,
    date_of_birth DATE NOT NULL,
    gender TEXT CHECK (gender IN ('Male', 'Female', 'Other')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# =========================
# APPOINTMENT TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS Appointment (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_id INTEGER NOT NULL,
    date_of_booking DATE NOT NULL,
    time_slot TEXT NOT NULL,
    status TEXT DEFAULT 'Scheduled'
        CHECK (status IN ('Scheduled', 'Completed', 'Cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)
        REFERENCES Patient(patient_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (doctor_id)
        REFERENCES Doctor(doctor_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- Prevent double booking for same doctor at same date & time
    UNIQUE(doctor_id, date_of_booking, time_slot)
);
""")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_patient_email ON Patient(patient_email);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_doctor_email ON Doctor(doctor_email);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointment_date ON Appointment(date_of_booking);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointment_status ON Appointment(status);")

conn.commit()

conn.close()
