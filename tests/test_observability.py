"""
Tests for health check endpoint, error handlers, and request hooks.
"""

from app.extensions import db as _db


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        r = client.get('/health')
        assert r.status_code == 200

    def test_health_returns_json(self, client):
        r = client.get('/health')
        assert r.content_type.startswith('application/json')

    def test_health_status_ok(self, client):
        r = client.get('/health')
        data = r.get_json()
        assert data['status'] == 'ok'

    def test_health_includes_database_field(self, client):
        r = client.get('/health')
        data = r.get_json()
        assert 'database' in data

    def test_health_database_ok(self, client):
        r = client.get('/health')
        data = r.get_json()
        assert data['database'] == 'ok'

    def test_health_does_not_require_auth(self, client):
        # Unauthenticated requests must reach /health — it is for infra use.
        r = client.get('/health')
        assert r.status_code == 200

    def test_health_accessible_as_regular_user(self, user_client):
        r = user_client.get('/health')
        assert r.status_code == 200

    def test_health_accessible_as_admin(self, admin_client):
        r = admin_client.get('/health')
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Error handlers — 400 / 403 / 404
# ---------------------------------------------------------------------------

class TestErrorHandlers:
    def test_404_on_unknown_route(self, client):
        r = client.get('/this-route-does-not-exist-xyz')
        assert r.status_code == 404

    def test_404_response_contains_error_code(self, client):
        r = client.get('/no-such-page-abc')
        assert b'404' in r.data

    def test_403_for_regular_user_on_admin_route(self, user_client):
        r = user_client.get('/admin/')
        assert r.status_code == 403

    def test_403_response_contains_error_code(self, user_client):
        r = user_client.get('/admin/')
        assert b'403' in r.data

    def test_400_handler_renders_400_template(self, app):
        # Invoke the 400 handler directly inside a request context.
        # handle_http_exception returns the raw handler return value — a
        # (body_str, status_int) tuple — rather than a full Response object.
        from werkzeug.exceptions import BadRequest
        with app.test_request_context('/'):
            body, status = app.handle_http_exception(BadRequest())
        assert status == 400
        assert '400' in body


# ---------------------------------------------------------------------------
# Request hooks — verify they do not interfere with normal operation
# ---------------------------------------------------------------------------

class TestRequestHooks:
    def test_normal_user_request_unaffected(self, user_client):
        r = user_client.get('/dashboard')
        assert r.status_code == 200

    def test_normal_admin_request_unaffected(self, admin_client):
        r = admin_client.get('/admin/')
        assert r.status_code == 200

    def test_unauthenticated_request_unaffected(self, client):
        r = client.get('/auth/login')
        assert r.status_code == 200

    def test_redirect_response_unaffected(self, client):
        # / redirects to login — hooks must not break redirect responses.
        r = client.get('/')
        assert r.status_code in (301, 302)
