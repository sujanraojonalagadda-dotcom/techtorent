import os
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "login"


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(app.instance_path, 'codesprint.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["CONTEST_DURATION_HOURS"] = 2

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from .models import Contest, User

        db.create_all()
        _seed_admins()
        _ensure_contest(app)

    from .routes import register_routes

    register_routes(app)


    @app.errorhandler(PermissionError)
    def handle_permission_error(error):
        return jsonify({"error": str(error)}), 403

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled exception: %s", error)
        return jsonify({"error": "An internal error occurred. Please contact admin."}), 500

    return app


def _seed_admins():
    from .models import User

    admins = [
        ("Admin One", "admin1@codesprint.com", "Admin@123"),
        ("Admin Two", "admin2@codesprint.com", "Admin@456"),
    ]
    for name, email, password in admins:
        if not User.query.filter_by(email=email).first():
            user = User(name=name, college_id=f"ADMIN-{email}", email=email, role="admin")
            user.set_password(password)
            db.session.add(user)
    db.session.commit()


def _ensure_contest(app):
    from .models import Contest

    contest = Contest.query.first()
    if not contest:
        contest = Contest(
            status="stopped",
            duration_minutes=app.config["CONTEST_DURATION_HOURS"] * 60,
            started_at=None,
            ends_at=None,
        )
        db.session.add(contest)
        db.session.commit()
