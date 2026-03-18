"""
Regular-user eSIM request and subscription top-up flows.
"""

from datetime import date

from app.extensions import db as _db
from app.models import ESim, Subscription


TODAY = date.today().isoformat()

VALID_ESIM_REQUEST = {
    'label':         'My Phone',
    'plan_name':     'Starter 5GB',
    'data_limit_gb': '5.0',
    'start_date':    TODAY,
}

VALID_TOPUP = {
    'plan_name':     'Extra 10GB',
    'data_limit_gb': '10.0',
    'start_date':    TODAY,
}


# ---------------------------------------------------------------------------
# eSIM request page — GET / layout
# ---------------------------------------------------------------------------

class TestESimRequestPage:
    def test_get_request_page_returns_200(self, user_client):
        r = user_client.get('/esims/request')
        assert r.status_code == 200
        assert b'Request' in r.data

    def test_unauthenticated_redirected(self, client):
        r = client.get('/esims/request')
        assert r.status_code == 302

    def test_back_button_not_present(self, user_client):
        r = user_client.get('/esims/request')
        # The page header must not contain a Back link
        assert b'Back' not in r.data

    def test_cancel_button_still_present(self, user_client):
        r = user_client.get('/esims/request')
        assert b'Cancel' in r.data


# ---------------------------------------------------------------------------
# eSIM request — POST success
# ---------------------------------------------------------------------------

class TestESimRequest:
    def test_submit_creates_esim_and_subscription(self, user_client, sample_user):
        r = user_client.post('/esims/request', data=VALID_ESIM_REQUEST,
                             follow_redirects=True)
        assert r.status_code == 200
        assert b'submitted' in r.data

        esim = ESim.query.filter_by(user_id=sample_user.id).first()
        assert esim is not None
        assert esim.is_confirmed is False
        assert esim.status == 'inactive'
        assert esim.iccid.startswith('89')
        assert len(esim.iccid) == 19

        sub = Subscription.query.filter_by(esim_id=esim.id).first()
        assert sub is not None
        assert sub.is_confirmed is False
        assert sub.plan_name == 'Starter 5GB'

    def test_submit_without_label_succeeds(self, user_client, sample_user):
        data = {**VALID_ESIM_REQUEST, 'label': ''}
        r = user_client.post('/esims/request', data=data, follow_redirects=True)
        assert r.status_code == 200
        assert b'submitted' in r.data
        esim = ESim.query.filter_by(user_id=sample_user.id).first()
        assert esim.label is None

    def test_iccid_auto_generated_starts_with_89(self, user_client, sample_user):
        user_client.post('/esims/request', data=VALID_ESIM_REQUEST,
                         follow_redirects=True)
        esim = ESim.query.filter_by(user_id=sample_user.id).first()
        assert esim.iccid[:2] == '89'


# ---------------------------------------------------------------------------
# eSIM request — validation errors
# ---------------------------------------------------------------------------

class TestESimRequestValidation:
    def test_missing_plan_name_shows_error(self, user_client):
        data = {**VALID_ESIM_REQUEST, 'plan_name': ''}
        r = user_client.post('/esims/request', data=data, follow_redirects=True)
        assert b'required' in r.data

    def test_missing_data_limit_shows_error(self, user_client):
        data = {**VALID_ESIM_REQUEST, 'data_limit_gb': ''}
        r = user_client.post('/esims/request', data=data, follow_redirects=True)
        assert b'required' in r.data

    def test_invalid_data_limit_shows_error(self, user_client):
        data = {**VALID_ESIM_REQUEST, 'data_limit_gb': 'abc'}
        r = user_client.post('/esims/request', data=data, follow_redirects=True)
        assert b'number' in r.data

    def test_zero_data_limit_shows_error(self, user_client):
        data = {**VALID_ESIM_REQUEST, 'data_limit_gb': '0'}
        r = user_client.post('/esims/request', data=data, follow_redirects=True)
        assert b'greater than 0' in r.data

    def test_missing_start_date_shows_error(self, user_client):
        data = {**VALID_ESIM_REQUEST, 'start_date': ''}
        r = user_client.post('/esims/request', data=data, follow_redirects=True)
        assert b'required' in r.data

    def test_invalid_start_date_shows_error(self, user_client):
        data = {**VALID_ESIM_REQUEST, 'start_date': 'not-a-date'}
        r = user_client.post('/esims/request', data=data, follow_redirects=True)
        assert b'valid date' in r.data


