"""
Admin — eSIM create / edit / delete tests.
"""

from app.extensions import db as _db
from app.models import ESim


VALID_ESIM = {
    'iccid':  '8944501234567899999',
    'label':  'Test SIM',
    'status': 'active',
}


class TestAdminCreateESim:
    def test_create_esim_success(self, admin_client, sample_user):
        r = admin_client.post(
            f'/admin/users/{sample_user.id}/esims/new',
            data=VALID_ESIM, follow_redirects=True
        )
        assert r.status_code == 200
        assert b'added successfully' in r.data
        assert ESim.query.filter_by(iccid='8944501234567899999').first() is not None

    def test_create_esim_duplicate_iccid(self, admin_client, sample_user, sample_esim):
        r = admin_client.post(
            f'/admin/users/{sample_user.id}/esims/new',
            data={**VALID_ESIM, 'iccid': sample_esim.iccid},
            follow_redirects=True
        )
        assert b'already exists' in r.data

    def test_create_esim_invalid_iccid_too_short(self, admin_client, sample_user):
        r = admin_client.post(
            f'/admin/users/{sample_user.id}/esims/new',
            data={**VALID_ESIM, 'iccid': '12345'},
            follow_redirects=True
        )
        assert b'19' in r.data

    def test_create_esim_iccid_with_letters(self, admin_client, sample_user):
        r = admin_client.post(
            f'/admin/users/{sample_user.id}/esims/new',
            data={**VALID_ESIM, 'iccid': 'ABCDE1234567890123'},
            follow_redirects=True
        )
        assert b'19' in r.data or b'digits' in r.data

    def test_create_esim_missing_iccid(self, admin_client, sample_user):
        r = admin_client.post(
            f'/admin/users/{sample_user.id}/esims/new',
            data={**VALID_ESIM, 'iccid': ''},
            follow_redirects=True
        )
        assert b'required' in r.data

    def test_create_esim_nonexistent_user_404(self, admin_client):
        r = admin_client.post('/admin/users/9999/esims/new', data=VALID_ESIM)
        assert r.status_code == 404

    def test_regular_user_cannot_create_esim(self, user_client, sample_user):
        r = user_client.post(
            f'/admin/users/{sample_user.id}/esims/new',
            data=VALID_ESIM
        )
        assert r.status_code == 403


class TestAdminEditESim:
    def test_edit_esim_updates_label(self, admin_client, sample_esim):
        r = admin_client.post(f'/admin/esims/{sample_esim.id}/edit', data={
            'iccid':         sample_esim.iccid,
            'label':         'Updated Label',
            'status':        'inactive',
            'is_confirmed':  '1',
        }, follow_redirects=True)
        assert b'updated successfully' in r.data
        esim = _db.session.get(ESim, sample_esim.id)
        assert esim.label == 'Updated Label'
        assert esim.status == 'inactive'

    def test_edit_esim_nonexistent_returns_404(self, admin_client):
        assert admin_client.get('/admin/esims/9999/edit').status_code == 404

    def test_edit_esim_duplicate_iccid_rejected(self, admin_client,
                                                 sample_user, sample_esim):
        other = ESim(iccid='8944501234567891111', status='active',
                     user_id=sample_user.id)
        _db.session.add(other)
        _db.session.commit()
        r = admin_client.post(f'/admin/esims/{other.id}/edit', data={
            'iccid':        sample_esim.iccid,
            'label':        '',
            'status':       'active',
            'is_confirmed': '1',
        }, follow_redirects=True)
        assert b'already exists' in r.data


class TestAdminDeleteESim:
    def test_delete_esim_success(self, admin_client, sample_esim):
        eid = sample_esim.id
        r = admin_client.post(f'/admin/esims/{eid}/delete',
                              follow_redirects=True)
        assert b'deleted' in r.data
        assert _db.session.get(ESim, eid) is None

    def test_delete_esim_cascades_subscriptions(self, admin_client,
                                                 sample_esim, sample_subscription):
        from app.models import Subscription
        eid = sample_esim.id
        sid = sample_subscription.id
        admin_client.post(f'/admin/esims/{eid}/delete')
        assert _db.session.get(Subscription, sid) is None

    def test_delete_nonexistent_esim_returns_404(self, admin_client):
        assert admin_client.post('/admin/esims/9999/delete').status_code == 404
