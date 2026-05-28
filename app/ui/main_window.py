"""Main application window with sidebar navigation and page stack."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.models.device import Device
from app.models.router_info import RouterInfo
from app.models.schedule import Schedule
from app.ui.theme import DARK_THEME
from app.utils.threading import PollingWorker

if TYPE_CHECKING:
    from app.router.client import RouterClient
    from app.store.app_store import AppStore
    from config.settings import AppSettings
    from database.db import LocalDatabase

logger = logging.getLogger(__name__)

# Navigation items: (page_key, display_label)
NAV_ITEMS = [
    ("dashboard", "Panel"),
    ("devices", "Dispositivos"),
    ("schedules", "Horarios"),
    ("guests", "Invitados"),
    ("settings", "Configuración"),
]


class MainWindow(QMainWindow):
    """Main application window for Router Manager."""

    def __init__(
        self,
        store: AppStore,
        router_client: RouterClient,
        settings: AppSettings,
        database: LocalDatabase,
    ) -> None:
        super().__init__()
        self._store = store
        self._router_client = router_client
        self._settings = settings
        self._database = database

        self._pages: dict[str, QWidget] = {}
        self._nav_buttons: dict[str, QPushButton] = {}
        self._polling_worker: PollingWorker | None = None

        self._setup_ui()
        self._connect_signals()
        self._restore_geometry()

        # Navigate to dashboard on startup
        self._navigate_to("dashboard")
        logger.info("MainWindow initialized")

    # ------------------------------------------------------------------ UI
    def _setup_ui(self) -> None:
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)
        self.setStyleSheet(DARK_THEME)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        root_layout.addWidget(self._build_sidebar(), 0)

        # Right side: topbar + page stack
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self._build_topbar(), 0)

        self._stack = QStackedWidget()
        right_layout.addWidget(self._stack, 1)

        root_layout.addWidget(right, 1)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Desconectado")
        self._status_bar.addPermanentWidget(self._status_label)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(0)

        title = QLabel("Router Manager")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #e4e4e7; "
            "padding: 0 16px 20px 16px;"
        )
        layout.addWidget(title)

        for page_key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=page_key: self._navigate_to(k))
            self._nav_buttons[page_key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        credit_label = QLabel('Hecho por <a href="https://github.com/axelmrak" style="color: #1e40af; text-decoration: none;">Axel Mrak</a>')
        credit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit_label.setOpenExternalLinks(True)
        credit_label.setStyleSheet("font-size: 11px; color: #52525b; padding: 2px 4px 0 4px;")
        layout.addWidget(credit_label)

        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(
            "color: #3f3f46; font-size: 10px; padding: 0 4px 4px 4px;"
        )
        layout.addWidget(version_label)

        return sidebar

    def _build_topbar(self) -> QWidget:
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(48)

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(16, 0, 16, 0)

        self._page_title = QLabel("Panel")
        self._page_title.setObjectName("title")
        layout.addWidget(self._page_title)

        layout.addStretch()

        self._conn_indicator = QLabel("\u25CF Desconectado")
        self._conn_indicator.setObjectName("connection-status")
        self._conn_indicator.setStyleSheet("color: #dc2626; font-size: 12px;")
        layout.addWidget(self._conn_indicator)

        return topbar

    # --------------------------------------------------------- Signals
    def _connect_signals(self) -> None:
        self._store.connection_status_changed.connect(self._on_connection_changed)
        self._store.error_occurred.connect(self._on_error)
        self._store.loading_changed.connect(self._on_loading)

    # --------------------------------------------------------- Navigation
    def _navigate_to(self, page_key: str) -> None:
        """Switch to the given page, creating it lazily if needed."""
        for key, btn in self._nav_buttons.items():
            btn.setChecked(key == page_key)

        page = self._pages.get(page_key)
        if page is None:
            page = self._create_page(page_key)
            if page is None:
                return
            self._pages[page_key] = page
            self._stack.addWidget(page)

        self._stack.setCurrentWidget(page)

        display_name = next(
            (label for key, label in NAV_ITEMS if key == page_key), page_key
        )
        self._page_title.setText(display_name)

    def _create_page(self, page_key: str) -> QWidget | None:
        """Lazily create a page widget by key."""
        if page_key == "dashboard":
            from app.ui.pages.dashboard import DashboardPage
            return DashboardPage(self._store, self._router_client)

        if page_key == "devices":
            from app.ui.pages.devices import DevicesPage
            return DevicesPage(self._store, self._router_client)

        if page_key == "schedules":
            from app.ui.pages.schedules import SchedulesPage
            return SchedulesPage(self._store, self._router_client)

        if page_key == "guests":
            from app.ui.pages.guests import GuestsPage
            return GuestsPage(self._store, self._router_client)

        if page_key == "settings":
            from app.ui.pages.settings import SettingsPage
            return SettingsPage(self._store, self._router_client, self._settings)

        logger.warning("Unknown page key: %s", page_key)
        return None

    # --------------------------------------------------------- Polling
    def start_polling(self, interval: int = 10) -> None:
        """Start the background polling worker."""
        if self._polling_worker is not None:
            self.stop_polling()

        self._polling_worker = PollingWorker(self._router_client, interval)
        self._polling_worker.devices_fetched.connect(self._on_devices_fetched)
        self._polling_worker.schedules_fetched.connect(self._on_schedules_fetched)
        self._polling_worker.system_info_fetched.connect(self._on_system_info_fetched)
        self._polling_worker.connection_lost.connect(self._on_connection_lost)
        self._polling_worker.connection_restored.connect(self._on_connection_restored)
        self._polling_worker.start()
        logger.info("Polling started with interval %ds", interval)

    def stop_polling(self) -> None:
        """Stop the background polling worker."""
        if self._polling_worker is not None:
            self._polling_worker.stop()
            self._polling_worker = None
            logger.info("Polling stopped")

    # --------------------------------------------------------- Polling slots
    def _on_devices_fetched(self, raw_devices: list) -> None:
        devices = [Device.from_router_data(d) for d in raw_devices]
        for device in devices:
            if self._store.is_guest(device.mac):
                device.is_guest = True
        self._store.set_devices(devices)
        guest_macs = [d.mac for d in devices if d.is_guest]
        self._store.load_guest_macs(guest_macs)

    def _on_schedules_fetched(self, raw_schedules: list) -> None:
        schedules = [Schedule.from_router_data(s) for s in raw_schedules]
        self._store.set_schedules(schedules)

    def _on_system_info_fetched(self, raw_info: dict) -> None:
        info = RouterInfo.from_router_data(raw_info)
        self._store.set_router_info(info)

    def _on_connection_lost(self, error_msg: str) -> None:
        self._store.set_connected(False)
        self._status_label.setText(f"Conexión perdida: {error_msg}")

    def _on_connection_restored(self) -> None:
        self._store.set_connected(True)
        self._status_label.setText("Conectado")

    # --------------------------------------------------------- Store slots
    def _on_connection_changed(self, connected: bool) -> None:
        if connected:
            self._conn_indicator.setText("\u25CF Conectado")
            self._conn_indicator.setStyleSheet("color: #16a34a; font-size: 12px;")
            self._status_label.setText("Conectado")
        else:
            self._conn_indicator.setText("\u25CF Desconectado")
            self._conn_indicator.setStyleSheet("color: #dc2626; font-size: 12px;")
            self._status_label.setText("Desconectado")

    def _on_error(self, title: str, message: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        self._status_bar.showMessage(f"Error: {title}", 5000)
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    def _on_loading(self, is_loading: bool) -> None:
        if is_loading:
            self._status_bar.showMessage("Cargando...")
        else:
            self._status_bar.clearMessage()

    # --------------------------------------------------------- Geometry
    def _restore_geometry(self) -> None:
        """Restore window geometry from settings if available."""
        geom = self._settings.get("window_geometry")
        if geom:
            try:
                from PySide6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromBase64(geom.encode("ascii")))
            except Exception:
                logger.debug("Failed to restore window geometry")

    def closeEvent(self, event) -> None:
        """Save geometry and stop polling on close."""
        try:
            geom = self.saveGeometry().toBase64().data().decode("ascii")
            self._settings.set("window_geometry", geom)
        except Exception:
            pass
        self.stop_polling()
        super().closeEvent(event)
