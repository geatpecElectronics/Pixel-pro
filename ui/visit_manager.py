# =============================================================
#  ui/visit_manager.py  — Visit Manager page (QWidget)
# =============================================================
import os
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QLineEdit, QTextEdit,
    QMessageBox, QStackedWidget, QGridLayout,
    QGraphicsDropShadowEffect, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (QFont, QColor, QPainter, QPainterPath,
    QLinearGradient, QBrush, QPen, QCursor)
from ui._styles import FIELD, DARK_RED, RED
from models.database import (get_session, Patient, Visit, CapturedImage, gen_visit_id)
from utils.session import UserSession

C = {
    "red":"#B91C1C","red_dark":"#991B1B","red_bright":"#DC2626",
    "red_light":"#FEE2E2","red_pale":"#FFF5F5","bg":"#F7F4F0","bg2":"#EFECE8",
    "white":"#FFFFFF","border":"#E8E3DC","border2":"#D6CFC5",
    "text":"#1C1410","text2":"#6B5E52","text3":"#A8998C",
    "blue":"#1D4ED8","blue_light":"#DBEAFE","green":"#15803D","green_light":"#DCFCE7",
    "amber":"#B45309","amber_light":"#FEF3C7",
}
STATUS_COLORS = {
    "Active":    (C["green"],  C["green_light"]),
    "Review":    (C["blue"],   C["blue_light"]),
    "Pending":   (C["amber"],  C["amber_light"]),
    "Completed": (C["text3"],  C["bg2"]),
}

def _shadow(w, blur=16, offset=(0,4), color=(28,20,16,18)):
    eff = QGraphicsDropShadowEffect(w)
    eff.setBlurRadius(blur); eff.setOffset(offset[0],offset[1]); eff.setColor(QColor(*color))
    w.setGraphicsEffect(eff)

def _load_patient(patient_id):
    sess = get_session()
    p = sess.query(Patient).filter(Patient.id==patient_id, Patient.is_deleted!=True).first()
    if not p: sess.close(); return {}
    d = {"id":p.id,"patient_id":p.patient_id or "—","first_name":p.first_name or "",
         "last_name":p.last_name or "","dob":p.dob,"gender":p.gender or "—",
         "phone":p.phone or "—","ref_doc":p.ref_doc or "—"}
    sess.close(); return d

def _load_visits(patient_id):
    from sqlalchemy.orm import joinedload
    sess = get_session()
    visits = (sess.query(Visit).options(joinedload(Visit.images))
              .filter(Visit.patient_id==patient_id, Visit.is_deleted!=True)
              .order_by(Visit.visit_date.desc()).all())
    result = []
    for v in visits:
        imgs = [i for i in (v.images or []) if not i.is_deleted]
        result.append({"id":v.id,"visit_id":v.visit_id or "—","visit_date":v.visit_date,
                       "doctor":v.doctor or "—","department":v.department or "—",
                       "clinical_notes":v.clinical_notes or "","image_count":len(imgs)})
    sess.close(); return result


