from app.database import engine, SessionLocal, Base
from app.models import User
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

USERS = [
    ("hr",            "hr",      "人事",  "HR专员"),
    ("mgr_delivery",  "manager", "交付",  "交付经理"),
    ("mgr_rd",        "manager", "产研",  "产研经理"),
    ("mgr_marketing", "manager", "市场",  "市场经理"),
    ("mgr_ops1",      "manager", "运营1", "运营经理1"),
    ("mgr_ops2",      "manager", "运营2", "运营经理2"),
    ("mgr_sales1",    "manager", "销售1", "销售经理1"),
    ("mgr_sales2",    "manager", "销售2", "销售经理2"),
    ("mgr_finance",   "manager", "财务",  "财务经理"),
    ("mgr_hr",        "manager", "人事",  "人事经理"),
    ("mgr_admin",     "manager", "综合办","综合办经理"),
    ("admin",         "admin",   "综合办","系统管理员"),
]

DEFAULT_PASSWORD = "Smart2026!"

created = 0
for username, role, _dept, display_name in USERS:
    if not db.query(User).filter(User.username == username).first():
        db.add(User(
            username=username,
            password_hash=hash_password("Admin@2026" if role == "admin" else DEFAULT_PASSWORD),
            role=role,
            display_name=display_name,
            must_change_password=(role == "admin"),
        ))
        created += 1

db.commit()
print(f"Seeded {created} new users ({len(USERS)} total defined)")
db.close()
