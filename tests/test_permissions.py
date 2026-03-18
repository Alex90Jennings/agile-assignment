"""
Permission tests — 403 for regular users, 302 redirects for unauthenticated
requests on all protected routes.
"""


# ---------------------------------------------------------------------------
# Admin routes — unauthenticated users should be redirected to login
# ---------------------------------------------------------------------------

ADMIN_GET_ROUTES = [
    '/admin/',
    '/admin/users',
    '/admin/users/new',
    '/admin/users/1',
    '/admin/users/1/edit',
    '/admin/businesses',
    '/admin/businesses/new',
    '/admin/businesses/1',
    '/admin/businesses/1/edit',
    '/admin/esims/1/edit',
    '/admin/esims/1/edit',
    '/admin/esims/1/subscriptions/new',
    '/admin/subscriptions/1/edit',
]

ADMIN_POST_ROUTES = [
    '/admin/users/new',
    '/admin/users/1/delete',
    '/admin/businesses/new',
    '/admin/businesses/1/delete',
    '/admin/esims/1/delete',
    '/admin/subscriptions/1/delete',
]


class TestUnauthenticatedRedirects:
    """Unauthenticated requests to protected GET routes redirect to login."""

    def test_admin_dashboard_redirects(self, client):
        r = client.get('/admin/', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_user_list_redirects(self, client):
        r = client.get('/admin/users', follow_redirects=False)
        assert r.status_code == 302

    def test_business_list_redirects(self, client):
        r = client.get('/admin/businesses', follow_redirects=False)
        assert r.status_code == 302

    def test_main_dashboard_redirects(self, client):
        r = client.get('/dashboard', follow_redirects=False)
        assert r.status_code == 302

    def test_profile_redirects(self, client):
        r = client.get('/profile', follow_redirects=False)
        assert r.status_code == 302

    def test_profile_edit_redirects(self, client):
        r = client.get('/profile/edit', follow_redirects=False)
        assert r.status_code == 302


class TestRegularUserForbidden:
    """Regular (non-admin) users get 403 on all admin routes."""

    def test_admin_dashboard_forbidden(self, user_client):
        assert user_client.get('/admin/').status_code == 403

    def test_user_list_forbidden(self, user_client):
        assert user_client.get('/admin/users').status_code == 403

    def test_create_user_get_forbidden(self, user_client):
        assert user_client.get('/admin/users/new').status_code == 403

    def test_create_user_post_forbidden(self, user_client):
        assert user_client.post('/admin/users/new', data={}).status_code == 403

    def test_user_detail_forbidden(self, user_client, sample_user):
        assert user_client.get(f'/admin/users/{sample_user.id}').status_code == 403

    def test_edit_user_get_forbidden(self, user_client, sample_user):
        assert user_client.get(f'/admin/users/{sample_user.id}/edit').status_code == 403

    def test_edit_user_post_forbidden(self, user_client, sample_user):
        assert user_client.post(f'/admin/users/{sample_user.id}/edit', data={}).status_code == 403

    def test_delete_user_forbidden(self, user_client, sample_user):
        assert user_client.post(f'/admin/users/{sample_user.id}/delete').status_code == 403

    def test_business_list_forbidden(self, user_client):
        assert user_client.get('/admin/businesses').status_code == 403

    def test_create_business_get_forbidden(self, user_client):
        assert user_client.get('/admin/businesses/new').status_code == 403

    def test_create_business_post_forbidden(self, user_client):
        assert user_client.post('/admin/businesses/new', data={}).status_code == 403

    def test_business_detail_forbidden(self, user_client, sample_business):
        assert user_client.get(f'/admin/businesses/{sample_business.id}').status_code == 403

    def test_edit_business_forbidden(self, user_client, sample_business):
        assert user_client.get(f'/admin/businesses/{sample_business.id}/edit').status_code == 403

    def test_delete_business_forbidden(self, user_client, sample_business):
        assert user_client.post(f'/admin/businesses/{sample_business.id}/delete').status_code == 403

    def test_create_esim_forbidden(self, user_client, sample_user):
        assert user_client.post(f'/admin/users/{sample_user.id}/esims/new', data={}).status_code == 403

    def test_edit_esim_forbidden(self, user_client, sample_esim):
        assert user_client.get(f'/admin/esims/{sample_esim.id}/edit').status_code == 403

    def test_delete_esim_forbidden(self, user_client, sample_esim):
        assert user_client.post(f'/admin/esims/{sample_esim.id}/delete').status_code == 403

    def test_create_subscription_forbidden(self, user_client, sample_esim):
        assert user_client.post(
            f'/admin/esims/{sample_esim.id}/subscriptions/new', data={}
        ).status_code == 403

    def test_edit_subscription_forbidden(self, user_client, sample_subscription):
        assert user_client.get(
            f'/admin/subscriptions/{sample_subscription.id}/edit'
        ).status_code == 403

    def test_delete_subscription_forbidden(self, user_client, sample_subscription):
        assert user_client.post(
            f'/admin/subscriptions/{sample_subscription.id}/delete'
        ).status_code == 403


class TestRegularUserOwnRoutes:
    """Regular users can access their own profile routes."""

    def test_own_dashboard_accessible(self, user_client):
        assert user_client.get('/dashboard').status_code == 200

    def test_own_profile_accessible(self, user_client):
        assert user_client.get('/profile').status_code == 200

    def test_own_profile_edit_accessible(self, user_client):
        assert user_client.get('/profile/edit').status_code == 200
