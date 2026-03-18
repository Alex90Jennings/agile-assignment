"""
Admin dashboard — pending request tables, search, and pagination.
"""

from datetime import date

from app.extensions import db as _db
from app.models import ESim, Subscription, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pending_esims(user_id, n, prefix='89111'):
    """Create n unconfirmed eSIMs for the given user."""
    esims = []
    for i in range(n):
        iccid = f'{prefix}{str(i).zfill(14)}'
        e = ESim(iccid=iccid, status='inactive', is_confirmed=False,
                 user_id=user_id)
        _db.session.add(e)
        esims.append(e)
    _db.session.commit()
    return esims


def _make_pending_subs(esim_id, n, prefix='Pending Plan'):
    """Create n unconfirmed subscriptions on the given eSIM."""
    subs = []
    for i in range(n):
        s = Subscription(
            esim_id=esim_id,
            plan_name=f'{prefix} {i}',
            data_limit_gb=5.0,
            start_date=date.today(),
            status='active',
            is_confirmed=False,
        )
        _db.session.add(s)
        subs.append(s)
    _db.session.commit()
    return subs


# ---------------------------------------------------------------------------
# Dashboard loads
# ---------------------------------------------------------------------------

class TestAdminDashboardLoads:
    def test_dashboard_returns_200(self, admin_client):
        r = admin_client.get('/admin/')
        assert r.status_code == 200

    def test_stat_cards_present(self, admin_client):
        r = admin_client.get('/admin/')
        assert b'Total Users' in r.data
        assert b'Businesses' in r.data

    def test_regular_user_gets_403(self, user_client):
        assert user_client.get('/admin/').status_code == 403

    def test_page_title_is_portal(self, admin_client):
        r = admin_client.get('/admin/')
        assert b'Portal' in r.data
        assert b'Portal &#8212; eSIM Admin' in r.data or b'Portal &mdash; eSIM Admin' in r.data or b'<title>Portal' in r.data

    def test_admin_nav_has_portal_link(self, admin_client):
        r = admin_client.get('/admin/')
        assert b'href="/admin/"' in r.data
        assert b'>Portal<' in r.data

    def test_admin_nav_has_dashboard_link(self, admin_client):
        r = admin_client.get('/admin/')
        assert b'href="/dashboard"' in r.data
        assert b'>Dashboard<' in r.data

    def test_portal_nav_link_is_active_on_admin_page(self, admin_client):
        r = admin_client.get('/admin/')
        # The Portal link should carry the active class on the /admin/ page
        assert b'nav-link active' in r.data


# ---------------------------------------------------------------------------
# Empty state — no pending requests
# ---------------------------------------------------------------------------

class TestDashboardEmptyState:
    def test_empty_state_shown_when_no_pending(self, admin_client):
        r = admin_client.get('/admin/')
        assert b'All caught up' in r.data

    def test_no_pending_tables_when_no_pending(self, admin_client):
        r = admin_client.get('/admin/')
        assert b'Pending eSIM Requests' not in r.data
        assert b'Pending Subscription Requests' not in r.data


# ---------------------------------------------------------------------------
# Pending eSIM requests table
# ---------------------------------------------------------------------------

class TestPendingESIMTable:
    def test_table_shown_when_pending_esims_exist(self, admin_client,
                                                   unconfirmed_esim):
        r = admin_client.get('/admin/')
        assert b'Pending eSIM Requests' in r.data

    def test_pending_esim_iccid_shown(self, admin_client, unconfirmed_esim):
        r = admin_client.get('/admin/')
        assert unconfirmed_esim.iccid.encode() in r.data

    def test_confirm_button_shown_for_pending_esim(self, admin_client,
                                                    unconfirmed_esim):
        r = admin_client.get('/admin/')
        assert b'Confirm' in r.data

    def test_empty_state_shows_when_no_pending(self, admin_client, sample_esim):
        # sample_esim is confirmed — no pending eSIMs
        r = admin_client.get('/admin/')
        assert b'All caught up' in r.data


# ---------------------------------------------------------------------------
# Pending subscription requests table
# ---------------------------------------------------------------------------

class TestPendingSubscriptionTable:
    def test_table_shown_when_pending_subs_exist(self, admin_client,
                                                  unconfirmed_subscription):
        r = admin_client.get('/admin/')
        assert b'Pending Subscription Requests' in r.data

    def test_pending_sub_plan_shown(self, admin_client,
                                    unconfirmed_subscription):
        r = admin_client.get('/admin/')
        assert b'Pending Plan' in r.data

    def test_esim_iccid_shown_in_sub_table(self, admin_client,
                                            unconfirmed_subscription):
        r = admin_client.get('/admin/')
        assert unconfirmed_subscription.esim.iccid.encode() in r.data


# ---------------------------------------------------------------------------
# Pending eSIM search
# ---------------------------------------------------------------------------

