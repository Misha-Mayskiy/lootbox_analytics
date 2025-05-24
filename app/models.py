from flask_login import UserMixin
import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from app import login_manager
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), index=True, unique=True, nullable=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=True)
    password_hash = db.Column(db.String(256))
    steam_id = db.Column(db.String(64), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    api_key = db.Column(db.String(128), unique=True, nullable=True, index=True)
    cs2_investment_amount = db.Column(db.Float, nullable=True, default=0.0)

    drops = db.relationship('UserDrop', backref='user', lazy='dynamic')
    cs2_inventory_items = db.relationship('UserCS2InventoryItem', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

    lootbox_types = db.relationship('LootboxType', backref='game', lazy=True)
    drops = db.relationship('UserDrop', backref='game', lazy=True)

    def __repr__(self):
        return f'<Game {self.name}>'


class LootboxType(db.Model):
    """Определяет типы 'лутбоксов' для каждой игры (баннеры, кейсы, паки карт)"""
    __tablename__ = 'lootbox_types'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    game_specific_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=False)

    drops = db.relationship('UserDrop', backref='lootbox_type', lazy=True)

    __table_args__ = (db.UniqueConstraint('game_id', 'game_specific_id', name='uq_game_specific_lootbox'),)

    def __repr__(self):
        return f'<LootboxType {self.name} (Game: {self.game.name})>'


class UserDrop(db.Model):
    """Основная таблица для хранения информации о каждом выпавшем предмете"""
    __tablename__ = 'user_drops'
    id = db.Column(db.Integer, primary_key=True)  # Внутренний ID записи
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    lootbox_type_id = db.Column(db.Integer, db.ForeignKey('lootbox_types.id'), nullable=False)

    external_drop_id = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    item_name = db.Column(db.String(255), nullable=False)
    # Текстовое представление типа предмета (Персонаж, Оружие, Скин, Карта и т.д.)
    item_type_text = db.Column(db.String(100), nullable=True)
    # Текстовое представление редкости (5 звезд, Covert, Легендарная и т.д.)
    item_rarity_text = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # Для хранения оригинального JSON-объекта дропа, если потребуется для отладки или будущей обработки
    raw_data = db.Column(db.JSON, nullable=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'game_id', 'external_drop_id', name='uq_user_game_external_drop'),)

    def __repr__(self):
        return f'<UserDrop ID: {self.id} Item: {self.item_name} User: {self.user.username}>'


class UserCS2InventoryItem(db.Model):
    __tablename__ = 'user_cs2_inventory_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)  # Будет ID игры CS2

    asset_id = db.Column(db.String(255), nullable=False,
                         index=True)  # Steam asset_id, уникален для предмета в инвентаре
    class_id = db.Column(db.String(255), nullable=False, index=True)
    instance_id = db.Column(db.String(255), nullable=False, index=True)

    name = db.Column(db.String(255), nullable=False)  # "AK-47 | Redline"
    market_hash_name = db.Column(db.String(255), nullable=False, index=True)  # Для запроса цены

    item_type_str = db.Column(db.String(100))  # "Rifle", "Knife", "Sticker" (из тегов)
    rarity_str = db.Column(db.String(100))  # "Covert", "Mil-Spec" (из тегов)
    rarity_internal_name = db.Column(db.String(100), nullable=True, index=True)  # internal_name
    rarity_color_hex = db.Column(db.String(7), nullable=True)  # HEX цвет из тега (e.g., "eb4b4b")
    exterior_str = db.Column(db.String(100))  # "Factory New", "Field-Tested" (из тегов)

    icon_url = db.Column(db.String(512))

    current_market_price = db.Column(db.Float, nullable=True)  # Цена в USD или выбранной валюте
    price_currency = db.Column(db.String(10), nullable=True)  # e.g., "USD", "RUB"
    last_price_update = db.Column(db.DateTime, nullable=True)

    tradable = db.Column(db.Boolean, default=True)
    marketable = db.Column(db.Boolean, default=True)

    snapshot_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'game_id', 'asset_id', name='uq_user_game_cs2_asset'),)

    def __repr__(self):
        return f'<UserCS2InventoryItem {self.name} (User: {self.user_id})>'


class PriceCacheCS2(db.Model):
    __tablename__ = 'price_cache_cs2'
    market_hash_name = db.Column(db.String(255), primary_key=True)
    price = db.Column(db.Float)
    currency = db.Column(db.String(10))  # e.g., 'USD', 'RUB' (Steam Market API возвращает код валюты)
    volume = db.Column(db.Integer, nullable=True)  # Количество продаж за 24 часа (если API отдает)
    last_fetched_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<PriceCacheCS2 {self.market_hash_name}: {self.price} {self.currency}>'
