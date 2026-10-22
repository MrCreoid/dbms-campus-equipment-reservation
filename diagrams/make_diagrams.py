"""Generates every SVG diagram used in the study guide. Run: python diagrams/make_diagrams.py"""
import math
import os
from xml.sax.saxutils import escape

OUT = os.path.dirname(os.path.abspath(__file__))
SANS = "Avenir Next, Helvetica Neue, Arial, sans-serif"
MONO = "Menlo, Consolas, monospace"
INK, MUTED, LINE, BG = "#1f2933", "#5b6775", "#c9d0d8", "#f6f7f9"
NAVY = "#1f3a4d"
# Entity colours (also used by the guide's CSS)
ENT = {
    "users": ("#2f5d7c", "#e6eef4"),
    "labs": ("#3d7a5a", "#e6f1ea"),
    "categories": ("#6b5591", "#eeeaf5"),
    "equipment": ("#a8641f", "#f8eee2"),
    "reservations": ("#2b7a78", "#e3f2f1"),
    "maintenance_records": ("#a33a3a", "#f7e6e6"),
}
STATE = {
    "pending": ("#8a6212", "#fbf0d9"), "approved": ("#2b6a3a", "#e3f1e6"), "rejected": ("#8a2f2f", "#f7e2e2"),
    "cancelled": ("#4a5561", "#eceff2"), "completed": ("#2f5d7c", "#e2ebf3"),
    "open": ("#8a2f2f", "#f7e2e2"), "in_progress": ("#8a6212", "#fbf0d9"), "resolved": ("#2b6a3a", "#e3f1e6"),
}
PY = ("#2f5d7c", "#e6eef4")   # Python steps
SQL = ("#a8641f", "#f8eee2")  # MySQL steps
OK = ("#2b6a3a", "#e3f1e6")
BAD = ("#8a2f2f", "#f7e2e2")
NEUTRAL = ("#4a5561", "#eef0f3")


