# eSIM Admin Dashboard

A Flask web application for managing eSIMs, subscriptions, users, and businesses.
Built as a university assignment demonstrating relational databases, role-based access control, CRUD operations, and automated testing.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask |
| ORM | Flask-SQLAlchemy |
| Auth | Flask-Login, Werkzeug (password hashing) |
| Database (dev) | SQLite |
| Database (prod) | Neon PostgreSQL |
| Deployment | Render |
| Testing | pytest |
| Validation | Manual server-side (no WTForms) |

---

## Roles

| Role | Permissions |
|---|---|
| **Admin** | Full CRUD on users, businesses, eSIMs, subscriptions |
| **Regular user** | Register, login/logout, view own eSIMs and subscriptions, edit own profile |

---

## Local Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd assignment
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set a strong `SECRET_KEY`. Leave `DATABASE_URL` as-is for SQLite development.

### 5. Initialise and seed the database

```bash
python seed.py
```

This drops and recreates all tables, then inserts demo data including:
- 10 businesses
- 12 users (1 admin, 1 regular demo user, 10 named users)
- 10 eSIMs
- 15 subscriptions

**Demo credentials:**

| Role | Email | Password |
|---|---|---|
| Admin | admin@example.com | admin1234 |
| User | user@example.com | user1234 |

### 6. Run the application

```bash
flask run
```

Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Running Tests

```bash
pytest -v
```

Tests use an in-memory SQLite database and do not touch your development database.

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Flask session signing key | `a-random-string` |
| `DATABASE_URL` | SQLAlchemy database URI | `sqlite:///dev.db` |
| `FLASK_ENV` | `development` or `production` | `development` |

---

## Project Structure

```
assignment/
├── app/
│   ├── __init__.py         # create_app() factory
│   ├── extensions.py       # db, login_manager instances
│   ├── models.py           # SQLAlchemy models + user_loader
│   ├── auth/               # /auth blueprint (login, register, logout)
│   ├── main/               # / blueprint (dashboard, profile)
│   ├── admin/              # /admin blueprint (full CRUD) — Stage 2
│   ├── templates/
│   └── static/
├── tests/
├── docs/
├── seed.py
├── config.py
├── run.py
└── requirements.txt
```

---

## Database Schema

### `businesses`
`id`, `name`, `registration_number` (unique), `created_at`, `updated_at`

### `users`
`id`, `email` (unique), `password_hash`, `first_name`, `last_name`, `is_admin`, `business_id` (FK), `created_at`, `updated_at`

### `esims`
`id`, `iccid` (unique), `label`, `status`, `user_id` (FK), `created_at`, `updated_at`

### `subscriptions`
`id`, `esim_id` (FK), `plan_name`, `data_limit_gb`, `start_date`, `end_date`, `status`, `created_at`, `updated_at`

See `docs/erd.png` for the entity-relationship diagram.

---

## CI/CD Pipeline

The project uses two GitHub Actions workflows located in `.github/workflows/`.

### CI — `ci.yml`

Runs on every push and pull request (all branches).

| Step | What it does |
|---|---|
| Checkout | Fetches the repository |
| Set up Python | Installs Python 3.11 |
| Install dependencies | `pip install -r requirements.txt` |
| Run tests | `pytest -v` against an in-memory SQLite database |

No external services are needed because `TestingConfig` uses `sqlite:///:memory:`.

### CD — `cd.yml`

Runs only on pushes to `main`, **after** CI passes implicitly (because the push only reaches `main` once a PR is merged and green).

It sends a `POST` request to the Render Deploy Hook URL, which tells Render to pull the latest commit and redeploy the service automatically.

### Configuring the GitHub secret

1. In Render, open your Web Service → **Settings** → **Deploy Hook** and copy the URL.
2. In your GitHub repository go to **Settings → Secrets and variables → Actions → New repository secret**.
3. Name it `RENDER_DEPLOY_HOOK_URL` and paste the URL.

The CD workflow reads this secret as `${{ secrets.RENDER_DEPLOY_HOOK_URL }}` — it is never exposed in logs.

---

## Deployment (Render + Neon)

> Deployment files will be added in Stage 4.

1. Create a Neon PostgreSQL database and copy the connection string.
2. Create a new Web Service on Render, connected to this repository.
3. Set environment variables in Render:
   - `SECRET_KEY`
   - `DATABASE_URL` (Neon connection string)
   - `FLASK_ENV=production`
4. Set the start command to: `gunicorn run:app`