# ---------------------------------------------------------------------------
# Subscription top-up — GET
# ---------------------------------------------------------------------------

class TestTopUpPage:
    def test_get_topup_page_returns_200(self, user_client, sample_esim):
        r = user_client.get(f'/esims/{sample_esim.id}/topup')
        assert r.status_code == 200
        assert b'Top-up' in r.data

    def test_topup_for_other_users_esim_returns_404(self, user_client,
                                                     admin_client, sample_admin):
        # Create an eSIM owned by admin, try to access as regular user
        from app.models import ESim as E
        e = E(iccid='8977777777777777777', status='active',
              is_confirmed=True, user_id=sample_admin.id)
        _db.session.add(e)
        _db.session.commit()
        r = user_client.get(f'/esims/{e.id}/topup')
        assert r.status_code == 404

    def test_nonexistent_esim_returns_404(self, user_client):
        r = user_client.get('/esims/9999/topup')
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Subscription top-up — POST success
# ---------------------------------------------------------------------------

class TestSubscriptionTopUp:
    def test_submit_topup_creates_subscription(self, user_client, sample_esim):
        r = user_client.post(f'/esims/{sample_esim.id}/topup', data=VALID_TOPUP,
                             follow_redirects=True)
        assert r.status_code == 200
        assert b'submitted' in r.data

        sub = Subscription.query.filter_by(
            esim_id=sample_esim.id, plan_name='Extra 10GB'
        ).first()
        assert sub is not None
        assert sub.is_confirmed is False

    def test_topup_subscription_not_confirmed(self, user_client, sample_esim):
        user_client.post(f'/esims/{sample_esim.id}/topup', data=VALID_TOPUP,
                         follow_redirects=True)
        sub = Subscription.query.filter_by(
            esim_id=sample_esim.id, plan_name='Extra 10GB'
        ).first()
        assert sub.is_confirmed is False


# ---------------------------------------------------------------------------
# Subscription top-up — validation errors
# ---------------------------------------------------------------------------

class TestTopUpValidation:
    def test_missing_plan_name_shows_error(self, user_client, sample_esim):
        data = {**VALID_TOPUP, 'plan_name': ''}
        r = user_client.post(f'/esims/{sample_esim.id}/topup', data=data,
                             follow_redirects=True)
        assert b'required' in r.data

    def test_missing_data_limit_shows_error(self, user_client, sample_esim):
        data = {**VALID_TOPUP, 'data_limit_gb': ''}
        r = user_client.post(f'/esims/{sample_esim.id}/topup', data=data,
                             follow_redirects=True)
        assert b'required' in r.data

    def test_missing_start_date_shows_error(self, user_client, sample_esim):
        data = {**VALID_TOPUP, 'start_date': ''}
        r = user_client.post(f'/esims/{sample_esim.id}/topup', data=data,
                             follow_redirects=True)
        assert b'required' in r.data


# ---------------------------------------------------------------------------
# Admin confirms eSIM request
# ---------------------------------------------------------------------------

class TestAdminConfirmsESimRequest:
    def test_confirm_esim_sets_confirmed_and_active(self, admin_client,
                                                     unconfirmed_esim):
        eid = unconfirmed_esim.id
        r = admin_client.post(f'/admin/esims/{eid}/confirm',
                              follow_redirects=True)
        assert r.status_code == 200
        assert b'confirmed' in r.data
        esim = _db.session.get(ESim, eid)
        assert esim.is_confirmed is True
        assert esim.status == 'active'

    def test_confirm_nonexistent_esim_returns_404(self, admin_client):
        r = admin_client.post('/admin/esims/9999/confirm')
        assert r.status_code == 404

    def test_confirm_esim_requires_admin(self, user_client, unconfirmed_esim):
        r = user_client.post(f'/admin/esims/{unconfirmed_esim.id}/confirm')
        assert r.status_code == 403

    def test_confirm_esim_only_accepts_post(self, admin_client, unconfirmed_esim):
        r = admin_client.get(f'/admin/esims/{unconfirmed_esim.id}/confirm')
        assert r.status_code == 405


