"""Video Platform Admin — entry point.

Launches the login dialog then the main window. All API calls run off the
GUI thread; technical errors are logged to a file and shown as friendly
Arabic messages (plan §29-32).
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from api_client import ApiClient
from config import AppConfig
from utils.logging_setup import log


def load_fonts(app: QApplication) -> None:
    """Bundle Tajawal so the UI looks identical on every machine.

    Qt fails to load font files from paths containing non-ASCII characters
    (e.g. an Arabic project folder), so we copy them to a temp ASCII-safe
    directory first and register from there.
    """
    import shutil
    import tempfile
    from pathlib import Path

    from PySide6.QtGui import QFontDatabase

    fonts_dir = Path(__file__).parent / "fonts"
    if not fonts_dir.exists():
        return

    target = Path(tempfile.gettempdir()) / "vpadmin_fonts"
    target.mkdir(parents=True, exist_ok=True)
    for ttf in fonts_dir.glob("*.ttf"):
        dest = target / ttf.name
        if not dest.exists() or dest.stat().st_size != ttf.stat().st_size:
            shutil.copy2(ttf, dest)
        QFontDatabase.addApplicationFont(str(dest))


def load_theme(app: QApplication) -> None:
    from pathlib import Path

    qss_path = Path(__file__).parent / "theme.qss"
    try:
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    except OSError:
        log.warning("theme.qss not found; using default styling")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("VideoPlatformAdmin")
    app.setLayoutDirection(Qt.RightToLeft)

    load_fonts(app)
    font = QFont("Tajawal", 10)
    font.setFamilies(["Tajawal", "Cairo", "Segoe UI"])
    app.setFont(font)
    load_theme(app)

    config = AppConfig.load()
    client = ApiClient(config)

    # Import here so logging/theme are ready first.
    from views.login import LoginDialog
    from views.main_window import MainWindow

    while True:
        login = LoginDialog(client, config)
        if login.exec() != login.DialogCode.Accepted:
            log.info("exit at login")
            return 0

        username = config.saved_username or "admin"
        # Prefer the username that actually logged in.
        if hasattr(login, "username"):
            typed = login.username.text().strip()
            if typed:
                username = typed

        try:
            window = MainWindow(client, config, username)
        except Exception:  # noqa: BLE001
            log.exception("failed to build main window")
            QMessageBox.critical(None, "خطأ", "تعذر تشغيل اللوحة. راجع ملف السجل.")
            return 1

        window.show()
        if app.exec() == 0:
            return 0
        # Session expired path would loop back to login in future versions.
        break

    return 0


if __name__ == "__main__":
    sys.exit(main())
