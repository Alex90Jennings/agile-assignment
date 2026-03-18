"""
Observability helpers — request tracing and error handlers with logging.

Two entry points called from create_app():

  register_request_hooks(app)
      Installs a before_request timer and an after_request logger so every
      non-static request produces one log line: method, path, status, duration.

  register_error_handlers(app)
      Replaces the bare error handlers with versions that log structured
      context (method, path, user, exception) before rendering the error page.

Both functions use app.logger via closure so they work correctly with Flask's
application factory pattern and do not depend on current_app being available.
"""

import time

from flask import g, request, render_template
from flask_login import current_user


def register_request_hooks(app):
    """Log method, path, status code, and duration for every non-static request."""

    @app.before_request
    def _start_timer():
        g.start_time = time.monotonic()

    @app.after_request
    def _log_request(response):
        # Skip static file serving — it adds noise without observability value.
        if request.endpoint == 'static':
            return response
        elapsed_ms = (time.monotonic() - g.get('start_time', time.monotonic())) * 1000
        app.logger.info(
            'REQUEST %s %s %d %.1fms',
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response


def register_error_handlers(app):
    """Register 400/403/404/500 handlers that log context before responding."""

    @app.errorhandler(400)
    def bad_request(e):
        app.logger.warning(
            'HTTP 400 method=%s path=%s', request.method, request.path
        )
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        user = current_user.email if current_user.is_authenticated else 'anonymous'
        app.logger.warning(
            'HTTP 403 method=%s path=%s user=%s', request.method, request.path, user
        )
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        app.logger.info(
            'HTTP 404 method=%s path=%s', request.method, request.path
        )
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        user = current_user.email if current_user.is_authenticated else 'anonymous'
        app.logger.error(
            'HTTP 500 method=%s path=%s user=%s exception=%s',
            request.method,
            request.path,
            user,
            str(e),
            exc_info=True,
        )
        return render_template('errors/500.html'), 500
