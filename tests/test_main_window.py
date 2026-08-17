from PySide6.QtWidgets import QScrollArea

from app.ui.main_window import ADMIN_MENU, PAGE_INDEX_ROLE, STAFF_MENU, MainWindow, _page_content


def _expected_page_count(menu_structure) -> int:
    return sum(1 if children is None else len(children) for _label, children in menu_structure)


def test_admin_menu_page_count(qapp):
    window = MainWindow(role="admin", username="admin1")
    assert window.stacked_pages.count() == _expected_page_count(ADMIN_MENU) + 1


def test_staff_menu_page_count(qapp):
    window = MainWindow(role="staff", username="staff1")
    assert window.stacked_pages.count() == _expected_page_count(STAFF_MENU) + 1


def test_initial_page_is_welcome_not_protected_content(qapp):
    window = MainWindow(role="admin", username="admin1")
    assert window.stacked_pages.currentIndex() == window._welcome_page_index

    protected_item = next(
        window.menu_list.item(i)
        for i in range(window.menu_list.count())
        if window.menu_list.item(i).data(PAGE_INDEX_ROLE) is not None
        and window.menu_list.item(i).text().strip().startswith("Personnel Setup")
    )
    assert window.stacked_pages.currentIndex() != protected_item.data(PAGE_INDEX_ROLE)


def test_leaf_item_click_switches_page(qapp):
    window = MainWindow(role="admin", username="admin1")
    leaf_items = [
        window.menu_list.item(i)
        for i in range(window.menu_list.count())
        if window.menu_list.item(i).data(PAGE_INDEX_ROLE) is not None
    ]
    assert len(leaf_items) == _expected_page_count(ADMIN_MENU)

    target_item = leaf_items[2]
    window._on_menu_item_clicked(target_item)
    assert window.stacked_pages.currentIndex() == target_item.data(PAGE_INDEX_ROLE)


def test_header_item_click_does_nothing(qapp):
    window = MainWindow(role="admin", username="admin1")
    header_items = [
        window.menu_list.item(i)
        for i in range(window.menu_list.count())
        if window.menu_list.item(i).data(PAGE_INDEX_ROLE) is None
    ]
    assert len(header_items) == len(ADMIN_MENU)

    window.stacked_pages.setCurrentIndex(0)
    window._on_menu_item_clicked(header_items[0])
    assert window.stacked_pages.currentIndex() == 0


def test_all_menu_pages_are_scrollable(qapp):
    for role, username, menu in (("admin", "admin1", ADMIN_MENU), ("staff", "staff1", STAFF_MENU)):
        window = MainWindow(role=role, username=username)
        leaf_items = [
            window.menu_list.item(i)
            for i in range(window.menu_list.count())
            if window.menu_list.item(i).data(PAGE_INDEX_ROLE) is not None
        ]
        assert len(leaf_items) == _expected_page_count(menu)

        for item in leaf_items:
            page_index = item.data(PAGE_INDEX_ROLE)
            container = window.stacked_pages.widget(page_index)
            assert isinstance(container, QScrollArea), item.text()
            assert container.widgetResizable() is True
            assert _page_content(container) is container.widget()
