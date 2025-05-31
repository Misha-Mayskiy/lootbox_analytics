import os
from flask_migrate import upgrade
from app import create_app, db
from app.models import User, Game, LootboxType, UserDrop, PriceCacheCS2, UserCS2InventoryItem

app = create_app()

if os.environ.get('RENDER') == 'true' or os.environ.get('FLASK_ENV') == 'production':
    with app.app_context():
        # 1. Применение миграций
        try:
            app.logger.info("RUN.PY: Попытка применить миграции БД...")
            upgrade()
            app.logger.info("RUN.PY: Миграции БД успешно применены (или уже были актуальны).")
        except Exception as e:
            app.logger.error(f"RUN.PY: Ошибка при автоматическом применении миграций: {e}", exc_info=True)

        # 2. Заполнение начальных данных (если их нет)
        try:
            app.logger.info("RUN.PY: Проверка и заполнение начальных данных...")

            genshin_game = Game.query.filter_by(slug='genshin').first()
            if not genshin_game:
                genshin_game = Game(name='Genshin Impact', slug='genshin')
                db.session.add(genshin_game)
                db.session.commit()
                app.logger.info(f"RUN.PY: Добавлена игра: Genshin Impact (ID: {genshin_game.id})")

                lootbox_types_data_genshin = [
                    {'game_specific_id': '100', 'name': 'Баннер новичка'},
                    {'game_specific_id': '200', 'name': 'Стандартный баннер'},
                    {'game_specific_id': '301', 'name': 'Ивентовый баннер персонажа'},
                    {'game_specific_id': '400', 'name': 'Ивентовый баннер персонажа (параллельный)'},
                    {'game_specific_id': '302', 'name': 'Баннер оружия (Воплощение божества)'}
                ]
                for lt_data in lootbox_types_data_genshin:
                    if not LootboxType.query.filter_by(game_id=genshin_game.id,
                                                       game_specific_id=lt_data['game_specific_id']).first():
                        new_lt = LootboxType(game_id=genshin_game.id, game_specific_id=lt_data['game_specific_id'],
                                             name=lt_data['name'])
                        db.session.add(new_lt)
                db.session.commit()  # Коммитим типы лутбоксов
                app.logger.info("RUN.PY: Добавлены/проверены LootboxTypes для Genshin Impact.")
            else:
                app.logger.info("RUN.PY: Игра Genshin Impact уже существует.")

            cs2_game = Game.query.filter_by(slug='cs2').first()
            if not cs2_game:
                cs2_game = Game(name='Counter-Strike 2', slug='cs2')
                db.session.add(cs2_game)
                db.session.commit()
                app.logger.info(f"RUN.PY: Добавлена игра: Counter-Strike 2 (ID: {cs2_game.id})")
            else:
                app.logger.info("RUN.PY: Игра Counter-Strike 2 уже существует.")

            app.logger.info("RUN.PY: Проверка начальных данных завершена.")

        except Exception as e:
            app.logger.error(f"RUN.PY: Ошибка при заполнении начальных данных: {e}", exc_info=True)
            db.session.rollback()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Game': Game, 'LootboxType': LootboxType,
            'UserDrop': UserDrop, 'UserCS2InventoryItem': UserCS2InventoryItem, 'PriceCacheCS2': PriceCacheCS2}


if __name__ == '__main__':
    app.run()
