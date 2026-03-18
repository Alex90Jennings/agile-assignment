"""
Tests for admin confirm_esim and confirm_subscription endpoints.
Covers: successful confirmation, state changes, redirect targets, permissions.
"""

from app.extensions import db as _db
from app.models import ESim, Subscription


class TestConfirmESim:
    def test_confirm_esim_sets_is_confirmed(self, admin_client, unconfirmed_esim):
        admin_client.post(f'/admin/esims/{unconfirmed_esim.id}/confirm')
        esim = _db.session.get(ESim, unconfirmed_esim.id)
        assert esim.is_confirmed is True

    def test_confirm_esim_sets_status_active(self, admin_client, unconfirmed_esim):
        admin_client.post(f'/admin/esims/{unconfirmed_esim.id}/confirm')
        esim = _db.session.get(ESim, unconfirmed_esim.id)
        assert esim.status == 'active'

    def test_confirm_esim_shows_success_flash(self, admin_client, unconfirmed_esim):
        r = admin_client.post(
            f'/admin/esims/{unconfirmed_esim.id}/confirm',
            follow_redirects=True
        )
        assert b'confirmed' in r.data

    def test_confirm_esim_redirects_to_user_detail(self, admin_client, unconfirmed_esim):
        r = admin_client.post(
            f'/admin/esims/{unconfirmed_esim.id}/confirm',
            follow_redirects=False
        )
        assert r.status_code == 302
        assert f'/admin/users/{unconfirmed_esim.user_id}' in r.headers['Location']

    def test_confirm_nonexistent_esim_returns_404(self, admin_client):
        assert admin_client.post('/admin/esims/9999/confirm').status_code == 404

    def test_confirm_esim_requires_admin(self, user_client, unconfirmed_esim):
        r = user_client.post(f'/admin/esims/{unconfirmed_esim.id}/confirm')
        assert r.status_code == 403

    def test_confirm_esim_only_accepts_post(self, admin_client, unconfirmed_esim):
        r = admin_client.get(f'/admin/esims/{unconfirmed_esim.id}/confirm')
        assert r.status_code == 405

    def test_confirm_already_confirmed_esim_is_idempotent(self, admin_client, sample_esim):
        # Confirming an already-confirmed eSIM should not error
        r = admin_client.post(
            f'/admin/esims/{sample_esim.id}/confirm',
            follow_redirects=True
        )
        assert r.status_code == 200
        esim = _db.session.get(ESim, sample_esim.id)
        assert esim.is_confirmed is True


class TestConfirmSubscription:
    def test_confirm_subscription_sets_is_confirmed(self, admin_client,
                                                      unconfirmed_subscription):
        admin_client.post(f'/admin/subscriptions/{unconfirmed_subscription.id}/confirm')
        sub = _db.session.get(Subscription, unconfirmed_subscription.id)
        assert sub.is_confirmed is True

    def test_confirm_subscription_shows_success_flash(self, admin_client,
                                                        unconfirmed_subscription):
        r = admin_client.post(
            f'/admin/subscriptions/{unconfirmed_subscription.id}/confirm',
            follow_redirects=True
        )
        assert b'confirmed' in r.data

    def test_confirm_subscription_redirects_to_user_detail(self, admin_client,
                                                             unconfirmed_subscription):
        r = admin_client.post(
            f'/admin/subscriptions/{unconfirmed_subscription.id}/confirm',
            follow_redirects=False
        )
        assert r.status_code == 302
        expected_user_id = unconfirmed_subscription.esim.user_id
        assert f'/admin/users/{expected_user_id}' in r.headers['Location']

    def test_confirm_nonexistent_subscription_returns_404(self, admin_client):
        assert admin_client.post('/admin/subscriptions/9999/confirm').status_code == 404

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

    def test_confirm_already_confirmed_subscription_is_idempotent(self, admin_client,
                                                                    sample_subscription):
        r = admin_client.post(
            f'/admin/subscriptions/{sample_subscription.id}/confirm',
            follow_redirects=True
        )
        assert r.status_code == 200
        sub = _db.session.get(Subscription, sample_subscription.id)
        assert sub.is_confirmed is True
