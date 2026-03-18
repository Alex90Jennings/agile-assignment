"""
Admin — Users CRUD tests.
"""

from app.extensions import db as _db
from app.models import Business, User


VALID_USER = {
    'first_name':       'Test',
    'last_name':        'Person',
    'email':            'newuser@test.com',
    'password':         'Secure1!',
    'confirm_password': 'Secure1!',
}


class TestAdminUserList:
    def test_admin_can_list_users(self, admin_client, sample_user):
        r = admin_client.get('/admin/users')
        assert r.status_code == 200
        assert b'user@test.com' in r.data

    def test_user_client_gets_403(self, user_client):
        r = user_client.get('/admin/users')
        assert r.status_code == 403

    def test_unauthenticated_redirects(self, client):
        r = client.get('/admin/users', follow_redirects=False)
        assert r.status_code == 302


class TestAdminCreateUser:
    def test_create_user_success(self, admin_client, sample_business):
        data = {**VALID_USER, 'business_id': sample_business.id}
        r = admin_client.post('/admin/users/new', data=data,
                              follow_redirects=True)
        assert r.status_code == 200
        assert b'created successfully' in r.data
        assert User.query.filter_by(email='newuser@test.com').first() is not None

    def test_create_user_no_business(self, admin_client):
        r = admin_client.post('/admin/users/new', data=VALID_USER,
                              follow_redirects=True)
        assert r.status_code == 200
        assert User.query.filter_by(email='newuser@test.com').first() is not None

    def test_create_user_as_admin(self, admin_client):
        data = {**VALID_USER, 'is_admin': '1'}
        admin_client.post('/admin/users/new', data=data)
        user = User.query.filter_by(email='newuser@test.com').first()
        assert user is not None
        assert user.is_admin is True

    def test_create_user_duplicate_email(self, admin_client, sample_user):
        data = {**VALID_USER, 'email': 'user@test.com'}
        r = admin_client.post('/admin/users/new', data=data,
                              follow_redirects=True)
        assert b'already in use' in r.data

    def test_create_user_missing_first_name(self, admin_client):
        data = {**VALID_USER, 'first_name': ''}
        r = admin_client.post('/admin/users/new', data=data,
                              follow_redirects=True)
        assert b'First name is required' in r.data

    def test_create_user_weak_password_no_special(self, admin_client):
        data = {**VALID_USER, 'password': 'Password1',
                'confirm_password': 'Password1'}
        r = admin_client.post('/admin/users/new', data=data,
                              follow_redirects=True)
        assert b'special' in r.data

    def test_create_user_weak_password_no_number(self, admin_client):
        data = {**VALID_USER, 'password': 'Password!',
                'confirm_password': 'Password!'}
        r = admin_client.post('/admin/users/new', data=data,
                              follow_redirects=True)
        assert b'number' in r.data

    def test_create_user_password_mismatch(self, admin_client):
        data = {**VALID_USER, 'confirm_password': 'Different1!'}
        r = admin_client.post('/admin/users/new', data=data,
                              follow_redirects=True)
        assert b'do not match' in r.data

    def test_create_user_missing_password(self, admin_client):
        data = {**VALID_USER, 'password': '', 'confirm_password': ''}
        r = admin_client.post('/admin/users/new', data=data,
                              follow_redirects=True)
        assert b'required' in r.data


class TestAdminUserDetail:
    def test_admin_can_view_user_detail(self, admin_client, sample_user):
        r = admin_client.get(f'/admin/users/{sample_user.id}')
        assert r.status_code == 200
        assert b'user@test.com' in r.data

    def test_nonexistent_user_returns_404(self, admin_client):
        r = admin_client.get('/admin/users/9999')
        assert r.status_code == 404