class SVG:
    def __init__(self, w, h):
        self.w, self.h, self.el = w, h, []

    def add(self, s):
        self.el.append(s)

    def rect(self, x, y, w, h, fill="#fff", stroke=LINE, r=6, sw=1.2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=12, weight=400, fill=INK, anchor="start", family=SANS, italic=False):
        it = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{fill}" text-anchor="{anchor}" xml:space="preserve"{it}>{escape(s)}</text>')

    def lines(self, x, y, items, size=12, lh=None, **kw):
        lh = lh or size * 1.35
        for i, s in enumerate(items):
            self.text(x, y + i * lh, s, size, **kw)

    def box(self, x, y, w, h, title=None, body=(), colors=NEUTRAL, size=12, mono_body=False, r=8, title_size=None):
        """Coloured box with a bold title and centred body lines."""
        stroke, fill = colors
        self.rect(x, y, w, h, fill, stroke, r, 1.4)
        n = (1 if title else 0) + len(body)
        lh = size * 1.35
        top = y + h / 2 - (n * lh) / 2 + size * 0.95
        cx = x + w / 2
        i = 0
        if title:
            self.text(cx, top, title, title_size or size + 1, 600, stroke, "middle")
            i = 1
        for s in body:
            self.text(cx, top + i * lh, s, size - (1 if mono_body else 0), 400, INK, "middle", MONO if mono_body else SANS)
            i += 1

    def pill(self, x, y, w, h, label, colors, size=12):
        stroke, fill = colors
        self.rect(x, y, w, h, fill, stroke, h / 2, 1.4)
        self.text(x + w / 2, y + h / 2 + size * 0.36, label, size, 600, stroke, "middle")

    def line(self, pts, color=MUTED, sw=1.4, dash=None, head=True, head_start=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.add(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{sw}"{d} stroke-linejoin="round"/>')
        if head:
            self._head(pts[-2], pts[-1], color)
        if head_start:
            self._head(pts[1], pts[0], color)

    def _head(self, a, b, color, size=8):
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        p1 = (b[0] - size * math.cos(ang - 0.42), b[1] - size * math.sin(ang - 0.42))
        p2 = (b[0] - size * math.cos(ang + 0.42), b[1] - size * math.sin(ang + 0.42))
        self.add(f'<polygon points="{b[0]},{b[1]} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" fill="{color}"/>')

    def label(self, x, y, s, size=11, fill=MUTED, bg="#fff", weight=500, anchor="middle", family=SANS):
        w = len(s) * size * (0.62 if family == MONO else 0.56) + 8
        x0 = x - w / 2 if anchor == "middle" else x - 4
        self.rect(x0, y - size, w, size * 1.45, bg, bg, 3, 0)
        self.text(x, y, s, size, weight, fill, anchor, family)

    def num(self, x, y, n, color=NAVY):
        self.add(f'<circle cx="{x}" cy="{y}" r="10" fill="{color}"/>')
        self.text(x, y + 4, str(n), 11, 700, "#fff", "middle")

    def save(self, name):
        body = "\n".join(self.el)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}">\n<rect width="100%" height="100%" fill="#fff"/>\n{body}\n</svg>\n')
        with open(os.path.join(OUT, name), "w") as f:
            f.write(svg)


def architecture():
    s = SVG(660, 400)
    cols = [
        ("Browser", ["HTML from", "templates/", "+ style.css", "GET / POST"], NEUTRAL),
        ("Flask app", ["app.py", "routes, @require", "validate_slot()", "booking_problem()", "render_template()"], PY),
        ("Connector", ["db.py", "get_connection()", "mysql-connector", "-python cursors", "%s parameters"], ("#6b5591", "#eeeaf5")),
        ("MySQL 8", ["campus_equipment", "6 InnoDB tables", "PK / FK / UNIQUE", "CHECK constraints", "row locks"], SQL),
    ]
    xs = [10, 180, 350, 520]
    w = 130
    for x, (t, body, c) in zip(xs, cols):
        s.box(x, 70, w, 150, t, body, c, 12)
    s.text(10, 30, "User", 13, 600, INK)
    s.text(10, 48, "student / lab_staff / admin clicks and submits forms", 11, 400, MUTED)
    labels_fwd = ["HTTP", "call", "SQL"]
    labels_back = ["HTML", "dicts", "rows"]
    for i in range(3):
        a, b = xs[i] + w, xs[i + 1]
        mid = (a + b) / 2
        s.line([(a + 2, 120), (b - 2, 120)], NAVY)
        s.line([(b - 2, 175), (a + 2, 175)], MUTED, dash="4 3")
        s.text(mid, 110, labels_fwd[i], 9.5, 600, NAVY, "middle")
        s.text(mid, 194, labels_back[i], 9.5, 500, MUTED, "middle")
    bands = [("Presentation", 10, 130, NEUTRAL), ("Application logic", 180, 130, PY),
             ("Data access", 350, 130, ("#6b5591", "#eeeaf5")), ("Database", 520, 130, SQL)]
    for t, x, w2, c in bands:
        s.rect(x, 240, w2, 30, c[1], c[1], 4, 0)
        s.text(x + w2 / 2, 260, t, 10.5, 600, c[0], "middle")
    s.rect(10, 290, 640, 100, BG, LINE, 8)
    s.text(24, 312, "Example: a student submits the reservation form", 12, 600, INK)
    steps = ["1  Browser POSTs /reservations with equipment_id, start_time, end_time, purpose",
             "2  app.py runs validate_slot(), then booking_problem() queries through a cursor",
             "3  MySQL answers: status, open maintenance count, overlapping approved count",
             "4  No problem → INSERT a 'pending' row; Flask flashes a message and redirects to /reservations"]
    s.lines(24, 334, steps, 11, 15.5, fill=INK)
    s.save("architecture.svg")


def file_flow():
    s = SVG(680, 420)
    s.box(250, 15, 180, 50, "Browser", ["user clicks / forms"], NEUTRAL, 12)
    s.box(250, 120, 180, 70, "app.py", ["routes, rules, SQL", "flask --app app run"], PY, 12)
    s.box(20, 110, 170, 90, "templates/ + static/", ["12 Jinja .html pages", "style.css"], NEUTRAL, 11)
    s.box(490, 110, 170, 90, "reports.sql", ["6 named report", "queries, loaded by", "load_reports()"], SQL, 11)
    s.box(250, 245, 180, 55, "db.py", ["get_connection()"], ("#6b5591", "#eeeaf5"), 12)
    s.box(20, 245, 170, 55, ".env", ["DB_* and SECRET_KEY"], NEUTRAL, 11)
    s.box(250, 345, 180, 60, "MySQL", ["campus_equipment"], SQL, 12)
    s.box(20, 345, 170, 60, "schema.sql", ["creates the 6 tables"], SQL, 11)
    s.box(490, 245, 170, 55, "seed.py", ["demo data"], PY, 11)
    s.box(490, 345, 170, 60, "tests/test_rules.py", ["unittest, no DB"], NEUTRAL, 11)
    s.line([(340, 65), (340, 118)], NAVY)
    s.text(348, 96, "HTTP", 10, 600, NAVY)
    s.line([(250, 155), (192, 155)], MUTED)
    s.text(221, 147, "renders", 9.5, 500, MUTED, "middle")
    s.line([(430, 155), (488, 155)], MUTED)
    s.text(459, 147, "reads", 9.5, 500, MUTED, "middle")
    s.line([(340, 190), (340, 243)], MUTED)
    s.text(348, 222, "imports", 10, 500, MUTED)
    s.line([(250, 272), (192, 272)], MUTED)
    s.text(221, 264, "reads", 9.5, 500, MUTED, "middle")
    s.line([(340, 300), (340, 343)], SQL[0])
    s.text(348, 327, "SQL", 10, 600, SQL[0])
    s.line([(190, 375), (248, 375)], SQL[0])
    s.text(219, 367, "import", 9.5, 500, SQL[0], "middle")
    s.line([(490, 272), (432, 272)], MUTED)
    s.text(461, 264, "imports", 9.5, 500, MUTED, "middle")
    s.line([(660, 375), (672, 375), (672, 222), (415, 222), (415, 192)], MUTED, dash="4 3")
    s.label(560, 226, "tests import pure functions", 9.5, MUTED)
    s.save("file_flow.svg")


def entity(s, x, y, w, name, attrs, row=19):
    stroke, fill = ENT[name]
    h = 30 + row * len(attrs) + 6
    s.rect(x, y, w, h, "#fff", stroke, 6, 1.6)
    s.add(f'<path d="M{x},{y + 30} L{x},{y + 6} Q{x},{y} {x + 6},{y} L{x + w - 6},{y} Q{x + w},{y} {x + w},{y + 6} L{x + w},{y + 30} Z" fill="{stroke}"/>')
    s.text(x + w / 2, y + 20, name.upper(), 12.5, 700, "#fff", "middle")
    for i, (col, tag) in enumerate(attrs):
        yy = y + 30 + 16 + i * row
        if i % 2 == 1:
            s.rect(x + 1, yy - 13, w - 2, row, fill, fill, 0, 0)
        bold = 700 if "PK" in tag else 400
        s.text(x + 10, yy, col, 11.5, bold, INK, family=MONO)
        if tag:
            s.text(x + w - 8, yy, tag, 9.5, 700, stroke, "end")
    return (x, y, w, h)


def crow(s, x, y, direction, kind, color=INK):
    """Draw a crow's-foot end marker at (x, y). direction: +1 line goes right from the entity edge, -1 left."""
    d = direction
    if kind in ("one", "zero_one"):
        s.add(f'<line x1="{x + d * 10}" y1="{y - 7}" x2="{x + d * 10}" y2="{y + 7}" stroke="{color}" stroke-width="1.6"/>')
    if kind == "one":
        s.add(f'<line x1="{x + d * 16}" y1="{y - 7}" x2="{x + d * 16}" y2="{y + 7}" stroke="{color}" stroke-width="1.6"/>')
    if kind == "zero_one":
        s.add(f'<circle cx="{x + d * 20}" cy="{y}" r="4.5" fill="#fff" stroke="{color}" stroke-width="1.5"/>')
    if kind == "zero_many":
        s.add(f'<line x1="{x}" y1="{y - 8}" x2="{x + d * 12}" y2="{y}" stroke="{color}" stroke-width="1.6"/>')
        s.add(f'<line x1="{x}" y1="{y + 8}" x2="{x + d * 12}" y2="{y}" stroke="{color}" stroke-width="1.6"/>')
        s.add(f'<circle cx="{x + d * 18}" cy="{y}" r="4.5" fill="#fff" stroke="{color}" stroke-width="1.5"/>')


def rel(s, a, b, kind_a, kind_b, label, color, mx, label_xy):
    """Orthogonal connector between two entity edges; each relationship gets its own vertical channel mx."""
    (x1, y1, d1), (x2, y2, d2) = a, b
    s.line([(x1, y1), (mx, y1), (mx, y2), (x2, y2)], color, 1.5, head=False)
    crow(s, x1, y1, d1, kind_a, color)
    crow(s, x2, y2, d2, kind_b, color)
    s.label(label_xy[0], label_xy[1], label, 10.5, color, weight=600)


def er_full():
    s = SVG(1140, 660)
    labs = entity(s, 20, 360, 200, "labs", [("lab_id", "PK"), ("lab_name", ""), ("building", "UQ1"), ("room_no", "UQ1")])
    cats = entity(s, 20, 90, 200, "categories", [("category_id", "PK"), ("category_name", "UQ")])
    eq = entity(s, 320, 160, 210, "equipment", [("equipment_id", "PK"), ("asset_tag", "UQ"), ("equipment_name", ""),
                                                ("category_id", "FK"), ("lab_id", "FK"), ("details", "N"),
                                                ("purchase_date", "N"), ("status", "")])
    res = entity(s, 620, 20, 220, "reservations", [("reservation_id", "PK"), ("equipment_id", "FK"), ("user_id", "FK"),
                                                   ("start_time", ""), ("end_time", ""), ("purpose", ""), ("status", ""),
                                                   ("reviewed_by", "FK, N"), ("created_at", "")])
    mnt = entity(s, 620, 300, 220, "maintenance_records", [("maintenance_id", "PK"), ("equipment_id", "FK"),
                                                           ("reported_by", "FK"), ("issue", ""), ("action_taken", "N"),
                                                           ("status", ""), ("handled_by", "FK, N"), ("reported_at", ""),
                                                           ("resolved_at", "N")])
    usr = entity(s, 945, 180, 180, "users", [("user_id", "PK"), ("name", ""), ("email", "UQ"), ("password_hash", ""),
                                             ("department", ""), ("role", ""), ("created_at", "")])
    row = lambda e, i: e[1] + 30 + 16 + i * 19 - 4  # y of attribute row i
    L, C, E, U = ENT["labs"][0], ENT["categories"][0], ENT["equipment"][0], ENT["users"][0]
    rel(s, (220, row(labs, 0), 1), (320, row(eq, 4), -1), "one", "zero_many", "contains", L, 285, (285, 420))
    rel(s, (220, row(cats, 0), 1), (320, row(eq, 3), -1), "one", "zero_many", "classifies", C, 255, (255, 200))
    rel(s, (530, row(eq, 0) - 5, 1), (620, row(res, 1), -1), "one", "zero_many", "booked in", E, 565, (565, 150))
    rel(s, (530, row(eq, 0) + 5, 1), (620, row(mnt, 1), -1), "one", "zero_many", "has", E, 590, (590, 300))
    rel(s, (945, row(usr, 0) - 5, -1), (840, row(res, 2), 1), "one", "zero_many", "requests", U, 915, (915, 160))
    rel(s, (945, row(usr, 0) + 5, -1), (840, row(res, 7), 1), "zero_one", "zero_many", "reviews", U, 882, (861, 216))
    rel(s, (945, row(usr, 5) - 5, -1), (840, row(mnt, 2), 1), "one", "zero_many", "reports", U, 870, (870, 360))
    rel(s, (945, row(usr, 5) + 5, -1), (840, row(mnt, 6), 1), "zero_one", "zero_many", "handles", U, 905, (905, 420))
    # legend
    lx, ly = 20, 520
    s.rect(lx, ly, 560, 125, BG, LINE, 8)
    s.text(lx + 14, ly + 22, "Legend (crow's-foot notation)", 12, 600, INK)
    items = [("one", "exactly one (mandatory)"), ("zero_one", "zero or one (nullable FK)"), ("zero_many", "zero or many")]
    for i, (k, t) in enumerate(items):
        yy = ly + 48 + i * 24
        s.add(f'<line x1="{lx + 20}" y1="{yy}" x2="{lx + 70}" y2="{yy}" stroke="{INK}" stroke-width="1.5"/>')
        crow(s, lx + 70, yy, -1, k)
        s.text(lx + 85, yy + 4, t, 11, 400, INK)
    tags = [("PK", "primary key"), ("FK", "foreign key"), ("UQ", "UNIQUE (UQ1 = composite unique pair)"), ("N", "nullable column")]
    for i, (t, d) in enumerate(tags):
        yy = ly + 48 + i * 19
        s.text(lx + 300, yy + 4, t, 10, 700, ENT["users"][0])
        s.text(lx + 335, yy + 4, d, 11, 400, INK)
    s.text(620, 600, "All eight relationships are one-to-many. Every foreign key uses ON DELETE RESTRICT,", 11, 400, MUTED)
    s.text(620, 617, "so referenced rows cannot be deleted while history points at them.", 11, 400, MUTED)
    s.save("er_diagram.svg")


def eer():
    s = SVG(680, 400)
    U = ENT["users"]
    s.box(240, 15, 200, 95, "USER", ["user_id (PK), name, email,", "password_hash, department,", "created_at, role"], U, 11.5)
    s.add(f'<circle cx="340" cy="165" r="18" fill="#fff" stroke="{U[0]}" stroke-width="1.6"/>')
    s.text(340, 171, "d", 15, 700, U[0], "middle")
    # double line = total participation
    s.add(f'<line x1="336" y1="110" x2="336" y2="147" stroke="{U[0]}" stroke-width="1.5"/>')
    s.add(f'<line x1="344" y1="110" x2="344" y2="147" stroke="{U[0]}" stroke-width="1.5"/>')
    subs = [("STUDENT", "role = 'student'", 60), ("LAB STAFF", "role = 'lab_staff'", 250), ("ADMIN", "role = 'admin'", 440)]
    s.line([(340, 183), (340, 203)], U[0], 1.5, head=False)
    s.line([(150, 203), (530, 203)], U[0], 1.5, head=False)
    for t, cond, x in subs:
        s.line([(x + 90, 203), (x + 90, 235)], U[0], 1.5, head=False)
        s.add(f'<path d="M{x + 82},{214} q8,9 16,0" fill="none" stroke="{U[0]}" stroke-width="1.6"/>')
        s.box(x, 235, 180, 55, t, [cond], (U[0], "#fff"), 12)
    s.rect(20, 310, 640, 80, BG, LINE, 8)
    s.lines(34, 333, ["d = disjoint (an account has exactly one role); double line = total (every account has a role).",
                      "Defining attribute: role. Subclasses have no extra attributes, so the relational schema",
                      "uses ONE users table with role ENUM('student','lab_staff','admin'), not three subtype tables."], 11.2, 17)
    s.save("eer_diagram.svg")


def login_flow():
    s = SVG(680, 470)
    s.text(20, 24, "Login: POST /login", 13, 700, NAVY)
    steps = [("Form sends email + password", PY), ("SELECT user_id, password_hash\nFROM users WHERE email = %s", SQL),
             ("check_password_hash(hash, password)", PY), ("session.clear(); session['user_id'] = id", PY),
             ("redirect to / (dashboard)", OK)]
    y = 40
    for i, (t, c) in enumerate(steps):
        parts = t.split("\n")
        h = 26 + 15 * len(parts)
        s.box(20, y, 300, h, None, parts, c, 11.5, mono_body=c in (SQL,) or "(" in t)
        if i < len(steps) - 1:
            s.line([(170, y + h), (170, y + h + 18)], MUTED)
        y += h + 18
    s.line([(320, 172), (345, 172), (345, 400), (320, 400)], BAD[0], dash="4 3", head=False)
    s.box(20, 380, 300, 40, None, ["no user / wrong password → flash 'Invalid email or password.'"], BAD, 10.5)
    s.text(350, 290, "no match", 10, 600, BAD[0])
    s.text(380, 24, "Every later request", 13, 700, NAVY)
    s.box(380, 40, 280, 62, "@app.before_request load_user()", ["g.user = SELECT ... FROM users", "WHERE user_id = session id"], PY, 11)
    s.line([(520, 102), (520, 122)], MUTED)
    s.box(380, 124, 280, 48, "@require(...roles) on the view", ["checks g.user and g.user['role']"], PY, 11)
    s.line([(520, 172), (520, 196)], MUTED)
    s.box(380, 198, 85, 70, None, ["not logged", "in → 302", "/login"], BAD, 10.5)
    s.box(477, 198, 85, 70, None, ["wrong", "role →", "abort(403)"], BAD, 10.5)
    s.box(574, 198, 86, 70, None, ["allowed →", "view runs"], OK, 10.5)
    s.rect(380, 290, 280, 130, BG, LINE, 8)
    s.lines(394, 312, ["Registration (POST /register)", "• checks fields, '@' in email, len ≥ 8",
                       "• generate_password_hash(password)", "• INSERT ... role = 'student' (fixed)",
                       "• duplicate email → IntegrityError", "  → 'account already exists'"], 11, 17.5)
    s.save("login_flow.svg")


def filters_flow():
    s = SVG(680, 250)
    s.box(10, 20, 190, 95, "GET /equipment", ["?q=osc", "&lab=1", "&category=1"], NEUTRAL, 11.5, mono_body=True)
    s.box(240, 20, 200, 95, "equipment_list()", ["builds conditions[]", "and params[] lists", "only for filters given"], PY, 11.5)
    s.box(480, 20, 190, 95, "MySQL", ["equipment JOIN", "categories JOIN labs", "+ 2 EXISTS subqueries"], SQL, 11.5)
    s.line([(200, 67), (238, 67)], NAVY)
    s.line([(440, 67), (478, 67)], NAVY)
    s.rect(10, 135, 660, 105, BG, LINE, 8)
    s.lines(24, 158, ["conditions = ['(e.equipment_name LIKE %s OR e.asset_tag LIKE %s)',",
                      "              'e.lab_id = %s', 'e.category_id = %s']",
                      "params     = ['%osc%', '%osc%', 1, 1]",
                      "where      = 'WHERE ' + ' AND '.join(conditions)   # only fixed text is joined",
                      "items      = query(sql_with_where, params)          # values bound by the driver"],
            10.5, 17, family=MONO)
    s.save("filters_flow.svg")


def reservation_lifecycle():
    s = SVG(680, 330)
    P = lambda name, x, y, w=120: s.pill(x, y, w, 36, name, STATE[name], 13)
    P("pending", 40, 140)
    P("approved", 290, 60)
    P("rejected", 290, 225)
    P("cancelled", 530, 140)
    P("completed", 530, 20)
    s.line([(160, 150), (288, 85)], STATE["approved"][0])
    s.label(215, 102, "staff approve", 10.5, STATE["approved"][0])
    s.line([(160, 168), (288, 238)], STATE["rejected"][0])
    s.label(218, 222, "staff reject", 10.5, STATE["rejected"][0])
    s.line([(410, 70), (528, 42)], STATE["completed"][0])
    s.label(470, 45, "staff complete", 10.5, STATE["completed"][0])
    s.line([(410, 88), (528, 150)], STATE["cancelled"][0])
    s.label(472, 128, "cancel", 10.5, STATE["cancelled"][0])
    s.line([(100, 176), (100, 290), (590, 290), (590, 178)], STATE["cancelled"][0])
    s.label(345, 294, "owner or staff cancels before the end time", 10.5, STATE["cancelled"][0])
    s.text(40, 128, "created by POST /reservations", 10.5, 500, MUTED)
    s.text(530, 78, "only after end_time", 10, 500, MUTED)
    s.text(425, 240, "final states keep the row", 10, 500, MUTED)
    s.text(425, 254, "(no DELETE anywhere)", 10, 500, MUTED)
    s.save("reservation_lifecycle.svg")


def reservation_submit():
    s = SVG(680, 420)
    s.box(170, 10, 280, 44, "POST /reservations", ["equipment_id, start_time, end_time, purpose"], NEUTRAL, 11)
    checks = [("validate_slot(start, end, now)", "missing, end ≤ start, or past", PY),
              ("purpose not empty", "'Please describe the purpose…'", PY),
              ("equipment.status = 'active' ?", "'…retired and cannot be booked'", SQL),
              ("unresolved maintenance = 0 ?", "'…unresolved maintenance issue'", SQL),
              ("overlapping APPROVED = 0 ?", "'…overlaps an approved reservation'", SQL)]
    y = 72
    s.line([(310, 54), (310, 70)], MUTED)
    for t, err, c in checks:
        s.box(170, y, 280, 40, None, [t], c, 11.5, mono_body=True)
        s.line([(450, y + 20), (473, y + 20)], BAD[0])
        s.box(475, y + 2, 200, 36, None, [err], BAD, 10)
        s.line([(310, y + 40), (310, y + 54)], OK[0])
        s.text(317, y + 51, "ok", 9.5, 600, OK[0])
        y += 56
    s.box(170, y, 280, 50, "INSERT INTO reservations", ["status defaults to 'pending'"], OK, 11.5)
    s.text(20, 90, "Python", 11, 700, PY[0])
    s.text(20, 106, "checks", 11, 700, PY[0])
    s.text(20, 205, "SQL checks in", 11, 700, SQL[0])
    s.text(20, 221, "booking_problem()", 11, 700, SQL[0], family=MONO)
    s.text(20, 380, "error → flash + back", 10.5, 500, BAD[0])
    s.text(20, 395, "to the item page", 10.5, 500, BAD[0])
    s.save("reservation_submit.svg")


def overlap_timeline():
    s = SVG(680, 420)
    x0, unit = 80, 160  # 1 hour = 160px, axis starts 09:30
    def tx(h): return x0 + (h - 9.5) * unit
    def axis(y):
        s.add(f'<line x1="{tx(9.5)}" y1="{y}" x2="{tx(12.75)}" y2="{y}" stroke="{LINE}" stroke-width="1"/>')
        for h in [10, 10.5, 11, 11.5, 12]:
            s.add(f'<line x1="{tx(h)}" y1="{y - 4}" x2="{tx(h)}" y2="{y + 4}" stroke="{MUTED}"/>')
            s.text(tx(h), y + 17, f"{int(h)}:{'30' if h % 1 else '00'}", 10.5, 500, MUTED, "middle")
    def bar(a, b, y, label, colors):
        s.rect(tx(a), y, tx(b) - tx(a), 26, colors[1], colors[0], 4, 1.4)
        s.text((tx(a) + tx(b)) / 2, y + 17, label, 11, 600, colors[0], "middle")
    s.text(20, 24, "Example 1 — conflict", 13, 700, BAD[0])
    bar(10, 11, 40, "approved 10:00–11:00", STATE["approved"])
    bar(10.5, 11.5, 74, "request 10:30–11:30", NEUTRAL)
    s.add(f'<rect x="{tx(10.5)}" y="36" width="{tx(11) - tx(10.5)}" height="68" fill="{BAD[0]}" fill-opacity="0.13"/>')
    s.text((tx(10.5) + tx(11)) / 2, 116, "overlap", 9.5, 700, BAD[0], "middle")
    axis(132)
    s.text(tx(11.55), 60, "10:00 < 11:30  ✓", 11, 500, INK, family=MONO)
    s.text(tx(11.55), 77, "11:00 > 10:30  ✓", 11, 500, INK, family=MONO)
    s.text(tx(11.55), 96, "both true → CONFLICT", 11, 700, BAD[0], family=MONO)
    s.text(20, 175, "Example 2 — touching slots", 13, 700, OK[0])
    bar(10, 11, 190, "approved 10:00–11:00", STATE["approved"])
    bar(11, 12, 224, "request 11:00–12:00", NEUTRAL)
    axis(268)
    s.text(tx(9.55), 238, "10:00 < 12:00  ✓", 11, 500, INK, family=MONO)
    s.text(tx(9.55), 255, "11:00 > 11:00  ✗", 11, 500, INK, family=MONO)
    s.text(tx(12.05), 214, "no conflict", 11, 700, OK[0], family=MONO)
    s.rect(20, 305, 640, 105, BG, LINE, 8)
    s.text(34, 328, "Rule used in booking_problem():", 12, 600, INK)
    s.text(34, 352, "existing.start_time < requested.end_time AND existing.end_time > requested.start_time", 11.2, 600,
           NAVY, family=MONO)
    s.lines(34, 376, ["Strict < and > mean intervals are half-open [start, end): a slot may start exactly when",
                      "another ends. Only rows with status = 'approved' are compared — pending requests never block."],
            11, 16)
    s.save("overlap_timeline.svg")


def race():
    s = SVG(680, 372)
    def lane(x, title, items, colors):
        s.text(x + 150, 52, title, 12, 700, colors[0], "middle")
        y = 64
        for t, c in items:
            s.box(x, y, 300, 34, None, [t], c, 10.5)
            y += 42
    s.text(20, 22, "Two staff approve overlapping requests A and B for the same item at the same moment", 12, 600, INK)
    lane(15, "Without FOR UPDATE (hypothetical)", [
        ("A: check overlaps → 0 found", PY), ("B: check overlaps → 0 found", PY),
        ("A: UPDATE A → approved, COMMIT", OK), ("B: UPDATE B → approved, COMMIT", OK),
        ("Result: two overlapping approved bookings", BAD)], NEUTRAL)
    lane(365, "Actual code: SELECT … FOR UPDATE", [
        ("A: lock equipment row, check → 0", PY), ("B: SELECT … FOR UPDATE → waits", SQL),
        ("A: UPDATE A → approved, COMMIT (lock freed)", OK), ("B: resumes, check → 1 overlap found", PY),
        ("B: ROLLBACK, flash overlap error", OK)], PY)
    s.add(f'<line x1="340" y1="45" x2="340" y2="275" stroke="{LINE}" stroke-dasharray="4 4"/>')
    s.rect(15, 290, 650, 72, BG, LINE, 8)
    s.lines(29, 312, ["Observed in this project's own test run: with the lock, exactly one of the two requests was",
                      "approved. When the lock was removed temporarily (and a 0.5 s pause added to widen the race",
                      "window), both were approved — the double booking above. The lock was then restored."], 11, 17)
    s.save("race_condition.svg")


def maintenance_lifecycle():
    s = SVG(680, 300)
    s.pill(30, 60, 130, 38, "open", STATE["open"], 13)
    s.pill(270, 60, 140, 38, "in_progress", STATE["in_progress"], 13)
    s.pill(520, 60, 130, 38, "resolved", STATE["resolved"], 13)
    s.line([(160, 79), (268, 79)], STATE["in_progress"][0])
    s.line([(410, 79), (518, 79)], STATE["resolved"][0])
    s.line([(95, 98), (95, 140), (585, 140), (585, 100)], STATE["resolved"][0])
    s.label(340, 144, "open → resolved directly is also allowed", 10.5, STATE["resolved"][0])
    s.text(95, 45, "INSERT by staff", 10.5, 500, MUTED, "middle")
    s.text(214, 70, "update", 10, 500, MUTED, "middle")
    s.text(464, 70, "update", 10, 500, MUTED, "middle")
    s.text(585, 45, "needs action_taken", 10.5, 500, MUTED, "middle")
    s.text(575, 122, "resolved_at = NOW()", 10, 500, MUTED, "end", MONO)
    s.box(30, 175, 300, 110, "While open or in_progress", ["• new requests refused", "• approvals refused",
                                                          "• existing approved bookings are only", "  flagged with a warning, not cancelled"],
          BAD, 11)
    s.box(350, 175, 300, 110, "Rules", ["maintenance_step_allowed(): forward only", "resolved records cannot change",
                                        "handled_by = the staff member who", "made the latest update"], NEUTRAL, 11)
    s.save("maintenance_lifecycle.svg")


def approval_sequence():
    LIFE = 800
    s = SVG(680, 810)
    cols = [("Staff browser", 95, NEUTRAL), ("Flask app.py", 310, PY), ("MySQL", 580, SQL)]
    for t, x, c in cols:
        s.box(x - 75, 10, 150, 36, None, [t], c, 12)
        s.add(f'<line x1="{x}" y1="46" x2="{x}" y2="{LIFE}" stroke="{LINE}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    B, F, M = 95, 310, 580
    y = [80]
    def msg(a, b, text, n, mono=False, back=False):
        yy = y[0]
        s.line([(a, yy), (b, yy)], MUTED if back else NAVY, 1.4, dash="4 3" if back else None)
        s.label((a + b) / 2, yy - 6, text, 10, MUTED if back else NAVY, family=MONO if mono else SANS)
        s.num(a - 16 if b > a else a + 16, yy, n)
        y[0] += 44
    def note(x, w, lines, c):
        yy = y[0] - 18
        h = 14 * len(lines) + 12
        s.rect(x - w / 2, yy, w, h, c[1], c[0], 6, 1.2)
        s.lines(x - w / 2 + 8, yy + 17, lines, 10, 14, family=MONO)
        y[0] += h + 12
    msg(B, F, "GET /reservations", 1)
    note(F, 250, ["load_user(): SELECT user by session", "@require(*STAFF): role ok?"], PY)
    msg(F, M, "SELECT r.*, … WHERE status='pending'", 2, True)
    msg(M, F, "pending rows (+ requester, equipment)", 3, back=True)
    msg(F, B, "render reservations.html", 4, back=True)
    msg(B, F, "POST /reservations/3/approve", 5)
    note(F, 250, ["@require(*STAFF) again", "conn.start_transaction()"], PY)
    msg(F, M, "SELECT * FROM reservations … FOR UPDATE", 6, True)
    note(F, 250, ["status == 'pending'?", "requester != current user?", "validate_slot(start, end, now)"], PY)
    msg(F, M, "SELECT status FROM equipment … FOR UPDATE", 7, True)
    msg(F, M, "COUNT unresolved maintenance", 8, True)
    msg(F, M, "COUNT overlapping approved", 9, True)
    note(F, 250, ["any error: conn.rollback()", "           flash(error)"], BAD)
    msg(F, M, "UPDATE … status='approved', reviewed_by", 10, True)
    msg(F, M, "COMMIT  (locks released)", 11, True)
    msg(F, B, "302 redirect + flash 'Reservation approved.'", 12, back=True)
    s.save("approval_sequence.svg")
    return y[0]


def cheat_tables():
    s = SVG(680, 262)
    pos = {"users": (480, 110), "labs": (20, 30), "categories": (20, 190), "equipment": (200, 110),
           "reservations": (330, 20), "maintenance_records": (330, 205)}
    w, h = 150, 52
    for n, (x, y) in pos.items():
        ww = 180 if n == "maintenance_records" else w
        s.box(x, y, ww, h, n, [], (ENT[n][0], ENT[n][1]), 12)
    s.line([(170, 56), (200, 120)], INK)
    s.line([(170, 216), (200, 150)], INK)
    s.line([(350, 125), (380, 74)], INK)
    s.line([(350, 150), (380, 203)], INK)
    s.line([(520, 110), (450, 74)], INK)
    s.line([(520, 162), (480, 203)], INK)
    for x, y, t in [(185, 80, "1:N"), (185, 195, "1:N"), (372, 100, "1:N"), (372, 185, "1:N"),
                    (520, 84, "1:N ×2"), (535, 188, "1:N ×2")]:
        s.label(x, y, t, 10, NAVY, weight=700)
    s.save("cheat_tables.svg")


if __name__ == "__main__":
    for f in [architecture, file_flow, er_full, eer, login_flow, filters_flow, reservation_lifecycle,
              reservation_submit, overlap_timeline, race, maintenance_lifecycle, approval_sequence, cheat_tables]:
        f()
    print("diagrams written to", OUT)
