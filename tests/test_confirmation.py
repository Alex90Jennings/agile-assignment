"""
Tests for the user confirmation/approval flow and regular-user header nav.

Covers:
- Self-registered users default to unconfirmed
- Admin-created users default to confirmed
- Unconfirmed users can log in but are gated to the pending page
- Unconfirmed users can access logout
- Confirmed users behave normally
- Admin can confirm/revoke a user via the edit form
- Regular user header includes Dashboard, Profile, and Logout
- Dashboard nav link is active when on the dashboard page
"""

from app.extensions import db as _db
from app.models import User


VALID_REGISTER = {
    'first_name':       'New',
    'last_name':        'User',
    'email':            'newuser@test.com',
    'password':         'Secure1!',
    'confirm_password': 'Secure1!',
}

VALID_ADMIN_USER = {
    'first_name':       'Admin',
    'last_name':        'Created',
    'email':            'admincreated@test.com',
    'password':         'Secure1!',
    'confirm_password': 'Secure1!',
}


# ---------------------------------------------------------------------------
# Default confirmation state
# ---------------------------------------------------------------------------

class TestConfirmationDefaults:

    def test_self_registered_user_is_unconfirmed(self, client):
        client.post('/auth/register', data=VALID_REGISTER)
        user = User.query.filter_by(email='newuser@test.com').first()
        assert user is not None
        assert user.is_confirmed is False

    def test_admin_created_user_is_confirmed(self, admin_client):
        admin_client.post('/admin/users/new', data=VALID_ADMIN_USER,
                          follow_redirects=True)
        user = User.query.filter_by(email='admincreated@test.com').first()
        assert user is not None
        assert user.is_confirmed is True


# ---------------------------------------------------------------------------
# Unconfirmed user access rules
# ---------------------------------------------------------------------------

class TestUnconfirmedUserAccess:

    def test_unconfirmed_user_can_login(self, client, unconfirmed_user):
        r = client.post('/auth/login', data={
            'email': 'unconfirmed@test.com',
            'password': 'Secure1!',
        }, follow_redirects=False)
        assert r.status_code == 302

    def test_unconfirmed_user_sees_pending_page(self, unconfirmed_client):
        r = unconfirmed_client.get('/pending')
        assert r.status_code == 200
        assert b'Awaiting' in r.data or b'awaiting' in r.data.lower()

    def test_unconfirmed_user_redirected_from_dashboard(self, unconfirmed_client):
        r = unconfirmed_client.get('/dashboard', follow_redirects=False)
        assert r.status_code == 302
        assert '/pending' in r.headers['Location']

    def test_unconfirmed_user_redirected_from_profile(self, unconfirmed_client):
        r = unconfirmed_client.get('/profile', follow_redirects=False)
        assert r.status_code == 302
        assert '/pending' in r.headers['Location']

    def test_unconfirmed_user_redirected_from_edit_profile(self, unconfirmed_client):
        r = unconfirmed_client.get('/profile/edit', follow_redirects=False)
        assert r.status_code == 302
        assert '/pending' in r.headers['Location']

    def test_unconfirmed_user_can_logout(self, unconfirmed_client):
        r = unconfirmed_client.get('/auth/logout', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']


# ---------------------------------------------------------------------------
# Confirmed user access
# ---------------------------------------------------------------------------

class TestConfirmedUserAccess:

    def test_confirmed_user_can_access_dashboard(self, user_client):
        assert user_client.get('/dashboard').status_code == 200

    def test_confirmed_user_can_access_profile(self, user_client):
        assert user_client.get('/profile').status_code == 200

    def test_confirmed_user_pending_page_redirects_to_dashboard(self, user_client):
        r = user_client.get('/pending', follow_redirects=False)
        assert r.status_code == 302
        assert '/dashboard' in r.headers['Location']


# ---------------------------------------------------------------------------
# Admin confirms / revokes a user
# ---------------------------------------------------------------------------

class TestAdminConfirmUser:

    def test_admin_can_confirm_unconfirmed_user(self, admin_client, unconfirmed_user):
        r = admin_client.post(
            f'/admin/users/{unconfirmed_user.id}/edit',
            data={
                'first_name':   unconfirmed_user.first_name,
                'last_name':    unconfirmed_user.last_name,
                'email':        unconfirmed_user.email,
                'is_confirmed': '1',
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b'updated successfully' in r.data
        user = _db.session.get(User, unconfirmed_user.id)
        assert user.is_confirmed is True

    def test_admin_can_revoke_confirmation(self, admin_client, sample_user):
        # sample_user starts confirmed; omitting is_confirmed unchecks the box
        r = admin_client.post(
            f'/admin/users/{sample_user.id}/edit',
            data={
                'first_name': sample_user.first_name,
                'last_name':  sample_user.last_name,
                'email':      sample_user.email,
                # is_confirmed omitted → False
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        user = _db.session.get(User, sample_user.id)
        assert user.is_confirmed is False

    def test_edit_form_shows_confirmed_checkbox(self, admin_client, sample_user):
        r = admin_client.get(f'/admin/users/{sample_user.id}/edit')
        assert r.status_code == 200
        assert b'is_confirmed' in r.data

    def test_edit_form_does_not_show_confirmed_on_create(self, admin_client):
        r = admin_client.get('/admin/users/new')
        assert r.status_code == 200
        # is_confirmed checkbox only appears on the edit form
        assert b'id="is_confirmed"' not in r.data


# ---------------------------------------------------------------------------
# Regular user header navigation
# ---------------------------------------------------------------------------

class TestRegularUserNav:

    def test_regular_user_header_includes_dashboard_link(self, user_client):
        r = user_client.get('/profile')
        assert r.status_code == 200
        assert b'/dashboard' in r.data

    def test_regular_user_header_includes_profile_link(self, user_client):
        r = user_client.get('/dashboard')
        assert r.status_code == 200
        assert b'/profile' in r.data

    def test_regular_user_header_includes_logout_link(self, user_client):
        r = user_client.get('/dashboard')
        assert b'/auth/logout' in r.data

    def test_dashboard_nav_link_is_active_on_dashboard_page(self, user_client):
        r = user_client.get('/dashboard')
        assert r.status_code == 200
        # The Dashboard link has class="nav-link active" when on /dashboard
        assert b'nav-link active' in r.data

    def test_admin_header_includes_portal_link(self, admin_client):
        # Admin nav has a "Portal" link pointing to /admin/
        r = admin_client.get('/admin/')
        assert r.status_code == 200
        assert b'href="/admin/"' in r.data
        assert b'>Portal<' in r.data

    def test_admin_header_includes_dashboard_link(self, admin_client):
        # Admin nav also has a "Dashboard" link pointing to /dashboard
        r = admin_client.get('/admin/')
        assert r.status_code == 200
        assert b'href="/dashboard"' in r.data
        assert b'>Dashboard<' in r.data
