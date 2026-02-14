from collections import defaultdict
from datetime import datetime, timedelta, timezone
import csv
import io

from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .execution import run_code
from .models import Contest, HiddenTestCase, Problem, Submission, User, Violation


ALLOWED_VIOLATIONS = {"copy_attempt", "paste_attempt", "tab_switch", "devtools_open"}


def register_routes(app):
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("admin_dashboard" if current_user.is_admin else "student_dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            college_id = request.form.get("college_id", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not all([name, college_id, email, password]):
                flash("All fields are required.", "danger")
                return render_template("register.html")

            if User.query.filter((User.email == email) | (User.college_id == college_id)).first():
                flash("Email or College ID already registered.", "danger")
                return render_template("register.html")

            user = User(name=name, college_id=college_id, email=email, role="student")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("admin_dashboard" if user.is_admin else "student_dashboard"))
            flash("Invalid credentials.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/student")
    @login_required
    def student_dashboard():
        _require_student()
        contest = _get_contest()
        problems = Problem.query.order_by(Problem.id.asc()).all() if _contest_active(contest) else []
        return render_template("student_dashboard.html", contest=contest, problems=problems, now=_utcnow())

    @app.route("/problem/<int:problem_id>")
    @login_required
    def solve_problem(problem_id):
        _require_student()
        contest = _get_contest()
        if not _contest_active(contest):
            flash("Contest is not active.", "warning")
            return redirect(url_for("student_dashboard"))
        problem = Problem.query.get_or_404(problem_id)
        return render_template("problem_solve.html", problem=problem, contest=contest)

    @app.post("/run/<int:problem_id>")
    @login_required
    def run_problem(problem_id):
        _require_student()
        contest = _get_contest()
        if not _contest_active(contest):
            return jsonify({"verdict": "Contest Not Active", "output": "", "error": "Contest not active"}), 403

        problem = Problem.query.get_or_404(problem_id)
        code = request.form.get("code", "")
        language = request.form.get("language", "python")
        custom_input = request.form.get("custom_input", "")
        result = run_code(language, code, custom_input, problem.time_limit)
        return jsonify(
            {
                "verdict": result["verdict"],
                "output": result.get("stdout", ""),
                "error": result.get("stderr", ""),
                "time": result.get("time", 0.0),
            }
        )

    @app.post("/submit/<int:problem_id>")
    @login_required
    def submit_problem(problem_id):
        _require_student()
        contest = _get_contest()
        if not _contest_active(contest):
            return jsonify({"verdict": "Contest Not Active", "score": 0, "error": "Contest not active"}), 403

        problem = Problem.query.get_or_404(problem_id)
        code = request.form.get("code", "")
        language = request.form.get("language", "python")

        test_cases = HiddenTestCase.query.filter_by(problem_id=problem.id).all()
        if not test_cases:
            verdict, score, ex_time = "Wrong Answer", 0, 0.0
        else:
            verdict = "Accepted"
            score = 100
            ex_time = 0.0
            for test_case in test_cases:
                result = run_code(language, code, test_case.input_data, problem.time_limit)
                ex_time = max(ex_time, result.get("time", 0.0))
                if result["verdict"] in {"Compilation Error", "Runtime Error", "Time Limit Exceeded"}:
                    verdict = result["verdict"]
                    score = 0
                    break
                actual = (result.get("stdout") or "").strip()
                expected = (test_case.expected_output or "").strip()
                if actual != expected:
                    verdict = "Wrong Answer"
                    score = 0
                    break

        submission = Submission(
            user_id=current_user.id,
            problem_id=problem.id,
            language=language,
            code=code,
            verdict=verdict,
            score=score,
            execution_time=ex_time,
        )
        db.session.add(submission)
        db.session.commit()
        return jsonify({"verdict": verdict, "score": score, "execution_time": ex_time})

    @app.route("/history")
    @login_required
    def submission_history():
        _require_student()
        submissions = (
            Submission.query.filter_by(user_id=current_user.id)
            .order_by(Submission.submitted_at.desc())
            .all()
        )
        return render_template("submission_history.html", submissions=submissions)

    @app.post("/log_violation")
    @login_required
    def log_violation():
        _require_student()
        violation_type = request.form.get("violation_type")
        if violation_type not in ALLOWED_VIOLATIONS:
            return jsonify({"status": "ignored"})

        violation = Violation(user_id=current_user.id, violation_type=violation_type)
        db.session.add(violation)
        db.session.commit()
        return jsonify({"status": "ok"})

    @app.route("/admin")
    @login_required
    def admin_dashboard():
        _require_admin()
        contest = _get_contest()
        total_participants = User.query.filter_by(role="student").count()
        total_submissions = Submission.query.count()
        recent_submissions = Submission.query.order_by(Submission.submitted_at.desc()).limit(10).all()

        v_counts = defaultdict(int)
        for vtype, count in db.session.query(Violation.violation_type, db.func.count(Violation.id)).group_by(
            Violation.violation_type
        ):
            v_counts[vtype] = count

        return render_template(
            "admin_dashboard.html",
            contest=contest,
            total_participants=total_participants,
            total_submissions=total_submissions,
            recent_submissions=recent_submissions,
            violation_counts=v_counts,
        )

    @app.post("/admin/contest/start")
    @login_required
    def start_contest():
        _require_admin()
        contest = _get_contest()
        contest.started_at = _utcnow()
        contest.ends_at = contest.started_at + timedelta(minutes=contest.duration_minutes)
        contest.status = "active"
        db.session.commit()
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/contest/stop")
    @login_required
    def stop_contest():
        _require_admin()
        contest = _get_contest()
        contest.status = "stopped"
        db.session.commit()
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/problems")
    @login_required
    def manage_problems():
        _require_admin()
        problems = Problem.query.order_by(Problem.id.asc()).all()
        return render_template("problem_manage.html", problems=problems)

    @app.route("/admin/problems/new", methods=["GET", "POST"])
    @login_required
    def add_problem():
        _require_admin()
        if request.method == "POST":
            problem = Problem(
                title=request.form.get("title", "").strip(),
                statement=request.form.get("statement", "").strip(),
                sample_input=request.form.get("sample_input", "").strip(),
                sample_output=request.form.get("sample_output", "").strip(),
                time_limit=max(1, int(request.form.get("time_limit", 2))),
            )
            db.session.add(problem)
            db.session.flush()
            _replace_test_cases(problem.id, request.form.get("tests", ""))
            db.session.commit()
            return redirect(url_for("manage_problems"))
        return render_template("problem_form.html", problem=None)

    @app.route("/admin/problems/<int:problem_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_problem(problem_id):
        _require_admin()
        problem = Problem.query.get_or_404(problem_id)
        if request.method == "POST":
            problem.title = request.form.get("title", "").strip()
            problem.statement = request.form.get("statement", "").strip()
            problem.sample_input = request.form.get("sample_input", "").strip()
            problem.sample_output = request.form.get("sample_output", "").strip()
            problem.time_limit = max(1, int(request.form.get("time_limit", 2)))
            _replace_test_cases(problem.id, request.form.get("tests", ""))
            db.session.commit()
            return redirect(url_for("manage_problems"))

        tests = "\n".join(f"{t.input_data}|||{t.expected_output}" for t in problem.test_cases)
        return render_template("problem_form.html", problem=problem, tests=tests)

    @app.post("/admin/problems/<int:problem_id>/delete")
    @login_required
    def delete_problem(problem_id):
        _require_admin()
        problem = Problem.query.get_or_404(problem_id)
        db.session.delete(problem)
        db.session.commit()
        return redirect(url_for("manage_problems"))

    @app.route("/admin/leaderboard")
    @login_required
    def leaderboard():
        _require_admin()
        contest = _get_contest()
        students = User.query.filter_by(role="student").all()
        rows = []
        for student in students:
            submissions = Submission.query.filter_by(user_id=student.id).all()
            by_problem_best = {}
            for s in submissions:
                by_problem_best[s.problem_id] = max(by_problem_best.get(s.problem_id, 0), s.score)
            total_score = sum(by_problem_best.values())
            solved = sum(1 for value in by_problem_best.values() if value == 100)
            last_submission = max((s.submitted_at for s in submissions), default=contest.started_at)
            violations = Violation.query.filter_by(user_id=student.id).count()
            delta = 0
            if contest.started_at and last_submission:
                delta = int((last_submission - contest.started_at).total_seconds())
            rows.append(
                {
                    "student": student,
                    "total_score": total_score,
                    "solved": solved,
                    "delta": delta,
                    "violations": violations,
                    "last_submission": last_submission or contest.started_at,
                }
            )

        rows.sort(key=lambda r: (-r["total_score"], r["delta"], r["violations"]))
        return render_template("leaderboard.html", rows=rows)

    @app.route("/admin/export")
    @login_required
    def export_csv():
        _require_admin()
        students = User.query.filter_by(role="student").all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Student Name", "Total Score", "Problems Solved"])
        for student in students:
            submissions = Submission.query.filter_by(user_id=student.id).all()
            by_problem_best = {}
            for s in submissions:
                by_problem_best[s.problem_id] = max(by_problem_best.get(s.problem_id, 0), s.score)
            total_score = sum(by_problem_best.values())
            solved = sum(1 for value in by_problem_best.values() if value == 100)
            writer.writerow([student.name, total_score, solved])

        data = io.BytesIO(output.getvalue().encode("utf-8"))
        return send_file(data, mimetype="text/csv", as_attachment=True, download_name="codesprint_results.csv")


def _replace_test_cases(problem_id, raw_tests):
    HiddenTestCase.query.filter_by(problem_id=problem_id).delete()
    for line in [row.strip() for row in raw_tests.splitlines() if row.strip()]:
        if "|||" not in line:
            continue
        input_data, expected = line.split("|||", 1)
        db.session.add(
            HiddenTestCase(
                problem_id=problem_id,
                input_data=input_data.strip(),
                expected_output=expected.strip(),
            )
        )


def _utcnow():
    return datetime.now(timezone.utc)


def _get_contest():
    return Contest.query.first()


def _contest_active(contest):
    if not contest or contest.status != "active" or not contest.started_at or not contest.ends_at:
        return False
    return contest.started_at <= _utcnow() <= contest.ends_at


def _require_admin():
    if not current_user.is_admin:
        raise PermissionError("Admins only")


def _require_student():
    if current_user.is_admin:
        raise PermissionError("Students only")
