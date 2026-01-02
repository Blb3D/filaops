from app.db.session import SessionLocal
from app.models.user import User

db = SessionLocal()
users = db.query(User).limit(5).all()
for u in users:
    print(f'{u.id}: {u.email} ({u.account_type})')
db.close()
