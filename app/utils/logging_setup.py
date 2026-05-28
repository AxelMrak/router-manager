"""Logging configuration with file output and crash handling."""

import logging
import logging.handlers
import sys
import traceback
from datetime import datetime
from pathlib import Path


def get_log_dir() -> Path:
    """Return log directory next to the executable/main script."""
    exe_path = Path(sys.argv[0]).resolve()
    log_dir = exe_path.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging() -> logging.Logger:
    """Configure file + console logging with rotation.

    Returns the root logger.
    """
    log_dir = get_log_dir()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"router-manager-{timestamp}.log"

    # Clean up logs older than 7 days
    _cleanup_old_logs(log_dir, days=7)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # File handler with rotation (5 MB per file, keep 3)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # Console handler (only INFO and above)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console_format = logging.Formatter("%(levelname)s: %(message)s")
    console.setFormatter(console_format)
    root_logger.addHandler(console)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized. Log file: %s", log_file)
    return root_logger


def _cleanup_old_logs(log_dir: Path, days: int) -> None:
    """Remove log files older than *days*."""
    cutoff = datetime.now().timestamp() - days * 86400
    for f in log_dir.glob("router-manager-*.log"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
        except OSError:
            pass


QT_MESSAGE_LEVELS = {
    0: "DEBUG",    # QtDebugMsg
    1: "WARNING",  # QtWarningMsg
    2: "CRITICAL", # QtCriticalMsg
    3: "FATAL",    # QtFatalMsg
    4: "INFO",     # QtInfoMsg
}


def qt_message_handler(mode: int, context, message: str) -> None:
    """Route Qt messages through Python logging.

    Suppress harmless warnings (e.g. font fallback, style hints)
    and log the rest.
    """
    level = QT_MESSAGE_LEVELS.get(mode, "INFO")
    logger = logging.getLogger("qt")

    # Suppress known harmless Qt warnings
    if "Populating font family aliases" in message:
        return
    if "QFont::" in message and "fallback" in message.lower():
        return
    if "QThread: Destroyed while thread" in message:
        # Log as warning, not error — this is non-fatal
        logger.warning("Qt: %s", message)
        return

    if level in ("WARNING", "CRITICAL", "FATAL"):
        logger.warning("Qt [%s]: %s", level, message)
    elif level == "DEBUG":
        logger.debug("Qt: %s", message)
    else:
        logger.info("Qt: %s", message)


class CrashHandler:
    """Global exception handler that logs and shows an error dialog.

    Install at startup to prevent silent crashes.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger("crash")

    def handle_exception(self, exc_type, exc_value, exc_tb) -> None:
        """Handle uncaught Python exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Let Ctrl+C pass through
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        # Format traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        tb_text = "".join(tb_lines)

        self._logger.critical("Unhandled exception:\n%s", tb_text)

        # Try to show a dialog if QApplication is running
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance()
            if app is not None:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error inesperado")
                msg_box.setText(
                    "La aplicación encontró un error inesperado y debe cerrarse."
                )
                from pathlib import Path
                log_path = Path(sys.argv[0]).resolve().parent / "logs"
                msg_box.setInformativeText(
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"Se guardó un registro en: {log_path}"
                )
                msg_box.setDetailedText(tb_text)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
        except Exception:
            self._logger.exception("Failed to show error dialog")

        # Call original hook
        sys.__excepthook__(exc_type, exc_value, exc_tb)


def install_crash_handler() -> None:
    """Install the global exception handler."""
    handler = CrashHandler()
    sys.excepthook = handler.handle_exception
