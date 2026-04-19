# =============================================================
#  ui/main_window.py  — Matches original Labomed GUI exactly
#  Dark red toolbar (#b01c20), white content, patient list rows
# =============================================================

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QFont, QPixmap, QColor

from models.database import get_session, Patient
from utils.session import UserSession

ASSETS  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
RED     = "#b01c20"
BG      = "#F5F5F5"

TOOLBAR_STYLE = f"""
    QFrame {{ background: {RED}; }}
    QPushButton {{
        background: transparent; color: white; border: none;
        padding: 8px 12px; border-radius: 4px; font-size: 13px;
    }}
    QPushButton:hover {{ background: rgba(255,255,255,0.18); }}
    QLabel {{ color: white; background: transparent; font-size: 13px; }}
"""


class PatientRow(QFrame):
    def __init__(self, patient, on_click):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background: white; border-bottom: 1px solid #DADADA; }
            QFrame:hover { background: #FFF5F5; }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._on_click = on_click
        self._pid = patient.id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Thumb placeholder
        thumb = QFrame()
        thumb.setFixedSize(50, 50)
        thumb.setStyleSheet("background: #E0E0E0; border-radius: 4px;")
        layout.addWidget(thumb)

        # Info
        info = QVBoxLayout()
        name_lbl = QLabel(f"Patient Name:  {patient.first_name or ''} {patient.last_name or ''}".strip())
        name_lbl.setStyleSheet("color: #222; font-size: 13px; font-weight: bold; background: transparent;")
        doc_lbl = QLabel(f"Doctor Name:  {patient.ref_doc or '—'}")
        doc_lbl.setStyleSheet("color: #555; font-size: 12px; background: transparent;")
        info.addWidget(name_lbl)
        info.addWidget(doc_lbl)
        layout.addLayout(info, stretch=1)

        # Meta
        meta = QVBoxLayout()
        dob_lbl = QLabel(f"DOB:  {patient.dob.strftime('%d %b %Y') if patient.dob else '—'}")
        dob_lbl.setStyleSheet("color: #555; font-size: 12px; background: transparent;")
        bg_lbl = QLabel(f"Blood Group:  {patient.blood_group or '—'}")
        bg_lbl.setStyleSheet("color: #555; font-size: 12px; background: transparent;")
        meta.addWidget(dob_lbl)
        meta.addWidget(bg_lbl)
        layout.addLayout(meta)

        # Camera button
        cam_btn = QPushButton("📷  Camera")
        cam_btn.setFixedSize(110, 34)
        cam_btn.setStyleSheet(f"""
            QPushButton {{ background: {RED}; color: white; border-radius: 5px;
                           font-size: 12px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background: #8C171A; }}
        """)
        cam_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cam_btn.clicked.connect(lambda: on_click("camera", patient.id))
        layout.addWidget(cam_btn)

        view_btn = QPushButton("📋  Report")
        view_btn.setFixedSize(100, 34)
        view_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {RED}; border: 1px solid {RED};
                           border-radius: 5px; font-size: 12px; font-weight: bold; }}
            QPushButton:hover {{ background: {RED}; color: white; }}
        """)
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.clicked.connect(lambda: on_click("report", patient.id))
        layout.addWidget(view_btn)

    def mousePressEvent(self, event):
        self._on_click("report", self._pid)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manage Patients")
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(f"QMainWindow {{ background: {BG}; font-family: 'Segoe UI'; }}")
        self._build_ui()
        self._load_patients()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ──────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(TOOLBAR_STYLE)
        t = QHBoxLayout(toolbar)
        t.setContentsMargins(14, 0, 14, 0)
        t.setSpacing(0)

        # Left icons (using text since we don't have icon files)
        add_btn = self._tbtn("🗂", "Add Patient")
        add_btn.clicked.connect(self._add_patient)
        t.addWidget(add_btn)

        save_btn = self._tbtn("💾", "Save")
        t.addWidget(save_btn)

        cam_btn = self._tbtn("📷", "Camera")
        cam_btn.clicked.connect(lambda: self._open_camera(None))
        t.addWidget(cam_btn)

        gallery_btn = self._tbtn("🖼", "Gallery")
        t.addWidget(gallery_btn)

        t.addStretch()

        # Date/Time
        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet("color:white; font-size:11px; background:transparent;")
        t.addWidget(self.date_lbl)
        t.addSpacing(20)

        # User
        user_lbl = QLabel(f"👤  {UserSession.username()}")
        user_lbl.setStyleSheet("color:white; font-size:13px; background:transparent;")
        t.addWidget(user_lbl)
        t.addSpacing(8)

        logout_btn = QPushButton("⏻")
        logout_btn.setFixedSize(36, 36)
        logout_btn.setToolTip("Logout")
        logout_btn.setStyleSheet("""
            QPushButton { background:transparent; color:white; border:none; font-size:18px; }
            QPushButton:hover { background: rgba(255,255,255,0.2); border-radius:4px; }
        """)
        logout_btn.clicked.connect(self._logout)
        t.addWidget(logout_btn)
        root.addWidget(toolbar)

        # ── Patient list ─────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #F5F5F5; }")

        self.list_widget = QWidget()
        self.list_widget.setStyleSheet("background: #F5F5F5;")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(20, 16, 20, 16)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()

        scroll.setWidget(self.list_widget)
        root.addWidget(scroll)

        # Clock
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _tbtn(self, icon, tooltip):
        btn = QPushButton(icon)
        btn.setFixedSize(44, 44)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:white; border:none; font-size:18px; }
            QPushButton:hover { background: rgba(255,255,255,0.18); border-radius:4px; }
        """)
        return btn

    def _tick(self):
        now = QDateTime.currentDateTime()
        self.date_lbl.setText(
            f"Date:  {now.toString('dd-MM-yyyy')}   |   Time:  {now.toString('hh:mm AP')}"
        )

    def _load_patients(self):
        # Clear existing rows
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            session = get_session()
            patients = session.query(Patient).filter_by(is_deleted=False).order_by(Patient.id.desc()).all()
            session.close()

            if not patients:
                empty = QLabel("No patients found. Click 🗂 to add a patient.")
                empty.setStyleSheet(f"color: {RED}; font-size: 14px; padding: 40px;")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.list_layout.insertWidget(0, empty)
            else:
                for i, p in enumerate(patients):
                    row = PatientRow(p, self._row_action)
                    self.list_layout.insertWidget(i, row)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _row_action(self, action, patient_id):
        if action == "camera":
            self._open_camera(patient_id)
        elif action == "report":
            self._view_report(patient_id)

    def _add_patient(self):
        from ui.add_patient_window import AddPatientWindow
        self.add_win = AddPatientWindow(parent_window=self)
        self.add_win.show()
        self.hide()

    def _view_report(self, pid):
        from ui.patient_report_window import PatientReportWindow
        session = get_session()
        p = session.query(Patient).get(pid)
        session.close()
        if p:
            self.rpt = PatientReportWindow(p)
            self.rpt.show()

    def _open_camera(self, pid):
        from ui.camera_window import CameraWindow
        self.cam = CameraWindow(patient_id=pid)
        self.cam.show()
        self.hide()

    def _logout(self):
        UserSession.end()
        from ui.login_window import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()
