from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
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

    db = get_db(current_app.config["DB_PATH"])
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

    db = get_db(current_app.config["DB_PATH"])

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
    return render_template(
        "dashboard.html",
        full_name=session.get("full_name"),
        role=session.get("role"),
    )
