from flask import Flask, render_template, request, send_from_directory, redirect, url_for, session, abort, jsonify
import sqlite3
import csv
import io
import os
import uuid
from datetime import datetime, timezone, timedelta
from functools import wraps
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from PIL import Image, UnidentifiedImageError
from civic_ai import suggest_category

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("CIVICFIX_SECRET_KEY", "local-demo-only-change-this-secret"),
    UPLOAD_FOLDER=str(BASE_DIR / "uploads"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("CIVICFIX_HTTPS", "0") == "1",
    PERMANENT_SESSION_LIFETIME=1800,
)
DB_PATH = BASE_DIR / "civicfix.db"
ADMIN_USERNAME = os.environ.get("CIVICFIX_ADMIN_USERNAME", "admin")
# Password is checked server-side only. Override the local-demo value using an environment variable.
ADMIN_PASSWORD = os.environ.get("CIVICFIX_ADMIN_PASSWORD", "CivicFix@123")
ADMIN_PASSWORD_HASH = os.environ.get("CIVICFIX_ADMIN_PASSWORD_HASH")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_STATUSES = {"Pending", "In Progress", "Resolved", "Rejected"}
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_database():
    conn = get_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        photo TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        admin_remarks TEXT NOT NULL DEFAULT ''
    )""")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(reports)")}
    if "user_id" not in columns:
        conn.execute("ALTER TABLE reports ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
    if "status" not in columns:
        conn.execute("ALTER TABLE reports ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'")
    if "admin_remarks" not in columns:
        conn.execute("ALTER TABLE reports ADD COLUMN admin_remarks TEXT NOT NULL DEFAULT ''")
    if "created_at" not in columns:
        conn.execute("ALTER TABLE reports ADD COLUMN created_at TEXT")
        conn.execute("UPDATE reports SET created_at = ? WHERE created_at IS NULL", (now_utc(),))
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE reports ADD COLUMN updated_at TEXT")
        conn.execute("UPDATE reports SET updated_at = COALESCE(created_at, ?) WHERE updated_at IS NULL", (now_utc(),))
    conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        comment TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        changed_at TEXT NOT NULL,
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
    )""")
    # Backfill an initial history event for complaints created by earlier project versions.
    conn.execute("""INSERT INTO status_history (report_id, old_status, new_status, changed_at)
        SELECT r.id, NULL, r.status, COALESCE(r.updated_at, r.created_at, ?)
        FROM reports r
        WHERE NOT EXISTS (SELECT 1 FROM status_history h WHERE h.report_id = r.id)""", (now_utc(),))
    conn.commit()
    conn.close()


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


