"""Simple confirmation dialog."""

import logging

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class ConfirmDialog(QDialog):
    """Simple yes/no confirmation dialog."""

    def __init__(self, title: str, message: str, parent=None, danger: bool = False):
        super().__init__(parent)
        self._danger = danger
        self._setup_ui(title, message)

    def _setup_ui(self, title: str, message: str):
        self.setWindowTitle(title)
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )

        # Apply danger styling if needed
        if self._danger:
            yes_btn = buttons.button(QDialogButtonBox.StandardButton.Yes)
            if yes_btn:
                yes_btn.setObjectName("danger")
                yes_btn.setText("Confirmar")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
