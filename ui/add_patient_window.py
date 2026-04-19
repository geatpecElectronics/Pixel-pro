# =============================================================
#  ui/add_patient_window.py — Matches original exactly
#  Dark red toolbar, white bg, #8B0000 section headers,
#  #E0E0E0 rounded input fields, 3 bottom buttons
# =============================================================

import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QDateEdit, QTextEdit,
    QFrame, QScrollArea, QGridLayout, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from models.database import get_session, Patient
from utils.session import UserSession

ASSETS   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
RED      = "#b01c20"
DARK_RED = "#8B0000"
FIELD_BG = "#E0E0E0"

TOOLBAR_STYLE = f"""
    QFrame {{ background: {RED}; }}
    QPushButton {{ background:transparent; color:white; border:none;
                   padding:8px 12px; border-radius:4px; font-size:13px; }}
    QPushButton:hover {{ background: rgba(255,255,255,0.18); }}
    QLabel {{ color:white; background:transparent; font-size:13px; }}
"""

FIELD_STYLE = f"""
    QLineEdit, QTextEdit, QDateEdit {{
        background: {FIELD_BG}; border: none; border-radius: 10px;
        padding: 8px 14px; font-size: 13px; color: #333;
    }}
    QComboBox {{
        background: {FIELD_BG}; border: none; border-radius: 10px;
        padding: 8px 14px; font-size: 13px; color: #333;
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox QAbstractItemView {{
        background: white; color: {RED};
        selection-background-color: {RED}; selection-color: white;
    }}
"""

LABEL_STYLE = "color: #4A4A4A; font-size: 13px; background: transparent;"
SECTION_HEADER = f"""
    QFrame {{ background: {DARK_RED}; border-radius: 4px; }}
    QLabel {{ color: white; font-size: 13px; font-weight: bold;
              background: transparent; padding: 8px 14px; }}
"""
BOTTOM_BTN = f"""
    QPushButton {{
        background: {DARK_RED}; color: white; border: none;
        font-size: 14px; font-weight: bold; border-radius: 0px;
    }}
    QPushButton:hover {{ background: {RED}; }}
"""


