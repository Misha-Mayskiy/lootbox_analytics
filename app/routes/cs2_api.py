import datetime
import re

import requests
from flask import current_app, jsonify, Blueprint
from flask_login import current_user, login_required

from app import db
from app.models import UserCS2InventoryItem, PriceCacheCS2, Game

bp_cs2_api = Blueprint('cs2_api', __name__, url_prefix='/api/v1/cs2')

STEAM_INVENTORY_URL_BASE = "https://steamcommunity.com/inventory"  # Базовый URL
STEAM_PRICE_URL_TEMPLATE = "https://steamcommunity.com/market/priceoverview/"
PRICE_CACHE_TTL_SECONDS = 3 * 60 * 60  # 3 часа


def _get_item_price_from_steam_market(market_hash_name, currency_code=1):  # 1 - USD, 5 - RUB
    """Получает цену маркета Steam, использует кэш."""
    cached_price = PriceCacheCS2.query.filter_by(market_hash_name=market_hash_name).first()

    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if cached_price:
        # Преобразуем last_fetched_at в aware datetime, если оно naive
        last_fetched_at_aware = cached_price.last_fetched_at
        if last_fetched_at_aware.tzinfo is None:
            last_fetched_at_aware = last_fetched_at_aware.replace(tzinfo=datetime.timezone.utc)

        if (now_utc - last_fetched_at_aware).total_seconds() < PRICE_CACHE_TTL_SECONDS:
            return cached_price.price, cached_price.currency

    response_data_json = None

    try:
        params = {
            'appid': 730,
            'currency': currency_code,
            'market_hash_name': market_hash_name  # requests сам закодирует этот параметр
        }
        response = requests.get(STEAM_PRICE_URL_TEMPLATE, params=params, timeout=10)
        response.raise_for_status()
        response_data_json = response.json()

        if response_data_json.get('success') and \
                (response_data_json.get('lowest_price') or response_data_json.get('median_price')):

            price_str = response_data_json.get('lowest_price') or response_data_json.get('median_price')
            if not price_str:  # Если оба None или пустые строки
                current_app.logger.warning(
                    f"Цена не найдена (lowest_price и median_price отсутствуют) для {market_hash_name}")
                return None, None

            # Регулярное выражение для извлечения числового значения цены
            match = re.search(r'(\d+[,.]?\d*)', price_str)
            if match:
                price_value_str = match.group(1).replace(',', '.')
                price = float(price_value_str)

                currency_symbol_map = {
                    "$": "USD", "pуб": "RUB", "€": "EUR", "£": "GBP", "₽": "RUB",
                    "USD": "USD", "RUB": "RUB", "EUR": "EUR", "GBP": "GBP"  # Для случаев, когда API отдает код
                }
                fetched_currency = "USD"  # Default

                for symbol_or_code, code in currency_symbol_map.items():
                    if symbol_or_code in price_str:
                        fetched_currency = code
                        break

                if cached_price:
                    cached_price.price = price
                    cached_price.currency = fetched_currency
                    cached_price.last_fetched_at = now_utc
                else:
                    cached_price = PriceCacheCS2(
                        market_hash_name=market_hash_name,
                        price=price,
                        currency=fetched_currency,
                        last_fetched_at=now_utc
                    )
                    db.session.add(cached_price)
                db.session.commit()
                return price, fetched_currency
            else:
                current_app.logger.warning(
                    f"Не удалось извлечь числовое значение цены из строки: '{price_str}' для {market_hash_name}")

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Ошибка запроса цены для {market_hash_name}: {e}")
    except (ValueError, KeyError, TypeError) as e:
        current_app.logger.error(
            f"Ошибка парсинга цены для {market_hash_name}: {e} (Ответ JSON: {response_data_json})")
    return None, None


