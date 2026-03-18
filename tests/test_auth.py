"""
Integration tests for the auth blueprint.
Covers: register, login, logout, redirect behaviour, validation errors.
"""

from app.extensions import db
from app.models import User


class TestRegisterPage:
    def test_register_page_returns_200(self, client):
        response = client.get('/auth/register')
        assert response.status_code == 200

    def test_register_page_contains_form(self, client):
        response = client.get('/auth/register')
        assert b'form' in response.data


class TestRegisterSubmit:
    VALID = {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'password': 'Secure1!',
        'confirm_password': 'Secure1!',
    }

    def test_register_success_redirects_to_login(self, client):
        response = client.post('/auth/register', data=self.VALID, follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']

    def test_register_success_creates_user(self, app, client):
        client.post('/auth/register', data=self.VALID)
        with app.app_context():
            assert User.query.filter_by(email='john@example.com').first() is not None

    def test_register_duplicate_email(self, client, sample_user):
        data = {**self.VALID, 'email': 'user@test.com'}
        response = client.post('/auth/register', data=data, follow_redirects=True)
        assert b'already registered' in response.data

    def test_register_password_mismatch(self, client):
        data = {**self.VALID, 'confirm_password': 'different999'}
        response = client.post('/auth/register', data=data, follow_redirects=True)
        assert b'do not match' in response.data

    def test_register_short_password(self, client):
        data = {**self.VALID, 'password': 'short', 'confirm_password': 'short'}
        response = client.post('/auth/register', data=data, follow_redirects=True)
        assert b'8 characters' in response.data

    def test_register_missing_first_name(self, client):
        data = {**self.VALID, 'first_name': ''}
        response = client.post('/auth/register', data=data, follow_redirects=True)
        assert b'First name is required' in response.data

    def test_register_missing_last_name(self, client):
        data = {**self.VALID, 'last_name': ''}
        response = client.post('/auth/register', data=data, follow_redirects=True)
        assert b'Last name is required' in response.data

    def test_register_missing_email(self, client):
        data = {**self.VALID, 'email': ''}
        response = client.post('/auth/register', data=data, follow_redirects=True)
        assert b'Email is required' in response.data

    def test_register_invalid_email(self, client):
        data = {**self.VALID, 'email': 'not-an-email'}
        response = client.post('/auth/register', data=data, follow_redirects=True)
        assert b'valid email' in response.data

    def test_register_empty_form_does_not_crash(self, client):
        response = client.post('/auth/register', data={}, follow_redirects=True)
        assert response.status_code == 200

    def test_register_password_is_not_stored_as_plaintext(self, app, client):
        client.post('/auth/register', data=self.VALID)
        with app.app_context():
            u = User.query.filter_by(email='john@example.com').first()
            assert u.password_hash != 'password123'

    def test_authenticated_user_redirected_away_from_register(self, user_client):
        response = user_client.get('/auth/register')
        assert response.status_code == 302


class TestLoginPage:
    def test_login_page_returns_200(self, client):
        assert client.get('/auth/login').status_code == 200

    def test_login_page_contains_form(self, client):
        assert b'form' in client.get('/auth/login').data


class TestLoginSubmit:
    def test_login_success_redirects_to_dashboard(self, client, sample_user):
        response = client.post('/auth/login', data={
            'email': 'user@test.com',
            'password': 'Secure1!',
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/dashboard' in response.headers['Location']

    def test_admin_login_redirects_to_admin_dashboard(self, client, sample_admin):
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'Secure1!',
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/admin' in response.headers['Location']

    def test_already_authenticated_admin_redirected_to_admin(self, admin_client):
        response = admin_client.get('/auth/login', follow_redirects=False)
        assert response.status_code == 302
        assert '/admin' in response.headers['Location']

    def test_login_wrong_password_shows_error(self, client, sample_user):
        response = client.post('/auth/login', data={
            'email': 'user@test.com',
            'password': 'wrongpassword',
        }, follow_redirects=True)
        assert b'Invalid email or password' in response.data

    def test_login_unknown_email_shows_error(self, client):
        response = client.post('/auth/login', data={
            'email': 'nobody@test.com',
            'password': 'password123',
        }, follow_redirects=True)
        assert b'Invalid email or password' in response.data

    def test_login_missing_fields_shows_error(self, client):
        response = client.post('/auth/login', data={
            'email': '',
            'password': '',
        }, follow_redirects=True)
        assert b'required' in response.data

    def test_authenticated_user_redirected_away_from_login(self, user_client):
        response = user_client.get('/auth/login')
        assert response.status_code == 302


class TestLogout:
    def test_logout_redirects_to_login(self, user_client):
        response = user_client.get('/auth/logout', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']

    def test_logout_clears_session(self, user_client):
        user_client.get('/auth/logout')
        response = user_client.get('/dashboard', follow_redirects=False)
        assert response.status_code == 302

    def test_logout_requires_login(self, client):
        response = client.get('/auth/logout', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']


class TestUnauthenticatedRedirects:
    def test_dashboard_redirects_unauthenticated(self, client):
        response = client.get('/dashboard', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.headers['Location']

    def test_profile_redirects_unauthenticated(self, client):
        response = client.get('/profile', follow_redirects=False)
        assert response.status_code == 302

    def test_edit_profile_redirects_unauthenticated(self, client):
        response = client.get('/profile/edit', follow_redirects=False)
        assert response.status_code == 302
