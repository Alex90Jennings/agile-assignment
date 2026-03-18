"""
Admin — Businesses CRUD tests.
"""

from app.extensions import db as _db
from app.models import Business, ESim, User


VALID_BIZ = {'name': 'New Corp', 'registration_number': 'REG-NEW'}


class TestAdminBusinessList:
    def test_admin_can_list_businesses(self, admin_client, sample_business):
        r = admin_client.get('/admin/businesses')
        assert r.status_code == 200
        assert b'Test Corp' in r.data

    def test_regular_user_gets_403(self, user_client):
        assert user_client.get('/admin/businesses').status_code == 403


class TestAdminCreateBusiness:
    def test_create_business_success(self, admin_client):
        r = admin_client.post('/admin/businesses/new', data=VALID_BIZ,
                              follow_redirects=True)
        assert r.status_code == 200
        assert b'created successfully' in r.data
        assert Business.query.filter_by(name='New Corp').first() is not None

    def test_create_business_no_reg_number(self, admin_client):
        r = admin_client.post('/admin/businesses/new',
                              data={'name': 'No Reg Corp'},
                              follow_redirects=True)
        assert r.status_code == 200
        assert Business.query.filter_by(name='No Reg Corp').first() is not None

    def test_create_business_missing_name(self, admin_client):
        r = admin_client.post('/admin/businesses/new',
                              data={'name': '', 'registration_number': 'X'},
                              follow_redirects=True)
        assert b'required' in r.data

    def test_create_business_duplicate_reg_number(self, admin_client, sample_business):
        r = admin_client.post('/admin/businesses/new',
                              data={'name': 'Other', 'registration_number': 'TEST-001'},
                              follow_redirects=True)
        assert b'already in use' in r.data


class TestAdminBusinessDetail:
    def test_admin_can_view_business(self, admin_client, sample_business):
        r = admin_client.get(f'/admin/businesses/{sample_business.id}')
        assert r.status_code == 200
        assert b'Test Corp' in r.data

    def test_nonexistent_business_returns_404(self, admin_client):
        assert admin_client.get('/admin/businesses/9999').status_code == 404


class TestAdminEditBusiness:
    def test_edit_business_updates_name(self, admin_client, sample_business):
        r = admin_client.post(f'/admin/businesses/{sample_business.id}/edit',
                              data={'name': 'Updated Corp', 'registration_number': ''},
                              follow_redirects=True)
        assert b'updated successfully' in r.data
        biz = _db.session.get(Business, sample_business.id)
        assert biz.name == 'Updated Corp'

    def test_edit_business_duplicate_reg_number(self, admin_client):
        b1 = Business(name='B1', registration_number='R-001')
        b2 = Business(name='B2', registration_number='R-002')
        _db.session.add_all([b1, b2])
        _db.session.commit()
        r = admin_client.post(f'/admin/businesses/{b2.id}/edit',
                              data={'name': 'B2', 'registration_number': 'R-001'},
                              follow_redirects=True)
        assert b'already in use' in r.data


class TestAdminDeleteBusiness:
    def test_delete_empty_business(self, admin_client, sample_business):
        # sample_business has users (sample_user needs it), so create a standalone one
        biz = Business(name='Standalone')
        _db.session.add(biz)
        _db.session.commit()
        bid = biz.id
        r = admin_client.post(f'/admin/businesses/{bid}/delete',
                              follow_redirects=True)
        assert b'deleted' in r.data
        assert _db.session.get(Business, bid) is None

    def test_cannot_delete_business_with_users(self, admin_client,
                                               sample_business, sample_user):
        r = admin_client.post(
            f'/admin/businesses/{sample_business.id}/delete',
            follow_redirects=True
        )
        assert b'still has' in r.data
        assert _db.session.get(Business, sample_business.id) is not None

    def test_delete_nonexistent_returns_404(self, admin_client):
        assert admin_client.post('/admin/businesses/9999/delete').status_code == 404


def _make_businesses(n, prefix='pgbiz'):
    """Create n businesses and flush to DB."""
    bizs = []
    for i in range(n):
        b = Business(name=f'{prefix}{i}')
        _db.session.add(b)
        bizs.append(b)
    _db.session.commit()
    return bizs


