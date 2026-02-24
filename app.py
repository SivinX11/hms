from __future__ import annotations

import os
from flask import Flask, redirect, url_for

from auth import auth_bp
from db import close_db, init_db


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

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
