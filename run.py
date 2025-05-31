import os

from flask import current_app
from flask_migrate import upgrade

from app import create_app, db
from app.models import User, Game

app = create_app()

if os.environ.get('RENDER') == 'true' or os.environ.get('FLASK_ENV') == 'production':
    with app.app_context():
        try:
            current_app.logger.info("Попытка применить миграции БД...")
            upgrade()
            current_app.logger.info("Миграции БД успешно применены (или уже были актуальны).")
        except Exception as e:
            current_app.logger.error(f"Ошибка при автоматическом применении миграций: {e}")


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Game': Game}


if __name__ == '__main__':
    app.run()
