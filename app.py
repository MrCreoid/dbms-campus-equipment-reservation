import os
import re
from datetime import datetime
from functools import wraps

import mysql.connector
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_connection

app = Flask(__name__)
# No fallback: without SECRET_KEY, Flask refuses to create sessions instead of using a guessable key.
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
# Browsers will not send the session cookie with cross-site form posts (basic CSRF protection).
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

STAFF = ("lab_staff", "admin")
MAINTENANCE_ORDER = ["open", "in_progress", "resolved"]

# Presenter crib notes, shown by the "For demo" toggle on every page (templates/base.html).
DEMO_NOTES = {
    "login": "Three demo logins are listed below, one per role. Student books equipment, lab staff "
             "approves bookings and handles maintenance, admin also manages labs and categories. "
             "Every page carries this For demo toggle. Passwords are hashed with Werkzeug; the "
             "session cookie is SameSite=Lax, so cross-site form posts cannot ride along.",
    "register": "Self-registration only ever creates a student. Staff and admin accounts are made by "
                "the lab office, so the role cannot be chosen from the form.",
    "dashboard": "Counts come from SQL aggregates, not Python loops. Staff and admin see lab-wide "
                 "totals; a student sees only their own pending and upcoming bookings — the same "
                 "template, filtered by role.",
    "equipment_list": "Catalogue with filters on lab, category and status. Each filter is a WHERE "
                      "clause built from request args with bound parameters, so there is no SQL "
                      "injection surface. Open an item to book it.",
    "equipment_detail": "Shows the item, its upcoming approved bookings and its maintenance history. "
                        "Booking a slot checks for overlap inside a transaction, so two people cannot "
                        "grab the same instrument.",
    "equipment_new": "Lab and category are foreign keys, so an item can never point at a lab that "
                     "does not exist.",
    "equipment_edit": "Retire equipment here rather than deleting it; past reservations keep pointing "
                      "at a real row.",
    "reservations": "A student sees their own requests and can cancel them. Staff see every request "
                    "and can approve, reject or complete one. Approval re-checks for overlap before "
                    "committing, in case another booking landed in the meantime.",
    "maintenance": "Staff log a fault against an item and walk it open to in progress to resolved. "
                   "Backwards jumps are rejected in code, so the status history stays honest.",
    "reports": "The analytics queries live in reports.sql, not in Python: joins, GROUP BY and "
               "aggregates answering utilisation, busiest labs and repeat faults.",
    "admin": "Labs and categories in use cannot be deleted — the foreign keys refuse it — which is "
             "the point: referential integrity is enforced by the database, not by hope.",
}

DEMO_LOGINS = [
    ("Student", "student@campus.test", "student12345"),
    ("Lab staff", "staff@campus.test", "staff12345"),
    ("Admin", "admin@campus.test", "admin12345"),
]


@app.context_processor
def demo_context():
    return {"demo_note": DEMO_NOTES.get(request.endpoint), "demo_logins": DEMO_LOGINS}



def validate_slot(start, end, now):
    """Return an error message for an invalid booking time range, or None."""
    if start is None or end is None:
        return "Please enter both a start and an end time."
    if end <= start:
        return "The end time must be later than the start time."
    if start <= now:
        return "Reservations must be for a future time slot."
    return None


def maintenance_step_allowed(current, new):
    # Records only move forward: open -> in_progress -> resolved (skipping in_progress is fine).
    return new in MAINTENANCE_ORDER and MAINTENANCE_ORDER.index(new) > MAINTENANCE_ORDER.index(current)


def load_reports(path=os.path.join(os.path.dirname(__file__), "reports.sql")):
    """reports.sql is the single source of report queries; each starts with '-- name: <key>'."""
    with open(path) as f:
        parts = re.split(r"^-- name: (\w+)\n", f.read(), flags=re.M)
    return {name: sql.strip().rstrip(";") for name, sql in zip(parts[1::2], parts[2::2])}


def go_back(default):
    # Only follow local paths, so a crafted form cannot redirect to another site.
    target = request.form.get("next", "")
    return redirect(target if target.startswith("/") and not target.startswith("//") else default)


