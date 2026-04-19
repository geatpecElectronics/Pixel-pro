# =============================================================
#  ui/register_page.py  —  Register  (QWidget, single-window shell)
# =============================================================
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QMessageBox,
    QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (QFont, QPainter, QColor, QPainterPath,
                          QBrush, QLinearGradient, QCursor)
from models.database import get_session, User

C_RED  = "#B91C1C"
C_DARK = "#991B1B"
C_BG   = "#F5F5F5"
C_FIELD= "#E0E0E0"
C_TEXT = "#1C1C1C"


def _shadow(w, blur=16, color=(0, 0, 0, 30), dx=0, dy=4):
    from PyQt6.QtWidgets import QGraphicsDropShadowEffect
    e = QGraphicsDropShadowEffect(w)
    e.setBlurRadius(blur); e.setColor(QColor(*color)); e.setOffset(dx, dy)
    w.setGraphicsEffect(e)


class _RedPanelRight(QWidget):
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect(); rad = 72
        path = QPainterPath()
        path.moveTo(r.right(), r.top())
        path.lineTo(r.left() + rad, r.top())
        path.quadTo(r.left(), r.top(), r.left(), r.top() + rad)
        path.lineTo(r.left(), r.bottom() - rad)
        path.quadTo(r.left(), r.bottom(), r.left() + rad, r.bottom())
        path.lineTo(r.right(), r.bottom())
        path.closeSubpath()
        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0, QColor(C_DARK)); grad.setColorAt(1, QColor(C_RED))
        p.fillPath(path, QBrush(grad))


class _Field(QFrame):
    def __init__(self, placeholder, echo=QLineEdit.EchoMode.Normal):
        super().__init__()
        self.setFixedHeight(56)
        self.setStyleSheet(f"QFrame{{background:{C_FIELD};border-radius:12px;"
                           "border:1.5px solid transparent;}}")
        lay = QHBoxLayout(self); lay.setContentsMargins(18, 0, 18, 0)
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(placeholder); self.inp.setEchoMode(echo)
        self.inp.setStyleSheet(f"QLineEdit{{background:transparent;border:none;"
                               f"font-size:14px;color:{C_TEXT};}}")
        lay.addWidget(self.inp)

    def text(self): return self.inp.text()


class RegisterPage(QWidget):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.setObjectName("register_page")
        self.setStyleSheet(f"QWidget#register_page{{background:{C_BG};font-family:'Segoe UI';}}")
        self._build()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # Left form
        left = QWidget(); left.setStyleSheet(f"background:{C_BG};")
        ll = QVBoxLayout(left); ll.setContentsMargins(64, 0, 64, 0)
        ll.setAlignment(Qt.AlignmentFlag.AlignCenter); ll.setSpacing(0)

        title = QLabel("Registration")
        title.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{C_RED};background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(title); ll.addSpacing(32)

        self._user  = _Field("Username")
        self._email = _Field("Email")
        self._pass  = _Field("Password", QLineEdit.EchoMode.Password)
        for f in [self._user, self._email, self._pass]:
            ll.addWidget(f); ll.addSpacing(16)

        ll.addSpacing(8)
        btn = QPushButton("Register"); btn.setFixedHeight(54)
        btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"QPushButton{{background:transparent;color:{C_RED};"
                          f"border:2px solid {C_RED};border-radius:12px;}}"
                          f"QPushButton:hover{{background:{C_RED};color:white;}}")
        btn.clicked.connect(self._register)
        _shadow(btn, 14, (185, 28, 28, 50), 0, 3)
        ll.addWidget(btn)
        root.addWidget(left, stretch=1)

        # Right red panel
        right = _RedPanelRight(); right.setFixedWidth(420)
        rl = QVBoxLayout(right); rl.setContentsMargins(64, 0, 52, 0)
        rl.setAlignment(Qt.AlignmentFlag.AlignCenter); rl.setSpacing(22)

        wb = QLabel("Welcome\nBack")
        wb.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        wb.setStyleSheet("color:white;background:transparent;")
        rl.addWidget(wb)

        sub = QLabel("Already have an account?")
        sub.setFont(QFont("Segoe UI", 12))
        sub.setStyleSheet("color:rgba(255,255,255,0.82);background:transparent;")
        rl.addWidget(sub)

        login_btn = QPushButton("Login"); login_btn.setFixedSize(170, 46)
        login_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        login_btn.setStyleSheet("QPushButton{background:transparent;color:white;"
                                "border:2px solid white;border-radius:10px;}"
                                "QPushButton:hover{background:rgba(255,255,255,0.15);}")
        login_btn.clicked.connect(lambda: self.shell.navigate("login"))
        rl.addWidget(login_btn)
        root.addWidget(right)

    def _register(self):
        user  = self._user.text().strip()
        email = self._email.text().strip()
        pwd   = self._pass.text().strip()
        if not user or not pwd:
            QMessageBox.warning(self, "Required", "Username and password are required."); return
        sess = get_session()
        if sess.query(User).filter_by(username=user).first():
            sess.close()
            QMessageBox.warning(self, "Taken", "Username already exists."); return
        u = User(username=user, password=pwd, email=email)
        sess.add(u); sess.commit(); sess.close()
        QMessageBox.information(self, "Registered", "Account created. Please log in.")
        self.shell.navigate("login")
