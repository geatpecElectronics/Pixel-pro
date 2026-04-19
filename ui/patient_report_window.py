# =============================================================
#  ui/patient_report_window.py
#  Patient info + all images & videos in one unified scrollable grid
# =============================================================

import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGridLayout, QSizePolicy,
    QMessageBox, QSpacerItem
)
from PyQt6.QtCore import Qt, QDateTime, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor

from models.database import get_session, Patient, PatientMedia
from utils.session import UserSession

RED      = "#b01c20"
DARK_RED = "#8B0000"


class MediaCard(QFrame):
    """Unified card for both images and videos."""
    def __init__(self, media: PatientMedia, on_annotate=None, on_delete=None):
        super().__init__()
        self.media = media
        self.setFixedSize(178, 215)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
            QFrame:hover {
                border: 1.5px solid #b01c20;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(7, 7, 7, 7)
        lay.setSpacing(5)

        # ── Thumbnail ─────────────────────────────────────────
        thumb = QLabel()
        thumb.setFixedSize(162, 128)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet("background:#f1f5f9; border-radius:6px; border:none;")

        if media.media_type == "image":
            path = media.file_path
            if os.path.exists(path):
                pix = QPixmap(path).scaled(
                    162, 128,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                thumb.setPixmap(pix)
            else:
                thumb.setText("⚠\nNot found")
                thumb.setStyleSheet("background:#fef2f2; color:#dc2626; font-size:11px; border-radius:6px; border:none;")
        else:
            # Video card
            thumb.setText("🎬")
            thumb.setFont(QFont("Segoe UI", 32))
            thumb.setStyleSheet("background:#0f172a; color:white; border-radius:6px; border:none;")

        lay.addWidget(thumb)

        # ── Type badge + filename ─────────────────────────────
        badge_row = QHBoxLayout()
        badge_row.setSpacing(4)

        badge = QLabel("IMG" if media.media_type == "image" else "VID")
        badge.setFixedHeight(16)
        badge.setStyleSheet(
            f"background:{'#166534' if media.media_type=='image' else '#1e40af'};"
            "color:white; font-size:9px; font-weight:bold; padding:0 5px;"
            "border-radius:3px; border:none;"
        )
        badge_row.addWidget(badge)

        ts = media.created_at.strftime("%d %b %H:%M") if media.created_at else ""
        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet("color:#6b7280; font-size:9px; background:transparent; border:none;")
        badge_row.addWidget(ts_lbl)
        badge_row.addStretch()
        lay.addLayout(badge_row)

        fname = os.path.basename(media.file_path)
        if len(fname) > 22: fname = fname[:20] + "…"
        name_lbl = QLabel(fname)
        name_lbl.setStyleSheet("color:#374151; font-size:10px; background:transparent; border:none;")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(name_lbl)

        # ── Action buttons ────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        btn_row.setContentsMargins(0, 0, 0, 0)

        if media.media_type == "image" and on_annotate:
            ann_btn = self._btn("✏", f"background:{RED};", "Annotate image")
            ann_btn.clicked.connect(lambda: on_annotate(media))
            btn_row.addWidget(ann_btn)

        open_btn = self._btn("↗", "background:#374151;", "Open file")
        open_btn.clicked.connect(lambda: self._open(media.file_path))
        btn_row.addWidget(open_btn)

        if on_delete:
            del_btn = self._btn("🗑", "background:#dc2626;", "Delete")
            del_btn.clicked.connect(lambda: on_delete(media))
            btn_row.addWidget(del_btn)

        lay.addLayout(btn_row)

    def _btn(self, icon, bg_style, tip):
        b = QPushButton(icon)
        b.setFixedSize(34, 28)
        b.setToolTip(tip)
        b.setStyleSheet(
            f"QPushButton{{{bg_style}color:white;border:none;border-radius:5px;font-size:13px;}}"
            f"QPushButton:hover{{opacity:0.8;}}"
        )
        return b

    def _open(self, path):
        if os.path.exists(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Not Found", f"File not found:\n{path}")


class PatientReportWindow(QMainWindow):
    def __init__(self, patient: Patient):
        super().__init__()
        self.patient = patient
        self.setWindowTitle(f"Patient Report — {patient.first_name} {patient.last_name}")
        self.setMinimumSize(1100, 760)
        self.setStyleSheet("QMainWindow{background:white; font-family:'Segoe UI';} QLabel{color:#1f2937;}")
        self._build_ui()
        self._load_media()

        self._clock = QTimer()
        self._clock.timeout.connect(self._tick)
        self._clock.start(1000)
        self._tick()

    # ─────────────────────────────────────────────────────────
    #  BUILD UI
    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none; background:white;}")

        body = QWidget()
        body.setStyleSheet("background:white;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 20, 24, 24)
        bl.setSpacing(16)

        # Patient name header
        name_lbl = QLabel(f"{self.patient.first_name or ''} {self.patient.last_name or ''}")
        name_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color:{RED}; background:transparent;")
        bl.addWidget(name_lbl)

        bl.addWidget(self._section_header("Basic Information"))
        bl.addLayout(self._basic_info_grid())

        bl.addWidget(self._section_header("Medical Information"))
        bl.addLayout(self._medical_info_grid())

        # Media section header with count badge
        mhdr = QHBoxLayout()
        mhdr.addWidget(self._section_header("Captured Media"))
        mhdr.addStretch()
        self.media_count_lbl = QLabel("")
        self.media_count_lbl.setStyleSheet(
            f"background:{RED}; color:white; font-size:11px; font-weight:bold;"
            "padding:3px 10px; border-radius:10px;"
        )
        mhdr.addWidget(self.media_count_lbl)
        bl.addLayout(mhdr)

        # Unified media grid
        self.media_grid_widget = QWidget()
        self.media_grid_widget.setStyleSheet("background:transparent;")
        self.media_grid = QGridLayout(self.media_grid_widget)
        self.media_grid.setSpacing(14)
        self.media_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        bl.addWidget(self.media_grid_widget)

        bl.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

    # ── Toolbar ───────────────────────────────────────────────
    def _build_toolbar(self):
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"QFrame{{background:{RED};}} QLabel{{color:white; background:transparent;}}")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(4)

        for icon in ["📄", "📷", "🖼"]:
            b = QPushButton(icon)
            b.setFixedSize(38, 38)
            b.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:18px;border-radius:4px;} QPushButton:hover{background:rgba(255,255,255,0.18);}")
            lay.addWidget(b)

        lay.addStretch()

        # Date
        date_col = QVBoxLayout()
        date_col.setSpacing(0)
        dh = QLabel("Date:")
        dh.setStyleSheet("color:#ddd; font-size:9px; background:transparent;")
        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent;")
        date_col.addWidget(dh); date_col.addWidget(self.date_lbl)
        lay.addLayout(date_col)

        sep = QLabel("|")
        sep.setStyleSheet("color:rgba(255,255,255,0.35); font-size:22px; background:transparent; padding:0 8px;")
        lay.addWidget(sep)

        time_col = QVBoxLayout()
        time_col.setSpacing(0)
        th = QLabel("Time:")
        th.setStyleSheet("color:#ddd; font-size:9px; background:transparent;")
        self.time_lbl = QLabel()
        self.time_lbl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent;")
        time_col.addWidget(th); time_col.addWidget(self.time_lbl)
        lay.addLayout(time_col)

        lay.addSpacing(14)

        user_lbl = QLabel(f"👤  {UserSession.username()}")
        user_lbl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent;")
        lay.addWidget(user_lbl)
        lay.addSpacing(8)

        logout = QPushButton("⏻")
        logout.setFixedSize(36, 36)
        logout.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:20px;border-radius:4px;} QPushButton:hover{background:rgba(255,255,255,0.18);}")
        logout.clicked.connect(self._logout)
        lay.addWidget(logout)
        return bar

    # ── Info grids ────────────────────────────────────────────
    def _basic_info_grid(self):
        p = self.patient
        rows = [
            [("First Name", p.first_name), ("Last Name", p.last_name)],
            [("Gender", p.gender), ("Date of Birth", p.dob.strftime("%d %b %Y") if p.dob else "—")],
            [("Contact", p.contact_number), ("Email", p.email_id)],
            [("Blood Group", p.blood_group), ("Address", p.address)],
        ]
        return self._info_grid(rows)

    def _medical_info_grid(self):
        p = self.patient
        rows = [
            [("Current Medications", p.current_medication), ("Existing Medical Conditions", p.existing_medical)],
            [("Past Medical History", p.past_medical_history), ("Allergies", p.allergies)],
            [("Referring Doctor", p.ref_doc), ("", "")],
        ]
        return self._info_grid(rows)

    def _info_grid(self, rows):
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setHorizontalSpacing(32)
        for r, row in enumerate(rows):
            for c, (label, value) in enumerate(row):
                if not label: continue
                lbl = QLabel(label)
                lbl.setStyleSheet("color:#6b7280; font-size:11px; background:transparent;")
                val = QLabel(value or "—")
                val.setStyleSheet(f"color:#111827; font-size:13px; font-weight:600; background:transparent;")
                val.setWordWrap(True)
                grid.addWidget(lbl, r*2,   c)
                grid.addWidget(val, r*2+1, c)
        return grid

    # ── Section header ────────────────────────────────────────
    def _section_header(self, text):
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setStyleSheet(f"QFrame{{background:{DARK_RED}; border-radius:5px;}} QLabel{{color:white; font-size:13px; font-weight:bold; background:transparent; padding-left:12px;}}")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(text))
        return frame

    # ─────────────────────────────────────────────────────────
    #  LOAD MEDIA — unified grid, images + videos together
    # ─────────────────────────────────────────────────────────
    def _load_media(self):
        # Clear grid
        while self.media_grid.count():
            item = self.media_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sess    = get_session()
        patient = sess.query(Patient).get(self.patient.id)
        media_rows = [m for m in (patient.media if patient else []) if not m.is_deleted]
        sess.close()

        # Also collect legacy path_image1..5
        legacy = []
        for i in range(1, 6):
            path = getattr(self.patient, f"path_image{i}", None)
            if path:
                fake = PatientMedia()
                fake.id          = -i
                fake.patient_id  = self.patient.id
                fake.media_type  = "image"
                fake.file_path   = path
                fake.annotated_path = None
                fake.created_at  = None
                legacy.append(fake)

        all_media = media_rows + legacy
        total = len(all_media)

        self.media_count_lbl.setText(
            f"{sum(1 for m in all_media if m.media_type=='image')} images  "
            f"·  {sum(1 for m in all_media if m.media_type=='video')} videos"
        )

        if not all_media:
            empty = QLabel("No media captured yet. Use the Camera page to take snapshots or record videos.")
            empty.setStyleSheet("color:#9ca3af; font-size:13px; padding:20px; background:transparent;")
            empty.setWordWrap(True)
            self.media_grid.addWidget(empty, 0, 0, 1, 5)
            return

        COLS = 5
        for idx, m in enumerate(all_media):
            row, col = divmod(idx, COLS)
            card = MediaCard(
                m,
                on_annotate=self._annotate if m.id > 0 else None,
                on_delete=self._delete     if m.id > 0 else None,
            )
            self.media_grid.addWidget(card, row, col)

    # ─────────────────────────────────────────────────────────
    #  ACTIONS
    # ─────────────────────────────────────────────────────────
    def _annotate(self, media: PatientMedia):
        from ui.annotation_editor import AnnotationEditor
        self.editor = AnnotationEditor(media.id, media.file_path, self.patient.id)
        self.editor.show()
        # Reload grid when editor closes so thumbnail refreshes
        self.editor.destroyed.connect(self._load_media)

    def _delete(self, media: PatientMedia):
        fname = os.path.basename(media.file_path)
        reply = QMessageBox.question(
            self, "Delete Media",
            f"Delete this {media.media_type}?\n{fname}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            sess = get_session()
            m = sess.query(PatientMedia).get(media.id)
            if m:
                m.is_deleted = True
                sess.commit()
            sess.close()
            self._load_media()

    def _tick(self):
        now = QDateTime.currentDateTime()
        self.date_lbl.setText(now.toString("dd-MM-yyyy"))
        self.time_lbl.setText(now.toString("hh:mm AP"))

    def _logout(self):
        UserSession.end()
        from ui.login_window import LoginWindow
        self.lw = LoginWindow()
        self.lw.show()
        self.close()
