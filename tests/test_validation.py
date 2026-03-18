"""
Unit tests for app/utils/validation.py (validate_password) and integration
tests for form-level validation across admin and auth routes.
"""

import pytest
from app.utils.validation import validate_password
from app.extensions import db as _db
from app.models import Business, User


# ---------------------------------------------------------------------------
# validate_password — unit tests
# ---------------------------------------------------------------------------

class TestValidatePassword:
    def test_valid_password_returns_no_errors(self):
        assert validate_password('Secure1!') == []

    def test_empty_string_returns_required_error(self):
        errors = validate_password('')
        assert errors == ['Password is required.']

    def test_too_short_returns_length_error(self):
        errors = validate_password('Ab1!')
        assert any('8 characters' in e for e in errors)

    def test_exactly_8_chars_is_valid(self):
        assert validate_password('Secure1!') == []

    def test_7_chars_is_invalid(self):
        errors = validate_password('Secur1!')
        assert any('8 characters' in e for e in errors)

    def test_no_letter_returns_letter_error(self):
        errors = validate_password('12345678!')
        assert any('letter' in e for e in errors)

    def test_no_digit_returns_number_error(self):
        errors = validate_password('Password!')
        assert any('number' in e for e in errors)

    def test_no_special_character_returns_special_error(self):
        errors = validate_password('Password1')
        assert any('special' in e for e in errors)

    def test_multiple_failures_returns_multiple_errors(self):
        # 'abc' → too short, no digit, no special
        errors = validate_password('abc')
        assert len(errors) >= 2

    def test_long_valid_password_passes(self):
        assert validate_password('MyLong$ecureP4ssword!2024') == []

    def test_special_characters_recognised(self):
        for char in '!@#$%^&*()':
            assert validate_password(f'Password1{char}') == []

    def test_only_letters_fails_digit_and_special(self):
        errors = validate_password('abcdefghi')
        assert any('number' in e for e in errors)
        assert any('special' in e for e in errors)

    def test_whitespace_only_returns_required_error(self):
        # A blank password string counts as falsy
        errors = validate_password('   ')
        # Contains no letter-like alpha, no digit, no special if stripped — but
        # the function checks the raw value, so whitespace fails alpha/digit/special checks
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Admin user form validation — integration tests (via HTTP)
# ---------------------------------------------------------------------------

class TestAdminCreateUserValidation:
    BASE = {
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'newuser@example.com',
        'password': 'Secure1!',
        'confirm_password': 'Secure1!',
    }

    def test_missing_first_name(self, admin_client):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'first_name': ''},
                              follow_redirects=True)
        assert b'First name is required' in r.data

    def test_missing_last_name(self, admin_client):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'last_name': ''},
                              follow_redirects=True)
        assert b'Last name is required' in r.data

    def test_missing_email(self, admin_client):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'email': ''},
                              follow_redirects=True)
        assert b'Email is required' in r.data

    def test_invalid_email_format(self, admin_client):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'email': 'not-an-email'},
                              follow_redirects=True)
        assert b'valid email' in r.data

    def test_duplicate_email_rejected(self, admin_client, sample_user):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'email': 'user@test.com'},
                              follow_redirects=True)
        assert b'already in use' in r.data

    def test_password_mismatch_rejected(self, admin_client):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'confirm_password': 'Different1!'},
                              follow_redirects=True)
        assert b'do not match' in r.data

    def test_weak_password_rejected(self, admin_client):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'password': 'weakpw',
                                    'confirm_password': 'weakpw'},
                              follow_redirects=True)
        assert r.status_code == 200
        assert b'created successfully' not in r.data

    def test_first_name_too_long(self, admin_client):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'first_name': 'A' * 81},
                              follow_redirects=True)
        assert b'80 characters' in r.data

    def test_last_name_too_long(self, admin_client):
        r = admin_client.post('/admin/users/new',
                              data={**self.BASE, 'last_name': 'B' * 81},
                              follow_redirects=True)
        assert b'80 characters' in r.data


# ---------------------------------------------------------------------------
# Admin edit user — keeping the same email should not trigger a clash
# ---------------------------------------------------------------------------

class TestAdminEditUserValidation:
    def test_edit_user_keeping_same_email_succeeds(self, admin_client, sample_user):
        r = admin_client.post(f'/admin/users/{sample_user.id}/edit', data={
            'first_name': 'Regular',
            'last_name': 'User',
            'email': 'user@test.com',
            'is_confirmed': '1',
        }, follow_redirects=True)
        assert b'updated successfully' in r.data

    def test_edit_user_to_duplicate_email_fails(self, admin_client,
                                                 sample_user, sample_admin):
        r = admin_client.post(f'/admin/users/{sample_user.id}/edit', data={
            'first_name': 'Regular',
            'last_name': 'User',
            'email': 'admin@test.com',
        }, follow_redirects=True)
        assert b'already in use' in r.data


