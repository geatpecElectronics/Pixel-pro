# =============================================================
#  ui/dashboard_window.py  — Pixel Pro Dashboard
#  UI ported exactly from pixel_pro_dashboard.py reference
# =============================================================
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QGridLayout,
    QGraphicsDropShadowEffect, QSizePolicy,
    QDialog, QListWidget, QListWidgetItem, QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer, QRect, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QLinearGradient,
    QBrush, QPen, QCursor, QPixmap
)
from models.database import get_session, Patient, Visit
from utils.session import UserSession
from sqlalchemy.orm import joinedload

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

C = {
    "red":          "#B91C1C",
    "red_dark":     "#991B1B",
    "red_bright":   "#DC2626",
    "red_light":    "#FEE2E2",
    "red_pale":     "#FFF5F5",
    "bg":           "#F7F4F0",
    "bg2":          "#EFECE8",
    "white":        "#FFFFFF",
    "border":       "#E8E3DC",
    "border2":      "#D6CFC5",
    "text":         "#1C1410",
    "text2":        "#6B5E52",
    "text3":        "#A8998C",
    "blue":         "#1D4ED8",
    "blue_light":   "#DBEAFE",
    "green":        "#15803D",
    "green_light":  "#DCFCE7",
    "amber":        "#B45309",
    "amber_light":  "#FEF3C7",
}


def _shadow(widget, blur=16, offset=(0, 4), color=(28, 20, 16, 18)):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(offset[0], offset[1])
    eff.setColor(QColor(*color))
    widget.setGraphicsEffect(eff)
    return eff


def _fetch_stats():
    sess = get_session()
    try:
        today = datetime.now().date()
        tp = sess.query(Patient).filter(Patient.is_deleted != True).count()
        tv = sess.query(Visit).filter(Visit.is_deleted != True).count()
        visits = sess.query(Visit).filter(Visit.is_deleted != True).all()
        tdy = sum(1 for v in visits if v.visit_date and v.visit_date.date() == today)
        return tp, tv, tdy
    finally:
        sess.close()


def _fetch_recent():
    sess = get_session()
    try:
        visits = (sess.query(Visit)
                  .options(joinedload(Visit.patient))
                  .filter(Visit.is_deleted != True)
                  .order_by(Visit.visit_date.desc())
                  .limit(10).all())
        result = []
        for v in visits:
            p = v.patient
            name = f"{p.first_name or ''} {p.last_name or ''}".strip() if p else "—"
            result.append({
                "id":           v.id,
                "visit_id":     v.visit_id or "—",
                "patient_name": name or "—",
                "patient_pid":  p.patient_id if p else "—",
                "doctor":       v.doctor or "—",
                "visit_date":   v.visit_date,
                "patient_id":   p.id if p else None,
            })
        return result
    finally:
        sess.close()


