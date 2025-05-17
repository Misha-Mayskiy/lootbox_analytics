from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Game, LootboxType, UserDrop
from datetime import datetime
import requests
import time
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from flask import Blueprint

bp = Blueprint('import_data_api', __name__, url_prefix='/api/v1')


def _fetch_gacha_log_for_type(base_url_with_auth, gacha_type_str):
    """
    Собирает историю для одного типа баннера по предоставленному URL.
    base_url_with_auth: URL, вставленный пользователем.
    gacha_type_str: Строка типа баннера ('301', '200', etc.).
    """
    gacha_log = []
    last_id = "0"
    page_size = 20

    try:
        parsed_original_url = urlparse(base_url_with_auth)
        original_query_params = parse_qs(parsed_original_url.query, keep_blank_values=True)
    except Exception as e:
        current_app.logger.error(f"Ошибка парсинга URL: {base_url_with_auth} - {e}")
        raise ValueError(f"Некорректный формат URL: {e}")

    allowed_hosts = ["hk4e-api-os.hoyoverse.com", "hk4e-api.hoyoverse.com",
                     "public-operation-hk4e-sg.hoyoverse.com", "public-operation-hk4e.mihoyo.com",
                     "sg-hk4e-api.hoyoverse.com", "webstatic-sea.hoyoverse.com",
                     "hk4e-sdk-os.hoyoverse.com"]

    is_valid_host = False
    for host in allowed_hosts:
        if host in parsed_original_url.netloc:
            is_valid_host = True
            break

    if not is_valid_host:
        current_app.logger.warning(f"Попытка импорта с неразрешенного хоста: {parsed_original_url.netloc}")
        raise ValueError("URL не принадлежит доверенному домену Hoyoverse/Mihoyo.")

    while True:
        current_query_params = {}
        for key, value in original_query_params.items():
            if key.lower() not in ['gacha_type', 'page', 'size', 'end_id', 'lang']:
                current_query_params[key] = value

        current_query_params['gacha_type'] = [gacha_type_str]
        current_query_params['size'] = [str(page_size)]
        current_query_params['end_id'] = [last_id]
        current_query_params['lang'] = ['en']

        new_query_string = urlencode(current_query_params, doseq=True)

        target_url_parts = list(parsed_original_url)
        target_url_parts[4] = new_query_string
        target_url = urlunparse(target_url_parts)

        try:
            response = requests.get(target_url, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            current_app.logger.error(f"Таймаут при запросе к API Mihoyo: {target_url}")
            raise ConnectionError(f"Таймаут ответа от сервера Mihoyo для баннера {gacha_type_str}.")
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Ошибка сети при запросе к API Mihoyo: {target_url} - {e}")
            raise ConnectionError(f"Ошибка сети при запросе к Mihoyo для баннера {gacha_type_str}: {e}")
        except ValueError:
            current_app.logger.error(f"Ошибка декодирования JSON от API Mihoyo: {target_url}")
            raise ValueError(f"Некорректный JSON ответ от Mihoyo для баннера {gacha_type_str}.")

        if data.get('retcode') != 0:
            message = data.get('message', 'Неизвестная ошибка от API Mihoyo.')
            current_app.logger.warning(
                f"API Mihoyo вернул retcode {data.get('retcode')} ({message}) для баннера {gacha_type_str}")
            if data.get('retcode') == -110:
                raise ValueError(
                    f"Ключ авторизации (authkey) в вашем URL истек или недействителен. Пожалуйста, получите новый URL из игры. ({message})")
            break

        current_batch = data.get('data', {}).get('list', [])
        if not current_batch:
            break

        gacha_log.extend(current_batch)
        last_id = current_batch[-1]['id']

        time.sleep(0.3)

    return gacha_log


@bp.route('/genshin/import-from-url', methods=['POST'])
@login_required
def import_genshin_from_url():
    data = request.get_json()
    wish_url = data.get('wish_history_url')

    if not wish_url:
        return jsonify(message="Параметр 'wish_history_url' отсутствует"), 400

    genshin_game = Game.query.filter_by(slug='genshin').first()
    if not genshin_game:
        current_app.logger.error("Игра Genshin Impact не найдена в БД при импорте по URL!")
        return jsonify(message="Ошибка конфигурации сервера: игра Genshin Impact не найдена."), 500

    required_lootbox_types_map = {
        "100": "Баннер новичка",
        "200": "Стандартный баннер",
        "301": "Ивентовый баннер персонажа",
        "400": "Ивентовый баннер персонажа #2",
        "302": "Баннер оружия (Воплощение божества)"
    }
    for game_spec_id, name in required_lootbox_types_map.items():
        if not LootboxType.query.filter_by(game_id=genshin_game.id, game_specific_id=game_spec_id).first():
            db.session.add(LootboxType(game_id=genshin_game.id, game_specific_id=game_spec_id, name=name))
    db.session.commit()

    gacha_types_to_fetch = ["400", "301", "302", "200", "100"]

    full_gacha_log = []
    fetch_errors = []

    try:
        for gacha_type_str in gacha_types_to_fetch:
            try:
                log_for_type = _fetch_gacha_log_for_type(wish_url, gacha_type_str)
                full_gacha_log.extend(log_for_type)
            except (ValueError, ConnectionError) as e:
                fetch_errors.append(str(e))
                if "Ключ авторизации" in str(e):
                    raise
            except Exception as e:
                fetch_errors.append(f"Непредвиденная ошибка при сборе для баннера {gacha_type_str}: {e}")

    except (ValueError, ConnectionError) as e:
        return jsonify(message=f"Ошибка при получении данных от Hoyoverse: {str(e)}"), 400
    except Exception as e:
        current_app.logger.error(f"Критическая ошибка при импорте по URL для user {current_user.id}: {e}")
        return jsonify(message=f"Произошла внутренняя ошибка сервера: {str(e)}"), 500

    if not full_gacha_log and fetch_errors:
        return jsonify(message="Не удалось получить данные ни по одному баннеру.", errors=fetch_errors), 400
    if not full_gacha_log and not fetch_errors:
        return jsonify(message="История молитв пуста или не удалось получить данные.", errors=fetch_errors), 200

    inserted_count = 0
    skipped_count = 0
    processing_errors = []

    for item_data in full_gacha_log:
        try:
            gacha_type = item_data.get('gacha_type')
            external_drop_id = item_data.get('id')
            timestamp_str = item_data.get('time')
            item_name = item_data.get('name')
            item_type_text = item_data.get('item_type')
            item_rarity_text = item_data.get('rank_type')
            quantity = int(item_data.get('count', 1))

            if not all([gacha_type, external_drop_id, timestamp_str, item_name, item_rarity_text]):
                processing_errors.append(
                    f"Пропущены обязательные поля для записи из API Mihoyo: id {external_drop_id or 'N/A'}")
                skipped_count += 1
                continue

            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            lootbox_type = LootboxType.query.filter_by(game_id=genshin_game.id, game_specific_id=gacha_type).first()
            if not lootbox_type:
                name_for_new_type = required_lootbox_types_map.get(gacha_type, f"Неизвестный баннер ({gacha_type})")
                current_app.logger.warning(
                    f"Автоматически создается отсутствующий тип лутбокса: {gacha_type} с именем '{name_for_new_type}'")
                lootbox_type = LootboxType(game_id=genshin_game.id, game_specific_id=gacha_type, name=name_for_new_type)
                db.session.add(lootbox_type)
                try:
                    db.session.commit()
                except Exception as e_commit:
                    db.session.rollback()
                    processing_errors.append(f"Ошибка создания нового типа лутбокса {gacha_type}: {e_commit}")
                    skipped_count += 1
                    continue

            exists = UserDrop.query.filter_by(
                user_id=current_user.id, game_id=genshin_game.id, external_drop_id=external_drop_id
            ).first()

            if exists:
                skipped_count += 1
                continue

            new_drop = UserDrop(
                user_id=current_user.id, game_id=genshin_game.id, lootbox_type_id=lootbox_type.id,
                external_drop_id=external_drop_id, timestamp=timestamp, item_name=item_name,
                item_type_text=item_type_text, item_rarity_text=item_rarity_text,
                quantity=quantity, raw_data=item_data
            )
            db.session.add(new_drop)
            inserted_count += 1
        except Exception as e:
            processing_errors.append(f"Ошибка обработки записи {external_drop_id or 'N/A'} при сохранении: {str(e)}")
            skipped_count += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка коммита в БД при импорте по URL для user {current_user.id}: {e}")
        return jsonify(message=f"Ошибка при сохранении данных в БД: {str(e)}"), 500

    final_message = "Данные успешно импортированы."
    if fetch_errors or processing_errors:
        final_message = "Импорт завершен с некоторыми проблемами."

    return jsonify(
        message=final_message,
        inserted=inserted_count,
        skipped=skipped_count,
        fetch_api_errors=fetch_errors,
        processing_db_errors=processing_errors
    ), 200
