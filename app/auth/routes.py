from flask import render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError

from app.auth import auth_bp
from app.extensions import db
from app.models import User
from app.utils.validation import validate_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_register(form):
    """Return (list_of_errors, cleaned_data_dict)."""
    errors = []

    first_name = form.get('first_name', '').strip()
    last_name = form.get('last_name', '').strip()
    email = form.get('email', '').strip().lower()
    password = form.get('password', '')
    confirm = form.get('confirm_password', '')

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

    errors.extend(validate_password(password))

    if password and not errors and password != confirm:
        errors.append('Passwords do not match.')

    return errors, {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        errors, data = _validate_register(request.form)

        if not errors:
            if User.query.filter_by(email=data['email']).first():
                errors.append('That email is already registered. Please log in.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html', form=request.form)

        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            is_confirmed=False,  # self-registered users require admin approval
        )
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        current_app.logger.info('REGISTER email=%s', data['email'])
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form={})


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.is_admin
                        else url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html', form=request.form)

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            current_app.logger.warning('LOGIN_FAILED email=%s', email)
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', form=request.form)

        login_user(user)
        current_app.logger.info('LOGIN_SUCCESS user=%s', user.email)
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('admin.dashboard') if user.is_admin
                        else url_for('main.dashboard'))

    return render_template('auth/login.html', form={})


@auth_bp.route('/logout')
@login_required
def logout():
    current_app.logger.info('LOGOUT user=%s', current_user.email)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
