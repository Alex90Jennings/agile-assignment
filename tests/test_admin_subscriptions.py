"""
Admin — Subscription create / edit / delete tests.
"""

from datetime import date, timedelta

from app.extensions import db as _db
from app.models import Subscription


TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()

VALID_SUB = {
    'plan_name':     'Basic Plan',
    'data_limit_gb': '5.0',
    'start_date':    TODAY,
    'end_date':      '',
    'status':        'active',
}


class TestAdminCreateSubscription:
    def test_create_subscription_success(self, admin_client, sample_esim):
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data=VALID_SUB, follow_redirects=True
        )
        assert r.status_code == 200
        assert b'added successfully' in r.data
        assert Subscription.query.filter_by(esim_id=sample_esim.id).first() is not None

    def test_create_subscription_with_end_date(self, admin_client, sample_esim):
        data = {**VALID_SUB, 'end_date': TOMORROW}
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data=data, follow_redirects=True
        )
        assert r.status_code == 200
        assert b'added successfully' in r.data

    def test_create_subscription_missing_plan_name(self, admin_client, sample_esim):
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data={**VALID_SUB, 'plan_name': ''},
            follow_redirects=True
        )
        assert b'required' in r.data

    def test_create_subscription_missing_data_limit(self, admin_client, sample_esim):
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data={**VALID_SUB, 'data_limit_gb': ''},
            follow_redirects=True
        )
        assert b'required' in r.data

    def test_create_subscription_invalid_data_limit(self, admin_client, sample_esim):
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data={**VALID_SUB, 'data_limit_gb': 'not-a-number'},
            follow_redirects=True
        )
        assert b'number' in r.data

    def test_create_subscription_negative_data_limit(self, admin_client, sample_esim):
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data={**VALID_SUB, 'data_limit_gb': '-1'},
            follow_redirects=True
        )
        assert b'positive' in r.data

    def test_create_subscription_exceeds_max_data_limit(self, admin_client, sample_esim):
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data={**VALID_SUB, 'data_limit_gb': '1025'},
            follow_redirects=True
        )
        assert b'1024' in r.data

    def test_create_subscription_at_max_data_limit(self, admin_client, sample_esim):
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data={**VALID_SUB, 'data_limit_gb': '1024'},
            follow_redirects=True
        )
        assert b'added successfully' in r.data

    def test_create_subscription_missing_start_date(self, admin_client, sample_esim):
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data={**VALID_SUB, 'start_date': ''},
            follow_redirects=True
        )
        assert b'required' in r.data

    def test_create_subscription_end_before_start(self, admin_client, sample_esim):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data={**VALID_SUB, 'end_date': yesterday},
            follow_redirects=True
        )
        assert b'after' in r.data

    def test_create_subscription_nonexistent_esim_404(self, admin_client):
        r = admin_client.post('/admin/esims/9999/subscriptions/new', data=VALID_SUB)
        assert r.status_code == 404

    def test_regular_user_cannot_create_subscription(self, user_client, sample_esim):
        r = user_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new',
            data=VALID_SUB
        )
        assert r.status_code == 403


class TestAdminEditSubscription:
    def test_edit_subscription_updates_plan(self, admin_client, sample_subscription):
        r = admin_client.post(
            f'/admin/subscriptions/{sample_subscription.id}/edit',
            data={
                'plan_name':     'Premium Plan',
                'data_limit_gb': '20.0',
                'start_date':    TODAY,
                'end_date':      '',
                'status':        'active',
                'is_confirmed':  '1',
            },
            follow_redirects=True
        )
        assert b'updated successfully' in r.data
        sub = _db.session.get(Subscription, sample_subscription.id)
        assert sub.plan_name == 'Premium Plan'
        assert sub.data_limit_gb == 20.0

    def test_edit_subscription_change_status(self, admin_client, sample_subscription):
        r = admin_client.post(
            f'/admin/subscriptions/{sample_subscription.id}/edit',
            data={
                'plan_name':     sample_subscription.plan_name,
                'data_limit_gb': str(sample_subscription.data_limit_gb),
                'start_date':    TODAY,
                'end_date':      '',
                'status':        'expired',
                'is_confirmed':  '1',
            },
            follow_redirects=True
        )
        assert b'updated successfully' in r.data
        sub = _db.session.get(Subscription, sample_subscription.id)
        assert sub.status == 'expired'

    def test_edit_subscription_nonexistent_returns_404(self, admin_client):
        assert admin_client.get('/admin/subscriptions/9999/edit').status_code == 404

    def test_edit_subscription_exceeds_max_data_limit(self, admin_client, sample_subscription):
        r = admin_client.post(
            f'/admin/subscriptions/{sample_subscription.id}/edit',
            data={
                'plan_name':     'Big Plan',
                'data_limit_gb': '2000',
                'start_date':    TODAY,
                'end_date':      '',
                'status':        'active',
            },
            follow_redirects=True
        )
        assert b'1024' in r.data

    def test_edit_subscription_invalid_status(self, admin_client, sample_subscription):
        r = admin_client.post(
            f'/admin/subscriptions/{sample_subscription.id}/edit',
            data={
                'plan_name':     'Plan',
                'data_limit_gb': '5',
                'start_date':    TODAY,
                'end_date':      '',
                'status':        'invalid_status',
            },
            follow_redirects=True
        )
        assert b'Status must be' in r.data


class TestAdminDeleteSubscription:
    def test_delete_subscription_success(self, admin_client, sample_subscription):
        sid = sample_subscription.id
        r = admin_client.post(
            f'/admin/subscriptions/{sid}/delete',
            follow_redirects=True
        )
        assert b'deleted' in r.data
        assert _db.session.get(Subscription, sid) is None

    def test_delete_nonexistent_subscription_returns_404(self, admin_client):
        assert admin_client.post('/admin/subscriptions/9999/delete').status_code == 404
