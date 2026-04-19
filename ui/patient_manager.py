# =============================================================
#  ui/patient_manager.py  — Patient Manager page (QWidget)
# =============================================================
import os
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QLineEdit, QTextEdit, QComboBox,
    QDateEdit, QMessageBox, QStackedWidget, QGridLayout)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from ui._styles import RED, DARK_RED, BG, FIELD, TEXT_MID, TEXT_LITE
from models.database import get_session, Patient, gen_patient_id
from utils.session import UserSession


def _all_patients(search=""):
    from sqlalchemy.orm import joinedload
    sess = get_session()
    q = (sess.query(Patient).options(joinedload(Patient.visits))
         .filter(Patient.is_deleted != True)
         .order_by(Patient.created_at.desc()).all())
    result = []
    for p in q:
        name = f"{p.first_name or ''} {p.last_name or ''}".strip().lower()
        pid  = (p.patient_id or "").lower()
        ph   = (p.phone or "").lower()
        if search and not any(search in x for x in [name, pid, ph]):
            continue
        result.append({
            "id": p.id, "patient_id": p.patient_id or "—",
            "first_name": p.first_name or "", "last_name": p.last_name or "",
            "dob": p.dob, "gender": p.gender or "—",
            "phone": p.phone or "—", "ref_doc": p.ref_doc or "—",
            "visit_count": sum(1 for v in (p.visits or []) if not v.is_deleted),
        })
    sess.close(); return result


def _load_for_edit(patient_id):
    sess = get_session()
    p = sess.query(Patient).filter_by(id=patient_id).first()
    if not p: sess.close(); return {}
    d = {"id": p.id, "patient_id": p.patient_id,
         "first_name": p.first_name or "", "last_name": p.last_name or "",
         "dob": p.dob, "gender": p.gender or "",
         "phone": p.phone or "", "ref_doc": p.ref_doc or "",
         "address": p.address or "", "notes": p.notes or ""}
    sess.close(); return d


class PatientRow(QFrame):
    def __init__(self, pd, on_visits, on_edit, on_camera, on_delete):
        super().__init__()
        self.setFixedHeight(68)
        self.setStyleSheet("QFrame{background:white;border-bottom:1px solid #f3f4f6;}"
                           "QFrame:hover{background:#fff5f5;}")
        lay = QHBoxLayout(self); lay.setContentsMargins(16, 0, 16, 0); lay.setSpacing(12)

        ic = QLabel(pd["first_name"][:1].upper() if pd["first_name"] else "?")
        ic.setFixedSize(40, 40); ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setStyleSheet("background:#fef2f2;border-radius:20px;font-size:16px;"
                         "font-weight:bold;color:#B91C1C;")
        lay.addWidget(ic)

        info = QVBoxLayout(); info.setSpacing(2)
        nm = QLabel(f"{pd['first_name']} {pd['last_name']}")
        nm.setStyleSheet("font-weight:bold;font-size:14px;color:#111827;background:transparent;")
        dob_str = pd["dob"].strftime("%d %b %Y") if pd.get("dob") else "—"
        meta = QLabel(f"ID: {pd['patient_id']}  ·  DOB: {dob_str}  ·  {pd['phone']}  ·  Dr. {pd['ref_doc']}")
        meta.setStyleSheet(f"font-size:11px;color:{TEXT_MID};background:transparent;")
        info.addWidget(nm); info.addWidget(meta); lay.addLayout(info, stretch=1)

        vc = pd["visit_count"]
        lay.addWidget(QLabel(f"{vc} visit{'s' if vc != 1 else ''}")
                      .__class__(f"{vc} visit{'s' if vc != 1 else ''}"
                      ) if False else _mk_lbl(f"{vc} visit{'s' if vc != 1 else ''}", TEXT_MID))

        pid = pd["id"]
        for lbl, fn, bg in [
            ("Camera",  lambda _=False, p=pid: on_camera(p),  RED),
            ("Visits",  lambda _=False, p=pid: on_visits(p),  "transparent"),
            ("Edit",    lambda _=False, p=pid: on_edit(p),    "#374151"),
            ("Delete",  lambda _=False, p=pid: on_delete(p),  "#dc2626"),
        ]:
            border = f"border:1.5px solid {RED};" if bg == "transparent" else ""
            color  = RED if bg == "transparent" else "white"
            b = QPushButton(lbl); b.setFixedSize(80, 30)
            b.setStyleSheet(f"QPushButton{{background:{bg};color:{color};"
                            f"{border}border-radius:6px;font-size:11px;font-weight:bold;}}"
                            "QPushButton:hover{opacity:0.85;}")
            b.clicked.connect(fn); lay.addWidget(b)


