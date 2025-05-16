from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.forms import LoginForm, RegistrationForm
from app.models import User
from urllib.parse import urlparse, urljoin

from flask import Blueprint

bp = Blueprint('auth', __name__,
               template_folder='../../templates/auth')  # Указываем путь к шаблонам относительно файла блюпринта


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))  # Или на дашборд
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not is_safe_url(next_page):
            next_page = url_for('main.dashboard')  # Или 'main.index'
        flash(f'Добро пожаловать, {user.username}!', 'success')
        return redirect(next_page)
    return render_template('login.html', title='Вход', form=form)


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
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, вы успешно зарегистрированы!', 'success')
        login_user(user)  # Автоматический вход после регистрации
        return redirect(url_for('main.dashboard'))  # Или на страницу "проверьте email"
    return render_template('register.html', title='Регистрация', form=form)
