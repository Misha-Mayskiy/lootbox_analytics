import datetime
import re
import secrets
from urllib.parse import urlparse, urljoin, urlunparse, urlencode

import requests
from flask import render_template, redirect, url_for, flash, request, Blueprint, current_app, session
from flask_login import login_user, logout_user, current_user, login_required

from app import db
from app.forms import LoginForm, RegistrationForm, EditUsernameForm, ChangePasswordForm, RegenerateApiKeyForm
from app.models import User

bp = Blueprint('auth', __name__,
               template_folder='../../templates/auth')
STEAM_OPENID_URL = 'https://steamcommunity.com/openid/login'


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
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
        return redirect(url_for('main.dashboard'))
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


def validate_steam_response(args):
    """Валидирует ответ от Steam, используя check_authentication."""
    validation_args = args.to_dict()
    validation_args['openid.mode'] = 'check_authentication'

    try:
        response = requests.post(STEAM_OPENID_URL, data=validation_args, timeout=10)
        response.raise_for_status()
        return "is_valid:true" in response.text
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Ошибка при валидации ответа Steam: {e}")
        return False


def get_steam_user_info_api(steam_id):
    """Получает информацию о пользователе через Steam Web API."""
    steam_api_key = current_app.config.get('STEAM_API_KEY')
    if not steam_api_key:
        current_app.logger.error("STEAM_API_KEY не настроен в конфигурации приложения.")
        return None

    params = {
        'key': steam_api_key,
        'steamids': steam_id
    }
    try:
        response = requests.get('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/', params=params,
                                timeout=10)
        response.raise_for_status()
        data = response.json()
        if data['response']['players']:
            return data['response']['players'][0]
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Ошибка запроса к Steam Web API (GetPlayerSummaries): {e}")
    except (KeyError, IndexError, ValueError) as e:
        current_app.logger.error(f"Ошибка парсинга ответа от Steam Web API: {e}")
    return None


@bp.route('/steam/login')
def steam_login():
    if current_user.is_authenticated and current_user.steam_id:
        flash('Ваш Steam аккаунт уже подключен.', 'info')
        return redirect(url_for('auth.user_profile'))

    if current_user.is_authenticated and not current_user.steam_id:
        session['next_url_after_steam_login'] = url_for('auth.user_profile', _external=True)

    elif 'next' in request.args:
        session['next_url_after_steam_login'] = request.args.get('next')

    base_url = request.url_root
    if base_url.endswith('/'):
        base_url = base_url[:-1]

    parsed_root = urlparse(request.url_root)
    actual_scheme = request.headers.get('X-Forwarded-Proto', parsed_root.scheme)

    return_to_path = url_for('auth.steam_callback')
    return_to_url = urlunparse((actual_scheme, parsed_root.netloc, return_to_path, '', '', ''))

    realm_url_parts = list(parsed_root)
    realm_url_parts[0] = actual_scheme  # Схема
    realm_url_parts[2] = ''  # path
    realm_url_parts[3] = ''  # params
    realm_url_parts[4] = ''  # query
    realm_url_parts[5] = ''  # fragment
    realm_url = urlunparse(realm_url_parts)

    params = {
        'openid.ns': "http://specs.openid.net/auth/2.0",
        'openid.identity': "http://specs.openid.net/auth/2.0/identifier_select",
        'openid.claimed_id': "http://specs.openid.net/auth/2.0/identifier_select",
        'openid.mode': 'checkid_setup',
        'openid.return_to': return_to_url,
        'openid.realm': realm_url  # Домен
    }

    param_string = urlencode(params)
    auth_url_steam = STEAM_OPENID_URL + "?" + param_string
    current_app.logger.info(f"Redirecting to Steam: {auth_url_steam}")
    return redirect(auth_url_steam)


