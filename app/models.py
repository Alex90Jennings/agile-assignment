from datetime import datetime, UTC
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


def _now():
    return datetime.now(UTC)


class Business(db.Model):
    __tablename__ = 'businesses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    users = db.relationship('User', backref='business', lazy=True)

    def __repr__(self):
        return f'<Business {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    # True  = approved; can access the full application.
    # False = awaiting admin confirmation (set on self-registration).
    # Admin-created users start confirmed; self-registered users start unconfirmed.
    is_confirmed = db.Column(db.Boolean, default=True, nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    esims = db.relationship(
        'ESim', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __repr__(self):
        return f'<User {self.email}>'


class ESim(db.Model):
    __tablename__ = 'esims'

    VALID_STATUSES = ('active', 'inactive', 'suspended')

    id = db.Column(db.Integer, primary_key=True)
    iccid = db.Column(db.String(22), unique=True, nullable=False)
    label = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')
    # True = admin-created or admin-confirmed; False = user-requested, awaiting approval.
    is_confirmed = db.Column(db.Boolean, default=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    subscriptions = db.relationship(
        'Subscription', backref='esim', lazy=True, cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<ESim {self.iccid}>'


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    VALID_STATUSES = ('active', 'expired', 'cancelled')

    id = db.Column(db.Integer, primary_key=True)
    esim_id = db.Column(db.Integer, db.ForeignKey('esims.id'), nullable=False)
    plan_name = db.Column(db.String(100), nullable=False)
    data_limit_gb = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')
    # True = admin-created or admin-confirmed; False = user-requested, awaiting approval.
    is_confirmed = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    def __repr__(self):
        return f'<Subscription {self.plan_name} on ESim {self.esim_id}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
