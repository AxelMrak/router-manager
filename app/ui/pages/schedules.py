"""Schedules page for managing device internet access schedules."""

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
    QCheckBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt

from app.widgets.card_widget import CardWidget

logger = logging.getLogger(__name__)


class SchedulesPage(QWidget):
    """Schedule management page."""

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

        # Header with action button
        header_layout = QHBoxLayout()
        header_layout.addStretch()

        self._new_schedule_btn = QPushButton("Nuevo horario")
        self._new_schedule_btn.setObjectName("success")
        self._new_schedule_btn.clicked.connect(self._on_new_schedule)
        header_layout.addWidget(self._new_schedule_btn)

        main_layout.addLayout(header_layout)

        # Schedule table
        table_card = CardWidget()
        table_layout = QVBoxLayout()

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Nombre",
            "Dispositivo",
            "Días",
            "Horario",
            "Activo",
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

        table_layout.addWidget(self._table)
        table_card.content_layout().addLayout(table_layout)
        main_layout.addWidget(table_card, 1)

    def _connect_signals(self):
        self._store.schedules_updated.connect(self._update_table)

    def _update_table(self, schedules=None):
        if schedules is None:
            schedules = self._store.schedules

        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        for schedule in schedules:
            self._add_schedule_row(schedule)

        self._table.setSortingEnabled(True)

    def _add_schedule_row(self, schedule):
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Name
        name_item = QTableWidgetItem(schedule.name)
        name_item.setData(Qt.UserRole, schedule.id)
        self._table.setItem(row, 0, name_item)

        # Device name
        device_name = schedule.device_name or "Dispositivo desconocido"
        device = self._store.get_device_by_mac(schedule.mac)
        if device:
            device_name = device.display_name
        self._table.setItem(row, 1, QTableWidgetItem(device_name))

        # Days
        days_item = QTableWidgetItem(schedule.weekdays_display)
        self._table.setItem(row, 2, days_item)

        # Time range
        time_item = QTableWidgetItem(schedule.time_range_display)
        self._table.setItem(row, 3, time_item)

        # Enabled checkbox
        enabled_widget = self._create_enabled_widget(schedule)
        self._table.setCellWidget(row, 4, enabled_widget)

        # Actions
        actions_widget = self._create_actions_widget(schedule)
        self._table.setCellWidget(row, 5, actions_widget)

    def _create_enabled_widget(self, schedule):
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QCheckBox

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        checkbox = QCheckBox()
        checkbox.setChecked(schedule.enabled)
        checkbox.stateChanged.connect(
            lambda state: self._on_toggle_enabled(schedule, state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(checkbox)

        return widget

    def _create_actions_widget(self, schedule):
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        edit_btn = QPushButton("Editar")
        edit_btn.setObjectName("secondary")
        edit_btn.setFixedWidth(55)
        edit_btn.clicked.connect(lambda: self._on_edit_schedule(schedule))
        layout.addWidget(edit_btn)

        delete_btn = QPushButton("Eliminar")
        delete_btn.setObjectName("danger")
        delete_btn.setFixedWidth(65)
        delete_btn.clicked.connect(lambda: self._on_delete_schedule(schedule))
        layout.addWidget(delete_btn)

        return widget

    def _on_new_schedule(self):
        from app.ui.dialogs.schedule_dialog import ScheduleDialog

        dialog = ScheduleDialog(self._store, self._router_client, parent=self)
        dialog.exec()
        self._refresh_schedules()

    def _on_edit_schedule(self, schedule):
        from app.ui.dialogs.schedule_dialog import ScheduleDialog

        dialog = ScheduleDialog(
            self._store,
            self._router_client,
            parent=self,
            existing_schedule=schedule,
        )
        dialog.exec()
        self._refresh_schedules()

    def _on_delete_schedule(self, schedule):
        from app.ui.dialogs.confirm_dialog import ConfirmDialog
        from app.utils.threading import WorkerThread

        dialog = ConfirmDialog(
            "Eliminar horario",
            f"¿Eliminar el horario '{schedule.name}'?",
            danger=True,
        )

        if dialog.exec():
            def delete():
                return self._router_client.delete_schedule(schedule.id)

            def on_result(success):
                if success:
                    self._store.remove_schedule(schedule.id)

            def on_error(title, msg):
                self._store.emit_error(title, msg)

            thread = WorkerThread(delete)
            thread.result.connect(on_result)
            thread.error.connect(on_error)
            thread.start()

    def _on_toggle_enabled(self, schedule, enabled):
        from app.utils.threading import WorkerThread

        def update():
            return self._router_client.update_schedule(schedule.id, enabled=enabled)

        def on_result(success):
            if success:
                schedule.enabled = enabled
                self._store.schedules_updated.emit(self._store.schedules)

        def on_error(title, msg):
            self._store.emit_error(title, msg)
            self._update_table()

        thread = WorkerThread(update)
        thread.result.connect(on_result)
        thread.error.connect(on_error)
        thread.start()

    def _refresh_schedules(self):
        from app.utils.threading import WorkerThread

        self._store.set_loading(True)

        def fetch_schedules():
            return self._router_client.get_schedules()

        def on_result(schedules_data):
            self._store.set_loading(False)
            from app.models.schedule import Schedule
            schedules = [Schedule.from_router_data(s) for s in schedules_data]
            self._store.set_schedules(schedules)

        def on_error(title, msg):
            self._store.set_loading(False)
            self._store.emit_error(title, msg)

        thread = WorkerThread(fetch_schedules)
        thread.result.connect(on_result)
        thread.error.connect(on_error)
        thread.start()
