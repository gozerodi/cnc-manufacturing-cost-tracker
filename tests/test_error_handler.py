import sys

from PySide6.QtWidgets import QMessageBox

from app.core import error_handler


def _raise_and_capture():
    try:
        raise RuntimeError("test error")
    except RuntimeError:
        return sys.exc_info()


def test_handle_unexpected_exception_shows_dialog_and_logs(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr(error_handler, "get_base_dir", lambda: str(tmp_path))

    exec_calls = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: exec_calls.append(self) or 0)

    exc_type, exc_value, exc_tb = _raise_and_capture()
    error_handler.handle_unexpected_exception(exc_type, exc_value, exc_tb)

    assert len(exec_calls) == 1

    log_path = tmp_path / error_handler.ERROR_LOG_FILENAME
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "RuntimeError" in content
    assert "test error" in content


def test_handle_unexpected_exception_survives_when_log_write_fails(qapp, monkeypatch, tmp_path):
    # If the target folder doesn't exist (e.g. no write permission next to the exe),
    # writing the log should fail silently, but the dialog must still be shown.
    monkeypatch.setattr(error_handler, "get_base_dir", lambda: str(tmp_path / "missing_folder"))

    exec_calls = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: exec_calls.append(self) or 0)

    exc_type, exc_value, exc_tb = _raise_and_capture()
    error_handler.handle_unexpected_exception(exc_type, exc_value, exc_tb)

    assert len(exec_calls) == 1


def test_keyboard_interrupt_delegates_to_default_hook(monkeypatch):
    exec_calls = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: exec_calls.append(self) or 0)

    default_hook_calls = []
    monkeypatch.setattr(
        sys, "__excepthook__", lambda *args: default_hook_calls.append(args)
    )

    try:
        raise KeyboardInterrupt()
    except KeyboardInterrupt:
        exc_type, exc_value, exc_tb = sys.exc_info()

    error_handler.handle_unexpected_exception(exc_type, exc_value, exc_tb)

    assert len(default_hook_calls) == 1
    assert exec_calls == []


def test_install_global_excepthook_sets_sys_excepthook():
    original_hook = sys.excepthook
    try:
        error_handler.install_global_excepthook()
        assert sys.excepthook is error_handler.handle_unexpected_exception
    finally:
        sys.excepthook = original_hook
