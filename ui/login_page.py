# =============================================================
#  ui/login_page.py  —  Login  (QWidget, single-window shell)
# =============================================================
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QMessageBox,
    QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (QFont, QPixmap, QPainter, QColor, QPainterPath,
                          QBrush, QLinearGradient, QCursor)
from models.database import get_session, User, init_db
from utils.session import UserSession

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

C_RED  = "#B91C1C"
C_DARK = "#991B1B"
C_BG   = "#F5F5F5"
C_FIELD= "#EDEDED"
C_TEXT = "#1C1C1C"
C_GREY = "#6B7280"


def _shadow(w, blur=16, color=(0, 0, 0, 30), dx=0, dy=4):
    e = QGraphicsDropShadowEffect(w)
    e.setBlurRadius(blur); e.setColor(QColor(*color)); e.setOffset(dx, dy)
    w.setGraphicsEffect(e)


class _RedPanel(QWidget):
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect(); rad = 72
        path = QPainterPath()
        path.moveTo(r.left(), r.top())
        path.lineTo(r.right() - rad, r.top())
        path.quadTo(r.right(), r.top(), r.right(), r.top() + rad)
        path.lineTo(r.right(), r.bottom() - rad)
        path.quadTo(r.right(), r.bottom(), r.right() - rad, r.bottom())
        path.lineTo(r.left(), r.bottom())
        path.closeSubpath()
        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0, QColor(C_DARK)); grad.setColorAt(1, QColor(C_RED))
        p.fillPath(path, QBrush(grad))


class _Field(QFrame):
    def __init__(self, placeholder, echo=QLineEdit.EchoMode.Normal):
        super().__init__()
        self.setFixedHeight(52)
        self.setStyleSheet(f"QFrame{{background:{C_FIELD};border-radius:10px;"
                           "border:1.5px solid transparent;}}")
        lay = QHBoxLayout(self); lay.setContentsMargins(16, 0, 16, 0)
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(placeholder); self.inp.setEchoMode(echo)
        self.inp.setStyleSheet(f"QLineEdit{{background:transparent;border:none;"
                               f"font-size:14px;color:{C_TEXT};}}")
        lay.addWidget(self.inp)

    def text(self): return self.inp.text()


class LoginPage(QWidget):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.setObjectName("login_page")
        init_db()
        self.setStyleSheet(f"QWidget#login_page{{background:{C_BG};font-family:'Segoe UI';}}")
        self._build()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # Left red panel
        left = _RedPanel(); left.setFixedWidth(380)
        ll = QVBoxLayout(left); ll.setContentsMargins(52, 0, 52, 0)
        ll.setAlignment(Qt.AlignmentFlag.AlignCenter); ll.setSpacing(22)

        hello = QLabel("Hello,\nWelcome")
        hello.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        hello.setStyleSheet("color:white;background:transparent;")
        ll.addWidget(hello)

        sub = QLabel("Don't have an account?")
        sub.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        sub.setStyleSheet("color:rgba(255,255,255,0.82);background:transparent;")
        ll.addWidget(sub)

        reg = QPushButton("Register"); reg.setFixedSize(170, 46)
        reg.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        reg.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reg.setStyleSheet("QPushButton{background:transparent;color:white;"
                          "border:2px solid white;border-radius:10px;}"
                          "QPushButton:hover{background:rgba(255,255,255,0.15);}")
        reg.clicked.connect(lambda: self.shell.navigate("register"))
        ll.addWidget(reg)
        root.addWidget(left)

        # Right form
        right = QWidget(); right.setStyleSheet(f"background:{C_BG};")
        rl = QVBoxLayout(right); rl.setContentsMargins(70, 0, 70, 0)
        rl.setAlignment(Qt.AlignmentFlag.AlignCenter); rl.setSpacing(0)

        logo = os.path.join(ASSETS, "logo.png")
        if os.path.exists(logo):
            lbl = QLabel()
            pix = QPixmap(logo).scaledToWidth(190, Qt.TransformationMode.SmoothTransformation)
            lbl.setPixmap(pix); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("background:transparent;")
            rl.addWidget(lbl); rl.addSpacing(6)

        title = QLabel("Login")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{C_RED};background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(title); rl.addSpacing(28)

        self._user = _Field("Username")
        self._pass = _Field("Password", QLineEdit.EchoMode.Password)
        self._pass.inp.returnPressed.connect(self._login)
        for f in [self._user, self._pass]:
            rl.addWidget(f); rl.addSpacing(14)

        fgt = QLabel("Forgot password?")
        fgt.setAlignment(Qt.AlignmentFlag.AlignRight)
        fgt.setStyleSheet(f"color:{C_GREY};font-size:12px;background:transparent;")
        rl.addWidget(fgt); rl.addSpacing(22)

        btn = QPushButton("Login"); btn.setFixedHeight(52)
        btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"QPushButton{{background:transparent;color:{C_RED};"
                          f"border:2px solid {C_RED};border-radius:10px;}}"
                          f"QPushButton:hover{{background:{C_RED};color:white;}}")
        btn.clicked.connect(self._login)
        _shadow(btn, 14, (185, 28, 28, 50), 0, 3)
        rl.addWidget(btn)
        root.addWidget(right, stretch=1)

    def _login(self):
        user = self._user.text().strip()
        pwd  = self._pass.text().strip()
        if not user or not pwd:
            QMessageBox.warning(self, "Required", "Enter username and password."); return
        sess = get_session()
        u = sess.query(User).filter(User.username == user,
                                    User.is_deleted != True).first()
        sess.close()
        if u and u.password == pwd:
            UserSession.start(u)
            self.shell.navigate("dashboard")
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid username or password.")
