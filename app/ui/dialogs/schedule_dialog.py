"""Schedule dialog for creating/editing schedules from the Schedules page."""

import logging

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTimeEdit,
    QCheckBox,
    QComboBox,
    QPushButton,
    QFormLayout,
    QDialogButtonBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTime

from app.models.schedule import WEEKDAY_NAMES

logger = logging.getLogger(__name__)


class ScheduleDialog(QDialog):
    """Dialog for creating or editing a schedule (device-agnostic)."""

    def __init__(self, store, router_client, parent=None, existing_schedule=None):
        super().__init__(parent)
        self._store = store
        self._router_client = router_client
        self._existing_schedule = existing_schedule
        self._weekday_checkboxes = []
        self._setup_ui()

        if existing_schedule:
            self._populate_existing_schedule()
        else:
            self._select_first_device()

    def _setup_ui(self):
        self.setWindowTitle("Nuevo horario" if not self._existing_schedule else "Editar horario")
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)

        # Device selector
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._device_combo = QComboBox()
        self._device_combo.setMinimumWidth(250)
        form_layout.addRow("Dispositivo:", self._device_combo)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Ej: Hora de tarea")
        form_layout.addRow("Nombre:", self._name_input)

        main_layout.addLayout(form_layout)

        # Weekday selection
        weekdays_label = QLabel("Días:")
        main_layout.addWidget(weekdays_label)

        weekdays_layout = QHBoxLayout()
        weekdays_layout.setSpacing(8)

        for i, day_name in enumerate(WEEKDAY_NAMES):
            checkbox = QCheckBox(day_name[:3])  # Mon, Tue, etc.
            checkbox.setChecked(True)
            self._weekday_checkboxes.append((i, checkbox))
            weekdays_layout.addWidget(checkbox)

        main_layout.addLayout(weekdays_layout)

        # Time selection
        time_layout = QHBoxLayout()
        time_layout.setSpacing(16)

        start_label = QLabel("Inicio:")
        self._start_time = QTimeEdit()
        self._start_time.setDisplayFormat("HH:mm")
        self._start_time.setTime(QTime(8, 0))
        time_layout.addWidget(start_label)
        time_layout.addWidget(self._start_time)

        end_label = QLabel("Fin:")
        self._end_time = QTimeEdit()
        self._end_time.setDisplayFormat("HH:mm")
        self._end_time.setTime(QTime(18, 0))
        time_layout.addWidget(end_label)
        time_layout.addWidget(self._end_time)

        main_layout.addLayout(time_layout)

        # Enabled checkbox
        self._enabled_checkbox = QCheckBox("Activado")
        self._enabled_checkbox.setChecked(True)
        main_layout.addWidget(self._enabled_checkbox)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def _populate_devices(self):
        self._device_combo.clear()
        for device in self._store.devices:
            self._device_combo.addItem(
                f"{device.display_name} ({device.ip})",
                device.mac,
            )

    def _select_first_device(self):
        self._populate_devices()
        if self._device_combo.count() > 0:
            self._device_combo.setCurrentIndex(0)

    def _populate_existing_schedule(self):
        self._populate_devices()

        # Select the correct device
        index = self._device_combo.findData(self._existing_schedule.mac)
        if index >= 0:
            self._device_combo.setCurrentIndex(index)

        self._name_input.setText(self._existing_schedule.name)

        # Set weekdays
        for i, checkbox in self._weekday_checkboxes:
            checkbox.setChecked(i in self._existing_schedule.weekdays)

        # Set times
        start_parts = self._existing_schedule.start_time.split(":")
        if len(start_parts) == 2:
            self._start_time.setTime(QTime(int(start_parts[0]), int(start_parts[1])))

        end_parts = self._existing_schedule.end_time.split(":")
        if len(end_parts) == 2:
            self._end_time.setTime(QTime(int(end_parts[0]), int(end_parts[1])))

        self._enabled_checkbox.setChecked(self._existing_schedule.enabled)

    def _validate(self):
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error de validación", "Ingresá un nombre para el horario.")
            return False

        if self._device_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Error de validación", "Seleccioná un dispositivo.")
            return False

        selected_weekdays = [i for i, cb in self._weekday_checkboxes if cb.isChecked()]
        if not selected_weekdays:
            QMessageBox.warning(self, "Error de validación", "Seleccioná al menos un día.")
            return False

        start_time = self._start_time.time()
        end_time = self._end_time.time()

        if start_time >= end_time:
            QMessageBox.warning(
                self,
                "Error de validación",
                "La hora de fin debe ser posterior a la de inicio.",
            )
            return False

        return True

    def _on_accept(self):
        if not self._validate():
            return

        from app.utils.threading import WorkerThread

        name = self._name_input.text().strip()
        mac = self._device_combo.currentData()
        weekdays = [i for i, cb in self._weekday_checkboxes if cb.isChecked()]
        start_time = self._start_time.time().toString("HH:mm")
        end_time = self._end_time.time().toString("HH:mm")
        enabled = self._enabled_checkbox.isChecked()

        self._store.set_loading(True)
        self.setEnabled(False)

        if self._existing_schedule:
            # Update existing schedule
            def update():
                return self._router_client.update_schedule(
                    self._existing_schedule.id,
                    name=name,
                    mac=mac,
                    weekdays=weekdays,
                    start_time=start_time,
                    end_time=end_time,
                    enabled=enabled,
                )

            def on_result(success):
                self._store.set_loading(False)
                self.setEnabled(True)
                if success:
                    # Refresh schedules
                    self._refresh_schedules()
                    self.accept()
                else:
                    self._store.emit_error("Error", "No se pudo actualizar el horario.")

            def on_error(title, msg):
                self._store.set_loading(False)
                self.setEnabled(True)
                self._store.emit_error(title, msg)

            thread = WorkerThread(update)
            thread.result.connect(on_result)
            thread.error.connect(on_error)
            thread.start()
        else:
            # Create new schedule
            def create():
                return self._router_client.create_schedule(
                    name=name,
                    mac=mac,
                    weekdays=weekdays,
                    start_time=start_time,
                    end_time=end_time,
                    enabled=enabled,
                )

            def on_result(result):
                self._store.set_loading(False)
                self.setEnabled(True)
                if result:
                    from app.models.schedule import Schedule
                    schedule = Schedule.from_router_data(result)
                    self._store.add_schedule(schedule)
                    self.accept()
                else:
                    self._store.emit_error("Error", "No se pudo crear el horario.")

            def on_error(title, msg):
                self._store.set_loading(False)
                self.setEnabled(True)
                self._store.emit_error(title, msg)

            thread = WorkerThread(create)
            thread.result.connect(on_result)
            thread.error.connect(on_error)
            thread.start()

    def _refresh_schedules(self):
        from app.utils.threading import WorkerThread

        def fetch_schedules():
            return self._router_client.get_schedules()

        def on_result(schedules_data):
            from app.models.schedule import Schedule
            schedules = [Schedule.from_router_data(s) for s in schedules_data]
            self._store.set_schedules(schedules)

        def on_error(title, msg):
            pass  # Silent fail for refresh

        thread = WorkerThread(fetch_schedules)
        thread.result.connect(on_result)
        thread.error.connect(on_error)
        thread.start()
