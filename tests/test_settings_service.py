import pytest

from app.services import settings_service

DEFAULT_PASSWORD = "admin123"


@pytest.fixture(autouse=True)
def restore_default_password():
    yield
    if not settings_service.verify_personnel_page_password(DEFAULT_PASSWORD):
        for candidate in ("temp_test_password_1", "temp_test_password_2"):
            try:
                settings_service.change_personnel_page_password(candidate, DEFAULT_PASSWORD)
                break
            except settings_service.InvalidPasswordError:
                continue


def test_default_password_verifies():
    assert settings_service.verify_personnel_page_password(DEFAULT_PASSWORD)
    assert not settings_service.verify_personnel_page_password("wrong_password")


def test_change_password_requires_correct_current_password():
    with pytest.raises(settings_service.InvalidPasswordError):
        settings_service.change_personnel_page_password("wrong_password", "temp_test_password_1")


def test_change_password_then_new_password_works():
    settings_service.change_personnel_page_password(DEFAULT_PASSWORD, "temp_test_password_1")
    assert settings_service.verify_personnel_page_password("temp_test_password_1")
    assert not settings_service.verify_personnel_page_password(DEFAULT_PASSWORD)

    settings_service.change_personnel_page_password("temp_test_password_1", DEFAULT_PASSWORD)
    assert settings_service.verify_personnel_page_password(DEFAULT_PASSWORD)
