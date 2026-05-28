"""Devices page with device table, search, filter, and actions."""

import logging
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QAbstractItemView,
    QLabel,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from app.models.device import DeviceStatus
from app.widgets.status_badge import StatusBadge
from app.widgets.card_widget import CardWidget

logger = logging.getLogger(__name__)


class DevicesPage(QWidget):
    """Main devices page with device table and controls."""

    def __init__(self, store, router_client):
        super().__init__()
        self._store = store
        self._router_client = router_client
        self._all_devices = []
        self._setup_ui()
        self._connect_signals()
        self._update_table()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Search bar
        search_layout = QHBoxLayout()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Buscar dispositivos...")
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.setMinimumWidth(300)
        search_layout.addWidget(self._search_input, 1)

        main_layout.addLayout(search_layout)

        # Filter row
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Estado:"))
        self._status_filter = QComboBox()
        self._status_filter.addItems(["Todos", "En línea", "Desconectado", "Bloqueado"])
        self._status_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._status_filter)

        filter_layout.addStretch()

        self._refresh_btn = QPushButton("Actualizar")
        self._refresh_btn.clicked.connect(self._on_refresh)
        filter_layout.addWidget(self._refresh_btn)

        main_layout.addLayout(filter_layout)

        # Device table
        table_card = CardWidget()
        table_layout = QVBoxLayout()

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Nombre",
            "Dirección IP",
            "Dirección MAC",
            "Estado",
            "Internet",
            "Horario",
            "Última vez",
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
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.cellDoubleClicked.connect(self._on_double_click)

        table_layout.addWidget(self._table)
        table_card.content_layout().addLayout(table_layout)
        main_layout.addWidget(table_card, 1)

    def _connect_signals(self):
        self._store.devices_updated.connect(self._on_devices_updated)
        self._store.device_changed.connect(self._on_device_changed)
        self._store.schedules_updated.connect(self._update_schedule_column)
        self._store.loading_changed.connect(self._on_loading_changed)

    def _on_devices_updated(self, devices):
        self._all_devices = devices
        self._update_table()

    def _on_device_changed(self, mac):
        self._update_table()

    def _update_table(self):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        search_text = self._search_input.text().lower()
        status_filter = self._status_filter.currentText()

        filtered_devices = self._all_devices
        if search_text:
            filtered_devices = [
                d for d in filtered_devices
                if (
                    search_text in d.display_name.lower()
                    or search_text in d.ip.lower()
                    or search_text in d.mac.lower()
                    or search_text in (d.hostname or "").lower()
                )
            ]

        if status_filter != "Todos":
            status_map = {
                "En línea": DeviceStatus.ONLINE,
                "Desconectado": DeviceStatus.OFFLINE,
                "Bloqueado": DeviceStatus.BLOCKED,
            }
            target_status = status_map.get(status_filter)
            if target_status:
                filtered_devices = [d for d in filtered_devices if d.status == target_status]

        for device in filtered_devices:
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

        # Internet access indicator
        internet_text = "Sí" if device.internet_access else "No"
        internet_item = QTableWidgetItem(internet_text)
        internet_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 4, internet_item)

        # Schedule
        schedule_name = "Ninguno"
        if device.schedule_id:
            for schedule in self._store.schedules:
                if schedule.id == device.schedule_id:
                    schedule_name = schedule.name
                    break
        schedule_item = QTableWidgetItem(schedule_name)
        self._table.setItem(row, 5, schedule_item)

        # Last seen
        last_seen = "Nunca"
        if device.last_seen:
            if isinstance(device.last_seen, datetime):
                last_seen = device.last_seen.strftime("%Y-%m-%d %H:%M")
            else:
                last_seen = str(device.last_seen)
        self._table.setItem(row, 6, QTableWidgetItem(last_seen))

        # Actions widget
        actions_widget = self._create_actions_widget(device)
        self._table.setCellWidget(row, 7, actions_widget)

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

        timer_btn = QPushButton("Timer")
        timer_btn.setObjectName("secondary")
        timer_btn.setFixedWidth(55)
        timer_btn.clicked.connect(lambda: self._on_timer_clicked(device))
        layout.addWidget(timer_btn)

        more_btn = QPushButton("...")
        more_btn.setFixedWidth(30)
        more_btn.clicked.connect(lambda: self._on_more_clicked(device, more_btn))
        layout.addWidget(more_btn)

        return widget

    def _update_schedule_column(self, schedules):
        self._update_table()

    def _on_loading_changed(self, is_loading):
        self._refresh_btn.setEnabled(not is_loading)

    def _on_search_changed(self, text):
        self._update_table()

    def _on_filter_changed(self, index):
        self._update_table()

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

        def on_error(title, msg):
            self._store.set_loading(False)
            self._store.emit_error(title, msg)

        thread = WorkerThread(fetch_devices)
        thread.result.connect(on_result)
        thread.error.connect(on_error)
        thread.start()

    def _on_block_unblock(self, device):
        from app.utils.threading import WorkerThread

        if device.status == DeviceStatus.BLOCKED:
            def unblock():
                return self._router_client.unblock_device(device.mac)

            def on_result(success):
                if success:
                    self._store.update_device(device.mac, status="online")

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

            def on_error(title, msg):
                self._store.emit_error(title, msg)

            thread = WorkerThread(block)
            thread.result.connect(on_result)
            thread.error.connect(on_error)
            thread.start()

    def _on_timer_clicked(self, device):
        from app.ui.dialogs.timer_dialog import TimerDialog

        existing_schedule = None
        for schedule in self._store.schedules:
            if schedule.mac.upper() == device.mac.upper():
                existing_schedule = schedule
                break

        dialog = TimerDialog(
            self._store,
            self._router_client,
            device_mac=device.mac,
            parent=self,
            existing_schedule=existing_schedule,
        )
        dialog.exec()
        self._on_refresh()

    def _on_more_clicked(self, device, button):
        menu = QMenu(self)

        rename_action = QAction("Renombrar", self)
        rename_action.triggered.connect(lambda: self._on_rename_device(device))
        menu.addAction(rename_action)

        guest_action = QAction("Marcar como invitado" if not device.is_guest else "Quitar de invitados", self)
        guest_action.triggered.connect(lambda: self._on_toggle_guest(device))
        menu.addAction(guest_action)

        menu.addSeparator()

        copy_mac_action = QAction("Copiar dirección MAC", self)
        copy_mac_action.triggered.connect(lambda: self._copy_to_clipboard(device.mac))
        menu.addAction(copy_mac_action)

        copy_ip_action = QAction("Copiar dirección IP", self)
        copy_ip_action.triggered.connect(lambda: self._copy_to_clipboard(device.ip))
        menu.addAction(copy_ip_action)

        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _on_context_menu(self, position):
        row = self._table.rowAt(position.y())
        if row < 0:
            return

        item = self._table.item(row, 0)
        if not item:
            return

        mac = item.data(Qt.UserRole)
        device = self._store.get_device_by_mac(mac)
        if not device:
            return

        self._on_more_clicked(device, self._table.viewport())

    def _on_double_click(self, row, column):
        item = self._table.item(row, 0)
        if not item:
            return

        mac = item.data(Qt.UserRole)
        device = self._store.get_device_by_mac(mac)
        if device:
            self._on_rename_device(device)

    def _on_rename_device(self, device):
        from app.ui.dialogs.device_dialog import DeviceDialog

        dialog = DeviceDialog(device, parent=self)
        if dialog.exec():
            new_name, is_guest = dialog.get_result()
            if new_name:
                self._store.set_alias(device.mac, new_name)
            if is_guest != device.is_guest:
                if is_guest:
                    self._store.add_guest(device.mac)
                else:
                    self._store.remove_guest(device.mac)
            self._update_table()

    def _on_toggle_guest(self, device):
        if device.is_guest:
            self._store.remove_guest(device.mac)
        else:
            self._store.add_guest(device.mac)
        self._update_table()

    def _copy_to_clipboard(self, text):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
