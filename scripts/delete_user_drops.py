from app.models import User, UserDrop
from app import db

username = input("Введите имя пользователя к очистке: ")
user = User.query.filter_by(username=f'{username}').first()
if user:
    drops_deleted = UserDrop.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    print(f"Удалено {drops_deleted} дропов для пользователя {user.username}")
else:
    print("Пользователь не найден")