@bp_cs2_api.route('/sync-inventory', methods=['POST'])
@login_required
def sync_cs2_inventory():
    if not current_user.steam_id:
        return jsonify(message="Steam аккаунт не подключен к вашему профилю."), 400

    try:
        # Валидация и преобразование steam_id
        validated_steam_id = str(int(current_user.steam_id))
    except ValueError:
        current_app.logger.error(f"Некорректный SteamID для пользователя {current_user.id}: {current_user.steam_id}")
        return jsonify(message="Некорректный формат SteamID."), 400

    cs2_game = Game.query.filter_by(slug='cs2').first()
    if not cs2_game:
        current_app.logger.error("Игра CS2 не найдена в БД при попытке синхронизации инвентаря.")
        return jsonify(message="Игра CS2 не настроена в системе."), 500

    # Формируем URL
    inventory_url = f"{STEAM_INVENTORY_URL_BASE}/{validated_steam_id}/730/2"
    inventory_params = {'l': 'english'}

    inventory_response_obj = None

    try:
        inventory_response_obj = requests.get(inventory_url, params=inventory_params, timeout=20)
        inventory_response_obj.raise_for_status()
        inventory_data_json = inventory_response_obj.json()

        current_app.logger.info(
            f"Ответ от Steam Inventory API для user {current_user.id} (success: {inventory_data_json.get('success')}):")
        if inventory_data_json and inventory_data_json.get("assets"):
            current_app.logger.info(f"  Количество assets: {len(inventory_data_json.get('assets'))}")
        else:
            current_app.logger.info(f"  assets отсутствует или пуст.")
        if inventory_data_json and inventory_data_json.get("descriptions"):
            current_app.logger.info(f"  Количество descriptions: {len(inventory_data_json.get('descriptions'))}")
        else:
            current_app.logger.info(f"  descriptions отсутствует или пуст.")

    except requests.exceptions.Timeout:
        current_app.logger.error(f"Таймаут при запросе инвентаря CS2 для user {current_user.id}")
        return jsonify(message="Таймаут ответа от Steam при запросе инвентаря."), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Ошибка сети при запросе инвентаря CS2 для user {current_user.id}: {e}")
        return jsonify(message=f"Ошибка сети при запросе инвентаря из Steam: {e}"), 502
    except ValueError:
        error_text_sample = inventory_response_obj.text[:500] if inventory_response_obj and hasattr(
            inventory_response_obj, 'text') else "N/A (ответ не получен или не текстовый)"
        current_app.logger.error(
            f"Ошибка декодирования JSON инвентаря CS2 для user {current_user.id}. Ответ: {error_text_sample}")
        return jsonify(
            message="Некорректный формат ответа от Steam. Возможно, инвентарь приватный, Steam недоступен, или структура ответа изменилась."), 500

    if not inventory_data_json or not inventory_data_json.get("success", False):  # Убедимся, что success == True
        message = "Не удалось получить инвентарь. Возможно, он приватный или Steam API временно недоступен."
        if inventory_data_json and "assets" in inventory_data_json and not inventory_data_json.get("assets"):
            message = "Ваш CS2 инвентарь пуст."

        error_detail = inventory_data_json.get('error', '') if inventory_data_json else ''
        current_app.logger.warning(
            f"Запрос инвентаря CS2 для user {current_user.id} неуспешен (success!=true или нет данных): {error_detail or message}")
        return jsonify(message=message), 400

    assets_list = inventory_data_json.get("assets", [])
    descriptions_list = inventory_data_json.get("descriptions", [])
    descriptions_map = {f"{desc['classid']}_{desc['instanceid']}": desc for desc in descriptions_list}

    UserCS2InventoryItem.query.filter_by(user_id=current_user.id, game_id=cs2_game.id).delete()

    items_processed = 0
    items_added_to_db = 0
    now_utc_for_items = datetime.datetime.now(datetime.timezone.utc)

    for asset_info in assets_list:
        items_processed += 1
        asset_id = asset_info.get("assetid")
        class_id = asset_info.get("classid")
        instance_id = asset_info.get("instanceid")
        description_key = f"{class_id}_{instance_id}"
        desc = descriptions_map.get(description_key)

        if not desc:
            current_app.logger.warning(
                f"Не найдено описание для {description_key} (asset: {asset_id}) у user {current_user.id}")
            continue

        name = desc.get("name")
        market_hash_name = desc.get("market_hash_name")
        icon_url_suffix = desc.get("icon_url")
        icon_url = f"https://steamcommunity-a.akamaihd.net/economy/image/{icon_url_suffix}" if icon_url_suffix else None

        tradable = bool(desc.get("tradable", 0))
        marketable = bool(desc.get("marketable", 0))

        item_type_str = "Unknown"
        rarity_str = "Unknown"
        exterior_str = "Unknown"
        rarity_internal_name = None
        rarity_color_hex = None

        for tag in desc.get("tags", []):
            category = tag.get("category")
            tag_name = tag.get("localized_tag_name", tag.get("name"))
            if category == "Type":
                item_type_str = tag_name
            elif category == "Rarity":
                rarity_str = tag_name
                rarity_internal_name = tag.get("internal_name")
                raw_color = tag.get("color")
                if raw_color:
                    rarity_color_hex = raw_color
            elif category == "Exterior":
                exterior_str = tag_name

        price, currency = _get_item_price_from_steam_market(market_hash_name)

        inventory_item = UserCS2InventoryItem(
            user_id=current_user.id,
            game_id=cs2_game.id,
            asset_id=str(asset_id),
            class_id=str(class_id),
            instance_id=str(instance_id),
            name=name,
            market_hash_name=market_hash_name,
            item_type_str=item_type_str,
            rarity_str=rarity_str,
            rarity_internal_name=rarity_internal_name,
            rarity_color_hex=rarity_color_hex,
            exterior_str=exterior_str,
            icon_url=icon_url,
            current_market_price=price,
            price_currency=currency,
            last_price_update=now_utc_for_items if price is not None else None,
            tradable=tradable,
            marketable=marketable,
            snapshot_time=now_utc_for_items
        )
        db.session.add(inventory_item)
        items_added_to_db += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка коммита CS2 инвентаря для user {current_user.id}: {e}")
        return jsonify(message=f"Ошибка сохранения данных инвентаря в БД: {str(e)}"), 500

    return jsonify(
        message=f"Инвентарь CS2 успешно синхронизирован. Обработано предметов: {items_processed}."
    ), 200
