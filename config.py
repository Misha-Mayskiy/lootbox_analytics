import datetime
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DEFAULT_SQLITE_URL = 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or DEFAULT_SQLITE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENID_FS_STORE_PATH = os.path.join(basedir, 'openid_store')
    STEAM_API_KEY = os.environ.get('STEAM_API_KEY')
    PREFERRED_URL_SCHEME = 'https'
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_DURATION = datetime.timedelta(days=30)
