# =============================================================
#  ui/register_window.py  — Register page
# =============================================================
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QMessageBox,
    QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (QFont, QPainter, QColor, QPainterPath,
                          QBrush, QLinearGradient, QCursor)
from models.database import get_session, User

C_RED="#B91C1C"; C_BG="#F5F5F5"; C_FIELD="#E0E0E0"; C_TEXT="#1C1C1C"


def _shadow(w, blur=16, color=(0,0,0,30), dx=0, dy=4):
    from PyQt6.QtWidgets import QGraphicsDropShadowEffect
    e = QGraphicsDropShadowEffect(w)
    e.setBlurRadius(blur); e.setColor(QColor(*color)); e.setOffset(dx,dy); w.setGraphicsEffect(e)


class _RedPanelRight(QWidget):
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect(); radius = 72
        path = QPainterPath()
        path.moveTo(r.right(), r.top())
        path.lineTo(r.left()+radius, r.top())
        path.quadTo(r.left(), r.top(), r.left(), r.top()+radius)
        path.lineTo(r.left(), r.bottom()-radius)
        path.quadTo(r.left(), r.bottom(), r.left()+radius, r.bottom())
        path.lineTo(r.right(), r.bottom()); path.closeSubpath()
        grad = QLinearGradient(0,0,0,r.height())
        grad.setColorAt(0,QColor("#991B1B")); grad.setColorAt(1,QColor("#B91C1C"))
        p.fillPath(path, QBrush(grad))


class _Field(QFrame):
    def __init__(self, ph, echo=QLineEdit.EchoMode.Normal):
        super().__init__(); self.setFixedHeight(56)
        self.setStyleSheet(f"QFrame{{background:{C_FIELD};border-radius:12px;border:1.5px solid transparent;}}")
        lay = QHBoxLayout(self); lay.setContentsMargins(18,0,18,0)
        self.inp = QLineEdit(); self.inp.setPlaceholderText(ph); self.inp.setEchoMode(echo)
        self.inp.setStyleSheet(f"QLineEdit{{background:transparent;border:none;font-size:14px;color:{C_TEXT};}}")
        lay.addWidget(self.inp)
    def text(self): return self.inp.text()


class RegisterPage(QWidget):
    def __init__(self, shell):
        super().__init__(); self.shell = shell
        self.setStyleSheet(f"QWidget{{background:{C_BG};font-family:'Segoe UI';}}")
        self._build()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        left = QWidget(); left.setStyleSheet(f"background:{C_BG};")
        ll = QVBoxLayout(left); ll.setContentsMargins(64,0,64,0)
        ll.setAlignment(Qt.AlignmentFlag.AlignCenter); ll.setSpacing(0)
        t = QLabel("Registration"); t.setFont(QFont("Segoe UI",30,QFont.Weight.Bold))
        t.setStyleSheet(f"color:{C_RED};background:transparent;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter); ll.addWidget(t); ll.addSpacing(32)
        self._u = _Field("Username"); self._e = _Field("Email")
        self._p = _Field("Password", QLineEdit.EchoMode.Password)
        for f in [self._u, self._e, self._p]: ll.addWidget(f); ll.addSpacing(16)
        ll.addSpacing(8)
        btn = QPushButton("Register"); btn.setFixedHeight(54)
        btn.setFont(QFont("Segoe UI",14,QFont.Weight.Bold))
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(f"QPushButton{{background:transparent;color:{C_RED};border:2px solid {C_RED};border-radius:12px;}}"
                          f"QPushButton:hover{{background:{C_RED};color:white;}}")
        btn.clicked.connect(self._register); _shadow(btn,14,(185,28,28,50),0,3); ll.addWidget(btn)
        root.addWidget(left, stretch=1)

        right = _RedPanelRight(); right.setFixedWidth(420)
        rl = QVBoxLayout(right); rl.setContentsMargins(64,0,52,0)
        rl.setAlignment(Qt.AlignmentFlag.AlignCenter); rl.setSpacing(22)
        wb = QLabel("Welcome\nBack"); wb.setFont(QFont("Segoe UI",34,QFont.Weight.Bold))
        wb.setStyleSheet("color:white;background:transparent;"); rl.addWidget(wb)
        s = QLabel("Already Have an Account ?"); s.setFont(QFont("Segoe UI",12))
        s.setStyleSheet("color:rgba(255,255,255,0.82);background:transparent;"); rl.addWidget(s)
        lb = QPushButton("Login"); lb.setFixedSize(170,46)
        lb.setFont(QFont("Segoe UI",13,QFont.Weight.Bold))
        lb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        lb.setStyleSheet("QPushButton{background:transparent;color:white;border:2px solid white;border-radius:10px;}"
                         "QPushButton:hover{background:rgba(255,255,255,0.15);}")
        lb.clicked.connect(lambda: self.shell.navigate("login")); rl.addWidget(lb)
        root.addWidget(right)

    def _register(self):
        user=self._u.text().strip(); email=self._e.text().strip(); pwd=self._p.text().strip()
        if not user or not pwd:
            QMessageBox.warning(self,"Required","Username and password are required."); return
        sess=get_session()
        if sess.query(User).filter_by(username=user).first():
            sess.close(); QMessageBox.warning(self,"Taken","Username already exists."); return
        sess.add(User(username=user,password=pwd,email=email)); sess.commit(); sess.close()
        QMessageBox.information(self,"Registered","Account created. Please log in.")
        self.shell.navigate("login")
