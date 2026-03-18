import random
from datetime import date

from flask import render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_required, current_user
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import text

from app.main import main_bp
from app.extensions import db
from app.models import User, ESim, Subscription
from app.utils.validation import validate_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_profile(form, exclude_user_id):
    """Return (list_of_errors, cleaned_data_dict)."""
    errors = []

    first_name = form.get('first_name', '').strip()
    last_name = form.get('last_name', '').strip()
    email = form.get('email', '').strip().lower()

    if not first_name:
        errors.append('First name is required.')
    elif len(first_name) > 80:
        errors.append('First name must be 80 characters or fewer.')

    if not last_name:
        errors.append('Last name is required.')
    elif len(last_name) > 80:
        errors.append('Last name must be 80 characters or fewer.')

    if not email:
        errors.append('Email is required.')
    else:
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            errors.append('Please enter a valid email address.')
        else:
            existing = User.query.filter(
                User.email == email, User.id != exclude_user_id
            ).first()
            if existing:
                errors.append('That email is already in use by another account.')

    return errors, {'first_name': first_name, 'last_name': last_name, 'email': email}


def _generate_iccid():
    """Generate a unique 19-digit ICCID starting with 89."""
    while True:
        iccid = '89' + ''.join(str(random.randint(0, 9)) for _ in range(17))
        if not ESim.query.filter_by(iccid=iccid).first():
            return iccid


def _validate_esim_request(form):
    """Validate eSIM + initial subscription request form. Return (errors, data)."""
    errors = []

    label = form.get('label', '').strip()
    plan_name = form.get('plan_name', '').strip()
    data_limit_str = form.get('data_limit_gb', '').strip()
    start_date_str = form.get('start_date', '').strip()

    if label and len(label) > 100:
        errors.append('Label must be 100 characters or fewer.')

    if not plan_name:
        errors.append('Plan name is required.')
    elif len(plan_name) > 100:
        errors.append('Plan name must be 100 characters or fewer.')

    data_limit_gb = None
    if not data_limit_str:
        errors.append('Data limit is required.')
    else:
        try:
            data_limit_gb = float(data_limit_str)
            if data_limit_gb <= 0:
                errors.append('Data limit must be greater than 0.')
        except ValueError:
            errors.append('Data limit must be a number.')

    start_date = None
    if not start_date_str:
        errors.append('Start date is required.')
    else:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            errors.append('Start date must be a valid date (YYYY-MM-DD).')

    return errors, {
        'label': label or None,
        'plan_name': plan_name,
        'data_limit_gb': data_limit_gb,
        'start_date': start_date,
    }


def _validate_topup_request(form):
    """Validate subscription top-up request form. Return (errors, data)."""
    errors = []

    plan_name = form.get('plan_name', '').strip()
    data_limit_str = form.get('data_limit_gb', '').strip()
    start_date_str = form.get('start_date', '').strip()

    if not plan_name:
        errors.append('Plan name is required.')
    elif len(plan_name) > 100:
        errors.append('Plan name must be 100 characters or fewer.')

    data_limit_gb = None
    if not data_limit_str:
        errors.append('Data limit is required.')
    else:
        try:
            data_limit_gb = float(data_limit_str)
            if data_limit_gb <= 0:
                errors.append('Data limit must be greater than 0.')
        except ValueError:
            errors.append('Data limit must be a number.')

    start_date = None
    if not start_date_str:
        errors.append('Start date is required.')
    else:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            errors.append('Start date must be a valid date (YYYY-MM-DD).')

    return errors, {
        'plan_name': plan_name,
        'data_limit_gb': data_limit_gb,
        'start_date': start_date,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/pending')
@login_required
def pending():
    """Awaiting-confirmation holding page for unconfirmed users."""
    if current_user.is_confirmed or current_user.is_admin:
        return redirect(url_for('main.dashboard'))
    return render_template('main/pending.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    esims = (
        ESim.query
        .filter_by(user_id=current_user.id)
        .order_by(ESim.created_at.desc())
        .all()
    )
    return render_template('main/dashboard.html', esims=esims)


@main_bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html')


@main_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        errors, data = _validate_profile(request.form, current_user.id)

        new_password = request.form.get('new_password', '').strip()
        current_password = request.form.get('current_password', '').strip()

        if new_password:
            if not current_password:
                errors.append('Enter your current password to set a new one.')
            elif not current_user.check_password(current_password):
                errors.append('Current password is incorrect.')
            else:
                errors.extend(validate_password(new_password))

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('main/edit_profile.html', form=request.form)

        current_user.first_name = data['first_name']
        current_user.last_name = data['last_name']
        current_user.email = data['email']

        if new_password and not errors:
            current_user.set_password(new_password)

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('main.profile'))

    return render_template('main/edit_profile.html', form={
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'email': current_user.email,
    })


@main_bp.route('/esims/request', methods=['GET', 'POST'])
@login_required
def request_esim():
    """Regular user requests a new eSIM with an initial subscription."""
    if request.method == 'POST':
        errors, data = _validate_esim_request(request.form)

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('main/esim_request.html', form=request.form)

        iccid = _generate_iccid()
        esim = ESim(
            iccid=iccid,
            label=data['label'],
            status='inactive',
            is_confirmed=False,
            user_id=current_user.id,
        )
        db.session.add(esim)
        db.session.flush()  # get esim.id before adding subscription

        sub = Subscription(
            esim_id=esim.id,
            plan_name=data['plan_name'],
            data_limit_gb=data['data_limit_gb'],
            start_date=data['start_date'],
            status='active',
            is_confirmed=False,
        )
        db.session.add(sub)
        db.session.commit()

        current_app.logger.info(
            'ESIM_REQUEST user=%s iccid=%s', current_user.email, iccid
        )
        flash('eSIM request submitted. Awaiting admin approval.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('main/esim_request.html', form={})


@main_bp.route('/esims/<int:id>/topup', methods=['GET', 'POST'])
@login_required
def request_topup(id):
    """Regular user requests an additional subscription for an existing eSIM."""
    esim = ESim.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        errors, data = _validate_topup_request(request.form)

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('main/topup_request.html', esim=esim, form=request.form)

        sub = Subscription(
            esim_id=esim.id,
            plan_name=data['plan_name'],
            data_limit_gb=data['data_limit_gb'],
            start_date=data['start_date'],
            status='active',
            is_confirmed=False,
        )
        db.session.add(sub)
        db.session.commit()

        current_app.logger.info(
            'TOPUP_REQUEST user=%s esim_id=%s', current_user.email, esim.id
        )
        flash('Top-up request submitted. Awaiting admin approval.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('main/topup_request.html', esim=esim, form={})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@main_bp.route('/health')
def health():
    """Lightweight health-check endpoint for uptime monitoring and deployments.

    Returns JSON with overall status and database connectivity. No auth required.
    Does not appear in the main navigation — it is for infrastructure use only.
    """
    try:
        db.session.execute(text('SELECT 1'))
        db_status = 'ok'
    except Exception as exc:
        current_app.logger.error('HEALTH_CHECK db_error=%s', exc)
        db_status = 'error'

    overall = 'ok' if db_status == 'ok' else 'degraded'
    return jsonify({'status': overall, 'database': db_status}), 200
