import datetime
from flask import Flask
from flask_wtf import CSRFProtect
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_openid import OpenID
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
oid = OpenID()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    csrf.init_app(app)

    if not app.debug and not app.testing:
        import logging
        from logging import FileHandler

        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = FileHandler('logs/lootbox_analytics.log')

        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Lootbox Analytics startup')

    app.config.from_object(config_class)

    if not app.secret_key and 'SECRET_KEY' in app.config:
        app.secret_key = app.config['SECRET_KEY']
    elif not app.secret_key:
        raise ValueError("No SECRET_KEY set for Flask application")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oid.init_app(app)

    if not os.path.exists(app.config.get('OPENID_FS_STORE_PATH', os.path.join(app.instance_path, 'openid_store'))):
        os.makedirs(app.config.get('OPENID_FS_STORE_PATH', os.path.join(app.instance_path, 'openid_store')))

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.routes.import_data import bp as import_data_api_bp
    app.register_blueprint(import_data_api_bp, url_prefix='/import')

    from app.routes.cs2_api import bp_cs2_api
    app.register_blueprint(bp_cs2_api)

    if not os.path.exists(app.config['OPENID_FS_STORE_PATH']):
        os.makedirs(app.config['OPENID_FS_STORE_PATH'])

    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.datetime.now().year}

    return app


from app import models
