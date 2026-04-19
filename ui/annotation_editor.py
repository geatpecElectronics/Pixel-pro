# =============================================================
#  ui/annotation_editor.py  —  Non-destructive annotation editor
#  Original image NEVER modified — annotations saved separately
# =============================================================
import os, json, math
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QDialog, QLineEdit, QColorDialog,
    QSpinBox, QSizePolicy, QMessageBox, QSlider, QComboBox, QGroupBox)
from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QPointF
from PyQt6.QtGui import (QPixmap, QPainter, QPen, QColor, QFont, QCursor)
from models.database import get_session, CapturedImage
from ui._styles import RED, DARK_RED

# ── Shared dark-dialog stylesheet ─────────────────────────────
_DLG_DARK = """
    QDialog   { background: #1e1e1e; }
    QLabel    { color: #ffffff; background: transparent; font-size: 13px; }
    QLineEdit {
        background: #2a2a2a; color: #ffffff;
        border: 1px solid #555; border-radius: 5px;
        padding: 6px 10px; font-size: 13px;
    }
    QLineEdit:focus { border-color: #b01c20; }
    QPushButton {
        background: #333333; color: #ffffff;
        border: 1px solid #555; border-radius: 5px;
        font-size: 12px; font-weight: bold; padding: 6px 20px;
    }
    QPushButton:hover   { background: #b01c20; border-color: #b01c20; }
    QPushButton:pressed { background: #831316; }
"""


