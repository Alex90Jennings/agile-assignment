# eSIM Admin Dashboard

A Flask web application for managing eSIMs, subscriptions, users and businesses, with role-based access, an admin approval workflow and 384 automated tests.

**Live demo:** [agile-assignment.onrender.com](https://agile-assignment.onrender.com) · **Repository:** [github.com/Alex90Jennings/agile-assignment](https://github.com/Alex90Jennings/agile-assignment)

> The live demo is on Render's free tier, so the first request after a quiet spell takes about 50 seconds to wake the service up. After that it is fast.

![The dashboard in use: signing in, the admin portal with pending requests, users, businesses, the add-user form, and a regular user's dashboard](docs/demo.gif)

---

## The story

This was my first Python project.

It was built for **Software Engineering and Agile (QAC020N227S)**, a Level 5, 20-credit module on my digital and technology solutions degree apprenticeship. The brief asked for a non-trivial web database application, built with an Agile approach and backed by a written report.

I chose eSIM and subscription management because it is the domain I work in, so I already understood the workflow: businesses have users, users hold eSIM profiles, and each eSIM carries connectivity subscriptions. Coming from JavaScript, the interesting part was learning how Python and Flask do things: blueprints instead of routers, SQLAlchemy models instead of hand-written SQL, decorators for access control, and pytest for testing.

The features that taught me the most were the ones the brief did not ask for: an admin confirmation gate for self-registered users, request-and-approve flows for eSIMs and top-ups, structured request logging, and a CI/CD pipeline that runs the tests on every push and redeploys on green.

---

## What it does

| Role | What they can do |
|---|---|
| **Regular user** | Register, log in, view their own eSIMs and subscriptions, request a new eSIM or a data top-up, edit their profile |
| **Admin** | Everything above, plus full create, read, update and delete on users, businesses, eSIMs and subscriptions, and approval of pending requests |

Self-registered accounts start unconfirmed. Until an admin confirms them, they are held on a pending page, which keeps casual sign-ups out of the real data.

---

## Try it

### On the live demo

`seed.py` creates three demo accounts, all with the password `Demo@1234` (if the hosted database was seeded from an older version, check `seed.py` on that commit):

| Account | Email | What it shows |
|---|---|---|
| Admin | `admin@example.com` | The admin portal, pending approvals and full CRUD |
| User | `user@example.com` | A regular user's eSIMs, subscriptions and requests |
| Pending | `pending@example.com` | The confirmation gate an unapproved account sees |

### On your machine

```bash
git clone https://github.com/Alex90Jennings/agile-assignment
cd agile-assignment

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then set your own SECRET_KEY
python seed.py                    # creates the tables and demo data
flask run                         # http://127.0.0.1:5000
```

`seed.py` drops and recreates every table, then inserts 10 businesses, 13 users, 10 eSIMs and 22 subscriptions, some deliberately left pending so the approval screens have something to show.

On macOS, port 5000 is often taken by AirPlay Receiver. Use `flask run --port 5001` if the page does not load, or turn AirPlay Receiver off in System Settings.

### Running the tests

```bash
pytest -v
```

384 tests covering models, validation, permissions, the approval flows, the admin screens and logging. They run against an in-memory SQLite database, so your development data is untouched.

---

## How it is built

| Layer | Choice |
|---|---|
| Framework | Flask, split into `auth`, `main` and `admin` blueprints |
| Database | SQLAlchemy models, SQLite in development, PostgreSQL (Neon) in production |
| Auth | Flask-Login with Werkzeug password hashing |
| Validation | Server-side helpers in `app/utils/validation.py` |
| Templates | Jinja2 with a shared layout and macros |
| Observability | Request timing, structured logs and custom 400/403/404/500 pages |
| Tests | pytest, 384 tests |
| CI/CD | GitHub Actions: tests on every push, deploy to Render when `main` is green |

```
assignment/
├── app/
│   ├── __init__.py          # app factory, logging, confirmation gate
│   ├── models.py            # Business, User, ESim, Subscription
│   ├── extensions.py        # db and login manager
│   ├── observability.py     # request hooks and error handlers
│   ├── auth/                # register, login, logout
│   ├── main/                # user dashboard, profile, requests
│   ├── admin/               # CRUD and approvals
│   ├── templates/
│   └── static/
├── tests/                   # 14 test modules
├── docs/                    # ERD and demo recording
├── config.py                # development, testing and production config
├── seed.py                  # demo data
└── run.py                   # entry point
```

### Database

![Entity relationship diagram: businesses have users, users have eSIMs, eSIMs have subscriptions](docs/erd.png)

A business has many users, a user has many eSIMs, and an eSIM has many subscriptions. Deleting a user removes their eSIMs, and deleting an eSIM removes its subscriptions.

---

## The assignment brief

The module is assessed by one piece of coursework worth 100%, split across three tasks plus academic conventions.

### Requirements for the application

- Design, develop and test a **web database application in Python**, using any framework.
- Include a **relational database with at least two tables**, each holding **10 records** for testing, with a variety of data types and proper **primary and foreign keys**.
- Provide **two user roles**, admin and regular, both of which must **register and log in**.
- All users can explore records from the database tables.
- **Admins** can perform all CRUD operations; **regular users** can create, read and update only.
- **Validate** input so invalid operations are impossible, and show **clear error messages** when rules are broken.
- Follow **modular design**, sensible naming, indentation, comments and refactoring.
- Consider **usability**: confirm destructive actions, and tell the user whether an action succeeded.

### Evidence required

A report containing a problem statement, scope, design documents, an ERD, an explanation of the structure and techniques, annotated screenshots, an end-user manual and instructions for running the application, plus the source code (a public repository or a ZIP) and the application hosted on a free cloud platform.

### The three tasks

| Task | Weight | What it asks for |
|---|---|---|
| **Task 1 — Web development project** | 60% | Build and test the application against the requirements above, using an Agile approach |
| **Task 2 — Report on the development** | 10% | Explain three Agile elements used (for example user stories, sprints, Kanban boards) with evidence |
| **Task 3 — Agile overview** | 20% | Compare and critically evaluate a chosen Agile framework against two others, and propose an improvement for your organisation |
| **Academic conventions** | 10% | Structure, argument, Harvard referencing and use of language |

---

## Marking scheme

The rubric marks each task across six bands:

| Band | Mark |
|---|---|
| Outstanding | 80–100% |
| Excellent | 70–79% |
| Very good | 60–69% |
| Good | 50–59% |
| Pass | 40–49% |
| Poor | 0–39% |

For **Task 1**, the top band asks for an application that meets or surpasses every requirement, with code that follows SOLID principles, considered usability, refactoring that removes duplication, validation of all data to the highest standard, sound error logging, correct storage and retrieval, and a report with a clear problem statement and all the necessary design documents. Lower bands step this down: a "Good" application meets the key requirements with some gaps in validation and refactoring, while a "Poor" one may not run at all.

**Tasks 2 and 3** are marked on how well the three Agile elements and the framework comparison are described, evidenced and critically evaluated. **Academic conventions** rewards presentation, the range of literature used and accurate Harvard referencing.

### How this project answers the brief

| Requirement | Where it lives |
|---|---|
| At least two tables, 10 records each | Four tables; `seed.py` loads 10 businesses, 13 users, 10 eSIMs and 22 subscriptions |
| Primary and foreign keys, varied types | `app/models.py` — integers, strings, booleans, floats, dates and timestamps |
| Two roles, both registering and logging in | `app/auth/routes.py`, with `is_admin` and the confirmation gate in `app/__init__.py` |
| Admin CRUD, restricted regular users | `app/admin/routes.py` and `app/main/routes.py` |
| Validation and error messages | `app/utils/validation.py`, plus flash messages and error templates |
| Modular design | Blueprints, shared utilities and template macros |
| Hosted application and source control | Deployed on Render, source on GitHub, tested and deployed by GitHub Actions |

---

## Deployment

The app runs on Render with a Neon PostgreSQL database. GitHub Actions runs `pytest` on every push (`.github/workflows/ci.yml`); when a push to `main` passes, a second workflow (`cd.yml`) calls the Render deploy hook stored in the `RENDER_DEPLOY_HOOK_URL` secret.

To deploy your own copy, create a Neon database and a Render web service pointing at the repository, set `SECRET_KEY`, `DATABASE_URL` and `FLASK_ENV=production`, and use `gunicorn run:app` as the start command.

| Variable | Purpose | Example |
|---|---|---|
| `SECRET_KEY` | Signs the session cookie | a long random string |
| `DATABASE_URL` | Database connection string | `sqlite:///dev.db` |
| `FLASK_ENV` | Which config to load | `development` or `production` |
