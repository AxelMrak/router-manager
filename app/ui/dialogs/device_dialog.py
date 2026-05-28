"""Device dialog for editing device details (alias/name)."""

import logging

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QLabel,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class DeviceDialog(QDialog):
    """Dialog for editing device details."""

    def __init__(self, device, parent=None):
        super().__init__(parent)
        self._device = device
        self._result_name = None
        self._result_is_guest = device.is_guest
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Editar dispositivo")
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)

        # Current device info
        info_layout = QFormLayout()
        info_layout.setSpacing(8)

        info_layout.addRow("Dirección MAC:", QLabel(self._device.mac))
        info_layout.addRow("Dirección IP:", QLabel(self._device.ip))

        if self._device.hostname:
            info_layout.addRow("Nombre de host:", QLabel(self._device.hostname))

        main_layout.addLayout(info_layout)

        # Alias input
        alias_layout = QFormLayout()
        alias_layout.setSpacing(8)

        self._alias_input = QLineEdit()
        self._alias_input.setPlaceholderText("Nombre personalizado...")
        self._alias_input.setText(
            self._device.display_name
            if self._device.display_name != self._device.hostname
            else ""
        )

        existing_alias = self._device.name if self._device.name != "Dispositivo desconocido" else ""
        if existing_alias:
            self._alias_input.setText(existing_alias)

        alias_layout.addRow("Nombre:", self._alias_input)
        main_layout.addLayout(alias_layout)

        # Guest checkbox
        self._guest_checkbox = QCheckBox("Marcar como dispositivo invitado")
        self._guest_checkbox.setChecked(self._device.is_guest)
        main_layout.addWidget(self._guest_checkbox)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def _on_accept(self):
        self._result_name = self._alias_input.text().strip()
        self._result_is_guest = self._guest_checkbox.isChecked()
        self.accept()

    def get_result(self):
        """Return tuple of (name, is_guest)."""
        return self._result_name, self._result_is_guest