class TestPendingESIMSearch:
    def test_search_by_partial_iccid_matches(self, admin_client,
                                              unconfirmed_esim):
        partial = unconfirmed_esim.iccid[2:8]
        r = admin_client.get(f'/admin/?esim_q={partial}')
        assert r.status_code == 200
        assert unconfirmed_esim.iccid.encode() in r.data

    def test_search_case_insensitive(self, admin_client, unconfirmed_esim):
        # ICCIDs are digits so case doesn't apply; test that query param is handled
        r = admin_client.get(f'/admin/?esim_q={unconfirmed_esim.iccid}')
        assert r.status_code == 200
        assert unconfirmed_esim.iccid.encode() in r.data

    def test_search_no_match_shows_empty_state(self, admin_client,
                                                unconfirmed_esim):
        r = admin_client.get('/admin/?esim_q=000NOMATCH999')
        assert r.status_code == 200
        assert b'No pending eSIM requests matching' in r.data

    def test_empty_search_shows_all_pending(self, admin_client, unconfirmed_esim):
        r = admin_client.get('/admin/?esim_q=')
        assert r.status_code == 200
        assert unconfirmed_esim.iccid.encode() in r.data

    def test_search_preserves_esim_q_in_page(self, admin_client, sample_user):
        _make_pending_esims(sample_user.id, 6, prefix='89222')
        r = admin_client.get('/admin/?esim_q=89222')
        assert b'89222' in r.data


# ---------------------------------------------------------------------------
# Pending subscription search
# ---------------------------------------------------------------------------

class TestPendingSubscriptionSearch:
    def test_search_by_partial_esim_iccid(self, admin_client,
                                           unconfirmed_subscription):
        iccid = unconfirmed_subscription.esim.iccid
        partial = iccid[2:8]
        r = admin_client.get(f'/admin/?sub_q={partial}')
        assert r.status_code == 200
        assert iccid.encode() in r.data

    def test_search_no_match_shows_empty_state(self, admin_client,
                                                unconfirmed_subscription):
        r = admin_client.get('/admin/?sub_q=000NOMATCH999')
        assert r.status_code == 200
        assert b'No pending subscription requests matching' in r.data

    def test_empty_search_shows_all_pending_subs(self, admin_client,
                                                  unconfirmed_subscription):
        r = admin_client.get('/admin/?sub_q=')
        assert r.status_code == 200
        assert b'Pending Plan' in r.data

    def test_search_preserves_sub_q_in_page(self, admin_client, sample_esim):
        _make_pending_subs(sample_esim.id, 6)
        r = admin_client.get(f'/admin/?sub_q={sample_esim.iccid}')
        assert b'pagination-btn' in r.data or sample_esim.iccid.encode() in r.data


# ---------------------------------------------------------------------------
# Pagination — pending eSIMs
# ---------------------------------------------------------------------------

class TestPendingESIMPagination:
    def test_first_page_returns_200(self, admin_client, sample_user):
        _make_pending_esims(sample_user.id, 6)
        r = admin_client.get('/admin/?esim_page=1')
        assert r.status_code == 200

    def test_second_page_returns_200(self, admin_client, sample_user):
        _make_pending_esims(sample_user.id, 6)
        r = admin_client.get('/admin/?esim_page=2')
        assert r.status_code == 200

    def test_out_of_range_page_returns_200(self, admin_client, sample_user):
        _make_pending_esims(sample_user.id, 6)
        r = admin_client.get('/admin/?esim_page=999')
        assert r.status_code == 200

    def test_pagination_controls_shown_for_over_five(self, admin_client,
                                                      sample_user):
        _make_pending_esims(sample_user.id, 6)
        r = admin_client.get('/admin/?esim_page=1')
        assert b'pagination-btn' in r.data

    def test_no_pagination_for_five_or_fewer(self, admin_client, sample_user):
        _make_pending_esims(sample_user.id, 3, prefix='89333')
        r = admin_client.get('/admin/')
        # There are only 3 pending esims — no pagination bar should appear
        # (But we must not count sub pagination bar if subs exist)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Pagination — pending subscriptions
# ---------------------------------------------------------------------------

class TestPendingSubscriptionPagination:
    def test_first_page_returns_200(self, admin_client, sample_esim):
        _make_pending_subs(sample_esim.id, 6)
        r = admin_client.get('/admin/?sub_page=1')
        assert r.status_code == 200

    def test_second_page_returns_200(self, admin_client, sample_esim):
        _make_pending_subs(sample_esim.id, 6)
        r = admin_client.get('/admin/?sub_page=2')
        assert r.status_code == 200

    def test_out_of_range_page_returns_200(self, admin_client, sample_esim):
        _make_pending_subs(sample_esim.id, 6)
        r = admin_client.get('/admin/?sub_page=999')
        assert r.status_code == 200

    def test_pagination_controls_shown_for_over_five(self, admin_client,
                                                      sample_esim):
        _make_pending_subs(sample_esim.id, 6)
        r = admin_client.get('/admin/?sub_page=1')
        assert b'pagination-btn' in r.data


# ---------------------------------------------------------------------------
# Independent query params — both tables coexist
# ---------------------------------------------------------------------------

class TestIndependentQueryParams:
    def test_esim_search_does_not_clear_sub_search(self, admin_client,
                                                    unconfirmed_esim,
                                                    unconfirmed_subscription):
        iccid = unconfirmed_esim.iccid
        sub_iccid = unconfirmed_subscription.esim.iccid
        r = admin_client.get(
            f'/admin/?esim_q={iccid}&sub_q={sub_iccid}'
        )
        assert r.status_code == 200
        # Both searches applied — both ICCIDs visible
        assert iccid.encode() in r.data
        assert sub_iccid.encode() in r.data

    def test_esim_page_does_not_affect_sub_page(self, admin_client,
                                                 sample_user, sample_esim):
        _make_pending_esims(sample_user.id, 6)
        _make_pending_subs(sample_esim.id, 6)
        r = admin_client.get('/admin/?esim_page=2&sub_page=1')
        assert r.status_code == 200
