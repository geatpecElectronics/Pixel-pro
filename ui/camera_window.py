# =============================================================
#  ui/camera_window.py — Exact Labomed GUI + embedded stream
#  d3dvideosink hwnd= embeds feed into the grey video panel
# =============================================================

import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QMessageBox, QButtonGroup,
    QRadioButton
)
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QPixmap

from models.database import get_session, Patient
from utils.session import UserSession
from services.camera_client import start_wifi_stream, stop_stream
from services.streaming_service import StreamingService

RED      = "#b01c20"
DARK_RED = "#831316"
ASSETS   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
SAVE_ROOT = r"C:\SavedMediaPMS"

TOOLBAR_STYLE = f"QFrame {{ background: {RED}; }}"

MENU_ITEMS = [
    ("🖥",  "Resolution"),
    ("☀",  "Exposure & Gain"),
    ("🎨",  "Color Adjustment"),
    ("◑",  "Black Level"),
    ("⏱",  "Frame Rate"),
    ("⇄",  "Flip"),
    ("✦",  "Test Pattern"),
]

MENU_NORMAL = f"""
    QPushButton {{
        background: transparent; color: white; border: none;
        text-align: left; padding: 0 16px;
        font-size: 15px; font-weight: bold;
    }}
    QPushButton:hover {{ background: rgba(255,255,255,0.15); }}
"""
MENU_ACTIVE = f"""
    QPushButton {{
        background: white; color: {RED}; border: none;
        text-align: left; padding: 0 16px;
        font-size: 15px; font-weight: bold;
    }}
"""
SEP = "background: rgba(255,255,255,0.25); max-height:1px;"


