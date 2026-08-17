from PySide6.QtWidgets import QInputDialog, QMessageBox

from app.ui.main_window import PAGE_INDEX_ROLE, PROTECTED_ROLE, MainWindow


def _personnel_menu_item(window: MainWindow):
    for i in range(window.menu_list.count()):
        item = window.menu_list.item(i)
        if item.data(PROTECTED_ROLE):
            return item
    raise AssertionError("Protected menu item not found")


def test_wrong_password_does_not_switch_page(qapp, monkeypatch):
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: ("wrong_password", True))
    )
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    window = MainWindow(role="admin", username="admin1")
    window.stacked_pages.setCurrentIndex(0)
    item = _personnel_menu_item(window)

    window._on_menu_item_clicked(item)

    assert window.stacked_pages.currentIndex() == 0
    assert len(warnings) == 1


def test_correct_password_switches_page_and_refreshes(qapp, monkeypatch):
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: ("admin123", True))
    )

    window = MainWindow(role="admin", username="admin1")
    window.stacked_pages.setCurrentIndex(0)
    item = _personnel_menu_item(window)

    window._on_menu_item_clicked(item)

    expected_page_index = item.data(PAGE_INDEX_ROLE)
    assert window.stacked_pages.currentIndex() == expected_page_index


def test_cancel_dialog_does_not_switch_page(qapp, monkeypatch):
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))

    window = MainWindow(role="admin", username="admin1")
    window.stacked_pages.setCurrentIndex(0)
    item = _personnel_menu_item(window)

    window._on_menu_item_clicked(item)

    assert window.stacked_pages.currentIndex() == 0


def test_password_is_asked_again_on_every_visit_no_session_memory(qapp, monkeypatch):
    window = MainWindow(role="admin", username="admin1")
    item = _personnel_menu_item(window)
    protected_page_index = item.data(PAGE_INDEX_ROLE)

    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: ("admin123", True))
    )
    window._on_menu_item_clicked(item)
    assert window.stacked_pages.currentIndex() == protected_page_index

    window.stacked_pages.setCurrentIndex(0)

    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: ("wrong_password", True))
    )
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    window._on_menu_item_clicked(item)

    assert window.stacked_pages.currentIndex() == 0
