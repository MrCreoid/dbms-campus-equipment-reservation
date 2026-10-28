"""Load fictional demo data. Safe to re-run: it does nothing if users already exist.
To start over, re-import schema.sql (which drops the tables) and run this again."""
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from db import get_connection

USERS = [
    # name, email, password, department, role  (local demo credentials only)
    ("Asha Nair", "admin@campus.test", "admin12345", "Lab Administration", "admin"),
    ("Ravi Deshmukh", "staff@campus.test", "staff12345", "Physics", "lab_staff"),
    ("Meera Iyer", "meera.staff@campus.test", "staff12345", "Electronics", "lab_staff"),
    ("Aarav Sharma", "student@campus.test", "student12345", "Computer Science", "student"),
    ("Ananya Rao", "ananya@campus.test", "student12345", "Electronics", "student"),
    ("Karan Mehta", "karan@campus.test", "student12345", "Physics", "student"),
]
LABS = [
    ("Physics Lab 1", "Science Block", "S-101"),
    ("Electronics Lab", "Engineering Block", "E-204"),
    ("Computing Lab", "Engineering Block", "E-310"),
    ("Optics Lab", "Science Block", "S-115"),
]
CATEGORIES = ["Measuring Instruments", "Electronics Equipment", "Computing Equipment", "Optical Instruments"]
EQUIPMENT = [
    # asset_tag, name, category no., lab no., details, purchase_date, status  (numbers are 1-based list positions)
    ("PHY-OSC-001", "Digital Oscilloscope", 1, 1, "100 MHz, 2-channel", "2021-07-12", "active"),
    ("PHY-OSC-002", "Digital Oscilloscope", 1, 1, "100 MHz, 2-channel", "2021-07-12", "active"),
    ("PHY-MM-001", "Digital Multimeter", 1, 1, None, "2019-03-02", "active"),
    ("ELE-FG-001", "Function Generator", 2, 2, "Up to 20 MHz sine/square", "2020-01-20", "active"),
    ("ELE-PS-001", "DC Power Supply", 2, 2, "0-30 V, 0-5 A", "2018-08-15", "active"),
    ("ELE-SS-001", "Soldering Station", 2, 2, None, "2016-05-10", "retired"),
    ("CMP-GPU-001", "GPU Workstation", 3, 3, "Shared deep-learning workstation", "2023-02-01", "active"),
    ("CMP-RPI-001", "Raspberry Pi Kit", 3, 3, "Board, sensors and breadboard", "2022-09-05", "active"),
    ("OPT-SPC-001", "Spectrometer", 4, 4, "Visible range", "2020-11-30", "active"),
    ("OPT-LSR-001", "He-Ne Laser Kit", 4, 4, "Class 2 laser, use goggles", "2019-12-01", "active"),
]


def main():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0]:
            print("Database already has users; skipping seed. Re-import schema.sql to start fresh.")
            return

        conn.start_transaction()
        user_ids = {}
        for name, email, password, department, role in USERS:
            cur.execute("INSERT INTO users (name, email, password_hash, department, role) VALUES (%s, %s, %s, %s, %s)",
                        (name, email, generate_password_hash(password), department, role))
            user_ids[email] = cur.lastrowid
        lab_ids, category_ids, equipment_ids = [], [], []
        for lab in LABS:
            cur.execute("INSERT INTO labs (lab_name, building, room_no) VALUES (%s, %s, %s)", lab)
            lab_ids.append(cur.lastrowid)
        for category in CATEGORIES:
            cur.execute("INSERT INTO categories (category_name) VALUES (%s)", (category,))
            category_ids.append(cur.lastrowid)
        for tag, name, cat, lab, details, bought, status in EQUIPMENT:
            cur.execute("INSERT INTO equipment (asset_tag, equipment_name, category_id, lab_id, details, "
                        "purchase_date, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (tag, name, category_ids[cat - 1], lab_ids[lab - 1], details, bought, status))
            equipment_ids.append(cur.lastrowid)

        eq = dict(zip([e[0] for e in EQUIPMENT], equipment_ids))
        aarav, ananya, karan = user_ids["student@campus.test"], user_ids["ananya@campus.test"], user_ids["karan@campus.test"]
        staff = user_ids["staff@campus.test"]
        base = datetime.now().replace(minute=0, second=0, microsecond=0)

        def slot(days, hour, hours=2):
            start = base.replace(hour=hour) + timedelta(days=days)
            return start, start + timedelta(hours=hours)

        reservations = [
            # equipment, requester, slot, purpose, status, reviewer
            ("PHY-OSC-001", aarav, slot(2, 10), "Signals lab assignment", "approved", staff),
            # Overlaps the approved booking above, so approving it demonstrates the conflict check.
            ("PHY-OSC-001", ananya, slot(2, 11), "Waveform measurements", "pending", None),
            ("PHY-OSC-002", ananya, slot(2, 11), "Waveform measurements", "pending", None),
            ("CMP-GPU-001", karan, slot(3, 14, 4), "Model training for mini project", "pending", None),
            ("ELE-FG-001", aarav, slot(4, 9), "Filter frequency response", "approved", staff),
            ("OPT-SPC-001", karan, slot(-5, 10), "Emission spectra experiment", "completed", staff),
            ("CMP-RPI-001", aarav, slot(-3, 13), "IoT sensor prototype", "completed", staff),
            ("CMP-RPI-001", ananya, slot(-2, 15), "Duplicate request", "rejected", staff),
            ("PHY-MM-001", karan, slot(1, 16), "Circuit debugging", "cancelled", None),
        ]
        for tag, requester, (start, end), purpose, status, reviewer in reservations:
            cur.execute("INSERT INTO reservations (equipment_id, user_id, start_time, end_time, purpose, status, "
                        "reviewed_by) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (eq[tag], requester, start, end, purpose, status, reviewer))

        meera = user_ids["meera.staff@campus.test"]
        maintenance = [
            # equipment, reporter, issue, action, status, handler, reported days ago, resolved days ago
            ("OPT-SPC-001", staff, "Calibration drift on the red end", "Recalibrated with mercury lamp",
             "resolved", meera, 20, 18),
            ("ELE-PS-001", meera, "Output voltage fluctuates under load", None, "open", None, 1, None),
            ("OPT-LSR-001", staff, "Laser output weak", "Replacement tube ordered", "in_progress", meera, 4, None),
        ]
        for tag, reporter, issue, action, status, handler, reported, resolved in maintenance:
            cur.execute("INSERT INTO maintenance_records (equipment_id, reported_by, issue, action_taken, status, "
                        "handled_by, reported_at, resolved_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (eq[tag], reporter, issue, action, status, handler, base - timedelta(days=reported),
                         base - timedelta(days=resolved) if resolved else None))
        conn.commit()
        print("Seeded demo data. Log in with admin@campus.test / admin12345 (see README for all accounts).")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
