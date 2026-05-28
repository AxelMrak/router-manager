"""Settings page for application configuration."""

import logging

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QDialogButtonBox,
    QMessageBox,
)
from PySide6.QtCore import Qt

from app.widgets.card_widget import CardWidget

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Application settings page."""

    def __init__(self, store, router_client, settings):
        super().__init__()
        self._store = store
        self._router_client = router_client
        self._settings = settings
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Scroll area for settings
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(12)

        # Router Connection section
        connection_card = CardWidget()
        connection_form = QFormLayout()
        connection_form.setSpacing(10)
        connection_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        connection_label = QLabel("Conexión al router")
        connection_label.setObjectName("section-header")
        connection_form.addRow("", connection_label)

        # Router IP
        self._router_host = QLineEdit()
        self._router_host.setPlaceholderText("192.168.1.1")
        self._router_host.textChanged.connect(self._on_field_changed)
        connection_form.addRow("IP del router:", self._router_host)

        self._router_username = QLineEdit()
        self._router_username.setPlaceholderText("root")
        self._router_username.textChanged.connect(self._on_field_changed)
        connection_form.addRow("Usuario:", self._router_username)

        self._router_password = QLineEdit()
        self._router_password.setPlaceholderText("Contraseña")
        self._router_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._router_password.textChanged.connect(self._on_field_changed)
        connection_form.addRow("Contraseña:", self._router_password)

        # Connection buttons
        btn_layout = QHBoxLayout()
        self._test_btn = QPushButton("Probar conexión")
        self._test_btn.setObjectName("secondary")
        self._test_btn.clicked.connect(self._on_test_connection)
        btn_layout.addWidget(self._test_btn)

        self._save_btn = QPushButton("Guardar y conectar")
        self._save_btn.setObjectName("success")
        self._save_btn.clicked.connect(self._on_save_connect)
        btn_layout.addWidget(self._save_btn)

        connection_form.addRow("", btn_layout)

        connection_card.content_layout().addLayout(connection_form)
        scroll_layout.addWidget(connection_card)

        # Polling section
        polling_card = CardWidget()
        polling_form = QFormLayout()
        polling_form.setSpacing(10)
        polling_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        polling_label = QLabel("Actualización automática")
        polling_label.setObjectName("section-header")
        polling_form.addRow("", polling_label)

        self._polling_interval = QSpinBox()
        self._polling_interval.setMinimum(5)
        self._polling_interval.setMaximum(60)
        self._polling_interval.setSuffix(" seg")
        self._polling_interval.valueChanged.connect(self._on_field_changed)
        polling_form.addRow("Intervalo:", self._polling_interval)

        polling_card.content_layout().addLayout(polling_form)
        scroll_layout.addWidget(polling_card)

        # Appearance section
        appearance_card = CardWidget()
        appearance_form = QFormLayout()
        appearance_form.setSpacing(10)
        appearance_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        appearance_label = QLabel("Apariencia")
        appearance_label.setObjectName("section-header")
        appearance_form.addRow("", appearance_label)

        theme_label = QLabel("Oscuro")
        theme_label.setObjectName("subtitle")
        appearance_form.addRow("Tema:", theme_label)

        appearance_card.content_layout().addLayout(appearance_form)
        scroll_layout.addWidget(appearance_card)

        # About section
        about_card = CardWidget()
        about_form = QFormLayout()
        about_form.setSpacing(10)
        about_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        about_label = QLabel("Acerca de")
        about_label.setObjectName("section-header")
        about_form.addRow("", about_label)

        version_label = QLabel("Router Manager v1.0.0")
        version_label.setObjectName("subtitle")
        about_form.addRow("Versión:", version_label)

        credits_label = QLabel("Aplicación de escritorio para gestionar el acceso a internet de tu router.")
        credits_label.setObjectName("subtitle")
        credits_label.setWordWrap(True)
        about_form.addRow("", credits_label)

        about_card.content_layout().addLayout(about_form)
        scroll_layout.addWidget(about_card)

        scroll_layout.addStretch()
        main_layout.addLayout(scroll_layout, 1)

    def _load_settings(self):
        self._router_host.setText(self._settings.get("router_host", "192.168.1.1"))
        self._router_username.setText(self._settings.get("router_username", "root"))
        self._router_password.setText(self._settings.get("router_password", ""))
        self._polling_interval.setValue(self._settings.get("polling_interval", 10))

    def _on_field_changed(self):
        self._save_btn.setEnabled(True)

    def _on_test_connection(self):
        from app.utils.threading import WorkerThread

        host = self._router_host.text().strip()
        if not host:
            self._store.emit_error("Error de conexión", "Ingresá una dirección IP del router.")
            return

        self._test_btn.setEnabled(False)
        self._test_btn.setText("Probando...")

        def test():
            original_host = self._router_client.host
            original_user = self._router_client.username
            original_pass = self._router_client.password

            self._router_client.host = host
            self._router_client.username = self._router_username.text().strip()
            self._router_client.password = self._router_password.text()
            self._router_client.base_url = f"http://{host}/ubus"

            try:
                result = self._router_client.test_connection()
                if result:
                    self._router_client.login()
                    return True
                return False
            finally:
                self._router_client.host = original_host
                self._router_client.username = original_user
                self._router_client.password = original_pass
                self._router_client.base_url = f"http://{original_host}/ubus"

        def on_result(success):
            self._test_btn.setEnabled(True)
            self._test_btn.setText("Probar conexión")

            if success:
                QMessageBox.information(self, "Conexión exitosa", "¡Conexión al router establecida!")
            else:
                self._store.emit_error("Conexión fallida", "No se pudo conectar al router. Verificá la configuración.")

        def on_error(title, msg):
            self._test_btn.setEnabled(True)
            self._test_btn.setText("Probar conexión")
            self._store.emit_error(title, msg)

        thread = WorkerThread(test)
        thread.result.connect(on_result)
        thread.error.connect(on_error)
        thread.start()
        # Keep reference to prevent GC while thread is running
        self._test_thread = thread

    def _on_save_connect(self):
        from app.utils.threading import WorkerThread

        host = self._router_host.text().strip()
        username = self._router_username.text().strip()
        password = self._router_password.text()

        if not host:
            self._store.emit_error("Error de validación", "Ingresá una dirección IP del router.")
            return

        self._settings.set("router_host", host)
        self._settings.set("router_username", username)
        self._settings.set("router_password", password)
        self._settings.set("polling_interval", self._polling_interval.value())

        self._router_client.host = host
        self._router_client.username = username
        self._router_client.password = password
        self._router_client.base_url = f"http://{host}/ubus"

        self._save_btn.setEnabled(False)

        self._store.set_loading(True)

        def connect():
            return self._router_client.login()

        def on_result(success):
            self._store.set_loading(False)
            if success:
                self._store.set_connected(True)
                QMessageBox.information(self, "Conectado", "¡Conexión al router establecida!")
            else:
                self._store.emit_error("Conexión fallida", "No se pudo conectar al router.")

        def on_error(title, msg):
            self._store.set_loading(False)
            self._store.emit_error(title, msg)

        thread = WorkerThread(connect)
        thread.result.connect(on_result)
        thread.error.connect(on_error)
        thread.start()
        # Keep reference to prevent GC while thread is running
        self._save_thread = thread
