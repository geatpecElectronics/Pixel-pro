# =============================================================
#  ui/main_shell.py  —  Single QMainWindow for entire app
#  All pages are QWidgets on a QStackedWidget.
#  Call shell.navigate("page", kwarg=val) to switch pages.
# =============================================================
import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QStackedWidget, QVBoxLayout
from PyQt6.QtGui import QIcon

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# ── Page name constants (import these anywhere you need them) ──
PAGE_LOGIN    = "login"
PAGE_REGISTER = "register"
PAGE_DASH     = "dashboard"
PAGE_PATIENTS = "patients"
PAGE_VISITS   = "visits"
PAGE_CAMERA   = "camera"
PAGE_REPORT   = "report"
PAGE_PACS     = "pacs"

# Pages rebuilt fresh every navigation (hold state / bound to a PK)
_VOLATILE = {PAGE_PATIENTS, PAGE_VISITS, PAGE_CAMERA, PAGE_REPORT, PAGE_DASH}


class MainShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pixel Pro")
        ico = os.path.join(ASSETS, "logo.ico")
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))

        self._stack = QStackedWidget()
        self._cache = {}           # page_name -> QWidget

        central = QWidget()
        central.setStyleSheet("QWidget#shell_central { background: #F5F5F5; }")
        central.setObjectName("shell_central")
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._stack)
        self.setCentralWidget(central)

        self.navigate(PAGE_LOGIN)

    # ── Public ────────────────────────────────────────────────

    def navigate(self, page: str, **kwargs):
        """Build (or reuse) a page widget and switch to it."""
        if page in _VOLATILE:
            self._evict(page)

        if page not in self._cache:
            w = self._build(page, **kwargs)
            self._cache[page] = w
            self._stack.addWidget(w)

        self._resize_for(page)
        self._stack.setCurrentWidget(self._cache[page])

    # ── Private ───────────────────────────────────────────────

    def _evict(self, page: str):
        if page in self._cache:
            old = self._cache.pop(page)
            self._stack.removeWidget(old)
            old.deleteLater()

    def _build(self, page: str, **kwargs) -> QWidget:
        if page == PAGE_LOGIN:
            from ui.login_page import LoginPage
            return LoginPage(self)

        if page == PAGE_REGISTER:
            from ui.register_page import RegisterPage
            return RegisterPage(self)

        if page == PAGE_DASH:
            from ui.dashboard_window import DashboardPage
            return DashboardPage(self)

        if page == PAGE_PATIENTS:
            from ui.patient_manager import PatientManagerPage
            return PatientManagerPage(self,
                mode=kwargs.get("mode", "list"),
                patient_id=kwargs.get("patient_id"))

        if page == PAGE_VISITS:
            from ui.visit_manager import VisitManagerPage
            return VisitManagerPage(self,
                patient_id=kwargs.get("patient_id"),
                create_new=kwargs.get("create_new", False))

        if page == PAGE_CAMERA:
            from ui.camera_capture import CameraPage
            return CameraPage(self, visit_id_pk=kwargs.get("visit_id_pk"))

        if page == PAGE_REPORT:
            from ui.report_builder import ReportPage
            return ReportPage(self, visit_id_pk=kwargs.get("visit_id_pk"))

        if page == PAGE_PACS:
            from ui.pacs_manager import PACSPage
            return PACSPage(self)

        raise ValueError(f"Unknown page: {page!r}")

    def _resize_for(self, page: str):
        if page in (PAGE_LOGIN, PAGE_REGISTER):
            self.setFixedSize(920, 580)
        else:
            # Remove fixed constraint, ensure minimum size
            self.setMinimumSize(1200, 720)
            self.setMaximumSize(16_777_215, 16_777_215)
            if self.width() < 1200 or self.height() < 720:
                self.resize(1280, 800)
