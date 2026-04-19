# =============================================================
#  ui/camera_capture.py  — Camera page (QWidget)
# =============================================================
import os
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy,
    QRadioButton, QMessageBox, QButtonGroup)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QFont
from ui._styles import RED, DARK_RED
from models.database import get_session, Visit, CapturedImage
from services.streaming_service import StreamingService
from utils.session import UserSession

SAVE_ROOT = os.path.join(
    os.environ.get("PIXELPRO_DATA_DIR",
                   os.path.join(os.path.expanduser("~"), "PixelPro")),
    "SavedMedia"
)


def _load_visit_dict(visit_id_pk):
    from models.database import Patient
    sess = get_session()
    try:
        v = sess.query(Visit).filter(Visit.id==int(visit_id_pk)).first()
        if not v: return {}
        p = sess.query(Patient).filter(Patient.id==v.patient_id).first() if v.patient_id else None
        return {"id":v.id,"visit_id":v.visit_id or "—","doctor":v.doctor or "—",
                "patient_id":p.id if p else None,"patient_pid":p.patient_id or "—" if p else "—",
                "patient_name":f"{p.first_name or ''} {p.last_name or ''}".strip() if p else "—"}
    except Exception as ex:
        print(f"[Camera] error: {ex}"); return {}
    finally: sess.close()


def _load_strip_images(visit_id_pk):
    sess = get_session()
    imgs = (sess.query(CapturedImage)
            .filter(CapturedImage.visit_id==int(visit_id_pk), CapturedImage.is_deleted!=True)
            .order_by(CapturedImage.sort_order).all())
    result = [{"id":i.id,"file_path":i.file_path or "","annotated_path":i.annotated_path or ""} for i in imgs]
    sess.close(); return result


