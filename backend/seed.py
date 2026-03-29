from app.database import engine, SessionLocal, Base
from app.models import User
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(User).filter(User.username == "admin").first():
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        role="manager",
        display_name="管理员",
    )
    db.add(admin)

    hr = User(
        username="hr",
        password_hash=hash_password("hr123"),
        role="hr",
        display_name="HR专员",
    )
    db.add(hr)
    db.commit()
    print("Seeded admin and hr users")
else:
    print("Users already exist")

db.close()