class _TextInputDialog(QDialog):
    """Dark-themed replacement for QInputDialog.getText."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Text")
        self.setFixedSize(340, 130)
        self.setStyleSheet(_DLG_DARK)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14); lay.setSpacing(10)
        lay.addWidget(QLabel("Enter label text:"))
        self._inp = QLineEdit(); self._inp.setFixedHeight(36)
        self._inp.returnPressed.connect(self.accept)
        lay.addWidget(self._inp)
        row = QHBoxLayout(); row.setSpacing(8); row.addStretch()
        ok = QPushButton("OK");     ok.setFixedSize(80, 32)
        ca = QPushButton("Cancel"); ca.setFixedSize(80, 32)
        ok.clicked.connect(self.accept); ca.clicked.connect(self.reject)
        row.addWidget(ok); row.addWidget(ca); lay.addLayout(row)

    def text(self): return self._inp.text()

TOOLS = [
    ("↗", "Arrow",      "arrow"),
    ("↔", "Distance",   "distance"),
    ("○", "Circle",     "circle"),
    ("□", "Rectangle",  "rect"),
    ("∠", "Angle",      "angle"),
    ("~","Freehand",   "freehand"),
    ("T", "Text",       "text"),
]

PRESET_COLORS = [
    ("#ff0000","Red"), ("#ffff00","Yellow"), ("#00ff00","Green"),
    ("#00cfff","Cyan"), ("#ff6600","Orange"), ("#ff00ff","Magenta"),
    ("#ffffff","White"), ("#000000","Black"),
]


# ── Canvas ─────────────────────────────────────────────────────
class ImageCanvas(QLabel):
    def __init__(self, pixmap, annotations, on_change):
        super().__init__()
        self._orig      = pixmap
        self._annots    = annotations
        self._on_change = on_change
        self._tool      = "arrow"
        self._color     = QColor("#ff0000")
        self._lw        = 2
        self._font_size = 14
        self._opacity   = 1.0
        self._pts       = []
        self._freehand  = []
        self._drawing   = False
        self._hover_pt  = None   # live cursor position in image coords
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._render()

    def set_tool(self, t):    self._tool = t; self._pts = []; self._freehand = []; self._hover_pt = None; self._render()
    def set_color(self, c):   self._color = c
    def set_lw(self, lw):     self._lw = lw
    def set_font_size(self, s): self._font_size = s
    def set_opacity(self, v): self._opacity = v / 100.0

    def _img_rect(self):
        lw, lh = self.width(), self.height()
        iw, ih = self._orig.width(), self._orig.height()
        if iw == 0 or ih == 0: return QRect(0, 0, lw, lh)
        scale = min(lw / iw, lh / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        return QRect((lw - nw) // 2, (lh - nh) // 2, nw, nh)

    def _to_img(self, pt: QPoint) -> QPointF:
        r = self._img_rect()
        if r.width() == 0 or r.height() == 0: return QPointF(0, 0)
        sx = self._orig.width()  / r.width()
        sy = self._orig.height() / r.height()
        return QPointF((pt.x() - r.x()) * sx, (pt.y() - r.y()) * sy)

    def _render(self):
        canvas  = self._orig.copy()
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw committed annotations
        for a in self._annots:
            self._draw_annotation(painter, a, canvas.width(), canvas.height())

        # Draw freehand stroke in progress
        if self._drawing and self._freehand:
            color = QColor(self._color)
            color.setAlphaF(self._opacity)
            pen = QPen(color, self._lw)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            for stroke in self._freehand:
                for i in range(len(stroke) - 1):
                    painter.drawLine(QPointF(*stroke[i]), QPointF(*stroke[i+1]))

        # Draw ghost preview for tools that need 2+ clicks
        if self._pts and self._hover_pt and not self._drawing:
            color = QColor(self._color)
            color.setAlphaF(self._opacity * 0.55)   # semi-transparent ghost
            pen = QPen(color, self._lw)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            hx, hy = self._hover_pt

            if self._tool in ("arrow", "distance"):
                x1, y1 = self._pts[0]
                painter.drawLine(QPointF(x1, y1), QPointF(hx, hy))

            elif self._tool == "circle":
                x1, y1 = self._pts[0]
                r = QRectF(min(x1,hx), min(y1,hy), abs(hx-x1), abs(hy-y1))
                painter.drawEllipse(r)

            elif self._tool == "rect":
                x1, y1 = self._pts[0]
                r = QRectF(min(x1,hx), min(y1,hy), abs(hx-x1), abs(hy-y1))
                painter.drawRect(r)

            elif self._tool == "angle":
                if len(self._pts) == 1:
                    x1, y1 = self._pts[0]
                    painter.drawLine(QPointF(x1, y1), QPointF(hx, hy))
                elif len(self._pts) == 2:
                    x1, y1 = self._pts[0]
                    xv, yv = self._pts[1]
                    painter.drawLine(QPointF(x1, y1), QPointF(xv, yv))
                    painter.drawLine(QPointF(xv, yv), QPointF(hx, hy))

        painter.end()
        scaled = canvas.scaled(self.size(),
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)

    def _make_pen(self, a: dict) -> QPen:
        color = QColor(a.get("color", "#ff0000"))
        color.setAlphaF(a.get("opacity", 1.0))
        pen   = QPen(color, a.get("lw", 2))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def _draw_annotation(self, p: QPainter, a: dict, W, H):
        pen  = self._make_pen(a)
        p.setPen(pen)
        kind = a.get("kind", "")
        pts  = a.get("pts", [])
        color = QColor(a.get("color", "#ff0000"))
        color.setAlphaF(a.get("opacity", 1.0))

        if kind == "arrow" and len(pts) >= 2:
            x1, y1 = pts[0]; x2, y2 = pts[1]
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            angle = math.atan2(y2 - y1, x2 - x1)
            hs = max(10, a.get("lw", 2) * 5)
            for da in [0.45, -0.45]:
                ax = x2 - hs * math.cos(angle - da)
                ay = y2 - hs * math.sin(angle - da)
                p.drawLine(QPointF(x2, y2), QPointF(ax, ay))

        elif kind == "distance" and len(pts) >= 2:
            x1, y1 = pts[0]; x2, y2 = pts[1]
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            dist = math.hypot(x2 - x1, y2 - y1)
            mid  = QPointF((x1+x2)/2, (y1+y2)/2)
            p.setPen(QPen(color, 1))
            fnt = QFont("Segoe UI", a.get("font_size", 12), QFont.Weight.Bold)
            p.setFont(fnt)
            p.drawText(QRectF(mid.x()+4, mid.y()-20, 120, 22),
                       Qt.AlignmentFlag.AlignLeft, f"{dist:.0f} px")
            p.setPen(pen)

        elif kind == "circle" and len(pts) >= 2:
            x1, y1 = pts[0]; x2, y2 = pts[1]
            r = QRectF(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
            p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(r)

        elif kind == "rect" and len(pts) >= 2:
            x1, y1 = pts[0]; x2, y2 = pts[1]
            r = QRectF(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
            p.setBrush(Qt.BrushStyle.NoBrush); p.drawRect(r)

        elif kind == "angle" and len(pts) >= 3:
            x1, y1 = pts[0]; xv, yv = pts[1]; x2, y2 = pts[2]
            p.drawLine(QPointF(x1,y1), QPointF(xv,yv))
            p.drawLine(QPointF(xv,yv), QPointF(x2,y2))
            a1 = math.atan2(y1-yv, x1-xv)
            a2 = math.atan2(y2-yv, x2-xv)
            deg = abs(math.degrees(a2 - a1))
            if deg > 180: deg = 360 - deg
            p.setPen(QPen(color, 1))
            fnt = QFont("Segoe UI", a.get("font_size", 12), QFont.Weight.Bold)
            p.setFont(fnt); p.drawText(QRectF(xv+6, yv-22, 80, 22),
                                       Qt.AlignmentFlag.AlignLeft, f"{deg:.1f}°")
            p.setPen(pen)

        elif kind == "freehand":
            for stroke in a.get("strokes", []):
                for i in range(len(stroke) - 1):
                    p.drawLine(QPointF(*stroke[i]), QPointF(*stroke[i+1]))

        elif kind == "text" and pts:
            x, y = pts[0]
            fnt = QFont("Segoe UI", a.get("font_size", 14), QFont.Weight.Bold)
            p.setFont(fnt)
            p.drawText(QPointF(x, y), a.get("text", ""))

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton: return
        ipt = self._to_img(e.pos())

        if self._tool == "freehand":
            self._drawing = True
            self._freehand = [[(ipt.x(), ipt.y())]]

        elif self._tool == "text":
            dlg = _TextInputDialog(self)
            if dlg.exec() and dlg.text().strip():
                text = dlg.text().strip()
                self._annots.append({
                    "kind": "text", "pts": [(ipt.x(), ipt.y())],
                    "text": text, "color": self._color.name(),
                    "lw": self._lw, "font_size": self._font_size,
                    "opacity": self._opacity,
                })
                self._on_change(); self._render()

        else:
            self._pts.append((ipt.x(), ipt.y()))
            needed = {"arrow":2,"distance":2,"circle":2,"rect":2,"angle":3}
            n = needed.get(self._tool, 2)
            if len(self._pts) >= n:
                self._annots.append({
                    "kind":  self._tool,
                    "pts":   self._pts[:n],
                    "color": self._color.name(),
                    "lw":    self._lw,
                    "font_size": self._font_size,
                    "opacity": self._opacity,
                })
                self._pts = []; self._on_change(); self._render()

    def mouseMoveEvent(self, e):
        ipt = self._to_img(e.pos())
        self._hover_pt = (ipt.x(), ipt.y())

        if self._tool == "freehand" and self._drawing and self._freehand:
            self._freehand[-1].append((ipt.x(), ipt.y()))

        # Re-render for live preview whenever we have a first point placed
        # or are drawing freehand
        if self._pts or self._drawing:
            self._render()

    def mouseReleaseEvent(self, e):
        if self._tool == "freehand" and self._drawing:
            self._drawing = False
            if self._freehand and self._freehand[0]:
                self._annots.append({
                    "kind": "freehand", "strokes": self._freehand,
                    "color": self._color.name(), "lw": self._lw,
                    "opacity": self._opacity,
                })
                self._freehand = []; self._on_change(); self._render()

    def resizeEvent(self, e):
        super().resizeEvent(e); self._render()

    def get_full_res(self) -> QPixmap:
        canvas = self._orig.copy()
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for a in self._annots:
            self._draw_annotation(p, a, canvas.width(), canvas.height())
        p.end(); return canvas


# ── Settings Panel (right side) ────────────────────────────────
class SettingsPanel(QFrame):
    def __init__(self, on_color, on_lw, on_font, on_opacity):
        super().__init__()
        self.setFixedWidth(220)
        self.setStyleSheet("QFrame{background:#1e1e1e;border-left:1px solid #333;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(18)

        # ── Color ─────────────────────────────────────────────
        lay.addWidget(self._section("Color"))

        # Preset swatches
        swatches = QWidget(); swatches.setStyleSheet("background:transparent;")
        sw_lay = QHBoxLayout(swatches); sw_lay.setContentsMargins(0,0,0,0); sw_lay.setSpacing(4)
        self._cur_color = QColor("#ff0000")
        self._on_color  = on_color

        def make_swatch(hex_color):
            b = QPushButton(); b.setFixedSize(22, 22)
            b.setStyleSheet(f"QPushButton{{background:{hex_color};border-radius:4px;"
                            f"border:1px solid #555;}}QPushButton:hover{{border:2px solid white;}}")
            b.clicked.connect(lambda _, c=hex_color: self._set_color(QColor(c)))
            return b

        for hex_c, _ in PRESET_COLORS:
            sw_lay.addWidget(make_swatch(hex_c))
        lay.addWidget(swatches)

        # Current color + custom picker
        self.color_preview = QPushButton("  ● Pick Custom Color…")
        self.color_preview.setFixedHeight(36)
        self.color_preview.setStyleSheet(
            f"QPushButton{{background:#ff0000;color:white;border:none;"
            f"border-radius:6px;font-size:12px;font-weight:bold;text-align:left;padding-left:8px;}}"
            f"QPushButton:hover{{opacity:0.9;}}")
        self.color_preview.clicked.connect(self._pick_custom)
        lay.addWidget(self.color_preview)

        # ── Stroke Width ──────────────────────────────────────
        lay.addWidget(self._section("Stroke Width"))
        self.lw_slider = QSlider(Qt.Orientation.Horizontal)
        self.lw_slider.setRange(1, 12); self.lw_slider.setValue(2)
        self.lw_slider.setStyleSheet(
            "QSlider::groove:horizontal{height:6px;background:#444;border-radius:3px;}"
            "QSlider::handle:horizontal{width:16px;height:16px;background:#b01c20;"
            "border-radius:8px;margin:-5px 0;}"
            "QSlider::sub-page:horizontal{background:#b01c20;border-radius:3px;}")
        lw_row = QHBoxLayout()
        self.lw_lbl = QLabel("2 px"); self.lw_lbl.setFixedWidth(36)
        self.lw_lbl.setStyleSheet("color:#aaa;font-size:12px;background:transparent;")
        lw_row.addWidget(self.lw_slider); lw_row.addWidget(self.lw_lbl)
        lay.addLayout(lw_row)
        self.lw_slider.valueChanged.connect(lambda v: (
            self.lw_lbl.setText(f"{v} px"), on_lw(v)))

        # Quick width buttons
        qw_row = QHBoxLayout(); qw_row.setSpacing(6)
        for w in [1, 2, 4, 8]:
            b = QPushButton(str(w)); b.setFixedSize(42, 28)
            b.setStyleSheet("QPushButton{background:#333;color:#ccc;border:none;"
                            "border-radius:4px;font-size:12px;}"
                            "QPushButton:hover{background:#b01c20;color:white;}")
            b.clicked.connect(lambda _, v=w: (self.lw_slider.setValue(v),))
            qw_row.addWidget(b)
        lay.addLayout(qw_row)

        # ── Font Size (for Text / Distance / Angle labels) ────
        lay.addWidget(self._section("Label Font Size"))
        fs_row = QHBoxLayout()
        self.fs_spin = QSpinBox(); self.fs_spin.setRange(8, 72); self.fs_spin.setValue(14)
        self.fs_spin.setFixedHeight(36)
        self.fs_spin.setStyleSheet("QSpinBox{background:#333;color:white;border:none;"
                                   "border-radius:6px;padding:4px 8px;font-size:13px;}"
                                   "QSpinBox::up-button,QSpinBox::down-button{"
                                   "background:#444;border:none;width:20px;}")
        self.fs_spin.valueChanged.connect(on_font)
        fs_row.addWidget(self.fs_spin)
        fs_lbl = QLabel("pt"); fs_lbl.setStyleSheet("color:#888;font-size:12px;background:transparent;")
        fs_row.addWidget(fs_lbl); fs_row.addStretch()
        lay.addLayout(fs_row)

        # ── Opacity ───────────────────────────────────────────
        lay.addWidget(self._section("◑  Opacity"))
        self.op_slider = QSlider(Qt.Orientation.Horizontal)
        self.op_slider.setRange(10, 100); self.op_slider.setValue(100)
        self.op_slider.setStyleSheet(self.lw_slider.styleSheet())
        op_row = QHBoxLayout()
        self.op_lbl = QLabel("100%"); self.op_lbl.setFixedWidth(38)
        self.op_lbl.setStyleSheet("color:#aaa;font-size:12px;background:transparent;")
        op_row.addWidget(self.op_slider); op_row.addWidget(self.op_lbl)
        lay.addLayout(op_row)
        self.op_slider.valueChanged.connect(lambda v: (
            self.op_lbl.setText(f"{v}%"), on_opacity(v)))

        lay.addStretch()

        # ── Instruction hint ──────────────────────────────────
        hint = QLabel("Click to place points.\nAngle tool needs 3 clicks.\n"
                      "Freehand: click & drag.")
        hint.setStyleSheet("color:#555;font-size:10px;background:transparent;"
                           "padding:8px 0;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

    def _section(self, txt):
        l = QLabel(txt)
        l.setStyleSheet("color:#ccc;font-size:12px;font-weight:bold;"
                        "background:transparent;padding-top:4px;")
        return l

    def _set_color(self, c: QColor):
        self._cur_color = c
        self._on_color(c)
        self.color_preview.setStyleSheet(
            f"QPushButton{{background:{c.name()};color:white;border:none;"
            f"border-radius:6px;font-size:12px;font-weight:bold;"
            f"text-align:left;padding-left:8px;}}"
            f"QPushButton:hover{{opacity:0.9;}}")

    def _pick_custom(self):
        dlg = QColorDialog(self._cur_color, self)
        dlg.setWindowTitle("Pick Annotation Color")
        dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        dlg.setStyleSheet("""
            QColorDialog { background: #1e1e1e; }
            QWidget      { background: #1e1e1e; color: #ffffff; font-size: 12px; }
            QLabel       { color: #ffffff; background: transparent; }
            QLineEdit    { background: #2a2a2a; color: #ffffff; border: 1px solid #555;
                           border-radius: 4px; padding: 3px 6px; }
            QPushButton  { background: #333; color: #ffffff; border: 1px solid #555;
                           border-radius: 4px; padding: 4px 14px; font-weight: bold; }
            QPushButton:hover   { background: #b01c20; border-color: #b01c20; }
            QSpinBox     { background: #2a2a2a; color: #ffffff; border: 1px solid #555;
                           border-radius: 4px; }
            QGroupBox    { color: #aaaaaa; border: 1px solid #444; border-radius: 4px;
                           margin-top: 6px; padding-top: 4px; }
        """)
        if dlg.exec() and dlg.selectedColor().isValid():
            self._set_color(dlg.selectedColor())


# ── Tool Panel (left side) ─────────────────────────────────────
class ToolPanel(QFrame):
    def __init__(self, on_select):
        super().__init__()
        self.setFixedWidth(80)
        self.setStyleSheet("QFrame{background:#161616;border-right:1px solid #333;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 12, 8, 12); lay.setSpacing(4)

        header = QLabel("TOOLS")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color:#555;font-size:9px;letter-spacing:2px;"
                             "background:transparent;padding-bottom:6px;")
        lay.addWidget(header)

        self._btns = {}
        for icon, label, mode in TOOLS:
            col = QVBoxLayout(); col.setSpacing(1)
            btn = QPushButton(icon); btn.setFixedSize(62, 44)
            btn.setToolTip(label)
            btn.setCheckable(True)
            btn.setStyleSheet(
                "QPushButton{background:#252525;color:white;border:1px solid #333;"
                "border-radius:8px;font-size:20px;}"
                "QPushButton:hover{background:#2e2e2e;border-color:#555;}"
                "QPushButton:checked{background:#b01c20;border-color:#b01c20;}")
            btn.clicked.connect(lambda _, m=mode: on_select(m))
            lbl = QLabel(label); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color:#666;font-size:9px;background:transparent;")
            self._btns[mode] = btn
            col.addWidget(btn); col.addWidget(lbl); lay.addLayout(col)
            lay.addSpacing(2)

        lay.addStretch()

    def select(self, mode):
        for m, b in self._btns.items():
            b.setChecked(m == mode)


# ── Main Window ────────────────────────────────────────────────
class AnnotationEditor(QMainWindow):
    def __init__(self, image_id: int, file_path: str):
        super().__init__()
        self.image_id  = image_id
        self.file_path = file_path
        self._changed  = False

        sess = get_session()
        img  = sess.query(CapturedImage).filter_by(id=image_id).first()
        annots = []
        if img and img.annotation_data:
            try: annots = json.loads(img.annotation_data)
            except: pass
        sess.close()

        self.setWindowTitle(f"Pixel Pro — Annotation Editor")
        self.setMinimumSize(1200, 760)
        self.setStyleSheet("QMainWindow{background:#1a1a1a;font-family:'Segoe UI';}")
        self._build_ui(annots)

    def _build_ui(self, annots):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self._build_topbar())

        pix = QPixmap(self.file_path)
        self.canvas = ImageCanvas(pix, annots, self._on_change)

        # Settings panel callbacks
        self.settings = SettingsPanel(
            on_color   = self.canvas.set_color,
            on_lw      = self.canvas.set_lw,
            on_font    = self.canvas.set_font_size,
            on_opacity = self.canvas.set_opacity,
        )
        self.tools = ToolPanel(self._sel_tool)

        body = QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)
        body.addWidget(self.tools)
        body.addWidget(self.canvas, stretch=1)
        body.addWidget(self.settings)

        bw = QWidget(); bw.setStyleSheet("background:#1a1a1a;"); bw.setLayout(body)
        root.addWidget(bw, stretch=1)
        root.addWidget(self._build_statusbar())

        self._sel_tool("arrow")

    def _build_topbar(self):
        bar = QFrame(); bar.setFixedHeight(52)
        bar.setStyleSheet(f"QFrame{{background:{RED};}}")
        lay = QHBoxLayout(bar); lay.setContentsMargins(14,0,14,0); lay.setSpacing(8)

        close = QPushButton("← Close"); close.setFixedHeight(34)
        close.setStyleSheet("QPushButton{background:transparent;color:white;border:none;"
                            "font-size:13px;}QPushButton:hover{text-decoration:underline;}")
        close.clicked.connect(self.close); lay.addWidget(close)

        t = QLabel(f"Annotation Editor  ·  {os.path.basename(self.file_path)}")
        t.setStyleSheet("color:white;font-size:13px;font-weight:bold;background:transparent;")
        lay.addWidget(t); lay.addStretch()

        undo = QPushButton("↩  Undo"); undo.setFixedSize(90, 34)
        undo.setStyleSheet("QPushButton{background:rgba(255,255,255,0.15);color:white;border:none;"
                           "border-radius:6px;font-size:12px;}"
                           "QPushButton:hover{background:rgba(255,255,255,0.25);}")
        undo.clicked.connect(self._undo); lay.addWidget(undo)

        clear = QPushButton("Clear All"); clear.setFixedSize(110, 34)
        clear.setStyleSheet("QPushButton{background:rgba(255,255,255,0.1);color:white;border:none;"
                            "border-radius:6px;font-size:12px;}"
                            "QPushButton:hover{background:rgba(220,50,50,0.5);}")
        clear.clicked.connect(self._clear_all); lay.addWidget(clear)

        save = QPushButton("Save Annotations"); save.setFixedHeight(34)
        save.setStyleSheet(f"QPushButton{{background:white;color:{DARK_RED};border:none;"
                           f"border-radius:6px;font-size:13px;font-weight:bold;padding:0 18px;}}"
                           f"QPushButton:hover{{background:#f5f5f5;}}")
        save.clicked.connect(self._save); lay.addWidget(save)
        return bar

    def _build_statusbar(self):
        bar = QFrame(); bar.setFixedHeight(28)
        bar.setStyleSheet("QFrame{background:#111;border-top:1px solid #333;}")
        lay = QHBoxLayout(bar); lay.setContentsMargins(12,0,12,0)
        self.status_lbl = QLabel("Click on the image to place annotations")
        self.status_lbl.setStyleSheet("color:#666;font-size:11px;background:transparent;")
        lay.addWidget(self.status_lbl); lay.addStretch()
        self.count_lbl = QLabel("0 annotations")
        self.count_lbl.setStyleSheet("color:#555;font-size:11px;background:transparent;")
        lay.addWidget(self.count_lbl)
        return bar

    def _sel_tool(self, mode):
        self.tools.select(mode)
        self.canvas.set_tool(mode)
        hints = {
            "arrow":    "Click start point, then end point to draw arrow",
            "distance": "Click two points to measure distance",
            "circle":   "Click two corners to draw circle",
            "rect":     "Click two corners to draw rectangle",
            "angle":    "Click 3 points: point A, vertex, point B",
            "freehand": "Click and drag to draw freehand",
            "text":     "Click where you want to place the text label",
        }
        self.status_lbl.setText(hints.get(mode, ""))

    def _on_change(self):
        self._changed = True
        n = len(self.canvas._annots)
        self.count_lbl.setText(f"{n} annotation{'s' if n!=1 else ''}")

    def _undo(self):
        if self.canvas._annots:
            self.canvas._annots.pop()
            self._on_change(); self.canvas._render()

    def _clear_all(self):
        if not self.canvas._annots: return
        r = QMessageBox.question(self, "Clear All",
            "Remove all annotations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.canvas._annots.clear()
            self._on_change(); self.canvas._render()

    def _save(self):
        base, ext = os.path.splitext(self.file_path)
        ann_path  = base + "_annotated" + ext
        full_res  = self.canvas.get_full_res()
        if full_res.save(ann_path, "PNG"):
            sess = get_session()
            img  = sess.query(CapturedImage).filter_by(id=self.image_id).first()
            if img:
                img.annotated_path   = ann_path
                img.annotation_data  = json.dumps(self.canvas._annots)
                sess.commit()
            sess.close()
            self._changed = False
            self.count_lbl.setText(
                f"{len(self.canvas._annots)} annotation(s) saved")
            QMessageBox.information(self, "Saved",
                "Annotations saved.\nOriginal image preserved unchanged.")
            self.close()
        else:
            QMessageBox.critical(self, "Save Error",
                f"Could not save annotated image to:\n{ann_path}")

    def closeEvent(self, e):
        if self._changed:
            r = QMessageBox.question(self, "Unsaved Changes",
                "Save annotations before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Save:
                self._save(); return
            elif r == QMessageBox.StandardButton.Cancel:
                e.ignore(); return
        super().closeEvent(e)
