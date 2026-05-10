"""
Blood Group Identification System — Redesigned UI v2
Larger fonts (15px base) + structured Analysis Detail block
"""

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QTextEdit,
    QTabWidget, QFileDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFrame, QSpinBox, QScrollArea,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QColor

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from blood_logic import (
        analyze_blood_sample,
        generate_compatibility_info, generate_result_details,
        generate_visualization_text,
        init_database, save_patient, save_blood_result,
        get_all_history, search_history, get_blood_type_stats,
        generate_pdf_report,
        save_email_config, get_email_config, send_email_report,
    )
    HAS_LOGIC = True
except ImportError:
    HAS_LOGIC = False

    def analyze_blood_sample(*a):
        return {'blood_type': 'A+', 'results': {
            'A': {'score': 62, 'positive': True,  'explanation': '[F1] Internal fragments : 8 -> 12.0/30 pts\n[F2] Fragment area ratio : 6.5% -> 13.5/25 pts\n[F3] Intensity std-dev : 38.8 -> 19.4/20 pts'},
            'B': {'score': 26, 'positive': False, 'explanation': '[F1] Internal fragments : 2 -> 3.0/30 pts\n[F2] Fragment area ratio : 1.2% -> 3.0/25 pts'},
            'D': {'score': 50, 'positive': True,  'explanation': '[F1] Internal fragments : 5 -> 9.0/30 pts\n[F2] Fragment area ratio : 4.1% -> 10.2/25 pts'},
        }}
    def generate_compatibility_info(bt): return "Can donate to: A+, AB+\nCan receive from: A+, A-, O+, O-"
    def generate_result_details(r, bt): return f"Blood type: {bt}\nAll tests completed."
    def generate_visualization_text(r): return "Score chart"
    def init_database(): pass
    def save_patient(**kw): return 1
    def save_blood_result(*a): pass
    def get_all_history(): return []
    def search_history(q): return []
    def get_blood_type_stats(): return {}
    def generate_pdf_report(*a): pass
    def save_email_config(*a): pass
    def get_email_config(): return None
    def send_email_report(*a): pass

init_database()

# ─── Design tokens ────────────────────────────────────────────────────────────
BG          = "#F7F8FA"
SURFACE     = "#FFFFFF"
SURFACE_2   = "#F0F2F5"
BORDER_L    = "#E4E7EC"
BORDER      = "#CDD2DA"
BORDER_D    = "#A8B0BC"
TXT_PRI     = "#0D1117"
TXT_SEC     = "#4A5568"
TXT_TER     = "#8A96A8"
RED         = "#C0392B"
RED_LIGHT   = "#FDF2F2"
RED_BORDER  = "#F5C6C6"
GREEN       = "#1A7F4B"
GREEN_LIGHT = "#F0FBF5"
GREEN_BDR   = "#A3D9B8"
BLUE        = "#1B5FAD"
BLUE_LIGHT  = "#EEF4FC"
BLUE_BDR    = "#A8C8F0"
AMBER       = "#B45309"
FONT_UI     = '"IBM Plex Sans", "Segoe UI", "Helvetica Neue", sans-serif'
FONT_MONO   = '"IBM Plex Mono", "Consolas", monospace'

