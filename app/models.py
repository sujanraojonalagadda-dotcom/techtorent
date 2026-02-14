from datetime import datetime, timezone
from flask_login import UserMixin
from . import bcrypt, db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    college_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    submissions = db.relationship("Submission", backref="user", lazy=True)
    violations = db.relationship("Violation", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="stopped", nullable=False)
    duration_minutes = db.Column(db.Integer, default=120, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)


class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    statement = db.Column(db.Text, nullable=False)
    sample_input = db.Column(db.Text, default="")
    sample_output = db.Column(db.Text, default="")
    time_limit = db.Column(db.Integer, default=2, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    test_cases = db.relationship("HiddenTestCase", backref="problem", lazy=True, cascade="all, delete-orphan")
    submissions = db.relationship("Submission", backref="problem", lazy=True)


class HiddenTestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey("problem.id"), nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    expected_output = db.Column(db.Text, nullable=False)


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey("problem.id"), nullable=False)
    language = db.Column(db.String(20), nullable=False)
    code = db.Column(db.Text, nullable=False)
    verdict = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, default=0, nullable=False)
    execution_time = db.Column(db.Float, default=0.0, nullable=False)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Violation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    violation_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
