import secrets
from flask import render_template, redirect, url_for, flash, request, Blueprint
from flask_login import login_user, logout_user, current_user, login_required
from app import db, oid
from app.forms import LoginForm, RegistrationForm
from app.models import User
from urllib.parse import urlparse, urljoin

bp = Blueprint('auth', __name__,
               template_folder='../../templates/auth')


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not is_safe_url(next_page):
            next_page = url_for('main.dashboard')
        flash(f'Добро пожаловать, {user.username}!', 'success')
        return redirect(next_page)
    return render_template('auth/login.html', title='Вход', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.api_key = secrets.token_hex(32)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, вы успешно зарегистрированы!', 'success')
        login_user(user)
        return redirect(url_for('main.dashboard'))
    return render_template('auth/register.html', title='Регистрация', form=form)


@bp.route('/steam_login')
@oid.loginhandler
def steam_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return oid.try_login('https://steamcommunity.com/openid/id/',
                         ask_for=['email', 'nickname'],  # Steam не всегда отдает
                         ask_for_optional=[])


@oid.after_login
def after_steam_login(resp):
    steam_id_full_url = resp.identity_url
    steam_id = steam_id_full_url.split('/')[-1]  # SteamID64

    if not steam_id:
        flash('Не удалось получить Steam ID.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(steam_id=steam_id).first()
    if user is None:
        username_candidate = f"steam_user_{steam_id}"
        email_candidate = f"{steam_id}@steam.localhost"

        existing_username = User.query.filter_by(username=username_candidate).first()
        existing_email = User.query.filter_by(email=email_candidate).first()

        if existing_username or existing_email:
            flash('Произошла ошибка при создании пользователя. Попробуйте обычную регистрацию.', 'danger')
            return redirect(url_for('auth.login'))

        user = User(steam_id=steam_id, username=username_candidate, email=email_candidate)
        db.session.add(user)
        db.session.commit()
        flash('Вы успешно вошли через Steam и для вас создан новый аккаунт!', 'success')
    else:
        flash(f'С возвращением, {user.username}! Вы вошли через Steam.', 'success')

    login_user(user)
    return redirect(url_for('main.dashboard') or request.args.get('next') or url_for('main.index'))