@bp.route('/steam/callback')
def steam_callback():
    args = request.args

    if not validate_steam_response(args):
        flash('Не удалось подтвердить ответ от Steam. Попробуйте снова.', 'danger')
        current_app.logger.warning("Ответ от Steam не прошел валидацию.")
        return redirect(url_for('auth.login'))

    identity_url = args.get('openid.identity')
    if not identity_url:
        flash('Ответ от Steam не содержит openid.identity.', 'danger')
        return redirect(url_for('auth.login'))

    match = re.search(r'steamcommunity.com/openid/id/(\d+)', identity_url)
    if not match:
        flash('Не удалось извлечь SteamID из ответа Steam.', 'danger')
        current_app.logger.error(f"Не удалось извлечь SteamID из identity_url: {identity_url}")
        return redirect(url_for('auth.login'))

    steam_id = match.group(1)

    if current_user.is_authenticated:
        existing_steam_user = User.query.filter(User.steam_id == steam_id, User.id != current_user.id).first()
        if existing_steam_user:
            flash('Этот Steam аккаунт уже привязан к другому профилю.', 'danger')
            return redirect(url_for('auth.user_profile'))

        current_user.steam_id = steam_id
        db.session.add(current_user)
        try:
            db.session.commit()
            flash('Ваш Steam аккаунт успешно подключен!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Ошибка привязки SteamID {steam_id} к user {current_user.id}: {e}")
            flash('Произошла ошибка при подключении Steam аккаунта.', 'danger')

        next_url = session.pop('next_url_after_steam_login', None) or url_for('auth.user_profile')
        if not is_safe_url(next_url):
            next_url = url_for('main.dashboard')
        return redirect(next_url)

    else:
        user = User.query.filter_by(steam_id=steam_id).first()
        if user is None:
            steam_user_info = get_steam_user_info_api(steam_id)
            username_candidate = f"steam_{steam_id}"
            if steam_user_info and 'personaname' in steam_user_info:
                username_candidate = steam_user_info['personaname']
                base_username = username_candidate
                count = 1
                while User.query.filter_by(username=username_candidate).first():
                    username_candidate = f"{base_username}_{count}"
                    count += 1

            email_candidate = f"{steam_id}@steam.local"
            if User.query.filter_by(email=email_candidate).first() and User.email.nullable is False:
                pass

            user = User(
                steam_id=steam_id,
                username=username_candidate,
                email=email_candidate
            )

            user.api_key = secrets.token_hex(32)
            db.session.add(user)
            try:
                db.session.commit()
                flash(f'Вы успешно вошли через Steam как {user.username} и для вас создан новый аккаунт!', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Ошибка создания Steam пользователя (ручная реализация): {e}")
                flash(f'Ошибка при создании пользователя Steam: {e}', 'danger')
                return redirect(url_for('auth.login'))
        else:
            flash(f'С возвращением, {user.username}! Вы вошли через Steam.', 'success')

        login_user(user)

        next_url = session.pop('next_url_after_steam_login', None) or url_for('main.dashboard')
        if not is_safe_url(next_url):
            next_url = url_for('main.dashboard')
        return redirect(next_url)


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    form_edit_username = EditUsernameForm(current_user.username, prefix="edit_username")  # Добавляем префикс
    form_change_password = ChangePasswordForm(prefix="change_password")  # Добавляем префикс
    form_regenerate_api = RegenerateApiKeyForm(prefix="regen_api")

    can_change_username = True
    time_until_next_username_change_str = ""

    if current_user.username_last_changed_at:
        # Убедимся, что username_last_changed_at - это aware datetime, если оно из БД может быть naive
        last_change_aware = current_user.username_last_changed_at
        if last_change_aware.tzinfo is None:
            last_change_aware = last_change_aware.replace(tzinfo=datetime.timezone.utc)

        time_since_last_change = datetime.datetime.now(datetime.timezone.utc) - last_change_aware

        # Устанавливаем интервал (например, 1 день или 1 минута для теста)
        change_interval = datetime.timedelta(days=1)
        # change_interval = datetime.timedelta(minutes=1) # Для теста

        if time_since_last_change < change_interval:
            can_change_username = False
            time_remaining = change_interval - time_since_last_change
            # Форматирование оставшегося времени
            hours, remainder = divmod(time_remaining.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            if int(hours) > 0:
                time_until_next_username_change_str = f"{int(hours)} ч {int(minutes)} мин"
            elif int(minutes) > 0:
                time_until_next_username_change_str = f"{int(minutes)} мин {int(seconds)} сек"
            else:
                time_until_next_username_change_str = f"{int(seconds)} сек"

    active_form_name = None  # Для JS, чтобы раскрыть нужную <details>

    if request.method == 'POST':
        if 'submit_username' in request.form:
            active_form_name = 'username'
            if not can_change_username:
                flash(f'Вы сможете сменить имя пользователя снова через {time_until_next_username_change_str}.',
                      'warning')
            elif form_edit_username.validate_on_submit():
                old_username = current_user.username
                current_user.username = form_edit_username.username.data
                current_user.username_last_changed_at = datetime.datetime.now(datetime.timezone.utc)
                try:
                    db.session.commit()
                    flash(f'Имя пользователя успешно изменено с "{old_username}" на "{current_user.username}".',
                          'success')
                    return redirect(url_for('auth.user_profile'))
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Ошибка смены username для user {current_user.id}: {e}")
                    flash('Произошла ошибка при смене имени. Возможно, такое имя уже занято.', 'danger')

        elif 'submit_password' in request.form and form_change_password.validate_on_submit():
            active_form_name = 'password'
            if current_user.password_hash and current_user.check_password(form_change_password.current_password.data):
                current_user.set_password(form_change_password.new_password.data)
                db.session.commit()
                flash('Пароль успешно изменен.', 'success')
                return redirect(url_for('auth.user_profile'))
            elif not current_user.password_hash:
                flash('Вы вошли через Steam, установка пароля через эту форму невозможна.', 'warning')
            else:
                flash('Неверный текущий пароль.', 'danger')

    if not active_form_name:  # Если это GET или POST без ошибок, но не редирект
        if form_edit_username.errors:
            active_form_name = 'username'
        elif form_change_password.errors:
            active_form_name = 'password'

    return render_template('main/user_profile.html',
                           title="Профиль пользователя",
                           form_edit_username=form_edit_username,
                           form_change_password=form_change_password,
                           form_regenerate_api=form_regenerate_api,  # Убедись, что она передается
                           can_change_username=can_change_username,  # Передаем флаг
                           time_until_next_username_change=time_until_next_username_change_str,  # Передаем строку
                           active_form=active_form_name)  # Для JS
