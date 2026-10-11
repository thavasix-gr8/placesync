from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import User


def create_admin():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.email == "admin@placesync.com").first()
        if existing_admin:
            print("Admin account already exists")
            return

        admin = User(
            name="PlaceSync Admin",
            email="admin@placesync.com",
            password_hash=hash_password("admin123"),
            role="admin",
            register_number="ADMIN001",
            department="Administration",
            batch="",
            cgpa=0,
            arrears=0,
        )
        db.add(admin)
        db.commit()
        print("Admin created: admin@placesync.com")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
