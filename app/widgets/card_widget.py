"""Card container widget styled via theme."""

from PySide6.QtWidgets import QFrame, QVBoxLayout


class CardWidget(QFrame):
    """A styled card container. Styling comes from the theme .card class."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)

    def content_layout(self) -> QVBoxLayout:
        return self._layout
