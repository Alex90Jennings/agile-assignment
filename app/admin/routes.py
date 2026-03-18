from datetime import date
from functools import wraps

from email_validator import validate_email, EmailNotValidError
from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.admin import admin_bp
from app.extensions import db
from app.models import Business, ESim, Subscription, User
from app.utils.pagination import get_page, get_search_term, paginate_query
from app.utils.validation import validate_password


# ---------------------------------------------------------------------------
# Permission decorator
# ---------------------------------------------------------------------------

def admin_required(f):
    """Require an authenticated admin user; otherwise 401→login or 403."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_user_form(form, existing_id=None, require_password=True):
    errors = []
    first_name = form.get('first_name', '').strip()
    last_name  = form.get('last_name',  '').strip()
    email      = form.get('email', '').strip().lower()
    password   = form.get('password', '')
    confirm    = form.get('confirm_password', '')
    is_admin   = bool(form.get('is_admin'))
    raw_biz    = form.get('business_id', '').strip()
    business_id = int(raw_biz) if raw_biz.isdigit() else None

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
            clash = User.query.filter(User.email == email).first()
            if clash and clash.id != existing_id:
                errors.append('That email is already in use.')

    if require_password or password:
        if require_password and not password:
            errors.append('Password is required.')
        elif password:
            pw_errors = validate_password(password)
            errors.extend(pw_errors)
            if not pw_errors and password != confirm:
                errors.append('Passwords do not match.')

    if business_id is not None and not db.session.get(Business, business_id):
        errors.append('Selected business does not exist.')

    return errors, {
        'first_name': first_name,
        'last_name':  last_name,
        'email':      email,
        'is_admin':   is_admin,
        'business_id': business_id,
        'password':   password,
    }


def _validate_business_form(form, existing_id=None):
    errors = []
    name    = form.get('name', '').strip()
    reg_num = form.get('registration_number', '').strip() or None

    if not name:
        errors.append('Business name is required.')
    elif len(name) > 200:
        errors.append('Business name must be 200 characters or fewer.')

    if reg_num:
        if len(reg_num) > 50:
            errors.append('Registration number must be 50 characters or fewer.')
        else:
            clash = Business.query.filter_by(registration_number=reg_num).first()
            if clash and clash.id != existing_id:
                errors.append('That registration number is already in use.')

    return errors, {'name': name, 'registration_number': reg_num}


def _validate_esim_form(form, existing_id=None):
    errors = []
    iccid  = form.get('iccid', '').strip()
    label  = form.get('label', '').strip() or None
    status = form.get('status', '').strip()

    if not iccid:
        errors.append('ICCID is required.')
    elif not iccid.isdigit() or not (19 <= len(iccid) <= 22):
        errors.append('ICCID must be 19–22 digits.')
    else:
        clash = ESim.query.filter_by(iccid=iccid).first()
        if clash and clash.id != existing_id:
            errors.append('An eSIM with that ICCID already exists.')

    if status not in ESim.VALID_STATUSES:
        errors.append(f'Status must be one of: {", ".join(ESim.VALID_STATUSES)}.')

    if label and len(label) > 100:
        errors.append('Label must be 100 characters or fewer.')

    return errors, {'iccid': iccid, 'label': label, 'status': status}


def _validate_subscription_form(form):
    errors = []
    plan_name      = form.get('plan_name', '').strip()
    data_limit_str = form.get('data_limit_gb', '').strip()
    start_str      = form.get('start_date', '').strip()
    end_str        = form.get('end_date', '').strip()
    status         = form.get('status', '').strip()

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
                errors.append('Data limit must be a positive number.')
            elif data_limit_gb > 1024:
                errors.append('Data limit cannot exceed 1024 GB.')
        except ValueError:
            errors.append('Data limit must be a number.')

    start_date = None
    if not start_str:
        errors.append('Start date is required.')
    else:
        try:
            start_date = date.fromisoformat(start_str)
        except ValueError:
            errors.append('Start date must be a valid date (YYYY-MM-DD).')

    end_date = None
    if end_str:
        try:
            end_date = date.fromisoformat(end_str)
            if start_date and end_date <= start_date:
                errors.append('End date must be after the start date.')
        except ValueError:
            errors.append('End date must be a valid date (YYYY-MM-DD).')

    if status not in Subscription.VALID_STATUSES:
        errors.append(f'Status must be one of: {", ".join(Subscription.VALID_STATUSES)}.')

    return errors, {
        'plan_name':     plan_name,
        'data_limit_gb': data_limit_gb,
        'start_date':    start_date,
        'end_date':      end_date,
        'status':        status,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_bp.route('/')
@admin_required
def dashboard():
    stats = {
        'users':          User.query.count(),
        'businesses':     Business.query.count(),
        'esims':          ESim.query.count(),
        'subscriptions':  Subscription.query.count(),
        'pending_esims':  ESim.query.filter_by(is_confirmed=False).count(),
        'pending_subs':   Subscription.query.filter_by(is_confirmed=False).count(),
    }

    esim_q     = get_search_term('esim_q')
    esim_page  = get_page('esim_page')
    esim_query = ESim.query.filter_by(is_confirmed=False)
    if esim_q:
        esim_query = esim_query.filter(ESim.iccid.ilike(f'%{esim_q}%'))
    pending_esims = paginate_query(esim_query.order_by(ESim.created_at.desc()), esim_page)

    sub_q     = get_search_term('sub_q')
    sub_page  = get_page('sub_page')
    sub_query = Subscription.query.filter_by(is_confirmed=False).join(ESim)
    if sub_q:
        sub_query = sub_query.filter(ESim.iccid.ilike(f'%{sub_q}%'))
    pending_subs = paginate_query(sub_query.order_by(Subscription.created_at.desc()), sub_page)

    return render_template('admin/dashboard.html',
                           stats=stats,
                           pending_esims=pending_esims,
                           esim_q=esim_q,
                           pending_subs=pending_subs,
                           sub_q=sub_q)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@admin_bp.route('/users')
@admin_required
def list_users():
    page  = get_page()
    q     = get_search_term()
    query = User.query.order_by(User.created_at.desc())
    if q:
        query = query.filter(User.email.ilike(f'%{q}%'))
    pagination = paginate_query(query, page)
    return render_template('admin/users/list.html',
                           users=pagination.items, pagination=pagination, q=q)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    businesses = Business.query.order_by(Business.name).all()
    if request.method == 'POST':
        errors, data = _validate_user_form(request.form, require_password=True)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/users/form.html',
                                   form=request.form, businesses=businesses)

        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            is_admin=data['is_admin'],
            is_confirmed=True,
            business_id=data['business_id'],
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(
            'CREATE_USER admin=%s new_user=%s is_admin=%s',
            current_user.email, user.email, user.is_admin,
        )
        flash(f'User {user.full_name} created successfully.', 'success')
        return redirect(url_for('admin.user_detail', id=user.id))

    return render_template('admin/users/form.html', form={},
                           businesses=businesses)


@admin_bp.route('/users/<int:id>')
@admin_required
def user_detail(id):
    user = db.session.get(User, id)
    if user is None:
        abort(404)
    esims_page  = get_page('esims_page')
    esims_q     = get_search_term('esims_q')
    esims_query = ESim.query.filter_by(user_id=id).order_by(ESim.id)
    if esims_q:
        esims_query = esims_query.filter(ESim.iccid.ilike(f'%{esims_q}%'))
    esims_pagination = paginate_query(esims_query, esims_page)
    total_esims = ESim.query.filter_by(user_id=id).count()
    return render_template('admin/users/detail.html', user=user,
                           esims=esims_pagination.items,
                           esims_pagination=esims_pagination,
                           total_esims=total_esims,
                           esims_q=esims_q)


@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    user = db.session.get(User, id)
    if user is None:
        abort(404)
    businesses = Business.query.order_by(Business.name).all()

    if request.method == 'POST':
        errors, data = _validate_user_form(
            request.form, existing_id=user.id, require_password=False
        )
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/users/form.html',
                                   form=request.form, user=user,
                                   businesses=businesses)

        prev_confirmed = user.is_confirmed
        user.first_name   = data['first_name']
        user.last_name    = data['last_name']
        user.email        = data['email']
        user.is_admin     = data['is_admin']
        user.is_confirmed = bool(request.form.get('is_confirmed'))
        user.business_id  = data['business_id']
        if data['password']:
            user.set_password(data['password'])
        db.session.commit()

        if not prev_confirmed and user.is_confirmed:
            current_app.logger.info(
                'CONFIRM_USER admin=%s user=%s', current_user.email, user.email
            )
        elif prev_confirmed and not user.is_confirmed:
            current_app.logger.warning(
                'REVOKE_USER_CONFIRMATION admin=%s user=%s',
                current_user.email, user.email,
            )
        current_app.logger.info(
            'EDIT_USER admin=%s user=%s', current_user.email, user.email
        )
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.user_detail', id=user.id))

    form = {
        'first_name':   user.first_name,
        'last_name':    user.last_name,
        'email':        user.email,
        'is_admin':     user.is_admin,
        'is_confirmed': user.is_confirmed,
        'business_id':  user.business_id,
    }
    return render_template('admin/users/form.html', form=form, user=user,
                           businesses=businesses)


@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@admin_required
def delete_user(id):
    user = db.session.get(User, id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.user_detail', id=id))
    name = user.full_name
    email = user.email
    db.session.delete(user)
    db.session.commit()
    current_app.logger.warning(
        'DELETE_USER admin=%s deleted_user=%s', current_user.email, email
    )
    flash(f'User {name} deleted.', 'success')
    return redirect(url_for('admin.list_users'))


# ---------------------------------------------------------------------------
# Businesses
# ---------------------------------------------------------------------------

@admin_bp.route('/businesses')
@admin_required
def list_businesses():
    page  = get_page()
    q     = get_search_term()
    query = Business.query.order_by(Business.name)
    if q:
        query = query.filter(Business.name.ilike(f'%{q}%'))
    pagination = paginate_query(query, page)
    return render_template('admin/businesses/list.html',
                           businesses=pagination.items, pagination=pagination, q=q)


@admin_bp.route('/businesses/new', methods=['GET', 'POST'])
@admin_required
def create_business():
    if request.method == 'POST':
        errors, data = _validate_business_form(request.form)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/businesses/form.html',
                                   form=request.form)

        biz = Business(name=data['name'],
                       registration_number=data['registration_number'])
        db.session.add(biz)
        db.session.commit()
        current_app.logger.info(
            'CREATE_BUSINESS admin=%s business="%s"', current_user.email, biz.name
        )
        flash(f'Business "{biz.name}" created successfully.', 'success')
        return redirect(url_for('admin.business_detail', id=biz.id))

    return render_template('admin/businesses/form.html', form={})


@admin_bp.route('/businesses/<int:id>')
@admin_required
def business_detail(id):
    biz = db.session.get(Business, id)
    if biz is None:
        abort(404)
    page  = get_page()
    q     = get_search_term()
    users_query = (User.query
                   .filter_by(business_id=id)
                   .order_by(User.created_at.desc()))
    if q:
        users_query = users_query.filter(User.email.ilike(f'%{q}%'))
    users_pagination = paginate_query(users_query, page)
    total_users = User.query.filter_by(business_id=id).count()
    return render_template('admin/businesses/detail.html', business=biz,
                           biz_users=users_pagination.items,
                           users_pagination=users_pagination,
                           total_users=total_users,
                           q=q)


@admin_bp.route('/businesses/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_business(id):
    biz = db.session.get(Business, id)
    if biz is None:
        abort(404)

    if request.method == 'POST':
        errors, data = _validate_business_form(request.form, existing_id=biz.id)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/businesses/form.html',
                                   form=request.form, business=biz)

        biz.name = data['name']
        biz.registration_number = data['registration_number']
        db.session.commit()
        current_app.logger.info(
            'EDIT_BUSINESS admin=%s business="%s"', current_user.email, biz.name
        )
        flash('Business updated successfully.', 'success')
        return redirect(url_for('admin.business_detail', id=biz.id))

    form = {
        'name':                biz.name,
        'registration_number': biz.registration_number or '',
    }
    return render_template('admin/businesses/form.html', form=form,
                           business=biz)


@admin_bp.route('/businesses/<int:id>/delete_all_users', methods=['POST'])
@admin_required
def delete_all_users(id):
    biz = db.session.get(Business, id)
    if biz is None:
        abort(404)
    users = (User.query
             .filter_by(business_id=id)
             .filter(User.id != current_user.id)
             .all())
    if not users:
        flash('No users to delete for this business.', 'info')
        return redirect(url_for('admin.business_detail', id=id))
    count = len(users)
    for user in users:
        db.session.delete(user)
    db.session.commit()
    current_app.logger.warning(
        'DELETE_ALL_USERS admin=%s business="%s" count=%d',
        current_user.email, biz.name, count,
    )
    flash(
        f'{count} user{"s" if count != 1 else ""} deleted from "{biz.name}".',
        'success',
    )
    return redirect(url_for('admin.business_detail', id=id))


@admin_bp.route('/businesses/<int:id>/delete', methods=['POST'])
@admin_required
def delete_business(id):
    biz = db.session.get(Business, id)
    if biz is None:
        abort(404)
    if biz.users:
        flash(
            f'Cannot delete "{biz.name}" — it still has '
            f'{len(biz.users)} user(s) assigned. '
            'Reassign or remove them first.',
            'danger',
        )
        return redirect(url_for('admin.business_detail', id=id))
    name = biz.name
    db.session.delete(biz)
    db.session.commit()
    current_app.logger.warning(
        'DELETE_BUSINESS admin=%s business="%s"', current_user.email, name
    )
    flash(f'Business "{name}" deleted.', 'success')
    return redirect(url_for('admin.list_businesses'))


# ---------------------------------------------------------------------------
# eSIMs
# ---------------------------------------------------------------------------

@admin_bp.route('/users/<int:user_id>/esims/new', methods=['GET', 'POST'])
@admin_required
def create_esim(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    if request.method == 'POST':
        errors, data = _validate_esim_form(request.form)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/esims/form.html',
                                   form=request.form, user=user,
                                   statuses=ESim.VALID_STATUSES)

        esim = ESim(
            iccid=data['iccid'],
            label=data['label'],
            status=data['status'],
            is_confirmed=True,
            user_id=user.id,
        )
        db.session.add(esim)
        db.session.commit()
        current_app.logger.info(
            'CREATE_ESIM admin=%s iccid=%s user=%s',
            current_user.email, esim.iccid, user.email,
        )
        flash('eSIM added successfully.', 'success')
        return redirect(url_for('admin.user_detail', id=user.id))

    return render_template('admin/esims/form.html',
                           form={'status': 'active'}, user=user,
                           statuses=ESim.VALID_STATUSES)


@admin_bp.route('/esims/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_esim(id):
    esim = db.session.get(ESim, id)
    if esim is None:
        abort(404)

    if request.method == 'POST':
        errors, data = _validate_esim_form(request.form, existing_id=esim.id)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/esims/form.html',
                                   form=request.form, esim=esim,
                                   user=esim.user,
                                   statuses=ESim.VALID_STATUSES)

        prev_confirmed = esim.is_confirmed
        esim.iccid        = data['iccid']
        esim.label        = data['label']
        esim.status       = data['status']
        esim.is_confirmed = bool(request.form.get('is_confirmed'))
        db.session.commit()

        if not prev_confirmed and esim.is_confirmed:
            current_app.logger.info(
                'CONFIRM_ESIM admin=%s esim_id=%d user=%s',
                current_user.email, id, esim.user.email,
            )
        current_app.logger.info(
            'EDIT_ESIM admin=%s esim_id=%d', current_user.email, id
        )
        flash('eSIM updated successfully.', 'success')
        return redirect(url_for('admin.user_detail', id=esim.user_id))

    form = {
        'iccid':        esim.iccid,
        'label':        esim.label or '',
        'status':       esim.status,
        'is_confirmed': esim.is_confirmed,
    }
    return render_template('admin/esims/form.html', form=form, esim=esim,
                           user=esim.user, statuses=ESim.VALID_STATUSES)


@admin_bp.route('/esims/<int:id>/confirm', methods=['POST'])
@admin_required
def confirm_esim(id):
    esim = db.session.get(ESim, id)
    if esim is None:
        abort(404)
    esim.is_confirmed = True
    esim.status = 'active'
    db.session.commit()
    current_app.logger.info(
        'CONFIRM_ESIM admin=%s esim_id=%d user=%s',
        current_user.email, id, esim.user.email,
    )
    flash('eSIM confirmed and activated.', 'success')
    return redirect(url_for('admin.user_detail', id=esim.user_id))


@admin_bp.route('/esims/<int:id>/delete', methods=['POST'])
@admin_required
def delete_esim(id):
    esim = db.session.get(ESim, id)
    if esim is None:
        abort(404)
    user_id = esim.user_id
    iccid = esim.iccid
    db.session.delete(esim)
    db.session.commit()
    current_app.logger.warning(
        'DELETE_ESIM admin=%s iccid=%s', current_user.email, iccid
    )
    flash('eSIM deleted.', 'success')
    return redirect(url_for('admin.user_detail', id=user_id))


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

@admin_bp.route('/esims/<int:esim_id>/subscriptions/new', methods=['GET', 'POST'])
@admin_required
def create_subscription(esim_id):
    esim = db.session.get(ESim, esim_id)
    if esim is None:
        abort(404)

    if request.method == 'POST':
        errors, data = _validate_subscription_form(request.form)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/subscriptions/form.html',
                                   form=request.form, esim=esim,
                                   statuses=Subscription.VALID_STATUSES)

        sub = Subscription(
            esim_id=esim.id,
            plan_name=data['plan_name'],
            data_limit_gb=data['data_limit_gb'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            status=data['status'],
            is_confirmed=True,
        )
        db.session.add(sub)
        db.session.commit()
        current_app.logger.info(
            'CREATE_SUBSCRIPTION admin=%s esim_id=%d plan=%s',
            current_user.email, esim.id, sub.plan_name,
        )
        flash('Subscription added successfully.', 'success')
        return redirect(url_for('admin.user_detail', id=esim.user_id))

    today = date.today().isoformat()
    return render_template('admin/subscriptions/form.html',
                           form={'start_date': today, 'status': 'active'},
                           esim=esim,
                           statuses=Subscription.VALID_STATUSES)


@admin_bp.route('/subscriptions/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_subscription(id):
    sub = db.session.get(Subscription, id)
    if sub is None:
        abort(404)

    if request.method == 'POST':
        errors, data = _validate_subscription_form(request.form)
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/subscriptions/form.html',
                                   form=request.form, subscription=sub,
                                   esim=sub.esim,
                                   statuses=Subscription.VALID_STATUSES)

        prev_confirmed = sub.is_confirmed
        sub.plan_name     = data['plan_name']
        sub.data_limit_gb = data['data_limit_gb']
        sub.start_date    = data['start_date']
        sub.end_date      = data['end_date']
        sub.status        = data['status']
        sub.is_confirmed  = bool(request.form.get('is_confirmed'))
        db.session.commit()

        if not prev_confirmed and sub.is_confirmed:
            current_app.logger.info(
                'CONFIRM_SUBSCRIPTION admin=%s sub_id=%d esim_id=%d',
                current_user.email, id, sub.esim_id,
            )
        current_app.logger.info(
            'EDIT_SUBSCRIPTION admin=%s sub_id=%d', current_user.email, id
        )
        flash('Subscription updated successfully.', 'success')
        return redirect(url_for('admin.user_detail', id=sub.esim.user_id))

    form = {
        'plan_name':     sub.plan_name,
        'data_limit_gb': sub.data_limit_gb,
        'start_date':    sub.start_date.isoformat() if sub.start_date else '',
        'end_date':      sub.end_date.isoformat() if sub.end_date else '',
        'status':        sub.status,
        'is_confirmed':  sub.is_confirmed,
    }
    return render_template('admin/subscriptions/form.html',
                           form=form, subscription=sub, esim=sub.esim,
                           statuses=Subscription.VALID_STATUSES)


@admin_bp.route('/subscriptions/<int:id>/confirm', methods=['POST'])
@admin_required
def confirm_subscription(id):
    sub = db.session.get(Subscription, id)
    if sub is None:
        abort(404)
    sub.is_confirmed = True
    db.session.commit()
    current_app.logger.info(
        'CONFIRM_SUBSCRIPTION admin=%s sub_id=%d esim_id=%d',
        current_user.email, id, sub.esim_id,
    )
    flash('Subscription confirmed.', 'success')
    return redirect(url_for('admin.user_detail', id=sub.esim.user_id))


@admin_bp.route('/subscriptions/<int:id>/delete', methods=['POST'])
@admin_required
def delete_subscription(id):
    sub = db.session.get(Subscription, id)
    if sub is None:
        abort(404)
    user_id = sub.esim.user_id
    plan = sub.plan_name
    db.session.delete(sub)
    db.session.commit()
    current_app.logger.warning(
        'DELETE_SUBSCRIPTION admin=%s sub_id=%d plan=%s',
        current_user.email, id, plan,
    )
    flash('Subscription deleted.', 'success')
    return redirect(url_for('admin.user_detail', id=user_id))