# ─── Top bar ─────────────────────────────────────────────────
class _TopBar(QWidget):
    back_clicked     = pyqtSignal()
    newvisit_clicked = pyqtSignal()
    logout_clicked   = pyqtSignal()

    def __init__(self, patient_name, patient_id, username=""):
        super().__init__(); self._pname = patient_name; self._pid = patient_id
        self._uname = username or "User"; self.setFixedHeight(64)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True); self._build()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0,0,self.width(),0)
        grad.setColorAt(0,QColor("#991B1B")); grad.setColorAt(0.5,QColor("#B91C1C")); grad.setColorAt(1,QColor("#DC2626"))
        p.fillRect(self.rect(), QBrush(grad))

    def _build(self):
        lay = QHBoxLayout(self); lay.setContentsMargins(20,0,20,0); lay.setSpacing(0)
        back = QPushButton("←"); back.setFixedSize(38,38); back.setFont(QFont("Segoe UI",18))
        back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back.setStyleSheet("QPushButton{background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);border-radius:10px;color:white;}"
                           "QPushButton:hover{background:rgba(255,255,255,0.22);}")
        back.clicked.connect(self.back_clicked); lay.addWidget(back); lay.addSpacing(14)
        from ui._styles import make_logo_widget
        lay.addWidget(make_logo_widget(44)); lay.addSpacing(12)
        div = QWidget(); div.setFixedSize(1,32); div.setStyleSheet("background:rgba(255,255,255,0.28);")
        lay.addWidget(div); lay.addSpacing(14)
        bc = QLabel()
        bc.setText(f'<span style="font-family:Segoe UI;font-size:14px;color:rgba(255,255,255,0.65);">Visits\u2009\u2014\u2009</span>'
                   f'<span style="font-family:Segoe UI;font-size:14px;font-weight:600;color:white;">{self._pname}</span>'
                   f'<span style="font-family:Segoe UI;font-size:14px;color:rgba(255,255,255,0.55);">\u2009\u00b7\u2009{self._pid}</span>')
        bc.setTextFormat(Qt.TextFormat.RichText); bc.setStyleSheet("background:transparent;")
        lay.addWidget(bc); lay.addStretch()
        div2 = QWidget(); div2.setFixedSize(1,32); div2.setStyleSheet("background:rgba(255,255,255,0.28);")
        lay.addSpacing(16); lay.addWidget(div2); lay.addSpacing(16)
        nv = QPushButton("\uff0b  New Visit"); nv.setFixedHeight(36)
        nv.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        nv.setFont(QFont("Segoe UI",11,QFont.Weight.DemiBold))
        nv.setStyleSheet("QPushButton{background:white;color:#B91C1C;border:none;border-radius:9px;padding:0 18px;font-weight:600;}"
                         "QPushButton:hover{background:#FFF5F5;}")
        nv.clicked.connect(self.newvisit_clicked); lay.addWidget(nv); lay.addSpacing(12)
        ub = QPushButton(self._uname[0].upper()); ub.setFixedSize(36,36)
        ub.setFont(QFont("Segoe UI",12,QFont.Weight.Bold))
        ub.setStyleSheet("QPushButton{background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.3);border-radius:10px;color:white;}"
                         "QPushButton:hover{background:rgba(255,255,255,0.28);}")
        lay.addWidget(ub); lay.addSpacing(10)
        pw = QPushButton("\u23fb"); pw.setFixedSize(36,36); pw.setFont(QFont("Segoe UI",14))
        pw.setStyleSheet("QPushButton{background:transparent;border:1px solid transparent;border-radius:9px;color:rgba(255,255,255,0.65);}"
                         "QPushButton:hover{background:rgba(255,255,255,0.14);border-color:rgba(255,255,255,0.2);color:white;}")
        pw.clicked.connect(self.logout_clicked); lay.addWidget(pw)


# ─── Patient info banner ──────────────────────────────────────
class _PatientBanner(QWidget):
    def __init__(self, fields):
        super().__init__(); self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build(fields); _shadow(self, blur=14, offset=(0,3), color=(28,20,16,12))

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath(); path.addRoundedRect(0,0,self.width(),self.height(),16,16)
        p.fillPath(path, QColor(C["white"])); p.setPen(QPen(QColor(C["border"]),1)); p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(C["red"]))
        p.drawRoundedRect(0,18,4,self.height()-36,2,2)

    def _build(self, fields):
        lay = QHBoxLayout(self); lay.setContentsMargins(22,18,22,18); lay.setSpacing(0)
        for i,(lbl_text,val_text) in enumerate(fields):
            if i > 0:
                div = QWidget(); div.setFixedSize(1,42); div.setStyleSheet(f"background:{C['border']};")
                lay.addWidget(div); lay.addSpacing(24)
            col = QVBoxLayout(); col.setSpacing(4); col.setContentsMargins(0,0,0,0)
            lbl = QLabel(lbl_text.upper()); lbl.setFont(QFont("Courier New",8,QFont.Weight.Bold))
            lbl.setStyleSheet(f"color:{C['text3']};background:transparent;")
            val = QLabel(str(val_text)); val.setFont(QFont("Segoe UI",13,QFont.Weight.DemiBold))
            val.setStyleSheet(f"color:{C['red']};background:transparent;")
            col.addWidget(lbl); col.addWidget(val); lay.addLayout(col)
            if i < len(fields)-1: lay.addSpacing(24)
        lay.addStretch()


