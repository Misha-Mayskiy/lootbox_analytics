from flask import Blueprint, render_template, url_for, redirect, flash
from flask_login import login_required, current_user

from app.models import Game
from app.services.genshin_stats_service import GenshinPityTracker, PITY_LIMITS

bp = Blueprint('main', __name__, template_folder='../../templates/main')


@bp.route('/')
@bp.route('/index')
def index():
    return render_template('main/index.html', title='Главная')


@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('main/dashboard.html', title='Дашборд')


@bp.route('/dashboard/genshin/import-url')
@login_required
def genshin_import_url_page():
    return render_template('main/import_genshin_url.html', title="Импорт Genshin Impact")


@bp.route('/dashboard/genshin-stats')
@login_required
def genshin_stats_page():
    user = current_user
    genshin_game = Game.query.filter_by(slug='genshin').first()

    if not genshin_game:
        flash('Игра Genshin Impact не найдена в конфигурации.', 'warning')
        return redirect(url_for('main.dashboard'))

    tracker = GenshinPityTracker(user, genshin_game)
    banner_states_data = tracker.calculate_all_banner_states()
    rarity_counts_overall, total_pulls_overall = tracker.get_overall_stats()
    latest_drops = tracker.get_latest_drops(limit=10)

    return render_template('main/genshin_stats.html',
                           title="Статистика Genshin Impact",
                           banner_states=banner_states_data,
                           pity_limits=PITY_LIMITS,
                           total_pulls_overall=total_pulls_overall,
                           rarity_counts_overall=rarity_counts_overall,
                           latest_drops=latest_drops)