GLOBAL_QSS = f"""
* {{
    font-family: {FONT_UI};
    font-size: 15px;
    color: {TXT_PRI};+
    outline: none;
}}
QMainWindow, QWidget#root {{ background: {BG}; }}

QScrollBar:vertical {{ border: none; background: {BG}; width: 6px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {BORDER_D}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ border: none; background: {BG}; height: 6px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 3px; }}

QTabWidget::pane {{ border: none; background: {BG}; margin-top: 0px; }}
QTabBar {{ background: {SURFACE}; border-bottom: 1px solid {BORDER_L}; }}
QTabBar::tab {{
    background: transparent; color: {TXT_TER};
    padding: 13px 24px; font-size: 15px; font-weight: 500;
    border-bottom: 2px solid transparent; min-width: 110px;
}}
QTabBar::tab:selected {{ color: {RED}; border-bottom: 2px solid {RED}; font-weight: 600; }}
QTabBar::tab:hover:!selected {{ color: {TXT_SEC}; background: {SURFACE_2}; }}
QTabBar::tab:disabled {{ color: {TXT_TER}; opacity: 0.5; }}

QLineEdit, QSpinBox, QComboBox {{
    background: {SURFACE}; color: {TXT_PRI};
    border: 1px solid {BORDER}; border-radius: 6px;
    padding: 10px 13px; font-size: 15px;
    selection-background-color: {BLUE_LIGHT};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {BLUE}; }}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{ border-color: {BORDER_D}; }}
QLineEdit[readOnly="true"] {{ background: {SURFACE_2}; color: {TXT_SEC}; }}
QComboBox::drop-down {{ border: none; width: 28px; subcontrol-position: right center; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER}; color: {TXT_PRI};
    selection-background-color: {BLUE_LIGHT}; selection-color: {BLUE}; outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {SURFACE_2}; border: none; width: 18px; border-left: 1px solid {BORDER_L};
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {BORDER_L}; }}

QTextEdit {{
    background: {SURFACE}; color: {TXT_PRI};
    border: 1px solid {BORDER_L}; border-radius: 6px;
    padding: 12px; font-family: {FONT_MONO}; font-size: 13px;
    selection-background-color: {BLUE_LIGHT};
}}

QPushButton {{
    border: 1px solid {BORDER}; border-radius: 6px;
    padding: 10px 18px; font-size: 15px; font-weight: 500;
    color: {TXT_SEC}; background: {SURFACE};
}}
QPushButton:hover {{ background: {SURFACE_2}; border-color: {BORDER_D}; color: {TXT_PRI}; }}
QPushButton:pressed {{ background: {BORDER_L}; }}
QPushButton:disabled {{ background: {SURFACE_2}; color: {TXT_TER}; border-color: {BORDER_L}; }}

QProgressBar {{
    border: none; border-radius: 2px; background: {BORDER_L};
    color: transparent; height: 3px;
}}
QProgressBar::chunk {{ background: {RED}; border-radius: 2px; }}

QTableWidget {{
    background: {SURFACE}; color: {TXT_PRI};
    gridline-color: {BORDER_L}; border: 1px solid {BORDER_L};
    border-radius: 8px; font-size: 14px;
    alternate-background-color: {BG};
    selection-background-color: {BLUE_LIGHT};
}}
QHeaderView::section {{
    background: {BG}; color: {TXT_TER};
    padding: 11px 14px; border: none;
    border-bottom: 1px solid {BORDER_L};
    font-size: 12px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.5px;
}}
QTableWidget::item {{ padding: 9px 14px; border: none; }}
QTableWidget::item:selected {{ background: {BLUE_LIGHT}; color: {TXT_PRI}; }}

QStatusBar {{
    background: {SURFACE}; color: {TXT_TER};
    border-top: 1px solid {BORDER_L}; padding: 6px 20px; font-size: 13px;
}}
QMessageBox {{ background: {SURFACE}; }}
QMessageBox QLabel {{ color: {TXT_PRI}; font-size: 15px; }}
"""


# ──────────────────────────────────────────────────────────────────────────────
# PRIMITIVES
# ──────────────────────────────────────────────────────────────────────────────

class Divider(QFrame):
    def __init__(self, vertical=False):
        super().__init__()
        if vertical:
            self.setFrameShape(QFrame.VLine)
            self.setFixedWidth(1)
        else:
            self.setFrameShape(QFrame.HLine)
            self.setFixedHeight(1)
        self.setStyleSheet(f"border: none; background: {BORDER_L};")


def label(text, size=15, color=TXT_PRI, bold=False, mono=False):
    lbl = QLabel(text)
    ff  = FONT_MONO if mono else FONT_UI
    fw  = "600" if bold else "400"
    lbl.setStyleSheet(
        f"font-size:{size}px; color:{color}; font-weight:{fw};"
        f"font-family:{ff}; background:transparent;"
    )
    return lbl


def section_header(title, subtitle=""):
    w = QWidget()
    w.setStyleSheet("background:transparent;")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    lay.addWidget(label(title, size=22, bold=True))
    if subtitle:
        lay.addWidget(label(subtitle, size=14, color=TXT_TER))
    return w


def card(padding=(20, 18, 20, 18)):
    w = QWidget()
    w.setObjectName("card")
    w.setStyleSheet(f"""
        QWidget#card {{
            background: {SURFACE};
            border: 1px solid {BORDER_L};
            border-radius: 10px;
        }}
    """)
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*padding)
    lay.setSpacing(12)
    return w, lay