# ─── Visit card ───────────────────────────────────────────────
class VisitCard(QWidget):
    open_imaging = pyqtSignal(int)
    open_report  = pyqtSignal(int)

    def __init__(self, vd):
        super().__init__(); self._vd = vd; self._hovered = False; self._status = "Active"
        self.setMinimumHeight(104); self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build(vd); _shadow(self, blur=14, offset=(0,3), color=(28,20,16,10))

    def enterEvent(self,e): self._hovered=True; self.update()
    def leaveEvent(self,e): self._hovered=False; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath(); path.addRoundedRect(0,0,self.width(),self.height(),16,16)
        p.fillPath(path, QColor(C["white"]))
        sc,_ = STATUS_COLORS.get(self._status,(C["text3"],C["bg2"]))
        bc = QColor(sc) if self._hovered else QColor(C["border"])
        bc.setAlpha(255 if self._hovered else 160)
        p.setPen(QPen(bc,1.5 if self._hovered else 1)); p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(sc))
        p.drawRoundedRect(0,14,4,self.height()-28,2,2)

    def _build(self, vd):
        lay = QHBoxLayout(self); lay.setContentsMargins(22,18,20,18); lay.setSpacing(0)
        left = QVBoxLayout(); left.setSpacing(6); left.setContentsMargins(0,0,0,0)
        id_row = QHBoxLayout(); id_row.setSpacing(10)
        vid_lbl = QLabel(vd["visit_id"]); vid_lbl.setFont(QFont("Courier New",13,QFont.Weight.Bold))
        vid_lbl.setStyleSheet(f"color:{C['text']};background:transparent;"); id_row.addWidget(vid_lbl)
        sc,sbg = STATUS_COLORS.get(self._status,(C["text3"],C["bg2"]))
        pill = QLabel(self._status); pill.setFont(QFont("Segoe UI",9,QFont.Weight.Bold))
        pill.setStyleSheet(f"color:{sc};background:{sbg};border-radius:7px;padding:2px 10px;")
        id_row.addWidget(pill); id_row.addStretch(); left.addLayout(id_row)
        meta_row = QHBoxLayout(); meta_row.setSpacing(20)
        vdate = vd["visit_date"]
        date_str = vdate.strftime("%d %b %Y") if vdate else "—"
        for text in [date_str, f"Dr. {vd['doctor']}", vd["department"]]:
            m = QLabel(text); m.setFont(QFont("Segoe UI",11))
            m.setStyleSheet(f"color:{C['text2']};background:transparent;"); meta_row.addWidget(m)
        n = vd["image_count"]
        if n > 0:
            img_lbl = QLabel(f"{n} image{'s' if n != 1 else ''}")
            img_lbl.setFont(QFont("Segoe UI",11))
            img_lbl.setStyleSheet(f"color:{C['text3']};background:transparent;")
            meta_row.addWidget(img_lbl)
        meta_row.addStretch(); left.addLayout(meta_row)
        if vd["clinical_notes"]:
            notes = vd["clinical_notes"]
            nl = QLabel(notes[:80]+("…" if len(notes)>80 else ""))
            nl.setFont(QFont("Segoe UI",10))
            nl.setStyleSheet(f"color:{C['text3']};background:transparent;"); nl.setWordWrap(True)
            left.addWidget(nl)
        lay.addLayout(left); lay.addStretch()
        btn_col = QVBoxLayout(); btn_col.setSpacing(6)
        for label, sig in [("Imaging", self.open_imaging), ("Report", self.open_report)]:
            if label == "Imaging":
                sty = (f"QPushButton{{background:{C['red_light']};color:{C['red']};"
                       f"border:1px solid {C['red_light']};border-radius:8px;padding:0 12px;}}"
                       f"QPushButton:hover{{background:{C['red']};color:white;border-color:{C['red']};}}")
            else:
                sty = (f"QPushButton{{background:{C['bg2']};color:{C['text2']};"
                       f"border:1px solid {C['border']};border-radius:8px;padding:0 12px;}}"
                       f"QPushButton:hover{{background:{C['border2']};}}")
            b = QPushButton(label); b.setFixedSize(110,32)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setFont(QFont("Segoe UI",10,QFont.Weight.DemiBold)); b.setStyleSheet(sty)
            b.clicked.connect(lambda _=False, s=sig, vid=vd["id"]: s.emit(vid))
            btn_col.addWidget(b)
        lay.addLayout(btn_col)


