# =============================================================
#  ui/report_builder.py  — Image select + Report editor + PDF
#  PDF uses pixel_pro_report_generator.py (ReportLab-based)
#  Hospital name/address/email/logo are GLOBAL — saved once,
#  auto-filled on every report, never lost between visits.
# =============================================================
import os, json, tempfile
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTextEdit, QLineEdit, QCheckBox, QMessageBox,
    QStackedWidget, QGridLayout, QFileDialog, QProgressDialog, QSizePolicy)
from PyQt6.QtCore  import Qt, QTimer, QSizeF
from PyQt6.QtGui   import QFont, QPixmap, QCursor
from ui._styles    import RED, DARK_RED, BG, FIELD, TEXT_MID, TEXT_LITE
from models.database import (get_session, Visit, Patient, CapturedImage,
                              PACSConfig, SavedReport, HospitalProfile)
from utils.session import UserSession

# ─── DESIGN TOKENS (match dashboard palette) ──────────────────
C = {
    "red":       "#B91C1C", "red_dark":  "#991B1B",
    "red_light": "#FEE2E2", "bg":        "#F7F4F0",
    "bg2":       "#EFECE8", "white":     "#FFFFFF",
    "border":    "#E8E3DC", "border2":   "#D6CFC5",
    "text":      "#1C1410", "text2":     "#6B5E52",
    "text3":     "#A8998C",
}

# ─── GLOBAL HOSPITAL PROFILE ──────────────────────────────────

def _load_hospital_profile() -> dict:
    sess = get_session()
    try:
        h = sess.query(HospitalProfile).first()
        if not h:
            return {"name": "", "address": "", "email": "", "phone": "", "logo_path": ""}
        return {
            "name":      h.name      or "",
            "address":   h.address   or "",
            "email":     h.email     or "",
            "phone":     h.phone     or "",
            "logo_path": h.logo_path or "",
        }
    finally:
        sess.close()


def _save_hospital_profile(data: dict):
    sess = get_session()
    try:
        h = sess.query(HospitalProfile).first()
        if not h:
            h = HospitalProfile(); sess.add(h)
        h.name      = data.get("name",      "")
        h.address   = data.get("address",   "")
        h.email     = data.get("email",     "")
        h.phone     = data.get("phone",     "")
        h.logo_path = data.get("logo_path", "")
        h.updated_at = datetime.now()
        sess.commit()
    finally:
        sess.close()


# ─── PER-VISIT SAVED REPORT ───────────────────────────────────

def _load_saved_report(visit_id_pk: int) -> dict:
    sess = get_session()
    try:
        r = sess.query(SavedReport).filter(
            SavedReport.visit_id == visit_id_pk,
            SavedReport.is_deleted != True
        ).order_by(SavedReport.saved_at.desc()).first()
        if not r:
            return {}
        return {
            "id":           r.id,
            "observations": r.observations or "",
            "diagnosis":    r.diagnosis    or "",
            "notes":        r.notes        or "",
            "doctor":       r.doctor       or "",
            "department":   r.department   or "",
            "signature":    r.signature    or "",
            "saved_at":     r.saved_at,
        }
    finally:
        sess.close()


def _upsert_saved_report(visit_id_pk: int, fields: dict) -> int:
    sess = get_session()
    try:
        r = sess.query(SavedReport).filter(
            SavedReport.visit_id == visit_id_pk,
            SavedReport.is_deleted != True
        ).first()
        if not r:
            r = SavedReport(visit_id=visit_id_pk); sess.add(r)
        r.observations = fields.get("observations", "")
        r.diagnosis    = fields.get("diagnosis",    "")
        r.notes        = fields.get("notes",        "")
        r.doctor       = fields.get("doctor",       "")
        r.department   = fields.get("department",   "")
        r.signature    = fields.get("signature",    "")
        r.report_html  = fields.get("report_html",  "")
        r.saved_at     = datetime.now()
        sess.commit()
        return r.id
    finally:
        sess.close()


# ─── VISIT / PATIENT DB HELPERS ───────────────────────────────

def _fetch_visit_and_patient(visit_id_pk: int) -> dict:
    sess = get_session()
    try:
        v = sess.query(Visit).filter(Visit.id == int(visit_id_pk)).first()
        if not v:
            return {}
        p = None
        if v.patient_id:
            p = sess.query(Patient).filter(Patient.id == int(v.patient_id)).first()
        dob = p.dob if p else None
        return {
            "visit_pk":            v.id,
            "visit_id":            v.visit_id            or "",
            "visit_date":          v.visit_date,
            "doctor":              v.doctor               or "",
            "department":          v.department           or "",
            "clinical_notes":      v.clinical_notes       or "",
            "patient_pk":          p.id                   if p else None,
            "patient_pid":         p.patient_id           or "" if p else "",
            "first_name":          p.first_name           or "" if p else "",
            "last_name":           p.last_name            or "" if p else "",
            "dob":                 dob,
            "gender":              p.gender               or "" if p else "",
            "phone":               p.phone                or "" if p else "",
            "email":               p.email_id             or "" if p else "",
            "address":             p.address              or "" if p else "",
            "ref_doc":             p.ref_doc              or "" if p else "",
            "blood_group":         p.blood_group          or "" if p else "",
            "current_medication":  p.current_medication   or "" if p else "",
            "existing_medical":    p.existing_medical     or "" if p else "",
            "past_medical_history":p.past_medical_history or "" if p else "",
            "allergies":           p.allergies            or "" if p else "",
        }
    except Exception as ex:
        import traceback; traceback.print_exc()
        return {}
    finally:
        sess.close()


