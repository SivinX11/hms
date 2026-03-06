from __future__ import annotations

import os

from flask import Flask, redirect, render_template, url_for

from auth import auth_bp
from db import close_db, get_db, init_db


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "src", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "src", "static"),
    )

    # Secret key for sessions/flash messages
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-prod")

    # SQLite DB path (defaults to bundled DB in this repo)
    app.config["DB_PATH"] = os.environ.get(
        "DB_PATH",
        os.path.join(os.path.dirname(__file__), "hospital_management.db"),
    )

    # Ensure required tables exist
    with app.app_context():
        init_db(app.config["DB_PATH"])

    # Close DB after each request
    app.teardown_appcontext(close_db)

    # Blueprints
    app.register_blueprint(auth_bp)

    @app.get("/")
    def index():
        # Send users to login by default
        return redirect(url_for("auth.login"))

    @app.get("/database")
    def show_all_data():
        """Display all data from the database."""
        db = get_db()

        # Fetch data from all tables
        users = db.execute("SELECT * FROM User;").fetchall()
        doctors = db.execute("SELECT * FROM Doctor;").fetchall()
        patients = db.execute("SELECT * FROM Patient;").fetchall()
        appointments = db.execute("SELECT * FROM Appointment;").fetchall()

        # Convert rows to dictionaries for easier template rendering
        users_list = [dict(row) for row in users]
        doctors_list = [dict(row) for row in doctors]
        patients_list = [dict(row) for row in patients]
        appointments_list = [dict(row) for row in appointments]

        return render_template(
            "database.html",
            users=users_list,
            doctors=doctors_list,
            patients=patients_list,
            appointments=appointments_list,
            users_count=len(users_list),
            doctors_count=len(doctors_list),
            patients_count=len(patients_list),
            appointments_count=len(appointments_list),
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