class CameraWindow(QMainWindow):
    def __init__(self, patient_id: int = None):
        super().__init__()
        self.patient_id   = patient_id
        self.patient      = None
        self.is_streaming = False
        self.is_recording = False
        self._active_menu = 2        # Resolution is index 0 in menu list
        self._menu_btns   = []

        self.setWindowTitle("Cam Video Page")
        self.setMinimumSize(1200, 720)
        self.setStyleSheet(f"QMainWindow {{ background: {RED}; font-family:'Segoe UI'; }}")

        if patient_id:
            sess = get_session()
            self.patient = sess.query(Patient).get(patient_id)
            sess.close()

        self._build_ui()

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

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_video_area(), stretch=1)

        body_w = QWidget()
        body_w.setLayout(body)
        root.addWidget(body_w, stretch=1)

    # ── Toolbar ───────────────────────────────────────────────
    def _build_toolbar(self):
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet(TOOLBAR_STYLE)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(2)

        for icon in ["➕", "📞", "📄"]:
            b = QPushButton(icon)
            b.setFixedSize(40, 40)
            b.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:18px;border-radius:4px;} QPushButton:hover{background:rgba(255,255,255,0.18);}")
            lay.addWidget(b)

        self.stream_btn = QPushButton("Start")
        self.stream_btn.setFixedHeight(34)
        self.stream_btn.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:14px;font-weight:bold;padding:0 12px;border-radius:4px;} QPushButton:hover{background:rgba(255,255,255,0.18);}")
        self.stream_btn.clicked.connect(self._toggle_stream)
        lay.addWidget(self.stream_btn)

        lay.addStretch()

        # Date
        date_col = QVBoxLayout()
        date_col.setSpacing(1)
        dh = QLabel("Date:")
        dh.setStyleSheet("color:#ddd; font-size:9px; background:transparent;")
        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent;")
        date_col.addWidget(dh)
        date_col.addWidget(self.date_lbl)
        lay.addLayout(date_col)

        divider = QLabel("|")
        divider.setStyleSheet("color:rgba(255,255,255,0.35); font-size:22px; background:transparent; padding:0 8px;")
        lay.addWidget(divider)

        # Time
        time_col = QVBoxLayout()
        time_col.setSpacing(1)
        th = QLabel("Time:")
        th.setStyleSheet("color:#ddd; font-size:9px; background:transparent;")
        self.time_lbl = QLabel()
        self.time_lbl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent;")
        time_col.addWidget(th)
        time_col.addWidget(self.time_lbl)
        lay.addLayout(time_col)

        lay.addSpacing(18)

        icon_lbl = QLabel("👤")
        icon_lbl.setStyleSheet("color:white; font-size:18px; background:transparent;")
        lay.addWidget(icon_lbl)
        name_lbl = QLabel(UserSession.username())
        name_lbl.setStyleSheet("color:white; font-size:13px; font-weight:bold; background:transparent; margin-left:4px;")
        lay.addWidget(name_lbl)
        lay.addSpacing(6)

        exit_btn = QPushButton("⏻")
        exit_btn.setFixedSize(36, 36)
        exit_btn.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:20px;border-radius:4px;} QPushButton:hover{background:rgba(255,255,255,0.18);}")
        exit_btn.clicked.connect(self._go_back)
        lay.addWidget(exit_btn)
        return bar

    # ── Left sidebar ──────────────────────────────────────────
    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(258)
        sidebar.setStyleSheet(f"QFrame {{ background: {RED}; }}")

        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Camera Source section ─────────────────────────────
        src_lbl = QLabel("  🎥  Camera Source")
        src_lbl.setFixedHeight(40)
        src_lbl.setStyleSheet(f"color:white; font-size:14px; font-weight:bold; background:{DARK_RED}; padding-left:10px;")
        lay.addWidget(src_lbl)

        # Internal radio
        self.radio_internal = QRadioButton("  🖥  Internal Camera")
        self.radio_internal.setChecked(True)
        self.radio_internal.setStyleSheet("QRadioButton{color:white; font-size:14px; background:transparent; padding:10px 14px;} QRadioButton::indicator{width:16px;height:16px;}")
        self.radio_internal.toggled.connect(self._on_source_changed)
        lay.addWidget(self.radio_internal)

        # WiFi radio
        self.radio_wifi = QRadioButton("  📡  WiFi Camera")
        self.radio_wifi.setStyleSheet("QRadioButton{color:white; font-size:14px; background:transparent; padding:10px 14px;} QRadioButton::indicator{width:16px;height:16px;}")
        lay.addWidget(self.radio_wifi)

        sep0 = QFrame(); sep0.setFixedHeight(1); sep0.setStyleSheet(SEP)
        lay.addWidget(sep0)

        # ── 7 menu items ──────────────────────────────────────
        for i, (icon, label) in enumerate(MENU_ITEMS):
            btn = QPushButton(f"  {icon}   {label}")
            btn.setFixedHeight(52)
            btn.setStyleSheet(MENU_NORMAL)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._activate_menu(idx))
            self._menu_btns.append(btn)
            lay.addWidget(btn)
            sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(SEP)
            lay.addWidget(sep)

        lay.addStretch()

        # Save + Preview/Stop buttons
        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(f"""
            QPushButton{{background:white;color:{DARK_RED};border-radius:10px;
                         font-size:17px;font-weight:bold;border:none;margin:0 24px;}}
            QPushButton:hover{{background:#f0f0f0;}}
        """)
        save_btn.clicked.connect(self._send_settings)
        lay.addWidget(save_btn)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setFixedHeight(44)
        self.preview_btn.setStyleSheet(f"""
            QPushButton{{background:{DARK_RED};color:#aaa;border-radius:10px;
                         font-size:17px;font-weight:bold;border:none;margin:0 24px 10px 24px;}}
            QPushButton:hover{{background:{RED};color:white;}}
        """)
        self.preview_btn.clicked.connect(self._toggle_stream)
        lay.addWidget(self.preview_btn)

        self._activate_menu(0)
        return sidebar

    # ── Video area ────────────────────────────────────────────
    def _build_video_area(self):
        wrapper = QWidget()
        wrapper.setStyleSheet("background:#CFCFCF;")
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # The actual frame GStreamer renders into
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background:#CFCFCF;")
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)

        vfl = QVBoxLayout(self.video_frame)
        self.video_label = QLabel("Click  Start  or  Preview  to begin streaming")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("color:#888; font-size:16px; background:transparent;")
        vfl.addWidget(self.video_label, alignment=Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(self.video_frame, stretch=1)

        # Bottom status bar
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"QFrame{{background:{RED};}}")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 0, 14, 0)
        bl.setSpacing(10)

        self.snap_btn = QPushButton("📷  Snapshot")
        self.snap_btn.setFixedSize(140, 32)
        self.snap_btn.setEnabled(False)
        self.snap_btn.setStyleSheet("""
            QPushButton{background:white;color:#831316;border-radius:6px;font-weight:bold;font-size:13px;border:none;}
            QPushButton:hover{background:#f0f0f0;}
            QPushButton:disabled{background:rgba(255,255,255,0.25);color:rgba(255,255,255,0.4);}
        """)
        self.snap_btn.clicked.connect(self._take_snapshot)
        bl.addWidget(self.snap_btn)

        self.rec_btn = QPushButton("⏺  Record")
        self.rec_btn.setFixedSize(130, 32)
        self.rec_btn.setEnabled(False)
        self.rec_btn.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,0.15);color:white;border-radius:6px;
                        font-weight:bold;font-size:13px;border:1px solid white;}
            QPushButton:hover{background:rgba(255,255,255,0.3);}
            QPushButton:disabled{background:transparent;color:rgba(255,255,255,0.3);border-color:rgba(255,255,255,0.3);}
        """)
        self.rec_btn.clicked.connect(self._toggle_recording)
        bl.addWidget(self.rec_btn)

        bl.addStretch()

        self.status_lbl = QLabel("● Not Streaming")
        self.status_lbl.setStyleSheet("color:rgba(255,255,255,0.6); font-size:13px; background:transparent;")
        bl.addWidget(self.status_lbl)

        lay.addWidget(bar)
        return wrapper

    # ─────────────────────────────────────────────────────────
    #  MENU + SOURCE
    # ─────────────────────────────────────────────────────────
    def _activate_menu(self, idx):
        for i, btn in enumerate(self._menu_btns):
            btn.setStyleSheet(MENU_ACTIVE if i == idx else MENU_NORMAL)
        self._active_menu = idx

    def _on_source_changed(self):
        mode = "internal" if self.radio_internal.isChecked() else "wifi"
        StreamingService.set_mode(mode)
        if self.is_streaming:
            self._stop_stream()

    # ─────────────────────────────────────────────────────────
    #  STREAM CONTROL
    # ─────────────────────────────────────────────────────────
    def _toggle_stream(self):
        if self.is_streaming:
            self._stop_stream()
        else:
            self._start_stream()

    def _start_stream(self):
        # Make sure the native HWND is created before we grab it
        self.video_frame.show()
        self.video_frame.repaint()

        if self.radio_wifi.isChecked():
            try:
                start_wifi_stream()
            except Exception as e:
                QMessageBox.critical(self, "WiFi Camera", str(e))
                return

        QTimer.singleShot(200, self._do_start_stream)

    def _do_start_stream(self):
        try:
            win_id = int(self.video_frame.winId())
            StreamingService.set_mode("internal" if self.radio_internal.isChecked() else "wifi")
            StreamingService.start(win_id, self.video_frame.width(), self.video_frame.height())

            self.is_streaming = True
            self.stream_btn.setText("Stop")
            self.preview_btn.setText("■  Stop")
            self.preview_btn.setStyleSheet(f"""
                QPushButton{{background:{DARK_RED};color:white;border-radius:10px;
                             font-size:17px;font-weight:bold;border:none;margin:0 24px 10px 24px;}}
                QPushButton:hover{{background:{RED};}}
            """)
            self.snap_btn.setEnabled(True)
            self.rec_btn.setEnabled(True)
            self.status_lbl.setText("● Streaming")
            self.status_lbl.setStyleSheet("color:#90ee90; font-size:13px; background:transparent;")
            self.video_label.hide()

        except Exception as e:
            QMessageBox.critical(self, "Stream Error", str(e))

    def _stop_stream(self):
        StreamingService.stop()
        if self.radio_wifi.isChecked():
            try: stop_stream()
            except: pass

        self.is_streaming = False
        self.stream_btn.setText("Start")
        self.preview_btn.setText("Preview")
        self.preview_btn.setStyleSheet(f"""
            QPushButton{{background:{DARK_RED};color:#aaa;border-radius:10px;
                         font-size:17px;font-weight:bold;border:none;margin:0 24px 10px 24px;}}
            QPushButton:hover{{background:{RED};color:white;}}
        """)
        self.snap_btn.setEnabled(False)
        self.rec_btn.setEnabled(False)
        self.status_lbl.setText("● Not Streaming")
        self.status_lbl.setStyleSheet("color:rgba(255,255,255,0.6); font-size:13px; background:transparent;")
        self.video_label.show()

    # ─────────────────────────────────────────────────────────
    #  SNAPSHOT
    # ─────────────────────────────────────────────────────────
    def _take_snapshot(self):
        pid    = self.patient_id or "unknown"
        folder = os.path.join(SAVE_ROOT, f"Patient_{pid}", "Images")
        os.makedirs(folder, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"Patient_{pid}_{ts}.png")

        try:
            from PyQt6.QtCore import QRect
            screen    = self.video_frame.screen()
            geo       = self.video_frame.geometry()
            global_tl = self.video_frame.mapToGlobal(geo.topLeft().__class__(0, 0))
            pixmap    = screen.grabWindow(
                0, global_tl.x(), global_tl.y(), geo.width(), geo.height()
            )
            if pixmap.save(path, "PNG"):
                self._save_image_to_db(path)
            else:
                QMessageBox.warning(self, "Snapshot", f"Failed to save:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Snapshot Error", str(e))

    def _save_image_to_db(self, path):
        if not self.patient_id:
            QMessageBox.information(self, "Snapshot", f"Saved (no patient linked):\n{path}")
            return
        from models.database import PatientMedia
        sess = get_session()
        m = PatientMedia(patient_id=self.patient_id, media_type="image", file_path=path)
        sess.add(m)
        sess.commit()
        sess.close()
        QMessageBox.information(self, "Snapshot", f"✅ Saved:\n{path}")

    # ─────────────────────────────────────────────────────────
    #  RECORDING
    # ─────────────────────────────────────────────────────────
    def _toggle_recording(self):
        if not self.is_recording:
            pid    = self.patient_id or "unknown"
            folder = os.path.join(SAVE_ROOT, f"Patient_{pid}", "Videos")
            os.makedirs(folder, exist_ok=True)
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(folder, f"Patient_{pid}_{ts}.mp4")
            try:
                win_id = int(self.video_frame.winId())
                StreamingService.start_recording(path, win_id=win_id)
                self.is_recording = True
                self._recording_path = path
                self.rec_btn.setText("⏹  Stop")
                self.status_lbl.setText("⏺  Recording")
                self.status_lbl.setStyleSheet("color:#ff6b6b; font-size:13px; background:transparent;")
            except Exception as e:
                QMessageBox.critical(self, "Recording Error", str(e))
        else:
            StreamingService.stop_recording()
            self.is_recording = False
            self.rec_btn.setText("⏺  Record")
            self.status_lbl.setText("● Streaming")
            self.status_lbl.setStyleSheet("color:#90ee90; font-size:13px; background:transparent;")
            # Save video to PatientMedia
            if self.patient_id and hasattr(self, '_recording_path'):
                from models.database import PatientMedia
                sess = get_session()
                m = PatientMedia(patient_id=self.patient_id, media_type="video",
                                 file_path=self._recording_path)
                sess.add(m)
                sess.commit()
                sess.close()

    # ─────────────────────────────────────────────────────────
    #  MISC
    # ─────────────────────────────────────────────────────────
    def _send_settings(self):
        QMessageBox.information(self, "Settings", "Settings saved.")

    def _tick(self):
        now = QDateTime.currentDateTime()
        self.date_lbl.setText(now.toString("dd-MM-yyyy"))
        self.time_lbl.setText(now.toString("hh:mm AP"))

    def _go_back(self):
        StreamingService.stop()
        StreamingService.stop_recording()
        from ui.main_window import MainWindow
        self.mw = MainWindow()
        self.mw.show()
        self.close()

    def closeEvent(self, event):
        StreamingService.stop()
        StreamingService.stop_recording()
        super().closeEvent(event)