def _fetch_images(visit_id_pk: int) -> list:
    sess = get_session()
    try:
        rows = (sess.query(CapturedImage)
                .filter(CapturedImage.visit_id == int(visit_id_pk),
                        CapturedImage.is_deleted != True)
                .order_by(CapturedImage.sort_order).all())
        return [{"id": r.id, "file_path": r.file_path or "",
                 "annotated_path": r.annotated_path or "",
                 "selected": bool(r.selected_for_report),
                 "captured_at": r.captured_at} for r in rows]
    finally:
        sess.close()


def _set_selected(img_id: int, selected: bool):
    sess = get_session()
    try:
        r = sess.query(CapturedImage).filter(CapturedImage.id == img_id).first()
        if r:
            r.selected_for_report = selected; sess.commit()
    finally:
        sess.close()


def _select_all_images(visit_id_pk: int):
    sess = get_session()
    try:
        rows = sess.query(CapturedImage).filter(
            CapturedImage.visit_id == int(visit_id_pk),
            CapturedImage.is_deleted != True).all()
        for r in rows:
            r.selected_for_report = True
        sess.commit()
    finally:
        sess.close()


# ─── IMAGE THUMBNAIL CARD ─────────────────────────────────────

class ImageSelectCard(QFrame):
    def __init__(self, img: dict, on_toggle):
        super().__init__()
        self.img_id = img["id"]
        sel = img["selected"]
        self.setFixedSize(164, 200)
        self.setStyleSheet(
            f"QFrame{{background:white;border-radius:10px;"
            f"border:2px solid {C['red'] if sel else C['border']};}}"
        )
        lay = QVBoxLayout(self); lay.setContentsMargins(6, 6, 6, 6); lay.setSpacing(4)

        thumb = QLabel(); thumb.setFixedSize(150, 116)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet("background:#1a1a1a;border-radius:6px;")
        path = img["annotated_path"] or img["file_path"]
        if path and os.path.exists(path):
            pix = QPixmap(path).scaled(150, 116,
                  Qt.AspectRatioMode.KeepAspectRatio,
                  Qt.TransformationMode.SmoothTransformation)
            thumb.setPixmap(pix)
        lay.addWidget(thumb)

        fn = QLabel(os.path.basename(img["file_path"]))
        fn.setStyleSheet(f"color:{C['text3']};font-size:9px;background:transparent;")
        fn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fn.setWordWrap(True); lay.addWidget(fn)

        if img["annotated_path"]:
            ab = QLabel("Annotated")
            ab.setStyleSheet(f"color:{C['red']};font-size:9px;font-weight:bold;background:transparent;")
            ab.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(ab)

        cb = QCheckBox("Include in report")
        cb.setChecked(sel)
        cb.setStyleSheet(f"color:{C['text2']};font-size:10px;background:transparent;")
        cb.toggled.connect(lambda s, iid=img["id"]: on_toggle(iid, s))
        lay.addWidget(cb)


# ─── SECTION HEADER WIDGET ────────────────────────────────────

def _sec(txt):
    f = QFrame(); f.setFixedHeight(36)
    f.setStyleSheet(f"QFrame{{background:{DARK_RED};border-radius:6px;}}")
    ll = QHBoxLayout(f); ll.setContentsMargins(0, 0, 0, 0)
    lb = QLabel(txt)
    lb.setStyleSheet("color:white;font-size:13px;font-weight:bold;"
                     "background:transparent;padding:0 14px;")
    ll.addWidget(lb); return f


def _field(ph, fixed_h=42):
    f = QLineEdit(); f.setPlaceholderText(ph)
    f.setFixedHeight(fixed_h); f.setStyleSheet(FIELD)
    return f


def _lbl(txt):
    l = QLabel(txt)
    l.setStyleSheet(f"color:{C['text2']};font-size:11px;background:transparent;")
    return l


# ─── MAIN PAGE ────────────────────────────────────────────────

