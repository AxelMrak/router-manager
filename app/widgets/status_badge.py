"""Status badge widget — colored dot + text label."""

from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget
from PySide6.QtCore import Qt


class StatusBadge(QWidget):
    """Colored status dot with text label."""

    COLORS = {
        "online": "#16a34a",
        "offline": "#52525b",
        "blocked": "#dc2626",
        "warning": "#ca8a04",
    }

    def __init__(self, status: str = "offline", text: str = None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)

        self.dot = QLabel("\u25CF")
        self.dot.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel(text or status.capitalize())
        self.label.setStyleSheet("font-size: 12px;")

        layout.addWidget(self.dot)
        layout.addWidget(self.label)

        self.set_status(status, text)

    def set_status(self, status: str, text: str = None):
        color = self.COLORS.get(status, "#52525b")
        self.dot.setStyleSheet(f"color: {color}; font-size: 6px;")
        self.label.setText(text or status.capitalize())
