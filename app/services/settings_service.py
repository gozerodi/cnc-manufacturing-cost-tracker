from app.core.database import get_session
from app.core.security import hash_password, verify_password
from app.repositories import app_settings_repository

PERSONNEL_PAGE_PASSWORD_KEY = "personnel_page_password"


class InvalidPasswordError(Exception):
    pass


def verify_personnel_page_password(plain_password: str) -> bool:
    session = get_session()
    try:
        setting = app_settings_repository.get_by_key(session, PERSONNEL_PAGE_PASSWORD_KEY)
        if setting is None:
            return False
        return verify_password(plain_password, setting.value)
    finally:
        session.close()


def change_personnel_page_password(current_password: str, new_password: str) -> None:
    session = get_session()
    try:
        setting = app_settings_repository.get_by_key(session, PERSONNEL_PAGE_PASSWORD_KEY)
        if setting is None or not verify_password(current_password, setting.value):
            raise InvalidPasswordError("Current password is incorrect.")
        setting.value = hash_password(new_password)
        session.commit()
    finally:
        session.close()
