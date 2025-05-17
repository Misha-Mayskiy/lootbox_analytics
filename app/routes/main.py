from flask import render_template, url_for, redirect, flash
from flask_login import login_required, current_user
from flask import Blueprint
from app.models import Game, UserDrop, LootboxType

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

    # Получаем все дропы пользователя для Genshin Impact
    drops = UserDrop.query.filter_by(user_id=user.id, game_id=genshin_game.id) \
        .order_by(UserDrop.timestamp.desc()) \
        .all()

    total_pulls = len(drops)

    # Статистика по редкости
    rarity_counts = {
        '3': UserDrop.query.filter_by(user_id=user.id, game_id=genshin_game.id, item_rarity_text='3').count(),
        '4': UserDrop.query.filter_by(user_id=user.id, game_id=genshin_game.id, item_rarity_text='4').count(),
        '5': UserDrop.query.filter_by(user_id=user.id, game_id=genshin_game.id, item_rarity_text='5').count(),
    }

    # Pity трекеры
    pity_data = {}
    # ID стандартного баннера и ивентовых баннеров персонажа (включая двойные)
    # Мы должны получить их из БД
    character_event_banner_types_ids = [
        lt.id for lt in LootboxType.query.filter_by(game_id=genshin_game.id) \
            .filter(LootboxType.game_specific_id.in_(['301', '400'])).all()
    ]
    standard_banner_type_id = LootboxType.query.filter_by(game_id=genshin_game.id, game_specific_id='200').first()
    weapon_banner_type_id = LootboxType.query.filter_by(game_id=genshin_game.id, game_specific_id='302').first()

    # Pity для ивентового баннера персонажа (5 звезд)
    if character_event_banner_types_ids:
        pulls_since_last_5_star_char_event = 0
        last_5_star_on_char_event_was_guarantee = False  # Упрощенно, нужно будет хранить это

        char_event_drops = UserDrop.query.filter_by(user_id=user.id, game_id=genshin_game.id) \
            .filter(UserDrop.lootbox_type_id.in_(character_event_banner_types_ids)) \
            .order_by(UserDrop.timestamp.asc()).all()  # ASC для подсчета pity

        for i, drop in enumerate(reversed(char_event_drops)):  # Идем с конца (самые новые)
            if drop.item_rarity_text == '5':
                # Здесь нужна логика определения, был ли это ивентовый персонаж или стандартный для 50/50
                # Пока просто считаем до последнего 5*
                break
            pulls_since_last_5_star_char_event += 1

        pity_data['character_event_5_star'] = {
            'pulls_since_last': pulls_since_last_5_star_char_event,
            'current_pity': pulls_since_last_5_star_char_event,  # В Genshin pity сбрасывается
            'guarantee_at': 90,
            # 'on_guarantee': last_5_star_on_char_event_was_guarantee # Для 50/50
        }

        # Pity для ивентового баннера персонажа (4 звезды)
        pulls_since_last_4_star_char_event = 0
        for i, drop in enumerate(reversed(char_event_drops)):
            if drop.item_rarity_text == '4':
                break
            pulls_since_last_4_star_char_event += 1
        pity_data['character_event_4_star'] = {
            'pulls_since_last': pulls_since_last_4_star_char_event,
            'current_pity': pulls_since_last_4_star_char_event,
            'guarantee_at': 10
        }

    # Pity для стандартного баннера (5 звезд)
    if standard_banner_type_id:
        pulls_since_last_5_star_standard = 0
        standard_drops = UserDrop.query.filter_by(user_id=user.id, game_id=genshin_game.id,
                                                  lootbox_type_id=standard_banner_type_id.id) \
            .order_by(UserDrop.timestamp.asc()).all()
        for i, drop in enumerate(reversed(standard_drops)):
            if drop.item_rarity_text == '5':
                break
            pulls_since_last_5_star_standard += 1
        pity_data['standard_banner_5_star'] = {
            'pulls_since_last': pulls_since_last_5_star_standard,
            'current_pity': pulls_since_last_5_star_standard,
            'guarantee_at': 90
        }
    # Аналогично можно добавить 4* pity для стандарта и pity для оружейного баннера (там своя сложная логика)

    # Последние несколько круток для отображения
    latest_drops = UserDrop.query.filter_by(user_id=user.id, game_id=genshin_game.id) \
        .order_by(UserDrop.timestamp.desc()) \
        .limit(10).all()

    return render_template('main/genshin_stats.html', title="Статистика Genshin Impact",
                           total_pulls=total_pulls, rarity_counts=rarity_counts,
                           pity_data=pity_data, latest_drops=latest_drops, drops_list=drops[:20])