class AddPatientWindow(QMainWindow):
    def __init__(self, parent_window=None, edit_patient_id=None):
        super().__init__()
        self.parent_window   = parent_window
        self.edit_patient_id = edit_patient_id
        self.setWindowTitle("Patient Details")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("QMainWindow { background: white; font-family: 'Segoe UI'; }")
        self._build_ui()
        if edit_patient_id:
            self._load_patient(edit_patient_id)

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
        for icon in ["📄", "📷", "🖼"]:
            b = QPushButton(icon)
            b.setFixedSize(44, 44)
            t.addWidget(b)
        t.addStretch()
        user_lbl = QLabel(f"👤  {UserSession.username()}")
        t.addWidget(user_lbl)
        t.addSpacing(8)
        logout_btn = QPushButton("⏻")
        logout_btn.setFixedSize(36, 36)
        logout_btn.clicked.connect(self._logout)
        t.addWidget(logout_btn)
        root.addWidget(toolbar)

        # ── Scrollable form ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:white; }")

        form_widget = QWidget()
        form_widget.setStyleSheet(f"background:white; {FIELD_STYLE}")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(20, 20, 20, 10)
        form_layout.setSpacing(14)

        # ── BASIC INFORMATION header ──────────────────────────
        form_layout.addWidget(self._section_header("Basic Information"))

        basic_grid = QGridLayout()
        basic_grid.setSpacing(14)
        basic_grid.setContentsMargins(0, 8, 0, 8)

        self.first_name = self._field("Enter First Name")
        self.last_name  = self._field("Enter Last Name")
        self.gender     = self._combo(["Select Gender", "Male", "Female", "Other"])
        self.dob        = self._date_field()
        self.contact    = self._field("Enter Number")
        self.email      = self._field("Enter Email ID")
        self.blood_group = self._combo(["Select Blood Group","A+","A-","B+","B-","AB+","AB-","O+","O-"])
        self.address    = self._field("Enter Address")

        # Row 0: First Name | Last Name
        basic_grid.addWidget(self._label("First Name"),   0, 0)
        basic_grid.addWidget(self._label("Last Name"),    0, 1)
        basic_grid.addWidget(self.first_name,             1, 0)
        basic_grid.addWidget(self.last_name,              1, 1)
        # Row 2: Gender | DOB
        basic_grid.addWidget(self._label("Gender"),       2, 0)
        basic_grid.addWidget(self._label("Date of Birth"),2, 1)
        basic_grid.addWidget(self.gender,                 3, 0)
        basic_grid.addWidget(self.dob,                    3, 1)
        # Row 4: Contact | Email
        basic_grid.addWidget(self._label("Contact Number"),4, 0)
        basic_grid.addWidget(self._label("Email ID"),      4, 1)
        basic_grid.addWidget(self.contact,                 5, 0)
        basic_grid.addWidget(self.email,                   5, 1)
        # Row 6: Blood Group | Address
        basic_grid.addWidget(self._label("Blood Group"),  6, 0)
        basic_grid.addWidget(self._label("Address"),      6, 1)
        basic_grid.addWidget(self.blood_group,            7, 0)
        basic_grid.addWidget(self.address,                7, 1)

        form_layout.addLayout(basic_grid)

        # ── MEDICAL INFORMATION header ────────────────────────
        form_layout.addWidget(self._section_header("Medical Information"))

        med_grid = QGridLayout()
        med_grid.setSpacing(14)
        med_grid.setContentsMargins(0, 8, 0, 8)

        self.current_med  = self._field("Enter Current Medications")
        med_grid.addWidget(self._label("Current Medications"), 0, 0, 1, 2)
        med_grid.addWidget(self.current_med,                   1, 0, 1, 2)

        self.existing_med = self._field("Enter Existing Medical")
        self.past_history = self._field("Enter Past Medical History")
        med_grid.addWidget(self._label("Existing Medical"),    2, 0)
        med_grid.addWidget(self._label("Past Medical History"),2, 1)
        med_grid.addWidget(self.existing_med,                  3, 0)
        med_grid.addWidget(self.past_history,                  3, 1)

        self.allergies = self._field("Enter Allergies")
        self.ref_doc   = self._field("Enter Referring Doctor")
        med_grid.addWidget(self._label("Allergies"),                       4, 0)
        med_grid.addWidget(self._label("Primary Physician / Referring Doctor"), 4, 1)
        med_grid.addWidget(self.allergies,                                 5, 0)
        med_grid.addWidget(self.ref_doc,                                   5, 1)

        form_layout.addLayout(med_grid)

        # Images section
        img_lbl = QLabel("Images")
        img_lbl.setStyleSheet(LABEL_STYLE + "font-size:14px; font-weight:bold;")
        form_layout.addWidget(img_lbl)

        img_row = QHBoxLayout()
        img_row.setSpacing(10)
        for _ in range(4):
            box = QFrame()
            box.setFixedSize(90, 90)
            box.setStyleSheet(f"""
                QFrame {{ background:{FIELD_BG}; border-radius:8px; }}
            """)
            plus = QLabel("+\nAdd Image")
            plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
            plus.setStyleSheet("color:#888; font-size:12px; background:transparent;")
            l = QVBoxLayout(box)
            l.addWidget(plus)
            img_row.addWidget(box)
        img_row.addStretch()
        form_layout.addLayout(img_row)
        form_layout.addStretch()

        scroll.setWidget(form_widget)
        root.addWidget(scroll)

        # ── Bottom 3 buttons ──────────────────────────────────
        btn_bar = QFrame()
        btn_bar.setFixedHeight(60)
        btn_bar.setStyleSheet("QFrame { background: white; border-top: 1px solid #ddd; }")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(0)

        exit_btn = QPushButton("Exit")
        exit_btn.setStyleSheet(BOTTOM_BTN)
        exit_btn.clicked.connect(self._go_back)

        report_btn = QPushButton("Report")
        report_btn.setStyleSheet(BOTTOM_BTN)

        save_btn = QPushButton("Save Patient Details+")
        save_btn.setStyleSheet(BOTTOM_BTN + f"QPushButton {{ background: {DARK_RED}; }}")
        save_btn.clicked.connect(self._save_patient)

        for b in [exit_btn, report_btn, save_btn]:
            b.setFixedHeight(60)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn_layout.addWidget(b)

        root.addWidget(btn_bar)

    # ── Helpers ───────────────────────────────────────────────
    def _section_header(self, text):
        frame = QFrame()
        frame.setFixedHeight(40)
        frame.setStyleSheet(SECTION_HEADER)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(text)
        layout.addWidget(lbl)
        return frame

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(LABEL_STYLE)
        return lbl

    def _field(self, placeholder):
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        f.setFixedHeight(42)
        f.setStyleSheet(f"""
            QLineEdit {{ background:{FIELD_BG}; border:none; border-radius:10px;
                         padding:0 14px; font-size:13px; color:#333; }}
        """)
        return f

    def _combo(self, items):
        cb = QComboBox()
        cb.addItems(items)
        cb.setFixedHeight(42)
        cb.setStyleSheet(f"""
            QComboBox {{ background:{FIELD_BG}; border:none; border-radius:10px;
                         padding:0 14px; font-size:13px; color:#333; }}
            QComboBox::drop-down {{ border:none; width:30px; }}
            QComboBox QAbstractItemView {{ background:white; color:{RED};
                selection-background-color:{RED}; selection-color:white; border:none; }}
        """)
        return cb

    def _date_field(self):
        d = QDateEdit()
        d.setCalendarPopup(True)
        d.setDate(QDate.currentDate())
        d.setFixedHeight(42)
        d.setDisplayFormat("dd/MM/yyyy")
        d.setStyleSheet(f"""
            QDateEdit {{ background:{FIELD_BG}; border:none; border-radius:10px;
                         padding:0 14px; font-size:13px; color:#333; }}
            QDateEdit::drop-down {{ border:none; }}
        """)
        return d

    def _save_patient(self):
        if not self.first_name.text().strip():
            QMessageBox.warning(self, "Validation", "Please enter First Name.")
            return
        if not self.last_name.text().strip():
            QMessageBox.warning(self, "Validation", "Please enter Last Name.")
            return
        if self.gender.currentIndex() == 0:
            QMessageBox.warning(self, "Validation", "Please select Gender.")
            return
        try:
            session = get_session()
            qd = self.dob.date()
            dob = datetime(qd.year(), qd.month(), qd.day())
            data = dict(
                first_name=self.first_name.text().strip(),
                last_name=self.last_name.text().strip(),
                gender=self.gender.currentText(),
                dob=dob,
                contact_number=self.contact.text().strip(),
                email_id=self.email.text().strip(),
                blood_group=self.blood_group.currentText() if self.blood_group.currentIndex() > 0 else "",
                address=self.address.text().strip(),
                ref_doc=self.ref_doc.text().strip(),
                current_medication=self.current_med.text().strip(),
                existing_medical=self.existing_med.text().strip(),
                past_medical_history=self.past_history.text().strip(),
                allergies=self.allergies.text().strip(),
                is_active=True, is_deleted=False,
            )
            if self.edit_patient_id:
                p = session.query(Patient).get(self.edit_patient_id)
                for k, v in data.items():
                    setattr(p, k, v)
            else:
                p = Patient(**data)
                session.add(p)
            session.commit()
            session.close()
            QMessageBox.information(self, "Success", "Patient saved successfully!")
            self._go_back()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _load_patient(self, pid):
        session = get_session()
        p = session.query(Patient).get(pid)
        session.close()
        if not p: return
        self.first_name.setText(p.first_name or "")
        self.last_name.setText(p.last_name or "")
        idx = self.gender.findText(p.gender or "")
        if idx >= 0: self.gender.setCurrentIndex(idx)
        if p.dob: self.dob.setDate(QDate(p.dob.year, p.dob.month, p.dob.day))
        self.contact.setText(p.contact_number or "")
        self.email.setText(p.email_id or "")
        bg_idx = self.blood_group.findText(p.blood_group or "")
        if bg_idx >= 0: self.blood_group.setCurrentIndex(bg_idx)
        self.address.setText(p.address or "")
        self.ref_doc.setText(p.ref_doc or "")
        self.current_med.setText(p.current_medication or "")
        self.existing_med.setText(p.existing_medical or "")
        self.past_history.setText(p.past_medical_history or "")
        self.allergies.setText(p.allergies or "")

    def _go_back(self):
        if self.parent_window:
            self.parent_window.show()
            self.parent_window._load_patients()
        self.close()

    def _logout(self):
        UserSession.end()
        from ui.login_window import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()
