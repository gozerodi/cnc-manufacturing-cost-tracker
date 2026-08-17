import sys

import qdarktheme
from PySide6.QtWidgets import QApplication, QMessageBox
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.config import ConfigError
from app.core.database import check_connection
from app.core.error_handler import install_global_excepthook
from app.ui.login_window import LoginWindow


def main() -> int:
    app = QApplication(sys.argv)
    install_global_excepthook()
    qdarktheme.setup_theme("auto")

    try:
        check_connection()
    except ConfigError as exc:
        QMessageBox.critical(None, "Configuration Error", str(exc))
        return 1
    except (OperationalError, SQLAlchemyError) as exc:
        QMessageBox.critical(
            None,
            "Database Connection Error",
            "Could not connect to the database. Please check the connection "
            f"details in config.ini.\n\nDetails: {exc}",
        )
        return 1

    login_window = LoginWindow()
    login_window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
