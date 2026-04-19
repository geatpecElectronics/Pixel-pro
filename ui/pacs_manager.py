# =============================================================
#  ui/pacs_manager.py  — PACS / DICOM page (QWidget)
# =============================================================
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QTextEdit,
    QMessageBox, QProgressBar, QSpinBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ui._styles import RED, DARK_RED, BG, FIELD
from models.database import get_session, PACSConfig
from utils.session import UserSession


class PACSPage(QWidget):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.setStyleSheet(f"QWidget{{background:{BG};font-family:'Segoe UI';}}")
        self._build_ui(); self._load_config()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        bar = QFrame(); bar.setFixedHeight(52); bar.setStyleSheet(f"QFrame{{background:{RED};}}")
        bl = QHBoxLayout(bar); bl.setContentsMargins(14,0,14,0)
        t = QLabel("PACS / DICOM Manager")
        t.setStyleSheet("color:white;font-size:15px;font-weight:bold;background:transparent;")
        bl.addWidget(t); bl.addStretch()
        close = QPushButton("Back"); close.setFixedHeight(34)
        close.setStyleSheet("QPushButton{background:transparent;color:white;border:1px solid "
                            "rgba(255,255,255,0.4);border-radius:6px;font-size:12px;padding:0 14px;}"
                            "QPushButton:hover{background:rgba(255,255,255,0.25);}")
        close.clicked.connect(lambda: self.shell.navigate("dashboard")); bl.addWidget(close)
        root.addWidget(bar)
        body = QWidget(); body.setStyleSheet(f"background:{BG};")
        bl2 = QHBoxLayout(body); bl2.setContentsMargins(24,20,24,20); bl2.setSpacing(24)
        left = QFrame(); left.setStyleSheet("QFrame{background:white;border-radius:10px;}")
        ll = QVBoxLayout(left); ll.setContentsMargins(20,20,20,20); ll.setSpacing(12)
        t2 = QLabel("PACS Server Configuration"); t2.setFont(QFont("Segoe UI",13,QFont.Weight.Bold))
        t2.setStyleSheet(f"color:{RED};background:transparent;"); ll.addWidget(t2)
        for attr, ph, lbl in [
            ("pacs_ip",    "e.g. 192.168.1.100", "PACS IP Address"),
            ("ae_title",   "e.g. ORTHANC",        "AE Title (Remote)"),
            ("local_ae",   "e.g. PIXELPRO",       "Local AE Title"),
            ("institution","e.g. City Hospital",  "Institution Name"),
        ]:
            lb = QLabel(lbl); lb.setStyleSheet("color:#4b5563;font-size:11px;background:transparent;")
            inp = QLineEdit(); inp.setPlaceholderText(ph); inp.setFixedHeight(42); inp.setStyleSheet(FIELD)
            setattr(self, attr, inp); ll.addWidget(lb); ll.addWidget(inp)
        lb = QLabel("Port"); lb.setStyleSheet("color:#4b5563;font-size:11px;background:transparent;")
        self.pacs_port = QSpinBox(); self.pacs_port.setRange(1,65535); self.pacs_port.setValue(104)
        self.pacs_port.setFixedHeight(42); self.pacs_port.setStyleSheet(FIELD)
        ll.addWidget(lb); ll.addWidget(self.pacs_port); ll.addStretch()
        save = QPushButton("Save Configuration"); save.setFixedHeight(38)
        save.setStyleSheet(f"QPushButton{{background:{RED};color:white;border:none;border-radius:6px;"
                           f"font-size:13px;font-weight:bold;}}QPushButton:hover{{background:{DARK_RED};}}")
        save.clicked.connect(self._save_config); ll.addWidget(save)
        right = QFrame(); right.setStyleSheet("QFrame{background:white;border-radius:10px;}")
        rl = QVBoxLayout(right); rl.setContentsMargins(20,20,20,20); rl.setSpacing(12)
        t3 = QLabel("Connection & Upload"); t3.setFont(QFont("Segoe UI",13,QFont.Weight.Bold))
        t3.setStyleSheet(f"color:{RED};background:transparent;"); rl.addWidget(t3)
        self.status_lbl = QLabel("Not connected")
        self.status_lbl.setStyleSheet("color:#9ca3af;font-size:13px;background:transparent;font-weight:bold;")
        rl.addWidget(self.status_lbl)
        test = QPushButton("Test Connection"); test.setFixedHeight(38)
        test.setStyleSheet(f"QPushButton{{background:transparent;color:{RED};border:1.5px solid {RED};"
                           f"border-radius:6px;font-size:13px;font-weight:bold;}}"
                           f"QPushButton:hover{{background:#fff0f0;}}")
        test.clicked.connect(self._test_connection); rl.addWidget(test)
        self.progress = QProgressBar(); self.progress.setVisible(False); self.progress.setFixedHeight(8)
        self.progress.setStyleSheet(f"QProgressBar{{background:#e5e7eb;border-radius:4px;border:none;}}"
                                    f"QProgressBar::chunk{{background:{RED};border-radius:4px;}}")
        rl.addWidget(self.progress)
        log_lbl = QLabel("Activity Log"); log_lbl.setStyleSheet("color:#4b5563;font-size:11px;background:transparent;font-weight:bold;")
        rl.addWidget(log_lbl)
        self.log = QTextEdit(); self.log.setReadOnly(True)
        self.log.setStyleSheet("QTextEdit{background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;font-size:11px;color:#374151;}")
        rl.addWidget(self.log, stretch=1)
        info = QFrame(); info.setStyleSheet(f"QFrame{{background:#fef2f2;border-radius:8px;border-left:4px solid {RED};}}")
        il = QVBoxLayout(info); il.setContentsMargins(14,10,14,10)
        ih = QLabel("DICOM Export Tags"); ih.setStyleSheet(f"color:{RED};font-size:12px;font-weight:bold;background:transparent;")
        ib = QLabel("Patient Name · Patient ID · Study ID · Study Date\nModality · Institution · Annotation Overlays")
        ib.setStyleSheet("color:#374151;font-size:11px;background:transparent;")
        il.addWidget(ih); il.addWidget(ib); rl.addWidget(info)
        bl2.addWidget(left, stretch=1); bl2.addWidget(right, stretch=1)
        root.addWidget(body, stretch=1)

    def _load_config(self):
        sess = get_session(); c = sess.query(PACSConfig).first(); sess.close()
        if c:
            self.pacs_ip.setText(c.pacs_ip or ""); self.pacs_port.setValue(c.pacs_port or 104)
            self.ae_title.setText(c.ae_title or ""); self.local_ae.setText(c.local_ae_title or "PIXELPRO")
            self.institution.setText(c.institution or "")

    def _save_config(self):
        sess = get_session(); c = sess.query(PACSConfig).first()
        if not c: c = PACSConfig(); sess.add(c)
        c.pacs_ip = self.pacs_ip.text().strip(); c.pacs_port = self.pacs_port.value()
        c.ae_title = self.ae_title.text().strip(); c.local_ae_title = self.local_ae.text().strip()
        c.institution = self.institution.text().strip()
        sess.commit(); sess.close(); self._log("Configuration saved.")
        QMessageBox.information(self, "Saved", "PACS configuration saved.")

    def _test_connection(self):
        ip = self.pacs_ip.text().strip()
        if not ip: QMessageBox.warning(self,"Required","Please enter PACS IP address."); return
        self._log(f"Testing connection to {ip}:{self.pacs_port.value()}...")
        self.status_lbl.setText("Connecting...")
        self.status_lbl.setStyleSheet("color:#f59e0b;font-size:13px;background:transparent;font-weight:bold;")
        QTimer.singleShot(1500, self._sim_connected)

    def _sim_connected(self):
        self.status_lbl.setText("Connected (simulation)")
        self.status_lbl.setStyleSheet("color:#16a34a;font-size:13px;background:transparent;font-weight:bold;")
        self._log("C-ECHO success (simulation mode)")

    def _log(self, msg):
        from datetime import datetime
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