def _mk_lbl(text, color):
    l = QLabel(text)
    l.setStyleSheet(f"color:{color};font-size:11px;background:transparent;")
    return l


class PatientManagerPage(QWidget):
    def __init__(self, shell, mode="list", patient_id=None):
        super().__init__()
        self.shell = shell; self.editing_id = patient_id
        self.setStyleSheet(f"QWidget{{background:{BG};font-family:'Segoe UI';}}")
        self._build_ui()
        if mode in ("list", "search"):
            self._reload()
        elif mode == "add":
            self.stack.setCurrentIndex(1)
        elif mode == "edit" and patient_id:
            self._populate(patient_id); self.stack.setCurrentIndex(1)

    def _toolbar(self):
        bar = QFrame(); bar.setFixedHeight(56)
        bar.setStyleSheet(f"QFrame{{background:{RED};}}")
        lay = QHBoxLayout(bar); lay.setContentsMargins(14, 0, 14, 0); lay.setSpacing(8)
        bk = QPushButton("Back"); bk.setFixedHeight(34)
        bk.setStyleSheet("QPushButton{background:transparent;color:white;border:1px solid "
                         "rgba(255,255,255,0.4);border-radius:6px;font-size:13px;padding:0 14px;}"
                         "QPushButton:hover{background:rgba(255,255,255,0.18);}")
        bk.clicked.connect(lambda: self.shell.navigate("dashboard")); lay.addWidget(bk)
        t = QLabel("Patient Manager")
        t.setStyleSheet("color:white;font-size:15px;font-weight:bold;background:transparent;")
        lay.addWidget(t); lay.addStretch()
        u = QLabel(UserSession.username())
        u.setStyleSheet("color:white;font-size:12px;background:transparent;"); lay.addWidget(u)
        lo = QPushButton("Logout"); lo.setFixedHeight(34)
        lo.setStyleSheet("QPushButton{background:transparent;color:white;border:1px solid "
                         "rgba(255,255,255,0.4);border-radius:6px;font-size:12px;padding:0 12px;}"
                         "QPushButton:hover{background:rgba(255,255,255,0.18);}")
        lo.clicked.connect(self._logout); lay.addWidget(lo)
        return bar

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(self._toolbar())
        self.stack = QStackedWidget()
        self.stack.addWidget(self._list_page())
        self.stack.addWidget(self._form_page())
        root.addWidget(self.stack, stretch=1)

    # ── List page ─────────────────────────────────────────────
    def _list_page(self):
        page = QWidget(); page.setStyleSheet(f"background:{BG};")
        pl = QVBoxLayout(page); pl.setContentsMargins(24, 16, 24, 16); pl.setSpacing(12)
        top = QHBoxLayout(); top.setSpacing(10)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search by name, ID or phone...")
        self.search.setFixedHeight(40)
        self.search.setStyleSheet("QLineEdit{background:white;border:1.5px solid #e5e7eb;"
                                  "border-radius:8px;padding:0 14px;font-size:13px;color:#111827;}"
                                  "QLineEdit:focus{border-color:#b01c20;}")
        self.search.textChanged.connect(self._reload); top.addWidget(self.search, stretch=1)
        add = QPushButton("+ New Patient"); add.setFixedHeight(40)
        add.setStyleSheet(f"QPushButton{{background:{RED};color:white;border:none;"
                          f"border-radius:8px;font-size:12px;font-weight:bold;padding:0 18px;}}"
                          f"QPushButton:hover{{background:{DARK_RED};}}")
        add.clicked.connect(self._show_add); top.addWidget(add); pl.addLayout(top)
        lf = QFrame(); lf.setStyleSheet("QFrame{background:white;border-radius:10px;}")
        self.list_vl = QVBoxLayout(lf); self.list_vl.setContentsMargins(0, 0, 0, 0); self.list_vl.setSpacing(0)
        sc = QScrollArea(); sc.setWidget(lf); sc.setWidgetResizable(True)
        sc.setStyleSheet("QScrollArea{border:none;}"); pl.addWidget(sc, stretch=1)
        self.count_lbl = QLabel()
        self.count_lbl.setStyleSheet(f"color:{TEXT_MID};font-size:11px;background:transparent;")
        pl.addWidget(self.count_lbl)
        return page

    def _reload(self):
        q = self.search.text().strip().lower() if hasattr(self, "search") else ""
        while self.list_vl.count():
            item = self.list_vl.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        patients = _all_patients(search=q)
        self.count_lbl.setText(f"{len(patients)} patient{'s' if len(patients) != 1 else ''}")
        if patients:
            for pd in patients:
                self.list_vl.addWidget(PatientRow(pd, self._view_visits,
                    self._edit_patient, self._start_camera, self._delete_patient))
        else:
            e = QLabel("No patients found.")
            e.setStyleSheet(f"color:{TEXT_LITE};font-size:14px;padding:30px;background:transparent;")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter); self.list_vl.addWidget(e)
        self.list_vl.addStretch()

    # ── Form page ─────────────────────────────────────────────
    def _form_page(self):
        page = QWidget(); page.setStyleSheet(f"background:{BG};")
        pl = QVBoxLayout(page); pl.setContentsMargins(0, 0, 0, 0); pl.setSpacing(0)
        ftb = QFrame(); ftb.setFixedHeight(48); ftb.setStyleSheet(f"QFrame{{background:{DARK_RED};}}")
        ftl = QHBoxLayout(ftb); ftl.setContentsMargins(14, 0, 14, 0)
        bk = QPushButton("Back to List")
        bk.setStyleSheet("QPushButton{background:transparent;color:white;border:none;font-size:13px;}"
                         "QPushButton:hover{text-decoration:underline;}")
        bk.clicked.connect(lambda: (self.stack.setCurrentIndex(0), self._reload()))
        ftl.addWidget(bk); ftl.addStretch()
        self.form_title = QLabel("New Patient")
        self.form_title.setStyleSheet("color:white;font-size:14px;font-weight:bold;background:transparent;")
        ftl.addWidget(self.form_title); pl.addWidget(ftb)
        sc = QScrollArea(); sc.setWidgetResizable(True)
        sc.setStyleSheet(f"QScrollArea{{border:none;background:{BG};}}")
        body = QWidget(); body.setStyleSheet(f"background:{BG};")
        bl = QVBoxLayout(body); bl.setContentsMargins(28, 20, 28, 20); bl.setSpacing(14)

        def shdr(txt):
            f = QFrame(); f.setFixedHeight(36); f.setStyleSheet(f"QFrame{{background:{DARK_RED};border-radius:5px;}}")
            ll = QHBoxLayout(f); ll.setContentsMargins(0, 0, 0, 0)
            lb = QLabel(txt); lb.setStyleSheet("color:white;font-size:13px;font-weight:bold;background:transparent;padding:0 14px;")
            ll.addWidget(lb); return f

        bl.addWidget(shdr("Basic Information"))
        grid = QGridLayout(); grid.setSpacing(12); grid.setHorizontalSpacing(20)
        self.f_first  = self._fi("First Name"); self.f_last = self._fi("Last Name")
        self.f_dob    = QDateEdit(); self.f_dob.setCalendarPopup(True)
        self.f_dob.setDate(QDate.currentDate()); self.f_dob.setFixedHeight(42); self.f_dob.setStyleSheet(FIELD)
        self.f_gender = QComboBox(); self.f_gender.addItems(["Select Gender","Male","Female","Other"])
        self.f_gender.setFixedHeight(42); self.f_gender.setStyleSheet(FIELD)
        self.f_phone  = self._fi("Phone"); self.f_refdoc = self._fi("Referring Doctor")
        for lbl, wid, r, c in [
            ("First Name *", self.f_first, 0, 0), ("Last Name *", self.f_last, 0, 1),
            ("Date of Birth", self.f_dob, 1, 0), ("Gender", self.f_gender, 1, 1),
            ("Phone", self.f_phone, 2, 0), ("Referring Doctor", self.f_refdoc, 2, 1),
        ]:
            ll = QLabel(lbl); ll.setStyleSheet("color:#4b5563;font-size:11px;background:transparent;")
            grid.addWidget(ll, r*2, c); grid.addWidget(wid, r*2+1, c)
        bl.addLayout(grid)
        self.f_addr = QTextEdit(); self.f_addr.setPlaceholderText("Address"); self.f_addr.setFixedHeight(70); self.f_addr.setStyleSheet(FIELD)
        self.f_notes = QTextEdit(); self.f_notes.setPlaceholderText("Notes"); self.f_notes.setFixedHeight(70); self.f_notes.setStyleSheet(FIELD)
        for lbl_txt, wid in [("Address", self.f_addr), ("Notes", self.f_notes)]:
            ll = QLabel(lbl_txt); ll.setStyleSheet("color:#4b5563;font-size:11px;background:transparent;")
            bl.addWidget(ll); bl.addWidget(wid)
        bl.addStretch(); sc.setWidget(body); pl.addWidget(sc, stretch=1)
        sbar = QFrame(); sbar.setFixedHeight(60); sbar.setStyleSheet(f"QFrame{{background:{DARK_RED};}}")
        sbl = QHBoxLayout(sbar); sbl.setContentsMargins(14, 0, 14, 0); sbl.setSpacing(10); sbl.addStretch()
        cancel = QPushButton("Cancel"); cancel.setFixedSize(110, 36)
        cancel.setStyleSheet("QPushButton{background:rgba(255,255,255,0.15);color:white;border:none;border-radius:6px;font-size:13px;}"
                             "QPushButton:hover{background:rgba(255,255,255,0.25);}")
        cancel.clicked.connect(lambda: (self.stack.setCurrentIndex(0), self._reload()))
        self.save_btn = QPushButton("Save Patient"); self.save_btn.setFixedSize(140, 36)
        self.save_btn.setStyleSheet("QPushButton{background:white;color:#831316;border:none;border-radius:6px;font-size:13px;font-weight:bold;}"
                                    "QPushButton:hover{background:#f5f5f5;}")
        self.save_btn.clicked.connect(self._save)
        sbl.addWidget(cancel); sbl.addWidget(self.save_btn); pl.addWidget(sbar)
        return page

    def _fi(self, ph):
        f = QLineEdit(); f.setPlaceholderText(ph); f.setFixedHeight(42); f.setStyleSheet(FIELD); return f

    def _populate(self, patient_id):
        pd = _load_for_edit(patient_id)
        if not pd: return
        self.form_title.setText(f"Edit Patient — {pd.get('patient_id','')}")
        self.f_first.setText(pd["first_name"]); self.f_last.setText(pd["last_name"])
        if pd.get("dob"):
            d = pd["dob"]; self.f_dob.setDate(QDate(d.year, d.month, d.day))
        idx = self.f_gender.findText(pd.get("gender", ""))
        if idx >= 0: self.f_gender.setCurrentIndex(idx)
        self.f_phone.setText(pd.get("phone","")); self.f_refdoc.setText(pd.get("ref_doc",""))
        self.f_addr.setPlainText(pd.get("address","")); self.f_notes.setPlainText(pd.get("notes",""))

    def _save(self):
        first = self.f_first.text().strip(); last = self.f_last.text().strip()
        if not first or not last:
            QMessageBox.warning(self, "Required", "First and Last name are required."); return
        sess = get_session()
        p = sess.query(Patient).filter_by(id=self.editing_id).first() if self.editing_id else None
        if not p: p = Patient(); p.patient_id = gen_patient_id(sess); sess.add(p)
        p.first_name = first; p.last_name = last
        d = self.f_dob.date(); p.dob = datetime(d.year(), d.month(), d.day())
        g = self.f_gender.currentText(); p.gender = g if g != "Select Gender" else None
        p.phone = self.f_phone.text().strip(); p.ref_doc = self.f_refdoc.text().strip()
        p.address = self.f_addr.toPlainText().strip(); p.notes = self.f_notes.toPlainText().strip()
        sess.commit(); sess.close()
        self.editing_id = None; self.stack.setCurrentIndex(0); self._reload()
        QMessageBox.information(self, "Saved", "Patient saved.")

    def _delete_patient(self, patient_id):
        if QMessageBox.question(self, "Delete Patient",
            "Delete this patient?\nAll visits will also be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
            return
        sess = get_session()
        try:
            p = sess.query(Patient).filter_by(id=patient_id).first()
            if p:
                p.is_deleted = True
                for v in (p.visits or []): v.is_deleted = True
                sess.commit()
        finally: sess.close()
        self._reload()

    def _show_add(self):
        self.editing_id = None; self.form_title.setText("New Patient")
        for w in [self.f_first, self.f_last, self.f_phone, self.f_refdoc]: w.clear()
        self.f_addr.clear(); self.f_notes.clear(); self.f_gender.setCurrentIndex(0)
        self.stack.setCurrentIndex(1)

    def _edit_patient(self, patient_id):
        self.editing_id = patient_id; self._populate(patient_id); self.stack.setCurrentIndex(1)

    def _view_visits(self, patient_id):
        self.shell.navigate("visits", patient_id=patient_id)

    def _start_camera(self, patient_id):
        self.shell.navigate("visits", patient_id=patient_id, create_new=True)

    def _logout(self):
        UserSession.end(); self.shell.navigate("login")