# ---------------------------------------------------------------------------
# Admin business form validation — integration tests
# ---------------------------------------------------------------------------

class TestAdminBusinessFormValidation:
    def test_missing_name_rejected(self, admin_client):
        r = admin_client.post('/admin/businesses/new',
                              data={'name': '', 'registration_number': 'R-001'},
                              follow_redirects=True)
        assert b'required' in r.data

    def test_name_too_long_rejected(self, admin_client):
        r = admin_client.post('/admin/businesses/new',
                              data={'name': 'X' * 201},
                              follow_redirects=True)
        assert b'200 characters' in r.data

    def test_reg_number_too_long_rejected(self, admin_client):
        r = admin_client.post('/admin/businesses/new',
                              data={'name': 'Corp', 'registration_number': 'R' * 51},
                              follow_redirects=True)
        assert b'50 characters' in r.data

    def test_valid_business_without_reg_number(self, admin_client):
        r = admin_client.post('/admin/businesses/new',
                              data={'name': 'Plain Corp'},
                              follow_redirects=True)
        assert b'created successfully' in r.data


# ---------------------------------------------------------------------------
# Admin eSIM form validation — integration tests
# ---------------------------------------------------------------------------

class TestAdminESimFormValidation:
    def test_iccid_too_short_rejected(self, admin_client, sample_user):
        r = admin_client.post(f'/admin/users/{sample_user.id}/esims/new', data={
            'iccid': '123456789',
            'label': '',
            'status': 'active',
        }, follow_redirects=True)
        assert b'19' in r.data

    def test_iccid_with_letters_rejected(self, admin_client, sample_user):
        r = admin_client.post(f'/admin/users/{sample_user.id}/esims/new', data={
            'iccid': 'ABCDE123456789012345',
            'label': '',
            'status': 'active',
        }, follow_redirects=True)
        assert b'digits' in r.data or b'19' in r.data

    def test_invalid_status_rejected(self, admin_client, sample_user):
        r = admin_client.post(f'/admin/users/{sample_user.id}/esims/new', data={
            'iccid': '8944501234567899991',
            'label': '',
            'status': 'notavalidstatus',
        }, follow_redirects=True)
        assert b'Status must be' in r.data

    def test_label_too_long_rejected(self, admin_client, sample_user):
        r = admin_client.post(f'/admin/users/{sample_user.id}/esims/new', data={
            'iccid': '8944501234567899992',
            'label': 'L' * 101,
            'status': 'active',
        }, follow_redirects=True)
        assert b'100 characters' in r.data


# ---------------------------------------------------------------------------
# Admin subscription form validation — integration tests
# ---------------------------------------------------------------------------

class TestAdminSubscriptionFormValidation:
    def test_missing_plan_name_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': '',
            'data_limit_gb': '5',
            'start_date': '2025-01-01',
            'status': 'active',
        }, follow_redirects=True)
        assert b'Plan name is required' in r.data

    def test_zero_data_limit_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': 'Test Plan',
            'data_limit_gb': '0',
            'start_date': '2025-01-01',
            'status': 'active',
        }, follow_redirects=True)
        assert b'positive' in r.data

    def test_negative_data_limit_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': 'Test Plan',
            'data_limit_gb': '-5',
            'start_date': '2025-01-01',
            'status': 'active',
        }, follow_redirects=True)
        assert b'positive' in r.data

    def test_data_limit_over_1024_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': 'Huge Plan',
            'data_limit_gb': '2000',
            'start_date': '2025-01-01',
            'status': 'active',
        }, follow_redirects=True)
        assert b'1024' in r.data

    def test_non_numeric_data_limit_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': 'Test Plan',
            'data_limit_gb': 'abc',
            'start_date': '2025-01-01',
            'status': 'active',
        }, follow_redirects=True)
        assert b'number' in r.data

    def test_end_date_before_start_date_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': 'Test Plan',
            'data_limit_gb': '5',
            'start_date': '2025-06-01',
            'end_date': '2025-01-01',
            'status': 'active',
        }, follow_redirects=True)
        assert b'after' in r.data

    def test_invalid_start_date_format_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': 'Test Plan',
            'data_limit_gb': '5',
            'start_date': 'not-a-date',
            'status': 'active',
        }, follow_redirects=True)
        assert b'valid date' in r.data

    def test_missing_start_date_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': 'Test Plan',
            'data_limit_gb': '5',
            'start_date': '',
            'status': 'active',
        }, follow_redirects=True)
        assert b'required' in r.data

    def test_plan_name_too_long_rejected(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/subscriptions/new', data={
            'plan_name': 'P' * 101,
            'data_limit_gb': '5',
            'start_date': '2025-01-01',
            'status': 'active',
        }, follow_redirects=True)
        assert b'100 characters' in r.data