class ReportPage(QWidget):
    def __init__(self, shell, visit_id_pk: int):
        super().__init__()
        self.shell = shell
        self.vpk  = int(visit_id_pk)
        self.data = _fetch_visit_and_patient(self.vpk)

        name = (f"{self.data.get('first_name','')} "
                f"{self.data.get('last_name','')}").strip() or "—"
        vid  = self.data.get("visit_id") or "—"

        self.setStyleSheet(f"QWidget{{background:{BG};font-family:'Segoe UI';}}")

        self._build_ui(name, vid)
        self._load_image_grid()
        self._restore_all()

    # ── Toolbar ───────────────────────────────────────────────
    def _build_toolbar(self, name, vid):
        bar = QFrame(); bar.setFixedHeight(56)
        bar.setStyleSheet(f"QFrame{{background:{C['red']};}}")
        lay = QHBoxLayout(bar); lay.setContentsMargins(14, 0, 14, 0); lay.setSpacing(8)

        bk = QPushButton("←"); bk.setFixedSize(36, 36)
        bk.setStyleSheet("QPushButton{background:transparent;color:white;border:none;"
                         "font-size:18px;border-radius:4px;}"
                         "QPushButton:hover{background:rgba(255,255,255,0.18);}")
        bk.clicked.connect(self._go_back); lay.addWidget(bk)

        t = QLabel(f"Report — {name}  ·  {vid}")
        t.setStyleSheet("color:white;font-size:14px;font-weight:bold;background:transparent;")
        lay.addWidget(t); lay.addStretch()

        u = QLabel(UserSession.username())
        u.setStyleSheet("color:white;font-size:12px;background:transparent;")
        lay.addWidget(u)
        lo = QPushButton("Logout"); lo.setFixedHeight(34)
        lo.setStyleSheet("QPushButton{background:transparent;color:white;border:1px solid "
                         "rgba(255,255,255,0.4);border-radius:6px;font-size:12px;padding:0 12px;}"
                         "QPushButton:hover{background:rgba(255,255,255,0.18);}")
        lo.clicked.connect(self._logout); lay.addWidget(lo)
        return bar

    # ── Full UI ───────────────────────────────────────────────
    def _build_ui(self, name, vid):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(self._build_toolbar(name, vid))
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_page0())   # image selection
        self.stack.addWidget(self._build_page1())   # report editor
        root.addWidget(self.stack, stretch=1)

    # ── Page 0: image selection ───────────────────────────────
    def _build_page0(self):
        page = QWidget(); page.setStyleSheet(f"background:{BG};")
        pl = QVBoxLayout(page); pl.setContentsMargins(28, 20, 28, 20); pl.setSpacing(14)

        hrow = QHBoxLayout()
        t = QLabel("Select Images for Report")
        t.setFont(QFont("Georgia", 15, QFont.Weight.Bold))
        t.setStyleSheet(f"color:{C['text']};background:transparent;")
        hrow.addWidget(t); hrow.addStretch()

        self._sel_lbl = QLabel("0 selected")
        self._sel_lbl.setStyleSheet(f"color:{C['text3']};font-size:12px;background:transparent;")
        hrow.addWidget(self._sel_lbl)

        sa = QPushButton("Select All"); sa.setFixedHeight(32)
        sa.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        sa.setStyleSheet(f"QPushButton{{background:transparent;color:{C['red']};"
                         f"border:1.5px solid {C['red']};border-radius:8px;"
                         f"font-size:11px;padding:0 14px;}}"
                         f"QPushButton:hover{{background:{C['red_light']};}}")
        sa.clicked.connect(self._select_all); hrow.addWidget(sa)

        nxt = QPushButton("Next: Write Report  →"); nxt.setFixedHeight(36)
        nxt.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        nxt.setStyleSheet(f"QPushButton{{background:{C['red']};color:white;border:none;"
                          f"border-radius:9px;font-size:12px;font-weight:bold;padding:0 20px;}}"
                          f"QPushButton:hover{{background:{C['red_dark']};}}")
        nxt.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        hrow.addWidget(nxt); pl.addLayout(hrow)

        sc = QScrollArea(); sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setStyleSheet("background:transparent;border:none;")
        self._grid_w = QWidget(); self._grid_w.setStyleSheet("background:transparent;")
        self._grid   = QGridLayout(self._grid_w)
        self._grid.setSpacing(14); self._grid.setContentsMargins(0, 0, 0, 0)
        sc.setWidget(self._grid_w); pl.addWidget(sc, stretch=1)
        return page

    def _load_image_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        imgs = _fetch_images(self.vpk)
        COLS = 5
        if imgs:
            for idx, img in enumerate(imgs):
                card = ImageSelectCard(img, self._toggle)
                self._grid.addWidget(card, idx // COLS, idx % COLS)
        else:
            lbl = QLabel("No images captured yet.")
            lbl.setStyleSheet(f"color:{C['text3']};font-size:14px;padding:40px;background:transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(lbl, 0, 0)
        self._update_sel_count()

    def _toggle(self, img_id: int, selected: bool):
        _set_selected(img_id, selected); self._update_sel_count()

    def _select_all(self):
        _select_all_images(self.vpk); self._load_image_grid()

    def _update_sel_count(self):
        sess = get_session()
        try:
            n = sess.query(CapturedImage).filter(
                CapturedImage.visit_id == self.vpk,
                CapturedImage.is_deleted != True,
                CapturedImage.selected_for_report == True).count()
        finally:
            sess.close()
        self._sel_lbl.setText(f"{n} image{'s' if n != 1 else ''} selected")

    # ── Page 1: report editor ─────────────────────────────────
    def _build_page1(self):
        page = QWidget(); page.setStyleSheet(f"background:{BG};")
        pl = QVBoxLayout(page); pl.setContentsMargins(0, 0, 0, 0); pl.setSpacing(0)

        # Sub-toolbar
        stb = QFrame(); stb.setFixedHeight(52)
        stb.setStyleSheet(f"QFrame{{background:{DARK_RED};}}")
        stl = QHBoxLayout(stb); stl.setContentsMargins(14, 0, 14, 0); stl.setSpacing(8)
        bk = QPushButton("← Image Selection")
        bk.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:13px;}"
                         "QPushButton:hover{text-decoration:underline;}")
        bk.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        stl.addWidget(bk); stl.addStretch()

        for lbl, fn, bg in [
            ("Save Draft",   self._save_draft,   "rgba(255,255,255,0.15)"),
            ("Export PDF",   self._do_pdf,       "rgba(255,255,255,0.15)"),
            ("Print",        self._do_print,     "rgba(255,255,255,0.15)"),
            ("Export DICOM", self._do_dicom,     "white"),
        ]:
            fc = "white" if bg != "white" else "#831316"
            b = QPushButton(lbl); b.setFixedHeight(36)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setStyleSheet(f"QPushButton{{background:{bg};color:{fc};border:none;"
                            f"border-radius:6px;font-size:12px;font-weight:bold;padding:0 16px;}}")
            b.clicked.connect(fn); stl.addWidget(b)
        pl.addWidget(stb)

        # Scrollable form
        sc = QScrollArea(); sc.setWidgetResizable(True)
        sc.setStyleSheet(f"QScrollArea{{border:none;background:{BG};}}")
        body = QWidget(); body.setStyleSheet(f"background:{BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(32, 24, 32, 32); bl.setSpacing(16)

        # ── 1. Hospital Profile (GLOBAL — saved once, locked after save) ──
        hosp_sec_row = QHBoxLayout()
        hosp_sec_row.addWidget(_sec("Hospital / Institution Profile"))
        hosp_sec_row.addStretch()
        self._hosp_saved_lbl = QLabel("")
        self._hosp_saved_lbl.setStyleSheet(
            f"color:#15803D;font-size:11px;font-weight:bold;background:transparent;")
        hosp_sec_row.addWidget(self._hosp_saved_lbl)
        # Edit / unlock button — hidden until profile is saved
        self._edit_hosp_btn = QPushButton("Edit Profile")
        self._edit_hosp_btn.setFixedHeight(32)
        self._edit_hosp_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._edit_hosp_btn.setStyleSheet(
            f"QPushButton{{background:{C['bg2']};color:{C['text2']};border:1px solid {C['border']};"
            f"border-radius:7px;font-size:11px;font-weight:bold;padding:0 14px;}}"
            f"QPushButton:hover{{background:{C['border2']};}}")
        self._edit_hosp_btn.setVisible(False)
        self._edit_hosp_btn.clicked.connect(self._unlock_hospital_profile)
        hosp_sec_row.addWidget(self._edit_hosp_btn)
        hosp_sec_row.setSpacing(10)
        bl.addLayout(hosp_sec_row)

        # All hospital fields — wrapped in a card widget so we can show/hide together
        self._hosp_card = QFrame()
        self._hosp_card.setStyleSheet(
            f"QFrame{{background:{C['white']};border:1px solid {C['border']};"
            f"border-radius:12px;border-left:4px solid {C['red']};}}")
        hc_lay = QVBoxLayout(self._hosp_card)
        hc_lay.setContentsMargins(20, 16, 20, 16); hc_lay.setSpacing(10)

        # Name row
        hc_lay.addWidget(_lbl("Hospital / Institution Name *"))
        self.f_hosp = _field("e.g. City Eye & General Hospital")
        hc_lay.addWidget(self.f_hosp)

        # Email + Phone row
        ep_grid = QGridLayout(); ep_grid.setSpacing(8); ep_grid.setHorizontalSpacing(16)
        self.f_hosp_email = _field("Hospital Email  (e.g. info@hospital.com)")
        self.f_hosp_phone = _field("Hospital Phone  (e.g. +91 22 1234 5678)")
        ep_grid.addWidget(_lbl("Email"), 0, 0); ep_grid.addWidget(self.f_hosp_email, 1, 0)
        ep_grid.addWidget(_lbl("Phone"), 0, 1); ep_grid.addWidget(self.f_hosp_phone, 1, 1)
        hc_lay.addLayout(ep_grid)

        # Address
        hc_lay.addWidget(_lbl("Full Address  (each line will appear separately on report)"))
        self.f_hosp_addr = QTextEdit()
        self.f_hosp_addr.setPlaceholderText(
            "Street / Building Name\nCity, State – PIN\n")
        self.f_hosp_addr.setFixedHeight(72); self.f_hosp_addr.setStyleSheet(FIELD)
        hc_lay.addWidget(self.f_hosp_addr)

        # Logo picker
        hc_lay.addWidget(_lbl("Hospital Logo  (PNG / JPG — shown on report header)"))
        logo_row = QHBoxLayout(); logo_row.setSpacing(8)
        self.f_logo_path = _field("No logo selected")
        self.f_logo_path.setReadOnly(True)
        self._pick_logo_btn = QPushButton("Browse...")
        self._pick_logo_btn.setFixedHeight(42)
        self._pick_logo_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._pick_logo_btn.setStyleSheet(
            f"QPushButton{{background:{C['bg2']};color:{C['text2']};"
            f"border:1px solid {C['border']};border-radius:8px;"
            f"font-size:11px;padding:0 14px;}}"
            f"QPushButton:hover{{background:{C['border2']};}}")
        self._pick_logo_btn.clicked.connect(self._pick_logo)
        logo_row.addWidget(self.f_logo_path, stretch=1)
        logo_row.addWidget(self._pick_logo_btn)
        hc_lay.addLayout(logo_row)

        # Save & Lock button
        save_hosp = QPushButton("Save & Lock Hospital Profile")
        save_hosp.setFixedHeight(38)
        save_hosp.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_hosp.setStyleSheet(
            f"QPushButton{{background:{C['red']};color:white;border:none;"
            f"border-radius:9px;font-size:12px;font-weight:bold;padding:0 20px;}}"
            f"QPushButton:hover{{background:{C['red_dark']};}}")
        save_hosp.clicked.connect(self._save_and_lock_hospital)
        hc_lay.addWidget(save_hosp, alignment=Qt.AlignmentFlag.AlignRight)

        # Locked display card — shown when profile is saved and fields are locked
        self._hosp_locked_card = QFrame()
        self._hosp_locked_card.setStyleSheet(
            f"QFrame{{background:#F0FDF4;border:1.5px solid #86EFAC;"
            f"border-radius:12px;border-left:4px solid #15803D;}}")
        hlc_lay = QVBoxLayout(self._hosp_locked_card)
        hlc_lay.setContentsMargins(20, 14, 20, 14); hlc_lay.setSpacing(4)
        self._hosp_lock_name  = QLabel("")
        self._hosp_lock_name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._hosp_lock_name.setStyleSheet("color:#991B1B;background:transparent;")
        self._hosp_lock_sub   = QLabel("")
        self._hosp_lock_sub.setFont(QFont("Segoe UI", 10))
        self._hosp_lock_sub.setStyleSheet(f"color:{C['text2']};background:transparent;")
        self._hosp_lock_addr  = QLabel("")
        self._hosp_lock_addr.setFont(QFont("Segoe UI", 10))
        self._hosp_lock_addr.setStyleSheet(f"color:{C['text3']};background:transparent;")
        hlc_lay.addWidget(self._hosp_lock_name)
        hlc_lay.addWidget(self._hosp_lock_sub)
        hlc_lay.addWidget(self._hosp_lock_addr)
        self._hosp_locked_card.setVisible(False)

        bl.addWidget(self._hosp_card)
        bl.addWidget(self._hosp_locked_card)

        # ── 2. Patient & Visit Info (read-only, from DB) ──────
        bl.addWidget(_sec("Patient & Visit Information"))
        d = self.data

        def val(k, fallback="—"):
            v = d.get(k)
            return str(v).strip() if v and str(v).strip() else fallback

        dob_str = d["dob"].strftime("%d %b %Y") if d.get("dob") else "—"
        vd_str  = d["visit_date"].strftime("%d %b %Y  %H:%M") if d.get("visit_date") else "—"
        name    = f"{val('first_name','')} {val('last_name','')}".strip() or "—"

        info_grid = QGridLayout(); info_grid.setSpacing(8); info_grid.setHorizontalSpacing(24)
        pairs = [
            ("Patient Name",   name),     ("Date of Birth", dob_str),
            ("Gender",         val("gender")),  ("Phone",   val("phone")),
            ("Referring Doctor", val("ref_doc")), ("Address", val("address")),
        ]
        for i, (lbl_txt, lbl_val) in enumerate(pairs):
            r, c = divmod(i, 2)
            base_c = c * 2
            ll = QLabel(lbl_txt)
            ll.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            ll.setStyleSheet(f"color:{C['text3']};background:transparent;")
            vv = QLabel(lbl_val)
            vv.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
            vv.setStyleSheet(f"color:{C['red']};background:transparent;")
            vv.setWordWrap(True)
            info_grid.addWidget(ll, r * 2,     base_c)
            info_grid.addWidget(vv, r * 2 + 1, base_c)

        info_card = QFrame()
        info_card.setStyleSheet(f"QFrame{{background:{C['white']};border-radius:12px;"
                                f"border:1px solid {C['border']};border-left:4px solid {C['red']};}}")
        ic_lay = QVBoxLayout(info_card); ic_lay.setContentsMargins(20, 16, 20, 16)
        ic_lay.addLayout(info_grid)

        bl.addWidget(info_card)

        # ── 3. Reporting Doctor / Department ─────────────────
        bl.addWidget(_sec("Reporting Details"))
        rd_grid = QGridLayout(); rd_grid.setSpacing(10); rd_grid.setHorizontalSpacing(18)
        self.f_doctor = _field("Reporting Doctor Name")
        self.f_dept   = _field("Department / Specialisation")
        self.f_sig    = _field("Signature Line  (e.g. Dr. Name · MBBS · Reg. No.)")
        for lbl_txt, wid, r, c in [
            ("Reporting Doctor",  self.f_doctor, 0, 0),
            ("Department",        self.f_dept,   0, 1),
        ]:
            rd_grid.addWidget(_lbl(lbl_txt), r * 2,     c)
            rd_grid.addWidget(wid,           r * 2 + 1, c)
        bl.addLayout(rd_grid)
        bl.addWidget(_lbl("Doctor Signature Line"))
        bl.addWidget(self.f_sig)

        # Pre-fill doctor/dept from visit
        self.f_doctor.setText(d.get("doctor", ""))
        self.f_dept.setText(d.get("department", ""))

        # ── 4. Observations & Diagnosis ───────────────────────
        bl.addWidget(_sec("Observations"))
        self.f_obs = QTextEdit()
        self.f_obs.setPlaceholderText("Write your clinical observations…")
        self.f_obs.setFixedHeight(120); self.f_obs.setStyleSheet(FIELD)
        if d.get("clinical_notes"):
            self.f_obs.setPlainText(d["clinical_notes"])
        bl.addWidget(self.f_obs)

        bl.addWidget(_sec("Diagnosis"))
        self.f_diag = QTextEdit()
        self.f_diag.setPlaceholderText("Write diagnosis / impression…")
        self.f_diag.setFixedHeight(100); self.f_diag.setStyleSheet(FIELD)
        bl.addWidget(self.f_diag)

        # ── 5. Visit Notes ────────────────────────────────────
        bl.addWidget(_sec("Visit Notes"))
        self.f_notes = QTextEdit()
        self.f_notes.setPlaceholderText("Additional visit notes…")
        self.f_notes.setFixedHeight(80); self.f_notes.setStyleSheet(FIELD)
        bl.addWidget(self.f_notes)

        bl.addStretch()
        sc.setWidget(body); pl.addWidget(sc, stretch=1)
        return page

    # ── Restore saved data on open ────────────────────────────
    def _restore_all(self):
        # 1. Hospital profile (global) — lock if already saved
        h = _load_hospital_profile()
        self.f_hosp.setText(h["name"])
        self.f_hosp_email.setText(h["email"])
        self.f_hosp_phone.setText(h["phone"])
        self.f_hosp_addr.setPlainText(h["address"])
        self.f_logo_path.setText(h["logo_path"])
        if h["name"]:
            self._apply_hospital_lock(h)   # lock immediately if profile exists

        # 2. Per-visit draft
        saved = _load_saved_report(self.vpk)
        if saved.get("observations"): self.f_obs.setPlainText(saved["observations"])
        if saved.get("diagnosis"):    self.f_diag.setPlainText(saved["diagnosis"])
        if saved.get("doctor"):       self.f_doctor.setText(saved["doctor"])
        if saved.get("department"):   self.f_dept.setText(saved["department"])
        if saved.get("signature"):    self.f_sig.setText(saved["signature"])
        if saved.get("notes"):        self.f_notes.setPlainText(saved["notes"])

    def _apply_hospital_lock(self, h: dict):
        """Switch to locked view — hides editable card, shows read-only summary."""
        # Update locked display
        self._hosp_lock_name.setText(h["name"])
        parts = []
        if h["phone"]: parts.append(h["phone"])
        if h["email"]: parts.append(h["email"])
        self._hosp_lock_sub.setText("  ·  ".join(parts) if parts else "")
        addr_preview = h["address"].replace("\n", "   ·   ").strip()
        logo_info = f"   Logo: {os.path.basename(h['logo_path'])}" if h.get("logo_path") else ""
        self._hosp_lock_addr.setText(addr_preview + logo_info)
        # Toggle visibility
        self._hosp_card.setVisible(False)
        self._hosp_locked_card.setVisible(True)
        self._hosp_saved_lbl.setText("Profile saved")
        self._edit_hosp_btn.setVisible(True)

    def _unlock_hospital_profile(self):
        """Show editable card again for changes."""
        self._hosp_card.setVisible(True)
        self._hosp_locked_card.setVisible(False)
        self._hosp_saved_lbl.setText("Editing...")
        self._edit_hosp_btn.setVisible(False)

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Hospital Logo",
            "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.f_logo_path.setText(path)

    def _save_and_lock_hospital(self):
        name = self.f_hosp.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Please enter the hospital name.")
            return
        h = {
            "name":      name,
            "address":   self.f_hosp_addr.toPlainText().strip(),
            "email":     self.f_hosp_email.text().strip(),
            "phone":     self.f_hosp_phone.text().strip(),
            "logo_path": self.f_logo_path.text().strip(),
        }
        _save_hospital_profile(h)
        self._apply_hospital_lock(h)
        QMessageBox.information(
            self, "Hospital Profile Locked",
            f'Profile for {name!r} has been saved.\n\n'
            "It will appear on every report automatically.\n"
            "Click 'Edit Profile' to make changes.")

    # keep old name as alias so nothing else breaks
    def _save_hospital_profile(self):
        self._save_and_lock_hospital()

    # ── Save per-visit draft ──────────────────────────────────
    def _collect_draft_fields(self) -> dict:
        return {
            "observations": self.f_obs.toPlainText().strip(),
            "diagnosis":    self.f_diag.toPlainText().strip(),
            "doctor":       self.f_doctor.text().strip(),
            "department":   self.f_dept.text().strip(),
            "signature":    self.f_sig.text().strip(),
            "notes":        self.f_notes.toPlainText().strip(),
        }

    def _save_draft(self):
        _upsert_saved_report(self.vpk, self._collect_draft_fields())
        QMessageBox.information(self, "Draft Saved",
                                "Report draft saved. Reopen the visit to continue editing.")

    def _save_draft_silent(self):
        _upsert_saved_report(self.vpk, self._collect_draft_fields())

    # ── Build PDF using ReportLab generator ──────────────────
    def _selected_image_paths(self) -> list:
        sess = get_session()
        try:
            rows = (sess.query(CapturedImage)
                    .filter(CapturedImage.visit_id == self.vpk,
                            CapturedImage.is_deleted != True,
                            CapturedImage.selected_for_report == True)
                    .order_by(CapturedImage.sort_order).all())
            return [r.annotated_path or r.file_path for r in rows
                    if (r.annotated_path or r.file_path)]
        finally:
            sess.close()

    def _build_report_data(self) -> dict:
        d  = self.data
        h  = _load_hospital_profile()

        def v(k, fb="—"):
            val = d.get(k)
            return str(val).strip() if val and str(val).strip() else fb

        dob_str = d["dob"].strftime("%d %b %Y") if d.get("dob") else "—"

        addr_lines = []
        if h["address"]:
            addr_lines = [ln.strip() for ln in h["address"].splitlines() if ln.strip()]
        if h["email"] or h["phone"]:
            contact = "  |  ".join(x for x in [h["phone"], h["email"]] if x)
            addr_lines.append(contact)

        return {
            "report_id": f"RPT-{d.get('visit_id','000')}",
            "hospital": {
                "name":      h["name"] or "Pixel Pro Medical",
                "address":   addr_lines or [""],
                "logo_path": h["logo_path"] if h["logo_path"] and os.path.exists(h["logo_path"]) else None,
            },
            "patient": {
                "first_name": v("first_name"),
                "last_name":  v("last_name"),
                "gender":     v("gender"),
                "dob":        dob_str,
                "phone":      v("phone"),
                "email":      v("email"),
                "address":    v("address"),
            },
            "medical": {
                "current_medications": v("current_medication"),
                "existing_medical":    v("existing_medical"),
                "past_history":        v("past_medical_history"),
                "allergies":           v("allergies"),
                "referring_doctor":    v("ref_doc"),
            },
            "images":       self._selected_image_paths(),
            "observations": self.f_obs.toPlainText().strip() or None,
            "diagnosis":    self.f_diag.toPlainText().strip() or None,
            "visit_notes":  self.f_notes.toPlainText().strip() or None,
            "reporting_doctor": self.f_doctor.text().strip() or v("doctor"),
            "department":       self.f_dept.text().strip() or v("department"),
            "signature":        self.f_sig.text().strip(),
        }

    def _do_pdf(self):
        vid  = self.data.get("visit_id", "RPT")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF",
            f"Report_{vid}_{datetime.now().strftime('%Y%m%d')}.pdf",
            "PDF Files (*.pdf)")
        if not path: return

        try:
            from ui.pixel_pro_report_generator import build_report
            build_report(path, self._build_report_data())
            self._save_draft_silent()
            QMessageBox.information(self, "PDF Saved", f"Report saved to:\n{path}")
        except ImportError:
            # Fallback: Qt-based HTML→PDF
            self._do_pdf_fallback(path)

    def _do_pdf_fallback(self, path):
        """Qt QPrinter fallback when reportlab is unavailable."""
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QTextDocument
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self._build_html_fallback())
            doc.setPageSize(QSizeF(printer.pageRect(printer.Unit.DevicePixel).size()))
            doc.print(printer)
            self._save_draft_silent()
            QMessageBox.information(self, "PDF Saved", f"Saved to:\n{path}\n\n(Install reportlab for full-quality output)")
        except Exception as ex:
            QMessageBox.critical(self, "Export Error", str(ex))

    def _build_html_fallback(self) -> str:
        """Simple HTML fallback used when reportlab is not installed."""
        d    = self.data
        h    = _load_hospital_profile()
        def e(val):
            if not val or str(val).strip() in ("", "None", "—"): return "—"
            return str(val).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        name = f"{d.get('first_name','')} {d.get('last_name','')}".strip()
        dob  = d["dob"].strftime("%d %b %Y") if d.get("dob") else "—"
        vd   = d["visit_date"].strftime("%d %b %Y  %H:%M") if d.get("visit_date") else "—"
        obs  = self.f_obs.toPlainText().strip() or "—"
        diag = self.f_diag.toPlainText().strip() or "—"
        hosp = h["name"] or "Medical Report"
        addr = h["address"].replace("\n", "<br/>") if h["address"] else ""
        def r2(l1,v1,l2,v2):
            s="style='color:#555;font-size:10pt;padding:4px 8px 4px 0;width:130px;'"
            b="style='font-size:10pt;font-weight:bold;padding:4px 8px 4px 0;'"
            return f"<tr><td {s}>{l1}</td><td {b}>{e(v1)}</td><td {s}>{l2}</td><td {b}>{e(v2)}</td></tr>"
        return f"""<html><body style='font-family:Arial;font-size:10pt;'>
<table width='100%' style='border-bottom:3px solid #B91C1C;margin-bottom:10px;'>
<tr><td><b style='font-size:18pt;color:#B91C1C;'>{e(hosp)}</b><br/>
<span style='color:#666;font-size:9pt;'>{addr}<br/>{e(h.get('email',''))}  {e(h.get('phone',''))}</span></td>
<td align='right' style='color:#999;font-size:9pt;'>{datetime.now().strftime('%d %b %Y')}</td></tr></table>
<p style='background:#991B1B;color:white;padding:5px 10px;font-weight:bold;'>PATIENT INFORMATION</p>
<table width='100%' style='border:1px solid #ddd;padding:8px;margin-bottom:10px;'>
{r2("Patient Name", name, "Date of Birth", dob)}
{r2("Gender", d.get("gender"), "Phone", d.get("phone"))}
{r2("Referring Doctor", d.get("ref_doc"), "Address", d.get("address"))}
</table>
<p style='background:#991B1B;color:white;padding:5px 10px;font-weight:bold;'>OBSERVATIONS</p>
<p style='border:1px solid #ddd;padding:8px;white-space:pre-wrap;'>{e(obs)}</p>
<p style='background:#991B1B;color:white;padding:5px 10px;font-weight:bold;'>DIAGNOSIS</p>
<p style='border:1px solid #ddd;padding:8px;white-space:pre-wrap;'>{e(diag)}</p>
<hr style='border:1px solid #B91C1C;margin:14px 0 6px 0;'/>
<table width='100%'><tr>
<td style='font-size:10pt;'><b>Reporting Doctor:</b> {e(self.f_sig.text() or self.f_doctor.text())}</td>
<td align='right' style='font-size:9pt;color:#999;'>Generated: {datetime.now().strftime('%d %b %Y  %H:%M')}</td>
</tr></table></body></html>"""

    def _do_print(self):
        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt6.QtGui import QTextDocument
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            if QPrintDialog(printer, self).exec():
                doc = QTextDocument()
                doc.setHtml(self._build_html_fallback())
                doc.setPageSize(QSizeF(printer.pageRect(printer.Unit.DevicePixel).size()))
                doc.print(printer)
        except Exception as ex:
            QMessageBox.critical(self, "Print Error", str(ex))

    def _do_dicom(self):
        imgs = self._selected_image_paths()
        if not imgs:
            QMessageBox.warning(self, "No Images", "Select at least one image first.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Select DICOM Output Folder")
        if not folder: return
        try:
            import pydicom
            from pydicom.dataset import Dataset, FileDataset
            from pydicom.uid import generate_uid
            import numpy as np
            from PIL import Image as PILImage
            self._dicom_real(imgs, folder)
        except ImportError:
            self._dicom_placeholder(imgs, folder)

    def _dicom_real(self, imgs, folder):
        import pydicom
        from pydicom.dataset import Dataset, FileDataset
        from pydicom.uid import generate_uid
        import numpy as np
        from PIL import Image as PILImage

        d    = self.data
        sess = get_session()
        cfg  = sess.query(PACSConfig).first(); sess.close()
        h    = _load_hospital_profile()
        inst = h["name"] or (cfg.institution if cfg else "") or "Pixel Pro"
        study_uid = generate_uid()

        prog = QProgressDialog("Exporting DICOM…", "Cancel", 0, len(imgs), self)
        prog.setWindowTitle("DICOM Export"); prog.show()
        exported = []

        for idx, path in enumerate(imgs):
            prog.setValue(idx)
            if prog.wasCanceled(): break
            if not path or not os.path.exists(path): continue
            arr = np.array(PILImage.open(path).convert("RGB"), dtype=np.uint8)
            ds  = FileDataset(None, {}, is_implicit_VR=False, is_little_endian=True)
            ds.file_meta = Dataset()
            ds.file_meta.MediaStorageSOPClassUID    = "1.2.840.10008.5.1.4.1.1.1"
            ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
            ds.file_meta.TransferSyntaxUID          = pydicom.uid.ExplicitVRLittleEndian
            ds.PatientName = f"{d.get('last_name','')}^{d.get('first_name','')}"
            ds.PatientID   = d.get("patient_pid", "—")
            dob = d.get("dob")
            ds.PatientBirthDate = dob.strftime("%Y%m%d") if dob else ""
            ds.PatientSex = (d.get("gender", "") or "")[:1].upper()
            ds.StudyInstanceUID = study_uid
            ds.StudyID   = d.get("visit_id", "—")
            vdate = d.get("visit_date") or datetime.now()
            ds.StudyDate = vdate.strftime("%Y%m%d")
            ds.StudyTime = vdate.strftime("%H%M%S")
            ds.ReferringPhysicianName = d.get("doctor", "")
            ds.InstitutionName = inst
            ds.Modality = (cfg.modality if cfg else "ES") or "ES"
            ds.SeriesInstanceUID = generate_uid()
            ds.SOPClassUID    = ds.file_meta.MediaStorageSOPClassUID
            ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
            ds.InstanceNumber = str(idx + 1)
            ds.Rows, ds.Columns = arr.shape[0], arr.shape[1]
            ds.SamplesPerPixel = 3
            ds.PhotometricInterpretation = "RGB"
            ds.BitsAllocated = ds.BitsStored = 8
            ds.HighBit = 7; ds.PixelRepresentation = 0; ds.PlanarConfiguration = 0
            ds.PixelData = arr.tobytes()
            out = os.path.join(folder, f"{d.get('visit_id','VS')}_img{idx+1:03d}.dcm")
            pydicom.dcmwrite(out, ds)
            exported.append(out)

        prog.setValue(len(imgs))
        QMessageBox.information(self, "DICOM Export Complete",
                                f"{len(exported)} file(s) exported to:\n{folder}")

    def _dicom_placeholder(self, imgs, folder):
        d = self.data
        out = os.path.join(folder, f"DICOM_manifest_{d.get('visit_id','VS')}.json")
        with open(out, "w") as f:
            json.dump({"note": "pip install pydicom pillow numpy for real DICOM",
                       "PatientName": f"{d.get('first_name','')} {d.get('last_name','')}",
                       "Images": [{"index": i+1, "file": p} for i, p in enumerate(imgs)]}, f, indent=2)
        QMessageBox.information(self, "pydicom Not Installed",
                                f"Manifest saved:\n{out}\n\nInstall: pip install pydicom pillow numpy")

    # ── Navigation ────────────────────────────────────────────
    def _go_back(self):
        self._save_draft_silent()
        pid = self.data.get("patient_pk")
        if pid:
            self.shell.navigate("visits", patient_id=pid)
        else:
            self.shell.navigate("dashboard")

    def _logout(self):
        self._save_draft_silent()
        UserSession.end()
        from ui.login_window import LoginWindow
        self.shell.navigate("login")
