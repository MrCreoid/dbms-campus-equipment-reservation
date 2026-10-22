# Feasibility Report: Campus Equipment & Lab Instrument Reservation with Maintenance Ledger

**Verdict: highly feasible as an undergraduate DBMS project, and already built and tested.**
The idea is a good fit because the hard parts (preventing double booking, keeping history, deriving availability)
are database problems, so the project shows real DBMS reasoning rather than just CRUD screens.

## 1. Technical feasibility: high

| Question | Assessment |
|----------|-----------|
| Does the stack fit? | Yes. Flask + MySQL + Jinja runs on any laptop with free software. There are 3 Python dependencies, no build step and no external services. |
| Is the hardest requirement solvable simply? | Yes. Overlap prevention is one SQL condition, and race-safety is a transaction with `SELECT … FOR UPDATE`. This was tested: two staff approving overlapping requests at the same instant gives exactly one approval. With the lock removed, the same test produced a double booking, so the lock is genuinely needed and genuinely works. |
| Can it stay within six tables? | Yes. Every requirement maps to the six entities with no extra tables, and the schema is in 3NF (also BCNF). |
| Risky areas | Time zones (solved by storing local `DATETIME` with app and DB on one machine) and MySQL setup on Windows (covered in the README's error table). |

## 2. Scope and effort feasibility: high

The finished project is about 1,750 lines in total, nearly half of it HTML templates and CSS:

| Part | Size |
|------|------|
| `app.py` (all routes and rules) | ~630 lines |
| `schema.sql` + `reports.sql` | ~165 lines |
| `seed.py` | ~120 lines |
| Templates + CSS | ~770 lines |

A team of 3–4 could build this from scratch in **3–4 weeks** part-time. A sensible split:

1. Schema, constraints, ER/EER diagram, normalization write-up.
2. Auth, roles, equipment and admin pages.
3. Reservation workflow and approval transaction.
4. Maintenance ledger, reports, seed data, testing.

## 3. Academic feasibility (DBMS syllabus coverage): strong

The project uses each concept for a reason, not just for show:

- **Keys and constraints:** PK, FK with deliberate `RESTRICT`, `UNIQUE` (including the composite lab location), `CHECK` (time order, resolution date consistency), `ENUM`.
- **Normalization:** clear 1NF→3NF argument, and derived availability instead of a redundant `is_available` flag.
- **Queries:** INNER/LEFT JOIN, GROUP BY with conditional aggregation, `EXISTS` subqueries, all in `reports.sql`, which the app runs directly.
- **Transactions and concurrency:** the approval transaction is the strongest viva topic in the project.
- **ER/EER:** eight 1:N relationships, two of them with optional participation (nullable FKs), plus a disjoint, total User specialization.

Likely viva questions the design answers well: *Why not store availability? Why RESTRICT instead of CASCADE? What
happens if two staff approve at once? Why is department not a table? Why one users table for three roles?*

## 4. Operational feasibility: good for a demo, limited for real deployment

It works well as a local, single-college demo. Before a real campus deployment, it would need:

- CSRF tokens on forms (currently it relies on `SameSite=Lax` cookies, which is enough locally),
- HTTPS and a production WSGI server instead of `flask run`,
- a password-reset flow and a way for admins to create staff accounts in the UI,
- email notifications for approvals (deliberately out of scope).

None of these affect the DBMS evaluation.

## 5. Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Team members can't run MySQL locally | Medium | README covers macOS/Windows setup and common errors; the schema also runs in MySQL Workbench. |
| Demo data gets messy before the viva | Medium | Re-import `schema.sql`, then run `seed.py` (about 5 seconds). |
| Examiner asks for more DBMS features (triggers/views) | Low–medium | Explain that they were not needed. If one is required, a view over the `under_maintenance` query is the natural candidate. |
| Seeded slots are relative to "now" | Low | Re-seed shortly before the demo so the "upcoming" bookings are still in the future. |

## 6. Verification performed

- 7/7 unit tests (`python -m unittest discover tests`).
- 82/82 end-to-end checks against a real MySQL 8.4 server through every route: role restrictions, all booking rules, approval, rejection, cancellation, completion, maintenance lifecycle, admin inventory, history preservation and concurrent approval.
- Direct SQL checks that MySQL itself rejects a bad time range, deleting referenced equipment/labs, an inconsistent resolved record, a duplicate lab location and an invalid role.
- Visual check of the UI at laptop and phone widths.