# ---------------------------------------------------------------------------
# Admin confirms subscription request
# ---------------------------------------------------------------------------

class TestAdminConfirmsSubscriptionRequest:
    def test_confirm_subscription_sets_confirmed(self, admin_client,
                                                  unconfirmed_subscription):
        sid = unconfirmed_subscription.id
        r = admin_client.post(f'/admin/subscriptions/{sid}/confirm',
                              follow_redirects=True)
        assert r.status_code == 200
        assert b'confirmed' in r.data
        sub = _db.session.get(Subscription, sid)
        assert sub.is_confirmed is True

    def test_confirm_nonexistent_subscription_returns_404(self, admin_client):
        r = admin_client.post('/admin/subscriptions/9999/confirm')
        assert r.status_code == 404

    def test_confirm_subscription_requires_admin(self, user_client,
                                                  unconfirmed_subscription):
        r = user_client.post(
            f'/admin/subscriptions/{unconfirmed_subscription.id}/confirm'
        )
        assert r.status_code == 403

    def test_confirm_subscription_only_accepts_post(self, admin_client,
                                                     unconfirmed_subscription):
        r = admin_client.get(
            f'/admin/subscriptions/{unconfirmed_subscription.id}/confirm'
        )
        assert r.status_code == 405


# ---------------------------------------------------------------------------
# Dashboard shows pending/confirmed status
# ---------------------------------------------------------------------------

class TestDashboardShowsStatus:
    def test_confirmed_esim_shows_status_badge(self, user_client, sample_esim):
        r = user_client.get('/dashboard')
        assert r.status_code == 200
        assert b'status-active' in r.data

    def test_pending_esim_shows_pending_badge(self, user_client, unconfirmed_esim):
        r = user_client.get('/dashboard')
        assert r.status_code == 200
        assert b'status-pending' in r.data
        assert b'Pending Approval' in r.data

    def test_pending_subscription_shows_pending_badge(self, user_client,
                                                       sample_esim,
                                                       unconfirmed_subscription):
        r = user_client.get('/dashboard')
        assert r.status_code == 200
        assert b'status-pending' in r.data

    def test_request_esim_button_shown(self, user_client):
        r = user_client.get('/dashboard')
        assert b'Request eSIM' in r.data

    def test_topup_button_shown_for_confirmed_esim(self, user_client, sample_esim):
        r = user_client.get('/dashboard')
        assert b'Request Top-up' in r.data

    def test_topup_button_not_shown_for_pending_esim(self, user_client,
                                                       unconfirmed_esim):
        r = user_client.get('/dashboard')
        assert b'Request Top-up' not in r.data


# ---------------------------------------------------------------------------
# Profile shows business card
# ---------------------------------------------------------------------------

class TestProfileShowsBusiness:
    def test_profile_shows_business_name(self, user_client, sample_user,
                                          sample_business):
        r = user_client.get('/profile')
        assert r.status_code == 200
        assert b'Test Corp' in r.data

    def test_profile_shows_business_reg_number(self, user_client, sample_user,
                                                sample_business):
        r = user_client.get('/profile')
        assert b'TEST-001' in r.data

    def test_profile_shows_business_profile_card_heading(self, user_client,
                                                          sample_user,
                                                          sample_business):
        r = user_client.get('/profile')
        assert b'Business Profile' in r.data

    def test_profile_shows_business_created_date(self, user_client, sample_user,
                                                  sample_business):
        r = user_client.get('/profile')
        # The created date is rendered in '%d %b %Y' format
        expected = sample_business.created_at.strftime('%d %b %Y').encode()
        assert expected in r.data

    def test_profile_no_business_card_when_no_business(self, app, sample_admin):
        from app.models import User
        u = User(first_name='No', last_name='Biz', email='nobiz@test.com',
                 is_confirmed=True, is_admin=False)
        u.set_password('Secure1!')
        _db.session.add(u)
        _db.session.commit()
        c = app.test_client()
        c.post('/auth/login', data={'email': 'nobiz@test.com',
                                    'password': 'Secure1!'},
               follow_redirects=True)
        r = c.get('/profile')
        assert r.status_code == 200
        assert b'Business Profile' not in r.data
        assert b'Test Corp' not in r.data