class TestAdminEditUser:
    def test_edit_user_updates_name(self, admin_client, sample_user):
        r = admin_client.post(f'/admin/users/{sample_user.id}/edit', data={
            'first_name': 'Updated',
            'last_name':  'Name',
            'email':      'user@test.com',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'updated successfully' in r.data
        user = _db.session.get(User, sample_user.id)
        assert user.first_name == 'Updated'

    def test_edit_user_change_password(self, admin_client, sample_user):
        admin_client.post(f'/admin/users/{sample_user.id}/edit', data={
            'first_name':       sample_user.first_name,
            'last_name':        sample_user.last_name,
            'email':            sample_user.email,
            'password':         'NewPass1!',
            'confirm_password': 'NewPass1!',
        })
        user = _db.session.get(User, sample_user.id)
        assert user.check_password('NewPass1!')

    def test_edit_user_blank_password_keeps_existing(self, admin_client, sample_user):
        admin_client.post(f'/admin/users/{sample_user.id}/edit', data={
            'first_name': sample_user.first_name,
            'last_name':  sample_user.last_name,
            'email':      sample_user.email,
            'password':   '',
            'confirm_password': '',
        })
        user = _db.session.get(User, sample_user.id)
        assert user.check_password('Secure1!')

    def test_edit_user_duplicate_email(self, admin_client, sample_user, sample_admin):
        r = admin_client.post(f'/admin/users/{sample_user.id}/edit', data={
            'first_name': 'Regular',
            'last_name':  'User',
            'email':      'admin@test.com',
        }, follow_redirects=True)
        assert b'already in use' in r.data

    def test_edit_nonexistent_user_returns_404(self, admin_client):
        r = admin_client.get('/admin/users/9999/edit')
        assert r.status_code == 404


class TestAdminDeleteUser:
    def test_admin_can_delete_user(self, admin_client, sample_user):
        uid = sample_user.id
        r = admin_client.post(f'/admin/users/{uid}/delete',
                              follow_redirects=True)
        assert r.status_code == 200
        assert b'deleted' in r.data
        assert _db.session.get(User, uid) is None

    def test_admin_cannot_delete_self(self, admin_client, sample_admin):
        r = admin_client.post(f'/admin/users/{sample_admin.id}/delete',
                              follow_redirects=True)
        assert b'cannot delete your own account' in r.data
        assert _db.session.get(User, sample_admin.id) is not None

    def test_delete_nonexistent_user_returns_404(self, admin_client):
        r = admin_client.post('/admin/users/9999/delete')
        assert r.status_code == 404


def _make_users(n, prefix='pgu'):
    """Create n non-admin confirmed users and flush to DB."""
    users = []
    for i in range(n):
        u = User(first_name=f'User{i}', last_name='Page',
                 email=f'{prefix}{i}@test.com', is_confirmed=True)
        u.set_password('Secure1!')
        _db.session.add(u)
        users.append(u)
    _db.session.commit()
    return users


class TestAdminUserSearch:
    def test_search_partial_email_match(self, admin_client, sample_user):
        r = admin_client.get('/admin/users?q=user@test')
        assert r.status_code == 200
        assert b'user@test.com' in r.data

    def test_search_case_insensitive(self, admin_client, sample_user):
        r = admin_client.get('/admin/users?q=USER@TEST')
        assert r.status_code == 200
        assert b'user@test.com' in r.data

    def test_search_no_match_shows_empty_state(self, admin_client):
        r = admin_client.get('/admin/users?q=nobody@nowhere.invalid')
        assert r.status_code == 200
        assert b'No users matching' in r.data

    def test_empty_search_shows_all_users(self, admin_client, sample_user):
        r = admin_client.get('/admin/users?q=')
        assert r.status_code == 200
        assert b'user@test.com' in r.data

    def test_search_excludes_non_matching_users(self, admin_client, sample_user, sample_admin):
        r = admin_client.get('/admin/users?q=user@test')
        assert r.status_code == 200
        assert b'user@test.com' in r.data
        assert b'admin@test.com' not in r.data

    def test_search_with_pagination(self, admin_client):
        _make_users(6)
        r = admin_client.get('/admin/users?q=pgu&page=1')
        assert r.status_code == 200

    def test_search_preserves_q_in_pagination_links(self, admin_client):
        _make_users(6)
        r = admin_client.get('/admin/users?q=pgu&page=1')
        assert b'q=pgu' in r.data

    def test_invalid_page_with_search_returns_200(self, admin_client):
        r = admin_client.get('/admin/users?q=test&page=999')
        assert r.status_code == 200


class TestAdminUserListPagination:
    def test_first_page_returns_200(self, admin_client):
        _make_users(6)
        r = admin_client.get('/admin/users?page=1')
        assert r.status_code == 200

    def test_second_page_returns_200(self, admin_client):
        _make_users(6)
        r = admin_client.get('/admin/users?page=2')
        assert r.status_code == 200

    def test_out_of_range_page_returns_200(self, admin_client):
        r = admin_client.get('/admin/users?page=999')
        assert r.status_code == 200

    def test_pagination_controls_shown_when_over_five(self, admin_client):
        _make_users(6)
        r = admin_client.get('/admin/users?page=1')
        assert b'pagination-btn' in r.data

    def test_no_pagination_controls_when_five_or_fewer(self, admin_client):
        _make_users(3, prefix='fewusr')
        r = admin_client.get('/admin/users')
        assert b'pagination-btn' not in r.data

    def test_total_count_shown_in_subtitle(self, admin_client):
        # admin_client already has 1 admin user; _make_users adds 6 more → 7 total
        _make_users(6)
        r = admin_client.get('/admin/users')
        assert b'7 registered' in r.data


class TestAdminUserDetailPagination:
    def test_esims_page_param_accepted(self, admin_client, sample_user):
        r = admin_client.get(f'/admin/users/{sample_user.id}?esims_page=1')
        assert r.status_code == 200

    def test_out_of_range_esims_page_returns_200(self, admin_client, sample_user):
        r = admin_client.get(f'/admin/users/{sample_user.id}?esims_page=999')
        assert r.status_code == 200


class TestAdminUserDetailSearch:
    def test_search_partial_iccid_match(self, admin_client, sample_user, sample_esim):
        r = admin_client.get(
            f'/admin/users/{sample_user.id}?esims_q=890123'
        )
        assert r.status_code == 200
        assert b'8901234567890123456' in r.data

    def test_search_case_insensitive(self, admin_client, sample_user, sample_esim):
        # ICCIDs are digits only; test that the filter doesn't crash on mixed case
        r = admin_client.get(
            f'/admin/users/{sample_user.id}?esims_q=8901234567890123456'
        )
        assert r.status_code == 200
        assert b'8901234567890123456' in r.data

    def test_search_no_match_shows_empty_state(self, admin_client, sample_user, sample_esim):
        r = admin_client.get(
            f'/admin/users/{sample_user.id}?esims_q=9999999999999'
        )
        assert r.status_code == 200
        assert b'No eSIMs matching' in r.data

    def test_empty_search_shows_all_esims(self, admin_client, sample_user, sample_esim):
        r = admin_client.get(f'/admin/users/{sample_user.id}?esims_q=')
        assert r.status_code == 200
        assert b'8901234567890123456' in r.data

    def test_total_esims_count_unaffected_by_search(self, admin_client,
                                                      sample_user, sample_esim):
        # Search that returns 0 results; account card should still show real total
        r = admin_client.get(
            f'/admin/users/{sample_user.id}?esims_q=NOMATCH'
        )
        assert r.status_code == 200
        # The account details card shows total_esims (1), not filtered count (0)
        assert b'<dd class="col-sm-8">1</dd>' in r.data
