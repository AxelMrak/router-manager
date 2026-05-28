"""Dashboard page with summary cards and router information."""

import logging

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGridLayout,
)
from PySide6.QtCore import Qt

from app.models.device import DeviceStatus
from app.widgets.card_widget import CardWidget

logger = logging.getLogger(__name__)


class DashboardPage(QWidget):
    """Dashboard page showing summary stats and router info."""

    def __init__(self, store, router_client):
        super().__init__()
        self._store = store
        self._router_client = router_client
        self._setup_ui()
        self._connect_signals()
        self._update_stats()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Stats cards row
        self._stats_cards = {}
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        stat_configs = [
            ("total", "Dispositivos"),
            ("online", "En línea"),
            ("blocked", "Bloqueados"),
            ("schedules", "Horarios activos"),
        ]

        for key, label in stat_configs:
            card = self._create_stat_card(key, label)
            self._stats_cards[key] = card
            stats_layout.addWidget(card)

        main_layout.addLayout(stats_layout)

        # Router info card
        router_card = CardWidget()
        router_layout = QVBoxLayout()
        router_layout.setSpacing(8)

        router_title = QLabel("Información del router")
        router_title.setObjectName("section-header")
        router_layout.addWidget(router_title)

        self._router_details = QGridLayout()
        self._router_details.setSpacing(6)
        router_layout.addLayout(self._router_details)

        # Initialize router info labels
        self._router_labels = {}
        info_items = [
            ("hostname", "Nombre"),
            ("model", "Modelo"),
            ("firmware", "Firmware"),
            ("uptime", "Tiempo activo"),
            ("ip", "Dirección IP"),
        ]
        for idx, (key, label_text) in enumerate(info_items):
            label_name = QLabel(f"{label_text}")
            label_name.setObjectName("subtitle")
            label_value = QLabel("\u2014")
            self._router_details.addWidget(label_name, idx, 0)
            self._router_details.addWidget(label_value, idx, 1)
            self._router_labels[key] = label_value

        router_card.content_layout().addLayout(router_layout)
        main_layout.addWidget(router_card)

        # Quick actions
        actions_card = CardWidget()
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        actions_title = QLabel("Acciones rápidas")
        actions_title.setObjectName("section-header")
        actions_layout.addWidget(actions_title)

        actions_buttons = QHBoxLayout()

        self._refresh_btn = QPushButton("Actualizar todo")
        self._refresh_btn.setObjectName("secondary")
        self._refresh_btn.clicked.connect(self._on_refresh)
        actions_buttons.addWidget(self._refresh_btn)

        self._block_guests_btn = QPushButton("Bloquear invitados")
        self._block_guests_btn.setObjectName("danger")
        self._block_guests_btn.clicked.connect(self._on_block_guests)
        actions_buttons.addWidget(self._block_guests_btn)

        actions_buttons.addStretch()

        actions_layout.addLayout(actions_buttons)
        actions_card.content_layout().addLayout(actions_layout)
        main_layout.addWidget(actions_card)

        main_layout.addStretch()

    def _create_stat_card(self, key, label):
        card = CardWidget()
        card_layout = QVBoxLayout()
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_label = QLabel("0")
        value_label.setObjectName("stat-value")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(label)
        desc_label.setObjectName("stat-label")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(value_label)
        card_layout.addWidget(desc_label)
        card.content_layout().addLayout(card_layout)

        card._value_label = value_label
        return card

    def _connect_signals(self):
        self._store.devices_updated.connect(self._update_stats)
        self._store.schedules_updated.connect(self._update_stats)
        self._store.router_info_updated.connect(self._update_router_info)
        self._store.connection_status_changed.connect(self._on_connection_changed)

    def _update_stats(self, *_args):
        devices = self._store.devices
        schedules = self._store.schedules

        total = len(devices)
        online = len([d for d in devices if d.status == DeviceStatus.ONLINE])
        blocked = len([d for d in devices if d.status == DeviceStatus.BLOCKED])
        active_schedules = len([s for s in schedules if s.enabled])

        self._stats_cards["total"]._value_label.setText(str(total))
        self._stats_cards["online"]._value_label.setText(str(online))
        self._stats_cards["blocked"]._value_label.setText(str(blocked))
        self._stats_cards["schedules"]._value_label.setText(str(active_schedules))

    def _update_router_info(self, router_info):
        self._router_labels["hostname"].setText(router_info.hostname or "\u2014")
        self._router_labels["model"].setText(router_info.model or "\u2014")
        self._router_labels["firmware"].setText(router_info.firmware_version or "\u2014")
        self._router_labels["uptime"].setText(router_info.uptime_display)
        self._router_labels["ip"].setText(router_info.ip_address or "\u2014")

    def _on_connection_changed(self, connected):
        self._refresh_btn.setEnabled(connected)
        self._block_guests_btn.setEnabled(connected)

    def _on_refresh(self):
        if self._router_client and self._store.is_connected:
            from app.utils.threading import WorkerThread

            self._store.set_loading(True)

            def fetch_all():
                devices = self._router_client.get_devices()
                schedules = self._router_client.get_schedules()
                system_info = self._router_client.get_system_info()
                return devices, schedules, system_info

            def on_result(result):
                self._store.set_loading(False)
                devices_data, schedules_data, system_info = result

                from app.models.device import Device
                from app.models.schedule import Schedule
                from app.models.router_info import RouterInfo

                devices = [Device.from_router_data(d) for d in devices_data]
                schedules = [Schedule.from_router_data(s) for s in schedules_data]
                router_info = RouterInfo.from_router_data(system_info)

                self._store.set_devices(devices)
                self._store.set_schedules(schedules)
                self._store.set_router_info(router_info)

            def on_error(title, msg):
                self._store.set_loading(False)
                self._store.emit_error(title, msg)

            thread = WorkerThread(fetch_all)
            thread.result.connect(on_result)
            thread.error.connect(on_error)
            thread.start()

    def _on_block_guests(self):
        guest_devices = self._store.guest_devices
        if not guest_devices:
            return

        from app.ui.dialogs.confirm_dialog import ConfirmDialog

        dialog = ConfirmDialog(
            "Bloquear invitados",
            f"¿Bloquear {len(guest_devices)} dispositivo(s) invitado(s)?",
            danger=True,
        )

        if dialog.exec():
            from app.utils.threading import WorkerThread

            for device in guest_devices:
                if device.status != DeviceStatus.BLOCKED:
                    thread = WorkerThread(self._router_client.block_device, device.mac)
                    thread.start()