create_database()


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = uuid.uuid4().hex
        session["csrf_token"] = token
    return token


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": csrf_token}


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")
        if not submitted or not expected or not __import__("hmac").compare_digest(submitted, expected):
            abort(400, description="The form security token is missing or expired. Refresh the page and try again.")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("user_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_connection()
    user = conn.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


@app.context_processor
def inject_user():
    return {"logged_in_user": current_user()}


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


def monthly_complaint_counts(conn, months=6):
    """Return database-backed monthly complaint totals for the latest months."""
    labels = []
    today = datetime.now(timezone.utc).date().replace(day=1)
    for offset in range(months - 1, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        labels.append((year, month))
    counts = {}
    rows = conn.execute("""SELECT substr(created_at, 1, 7) AS month_key, COUNT(*) AS total
        FROM reports WHERE created_at IS NOT NULL GROUP BY month_key""").fetchall()
    for row in rows:
        counts[row["month_key"]] = row["total"]
    return [{"label": datetime(year, month, 1).strftime("%b %Y"),
             "count": counts.get(f"{year:04d}-{month:02d}", 0)} for year, month in labels]


def dashboard_stats(reports):
    return {
        "total": len(reports),
        "resolved": sum(1 for r in reports if r["status"] == "Resolved"),
        "in_progress": sum(1 for r in reports if r["status"] == "In Progress"),
        "pending": sum(1 for r in reports if r["status"] == "Pending"),
        "rejected": sum(1 for r in reports if r["status"] == "Rejected"),
    }


def valid_image(file_storage):
    """Validate extension and decode the actual image, not just its browser MIME type."""
    original = secure_filename(file_storage.filename or "")
    if not original or "." not in original:
        return None
    extension = original.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return None
    try:
        file_storage.stream.seek(0)
        with Image.open(file_storage.stream) as img:
            img.verify()
            if img.format not in ALLOWED_FORMATS:
                return None
        file_storage.stream.seek(0)
        return extension
    except (UnidentifiedImageError, OSError, ValueError):
        return None


@app.route("/")
def home():
    conn = get_connection()
    reports = conn.execute("SELECT status FROM reports").fetchall()
    conn.close()
    return render_template("index.html", stats=dashboard_stats(reports))


@app.route("/api/suggest-category", methods=["POST"])
def api_suggest_category():
    """Suggest a complaint category from its description; citizens can always override it."""
    payload = request.get_json(silent=True) or {}
    description = str(payload.get("description", "")).strip()
    if len(description) < 8:
        return jsonify({"suggestion": None, "message": "Enter a little more detail to get a suggestion."})
    if len(description) > 2000:
        return jsonify({"error": "Description is too long."}), 400
    result = suggest_category(description)
    return jsonify(result)


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        if not all([name, category, description, location]):
            return render_template("report.html", error="Please complete all required fields."), 400
        if len(name) > 100 or len(category) > 60 or len(location) > 180 or len(description) > 2000:
            return render_template("report.html", error="Please check the field lengths and try again."), 400

        # Soft duplicate warning: do not block legitimate reports. A matching category/location
        # submitted in the last 24 hours is shown to the citizen for review.
        conn_check = get_connection()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
        duplicate = conn_check.execute("""SELECT id FROM reports
            WHERE lower(category)=lower(?) AND lower(location)=lower(?) AND created_at >= ?
            ORDER BY id DESC LIMIT 1""", (category, location, cutoff)).fetchone()
        conn_check.close()
        if duplicate and request.form.get("confirm_possible_duplicate") != "yes":
            return render_template("report.html", duplicate_id=duplicate["id"],
                form_values=request.form), 200

        photo = request.files.get("photo")
        photo_name = ""
        if photo and photo.filename:
            extension = valid_image(photo)
            if not extension:
                return render_template("report.html", error="Invalid image. Upload a genuine JPG, JPEG, PNG or WEBP image."), 400
            photo_name = f"{uuid.uuid4().hex}.{extension}"
            photo_path = Path(app.config["UPLOAD_FOLDER"]) / photo_name
            photo.save(photo_path)

        conn = get_connection()
        try:
            cursor = conn.execute("""INSERT INTO reports
                (name, category, description, location, photo, status, created_at, updated_at, user_id)
                VALUES (?, ?, ?, ?, ?, 'Pending', ?, ?, ?)""",
                (name, category, description, location, photo_name, now_utc(), now_utc(), session.get("user_id")))
            report_id = cursor.lastrowid
            conn.execute("INSERT INTO status_history (report_id, old_status, new_status, changed_at) VALUES (?, NULL, 'Pending', ?)", (report_id, now_utc()))
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            if photo_name:
                (Path(app.config["UPLOAD_FOLDER"]) / photo_name).unlink(missing_ok=True)
            app.logger.exception("Could not save complaint")
            return render_template("report.html", error="We could not save your complaint. Please try again."), 500
        finally:
            conn.close()
        return render_template("success.html", report_id=report_id)
    return render_template("report.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(name) < 2 or len(name) > 100 or "@" not in email or len(email) > 160 or len(password) < 8:
            error = "Enter a valid name and email. Password must contain at least 8 characters."
        else:
            conn = get_connection()
            try:
                cur = conn.execute("INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                                   (name, email, generate_password_hash(password), now_utc()))
                conn.commit()
                session.clear(); session["user_id"] = cur.lastrowid; session["user_name"] = name; session.permanent = True
                return redirect(url_for("user_dashboard"))
            except sqlite3.IntegrityError:
                error = "An account with that email already exists."
            finally:
                conn.close()
    return render_template("auth.html", mode="register", error=error)


@app.route("/login", methods=["GET", "POST"])
def user_login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_connection(); user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone(); conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear(); session["user_id"] = user["id"]; session["user_name"] = user["name"]; session.permanent = True
            return redirect(url_for("user_dashboard"))
        error = "Incorrect email or password."
    return render_template("auth.html", mode="login", error=error)


@app.route("/logout", methods=["POST"])
@login_required
def user_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def user_dashboard():
    conn = get_connection()
    reports = conn.execute("SELECT * FROM reports WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)).fetchall()
    notices = conn.execute("""SELECT h.*, r.category FROM status_history h JOIN reports r ON r.id=h.report_id
        WHERE r.user_id = ? ORDER BY h.id DESC LIMIT 12""", (session["user_id"],)).fetchall()
    feedback_ids = {r[0] for r in conn.execute("SELECT report_id FROM feedback WHERE user_id = ?", (session["user_id"],)).fetchall()}
    conn.close()
    return render_template("user_dashboard.html", reports=reports, notices=notices, feedback_ids=feedback_ids)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    error = None
    conn = get_connection()
    if request.method == "POST":
        name = request.form.get("name", "").strip(); email = request.form.get("email", "").strip().lower()
        if len(name) < 2 or len(name) > 100 or "@" not in email:
            error = "Enter a valid name and email."
        else:
            try:
                conn.execute("UPDATE users SET name=?, email=? WHERE id=?", (name, email, session["user_id"]))
                conn.commit(); session["user_name"] = name
                return redirect(url_for("profile"))
            except sqlite3.IntegrityError:
                error = "That email address is already in use."
    user = conn.execute("SELECT id,name,email,created_at FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template("profile.html", user=user, error=error)


@app.route("/feedback/<int:report_id>", methods=["POST"])
@login_required
def submit_feedback(report_id):
    try: rating = int(request.form.get("rating", "0"))
    except ValueError: rating = 0
    comment = request.form.get("comment", "").strip()
    if rating not in range(1, 6) or len(comment) > 1000:
        abort(400, description="Choose a rating from 1 to 5 and keep feedback under 1000 characters.")
    conn = get_connection()
    report_item = conn.execute("SELECT status FROM reports WHERE id=? AND user_id=?", (report_id, session["user_id"])).fetchone()
    if not report_item or report_item["status"] != "Resolved":
        conn.close(); abort(403)
    conn.execute("INSERT OR REPLACE INTO feedback (report_id,user_id,rating,comment,created_at) VALUES (?,?,?,?,?)",
                 (report_id, session["user_id"], rating, comment, now_utc()))
    conn.commit(); conn.close()
    return redirect(url_for("user_dashboard"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if ADMIN_PASSWORD_HASH:
            password_ok = check_password_hash(ADMIN_PASSWORD_HASH, password)
        else:
            password_ok = __import__("hmac").compare_digest(password, ADMIN_PASSWORD)
        if __import__("hmac").compare_digest(username, ADMIN_USERNAME) and password_ok:
            session.clear()
            session["is_admin"] = True
            session["admin_username"] = username
            session.permanent = True
            return redirect(url_for("admin"))
        error = "Incorrect username or password. Please try again."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin():
    conn = get_connection()
    reports = conn.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    users = conn.execute("SELECT id,name,email,created_at FROM users ORDER BY id DESC").fetchall()
    conn.close()
    stats = dashboard_stats(reports)
    categories = {}
    for item in reports:
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    conn = get_connection()
    monthly = monthly_complaint_counts(conn)
    conn.close()
    return render_template("admin.html", reports=reports, stats=stats, categories=categories, users=users, monthly=monthly)


@app.route("/admin/export.csv")
@admin_required
def export_reports():
    """Download current complaint records as a CSV for project reporting."""
    conn = get_connection()
    rows = conn.execute("""SELECT id, name, category, description, location, status,
        admin_remarks, created_at, updated_at FROM reports ORDER BY id DESC""").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Complaint ID", "Citizen", "Category", "Description", "Location",
                     "Status", "Admin Remarks", "Created At (UTC)", "Updated At (UTC)"])
    for row in rows:
        writer.writerow([row[key] or "" for key in row.keys()])
    from flask import Response
    return Response("\ufeff" + output.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=civicfix_complaints.csv"})


@app.route("/admin/export.pdf")
@admin_required
def export_pdf():
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        abort(501, description="PDF export dependency is not installed. Run pip install -r requirements.txt.")
    conn = get_connection(); rows = conn.execute("SELECT id,category,location,status,created_at FROM reports ORDER BY id DESC").fetchall(); conn.close()
    output = io.BytesIO(); doc = SimpleDocTemplate(output, pagesize=landscape(A4)); styles = getSampleStyleSheet()
    data = [["ID", "Category", "Location", "Status", "Created (UTC)"]]
    data.extend([[str(r["id"]), r["category"], r["location"], r["status"], r["created_at"] or ""] for r in rows])
    table = Table(data, repeatRows=1); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#172554")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.4,colors.grey),("FONTSIZE",(0,0),(-1,-1),8),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#eff6ff")])]))
    doc.build([Paragraph("CivicFix Complaint Report", styles["Title"]), Spacer(1,12), table]); output.seek(0)
    from flask import send_file
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name="civicfix_complaints.pdf")


@app.route("/update_status/<int:report_id>", methods=["POST"])
@admin_required
def update_status(report_id):
    new_status = request.form.get("status", "")
    remarks = request.form.get("admin_remarks", "").strip()
    if len(remarks) > 1000:
        abort(400, description="Admin remarks must be 1000 characters or fewer.")
    if new_status not in ALLOWED_STATUSES:
        abort(400, description="Invalid complaint status.")
    conn = get_connection()
    try:
        current = conn.execute("SELECT status FROM reports WHERE id = ?", (report_id,)).fetchone()
        if current is None:
            abort(404)
        old_status = current["status"]
        changed = now_utc()
        # Always persist the submitted remark, even when the status stays the same.
        conn.execute(
            "UPDATE reports SET status = ?, admin_remarks = ?, updated_at = ? WHERE id = ?",
            (new_status, remarks, changed, report_id),
        )
        # Record a history event only when the status actually changes.
        if old_status != new_status:
            conn.execute(
                "INSERT INTO status_history (report_id, old_status, new_status, changed_at) VALUES (?, ?, ?, ?)",
                (report_id, old_status, new_status, changed),
            )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        app.logger.exception("Could not update complaint status")
        abort(500)
    finally:
        conn.close()
    return redirect(url_for("admin"))


@app.route("/track", methods=["GET"])
def track():
    report_id = request.args.get("report_id", "").strip()
    if not report_id:
        return render_template("track.html")
    if not report_id.isdigit() or len(report_id) > 12:
        return render_template("track.html", error="Please enter a valid numeric Tracking ID.", searched=True), 400
    conn = get_connection()
    report_item = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    history = []
    if report_item and report_item["user_id"] is not None and report_item["user_id"] != session.get("user_id") and not session.get("is_admin"):
        report_item = None
    if report_item:
        history = conn.execute("SELECT old_status, new_status, changed_at FROM status_history WHERE report_id = ? ORDER BY id ASC", (report_id,)).fetchall()
    conn.close()
    return render_template("track.html", report=report_item, history=history, searched=True)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # Upload names are generated UUIDs; never allow path traversal.
    if Path(filename).name != filename:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)


@app.errorhandler(413)
def file_too_large(error):
    return render_template("report.html", error="The selected file is too large. Please upload an image under 5 MB."), 413


@app.errorhandler(400)
def bad_request(error):
    return render_template("report.html", error=getattr(error, "description", "Invalid request. Please refresh and try again.")), 400


if __name__ == "__main__":
    # Debug mode is for local development only. Do not expose this server to the internet.
    app.run(debug=os.environ.get("CIVICFIX_DEBUG", "0") == "1")
