from __future__ import annotations

import json
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


@auth_bp.get("/login")
def login():
    return render_template("login.html")


@auth_bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not email or not password:
        flash("Please enter both email and password.", "error")
        return redirect(url_for("auth.login"))

    db = get_db()
    user = db.execute(
        "SELECT user_id, full_name, email, password_hash, role, is_active FROM User WHERE email = ?",
        (email,),
    ).fetchone()

    if user is None or user["is_active"] != 1:
        flash("Invalid login details.", "error")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user["password_hash"], password):
        flash("Invalid login details.", "error")
        return redirect(url_for("auth.login"))

    session.clear()
    session["user_id"] = user["user_id"]
    session["full_name"] = user["full_name"]
    session["role"] = user["role"]
    session["email"] = user["email"]

    flash(f"Welcome, {user['full_name']}!", "success")
    return redirect(url_for("auth.dashboard"))


@auth_bp.get("/register")
def register():
    return render_template("register.html")


@auth_bp.post("/register")
def register_post():
    full_name = (request.form.get("full_name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    role = (request.form.get("role") or "Patient").strip()
    password = request.form.get("password") or ""
    confirm = request.form.get("confirm_password") or ""

    if not full_name or not email or not password:
        flash("Please fill all required fields.", "error")
        return redirect(url_for("auth.register"))

    if role not in {"Patient", "Doctor", "Admin"}:
        flash("Invalid role selected.", "error")
        return redirect(url_for("auth.register"))

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("auth.register"))

    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.register"))

    db = get_db()

    existing = db.execute("SELECT 1 FROM User WHERE email = ?", (email,)).fetchone()
    if existing:
        flash("That email is already registered. Please login.", "error")
        return redirect(url_for("auth.login"))

    db.execute(
        "INSERT INTO User(full_name, email, password_hash, role) VALUES(?,?,?,?)",
        (full_name, email, generate_password_hash(password, method="pbkdf2:sha256", salt_length=16), role),
    )
    db.commit()

    flash("Registration successful. Please login.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.get("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.get("/dashboard")
@login_required
def dashboard():
    user_role = session.get("role")

    if user_role == "Doctor":
        return doctor_dashboard()
    elif user_role == "Patient":
        return patient_dashboard()

    return render_template(
        "dashboard.html",
        full_name=session.get("full_name"),
        role=user_role,
    )


def doctor_dashboard():
    """Doctor-specific dashboard with appointments and statistics."""
    user_id = session.get("user_id")
    full_name = session.get("full_name")
    user_email = session.get("email")

    db = get_db()

    # Get doctor information from Doctor table using email
    doctor = db.execute(
        "SELECT doctor_id, doctor_name, doctor_email, speciality, consultation_fee, is_active FROM Doctor WHERE doctor_email = ?",
        (user_email,),
    ).fetchone()

    if not doctor:
        # Render doctor dashboard with placeholder data
        return render_template(
            "doctor.html",
            full_name=full_name,
            doctor_email=user_email,
            speciality=None,
            consultation_fee=0.0,
            is_active=1,
            appointments=[],
            total_appointments=0,
            scheduled_count=0,
            completed_count=0,
            cancelled_count=0,
            this_week_appointments=0,
            pending_appointments=0,
            completion_rate=0,
            unique_patients=0,
        )

    doctor_id = doctor["doctor_id"]

    # Get all appointments for this doctor
    appointments = db.execute(
        """
        SELECT
            a.appointment_id,
            a.patient_id,
            a.date_of_booking,
            a.time_slot,
            a.status,
            p.patient_name,
            p.patient_email
        FROM Appointment a
        JOIN Patient p ON a.patient_id = p.patient_id
        WHERE a.doctor_id = ?
        ORDER BY a.date_of_booking DESC, a.time_slot DESC
        """,
        (doctor_id,),
    ).fetchall()

    # Calculate statistics
    total_appointments = len(appointments)
    scheduled_count = sum(1 for a in appointments if a["status"] == "Scheduled")
    completed_count = sum(1 for a in appointments if a["status"] == "Completed")
    cancelled_count = sum(1 for a in appointments if a["status"] == "Cancelled")

    # Get this week's appointments
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    this_week_appointments = sum(
        1 for a in appointments
        if week_start <= datetime.strptime(a["date_of_booking"], "%Y-%m-%d").date() <= week_end
    )

    # Get pending appointments (Scheduled status)
    pending_appointments = scheduled_count

    # Calculate completion rate
    completion_rate = (
        int((completed_count / total_appointments) * 100)
        if total_appointments > 0 else 0
    )

    # Count unique patients
    unique_patients = len(set(a["patient_id"] for a in appointments))

    return render_template(
        "doctor.html",
        full_name=full_name,
        doctor_email=doctor["doctor_email"],
        speciality=doctor["speciality"],
        consultation_fee=doctor["consultation_fee"],
        is_active=doctor["is_active"],
        appointments=appointments,
        total_appointments=total_appointments,
        scheduled_count=scheduled_count,
        completed_count=completed_count,
        cancelled_count=cancelled_count,
        this_week_appointments=this_week_appointments,
        pending_appointments=pending_appointments,
        completion_rate=completion_rate,
        unique_patients=unique_patients,
    )


def patient_dashboard():
    """Patient-specific dashboard with appointments and doctors."""
    from datetime import datetime

    full_name = session.get("full_name")
    user_email = session.get("email")

    db = get_db()

    # Get patient information from Patient table using email
    patient = db.execute(
        "SELECT patient_id, patient_name, patient_email, date_of_birth, gender, created_at FROM Patient WHERE patient_email = ?",
        (user_email,),
    ).fetchone()

    # Default values if patient profile doesn't exist
    appointments = []
    doctors = []
    total_appointments = 0
    scheduled_count = 0
    completed_count = 0
    unique_doctors = 0

    patient_id = None
    patient_email = user_email
    date_of_birth = None
    gender = None
    created_at = None
    age = 0

    # If patient exists, fetch their data
    if patient:
        patient_id = patient["patient_id"]
        patient_email = patient["patient_email"]
        date_of_birth = patient["date_of_birth"]
        gender = patient["gender"]
        created_at = patient["created_at"]

        # Calculate age
        if date_of_birth:
            try:
                birth_date = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                today = datetime.now().date()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            except (ValueError, TypeError):
                age = 0

        # Get all appointments for this patient
        appointments_data = db.execute(
            """
            SELECT
                a.appointment_id,
                a.doctor_id,
                a.date_of_booking,
                a.time_slot,
                a.status,
                d.doctor_name,
                d.speciality,
                d.consultation_fee
            FROM Appointment a
            JOIN Doctor d ON a.doctor_id = d.doctor_id
            WHERE a.patient_id = ?
            ORDER BY a.date_of_booking DESC, a.time_slot DESC
            """,
            (patient_id,),
        ).fetchall()

        appointments = [dict(row) for row in appointments_data]

        # Calculate statistics
        total_appointments = len(appointments)
        scheduled_count = sum(1 for a in appointments if a["status"] == "Scheduled")
        completed_count = sum(1 for a in appointments if a["status"] == "Completed")
        unique_doctors = len(set(a["doctor_id"] for a in appointments))

    # Get all active doctors
    doctors_data = db.execute(
        """
        SELECT doctor_id, doctor_name, doctor_email, speciality, consultation_fee, is_active
        FROM Doctor
        WHERE is_active = 1
        ORDER BY doctor_name ASC
        """,
    ).fetchall()

    doctors = [dict(row) for row in doctors_data]

    return render_template(
        "patient.html",
        full_name=full_name,
        patient_email=patient_email,
        date_of_birth=date_of_birth or "Not set",
        gender=gender,
        created_at=created_at,
        age=age,
        appointments=appointments,
        doctors=doctors,
        total_appointments=total_appointments,
        scheduled_count=scheduled_count,
        completed_count=completed_count,
        unique_doctors=unique_doctors,
    )


@auth_bp.post("/update-doctor-profile")
@login_required
def update_doctor_profile():
    """Update or create doctor profile with speciality and consultation fee."""
    user_email = session.get("email")
    doctor_name = request.form.get("doctor_name") or ""
    speciality = request.form.get("speciality") or ""
    consultation_fee = request.form.get("consultation_fee") or 0

    if not speciality or speciality.strip() == "":
        flash("Please select a speciality.", "error")
        return redirect(url_for("auth.dashboard"))

    try:
        consultation_fee = float(consultation_fee)
        if consultation_fee < 0:
            raise ValueError("Consultation fee cannot be negative")
    except (ValueError, TypeError):
        flash("Please enter a valid consultation fee.", "error")
        return redirect(url_for("auth.dashboard"))

    db = get_db()

    # Check if doctor profile already exists
    existing_doctor = db.execute(
        "SELECT doctor_id FROM Doctor WHERE doctor_email = ?",
        (user_email,),
    ).fetchone()

    if existing_doctor:
        # Update existing doctor profile
        db.execute(
            """
            UPDATE Doctor
            SET doctor_name = ?, speciality = ?, consultation_fee = ?
            WHERE doctor_email = ?
            """,
            (doctor_name or session.get("full_name"), speciality, consultation_fee, user_email),
        )
        flash("Doctor profile updated successfully!", "success")
    else:
        # Create new doctor profile
        try:
            db.execute(
                """
                INSERT INTO Doctor (doctor_name, doctor_email, speciality, consultation_fee, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (doctor_name or session.get("full_name"), user_email, speciality, consultation_fee),
            )
            flash("Doctor profile created successfully!", "success")
        except Exception as e:
            flash("Error creating doctor profile. Please try again.", "error")
            return redirect(url_for("auth.dashboard"))

    db.commit()
    return redirect(url_for("auth.dashboard"))


@auth_bp.post("/update-patient-profile")
@login_required
def update_patient_profile():
    """Update or create patient profile with date of birth and gender."""
    user_email = session.get("email")
    patient_name = request.form.get("patient_name") or ""
    date_of_birth = request.form.get("date_of_birth") or ""
    gender = request.form.get("gender") or ""

    if not date_of_birth or date_of_birth.strip() == "":
        flash("Please enter your date of birth.", "error")
        return redirect(url_for("auth.dashboard"))

    if not gender or gender.strip() == "":
        flash("Please select your gender.", "error")
        return redirect(url_for("auth.dashboard"))

    # Validate date format
    try:
        datetime.strptime(date_of_birth, "%Y-%m-%d")
    except (ValueError, TypeError):
        flash("Please enter a valid date of birth.", "error")
        return redirect(url_for("auth.dashboard"))

    if gender not in {"Male", "Female", "Other"}:
        flash("Please select a valid gender.", "error")
        return redirect(url_for("auth.dashboard"))

    db = get_db()

    # Check if patient profile already exists
    existing_patient = db.execute(
        "SELECT patient_id FROM Patient WHERE patient_email = ?",
        (user_email,),
    ).fetchone()

    if existing_patient:
        # Update existing patient profile
        db.execute(
            """
            UPDATE Patient
            SET patient_name = ?, date_of_birth = ?, gender = ?
            WHERE patient_email = ?
            """,
            (patient_name or session.get("full_name"), date_of_birth, gender, user_email),
        )
        flash("Patient profile updated successfully!", "success")
    else:
        # Create new patient profile
        try:
            db.execute(
                """
                INSERT INTO Patient (patient_name, patient_email, date_of_birth, gender)
                VALUES (?, ?, ?, ?)
                """,
                (patient_name or session.get("full_name"), user_email, date_of_birth, gender),
            )
            flash("Patient profile created successfully!", "success")
        except Exception as e:
            flash("Error creating patient profile. Please try again.", "error")
            return redirect(url_for("auth.dashboard"))

    db.commit()
    return redirect(url_for("auth.dashboard"))


@auth_bp.post("/book-appointment")
@login_required
def book_appointment():
    """Book an appointment between patient and doctor."""
    user_email = session.get("email")
    doctor_id = request.form.get("doctor_id")
    date_of_booking = request.form.get("date_of_booking")
    time_slot = request.form.get("time_slot")
    reason = request.form.get("reason") or ""

    # Validate inputs
    if not doctor_id or not date_of_booking or not time_slot:
        return jsonify({"success": False, "message": "Please fill in all required fields."}), 400

    try:
        doctor_id = int(doctor_id)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid doctor ID."}), 400

    # Validate date format
    try:
        appointment_date = datetime.strptime(date_of_booking, "%Y-%m-%d").date()
        # Check if date is in the future
        if appointment_date < datetime.now().date():
            return jsonify({"success": False, "message": "Please select a future date."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid date format."}), 400

    # Validate time slot
    valid_slots = ["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"]
    if time_slot not in valid_slots:
        return jsonify({"success": False, "message": "Invalid time slot selected."}), 400

    db = get_db()

    # Get patient ID from email
    patient = db.execute(
        "SELECT patient_id FROM Patient WHERE patient_email = ?",
        (user_email,),
    ).fetchone()

    if not patient:
        return jsonify({"success": False, "message": "Patient profile not found. Please complete your profile first."}), 400

    patient_id = patient["patient_id"]

    # Verify doctor exists and is active
    doctor = db.execute(
        "SELECT doctor_id, is_active FROM Doctor WHERE doctor_id = ?",
        (doctor_id,),
    ).fetchone()

    if not doctor:
        return jsonify({"success": False, "message": "Doctor not found."}), 400

    if not doctor["is_active"]:
        return jsonify({"success": False, "message": "This doctor is currently unavailable."}), 400

    # Check for existing appointment at same time/doctor
    existing = db.execute(
        """
        SELECT appointment_id FROM Appointment
        WHERE doctor_id = ? AND date_of_booking = ? AND time_slot = ?
        """,
        (doctor_id, date_of_booking, time_slot),
    ).fetchone()

    if existing:
        return jsonify({"success": False, "message": "This time slot is already booked. Please choose another."}), 400

    # Check if patient already has an appointment at same time
    patient_conflict = db.execute(
        """
        SELECT appointment_id FROM Appointment
        WHERE patient_id = ? AND date_of_booking = ? AND time_slot = ?
        """,
        (patient_id, date_of_booking, time_slot),
    ).fetchone()

    if patient_conflict:
        return jsonify({"success": False, "message": "You already have an appointment at this time."}), 400

    try:
        # Create appointment
        db.execute(
            """
            INSERT INTO Appointment (patient_id, doctor_id, date_of_booking, time_slot, status)
            VALUES (?, ?, ?, ?, 'Scheduled')
            """,
            (patient_id, doctor_id, date_of_booking, time_slot),
        )
        db.commit()

        return jsonify({"success": True, "message": "Appointment booked successfully!"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Error booking appointment: {str(e)}"}), 500
