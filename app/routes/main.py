from flask import Blueprint, render_template, url_for, redirect, flash
from flask_login import login_required, current_user

from app.models import Game, UserCS2InventoryItem
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


@bp.route('/dashboard/cs2-stats')
@login_required
def cs2_stats_page():
    if not current_user.steam_id:
        flash('Пожалуйста, подключите ваш Steam аккаунт для доступа к статистике CS2.', 'info')
        return redirect(url_for('main.dashboard'))

    cs2_game = Game.query.filter_by(slug='cs2').first()
    if not cs2_game:
        flash('Игра CS2 не настроена в системе.', 'danger')
        return redirect(url_for('main.dashboard'))

    # 1. Загружаем предметы инвентаря CS2 для текущего пользователя
    inventory_items = UserCS2InventoryItem.query.filter_by(
        user_id=current_user.id,
        game_id=cs2_game.id
    ).order_by(UserCS2InventoryItem.current_market_price.desc().nullslast()).all()

    # 2. Расчет общей стоимости и определение основной валюты
    total_inventory_value = 0
    currency = "USD"
    if inventory_items:
        total_inventory_value = sum(
            item.current_market_price for item in inventory_items if item.current_market_price is not None
        )
        first_item_with_price = next((item for item in inventory_items if item.price_currency), None)
        if first_item_with_price:
            currency = first_item_with_price.price_currency

    # 3. Подготовка данных для ГРАФИКА РЕДКОСТЕЙ (используя rarity_internal_name и rarity_color_hex)
    CSGO_RARITY_ORDER_MAP = {
        # internal_name: (DisplayName, SortOrder, FallbackColorIfNotInDB)
        "Rarity_Common_Weapon": ("Consumer Grade", 1, "#b0c3d9"),
        "Rarity_Uncommon_Weapon": ("Industrial Grade", 2, "#5e98d9"),
        "Rarity_Rare_Weapon": ("Mil-Spec", 3, "#4b69ff"),  # Для оружия, наклеек, музыки это может быть "High Grade"
        "Rarity_Mythical_Weapon": ("Restricted", 4, "#8847ff"),
        "Rarity_Legendary_Weapon": ("Classified", 5, "#d32ce6"),
        "Rarity_Ancient_Weapon": ("Covert", 6, "#eb4b4b"),  # Ножи/перчатки тоже часто тут
        "Rarity_Contraband": ("Contraband", 7, "#e4ae39"),
        "Rarity_Common": ("Base Grade", 0, "#d2d2d2"),  # Для кейсов, граффити
        # "Rarity_Rare":             ("High Grade", 2.5, "#4b69ff") # Если для музыки/стикеров отдельный internal_name
        # Добавь другие internal_name, если они встречаются
    }

    rarity_counts_for_chart = {}  # { (sort_order, display_name): count }
    item_colors_for_chart = {}  # { (sort_order, display_name): color_hex }

    if inventory_items:
        for item in inventory_items:
            if not item.rarity_internal_name:  # Пропускаем предметы без internal_name редкости
                continue

            mapped_rarity_info = CSGO_RARITY_ORDER_MAP.get(item.rarity_internal_name)

            display_name = item.rarity_str  # По умолчанию используем локализованное имя из БД
            # Цвет из БД (если есть), иначе из маппинга, иначе дефолтный
            color = f"#{item.rarity_color_hex.lstrip('#')}" if item.rarity_color_hex else \
                (mapped_rarity_info[2] if mapped_rarity_info else "#cccccc")
            sort_order = mapped_rarity_info[1] if mapped_rarity_info else 99

            if mapped_rarity_info:  # Если нашли в маппинге, используем его DisplayName
                display_name = mapped_rarity_info[0]

            key = (sort_order, display_name)
            rarity_counts_for_chart[key] = rarity_counts_for_chart.get(key, 0) + 1
            if key not in item_colors_for_chart:
                item_colors_for_chart[key] = color

    sorted_rarity_items = sorted(rarity_counts_for_chart.items(), key=lambda x: x[0][0])

    rarity_chart_labels = [item[0][1] for item in sorted_rarity_items]
    rarity_chart_values = [item[1] for item in sorted_rarity_items]
    rarity_chart_colors = [item_colors_for_chart[item[0]] for item in sorted_rarity_items]

    rarity_chart_data = {
        'labels': rarity_chart_labels,
        'datasets': [{
            'data': rarity_chart_values,
            'backgroundColor': rarity_chart_colors
        }]
    }

    # 4. Подготовка данных для ГРАФИКА ТИПОВ ПРЕДМЕТОВ
    type_distribution = {}
    type_chart_colors_map = {}  # Для консистентных цветов типов
    predefined_type_colors = ['#6FCF97', '#F2C94C', '#2F80ED', '#EB5757', '#9B51E0', '#219653', '#A0AEC0', '#F2994A',
                              '#2D9CDB']
    color_idx = 0

    if inventory_items:
        types = [item.item_type_str for item in inventory_items if
                 item.item_type_str and item.item_type_str != "Unknown"]
        for i_type in sorted(list(set(types))):  # Сортируем типы для консистентного порядка и цветов
            type_distribution[i_type] = types.count(i_type)
            if i_type not in type_chart_colors_map:
                type_chart_colors_map[i_type] = predefined_type_colors[color_idx % len(predefined_type_colors)]
                color_idx += 1

    type_chart_labels = list(type_distribution.keys())
    type_chart_values = list(type_distribution.values())
    type_chart_colors = [type_chart_colors_map[label] for label in type_chart_labels]

    type_chart_data = {
        'labels': type_chart_labels,
        'datasets': [{
            'data': type_chart_values,
            'backgroundColor': type_chart_colors
        }]
    }

    # 5. Расчет ROI
    user_cs2_investment = current_user.cs2_investment_amount or 0.0
    roi = 0.0
    if user_cs2_investment > 0:  # Избегаем деления на ноль
        roi = ((total_inventory_value - user_cs2_investment) / user_cs2_investment) * 100
        roi = round(roi, 2)

    return render_template('main/cs2_stats.html',
                           title="Статистика CS2",
                           inventory_items=inventory_items,
                           total_inventory_value=round(total_inventory_value, 2),
                           currency=currency,
                           user_cs2_investment=user_cs2_investment,
                           roi=roi,
                           rarity_chart_data=rarity_chart_data,
                           type_chart_data=type_chart_data)
