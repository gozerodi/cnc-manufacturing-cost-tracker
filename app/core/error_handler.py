import datetime
import os
import sys
import traceback

from PySide6.QtWidgets import QMessageBox

from app.core.config import get_base_dir

ERROR_LOG_FILENAME = "error_log.txt"


def _write_error_log(text: str) -> None:
    try:
        log_path = os.path.join(get_base_dir(), ERROR_LOG_FILENAME)
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(text)
    except OSError:
        pass


def handle_unexpected_exception(exc_type, exc_value, exc_traceback) -> None:
    """A windowed PyInstaller exe has no console/stderr, so the default behavior (trying to
    print the traceback to stderr) can silently kill the app. Instead we write the error to
    a log file and show the user a dialog; the app stays open and the user can continue.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _write_error_log(f"[{timestamp}]\n{details}\n")

    message_box = QMessageBox()
    message_box.setIcon(QMessageBox.Icon.Critical)
    message_box.setWindowTitle("Unexpected Error")
    message_box.setText(
        "An unexpected error occurred.\n\n"
        "The application will remain open, but the last action may not have completed. "
        f"Error details were saved to '{ERROR_LOG_FILENAME}'."
    )
    message_box.setDetailedText(details)
    message_box.exec()


def install_global_excepthook() -> None:
    sys.excepthook = handle_unexpected_exception