def btn_primary(text):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setFixedHeight(42)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{RED}; color:white; border:none;
            border-radius:6px; font-size:15px; font-weight:600; padding:0 20px;
        }}
        QPushButton:hover {{ background:#a93226; }}
        QPushButton:pressed {{ background:#922b21; }}
        QPushButton:disabled {{ background:{BORDER}; color:{TXT_TER}; }}
    """)
    return b


def btn_secondary(text):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setFixedHeight(42)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{SURFACE}; color:{TXT_SEC};
            border:1px solid {BORDER}; border-radius:6px;
            font-size:15px; font-weight:500; padding:0 18px;
        }}
        QPushButton:hover {{ background:{SURFACE_2}; border-color:{BORDER_D}; color:{TXT_PRI}; }}
        QPushButton:disabled {{ color:{TXT_TER}; border-color:{BORDER_L}; }}
    """)
    return b


def btn_ghost(text, color=RED):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setFixedHeight(42)
    b.setStyleSheet(f"""
        QPushButton {{
            background:transparent; color:{color};
            border:1px solid {color}44; border-radius:6px;
            font-size:15px; font-weight:500; padding:0 16px;
        }}
        QPushButton:hover {{ background:{color}10; border-color:{color}; }}
        QPushButton:disabled {{ color:{TXT_TER}; border-color:{BORDER_L}; }}
    """)
    return b


def field_row(lbl_text, widget):
    lay = QVBoxLayout()
    lay.setSpacing(5)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(label(lbl_text, size=13, color=TXT_SEC))
    lay.addWidget(widget)
    return lay


# ──────────────────────────────────────────────────────────────────────────────
# STEP BAR
# ──────────────────────────────────────────────────────────────────────────────

class StepBar(QWidget):
    STEPS = ["Patient", "Blood Test", "Results"]

    def __init__(self):
        super().__init__()
        self._current = 0
        self._done = [False, False, False]
        self.setFixedHeight(40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._labels = []
        for i, s in enumerate(self.STEPS):
            lbl = QLabel(s)
            lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl, 1)
            self._labels.append(lbl)
            if i < len(self.STEPS) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFixedHeight(1)
                line.setStyleSheet(f"background:{BORDER_L};")
                lay.addWidget(line, 2)
        self._update_styles()

    def set_step(self, idx):
        self._current = idx
        for i in range(idx):
            self._done[i] = True
        self._update_styles()

    def _update_styles(self):
        for i, lbl in enumerate(self._labels):
            if i == self._current:
                lbl.setStyleSheet(f"color:{RED}; font-size:13px; font-weight:700; background:transparent;")
            elif self._done[i]:
                lbl.setStyleSheet(f"color:{GREEN}; font-size:13px; font-weight:600; background:transparent;")
                lbl.setText("✓ " + self.STEPS[i])
            else:
                lbl.setStyleSheet(f"color:{TXT_TER}; font-size:13px; font-weight:400; background:transparent;")
                lbl.setText(self.STEPS[i])


# ──────────────────────────────────────────────────────────────────────────────
# EMAIL DIALOG
# ──────────────────────────────────────────────────────────────────────────────

class EmailSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Configuration")
        self.setFixedSize(440, 280)
        self.setStyleSheet(f"QDialog {{ background:{SURFACE}; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)
        lay.addWidget(label("Configure email sender", size=18, bold=True))
        note = label(
            "Use a Gmail App Password — not your regular password.\n"
            "Google Account → Security → 2-Step Verification → App Passwords",
            size=13, color=TXT_TER
        )
        note.setWordWrap(True)
        lay.addWidget(note)
        self.email_in = QLineEdit()
        self.email_in.setPlaceholderText("your.email@gmail.com")
        lay.addLayout(field_row("Gmail address", self.email_in))
        self.pass_in = QLineEdit()
        self.pass_in.setPlaceholderText("App password")
        self.pass_in.setEchoMode(QLineEdit.Password)
        lay.addLayout(field_row("App password", self.pass_in))
        save_btn = btn_primary("Save")
        save_btn.clicked.connect(self._save)
        lay.addWidget(save_btn)

    def _save(self):
        e = self.email_in.text().strip()
        p = self.pass_in.text().strip()
        if not e or not p:
            QMessageBox.warning(self, "Incomplete", "Please fill in both fields.")
            return
        save_email_config(e, p)
        QMessageBox.information(self, "Saved", "Email configuration saved.")
        self.accept()


# ──────────────────────────────────────────────────────────────────────────────
# ANALYSIS THREAD
# ──────────────────────────────────────────────────────────────────────────────

class AnalysisThread(QThread):
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, a, b, d):
        super().__init__()
        self._paths = (a, b, d)

    def run(self):
        try:
            self.finished.emit(analyze_blood_sample(*self._paths))
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────────────────────────────────────
# TEST PANEL  (per-reagent image + score)
# ──────────────────────────────────────────────────────────────────────────────

class TestPanel(QWidget):
    COLORS = {'A': RED, 'B': BLUE, 'D': AMBER}
    NAMES  = {'A': 'Anti-A', 'B': 'Anti-B', 'D': 'Anti-D (Rh)'}

    def __init__(self, key, upload_cb):
        super().__init__()
        self.key = key
        color = self.COLORS[key]
        self.setObjectName("testpanel")
        self.setStyleSheet(f"""
            QWidget#testpanel {{
                background:{SURFACE}; border:1px solid {BORDER_L}; border-radius:10px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hrow = QHBoxLayout()
        hrow.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color}; font-size:9px; background:transparent;")
        hrow.addWidget(dot)
        hrow.addWidget(label(self.NAMES[key], size=14, bold=True, color=TXT_SEC))
        hrow.addStretch()
        lay.addLayout(hrow)

        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(160, 110)
        self.img_lbl.setAlignment(Qt.AlignCenter)
        self._reset_img_style()
        self.img_lbl.setText("No image")
        lay.addWidget(self.img_lbl, alignment=Qt.AlignHCenter)

        self.score_lbl = label("—", size=28, bold=True, color=TXT_TER)
        self.score_lbl.setAlignment(Qt.AlignCenter)
        self.score_lbl.setStyleSheet(f"color:{TXT_TER}; font-size:28px; font-weight:700; background:transparent;")
        sub = label("agglutination score", size=12, color=TXT_TER)
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.score_lbl)
        lay.addWidget(sub)

        self.result_badge = QLabel("Awaiting image")
        self.result_badge.setAlignment(Qt.AlignCenter)
        self.result_badge.setFixedHeight(28)
        self._reset_badge_style()
        lay.addWidget(self.result_badge)

        self.upload_btn = QPushButton("Upload image")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.setFixedHeight(34)
        self.upload_btn.setStyleSheet(f"""
            QPushButton {{
                background:{SURFACE_2}; color:{TXT_SEC};
                border:1px solid {BORDER}; border-radius:5px;
                font-size:13px; font-weight:500;
            }}
            QPushButton:hover {{ background:{BG}; border-color:{color}; color:{color}; }}
        """)
        self.upload_btn.clicked.connect(lambda: upload_cb(key))
        lay.addWidget(self.upload_btn)

    def _reset_img_style(self):
        self.img_lbl.setStyleSheet(f"""
            background:{BG}; border:1px dashed {BORDER};
            border-radius:6px; color:{TXT_TER}; font-size:13px;
        """)

    def _reset_badge_style(self):
        self.result_badge.setText("Awaiting image")
        self.result_badge.setStyleSheet(f"""
            background:{SURFACE_2}; color:{TXT_TER};
            border-radius:14px; font-size:13px; font-weight:600;
        """)

    def set_result(self, score, positive):
        c = RED if positive else GREEN
        gl = RED_LIGHT if positive else GREEN_LIGHT
        gb = RED_BORDER if positive else GREEN_BDR
        txt = "Positive" if positive else "Negative"
        self.score_lbl.setStyleSheet(f"color:{c}; font-size:28px; font-weight:700; background:transparent;")
        self.score_lbl.setText(f"{score:.0f}")
        self.result_badge.setText(txt)
        self.result_badge.setStyleSheet(f"""
            background:{gl}; color:{c}; border:1px solid {gb};
            border-radius:14px; font-size:13px; font-weight:600;
        """)

    def set_image(self, path):
        pix = QPixmap(path).scaled(156, 106, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_lbl.setPixmap(pix)
        self.img_lbl.setStyleSheet(f"background:{BG}; border:1px solid {BORDER_L}; border-radius:6px;")

    def reset(self):
        self.img_lbl.setPixmap(QPixmap())
        self.img_lbl.setText("No image")
        self._reset_img_style()
        self.score_lbl.setText("—")
        self.score_lbl.setStyleSheet(f"color:{TXT_TER}; font-size:28px; font-weight:700; background:transparent;")
        self._reset_badge_style()


# ──────────────────────────────────────────────────────────────────────────────
# ANALYSIS DETAIL WIDGET
# ──────────────────────────────────────────────────────────────────────────────

class AnalysisDetailWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QWidget#card {{
                background:{SURFACE}; border:1px solid {BORDER_L}; border-radius:10px;
            }}
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(10)

        outer.addWidget(label("Analysis Detail", size=14, bold=True, color=TXT_SEC))
        outer.addWidget(Divider())

        self.hero = QWidget()
        self.hero.setFixedHeight(54)
        self.hero.setStyleSheet(f"""
            background:{RED_LIGHT}; border:1px solid {RED_BORDER}; border-radius:8px;
        """)
        hl = QHBoxLayout(self.hero)
        hl.setContentsMargins(18, 0, 18, 0)
        hl.addWidget(label("Blood Group:", size=14, color=TXT_SEC))
        hl.addSpacing(10)
        self.hero_value = label("—", size=22, bold=True, color=RED)
        hl.addWidget(self.hero_value)
        hl.addStretch()
        outer.addWidget(self.hero)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        scroll.setFixedHeight(140)

        self._inner = QWidget()
        self._inner.setStyleSheet("background:transparent;")
        self._detail_lay = QVBoxLayout(self._inner)
        self._detail_lay.setContentsMargins(0, 4, 0, 4)
        self._detail_lay.setSpacing(6)
        self._show_placeholder()

        scroll.setWidget(self._inner)
        outer.addWidget(scroll)

    def _show_placeholder(self):
        ph = label("Per-test analysis will appear here after running…", size=13, color=TXT_TER)
        self._detail_lay.addWidget(ph)
        self._detail_lay.addStretch()

    def _clear_layout(self):
        while self._detail_lay.count():
            item = self._detail_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def clear(self):
        self._clear_layout()
        self._show_placeholder()
        self.hero_value.setText("—")

    def set_data(self, blood_type, results):
        self._clear_layout()
        self.hero_value.setText(blood_type)

        tags = [("Anti-A", "A"), ("Anti-B", "B"), ("Anti-D (Rh)", "D")]
        for idx, (tag, key) in enumerate(tags):
            r = results[key]
            pos   = r['positive']
            score = r['score']
            ac    = RED if pos else GREEN
            gl    = RED_LIGHT if pos else GREEN_LIGHT
            gb    = RED_BORDER if pos else GREEN_BDR
            status = "Positive" if pos else "Negative"

            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)

            rl.addWidget(label(f"[{tag}]", size=13, bold=True, color=TXT_SEC))
            rl.addWidget(label(f"Score: {score:.1f}", size=13, color=TXT_PRI, mono=True))
            rl.addWidget(label("→", size=13, color=TXT_TER))

            pill = QLabel(status)
            pill.setFixedHeight(22)
            pill.setAlignment(Qt.AlignCenter)
            pill.setStyleSheet(f"""
                background:{gl}; color:{ac}; border:1px solid {gb};
                border-radius:11px; padding:0 10px; font-size:12px; font-weight:700;
            """)
            rl.addWidget(pill)
            rl.addStretch()
            self._detail_lay.addWidget(row_w)

            exp_lbl = label(r.get('explanation', ''), size=12, color=TXT_TER, mono=True)
            exp_lbl.setWordWrap(True)
            self._detail_lay.addWidget(exp_lbl)

            if idx < len(tags) - 1:
                self._detail_lay.addWidget(Divider())

        self._detail_lay.addStretch()


# ──────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ──────────────────────────────────────────────────────────────────────────────

class BloodTypingApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blood Group Identification System")
        self.resize(1080, 720)
        self.setMinimumSize(900, 640)
        self.anti_a_path        = None
        self.anti_b_path        = None
        self.anti_d_path        = None
        self.analysis_result    = None
        self.current_patient_id = None
        self.patient_info       = {}
        self.setStyleSheet(GLOBAL_QSS)
        self._build_ui()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # Nav
        nav = QWidget()
        nav.setFixedHeight(54)
        nav.setStyleSheet(f"background:{SURFACE}; border-bottom:1px solid {BORDER_L};")
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(24, 0, 24, 0)
        nl.setSpacing(12)
        dot = QLabel("◆")
        dot.setStyleSheet(f"color:{RED}; font-size:17px; background:transparent;")
        nl.addWidget(dot)
        nl.addWidget(label("Blood Group Identification", size=15, bold=True))
        sep = Divider(vertical=True)
        sep.setFixedHeight(20)
        nl.addWidget(sep)
        nl.addWidget(label("Advanced agglutination analysis", size=13, color=TXT_TER))
        nl.addStretch()
        self.step_bar = StepBar()
        self.step_bar.setFixedWidth(440)
        nl.addWidget(self.step_bar)
        rl.addWidget(nav)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        rl.addWidget(self.tabs, 1)

        self._tab_patient()
        self._tab_blood_test()
        self._tab_results()
        self._tab_visualization()
        self._tab_history()

        for i in range(1, 5):
            self.tabs.setTabEnabled(i, False)
        self.statusBar().showMessage("Complete patient details to begin")

    # ── Tab 0: Patient ─────────────────────────────────────────────────────────

    def _tab_patient(self):
        tab = QWidget()
        tab.setStyleSheet(f"background:{BG};")
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(0)
        outer.addWidget(section_header("Patient Identity", "Enter patient details to begin the blood test"))
        outer.addSpacing(18)

        form_card, fl = card()
        fl.addWidget(label("Patient information", size=14, bold=True))
        fl.addWidget(Divider())
        self.name_in = QLineEdit()
        self.name_in.setPlaceholderText("Full name")
        fl.addLayout(field_row("Full name", self.name_in))
        r2 = QHBoxLayout()
        r2.setSpacing(12)
        self.age_in = QSpinBox()
        self.age_in.setRange(0, 150)
        self.age_in.setValue(25)
        self.gender_in = QComboBox()
        self.gender_in.addItems(["Male", "Female", "Other"])
        r2.addLayout(field_row("Age", self.age_in))
        r2.addLayout(field_row("Gender", self.gender_in))
        fl.addLayout(r2)
        self.phone_in = QLineEdit()
        self.phone_in.setPlaceholderText("+91 98765 43210")
        fl.addLayout(field_row("Phone number", self.phone_in))
        self.doctor_email_in = QLineEdit()
        self.doctor_email_in.setPlaceholderText("doctor@hospital.com")
        fl.addLayout(field_row("Doctor's email", self.doctor_email_in))
        fl.addSpacing(4)
        self.save_patient_btn = btn_primary("Save patient & continue")
        self.save_patient_btn.clicked.connect(self._submit_patient)
        fl.addWidget(self.save_patient_btn)
        self.patient_status = QLabel("")
        self.patient_status.setWordWrap(True)
        self.patient_status.setMinimumHeight(60)
        self.patient_status.setStyleSheet(f"""
            background:{SURFACE_2}; border:1px solid {BORDER_L};
            border-radius:6px; padding:12px 14px; font-size:13px; color:{TXT_TER};
        """)
        fl.addWidget(self.patient_status)
        outer.addWidget(form_card)
        self.tabs.addTab(tab, "Patient Identity")

    # ── Tab 1: Blood Test ──────────────────────────────────────────────────────

    def _tab_blood_test(self):
        tab = QWidget()
        tab.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        lay.addWidget(section_header(
            "Blood Sample Analysis",
            "Upload slide images for each reagent — results are computed automatically"
        ))

        panels_row = QHBoxLayout()
        panels_row.setSpacing(12)
        self.test_panels = {}
        for key in ['A', 'B', 'D']:
            p = TestPanel(key, self._upload_test_img)
            self.test_panels[key] = p
            panels_row.addWidget(p)
        lay.addLayout(panels_row)

        self.analysis_detail_widget = AnalysisDetailWidget()
        lay.addWidget(self.analysis_detail_widget)

        self.analyze_btn = btn_primary("Run blood group analysis")
        self.analyze_btn.setFixedHeight(46)
        self.analyze_btn.setStyleSheet(self.analyze_btn.styleSheet() + "font-size:15px;")
        self.analyze_btn.clicked.connect(self._run_analysis)
        lay.addWidget(self.analyze_btn)

        self.tabs.addTab(tab, "Blood Test")

    # ── Tab 2: Results ─────────────────────────────────────────────────────────

    def _tab_results(self):
        tab = QWidget()
        tab.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)
        lay.addWidget(section_header("Final Report"))

        hero, hero_lay = card((0, 0, 0, 0))
        hero.setFixedHeight(80)
        hero.setStyleSheet(f"""
            QWidget#card {{
                background:{RED_LIGHT}; border:1px solid {RED_BORDER}; border-radius:10px;
            }}
        """)
        self.blood_type_badge = QLabel("—")
        self.blood_type_badge.setAlignment(Qt.AlignCenter)
        self.blood_type_badge.setStyleSheet(f"""
            color:{RED}; font-size:32px; font-weight:700;
            letter-spacing:3px; background:transparent;
        """)
        hero_lay.addWidget(self.blood_type_badge)
        lay.addWidget(hero)

        split = QHBoxLayout()
        split.setSpacing(12)
        rc, rl2 = card()
        rl2.addWidget(label("Test results", size=13, bold=True, color=TXT_SEC))
        rl2.addWidget(Divider())
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        rl2.addWidget(self.results_text)
        cc, cl = card()
        cl.addWidget(label("Compatibility", size=13, bold=True, color=TXT_SEC))
        cl.addWidget(Divider())
        self.compat_text = QTextEdit()
        self.compat_text.setReadOnly(True)
        cl.addWidget(self.compat_text)
        split.addWidget(rc)
        split.addWidget(cc)
        lay.addLayout(split, 1)

        act = QHBoxLayout()
        act.setSpacing(8)
        self.pdf_btn = btn_secondary("Save PDF report")
        self.pdf_btn.clicked.connect(self._save_pdf)
        self.email_btn = btn_ghost("Email to doctor", BLUE)
        self.email_btn.clicked.connect(self._send_email)
        self.email_setup_btn = btn_secondary("Email setup")
        self.email_setup_btn.clicked.connect(self._open_email_setup)
        self.new_btn = btn_primary("New patient")
        self.new_btn.clicked.connect(self._clear_all)
        act.addWidget(self.pdf_btn)
        act.addWidget(self.email_btn)
        act.addWidget(self.email_setup_btn)
        act.addStretch()
        act.addWidget(self.new_btn)
        lay.addLayout(act)
        self.tabs.addTab(tab, "Final Report")

    # ── Tab 3: Visualization ───────────────────────────────────────────────────

    def _tab_visualization(self):
        tab = QWidget()
        tab.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(section_header(
            "Score Visualization",
            "Agglutination scores per reagent — threshold at 40 indicates positive reaction"
        ))
        if HAS_MATPLOTLIB:
            chart_card, chart_lay = card()
            self.chart_fig = Figure(figsize=(8, 3.6), facecolor=SURFACE)
            self.chart_canvas = FigureCanvas(self.chart_fig)
            self.chart_canvas.setStyleSheet(f"background:{SURFACE};")
            chart_lay.addWidget(self.chart_canvas)
            lay.addWidget(chart_card, 1)
        else:
            self.viz_text = QTextEdit()
            self.viz_text.setReadOnly(True)
            lay.addWidget(self.viz_text, 1)
        self.tabs.addTab(tab, "Visualization")

    # ── Tab 4: History ─────────────────────────────────────────────────────────

    def _tab_history(self):
        tab = QWidget()
        tab.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(section_header("Patient History"))

        sr = QHBoxLayout()
        sr.setSpacing(8)
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search by patient name…")
        self.history_search.returnPressed.connect(self._load_history)
        self.history_search.setFixedHeight(40)
        sb = btn_primary("Search")
        sb.clicked.connect(self._load_history)
        rb = btn_secondary("Refresh")
        rb.clicked.connect(self._load_history)
        sr.addWidget(self.history_search, 1)
        sr.addWidget(sb)
        sr.addWidget(rb)
        lay.addLayout(sr)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(
            ["Name", "Blood Type", "Date", "Age", "Gender", "Score A", "Score B"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setShowGrid(False)
        lay.addWidget(self.history_table, 1)

        sc, sl = card((14, 10, 14, 10))
        sl.addWidget(label("Blood type distribution", size=13, bold=True, color=TXT_SEC))
        self.stats_lbl = QLabel("No records yet")
        self.stats_lbl.setStyleSheet(f"color:{TXT_SEC}; font-size:14px; background:transparent;")
        self.stats_lbl.setWordWrap(True)
        sl.addWidget(self.stats_lbl)
        lay.addWidget(sc)
        self.tabs.addTab(tab, "History")

    # ── Patient handler ─────────────────────────────────────────────────────────

    def _submit_patient(self):
        name = self.name_in.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please enter the patient's full name.")
            return
        self._collect_patient()
        pid = save_patient(
            name=name,
            age=self.age_in.value(),
            gender=self.gender_in.currentText(),
            phone=self.phone_in.text().strip(),
            doctor_email=self.doctor_email_in.text().strip(),
            fingerprint_desc=""
        )
        self.current_patient_id = pid
        self.patient_info['id'] = pid
        self.patient_status.setText(
            f"Details saved — {name}  ·  Age {self.age_in.value()}  ·  {self.gender_in.currentText()}"
        )
        self.patient_status.setStyleSheet(f"""
            background:{GREEN_LIGHT}; border:1px solid {GREEN_BDR};
            border-radius:6px; padding:12px 14px; font-size:13px; color:{GREEN};
        """)
        self.tabs.setTabEnabled(1, True)
        self.step_bar.set_step(1)
        self.statusBar().showMessage(f"Patient saved — {name}. Proceed to Blood Test.")

    def _collect_patient(self):
        self.patient_info = {
            'id': self.current_patient_id,
            'name': self.name_in.text().strip() or "—",
            'age': self.age_in.value(),
            'gender': self.gender_in.currentText(),
            'phone': self.phone_in.text().strip(),
            'doctor_email': self.doctor_email_in.text().strip(),
        }

    # ── Blood test handlers ─────────────────────────────────────────────────────

    def _upload_test_img(self, key):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select {key} test image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif)"
        )
        if path:
            if key == 'A':   self.anti_a_path = path
            elif key == 'B': self.anti_b_path = path
            else:            self.anti_d_path = path
            self.test_panels[key].set_image(path)

    def _run_analysis(self):
        if not all([self.anti_a_path, self.anti_b_path, self.anti_d_path]):
            QMessageBox.warning(
                self, "Missing images",
                "Please upload images for all three tests (Anti-A, Anti-B, Anti-D) before analyzing."
            )
            return
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing…")
        self.statusBar().showMessage("Running blood group analysis…")
        self._analysis_thread = AnalysisThread(self.anti_a_path, self.anti_b_path, self.anti_d_path)
        self._analysis_thread.finished.connect(self._on_analysis_done)
        self._analysis_thread.error.connect(self._on_analysis_error)
        self._analysis_thread.start()

    def _on_analysis_error(self, msg):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Run blood group analysis")
        QMessageBox.critical(self, "Analysis error", msg)

    def _on_analysis_done(self, result):
        self.analysis_result = result
        bt  = result['blood_type']
        res = result['results']

        for key in ['A', 'B', 'D']:
            self.test_panels[key].set_result(res[key]['score'], res[key]['positive'])

        self.analysis_detail_widget.set_data(bt, res)

        self.blood_type_badge.setText(f"Blood Group:  {bt}")
        self._collect_patient()
        self.results_text.setText(generate_result_details(res, bt))
        self.compat_text.setText(generate_compatibility_info(bt))
        self._update_chart(res)

        if self.current_patient_id:
            save_blood_result(self.current_patient_id, bt, res)

        for i in range(2, 5):
            self.tabs.setTabEnabled(i, True)
        self.step_bar.set_step(2)
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Run blood group analysis")
        self.statusBar().showMessage(f"Analysis complete — Blood type: {bt}")

    # ── Chart ───────────────────────────────────────────────────────────────────

    def _update_chart(self, results):
        if HAS_MATPLOTLIB:
            self.chart_fig.clear()
            ax = self.chart_fig.add_subplot(111)
            ax.set_facecolor(SURFACE)
            self.chart_fig.patch.set_facecolor(SURFACE)
            labels    = ['Anti-A', 'Anti-B', 'Anti-D']
            scores    = [results['A']['score'], results['B']['score'], results['D']['score']]
            positives = [results['A']['positive'], results['B']['positive'], results['D']['positive']]
            bar_colors = [RED if p else GREEN for p in positives]
            bars = ax.bar(labels, scores, color=bar_colors, width=0.35, edgecolor='none', zorder=3, alpha=0.85)
            ax.axhline(y=40, color=AMBER, linestyle='--', linewidth=1, label='Threshold (40)', zorder=2, alpha=0.8)
            for bar, score, pos in zip(bars, scores, positives):
                ax.text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                    f"{score:.0f}\n{'POS' if pos else 'NEG'}",
                    ha='center', va='bottom', color=TXT_SEC, fontsize=10, fontweight='600'
                )
            ax.set_ylim(0, 115)
            ax.set_ylabel('Agglutination score', color=TXT_TER, fontsize=11)
            ax.set_title('Reagent test scores', color=TXT_PRI, fontsize=13, fontweight='bold', pad=12)
            ax.tick_params(colors=TXT_TER, labelsize=11)
            for spine in ax.spines.values(): spine.set_color(BORDER_L)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.legend(facecolor=SURFACE, edgecolor=BORDER_L, labelcolor=TXT_SEC, fontsize=10)
            ax.grid(axis='y', alpha=0.4, color=BORDER_L, linestyle='-')
            self.chart_fig.tight_layout(pad=2.0)
            self.chart_canvas.draw()
        else:
            if hasattr(self, 'viz_text'):
                self.viz_text.setText(generate_visualization_text(results))

    # ── Report / Email ──────────────────────────────────────────────────────────

    def _save_pdf(self):
        if not self.analysis_result: return
        name = self.patient_info.get('name', 'patient').replace(' ', '_')
        default = f"BloodReport_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF report", default, "PDF Files (*.pdf)")
        if path:
            try:
                generate_pdf_report(self.patient_info, self.analysis_result, path)
                QMessageBox.information(self, "Saved", f"PDF saved:\n{path}")
                self.statusBar().showMessage(f"PDF saved: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not generate PDF:\n{e}")

    def _send_email(self):
        if not self.analysis_result: return
        to = self.patient_info.get('doctor_email', '').strip()
        if not to:
            QMessageBox.warning(self, "No email", "Please enter the doctor's email in the patient form.")
            return
        config = get_email_config()
        if not config:
            QMessageBox.information(self, "Setup required", "Please configure the sender email first.")
            self._open_email_setup()
            return
        tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        os.makedirs(tmp, exist_ok=True)
        name = self.patient_info.get('name', 'patient').replace(' ', '_')
        pdf_path = os.path.join(tmp, f"Report_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
        try:
            generate_pdf_report(self.patient_info, self.analysis_result, pdf_path)
            send_email_report(to, pdf_path, self.patient_info.get('name', '—'), self.analysis_result['blood_type'])
            QMessageBox.information(self, "Sent", f"Report emailed to {to}")
            self.statusBar().showMessage(f"Email sent to {to}")
        except Exception as e:
            QMessageBox.critical(self, "Email error", f"Could not send email:\n{e}")

    def _open_email_setup(self):
        EmailSetupDialog(self).exec_()

    # ── History ─────────────────────────────────────────────────────────────────

    def _on_tab_changed(self, idx):
        if idx == 4:
            self._load_history()

    def _load_history(self):
        q    = self.history_search.text().strip()
        rows = search_history(q) if q else get_all_history()
        self.history_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.history_table.setItem(i, 0, QTableWidgetItem(str(row.get('name', '—'))))
            bt_item = QTableWidgetItem(str(row.get('blood_type', '—')))
            bt_item.setForeground(QColor(RED))
            bt_item.setFont(QFont("IBM Plex Sans", 13, QFont.Bold))
            self.history_table.setItem(i, 1, bt_item)
            self.history_table.setItem(i, 2, QTableWidgetItem(str(row.get('analysis_date', '—'))))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(row.get('age', '—'))))
            self.history_table.setItem(i, 4, QTableWidgetItem(str(row.get('gender', '—'))))
            self.history_table.setItem(i, 5, QTableWidgetItem(f"{row.get('score_a', 0):.1f}"))
            self.history_table.setItem(i, 6, QTableWidgetItem(f"{row.get('score_b', 0):.1f}"))
        stats = get_blood_type_stats()
        if stats:
            total = sum(stats.values())
            parts = [f"{bt}: {cnt} ({cnt/total*100:.0f}%)" for bt, cnt in sorted(stats.items(), key=lambda x: -x[1])]
            self.stats_lbl.setText(f"Total: {total}   ·   " + "   ·   ".join(parts))
        else:
            self.stats_lbl.setText("No records yet")

    # ── Clear / New patient ─────────────────────────────────────────────────────

    def _clear_all(self):
        self.anti_a_path = self.anti_b_path = self.anti_d_path = None
        self.analysis_result    = None
        self.current_patient_id = None
        self.patient_info       = {}
        self.name_in.clear()
        self.age_in.setValue(25)
        self.gender_in.setCurrentIndex(0)
        self.phone_in.clear()
        self.doctor_email_in.clear()
        self.patient_status.setText("")
        self.patient_status.setStyleSheet(f"""
            background:{SURFACE_2}; border:1px solid {BORDER_L};
            border-radius:6px; padding:12px 14px; font-size:13px; color:{TXT_TER};
        """)
        for key in ['A', 'B', 'D']:
            self.test_panels[key].reset()
        self.analysis_detail_widget.clear()
        self.results_text.clear()
        self.compat_text.clear()
        self.blood_type_badge.setText("—")
        if HAS_MATPLOTLIB:
            self.chart_fig.clear()
            self.chart_canvas.draw()
        for i in range(1, 5):
            self.tabs.setTabEnabled(i, False)
        self.tabs.setCurrentIndex(0)
        self.step_bar._current = 0
        self.step_bar._done    = [False, False, False]
        self.step_bar._update_styles()
        self.statusBar().showMessage("Ready — complete patient details to begin")


# ──────────────────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("IBM Plex Sans", 11))
    window = BloodTypingApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()