class ThumbCard(QFrame):
    def __init__(self, img_dict, on_annotate, on_delete):
        super().__init__(); self.img_id = img_dict["id"]
        self.setFixedSize(130,120)
        self.setStyleSheet("QFrame{background:#3a3a3a;border-radius:6px;border:2px solid #666;}"
                           "QFrame:hover{border-color:#b01c20;}")
        lay = QVBoxLayout(self); lay.setContentsMargins(5,5,5,5); lay.setSpacing(4)
        thumb = QLabel(); thumb.setFixedSize(118,78); thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet("background:#555;border-radius:3px;color:white;font-size:10px;")
        path = img_dict.get("annotated_path") or img_dict.get("file_path","")
        if path and os.path.exists(path):
            pix = QPixmap(path).scaled(118,78,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
            thumb.setPixmap(pix)
        else:
            thumb.setText("No preview")
        lay.addWidget(thumb)
        row = QHBoxLayout(); row.setSpacing(4)
        for lbl, fn, col in [
            ("Edit",   lambda _=False, iid=img_dict["id"]: on_annotate(iid), "#b01c20"),
            ("Delete", lambda _=False, iid=img_dict["id"]: on_delete(iid),   "#374151"),
        ]:
            b = QPushButton(lbl); b.setFixedHeight(24)
            b.setStyleSheet(f"QPushButton{{background:{col};color:white;border:none;"
                            f"border-radius:3px;font-size:11px;font-weight:bold;}}"
                            "QPushButton:hover{opacity:0.85;}")
            b.clicked.connect(fn); row.addWidget(b)
        lay.addLayout(row)


class CameraPage(QWidget):
    def __init__(self, shell, visit_id_pk):
        super().__init__()
        self.shell = shell; self.visit_id_pk = visit_id_pk
        self.visit_dict = _load_visit_dict(visit_id_pk)
        self.is_streaming = False; self.is_recording = False
        self._rec_path = None; self._menu_btns = []
        self.setStyleSheet(f"QWidget{{background:{RED};font-family:'Segoe UI';}}")
        self._build_ui(); self._load_strip()

    def _toolbar(self):
        bar = QFrame(); bar.setFixedHeight(58); bar.setStyleSheet(f"QFrame{{background:{RED};}}")
        lay = QHBoxLayout(bar); lay.setContentsMargins(14,0,14,0); lay.setSpacing(6)
        bk = QPushButton("←"); bk.setFixedSize(36,36)
        bk.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:18px;border-radius:4px;}"
                         "QPushButton:hover{background:rgba(255,255,255,0.18);}")
        bk.clicked.connect(self._go_back); lay.addWidget(bk)
        vd = self.visit_dict
        info = QLabel(f"{vd.get('patient_name','—')}  ·  {vd.get('visit_id','—')}  ·  Dr. {vd.get('doctor','—')}")
        info.setStyleSheet("color:white;font-size:13px;font-weight:bold;background:transparent;")
        lay.addWidget(info); lay.addSpacing(16)
        self.stream_btn = QPushButton("Start Stream"); self.stream_btn.setFixedHeight(34)
        self.stream_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.15);color:white;border:none;"
                                      "border-radius:6px;font-size:13px;font-weight:bold;padding:0 16px;}"
                                      "QPushButton:hover{background:rgba(255,255,255,0.25);}")
        self.stream_btn.clicked.connect(self._toggle_stream); lay.addWidget(self.stream_btn)
        lay.addStretch()
        u = QLabel(UserSession.username())
        u.setStyleSheet("color:white;font-size:12px;background:transparent;"); lay.addWidget(u)
        ex = QPushButton("\u23fb"); ex.setFixedSize(36,36)
        ex.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:20px;"
                         "border-radius:4px;}QPushButton:hover{background:rgba(255,255,255,0.18);}")
        ex.clicked.connect(self._go_back); lay.addWidget(ex)
        return bar

    def _sidebar(self):
        sb = QFrame(); sb.setFixedWidth(250); sb.setStyleSheet(f"QFrame{{background:{RED};}}")
        sl = QVBoxLayout(sb); sl.setContentsMargins(0,0,0,0); sl.setSpacing(0)
        src_hdr = QLabel("  Camera Source"); src_hdr.setFixedHeight(40)
        src_hdr.setStyleSheet(f"color:white;font-size:13px;font-weight:bold;background:{DARK_RED};padding-left:10px;")
        sl.addWidget(src_hdr)
        self.bg = QButtonGroup(self)
        for i, (label, mode) in enumerate([("Internal Camera","internal"),("WiFi Camera","wifi"),("USB Camera","usb")]):
            r = QRadioButton(f"  {label}")
            r.setStyleSheet("QRadioButton{color:white;font-size:13px;background:transparent;padding:9px 14px;}"
                            "QRadioButton::indicator{width:16px;height:16px;border-radius:8px;"
                            "border:2px solid rgba(255,255,255,0.7);background:transparent;}"
                            "QRadioButton::indicator:checked{background:white;border:2px solid white;}"
                            "QRadioButton::indicator:unchecked:hover{border-color:white;}")
            r.setProperty("mode", mode)
            if i == 0: r.setChecked(True)
            r.toggled.connect(self._source_changed)
            self.bg.addButton(r, i); sl.addWidget(r)
        self.wifi_lbl = QLabel()
        self.wifi_lbl.setStyleSheet("color:#fbbf24;font-size:11px;background:transparent;padding-left:20px;")
        self.wifi_lbl.hide(); sl.addWidget(self.wifi_lbl)
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:rgba(255,255,255,0.2);")
        sl.addWidget(sep); sl.addStretch()
        report_btn = QPushButton("Review & Report"); report_btn.setFixedHeight(40)
        report_btn.setStyleSheet(f"QPushButton{{background:white;color:{DARK_RED};border:none;"
                                 f"border-radius:8px;font-size:13px;font-weight:bold;margin:0 14px;}}"
                                 f"QPushButton:hover{{background:#f5f5f5;}}")
        report_btn.clicked.connect(self._go_report); sl.addWidget(report_btn)
        done_btn = QPushButton("Done"); done_btn.setFixedHeight(40)
        done_btn.setStyleSheet(f"QPushButton{{background:{DARK_RED};color:white;border:none;"
                               f"border-radius:8px;font-size:13px;font-weight:bold;margin:0 14px 12px 14px;}}"
                               f"QPushButton:hover{{background:#6b0f12;}}")
        done_btn.clicked.connect(self._go_back); sl.addWidget(done_btn)
        return sb

    def _main_area(self):
        wrap = QWidget(); wrap.setStyleSheet("background:#CFCFCF;")
        wl = QVBoxLayout(wrap); wl.setContentsMargins(0,0,0,0); wl.setSpacing(0)
        self.video_frame = QFrame(); self.video_frame.setStyleSheet("background:#1a1a1a;")
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)
        self.video_hint = QLabel("Select camera source and click  Start Stream")
        self.video_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_hint.setStyleSheet("color:#555;font-size:15px;background:transparent;")
        vfl = QVBoxLayout(self.video_frame)
        vfl.addWidget(self.video_hint, alignment=Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(self.video_frame, stretch=1)
        ctrl = QFrame(); ctrl.setFixedHeight(52); ctrl.setStyleSheet(f"QFrame{{background:{RED};}}")
        cl = QHBoxLayout(ctrl); cl.setContentsMargins(14,0,14,0); cl.setSpacing(10)
        self.snap_btn = QPushButton("Capture"); self.snap_btn.setFixedSize(120,36); self.snap_btn.setEnabled(False)
        self.snap_btn.setStyleSheet("QPushButton{background:white;color:#831316;border:none;border-radius:6px;"
                                    "font-size:13px;font-weight:bold;}"
                                    "QPushButton:hover{background:#f5f5f5;}"
                                    "QPushButton:disabled{background:rgba(255,255,255,0.2);color:rgba(255,255,255,0.4);}")
        self.snap_btn.clicked.connect(self._capture); cl.addWidget(self.snap_btn)
        self.rec_btn = QPushButton("Record"); self.rec_btn.setFixedSize(110,36); self.rec_btn.setEnabled(False)
        self.rec_btn.setStyleSheet("QPushButton{background:rgba(255,255,255,0.12);color:white;border:1px solid white;"
                                   "border-radius:6px;font-size:13px;font-weight:bold;}"
                                   "QPushButton:hover{background:rgba(255,255,255,0.22);}"
                                   "QPushButton:disabled{background:transparent;color:rgba(255,255,255,0.3);border-color:rgba(255,255,255,0.3);}")
        self.rec_btn.clicked.connect(self._toggle_recording); cl.addWidget(self.rec_btn)
        cl.addStretch()
        self.status_lbl = QLabel("Not Streaming")
        self.status_lbl.setStyleSheet("color:rgba(255,255,255,0.5);font-size:12px;background:transparent;")
        cl.addWidget(self.status_lbl); wl.addWidget(ctrl)
        shdr = QFrame(); shdr.setFixedHeight(32); shdr.setStyleSheet(f"QFrame{{background:{DARK_RED};}}")
        shl = QHBoxLayout(shdr); shl.setContentsMargins(14,0,14,0)
        self.strip_count = QLabel("0 images")
        self.strip_count.setStyleSheet("color:white;font-size:11px;background:transparent;")
        shl.addWidget(self.strip_count); shl.addStretch()
        va = QPushButton("Review & Select"); va.setFixedHeight(22)
        va.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:11px;}"
                         "QPushButton:hover{text-decoration:underline;}")
        va.clicked.connect(self._go_report); shl.addWidget(va); wl.addWidget(shdr)
        strip_sc = QScrollArea(); strip_sc.setFixedHeight(128); strip_sc.setWidgetResizable(True)
        strip_sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        strip_sc.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        strip_sc.setStyleSheet("QScrollArea{border:none;background:#1a1a1a;}")
        self.strip_w = QWidget(); self.strip_w.setStyleSheet("background:#1a1a1a;")
        self.strip_vl = QHBoxLayout(self.strip_w)
        self.strip_vl.setContentsMargins(8,8,8,8); self.strip_vl.setSpacing(8)
        self.strip_vl.addStretch(); strip_sc.setWidget(self.strip_w); wl.addWidget(strip_sc)
        return wrap

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self._toolbar())
        body = QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)
        body.addWidget(self._sidebar()); body.addWidget(self._main_area(), stretch=1)
        bw = QWidget(); bw.setLayout(body); root.addWidget(bw, stretch=1)

    def _load_strip(self):
        while self.strip_vl.count():
            item = self.strip_vl.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        imgs = _load_strip_images(self.visit_id_pk)
        self.strip_count.setText(f"{len(imgs)} image{'s' if len(imgs)!=1 else ''} captured")
        for img in imgs: self.strip_vl.addWidget(ThumbCard(img, self._annotate, self._delete_img))
        self.strip_vl.addStretch()

    def _source_changed(self):
        for btn in self.bg.buttons():
            if btn.isChecked():
                mode = btn.property("mode")
                StreamingService.set_mode(mode)          # ← tell service which source
                if mode in ("wifi", "usb"):
                    self.wifi_lbl.setText("  Select Start Stream to connect...")
                    self.wifi_lbl.show()
                else:
                    self.wifi_lbl.hide()
        if self.is_streaming:
            self._stop_stream()

    def _toggle_stream(self):
        if self.is_streaming: self._stop_stream()
        else: self._start_stream()

    def _start_stream(self):
        self.video_frame.repaint(); QTimer.singleShot(200, self._do_start)

    def _do_start(self):
        try:
            StreamingService.start(
                int(self.video_frame.winId()),
                self.video_frame.width(),
                self.video_frame.height(),
                on_wifi_fail=self._on_wifi_fail,
                on_wifi_status=self._on_wifi_status,
            )
            # For WiFi mode the stream starts asynchronously after handshake —
            # mark as streaming immediately so the UI buttons are correct.
            self.is_streaming = True
            self.stream_btn.setText("Stop Stream")
            self.snap_btn.setEnabled(True)
            self.rec_btn.setEnabled(True)
            self.video_hint.hide()
            if StreamingService._mode in ("wifi", "usb"):
                label = "WiFi" if StreamingService._mode == "wifi" else "USB"
                self.status_lbl.setText(f"Connecting to {label} camera...")
                self.status_lbl.setStyleSheet(
                    "color:#fbbf24;font-size:12px;background:transparent;")
            else:
                self.status_lbl.setText("Streaming")
                self.status_lbl.setStyleSheet(
                    "color:#90ee90;font-size:12px;background:transparent;")
        except Exception as e:
            QMessageBox.critical(self, "Stream Error", str(e))

    def _on_wifi_status(self, msg: str):
        """Called from background thread — must use QTimer to touch UI safely."""
        QTimer.singleShot(0, lambda: self._set_wifi_status(msg))

    def _set_wifi_status(self, msg: str):
        self.wifi_lbl.setText(f"  {msg}")
        self.wifi_lbl.show()
        self.status_lbl.setText(msg)

    def _on_wifi_fail(self):
        """Called from background thread after 5-min timeout."""
        QTimer.singleShot(0, self._handle_wifi_fail)

    def _handle_wifi_fail(self):
        mode  = StreamingService._mode
        label = "USB" if mode == "usb" else "WiFi"
        self._stop_stream()
        self.wifi_lbl.setText(f"  {label} camera not available")
        self.wifi_lbl.show()
        self.status_lbl.setText(f"{label} camera not available")
        self.status_lbl.setStyleSheet(
            "color:#ff6b6b;font-size:12px;background:transparent;")
        QMessageBox.warning(
            self, f"{label} Camera",
            f"Could not connect to {label} camera after 5 minutes.\n"
            f"Make sure the camera is powered on and reachable."
        )

    def _stop_stream(self):
        StreamingService.stop(); self.is_streaming = False; self.stream_btn.setText("Start Stream")
        self.snap_btn.setEnabled(False); self.rec_btn.setEnabled(False)
        self.status_lbl.setText("Not Streaming")
        self.status_lbl.setStyleSheet("color:rgba(255,255,255,0.5);font-size:12px;background:transparent;")
        self.video_hint.show()

    def _capture(self):
        vd = self.visit_dict
        pid = vd.get("patient_pid","unknown"); vid = vd.get("visit_id","unknown")
        folder = os.path.join(SAVE_ROOT,"Patients",pid,vid,"images")
        os.makedirs(folder, exist_ok=True)
        sess = get_session()
        count = sess.query(CapturedImage).filter(CapturedImage.visit_id==self.visit_id_pk, CapturedImage.is_deleted!=True).count()
        sess.close()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"img_{count+1:03d}_{ts}.png")
        try:
            global_tl = self.video_frame.mapToGlobal(QPoint(0,0)); geo = self.video_frame.geometry()
            pix = self.video_frame.screen().grabWindow(0,global_tl.x(),global_tl.y(),geo.width(),geo.height())
            if pix.save(path,"PNG"):
                src = ("wifi" if self.bg.button(1).isChecked() else "usb" if self.bg.button(2).isChecked() else "internal")
                sess = get_session(); sess.add(CapturedImage(visit_id=self.visit_id_pk,file_path=path,camera_source=src,sort_order=count))
                sess.commit(); sess.close(); self._load_strip()
            else:
                QMessageBox.warning(self,"Capture Failed",f"Could not save:\n{path}")
        except Exception as e:
            QMessageBox.critical(self,"Capture Error",str(e))

    def _toggle_recording(self):
        if not self.is_recording:
            vd = self.visit_dict
            folder = os.path.join(SAVE_ROOT,"Patients",vd.get("patient_pid","x"),vd.get("visit_id","x"),"videos")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder,f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            try:
                StreamingService.start_recording(path, int(self.video_frame.winId()))
                self.is_recording = True; self._rec_path = path; self.rec_btn.setText("Stop Rec")
                self.status_lbl.setText("Recording")
                self.status_lbl.setStyleSheet("color:#ff6b6b;font-size:12px;background:transparent;")
            except Exception as e:
                QMessageBox.critical(self,"Record Error",str(e))
        else:
            StreamingService.stop_recording(); self.is_recording = False; self.rec_btn.setText("Record")
            self.status_lbl.setText("Streaming")
            self.status_lbl.setStyleSheet("color:#90ee90;font-size:12px;background:transparent;")

    def _annotate(self, img_id):
        sess = get_session(); img = sess.query(CapturedImage).filter_by(id=img_id).first()
        path = img.file_path if img else None; sess.close()
        if not path: return
        from ui.annotation_editor import AnnotationEditor
        self.ed = AnnotationEditor(img_id, path); self.ed.show()
        self.ed.destroyed.connect(self._load_strip)

    def _delete_img(self, img_id):
        if QMessageBox.question(self,"Delete","Delete this image?",
           QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
           ) == QMessageBox.StandardButton.Yes:
            sess = get_session(); i = sess.query(CapturedImage).filter_by(id=img_id).first()
            if i: i.is_deleted=True; sess.commit()
            sess.close(); self._load_strip()

    def _go_report(self):
        StreamingService.stop(); self.shell.navigate("report", visit_id_pk=self.visit_id_pk)

    def _go_back(self):
        StreamingService.stop(); StreamingService.stop_recording()
        vd = self.visit_dict
        self.shell.navigate("visits", patient_id=vd.get("patient_id"))

    def hideEvent(self, e):
        StreamingService.stop(); StreamingService.stop_recording(); super().hideEvent(e)