# ── TopBar ────────────────────────────────────────────────────
class TopBar(QWidget):
    logout_clicked = pyqtSignal()

    def __init__(self, username="User", parent=None):
        super().__init__(parent)
        self.username = username
        self.setFixedHeight(64)
        self._build()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(C["red_dark"]))
        grad.setColorAt(0.4, QColor(C["red"]))
        grad.setColorAt(1.0, QColor(C["red_bright"]))
        p.fillRect(self.rect(), QBrush(grad))
        p.setPen(QPen(QColor(0, 0, 0, 30), 1))
        p.drawLine(0, self.height()-1, self.width(), self.height()-1)

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 24, 0)
        lay.setSpacing(0)

        # Logo — composited onto off-white pill so transparent PNG doesn't bleed red
        from ui._styles import make_logo_widget
        lay.addWidget(make_logo_widget(44))

        # Divider
        div = QFrame()
        div.setFixedSize(1, 34)
        div.setStyleSheet("background: rgba(255,255,255,0.25);")
        lay.addSpacing(18); lay.addWidget(div); lay.addSpacing(18)

        # Pixel Pro name
        pn = QLabel("Pixel Pro")
        pn.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        pn.setStyleSheet("color: rgba(255,255,255,0.92); background: transparent;")
        lay.addWidget(pn)
        lay.addStretch()

        # User pill
        self.user_btn = QPushButton()
        self.user_btn.setFixedHeight(36)
        self.user_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        inner = QHBoxLayout(self.user_btn)
        inner.setContentsMargins(8, 0, 14, 0); inner.setSpacing(8)
        av = QLabel(self.username[0].upper())
        av.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        av.setFixedSize(26, 26)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av.setStyleSheet("background: white; color: #B91C1C; border-radius: 13px;")
        un = QLabel(self.username)
        un.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        un.setStyleSheet("color: white; background: transparent;")
        inner.addWidget(av); inner.addWidget(un)
        self.user_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.22); border-radius: 10px; }
            QPushButton:hover { background: rgba(255,255,255,0.22); }
        """)
        lay.addWidget(self.user_btn); lay.addSpacing(12)

        # Power
        power = QPushButton("⏻")
        power.setFixedSize(36, 36)
        power.setFont(QFont("Segoe UI", 14))
        power.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        power.setStyleSheet("""
            QPushButton { background: transparent; border: 1px solid transparent;
                border-radius: 9px; color: rgba(255,255,255,0.65); }
            QPushButton:hover { background: rgba(255,255,255,0.14);
                border-color: rgba(255,255,255,0.2); color: white; }
        """)
        power.clicked.connect(self.logout_clicked)
        lay.addWidget(power)


# ── StatCard ──────────────────────────────────────────────────
class StatCard(QWidget):
    ACCENTS = {
        "red":   (C["red"],   C["red_light"]),
        "blue":  (C["blue"],  C["blue_light"]),
        "green": (C["green"], C["green_light"]),
    }

    def __init__(self, value, label_text, accent="red", icon_text="👤", parent=None):
        super().__init__(parent)
        self.accent_col, self.accent_bg = self.ACCENTS[accent]
        self.value_text = str(value)
        self.label_text = label_text
        self.icon_text  = icon_text
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build()
        _shadow(self, blur=20, offset=(0, 4), color=(28, 20, 16, 14))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 18, 18)
        p.fillPath(path, QColor(C["white"]))
        p.setPen(QPen(QColor(C["border"]), 1))
        p.drawPath(path)
        acc = QPainterPath()
        acc.addRoundedRect(0, 16, 3, self.height()-32, 1.5, 1.5)
        p.fillPath(acc, QColor(self.accent_col))
        p.setOpacity(0.05)
        p.setFont(QFont("Georgia", 62, QFont.Weight.Bold))
        p.setPen(QColor(self.accent_col))
        p.drawText(QRect(self.width()-80, -10, 90, self.height()+20),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self.value_text)
        p.setOpacity(1.0)

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20); lay.setSpacing(16)
        icon_w = QLabel(self.icon_text)
        icon_w.setFixedSize(52, 52)
        icon_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_w.setFont(QFont("Segoe UI Emoji", 22))
        icon_w.setStyleSheet(f"background: {self.accent_bg}; border-radius: 14px;")
        lay.addWidget(icon_w)
        tc = QVBoxLayout(); tc.setSpacing(4); tc.setContentsMargins(0,0,0,0)
        self.val_lbl = QLabel(self.value_text)
        self.val_lbl.setFont(QFont("Georgia", 28, QFont.Weight.Bold))
        self.val_lbl.setStyleSheet(f"color: {self.accent_col}; background: transparent;")
        lbl = QLabel(self.label_text)
        lbl.setFont(QFont("Segoe UI", 12))
        lbl.setStyleSheet(f"color: {C['text3']}; background: transparent;")
        tc.addWidget(self.val_lbl); tc.addWidget(lbl)
        lay.addLayout(tc); lay.addStretch()

    def set_value(self, v):
        self.value_text = str(v)
        self.val_lbl.setText(self.value_text)
        self.update()


# ── ActionCard ────────────────────────────────────────────────
class ActionCard(QWidget):
    card_clicked = pyqtSignal(str)
    ACCENTS = {
        "red":   (C["red"],   C["red_light"]),
        "blue":  (C["blue"],  C["blue_light"]),
        "green": (C["green"], C["green_light"]),
        "amber": (C["amber"], C["amber_light"]),
    }

    def __init__(self, label_text, icon_text, accent="red", parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.icon_text  = icon_text
        self.accent_col, self.accent_bg = self.ACCENTS[accent]
        self._hovered = False
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build()
        _shadow(self, blur=8, offset=(0, 2), color=(28, 20, 16, 10))

    def enterEvent(self, e): self._hovered = True;  self.update()
    def leaveEvent(self, e): self._hovered = False; self.update()
    def mousePressEvent(self, e): self.card_clicked.emit(self.label_text)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 18, 18)
        p.fillPath(path, QColor(C["white"]))
        bc = QColor(self.accent_col if self._hovered else C["border"])
        bc.setAlpha(255 if self._hovered else 180)
        p.setPen(QPen(bc, 1.5 if self._hovered else 1))
        p.drawPath(path)
        if self._hovered:
            bar = QPainterPath()
            bar.addRoundedRect(18, self.height()-3, self.width()-36, 3, 1.5, 1.5)
            p.fillPath(bar, QColor(self.accent_col))

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 22, 20, 22)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.setSpacing(12)
        icon_w = QLabel(self.icon_text)
        icon_w.setFixedSize(56, 56)
        icon_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_w.setFont(QFont("Segoe UI Emoji", 24))
        icon_w.setStyleSheet(f"background: {self.accent_bg}; border-radius: 16px;")
        lbl = QLabel(self.label_text)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color: {C['text']}; background: transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_w, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl,    alignment=Qt.AlignmentFlag.AlignCenter)


# ── VisitRow ──────────────────────────────────────────────────
class VisitRow(QWidget):
    open_clicked = pyqtSignal(int)
    STATUS_STYLES = {
        "Review":  (C["red"],   C["red_light"]),
        "Active":  (C["green"], C["green_light"]),
        "Pending": (C["amber"], C["amber_light"]),
    }

    def __init__(self, vd: dict, on_open, parent=None):
        super().__init__(parent)
        self._vid = vd["id"]
        name   = vd.get("patient_name", "—")
        tags   = [t for t in [vd.get("patient_pid",""), vd.get("visit_id",""),
                               f"Dr. {vd.get('doctor','')}".strip(". ")] if t and t != "—"]
        vdate  = vd.get("visit_date")
        date_s = vdate.strftime("%d %b %Y") if vdate else "—"
        status = "Active"

        self._hovered = False
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._status = status
        self._build(name, tags, status, date_s)
        _shadow(self, blur=6, offset=(0, 1), color=(28, 20, 16, 8))
        self.open_clicked.connect(on_open)

    def enterEvent(self, e): self._hovered = True;  self.update()
    def leaveEvent(self, e): self._hovered = False; self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        p.fillPath(path, QColor(C["white"]))
        p.setPen(QPen(QColor(C["border2"] if self._hovered else C["border"]), 1))
        p.drawPath(path)
        if self._hovered:
            col = self.STATUS_STYLES[self._status][0]
            bar = QPainterPath()
            bar.addRoundedRect(0, 0, 3, self.height(), 1.5, 1.5)
            p.fillPath(bar, QColor(col))

    def _build(self, name, tags, status, date_s):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 12, 16, 12); lay.setSpacing(14)
        init = name[0].upper() if name and name[0].isalpha() else "?"
        av = QLabel(init)
        av.setFixedSize(44, 44)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av.setFont(QFont("Georgia", 15, QFont.Weight.Bold))
        av.setStyleSheet(f"background: {C['bg2']}; color: {C['text2']}; "
                         f"border-radius: 11px; border: 1.5px solid {C['border']};")
        info = QVBoxLayout(); info.setSpacing(5); info.setContentsMargins(0,0,0,0)
        nm = QLabel(name)
        nm.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        nm.setStyleSheet(f"color: {C['text']}; background: transparent;")
        tr = QHBoxLayout(); tr.setSpacing(6); tr.setContentsMargins(0,0,0,0)
        for i, tag in enumerate(tags):
            t = QLabel(tag)
            t.setFont(QFont("Courier New", 10))
            t.setStyleSheet(f"color: {C['text3']}; background: {C['bg2']}; "
                            f"border: 1px solid {C['border']}; border-radius: 5px; padding: 1px 7px;")
            tr.addWidget(t)
            if i < len(tags)-1:
                dot = QLabel("·"); dot.setStyleSheet(f"color: {C['border2']}; background: transparent;")
                tr.addWidget(dot)
        tr.addStretch()
        info.addWidget(nm); info.addLayout(tr)
        right = QHBoxLayout(); right.setSpacing(14); right.setContentsMargins(0,0,0,0)
        right.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        st_col, st_bg = self.STATUS_STYLES[status]
        sl = QLabel(status)
        sl.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        sl.setFixedHeight(22)
        sl.setStyleSheet(f"color: {st_col}; background: {st_bg}; border-radius: 10px; "
                         f"border: 1px solid {st_col}44; padding: 0 10px;")
        sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl = QLabel(date_s)
        dl.setFont(QFont("Courier New", 10))
        dl.setStyleSheet(f"color: {C['text3']}; background: transparent;")
        btn = QPushButton("Open  →")
        btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        btn.setFixedSize(88, 32)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"""
            QPushButton {{ background: {C['red']}; color: white; border: none; border-radius: 9px; }}
            QPushButton:hover {{ background: {C['red_dark']}; }}
        """)
        btn.clicked.connect(lambda _=False: self.open_clicked.emit(self._vid))
        right.addWidget(sl); right.addWidget(dl); right.addWidget(btn)
        lay.addWidget(av); lay.addLayout(info, 1); lay.addLayout(right)


# ── ActivityItem ──────────────────────────────────────────────
class ActivityItem(QWidget):
    COLORS = {
        "red":   (C["red"],   C["red_light"]),
        "blue":  (C["blue"],  C["blue_light"]),
        "green": (C["green"], C["green_light"]),
        "amber": (C["amber"], C["amber_light"]),
    }

    def __init__(self, icon, title, sub, time_str, accent="red", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        col, bg = self.COLORS[accent]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8); lay.setSpacing(12)
        dot = QLabel(icon)
        dot.setFixedSize(34, 34)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setFont(QFont("Segoe UI Emoji", 14))
        dot.setStyleSheet(f"background: {bg}; border-radius: 9px; border: 1px solid {col}33;")
        body = QVBoxLayout(); body.setSpacing(2); body.setContentsMargins(0,0,0,0)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        t.setStyleSheet(f"color: {C['text']}; background: transparent;")
        s = QLabel(sub)
        s.setFont(QFont("Segoe UI", 11))
        s.setStyleSheet(f"color: {C['text3']}; background: transparent;")
        body.addWidget(t); body.addWidget(s)
        tl = QLabel(time_str)
        tl.setFont(QFont("Courier New", 10))
        tl.setStyleSheet(f"color: {C['text3']}; background: transparent;")
        tl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(dot); lay.addLayout(body, 1); lay.addWidget(tl)


# ── Panel ─────────────────────────────────────────────────────
class Panel(QWidget):
    def __init__(self, title, link_text="", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._main = QVBoxLayout(self)
        self._main.setContentsMargins(0, 0, 0, 0); self._main.setSpacing(0)
        hdr = QWidget()
        hdr.setStyleSheet(f"background: {C['white']}; border-bottom: 1px solid {C['border']};"
                          f"border-top-left-radius: 16px; border-top-right-radius: 16px;")
        hdr.setFixedHeight(50)
        hdr_lay = QHBoxLayout(hdr); hdr_lay.setContentsMargins(22, 0, 16, 0)
        tl = QLabel(title)
        tl.setFont(QFont("Georgia", 13, QFont.Weight.Bold))
        tl.setStyleSheet(f"color: {C['text']}; background: transparent; border: none;")
        hdr_lay.addWidget(tl); hdr_lay.addStretch()
        if link_text:
            lk = QLabel(link_text)
            lk.setFont(QFont("Courier New", 10))
            lk.setStyleSheet(f"color: {C['text3']}; background: transparent; border: none; padding: 4px 10px;")
            hdr_lay.addWidget(lk)
        self._main.addWidget(hdr)
        self._body = QWidget()
        self._body.setStyleSheet(f"background: {C['white']}; border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(22, 16, 22, 18); self._body_lay.setSpacing(0)
        self._main.addWidget(self._body)
        _shadow(self, blur=20, offset=(0, 4), color=(28, 20, 16, 12))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        p.fillPath(path, QColor(C["white"]))
        p.setPen(QPen(QColor(C["border"]), 1))
        p.drawPath(path)

    def body(self): return self._body_lay


# ── SectionHeader ─────────────────────────────────────────────
class SectionHeader(QWidget):
    def __init__(self, title, link_text="", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        tr = QHBoxLayout(); tr.setSpacing(10)
        t = QLabel(title)
        t.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {C['text']}; background: transparent;")
        tr.addWidget(t)
        dash = QWidget(); dash.setFixedSize(28, 2)
        dash.setStyleSheet(f"background: {C['red']}; border-radius: 1px;")
        tr.addWidget(dash, alignment=Qt.AlignmentFlag.AlignVCenter)
        tr.addStretch()
        lay.addLayout(tr)
        if link_text:
            lk = QLabel(link_text)
            lk.setFont(QFont("Courier New", 10))
            lk.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            lk.setStyleSheet(f"color: {C['text3']}; background: {C['white']}; "
                             f"border: 1px solid {C['border']}; border-radius: 7px; padding: 4px 12px;")
            lay.addWidget(lk)


# ── DatePill ──────────────────────────────────────────────────
class DatePill(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.lbl = QLabel()
        self.lbl.setFont(QFont("Courier New", 11))
        self.lbl.setStyleSheet(f"color: {C['text2']}; background: transparent;")
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        pill = QWidget()
        pill.setStyleSheet(f"background: {C['white']}; border: 1px solid {C['border']}; border-radius: 20px;")
        pl = QHBoxLayout(pill); pl.setContentsMargins(14, 6, 16, 6); pl.setSpacing(8)
        dot = QWidget(); dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {C['green']}; border-radius: 4px;")
        pl.addWidget(dot); pl.addWidget(self.lbl)
        lay.addWidget(pill)
        _shadow(pill, blur=6, offset=(0, 1), color=(28, 20, 16, 8))
        self._tick()

    def _tick(self):
        self.lbl.setText(datetime.now().strftime("%A, %d %B %Y"))


# ── Patient Search Dialog ─────────────────────────────────────
from PyQt6.QtWidgets import QDialog, QListWidget, QListWidgetItem

class _PatientSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_patient_id = None
        self.setWindowTitle("Search Patients")
        self.setMinimumSize(560, 480)
        self.setStyleSheet(f"QDialog {{ background: {C['bg']}; }}")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(14)

        # Title
        title = QLabel("Search Patients")
        title.setFont(QFont("Georgia", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C['text']}; background: transparent;")
        lay.addWidget(title)

        # Search box
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Type name, ID or phone…")
        self._search.setFixedHeight(44)
        self._search.setStyleSheet(
            f"QLineEdit {{ background: white; border: 1.5px solid {C['border2']};"
            f"  border-radius: 10px; padding: 0 16px; font-size: 13px; color: {C['text']}; }}"
            f"QLineEdit:focus {{ border-color: {C['red']}; }}"
        )
        self._search.textChanged.connect(self._refresh)
        lay.addWidget(self._search)

        # Recent label
        self._list_label = QLabel("Recent patients")
        self._list_label.setFont(QFont("Courier New", 9))
        self._list_label.setStyleSheet(f"color: {C['text3']}; background: transparent;")
        lay.addWidget(self._list_label)

        # Results list
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{ background: white; border: 1px solid {C['border']};
                border-radius: 10px; padding: 4px; }}
            QListWidget::item {{ padding: 10px 14px; border-radius: 7px;
                color: {C['text']}; font-size: 13px; }}
            QListWidget::item:hover {{ background: {C['red_light']}; }}
            QListWidget::item:selected {{ background: {C['red_light']};
                color: {C['red']}; font-weight: bold; }}
        """)
        self._list.itemDoubleClicked.connect(self._pick)
        lay.addWidget(self._list, stretch=1)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(36)
        cancel.setStyleSheet(
            f"QPushButton {{ background: {C['bg2']}; color: {C['text2']}; border: none;"
            f"  border-radius: 8px; padding: 0 20px; font-size: 13px; }}"
            f"QPushButton:hover {{ background: {C['border2']}; }}"
        )
        cancel.clicked.connect(self.reject)
        open_btn = QPushButton("Open Patient →")
        open_btn.setFixedHeight(36)
        open_btn.setStyleSheet(
            f"QPushButton {{ background: {C['red']}; color: white; border: none;"
            f"  border-radius: 8px; padding: 0 20px; font-size: 13px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {C['red_dark']}; }}"
        )
        open_btn.clicked.connect(self._pick)
        btn_row.addWidget(cancel); btn_row.addWidget(open_btn)
        lay.addLayout(btn_row)

        self._patients = []
        self._refresh("")

    def _refresh(self, text=""):
        from models.database import get_session, Patient
        from sqlalchemy.orm import joinedload
        q = text.strip().lower() if text else ""
        sess = get_session()
        rows = (sess.query(Patient)
                .filter(Patient.is_deleted != True)
                .order_by(Patient.created_at.desc())
                .limit(50).all())
        result = []
        for p in rows:
            name = f"{p.first_name or ''} {p.last_name or ''}".strip()
            pid  = (p.patient_id or "").lower()
            ph   = (p.phone or "").lower()
            if q and not any(q in x for x in [name.lower(), pid, ph]):
                continue
            result.append((p.id, name, p.patient_id or "—", p.phone or "—"))
        sess.close()
        self._patients = result

        self._list.clear()
        if not result:
            item = QListWidgetItem("No patients found.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._list.addItem(item)
        else:
            for pid, name, ptid, phone in result:
                item = QListWidgetItem(f"{name}   ·   {ptid}   ·   📞 {phone}")
                item.setData(Qt.ItemDataRole.UserRole, pid)
                self._list.addItem(item)

        self._list_label.setText(
            f"{'Search results' if q else 'Recent patients'} — {len(result)} found")

    def _pick(self):
        item = self._list.currentItem()
        if not item: return
        pid = item.data(Qt.ItemDataRole.UserRole)
        if pid:
            self.selected_patient_id = pid
            self.accept()


# ── DashboardWindow ───────────────────────────────────────────
class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pixel Pro — Dashboard")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 700)
        self.setStyleSheet(f"QMainWindow {{ background: {C['bg']}; }}")
        self._build()
        self._load_data()
        self._clock = QTimer()
        self._clock.timeout.connect(self._tick)
        self._clock.start(60000); self._tick()

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        central.setStyleSheet(f"background: {C['bg']};")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        uname = UserSession.username() or "User"
        self._topbar = TopBar(uname)
        self._topbar.logout_clicked.connect(self._logout)
        root.addWidget(self._topbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget(); content.setStyleSheet("background: transparent;")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(40, 36, 40, 48); cv.setSpacing(0)

        # Greeting
        gr = QHBoxLayout(); gr.setContentsMargins(0, 0, 0, 32)
        greet = QLabel(f'<span style="font-family: Georgia; font-size: 26px; font-weight: bold; color: {C["text"]};">'
                       f'Good day, <span style="color: {C["red"]};">{uname}</span> 👋</span>')
        greet.setTextFormat(Qt.TextFormat.RichText)
        gr.addWidget(greet); gr.addStretch()
        self._date_pill = DatePill()
        gr.addWidget(self._date_pill, alignment=Qt.AlignmentFlag.AlignVCenter)
        cv.addLayout(gr)

        # Stats
        sr = QHBoxLayout(); sr.setSpacing(16); sr.setContentsMargins(0, 0, 0, 32)
        self._sc_patients = StatCard(0, "Total Patients", "red",   "👥")
        self._sc_visits   = StatCard(0, "Total Visits",   "blue",  "📅")
        self._sc_today    = StatCard(0, "Today's Visits", "green", "🗓️")
        for sc in [self._sc_patients, self._sc_visits, self._sc_today]:
            sr.addWidget(sc)
        cv.addLayout(sr)

        # Quick Actions
        cv.addWidget(SectionHeader("Quick Actions"))
        cv.addSpacing(16)
        qg = QHBoxLayout(); qg.setSpacing(14)
        for label_t, icon, accent, fn in [
            ("New Patient",    "➕", "red",   self._new_patient),
            ("Search Patient", "🔍", "blue",  self._search_patient),
            ("All Patients",   "👥", "green", self._go_patients),
            ("PACS Settings",  "⚙️", "amber", self._pacs_settings),
        ]:
            card = ActionCard(label_t, icon, accent)
            card.card_clicked.connect(lambda _, f=fn: f())
            qg.addWidget(card)
        cv.addLayout(qg)
        cv.addSpacing(32)

        # Recent Visits
        cv.addWidget(SectionHeader("Recent Visits", "View all →"))
        cv.addSpacing(16)
        self._visits_col = QVBoxLayout(); self._visits_col.setSpacing(10)
        cv.addLayout(self._visits_col)
        cv.addSpacing(32)

        # Activity Log
        act_panel = Panel("Activity Log", "Today")
        ab = act_panel.body()
        ab.setContentsMargins(22, 12, 22, 18)
        act_grid = QGridLayout(); act_grid.setSpacing(0); act_grid.setHorizontalSpacing(32)
        activities = [
            ("▶️",  "Session started",      "Camera ready",        "Now",     "red"),
            ("🖼️", "Image capture ready",   "Awaiting session",    "—",       "blue"),
            ("➕",  "Patient registration",  "Add new patients",    "—",       "green"),
            ("📄",  "Report builder",        "Generate visit PDFs", "—",       "amber"),
        ]
        for i, (icon, title, sub, t, accent) in enumerate(activities):
            row = i // 2; col = i % 2
            if i >= 2:
                line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet(f"color: {C['border']}; background: {C['border']};")
                line.setFixedHeight(1); act_grid.addWidget(line, row*2-1, col)
            act_grid.addWidget(ActivityItem(icon, title, sub, t, accent), row*2, col)
        ab.addLayout(act_grid)
        cv.addWidget(act_panel)
        cv.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

    def _load_data(self):
        tp, tv, tdy = _fetch_stats()
        self._sc_patients.set_value(tp)
        self._sc_visits.set_value(tv)
        self._sc_today.set_value(tdy)

        while self._visits_col.count():
            item = self._visits_col.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        visits = _fetch_recent()
        if visits:
            for vd in visits:
                self._visits_col.addWidget(VisitRow(vd, self._open_visit))
        else:
            e = QLabel("No visits yet. Register a patient and start a visit.")
            e.setFont(QFont("Segoe UI", 13))
            e.setStyleSheet(f"color: {C['text3']}; padding: 28px; background: transparent;")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._visits_col.addWidget(e)

    def _tick(self):
        self._date_pill._tick()

    def _new_patient(self):
        from ui.patient_manager import PatientManagerWindow
        self.w = PatientManagerWindow(mode="add"); self.w.show(); self.close()

    def _search_patient(self):
        dlg = _PatientSearchDialog(self)
        dlg.exec()
        if dlg.selected_patient_id:
            from ui.visit_manager import VisitManagerWindow
            self.w = VisitManagerWindow(patient_id=dlg.selected_patient_id)
            self.w.show(); self.close()

    def _go_patients(self):
        from ui.patient_manager import PatientManagerWindow
        self.w = PatientManagerWindow(); self.w.show(); self.close()

    def _open_visit(self, visit_id: int):
        sess = get_session()
        v = sess.query(Visit).filter_by(id=visit_id).first()
        patient_id = v.patient_id if v else None
        sess.close()
        if patient_id:
            from ui.visit_manager import VisitManagerWindow
            self.w = VisitManagerWindow(patient_id=patient_id)
            self.w.show(); self.close()

    def _pacs_settings(self):
        from ui.pacs_manager import PACSManagerWindow
        self.w = PACSManagerWindow(); self.w.show()

    def _logout(self):
        UserSession.end()
        from ui.login_window import LoginWindow
        self.lw = LoginWindow(); self.lw.show(); self.close()


# =============================================================
#  DashboardPage — QWidget wrapper for single-window shell
# =============================================================
class DashboardPage(QWidget):
    """Shell-compatible page that contains the full dashboard UI."""

    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.setObjectName("dashboard_page")
        self.setStyleSheet(f"QWidget#dashboard_page {{ background: {C['bg']}; }}")
        self._build()
        self._load_data()
        self._clock = QTimer()
        self._clock.timeout.connect(self._tick)
        self._clock.start(60000); self._tick()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        uname = UserSession.username() or "User"
        self._topbar = TopBar(uname)
        self._topbar.logout_clicked.connect(self._logout)
        root.addWidget(self._topbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea{{background:{C['bg']};border:none;}}"
                             f"QScrollArea>QWidget>QWidget{{background:{C['bg']};}}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget(); content.setStyleSheet(f"background:{C['bg']};")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(40, 36, 40, 48); cv.setSpacing(0)

        gr = QHBoxLayout(); gr.setContentsMargins(0, 0, 0, 32)
        greet = QLabel(f'<span style="font-family: Georgia; font-size: 26px; font-weight: bold; color: {C["text"]};">'
                       f'Good day, <span style="color: {C["red"]};">{uname}</span> \U0001f44b</span>')
        greet.setTextFormat(Qt.TextFormat.RichText)
        gr.addWidget(greet); gr.addStretch()
        self._date_pill = DatePill()
        gr.addWidget(self._date_pill, alignment=Qt.AlignmentFlag.AlignVCenter)
        cv.addLayout(gr)

        sr = QHBoxLayout(); sr.setSpacing(16); sr.setContentsMargins(0, 0, 0, 32)
        self._sc_patients = StatCard(0, "Total Patients", "red",   "👥")
        self._sc_visits   = StatCard(0, "Total Visits",   "blue",  "📅")
        self._sc_today    = StatCard(0, "Today's Visits", "green", "🗓️")
        for sc in [self._sc_patients, self._sc_visits, self._sc_today]:
            sr.addWidget(sc)
        cv.addLayout(sr)

        cv.addWidget(SectionHeader("Quick Actions"))
        cv.addSpacing(16)
        qg = QHBoxLayout(); qg.setSpacing(14)
        for label_t, icon, accent, fn in [
            ("New Patient",    "➕", "red",   self._new_patient),
            ("Search Patient", "🔍", "blue",  self._search_patient),
            ("All Patients",   "👥", "green", self._go_patients),
            ("PACS Settings",  "⚙️", "amber", self._pacs_settings),
        ]:
            card = ActionCard(label_t, icon, accent)
            card.card_clicked.connect(lambda _, f=fn: f())
            qg.addWidget(card)
        cv.addLayout(qg)
        cv.addSpacing(32)

        cv.addWidget(SectionHeader("Recent Visits", "View all →"))
        cv.addSpacing(16)
        self._visits_col = QVBoxLayout(); self._visits_col.setSpacing(10)
        cv.addLayout(self._visits_col)
        cv.addSpacing(32)

        act_panel = Panel("Activity Log", "Today")
        ab = act_panel.body()
        ab.setContentsMargins(22, 12, 22, 18)
        act_grid = QGridLayout(); act_grid.setSpacing(0); act_grid.setHorizontalSpacing(32)
        activities = [
            ("▶️",  "Session started",      "Camera ready",        "Now",  "red"),
            ("🖼️", "Image capture ready",   "Awaiting session",    "—",    "blue"),
            ("➕",  "Patient registration",  "Add new patients",    "—",    "green"),
            ("📄",  "Report builder",        "Generate visit PDFs", "—",    "amber"),
        ]
        for i, (icon, title, sub, t, accent) in enumerate(activities):
            row = i // 2; col = i % 2
            if i >= 2:
                line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet(f"color: {C['border']}; background: {C['border']};")
                line.setFixedHeight(1); act_grid.addWidget(line, row*2-1, col)
            act_grid.addWidget(ActivityItem(icon, title, sub, t, accent), row*2, col)
        ab.addLayout(act_grid)
        cv.addWidget(act_panel)
        cv.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

    def _load_data(self):
        tp, tv, tdy = _fetch_stats()
        self._sc_patients.set_value(tp)
        self._sc_visits.set_value(tv)
        self._sc_today.set_value(tdy)

        while self._visits_col.count():
            item = self._visits_col.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        visits = _fetch_recent()
        if visits:
            for vd in visits:
                self._visits_col.addWidget(VisitRow(vd, self._open_visit))
        else:
            e = QLabel("No visits yet. Register a patient and start a visit.")
            e.setFont(QFont("Segoe UI", 13))
            e.setStyleSheet(f"color: {C['text3']}; padding: 28px; background: transparent;")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._visits_col.addWidget(e)

    def _tick(self):
        self._date_pill._tick()

    def _new_patient(self):
        self.shell.navigate("patients", mode="add")

    def _search_patient(self):
        dlg = _PatientSearchDialog(self)
        dlg.exec()
        if dlg.selected_patient_id:
            self.shell.navigate("visits", patient_id=dlg.selected_patient_id)

    def _go_patients(self):
        self.shell.navigate("patients")

    def _open_visit(self, visit_id: int):
        sess = get_session()
        v = sess.query(Visit).filter_by(id=visit_id).first()
        patient_id = v.patient_id if v else None
        sess.close()
        if patient_id:
            self.shell.navigate("visits", patient_id=patient_id)

    def _pacs_settings(self):
        self.shell.navigate("pacs")

    def _logout(self):
        UserSession.end()
        self.shell.navigate("login")
