import datetime
import requests
import re
from flask import current_app, jsonify, Blueprint
from flask_login import current_user, login_required
from app import db
from app.models import UserCS2InventoryItem, PriceCacheCS2, Game

bp_cs2_api = Blueprint('cs2_api', __name__, url_prefix='/api/v1/cs2')


STEAM_INVENTORY_URL_TEMPLATE = "https://steamcommunity.com/inventory/{steam_id}/730/2?l=english&count=5000"
STEAM_PRICE_URL_TEMPLATE = "https://steamcommunity.com/market/priceoverview/"
PRICE_CACHE_TTL_SECONDS = 3 * 60 * 60  # 3 часа


def _get_item_price_from_steam_market(market_hash_name, currency_code=1):  # 1 - USD, 5 - RUB
    """Получает цену маркета Steam, использует кэш."""
    cached_price = PriceCacheCS2.query.filter_by(market_hash_name=market_hash_name).first()
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if cached_price and \
            (now_utc - cached_price.last_fetched_at.replace(
                tzinfo=datetime.timezone.utc)).total_seconds() < PRICE_CACHE_TTL_SECONDS:
        return cached_price.price, cached_price.currency

    response_data_json = None

    try:
        params = {
            'appid': 730,
            'currency': currency_code,
            'market_hash_name': market_hash_name
        }
        response = requests.get(STEAM_PRICE_URL_TEMPLATE, params=params, timeout=10)
        response.raise_for_status()
        response_data_json = response.json()

        if response_data_json.get('success') and (
                response_data_json.get('lowest_price') or response_data_json.get('median_price')):
            price_str = response_data_json.get('lowest_price') or response_data_json.get('median_price')

            match = re.search(r'(\d+[,.]?\d*)', price_str)
            if match:
                price_value_str = match.group(1).replace(',', '.')
                price = float(price_value_str)

                currency_symbol_map = {
                    "$": "USD", "pуб": "RUB", "€": "EUR", "£": "GBP", "₽": "RUB"
                }
                fetched_currency = "USD"
                for symbol, code in currency_symbol_map.items():
                    if symbol in price_str:  # Проверяем символ валюты
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

    cs2_game = Game.query.filter_by(slug='cs2').first()
    if not cs2_game:
        current_app.logger.error("Игра CS2 не найдена в БД при попытке синхронизации инвентаря.")
        return jsonify(message="Игра CS2 не настроена в системе."), 500

    inventory_url = STEAM_INVENTORY_URL_TEMPLATE.format(steam_id=current_user.steam_id)
    inventory_response_obj = None

    try:
        inventory_response_obj = requests.get(inventory_url, timeout=20)
        inventory_response_obj.raise_for_status()
        inventory_data_json = inventory_response_obj.json()
    except requests.exceptions.Timeout:
        current_app.logger.error(f"Таймаут при запросе инвентаря CS2 для user {current_user.id}")
        return jsonify(message="Таймаут ответа от Steam при запросе инвентаря."), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Ошибка сети при запросе инвентаря CS2 для user {current_user.id}: {e}")
        return jsonify(message=f"Ошибка сети при запросе инвентаря из Steam: {e}"), 502
    except ValueError:
        error_text_sample = inventory_response_obj.text[:500] if inventory_response_obj else "N/A"
        current_app.logger.error(
            f"Ошибка декодирования JSON инвентаря CS2 для user {current_user.id}. Ответ: {error_text_sample}")
        return jsonify(
            message="Некорректный формат ответа от Steam (не JSON). Возможно, инвентарь приватный или Steam недоступен."), 500

    if not inventory_data_json or not inventory_data_json.get("success"):
        message = "Не удалось получить инвентарь. Возможно, он приватный или Steam API временно недоступен."
        if inventory_data_json and "more" in inventory_data_json and inventory_data_json.get(
                "more") is False and not inventory_data_json.get("rgInventory"):
            message = "Ваш CS2 инвентарь пуст."

        error_detail = inventory_data_json.get('error', '') if inventory_data_json else ''
        current_app.logger.warning(
            f"Запрос инвентаря CS2 для user {current_user.id} неуспешен: {error_detail or message}")
        return jsonify(message=message), 400

    assets = inventory_data_json.get("rgInventory", {})
    descriptions = inventory_data_json.get("rgDescriptions", {})

    UserCS2InventoryItem.query.filter_by(user_id=current_user.id, game_id=cs2_game.id).delete()

    items_processed = 0
    items_added_to_db = 0
    now_utc_for_items = datetime.datetime.now(
        datetime.timezone.utc)

    for asset_id, asset_info in assets.items():
        items_processed += 1
        class_id = asset_info.get("classid")
        instance_id = asset_info.get("instanceid")
        description_key = f"{class_id}_{instance_id}"
        desc = descriptions.get(description_key)

        if not desc:
            current_app.logger.warning(f"Не найдено описание для {description_key} у user {current_user.id}")
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

        for tag in desc.get("tags", []):
            category = tag.get("category")
            if category == "Type":
                item_type_str = tag.get("localized_tag_name", tag.get("name"))
            elif category == "Rarity":
                rarity_str = tag.get("localized_tag_name", tag.get("name"))
            elif category == "Exterior":
                exterior_str = tag.get("localized_tag_name", tag.get("name"))

        price, currency = _get_item_price_from_steam_market(market_hash_name)

        inventory_item = UserCS2InventoryItem(
            user_id=current_user.id,
            game_id=cs2_game.id,
            asset_id=asset_id,
            class_id=class_id,
            instance_id=instance_id,
            name=name,
            market_hash_name=market_hash_name,
            item_type_str=item_type_str,
            rarity_str=rarity_str,
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
        message=f"Инвентарь CS2 успешно синхронизирован. Обработано предметов: {items_processed}, Добавлено/обновлено в БД: {items_added_to_db}."
    ), 200
