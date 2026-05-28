"""Guest devices page for managing guest network devices."""

import logging

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QComboBox,
)
from PySide6.QtCore import Qt

from app.models.device import DeviceStatus
from app.widgets.card_widget import CardWidget
from app.widgets.status_badge import StatusBadge

logger = logging.getLogger(__name__)


class GuestsPage(QWidget):
    """Guest device management page."""

    def __init__(self, store, router_client):
        super().__init__()
        self._store = store
        self._router_client = router_client
        self._setup_ui()
        self._connect_signals()
        self._update_table()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Header with action buttons
        header_layout = QHBoxLayout()
        header_layout.addStretch()

        self._add_guest_btn = QPushButton("Agregar invitado")
        self._add_guest_btn.setObjectName("success")
        self._add_guest_btn.clicked.connect(self._on_add_guest)
        header_layout.addWidget(self._add_guest_btn)

        self._refresh_btn = QPushButton("Actualizar")
        self._refresh_btn.setObjectName("secondary")
        self._refresh_btn.clicked.connect(self._on_refresh)
        header_layout.addWidget(self._refresh_btn)

        main_layout.addLayout(header_layout)

        # Guest devices table
        table_card = CardWidget()
        table_layout = QVBoxLayout()

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Nombre",
            "Dirección IP",
            "Dirección MAC",
            "Estado",
            "Acciones",
        ])
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        table_layout.addWidget(self._table)
        table_card.content_layout().addLayout(table_layout)
        main_layout.addWidget(table_card, 1)

        # Empty state label
        self._empty_label = QLabel("No hay dispositivos invitados.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("subtitle")
        self._empty_label.hide()
        main_layout.addWidget(self._empty_label)

    def _connect_signals(self):
        self._store.guest_devices_updated.connect(self._update_table)
        self._store.devices_updated.connect(lambda *_: self._update_table())
        self._store.loading_changed.connect(self._on_loading_changed)

    def _update_table(self, guest_devices=None):
        if guest_devices is None:
            guest_devices = self._store.guest_devices

        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        if not guest_devices:
            self._empty_label.show()
            self._table.hide()
            return

        self._empty_label.hide()
        self._table.show()

        for device in guest_devices:
            self._add_device_row(device)

        self._table.setSortingEnabled(True)

    def _add_device_row(self, device):
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Device name
        name_item = QTableWidgetItem(device.display_name)
        name_item.setData(Qt.UserRole, device.mac)
        self._table.setItem(row, 0, name_item)

        # IP Address
        self._table.setItem(row, 1, QTableWidgetItem(device.ip))

        # MAC Address
        self._table.setItem(row, 2, QTableWidgetItem(device.mac))

        # Status badge
        status_widget = StatusBadge(status=device.status.value)
        self._table.setCellWidget(row, 3, status_widget)

        # Actions
        actions_widget = self._create_actions_widget(device)
        self._table.setCellWidget(row, 4, actions_widget)

    def _create_actions_widget(self, device):
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        if device.status == DeviceStatus.BLOCKED:
            unblock_btn = QPushButton("Desbloquear")
            unblock_btn.setObjectName("success")
            unblock_btn.setFixedWidth(85)
            unblock_btn.clicked.connect(lambda: self._on_block_unblock(device))
            layout.addWidget(unblock_btn)
        else:
            block_btn = QPushButton("Bloquear")
            block_btn.setObjectName("danger")
            block_btn.setFixedWidth(75)
            block_btn.clicked.connect(lambda: self._on_block_unblock(device))
            layout.addWidget(block_btn)

        remove_btn = QPushButton("Quitar")
        remove_btn.setObjectName("secondary")
        remove_btn.setFixedWidth(55)
        remove_btn.clicked.connect(lambda: self._on_remove_guest(device))
        layout.addWidget(remove_btn)

        return widget

    def _on_loading_changed(self, is_loading):
        self._refresh_btn.setEnabled(not is_loading)
        self._add_guest_btn.setEnabled(not is_loading)

    def _on_refresh(self):
        from app.utils.threading import WorkerThread

        self._store.set_loading(True)

        def fetch_devices():
            return self._router_client.get_devices()

        def on_result(devices_data):
            self._store.set_loading(False)
            from app.models.device import Device
            devices = [Device.from_router_data(d) for d in devices_data]
            self._store.set_devices(devices)

            for device in devices:
                if self._store.is_guest(device.mac):
                    device.is_guest = True

            guest_macs = [d.mac for d in devices if d.is_guest]
            self._store.load_guest_macs(guest_macs)

        def on_error(title, msg):
            self._store.set_loading(False)
            self._store.emit_error(title, msg)

        thread = WorkerThread(fetch_devices)
        thread.result.connect(on_result)
        thread.error.connect(on_error)
        thread.start()

    def _on_add_guest(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar invitado")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Seleccioná un dispositivo para marcar como invitado:"))

        device_combo = QComboBox()
        device_combo.setMinimumWidth(300)

        non_guests = [d for d in self._store.devices if not d.is_guest]
        for device in non_guests:
            device_combo.addItem(
                f"{device.display_name} ({device.ip})",
                device.mac,
            )

        layout.addWidget(device_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            mac = device_combo.currentData()
            if mac:
                self._store.add_guest(mac)

    def _on_remove_guest(self, device):
        self._store.remove_guest(device.mac)
        self._update_table()

    def _on_block_unblock(self, device):
        from app.utils.threading import WorkerThread

        if device.status == DeviceStatus.BLOCKED:
            def unblock():
                return self._router_client.unblock_device(device.mac)

            def on_result(success):
                if success:
                    self._store.update_device(device.mac, status="online")
                    self._update_table()

            def on_error(title, msg):
                self._store.emit_error(title, msg)

            thread = WorkerThread(unblock)
            thread.result.connect(on_result)
            thread.error.connect(on_error)
            thread.start()
        else:
            def block():
                return self._router_client.block_device(device.mac)

            def on_result(success):
                if success:
                    self._store.update_device(device.mac, status="blocked")
                    self._update_table()

            def on_error(title, msg):
                self._store.emit_error(title, msg)

            thread = WorkerThread(block)
            thread.result.connect(on_result)
            thread.error.connect(on_error)
            thread.start()