def parse_datetime(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def db():
    if "db" not in g:
        g.db = get_connection()
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def query(sql, params=(), one=False):
    cur = db().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    cur = db().cursor()
    try:
        cur.execute(sql, params)
        return cur.lastrowid
    finally:
        cur.close()


def require(*roles):
    """Protect a view: any logged-in user, or only the given roles."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if roles and g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.before_request
def load_user():
    g.user = None
    if "user_id" in session:
        g.user = query("SELECT user_id, name, email, department, role FROM users WHERE user_id = %s",
                       (session["user_id"],), one=True)


@app.template_filter("when")
def format_when(value):
    return value.strftime("%d %b %Y, %H:%M") if value else "—"


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, message="You do not have permission to do that."), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, message="That page or record does not exist."), 404


@app.errorhandler(mysql.connector.Error)
def database_error(e):
    app.logger.exception("Database error: %s", e)
    return render_template("error.html", code=500,
                           message="A database error occurred. Check that MySQL is running and .env is correct."), 500


def booking_problem(cur, equipment_id, start, end):
    """Why this slot cannot be approved/booked, or None. Locks the equipment row inside a transaction."""
    cur.execute("SELECT status FROM equipment WHERE equipment_id = %s FOR UPDATE", (equipment_id,))
    item = cur.fetchone()
    if item is None:
        return "Equipment not found."
    if item["status"] != "active":
        return "This equipment is retired and cannot be booked."
    cur.execute("SELECT COUNT(*) AS n FROM maintenance_records "
                "WHERE equipment_id = %s AND status <> 'resolved'", (equipment_id,))
    if cur.fetchone()["n"]:
        return "This equipment has an unresolved maintenance issue."
    cur.execute("SELECT COUNT(*) AS n FROM reservations "
                "WHERE equipment_id = %s AND status = 'approved' AND start_time < %s AND end_time > %s",
                (equipment_id, end, start))
    if cur.fetchone()["n"]:
        return "This time slot overlaps an approved reservation for the same equipment."
    return None


def upcoming_approved_count(equipment_id):
    return query("SELECT COUNT(*) AS n FROM reservations "
                 "WHERE equipment_id = %s AND status = 'approved' AND end_time > NOW()",
                 (equipment_id,), one=True)["n"]


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = query("SELECT user_id, password_hash FROM users WHERE email = %s",
                     (request.form["email"].strip().lower(),), one=True)
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.clear()
            session["user_id"] = user["user_id"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        department = request.form["department"].strip()
        password = request.form["password"]
        if not (name and email and department):
            flash("All fields are required.", "error")
        elif "@" not in email:
            flash("Please enter a valid email address.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        else:
            try:
                # Public registration always creates a student; staff/admin come from seed.py.
                execute("INSERT INTO users (name, email, password_hash, department, role) "
                        "VALUES (%s, %s, %s, %s, 'student')",
                        (name, email, generate_password_hash(password), department))
            except mysql.connector.IntegrityError:
                flash("An account with that email already exists.", "error")
            else:
                flash("Account created. You can log in now.", "success")
                return redirect(url_for("login"))
    return render_template("register.html")


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/")
@require()
def dashboard():
    uid = g.user["user_id"]
    counts = query("""
        SELECT
            (SELECT COUNT(*) FROM equipment WHERE status = 'active') AS active_equipment,
            (SELECT COUNT(*) FROM reservations WHERE status = 'pending') AS pending_all,
            (SELECT COUNT(*) FROM reservations WHERE status = 'approved' AND end_time > NOW()) AS upcoming_all,
            (SELECT COUNT(*) FROM maintenance_records WHERE status <> 'resolved') AS open_maintenance,
            (SELECT COUNT(*) FROM reservations WHERE user_id = %s AND status = 'pending') AS my_pending,
            (SELECT COUNT(*) FROM reservations
              WHERE user_id = %s AND status = 'approved' AND end_time > NOW()) AS my_upcoming
    """, (uid, uid), one=True)
    my_next = query("""
        SELECT r.start_time, r.end_time, r.status, e.equipment_id, e.equipment_name, e.asset_tag
        FROM reservations r JOIN equipment e ON e.equipment_id = r.equipment_id
        WHERE r.user_id = %s AND r.status IN ('pending', 'approved') AND r.end_time > NOW()
        ORDER BY r.start_time LIMIT 5
    """, (uid,))
    return render_template("dashboard.html", counts=counts, my_next=my_next)


@app.route("/equipment")
@require()
def equipment_list():
    q = request.args.get("q", "").strip()
    lab_id = request.args.get("lab", type=int)
    category_id = request.args.get("category", type=int)
    conditions, params = [], []
    if q:
        conditions.append("(e.equipment_name LIKE %s OR e.asset_tag LIKE %s)")
        params += [f"%{q}%", f"%{q}%"]
    if lab_id:
        conditions.append("e.lab_id = %s")
        params.append(lab_id)
    if category_id:
        conditions.append("e.category_id = %s")
        params.append(category_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    items = query(f"""
        SELECT e.equipment_id, e.asset_tag, e.equipment_name, e.status,
               c.category_name, l.lab_name, l.building, l.room_no,
               EXISTS (SELECT 1 FROM maintenance_records m
                       WHERE m.equipment_id = e.equipment_id AND m.status <> 'resolved') AS under_maintenance,
               EXISTS (SELECT 1 FROM reservations r
                       WHERE r.equipment_id = e.equipment_id AND r.status = 'approved'
                         AND NOW() BETWEEN r.start_time AND r.end_time) AS in_use
        FROM equipment e
        JOIN categories c ON c.category_id = e.category_id
        JOIN labs l ON l.lab_id = e.lab_id
        {where}
        ORDER BY e.equipment_name, e.asset_tag
    """, params)
    return render_template("equipment.html", items=items, q=q, lab_id=lab_id, category_id=category_id,
                           labs=query("SELECT lab_id, lab_name FROM labs ORDER BY lab_name"),
                           categories=query("SELECT category_id, category_name FROM categories ORDER BY category_name"))


@app.route("/equipment/<int:equipment_id>")
@require()
def equipment_detail(equipment_id):
    item = query("""
        SELECT e.*, c.category_name, l.lab_name, l.building, l.room_no
        FROM equipment e
        JOIN categories c ON c.category_id = e.category_id
        JOIN labs l ON l.lab_id = e.lab_id
        WHERE e.equipment_id = %s
    """, (equipment_id,), one=True)
    if item is None:
        abort(404)
    upcoming = query("""
        SELECT r.reservation_id, r.start_time, r.end_time, r.purpose, u.name AS requester
        FROM reservations r JOIN users u ON u.user_id = r.user_id
        WHERE r.equipment_id = %s AND r.status = 'approved' AND r.end_time > NOW()
        ORDER BY r.start_time
    """, (equipment_id,))
    history = query("""
        SELECT m.*, rep.name AS reporter, h.name AS handler
        FROM maintenance_records m
        JOIN users rep ON rep.user_id = m.reported_by
        LEFT JOIN users h ON h.user_id = m.handled_by
        WHERE m.equipment_id = %s
        ORDER BY m.reported_at DESC
    """, (equipment_id,))
    unresolved = any(m["status"] != "resolved" for m in history)
    return render_template("equipment_detail.html", item=item, upcoming=upcoming, history=history,
                           bookable=item["status"] == "active" and not unresolved, unresolved=unresolved)


def equipment_form_data():
    f = request.form
    return (f["asset_tag"].strip(), f["equipment_name"].strip(), f.get("category_id", type=int),
            f.get("lab_id", type=int), f["details"].strip() or None, f["purchase_date"] or None)


def render_equipment_form(item):
    return render_template("equipment_form.html", item=item,
                           labs=query("SELECT lab_id, lab_name, building, room_no FROM labs ORDER BY lab_name"),
                           categories=query("SELECT category_id, category_name FROM categories ORDER BY category_name"))


@app.route("/equipment/new", methods=["GET", "POST"])
@require("admin")
def equipment_new():
    if request.method == "POST":
        data = equipment_form_data()
        if not all(data[:4]):
            flash("Asset tag, name, category and lab are required.", "error")
        else:
            try:
                new_id = execute("INSERT INTO equipment (asset_tag, equipment_name, category_id, lab_id, "
                                 "details, purchase_date) VALUES (%s, %s, %s, %s, %s, %s)", data)
            except mysql.connector.IntegrityError:
                flash("That asset tag is already in use, or the lab/category is invalid.", "error")
            else:
                flash("Equipment added.", "success")
                return redirect(url_for("equipment_detail", equipment_id=new_id))
    return render_equipment_form(None)


@app.route("/equipment/<int:equipment_id>/edit", methods=["GET", "POST"])
@require("admin")
def equipment_edit(equipment_id):
    item = query("SELECT * FROM equipment WHERE equipment_id = %s", (equipment_id,), one=True)
    if item is None:
        abort(404)
    if request.method == "POST":
        data = equipment_form_data()
        status = request.form.get("status")
        if not all(data[:4]) or status not in ("active", "retired"):
            flash("Asset tag, name, category, lab and status are required.", "error")
        else:
            try:
                execute("UPDATE equipment SET asset_tag = %s, equipment_name = %s, category_id = %s, lab_id = %s, "
                        "details = %s, purchase_date = %s, status = %s WHERE equipment_id = %s",
                        (*data, status, equipment_id))
            except mysql.connector.IntegrityError:
                flash("That asset tag is already in use, or the lab/category is invalid.", "error")
            else:
                flash("Equipment updated.", "success")
                if status == "retired" and upcoming_approved_count(equipment_id):
                    flash("This retired item still has upcoming approved reservations. "
                          "Review and cancel them below.", "warning")
                return redirect(url_for("equipment_detail", equipment_id=equipment_id))
    return render_equipment_form(item)


@app.route("/admin")
@require("admin")
def admin():
    labs = query("""
        SELECT l.lab_id, l.lab_name, l.building, l.room_no, COUNT(e.equipment_id) AS items
        FROM labs l LEFT JOIN equipment e ON e.lab_id = l.lab_id
        GROUP BY l.lab_id, l.lab_name, l.building, l.room_no
        ORDER BY l.lab_name
    """)
    categories = query("""
        SELECT c.category_id, c.category_name, COUNT(e.equipment_id) AS items
        FROM categories c LEFT JOIN equipment e ON e.category_id = c.category_id
        GROUP BY c.category_id, c.category_name
        ORDER BY c.category_name
    """)
    return render_template("admin.html", labs=labs, categories=categories)


@app.post("/admin/labs")
@require("admin")
def add_lab():
    values = [request.form[k].strip() for k in ("lab_name", "building", "room_no")]
    if not all(values):
        flash("Lab name, building and room number are required.", "error")
    else:
        try:
            execute("INSERT INTO labs (lab_name, building, room_no) VALUES (%s, %s, %s)", values)
            flash("Laboratory added.", "success")
        except mysql.connector.IntegrityError:
            flash("A laboratory already exists at that building and room.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/categories")
@require("admin")
def add_category():
    name = request.form["category_name"].strip()
    if not name:
        flash("Category name is required.", "error")
    else:
        try:
            execute("INSERT INTO categories (category_name) VALUES (%s)", (name,))
            flash("Category added.", "success")
        except mysql.connector.IntegrityError:
            flash("That category already exists.", "error")
    return redirect(url_for("admin"))


@app.post("/reservations")
@require()
def reservation_create():
    equipment_id = request.form.get("equipment_id", type=int)
    start = parse_datetime(request.form.get("start_time"))
    end = parse_datetime(request.form.get("end_time"))
    purpose = request.form.get("purpose", "").strip()
    error = validate_slot(start, end, datetime.now())
    if not error and not purpose:
        error = "Please describe the purpose of the reservation."
    if not error:
        cur = db().cursor(dictionary=True)
        try:
            error = booking_problem(cur, equipment_id, start, end)
        finally:
            cur.close()
    if error:
        flash(error, "error")
    else:
        execute("INSERT INTO reservations (equipment_id, user_id, start_time, end_time, purpose) "
                "VALUES (%s, %s, %s, %s, %s)", (equipment_id, g.user["user_id"], start, end, purpose[:255]))
        flash("Reservation requested. Lab staff will review it.", "success")
        return redirect(url_for("reservations"))
    if equipment_id:
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))
    return redirect(url_for("equipment_list"))


@app.route("/reservations")
@require()
def reservations():
    base = """
        SELECT r.*, e.equipment_name, e.asset_tag, u.name AS requester, u.email, u.department,
               rv.name AS reviewer, r.end_time <= NOW() AS has_ended
        FROM reservations r
        JOIN equipment e ON e.equipment_id = r.equipment_id
        JOIN users u ON u.user_id = r.user_id
        LEFT JOIN users rv ON rv.user_id = r.reviewed_by
    """
    mine = query(base + " WHERE r.user_id = %s ORDER BY r.start_time DESC", (g.user["user_id"],))
    pending = approved = []
    if g.user["role"] in STAFF:
        pending = query(base + " WHERE r.status = 'pending' ORDER BY r.start_time")
        approved = query(base + " WHERE r.status = 'approved' ORDER BY r.start_time")
    return render_template("reservations.html", mine=mine, pending=pending, approved=approved)


def get_reservation(reservation_id):
    res = query("SELECT * FROM reservations WHERE reservation_id = %s", (reservation_id,), one=True)
    if res is None:
        abort(404)
    return res


@app.post("/reservations/<int:reservation_id>/approve")
@require(*STAFF)
def reservation_approve(reservation_id):
    conn = db()
    cur = conn.cursor(dictionary=True)
    try:
        # The final checks and the update run in one transaction; FOR UPDATE locks the reservation and
        # equipment rows so two staff members cannot approve overlapping requests at the same time.
        conn.start_transaction()
        cur.execute("SELECT * FROM reservations WHERE reservation_id = %s FOR UPDATE", (reservation_id,))
        res = cur.fetchone()
        if res is None or res["status"] != "pending":
            error = "Only pending requests can be approved."
        elif res["user_id"] == g.user["user_id"]:
            error = "You cannot approve your own request."
        else:
            error = (validate_slot(res["start_time"], res["end_time"], datetime.now())
                     or booking_problem(cur, res["equipment_id"], res["start_time"], res["end_time"]))
        if error:
            conn.rollback()
            flash(error, "error")
        else:
            cur.execute("UPDATE reservations SET status = 'approved', reviewed_by = %s WHERE reservation_id = %s",
                        (g.user["user_id"], reservation_id))
            conn.commit()
            flash("Reservation approved.", "success")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    return redirect(url_for("reservations"))


@app.post("/reservations/<int:reservation_id>/reject")
@require(*STAFF)
def reservation_reject(reservation_id):
    res = get_reservation(reservation_id)
    if res["status"] != "pending":
        flash("Only pending requests can be rejected.", "error")
    elif res["user_id"] == g.user["user_id"]:
        flash("You cannot review your own request.", "error")
    else:
        execute("UPDATE reservations SET status = 'rejected', reviewed_by = %s "
                "WHERE reservation_id = %s AND status = 'pending'", (g.user["user_id"], reservation_id))
        flash("Reservation rejected.", "success")
    return redirect(url_for("reservations"))


@app.post("/reservations/<int:reservation_id>/cancel")
@require()
def reservation_cancel(reservation_id):
    res = get_reservation(reservation_id)
    if res["user_id"] != g.user["user_id"] and g.user["role"] not in STAFF:
        abort(403)
    if res["status"] not in ("pending", "approved"):
        flash("Only pending or approved reservations can be cancelled.", "error")
    elif res["end_time"] <= datetime.now():
        flash("This reservation has already ended; staff can mark it as completed instead.", "error")
    else:
        execute("UPDATE reservations SET status = 'cancelled' "
                "WHERE reservation_id = %s AND status IN ('pending', 'approved')", (reservation_id,))
        flash("Reservation cancelled.", "success")
    return go_back(url_for("reservations"))


@app.post("/reservations/<int:reservation_id>/complete")
@require(*STAFF)
def reservation_complete(reservation_id):
    res = get_reservation(reservation_id)
    if res["status"] != "approved":
        flash("Only approved reservations can be completed.", "error")
    elif res["end_time"] > datetime.now():
        flash("A reservation can be completed only after its end time.", "error")
    else:
        execute("UPDATE reservations SET status = 'completed' "
                "WHERE reservation_id = %s AND status = 'approved'", (reservation_id,))
        flash("Reservation marked as completed.", "success")
    return redirect(url_for("reservations"))


@app.route("/maintenance")
@require(*STAFF)
def maintenance():
    status = request.args.get("status", "")
    sql = """
        SELECT m.*, e.equipment_name, e.asset_tag, rep.name AS reporter, h.name AS handler
        FROM maintenance_records m
        JOIN equipment e ON e.equipment_id = m.equipment_id
        JOIN users rep ON rep.user_id = m.reported_by
        LEFT JOIN users h ON h.user_id = m.handled_by
    """
    if status in MAINTENANCE_ORDER:
        records = query(sql + " WHERE m.status = %s ORDER BY m.reported_at DESC", (status,))
    else:
        records = query(sql + " ORDER BY m.status = 'resolved', m.reported_at DESC")
    equipment = query("SELECT equipment_id, equipment_name, asset_tag FROM equipment ORDER BY equipment_name")
    return render_template("maintenance.html", records=records, equipment=equipment, status=status,
                           order=MAINTENANCE_ORDER)


@app.post("/maintenance")
@require(*STAFF)
def maintenance_report():
    equipment_id = request.form.get("equipment_id", type=int)
    issue = request.form.get("issue", "").strip()
    if not equipment_id or not issue:
        flash("Choose the equipment and describe the issue.", "error")
        return go_back(url_for("maintenance"))
    try:
        execute("INSERT INTO maintenance_records (equipment_id, reported_by, issue) VALUES (%s, %s, %s)",
                (equipment_id, g.user["user_id"], issue))
    except mysql.connector.IntegrityError:
        flash("Unknown equipment.", "error")
        return redirect(url_for("maintenance"))
    flash("Maintenance issue recorded. The item cannot be booked until it is resolved.", "success")
    affected = upcoming_approved_count(equipment_id)
    if affected:
        flash(f"Warning: this item has {affected} upcoming approved reservation(s). "
              "Review them below and cancel any that are affected.", "warning")
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))
    return go_back(url_for("maintenance"))


@app.post("/maintenance/<int:maintenance_id>/update")
@require(*STAFF)
def maintenance_update(maintenance_id):
    record = query("SELECT status, action_taken FROM maintenance_records WHERE maintenance_id = %s",
                   (maintenance_id,), one=True)
    if record is None:
        abort(404)
    new_status = request.form.get("status")
    action = request.form.get("action_taken", "").strip() or record["action_taken"]
    if not maintenance_step_allowed(record["status"], new_status):
        flash("Maintenance records can only move forward: open → in progress → resolved.", "error")
    elif new_status == "resolved" and not action:
        flash("Describe the action taken before resolving the record.", "error")
    else:
        execute("UPDATE maintenance_records SET status = %s, action_taken = %s, handled_by = %s, "
                "resolved_at = IF(%s = 'resolved', NOW(), NULL) WHERE maintenance_id = %s",
                (new_status, action, g.user["user_id"], new_status, maintenance_id))
        flash("Maintenance record updated.", "success")
    return redirect(url_for("maintenance"))


@app.route("/reports")
@require(*STAFF)
def reports():
    sql = load_reports()
    selected = request.args.get("equipment", type=int)
    history = []
    if selected:
        execute("SET @equipment_id = %s", (selected,))
        history = query(sql["maintenance_history"])
    return render_template(
        "reports.html",
        by_lab=query(sql["equipment_by_lab_category"]),
        by_requester=query(sql["reservations_by_requester"]),
        popular=query(sql["most_reserved"]),
        under_maintenance=query(sql["under_maintenance"]),
        pending=query(sql["pending_requests"]),
        history=history, selected=selected,
        equipment=query("SELECT equipment_id, equipment_name, asset_tag FROM equipment ORDER BY equipment_name"),
    )


if __name__ == "__main__":
    app.run(debug=True)
