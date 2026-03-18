import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, redirect, url_for, request
from flask_login import current_user
from config import config
from app.extensions import db, login_manager
from app.observability import register_request_hooks, register_error_handlers


def _configure_logging(app):
    """Console handler always; rotating file handler outside test mode."""
    if app.logger.handlers:
        return
    fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    app.logger.propagate = False
    app.logger.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(logging.INFO)
    app.logger.addHandler(console)
    if not app.testing:
        log_dir = os.path.join(os.path.dirname(app.root_path), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'), maxBytes=1_048_576, backupCount=5
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.INFO)
        app.logger.addHandler(fh)


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    _configure_logging(app)

    db.init_app(app)
    login_manager.init_app(app)

    # Register observability hooks before blueprints and before the confirmation
    # gate so the request timer starts on every request, including redirected ones.
    register_request_hooks(app)
    register_error_handlers(app)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.main import main_bp
    app.register_blueprint(main_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp)

    with app.app_context():
        from app import models  # noqa: F401 — registers models with SQLAlchemy
        db.create_all()

    # ---------------------------------------------------------------------------
    # Confirmation gate — runs before every request.
    # Unconfirmed regular users may only access the pending page and logout.
    # Admins and confirmed users are not affected.
    # ---------------------------------------------------------------------------
    @app.before_request
    def _require_confirmed():
        if (
            current_user.is_authenticated
            and not current_user.is_admin
            and not current_user.is_confirmed
            and request.endpoint not in ('main.pending', 'auth.logout', 'static')
            and request.endpoint is not None
        ):
            app.logger.info(
                'UNCONFIRMED_REDIRECT user=%s endpoint=%s',
                current_user.email,
                request.endpoint,
            )
            return redirect(url_for('main.pending'))

    return app
