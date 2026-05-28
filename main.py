"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from app.router.client import RouterClient
from app.store.app_store import AppStore
from app.ui.main_window import MainWindow
from app.utils.logging_setup import (
    install_crash_handler,
    qt_message_handler,
    setup_logging,
)
from config.settings import AppSettings
from database.db import LocalDatabase


def main() -> None:
    """Initialize and run the Router Manager application."""
    # --- Logging & crash handling (must come first) ---
    setup_logging()
    install_crash_handler()

    import logging

    logger = logging.getLogger(__name__)

    app = QApplication(sys.argv)

    # Route Qt warnings/errors through Python logging
    from PySide6 import QtCore

    QtCore.qInstallMessageHandler(qt_message_handler)

    app.setApplicationName("Router Manager")
    app.setApplicationVersion("0.1.0")

    # Initialize services
    settings = AppSettings()
    database = LocalDatabase()
    store = AppStore()

    router_client = RouterClient(
        host=settings.get("router_host", "192.168.1.1"),
        username=settings.get("router_username", "root"),
        password=settings.get("router_password", ""),
    )

    # Load persisted data into store
    store.load_aliases(database.get_aliases())
    guest_macs = database.get_guest_macs()
    if guest_macs:
        store.load_guest_macs(guest_macs)

    # Create main window with all dependencies
    window = MainWindow(
        store=store,
        router_client=router_client,
        settings=settings,
        database=database,
    )
    window.setWindowTitle("Router Manager")
    window.show()

    # Auto-login and start polling if configured
    if settings.get("auto_login") and settings.get("router_password"):
        from app.utils.threading import WorkerThread

        def try_login():
            router_client.login()
            return True

        def on_login_success(result):
            store.set_connected(True)
            interval = settings.get("polling_interval", 10)
            window.start_polling(interval)
            logger.info("Auto-login successful, polling started")

        def on_login_error(title, msg):
            store.set_connected(False)
            logger.warning("Auto-login failed: %s", msg)

        login_thread = WorkerThread(try_login)
        login_thread.result.connect(on_login_success)
        login_thread.error.connect(on_login_error)
        login_thread.start()
        # Keep reference to prevent GC while thread is running
        window._login_thread = login_thread

    def cleanup() -> None:
        window.stop_polling()
        try:
            if router_client.auth_token:
                router_client.logout()
        except Exception:
            pass
        logger.info("Application shutting down")

    app.aboutToQuit.connect(cleanup)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