class TestAdminBusinessListSearch:
    def test_search_partial_name_match(self, admin_client, sample_business):
        r = admin_client.get('/admin/businesses?q=Test')
        assert r.status_code == 200
        assert b'Test Corp' in r.data

    def test_search_case_insensitive(self, admin_client, sample_business):
        r = admin_client.get('/admin/businesses?q=test corp')
        assert r.status_code == 200
        assert b'Test Corp' in r.data

    def test_search_no_match_shows_empty_state(self, admin_client):
        r = admin_client.get('/admin/businesses?q=NOMATCH_XYZ')
        assert r.status_code == 200
        assert b'No businesses matching' in r.data

    def test_empty_search_shows_all_businesses(self, admin_client, sample_business):
        r = admin_client.get('/admin/businesses?q=')
        assert r.status_code == 200
        assert b'Test Corp' in r.data

    def test_search_excludes_non_matching(self, admin_client, sample_business):
        other = Business(name='Other Corp')
        _db.session.add(other)
        _db.session.commit()
        r = admin_client.get('/admin/businesses?q=Test')
        assert b'Test Corp' in r.data
        assert b'Other Corp' not in r.data

    def test_search_with_pagination(self, admin_client):
        _make_businesses(6, prefix='SearchBiz')
        r = admin_client.get('/admin/businesses?q=SearchBiz&page=1')
        assert r.status_code == 200

    def test_search_preserves_q_in_pagination_links(self, admin_client):
        _make_businesses(6, prefix='QBiz')
        r = admin_client.get('/admin/businesses?q=QBiz&page=1')
        assert b'q=QBiz' in r.data

    def test_invalid_page_with_search_returns_200(self, admin_client):
        r = admin_client.get('/admin/businesses?q=test&page=999')
        assert r.status_code == 200


class TestAdminBusinessListPagination:
    def test_first_page_returns_200(self, admin_client):
        _make_businesses(6)
        r = admin_client.get('/admin/businesses?page=1')
        assert r.status_code == 200

    def test_second_page_returns_200(self, admin_client):
        _make_businesses(6)
        r = admin_client.get('/admin/businesses?page=2')
        assert r.status_code == 200

    def test_out_of_range_page_returns_200(self, admin_client):
        r = admin_client.get('/admin/businesses?page=999')
        assert r.status_code == 200

    def test_pagination_controls_shown_when_over_five(self, admin_client):
        _make_businesses(6)
        r = admin_client.get('/admin/businesses?page=1')
        assert b'pagination-btn' in r.data

    def test_no_pagination_controls_when_five_or_fewer(self, admin_client):
        _make_businesses(3, prefix='fewbiz')
        r = admin_client.get('/admin/businesses')
        assert b'pagination-btn' not in r.data

    def test_total_count_shown_in_subtitle(self, admin_client):
        # admin_client already has 1 business (sample_business); _make_businesses adds 6 → 7 total
        _make_businesses(6)
        r = admin_client.get('/admin/businesses')
        assert b'7 registered' in r.data


class TestAdminBusinessDetailPagination:
    def test_page_param_accepted(self, admin_client, sample_business):
        r = admin_client.get(f'/admin/businesses/{sample_business.id}?page=1')
        assert r.status_code == 200

    def test_out_of_range_page_returns_200(self, admin_client, sample_business):
        r = admin_client.get(f'/admin/businesses/{sample_business.id}?page=999')
        assert r.status_code == 200


def _make_users_for_biz(business_id, n, prefix='bzusr'):
    """Create n confirmed users assigned to the given business."""
    for i in range(n):
        u = User(first_name=f'U{i}', last_name='Biz',
                 email=f'{prefix}{i}@test.com',
                 is_confirmed=True, business_id=business_id)
        u.set_password('Secure1!')
        _db.session.add(u)
    _db.session.commit()


