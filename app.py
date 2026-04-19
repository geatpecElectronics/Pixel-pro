# =============================================================
#  app.py  —  Pixel Pro entry point
# =============================================================
import sys, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

# When frozen by PyInstaller, assets live next to the exe.
# When running from source, they're relative to this file.
if getattr(sys, "frozen", False):
    BASE_DIR   = os.path.dirname(sys.executable)
    ASSETS     = os.path.join(BASE_DIR, "assets")
else:
    BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
    ASSETS     = os.path.join(BASE_DIR, "assets")

# Database lives in %APPDATA%\Labomed\PixelPro\ so it:
#   - survives uninstall / reinstall
#   - works without admin rights on any Windows machine
#   - is separate from Program Files (which is read-only for users)
APP_DATA   = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Labomed", "PixelPro"
)
os.makedirs(APP_DATA, exist_ok=True)
os.environ["PIXELPRO_DATA_DIR"] = APP_DATA   # database.py reads this


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Pixel Pro")
    app.setOrganizationName("Labomed")

    # Force Fusion style + light palette so QMessageBox/QDialog always
    # render with black text on white, regardless of OS dark mode.
    from PyQt6.QtWidgets import QStyleFactory
    from PyQt6.QtGui import QPalette, QColor
    app.setStyle(QStyleFactory.create("Fusion"))
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor("#F5F5F5"))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor("#111111"))
    pal.setColor(QPalette.ColorRole.Base,            QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor("#F0F0F0"))
    pal.setColor(QPalette.ColorRole.Text,            QColor("#111111"))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor("#111111"))
    pal.setColor(QPalette.ColorRole.Button,          QColor("#E0E0E0"))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor("#B91C1C"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor("#111111"))
    app.setPalette(pal)

    icon_path = os.path.join(ASSETS, "logo.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from models.database import init_db
    init_db()

    from ui.main_shell import MainShell
    shell = MainShell()
    shell.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
