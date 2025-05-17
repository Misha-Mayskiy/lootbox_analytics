import secrets
from flask import render_template, redirect, url_for, flash, request, Blueprint, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db, oauth
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


@bp.route('/steam/login')
def steam_authorize():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    redirect_uri = url_for('auth.steam_callback', _external=True,
                           _scheme='https')

    return oauth.steam.authorize_redirect(redirect_uri)


@bp.route('/steam/callback')
def steam_callback():
    try:
        token = oauth.steam.authorize_access_token()
    except Exception as e:
        current_app.logger.error(f"Steam OAuth callback error: {e}")
        flash(f'Ошибка аутентификации через Steam: {e}', 'danger')
        return redirect(url_for('auth.login'))

    if not token:
        flash('Не удалось получить токен от Steam.', 'danger')
        return redirect(url_for('auth.login'))

    userinfo = token.get('userinfo')

    if not userinfo:
        id_token_claims = oauth.steam.parse_id_token(token)
        if not id_token_claims:
            flash('Не удалось получить информацию о пользователе из Steam токена.', 'danger')
            return redirect(url_for('auth.login'))
        userinfo = id_token_claims  # Используем все клеймы из id_token

    steam_identity_url = userinfo.get('sub')
    if not steam_identity_url or not steam_identity_url.startswith('https://steamcommunity.com/openid/id/'):
        flash('Не удалось извлечь корректный Steam ID из ответа Steam.', 'danger')
        current_app.logger.error(f"Invalid 'sub' in Steam userinfo: {steam_identity_url}")
        return redirect(url_for('auth.login'))

    steam_id = steam_identity_url.split('/')[-1]

    user = User.query.filter_by(steam_id=steam_id).first()
    if user is None:
        username_candidate = f"steam_{steam_id}"

        user = User(
            steam_id=steam_id,
            username=username_candidate,
            email=f"{steam_id}@steam.local"
        )

        import secrets
        user.api_key = secrets.token_hex(32)
        db.session.add(user)
        try:
            db.session.commit()
            flash('Вы успешно вошли через Steam и для вас создан новый аккаунт!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Ошибка создания Steam пользователя (Authlib): {e}")
            flash(f'Ошибка при создании пользователя Steam: {e}', 'danger')
            return redirect(url_for('auth.login'))
    else:
        flash(f'С возвращением, {user.username}! Вы вошли через Steam.', 'success')

    login_user(user)

    next_url = session.pop('next_url_after_steam_login', None) or url_for('main.dashboard')
    if not is_safe_url(next_url):
        next_url = url_for('main.dashboard')
    return redirect(next_url)