# ─── Empty state ─────────────────────────────────────────────
class _EmptyState(QWidget):
    def __init__(self):
        super().__init__(); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QVBoxLayout(self); lay.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.setSpacing(12)
        icon_wrap = QWidget(); icon_wrap.setFixedSize(72,72)
        icon_wrap.setStyleSheet(f"background:{C['red_light']};border-radius:36px;")
        icon_lay = QVBoxLayout(icon_wrap); icon_lay.setContentsMargins(0,0,0,0)
        icon_lbl = QLabel("—"); icon_lbl.setFont(QFont("Segoe UI",26))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); icon_lbl.setStyleSheet("background:transparent;")
        icon_lay.addWidget(icon_lbl)
        msg = QLabel("No visits yet."); msg.setFont(QFont("Georgia",16,QFont.Weight.Bold))
        msg.setStyleSheet(f"color:{C['text2']};background:transparent;"); msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Click  + New Visit  to add the first visit for this patient.")
        sub.setFont(QFont("Segoe UI",11))
        sub.setStyleSheet(f"color:{C['text3']};background:transparent;"); sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(); lay.addWidget(icon_wrap, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(4); lay.addWidget(msg); lay.addWidget(sub); lay.addStretch()


# ─── Main page ────────────────────────────────────────────────
class VisitManagerPage(QWidget):
    def __init__(self, shell, patient_id, create_new=False):
        super().__init__()
        self.shell = shell; self.patient_id = patient_id
        self.patient_dict = _load_patient(patient_id)
        self.setStyleSheet(f"QWidget{{background:{C['bg']};font-family:'Segoe UI';}}")
        self._build_ui(); self._load_visits_data()
        if create_new:
            QTimer.singleShot(100, lambda: self.stack.setCurrentIndex(1))

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        pd = self.patient_dict
        pname = f"{pd.get('first_name','')} {pd.get('last_name','')}".strip()
        self._topbar = _TopBar(pname, pd.get("patient_id","—"), username=UserSession.username())
        self._topbar.back_clicked.connect(lambda: self.shell.navigate("patients"))
        self._topbar.newvisit_clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self._topbar.logout_clicked.connect(self._logout)
        root.addWidget(self._topbar)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._visits_page())
        self.stack.addWidget(self._new_visit_page())
        root.addWidget(self.stack, stretch=1)

    def _visits_page(self):
        page = QWidget(); page.setStyleSheet(f"background:{C['bg']};")
        pl = QVBoxLayout(page); pl.setContentsMargins(40,32,40,48); pl.setSpacing(0)
        pd = self.patient_dict
        dob_str = pd["dob"].strftime("%d %b %Y") if pd.get("dob") else "—"
        fields = [("Patient ID", pd.get("patient_id","—")),
                  ("Name", f"{pd.get('first_name','')} {pd.get('last_name','')}".strip()),
                  ("DOB", dob_str), ("Gender", pd.get("gender","—")),
                  ("Phone", pd.get("phone","—")), ("Doctor", pd.get("ref_doc","—"))]
        pl.addWidget(_PatientBanner(fields)); pl.addSpacing(28)
        count_row = QHBoxLayout()
        self.vc_lbl = QLabel(); self.vc_lbl.setFont(QFont("Georgia",14,QFont.Weight.Bold))
        self.vc_lbl.setStyleSheet(f"color:{C['text2']};background:transparent;")
        count_row.addWidget(self.vc_lbl); count_row.addStretch(); pl.addLayout(count_row); pl.addSpacing(16)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setStyleSheet("background:transparent;border:none;")
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.visits_w = QWidget(); self.visits_w.setStyleSheet("background:transparent;")
        self.visits_vl = QVBoxLayout(self.visits_w)
        self.visits_vl.setContentsMargins(0,0,0,0); self.visits_vl.setSpacing(12)
        sc.setWidget(self.visits_w); pl.addWidget(sc, stretch=1)
        return page

    def _load_visits_data(self):
        while self.visits_vl.count():
            item = self.visits_vl.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        visits = _load_visits(self.patient_id)
        n = len(visits); self.vc_lbl.setText(f"{n} visit{'s' if n != 1 else ''}")
        if visits:
            for vd in visits:
                card = VisitCard(vd)
                card.open_imaging.connect(self._open_imaging)
                card.open_report.connect(self._open_report)
                self.visits_vl.addWidget(card)
        else:
            empty = _EmptyState(); empty.setMinimumHeight(360); self.visits_vl.addWidget(empty)
        self.visits_vl.addStretch()

    def _new_visit_page(self):
        page = QWidget(); page.setStyleSheet(f"background:{C['bg']};")
        pl = QVBoxLayout(page); pl.setContentsMargins(0,0,0,0); pl.setSpacing(0)
        hdr = QFrame(); hdr.setFixedHeight(46); hdr.setStyleSheet(f"QFrame{{background:{C['red_dark']};}}")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0)
        bk = QPushButton("Back")
        bk.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:13px;}"
                         "QPushButton:hover{text-decoration:underline;}")
        bk.clicked.connect(lambda: self.stack.setCurrentIndex(0)); hl.addWidget(bk); hl.addStretch()
        ht = QLabel("New Visit"); ht.setStyleSheet("color:white;font-size:14px;font-weight:bold;background:transparent;")
        hl.addWidget(ht); pl.addWidget(hdr)
        sc = QScrollArea(); sc.setWidgetResizable(True)
        sc.setStyleSheet(f"QScrollArea{{border:none;background:{C['bg']};}}")
        body = QWidget(); body.setStyleSheet(f"background:{C['bg']};")
        bl = QVBoxLayout(body); bl.setContentsMargins(40,28,40,28); bl.setSpacing(14)
        grid = QGridLayout(); grid.setSpacing(12); grid.setHorizontalSpacing(20)
        self.vf_doctor = QLineEdit(); self.vf_doctor.setPlaceholderText("Doctor Name *")
        self.vf_doctor.setFixedHeight(42); self.vf_doctor.setStyleSheet(FIELD)
        self.vf_dept = QLineEdit(); self.vf_dept.setPlaceholderText("Department")
        self.vf_dept.setFixedHeight(42); self.vf_dept.setStyleSheet(FIELD)
        self.vf_notes = QTextEdit(); self.vf_notes.setPlaceholderText("Clinical notes...")
        self.vf_notes.setFixedHeight(120); self.vf_notes.setStyleSheet(FIELD)
        for lbl, wid, r, c in [("Doctor *",self.vf_doctor,0,0),("Department",self.vf_dept,0,1)]:
            ll = QLabel(lbl); ll.setStyleSheet(f"color:{C['text2']};font-size:11px;background:transparent;")
            grid.addWidget(ll,r*2,c); grid.addWidget(wid,r*2+1,c)
        bl.addLayout(grid)
        cn = QLabel("Clinical Notes"); cn.setStyleSheet(f"color:{C['text2']};font-size:11px;background:transparent;")
        bl.addWidget(cn); bl.addWidget(self.vf_notes); bl.addStretch()
        sc.setWidget(body); pl.addWidget(sc, stretch=1)
        sbar = QFrame(); sbar.setFixedHeight(60); sbar.setStyleSheet(f"QFrame{{background:{C['red_dark']};}}")
        sbl = QHBoxLayout(sbar); sbl.setContentsMargins(20,0,20,0); sbl.setSpacing(10); sbl.addStretch()
        save_img = QPushButton("Save & Start Imaging"); save_img.setFixedHeight(36)
        save_img.setStyleSheet("QPushButton{background:white;color:#B91C1C;border:none;border-radius:9px;"
                               "font-size:13px;font-weight:bold;padding:0 20px;}"
                               "QPushButton:hover{background:#FFF5F5;}")
        save_img.clicked.connect(self._save_and_image)
        save_only = QPushButton("Save Visit"); save_only.setFixedHeight(36)
        save_only.setStyleSheet("QPushButton{background:rgba(255,255,255,0.2);color:white;border:none;"
                                "border-radius:9px;font-size:13px;padding:0 20px;}"
                                "QPushButton:hover{background:rgba(255,255,255,0.3);}")
        save_only.clicked.connect(lambda: self._save_visit(go_imaging=False))
        sbl.addWidget(save_only); sbl.addWidget(save_img); pl.addWidget(sbar)
        return page

    def _save_visit(self, go_imaging=False):
        doc = self.vf_doctor.text().strip()
        if not doc:
            QMessageBox.warning(self, "Required", "Doctor name is required."); return None
        sess = get_session()
        v = Visit(visit_id=gen_visit_id(sess), patient_id=self.patient_id,
                  doctor=doc, department=self.vf_dept.text().strip(),
                  clinical_notes=self.vf_notes.toPlainText().strip(), visit_date=datetime.now())
        sess.add(v); sess.commit(); vid = v.id; sess.close()
        self.stack.setCurrentIndex(0); self._load_visits_data()
        if not go_imaging: QMessageBox.information(self, "Saved", "Visit created.")
        return vid

    def _save_and_image(self):
        vid = self._save_visit(go_imaging=True)
        if vid: self._open_imaging(vid)

    def _open_imaging(self, visit_id_pk):
        self.shell.navigate("camera", visit_id_pk=visit_id_pk)

    def _open_report(self, visit_id_pk):
        self.shell.navigate("report", visit_id_pk=visit_id_pk)

    def _logout(self):
        UserSession.end(); self.shell.navigate("login")
