"""
Unit tests for SQLAlchemy models.
Covers: field defaults, password hashing, relationships, repr strings.

Note: no `with app.app_context():` blocks needed here — the autouse
`db_ctx` fixture in conftest.py provides an active context for every test.
"""

from datetime import date

import pytest

from app.extensions import db as _db
from app.models import Business, ESim, Subscription, User


class TestUserModel:
    def test_password_is_hashed(self, sample_user):
        assert sample_user.password_hash != 'Secure1!'

    def test_check_password_correct(self, sample_user):
        assert sample_user.check_password('Secure1!') is True

    def test_check_password_incorrect(self, sample_user):
        assert sample_user.check_password('wrongpassword') is False

    def test_full_name_property(self, sample_user):
        assert sample_user.full_name == 'Regular User'

    def test_is_admin_default_false(self):
        u = User(email='new@test.com', first_name='New', last_name='User')
        u.set_password('password123')
        _db.session.add(u)
        _db.session.commit()
        assert u.is_admin is False

    def test_repr_contains_email(self, sample_user):
        assert 'user@test.com' in repr(sample_user)

    def test_created_at_set_on_insert(self, sample_user):
        assert sample_user.created_at is not None

    def test_updated_at_set_on_insert(self, sample_user):
        assert sample_user.updated_at is not None


class TestBusinessModel:
    def test_repr_contains_name(self, sample_business):
        assert 'Test Corp' in repr(sample_business)

    def test_users_relationship(self, sample_business, sample_user):
        biz = _db.session.get(Business, sample_business.id)
        assert any(u.id == sample_user.id for u in biz.users)

    def test_created_at_set_on_insert(self, sample_business):
        assert sample_business.created_at is not None


class TestESimModel:
    def test_repr_contains_iccid(self, sample_esim):
        assert '8901234567890123456' in repr(sample_esim)

    def test_default_status_is_active(self, sample_user):
        e = ESim(iccid='0000000000000000001', user_id=sample_user.id)
        _db.session.add(e)
        _db.session.commit()
        assert e.status == 'active'

    def test_user_backref(self, sample_esim, sample_user):
        e = _db.session.get(ESim, sample_esim.id)
        assert e.user.id == sample_user.id

    def test_created_at_set_on_insert(self, sample_esim):
        assert sample_esim.created_at is not None

    def test_valid_statuses_constant(self):
        assert 'active' in ESim.VALID_STATUSES
        assert 'inactive' in ESim.VALID_STATUSES
        assert 'suspended' in ESim.VALID_STATUSES


class TestSubscriptionModel:
    def test_repr_contains_plan_name(self, sample_subscription):
        assert 'Basic Plan' in repr(sample_subscription)

    def test_default_status_is_active(self, sample_esim):
        s = Subscription(
            esim_id=sample_esim.id,
            plan_name='Test Plan',
            data_limit_gb=10.0,
            start_date=date.today(),
        )
        _db.session.add(s)
        _db.session.commit()
        assert s.status == 'active'

    def test_esim_backref(self, sample_subscription, sample_esim):
        s = _db.session.get(Subscription, sample_subscription.id)
        assert s.esim.id == sample_esim.id

    def test_created_at_set_on_insert(self, sample_subscription):
        assert sample_subscription.created_at is not None

    def test_valid_statuses_constant(self):
        assert 'active' in Subscription.VALID_STATUSES
        assert 'expired' in Subscription.VALID_STATUSES
        assert 'cancelled' in Subscription.VALID_STATUSES


class TestCascadeDelete:
    def test_deleting_user_deletes_esims(self, sample_user, sample_esim):
        esim_id = sample_esim.id
        user = _db.session.get(User, sample_user.id)
        _db.session.delete(user)
        _db.session.commit()
        assert _db.session.get(ESim, esim_id) is None

    def test_deleting_esim_deletes_subscriptions(self, sample_esim, sample_subscription):
        sub_id = sample_subscription.id
        esim = _db.session.get(ESim, sample_esim.id)
        _db.session.delete(esim)
        _db.session.commit()
        assert _db.session.get(Subscription, sub_id) is None
