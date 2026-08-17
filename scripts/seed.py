"""Creates the demo login users and default settings. Skips ones that already exist on re-run."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_session
from app.core.security import hash_password
from app.models import AppSetting, User

PERSONNEL_PAGE_PASSWORD_KEY = "personnel_page_password"


def seed() -> None:
    session = get_session()
    try:
        if not session.query(User).filter_by(username="admin1").first():
            session.add(
                User(
                    username="admin1",
                    password_hash=hash_password("admin123"),
                    role="admin",
                )
            )
            print("User created: admin1")
        else:
            print("User already exists, skipping: admin1")

        if not session.query(User).filter_by(username="staff1").first():
            session.add(
                User(
                    username="staff1",
                    password_hash=hash_password("staff123"),
                    role="staff",
                )
            )
            print("User created: staff1")
        else:
            print("User already exists, skipping: staff1")

        if not session.query(AppSetting).filter_by(key=PERSONNEL_PAGE_PASSWORD_KEY).first():
            session.add(
                AppSetting(
                    key=PERSONNEL_PAGE_PASSWORD_KEY,
                    value=hash_password("admin123"),
                )
            )
            print(f"Setting created: {PERSONNEL_PAGE_PASSWORD_KEY}")
        else:
            print(f"Setting already exists, skipping: {PERSONNEL_PAGE_PASSWORD_KEY}")

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed()