class TestAdminBusinessDetailSearch:
    def test_search_partial_email_match(self, admin_client, sample_business, sample_user):
        r = admin_client.get(
            f'/admin/businesses/{sample_business.id}?q=user@test'
        )
        assert r.status_code == 200
        assert b'user@test.com' in r.data

    def test_search_case_insensitive(self, admin_client, sample_business, sample_user):
        r = admin_client.get(
            f'/admin/businesses/{sample_business.id}?q=USER@TEST'
        )
        assert r.status_code == 200
        assert b'user@test.com' in r.data

    def test_search_no_match_shows_empty_state(self, admin_client, sample_business):
        r = admin_client.get(
            f'/admin/businesses/{sample_business.id}?q=nobody@nowhere.invalid'
        )
        assert r.status_code == 200
        assert b'No users matching' in r.data

    def test_empty_search_shows_all_users(self, admin_client, sample_business, sample_user):
        r = admin_client.get(f'/admin/businesses/{sample_business.id}?q=')
        assert r.status_code == 200
        assert b'user@test.com' in r.data

    def test_search_with_pagination(self, admin_client, sample_business):
        _make_users_for_biz(sample_business.id, 6)
        r = admin_client.get(
            f'/admin/businesses/{sample_business.id}?q=bzusr&page=1'
        )
        assert r.status_code == 200

    def test_search_preserves_q_in_pagination_links(self, admin_client, sample_business):
        _make_users_for_biz(sample_business.id, 6)
        r = admin_client.get(
            f'/admin/businesses/{sample_business.id}?q=bzusr&page=1'
        )
        assert b'q=bzusr' in r.data

    def test_invalid_page_with_search_returns_200(self, admin_client, sample_business):
        r = admin_client.get(
            f'/admin/businesses/{sample_business.id}?q=test&page=999'
        )
        assert r.status_code == 200

    def test_total_users_count_unaffected_by_search(self, admin_client,
                                                     sample_business, sample_user):
        # Details card and heading always reflect total, not filtered count
        r = admin_client.get(
            f'/admin/businesses/{sample_business.id}?q=admin@test'
        )
        # sample_business has sample_user + sample_admin; search returns 1
        # but "Assigned Users (2)" heading should still show 2
        assert b'Assigned Users (2)' in r.data


class TestAdminDeleteAllUsers:
    def test_delete_all_users_success(self, admin_client, sample_business, sample_user):
        # sample_business has sample_admin (excluded as self) + sample_user → deletes 1
        uid = sample_user.id
        r = admin_client.post(
            f'/admin/businesses/{sample_business.id}/delete_all_users',
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b'deleted' in r.data
        assert _db.session.get(User, uid) is None

    def test_delete_all_users_when_none_shows_info(self, admin_client):
        # Create a business with no users at all
        biz = Business(name='Empty Biz')
        _db.session.add(biz)
        _db.session.commit()
        r = admin_client.post(
            f'/admin/businesses/{biz.id}/delete_all_users',
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b'No users to delete' in r.data

    def test_delete_all_users_requires_admin(self, user_client, sample_business):
        r = user_client.post(
            f'/admin/businesses/{sample_business.id}/delete_all_users'
        )
        assert r.status_code == 403

    def test_delete_all_users_only_accepts_post(self, admin_client, sample_business):
        r = admin_client.get(
            f'/admin/businesses/{sample_business.id}/delete_all_users'
        )
        assert r.status_code == 405

    def test_delete_all_users_nonexistent_business_returns_404(self, admin_client):
        r = admin_client.post('/admin/businesses/9999/delete_all_users')
        assert r.status_code == 404

    def test_delete_all_users_cascades_esims(self, admin_client, sample_esim):
        esim_id = sample_esim.id
        business_id = sample_esim.user.business_id
        admin_client.post(
            f'/admin/businesses/{business_id}/delete_all_users',
            follow_redirects=True,
        )
        assert _db.session.get(ESim, esim_id) is None

    def test_delete_all_users_does_not_delete_business(self,
                                                        admin_client,
                                                        sample_business,
                                                        sample_user):
        bid = sample_business.id
        admin_client.post(
            f'/admin/businesses/{bid}/delete_all_users',
            follow_redirects=True,
        )
        assert _db.session.get(Business, bid) is not None

    def test_delete_all_users_excludes_current_admin(self,
                                                      admin_client,
                                                      sample_admin,
                                                      sample_business):
        # Only the admin is in this business; action should leave them intact
        admin_id = sample_admin.id
        admin_client.post(
            f'/admin/businesses/{sample_business.id}/delete_all_users',
            follow_redirects=True,
        )
        assert _db.session.get(User, admin_id) is not None
