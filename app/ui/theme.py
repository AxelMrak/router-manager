"""Utilitarian dark theme for Router Manager.

Design language: industrial/tool-grade interface inspired by pfSense and UniFi.
No decorative elements. No rounded corners beyond 4px. No neon accents.
Typography-driven hierarchy with restrained color use.
"""

DARK_THEME = """
/* === BASE === */
QWidget {
    background-color: #0c0c0f;
    color: #e4e4e7;
    font-family: ".AppleSystemUIFont", "SF Pro Text", "system", sans-serif;
    font-size: 13px;
    line-height: 1.4;
}

QMainWindow {
    background-color: #0c0c0f;
}

/* === SIDEBAR === */
#sidebar {
    background-color: #151518;
    border-right: 1px solid #2a2a2f;
    min-width: 200px;
    max-width: 200px;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #71717a;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 10px 16px 10px 13px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    margin: 0;
}

#sidebar QPushButton:hover {
    color: #e4e4e7;
    background-color: #1c1c20;
}

#sidebar QPushButton:checked,
#sidebar QPushButton[active="true"] {
    color: #e4e4e7;
    border-left: 3px solid #1e40af;
    background-color: #1c1c20;
    font-weight: 600;
}

/* === TOPBAR === */
#topbar {
    background-color: #0c0c0f;
    border-bottom: 1px solid #2a2a2f;
    padding: 0 16px;
    min-height: 48px;
    max-height: 48px;
}

#topbar QLabel#title {
    font-size: 14px;
    font-weight: 600;
    color: #e4e4e7;
}

#topbar QLabel#connection-status {
    font-size: 12px;
    color: #71717a;
}

/* === CARDS === */
.card, QFrame[class="card"] {
    background-color: #151518;
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    padding: 16px;
}

/* === TABLES === */
QTableWidget, QTableView {
    background-color: #151518;
    alternate-background-color: #1c1c20;
    color: #e4e4e7;
    gridline-color: #1f1f24;
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    selection-background-color: #1c1c20;
    selection-color: #e4e4e7;
    font-size: 13px;
}

QTableWidget::item, QTableView::item {
    padding: 6px 12px;
    border-bottom: 1px solid #1f1f24;
}

QHeaderView::section {
    background-color: #0c0c0f;
    color: #71717a;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #2a2a2f;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* === BUTTONS === */
QPushButton {
    background-color: #1c1c20;
    color: #e4e4e7;
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #2a2a2f;
    border-color: #1e40af;
}

QPushButton:pressed {
    background-color: #151518;
}

QPushButton:disabled {
    background-color: #151518;
    color: #52525b;
    border-color: #1f1f24;
}

QPushButton#danger {
    background-color: #dc2626;
    border-color: #dc2626;
    color: #ffffff;
}

QPushButton#danger:hover {
    background-color: #b91c1c;
    border-color: #b91c1c;
}

QPushButton#success {
    background-color: #16a34a;
    border-color: #16a34a;
    color: #ffffff;
}

QPushButton#success:hover {
    background-color: #15803d;
    border-color: #15803d;
}

QPushButton#secondary {
    background-color: transparent;
    border: 1px solid #2a2a2f;
    color: #71717a;
}

QPushButton#secondary:hover {
    background-color: #1c1c20;
    color: #e4e4e7;
    border-color: #2a2a2f;
}

/* === INPUTS === */
QLineEdit, QSpinBox, QTimeEdit, QComboBox {
    background-color: #1c1c20;
    color: #e4e4e7;
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
}

QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus, QComboBox:focus {
    border: 1px solid #1e40af;
}

QComboBox {
    padding-right: 28px;
    min-height: 20px;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
    subcontrol-origin: padding;
    subcontrol-position: right;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #71717a;
    margin-right: 8px;
}

QComboBox:hover::down-arrow {
    border-top-color: #e4e4e7;
}

QComboBox QAbstractItemView {
    background-color: #151518;
    color: #e4e4e7;
    selection-background-color: #1e40af;
    selection-color: #ffffff;
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    padding: 6px 12px;
    min-height: 24px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #1c1c20;
}

/* === CHECKBOXES === */
QCheckBox {
    spacing: 8px;
    color: #e4e4e7;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #2a2a2f;
    background-color: #1c1c20;
}

QCheckBox::indicator:checked {
    background-color: #1e40af;
    border-color: #1e40af;
}

/* === SCROLLBARS === */
QScrollBar:vertical {
    background-color: #0c0c0f;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background-color: #2a2a2f;
    border-radius: 3px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #1e40af;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0c0c0f;
    height: 6px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal {
    background-color: #2a2a2f;
    border-radius: 3px;
    min-width: 30px;
}

/* === STATUS BAR === */
QStatusBar {
    background-color: #151518;
    color: #71717a;
    border-top: 1px solid #2a2a2f;
    padding: 4px 16px;
    font-size: 12px;
}

/* === TABS === */
QTabWidget::pane {
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    background-color: #151518;
}

QTabBar::tab {
    background-color: #0c0c0f;
    color: #71717a;
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 4px;
    font-size: 13px;
}

QTabBar::tab:selected {
    color: #e4e4e7;
    border-bottom: 2px solid #1e40af;
}

QTabBar::tab:hover {
    color: #e4e4e7;
}

/* === TOOLTIPS === */
QToolTip {
    background-color: #151518;
    color: #e4e4e7;
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}

/* === PROGRESS BAR === */
QProgressBar {
    background-color: #1c1c20;
    border: 1px solid #2a2a2f;
    border-radius: 2px;
    text-align: center;
    color: #e4e4e7;
    height: 4px;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #1e40af;
    border-radius: 1px;
}

/* === GROUP BOX === */
QGroupBox {
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    color: #71717a;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #71717a;
}

/* === SPINBOX === */
QSpinBox {
    padding-right: 24px;
    min-height: 20px;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: transparent;
    border: none;
    width: 20px;
    subcontrol-origin: border;
    subcontrol-position: right;
}

QSpinBox::up-button {
    subcontrol-position: top right;
}

QSpinBox::down-button {
    subcontrol-position: bottom right;
}

QSpinBox::up-arrow {
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-bottom: 4px solid #71717a;
    margin-bottom: 2px;
}

QSpinBox::down-arrow {
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid #71717a;
    margin-top: 2px;
}

QSpinBox::up-arrow:hover {
    border-bottom-color: #e4e4e7;
}

QSpinBox::down-arrow:hover {
    border-top-color: #e4e4e7;
}

/* === SPLITTER === */
QSplitter::handle {
    background-color: #2a2a2f;
}

/* === MENU === */
QMenu {
    background-color: #151518;
    border: 1px solid #2a2a2f;
    border-radius: 4px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px;
    border-radius: 2px;
}

QMenu::item:selected {
    background-color: #1c1c20;
}

/* === DIALOG === */
QDialog {
    background-color: #0c0c0f;
}

/* === LABELS === */
QLabel#subtitle {
    color: #71717a;
    font-size: 12px;
}

QLabel#stat-value {
    font-size: 24px;
    font-weight: 600;
    color: #e4e4e7;
    font-family: "Menlo", "Consolas", monospace;
}

QLabel#stat-label {
    font-size: 11px;
    color: #71717a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 500;
}

QLabel#section-header {
    font-size: 13px;
    font-weight: 600;
    color: #71717a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel#page-title {
    font-size: 15px;
    font-weight: 600;
    color: #e4e4e7;
}

/* === MONOSPACE DATA === */
QLabel#monospace {
    font-family: "Menlo", "Consolas", monospace;
    font-size: 12px;
    color: #a1a1aa;
}
"""

def apply_theme(app):
    """Apply the dark theme to a QApplication."""
    app.setStyleSheet(DARK_THEME)
