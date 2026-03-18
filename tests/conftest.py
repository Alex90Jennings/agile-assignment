"""
Shared fixtures for the test suite.

Root cause of g/_login_user contamination (Flask 3.x):
  Flask 3.x reuses an already-active app context for every incoming request
  rather than pushing a new one. This means `flask.g` (where Flask-Login
  stores `_login_user`) is shared across ALL requests made while the outer
  app context is alive. A session-scoped app context therefore leaks login
  state between tests.

Fix:
  - `app` (session-scoped) only creates the Flask application; it does NOT
    push a persistent app context.
  - `db_ctx` (function-scoped, autouse) pushes a FRESH app context for each
    test. Every request made during that test reuses this context (expected),
    but the context — and its `g` — is torn down after the test completes.
  - StaticPool in TestingConfig ensures the single in-memory SQLite connection
    is reused across all function-scoped contexts.
"""

import pytest
from datetime import date

from app import create_app
from app.extensions import db as _db
from app.models import Business, User, ESim, Subscription


# ---------------------------------------------------------------------------
# App lifecycle — session-scoped, NO persistent context push
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def app():
    return create_app('testing')


# ---------------------------------------------------------------------------
# Per-test app context + DB cleanup — the fix for g contamination
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def db_ctx(app):
    """Push a fresh app context (and fresh g) for every test.

    All data fixtures and test-client requests share this context, so
    Flask-Login's g._login_user is scoped to exactly one test at a time.
    """
    with app.app_context():
        _db.create_all()
        yield
        _db.session.remove()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


# ---------------------------------------------------------------------------
# Test client
# ---------------------------------------------------------------------------

@pytest.fixture
def client(app):
    """Fresh, unauthenticated test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Seed fixtures — run inside db_ctx's app context (no nested context needed)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_business():
    b = Business(name='Test Corp', registration_number='TEST-001')
    _db.session.add(b)
    _db.session.commit()
    _db.session.refresh(b)
    return b


@pytest.fixture
def sample_admin(sample_business):
    u = User(
        email='admin@test.com',
        first_name='Admin',
        last_name='Test',
        is_admin=True,
        is_confirmed=True,
        business_id=sample_business.id,
    )
    u.set_password('Secure1!')
    _db.session.add(u)
    _db.session.commit()
    _db.session.refresh(u)
    return u


@pytest.fixture
def sample_user(sample_business):
    u = User(
        email='user@test.com',
        first_name='Regular',
        last_name='User',
        is_admin=False,
        is_confirmed=True,
        business_id=sample_business.id,
    )
    u.set_password('Secure1!')
    _db.session.add(u)
    _db.session.commit()
    _db.session.refresh(u)
    return u


@pytest.fixture
def unconfirmed_user(sample_business):
    u = User(
        email='unconfirmed@test.com',
        first_name='Pending',
        last_name='User',
        is_admin=False,
        is_confirmed=False,
        business_id=sample_business.id,
    )
    u.set_password('Secure1!')
    _db.session.add(u)
    _db.session.commit()
    _db.session.refresh(u)
    return u


@pytest.fixture
def sample_esim(sample_user):
    e = ESim(
        iccid='8901234567890123456',
        label='Test eSIM',
        status='active',
        is_confirmed=True,
        user_id=sample_user.id,
    )
    _db.session.add(e)
    _db.session.commit()
    _db.session.refresh(e)
    return e


@pytest.fixture
def unconfirmed_esim(sample_user):
    e = ESim(
        iccid='8999999999999999999',
        label='Pending eSIM',
        status='inactive',
        is_confirmed=False,
        user_id=sample_user.id,
    )
    _db.session.add(e)
    _db.session.commit()
    _db.session.refresh(e)
    return e


@pytest.fixture
def sample_subscription(sample_esim):
    s = Subscription(
        esim_id=sample_esim.id,
        plan_name='Basic Plan',
        data_limit_gb=5.0,
        start_date=date.today(),
        end_date=None,
        status='active',
        is_confirmed=True,
    )
    _db.session.add(s)
    _db.session.commit()
    _db.session.refresh(s)
    return s


@pytest.fixture
def unconfirmed_subscription(sample_esim):
    s = Subscription(
        esim_id=sample_esim.id,
        plan_name='Pending Plan',
        data_limit_gb=10.0,
        start_date=date.today(),
        end_date=None,
        status='active',
        is_confirmed=False,
    )
    _db.session.add(s)
    _db.session.commit()
    _db.session.refresh(s)
    return s


# ---------------------------------------------------------------------------
# Authenticated clients — each uses its own test_client so login state
# cannot leak into tests that use the base `client` fixture.
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_client(app, sample_admin):
    c = app.test_client()
    c.post('/auth/login', data={
        'email': 'admin@test.com',
        'password': 'Secure1!',
    }, follow_redirects=True)
    return c


@pytest.fixture
def user_client(app, sample_user):
    c = app.test_client()
    c.post('/auth/login', data={
        'email': 'user@test.com',
        'password': 'Secure1!',
    }, follow_redirects=True)
    return c


@pytest.fixture
def unconfirmed_client(app, unconfirmed_user):
    c = app.test_client()
    c.post('/auth/login', data={
        'email': 'unconfirmed@test.com',
        'password': 'Secure1!',
    }, follow_redirects=True)
    return c
