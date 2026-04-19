# =============================================================
#  ui/_styles.py  — Shared design tokens for Pixel Pro
#  Labomed red palette + field / button helpers
# =============================================================

RED       = "#b01c20"
DARK_RED  = "#831316"
BG        = "#F5F5F5"
WHITE     = "#FFFFFF"
FIELD_BG  = "#E0E0E0"
TEXT_DARK = "#111827"
TEXT_MID  = "#6b7280"
TEXT_LITE = "#9ca3af"

FIELD = (
    "QLineEdit, QComboBox, QDateEdit, QTextEdit {"
    "  background:#E0E0E0; border:none; border-radius:8px;"
    "  padding:8px 12px; font-size:13px; color:#111827; }"
    "QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {"
    "  background:#d4d4d4; }"
    "QComboBox QAbstractItemView {"
    "  background:#FFFFFF; color:#111827; border:1px solid #d1d5db;"
    "  border-radius:6px; selection-background-color:#E0E0E0;"
    "  selection-color:#111827; outline:none; }"
    "QComboBox::drop-down { border:none; }"
    "QComboBox::down-arrow { image:none; width:0; }"
)

SECTION_HDR = (
    f"QFrame {{ background:{DARK_RED}; border-radius:5px; }}"
    f"QLabel {{ color:white; font-size:13px; font-weight:bold;"
    f"          background:transparent; padding:8px 14px; }}"
)

def primary_btn(label, w=None, h=36) -> str:
    """Returns stylesheet string for a primary red button."""
    return (
        f"QPushButton {{ background:{RED}; color:white; border:none;"
        f"  border-radius:6px; font-size:13px; font-weight:bold;"
        f"  padding:0 18px; }}"
        f"QPushButton:hover {{ background:{DARK_RED}; }}"
        f"QPushButton:disabled {{ background:#d1d5db; color:#9ca3af; }}"
    )

def ghost_btn() -> str:
    return (
        f"QPushButton {{ background:transparent; color:{RED}; border:1.5px solid {RED};"
        f"  border-radius:6px; font-size:13px; font-weight:bold; padding:0 18px; }}"
        f"QPushButton:hover {{ background:#fff0f0; }}"
    )

def toolbar_icon_btn() -> str:
    return (
        "QPushButton { background:transparent; color:white; border:none;"
        "  font-size:18px; border-radius:4px; }"
        "QPushButton:hover { background:rgba(255,255,255,0.18); }"
    )

def make_logo_widget(height=44):
    """
    Returns a QLabel showing the Labomed logo composited onto an off-white
    rounded pill — so a transparent PNG doesn't bleed red on the gradient bar.
    Falls back to a plain 'Pixel Pro' text label if logo.png is missing.
    """
    import os
    from PyQt6.QtWidgets import QLabel
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
    from PyQt6.QtCore import Qt

    logo_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "assets", "logo.png"
    )
    if os.path.exists(logo_path):
        src = QPixmap(logo_path).scaledToHeight(
            height - 4, Qt.TransformationMode.SmoothTransformation
        )
        pad_h, pad_v = 10, 4
        canvas = QPixmap(src.width() + pad_h * 2, height)
        canvas.fill(QColor(0, 0, 0, 0))          # fully transparent base
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # off-white pill (255,252,248 ≈ warm white, 0.88 opacity)
        p.setBrush(QColor(255, 252, 248, 224))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(canvas.rect(), 10, 10)
        p.drawPixmap(pad_h, pad_v, src)
        p.end()
        lbl = QLabel()
        lbl.setPixmap(canvas)
        lbl.setFixedSize(canvas.size())
        lbl.setStyleSheet("background: transparent;")
    else:
        lbl = QLabel("Pixel Pro")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl.setStyleSheet("color: white; background: transparent;")
    return lbl
