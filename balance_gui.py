import sys
import json
import base64
import urllib.request
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QInputDialog, QMessageBox, QAbstractItemView, QMenu, QScrollArea,
    QFrame, QStackedWidget, QButtonGroup, QDialog, QComboBox, QFileDialog, QDateEdit, QColorDialog
)
from PyQt6.QtCore import Qt, QSize, QByteArray, QBuffer, QEvent, QDate
from PyQt6.QtGui import QColor, QTextDocument, QPdfWriter, QPixmap, QIcon, QPainter, QPainterPath

from balance_logic import SettingsManager, ProjectManager, BalanceCalculator

APP_VERSION = "0.3.0"

FONT_STACK = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

# Currency formatting mapping: (Prefix, Suffix, Decimals, Space)
CURRENCIES = {
    "RM": ("RM", "", 2, False),
    "$": ("$", "", 2, False),
    "€": ("", "€", 2, True),
    "£": ("£", "", 2, False),
    "¥": ("¥", "", 0, False),
    "A$": ("A$", "", 2, False),
    "C$": ("C$", "", 2, False),
    "₹": ("₹", "", 2, False),
    "S$": ("S$", "", 2, False),
    "CHF": ("", "CHF", 2, True),
    "kr": ("", "kr", 2, True),
}

# ─── Dynamic Stylesheet Generator ──────────────────────────────────────────────

def get_actual_theme(theme_setting):
    if theme_setting.lower() == "system":
        if QApplication.instance():
            scheme = QApplication.styleHints().colorScheme()
            return "dark" if scheme == Qt.ColorScheme.Dark else "light"
        return "light"
    return theme_setting.lower()

def generate_stylesheet(theme_setting, accent_hex):
    actual_theme = get_actual_theme(theme_setting)
    accent = QColor(accent_hex)
    
    if actual_theme == "dark":
        bg = "#121212"
        panel = "#1A1A1A"
        text = "#E0E0E0"
        border = "#333333"
        hover_bg = "#2C2C2C"
        input_bg = "#1E1E1E"
        header_bg = "#161616"
        second_btn = "#333333"
        second_btn_hover = "#444444"
        accent_hover = accent.lighter(115).name()
        accent_pressed = accent.lighter(130).name()
        selection_bg = QColor(accent.red(), accent.green(), accent.blue(), 60).name()
        subtitle_color = "#AAAAAA"
    else:
        bg = "#FFFFFF"
        panel = "#F8F9FA"
        text = "#333333"
        border = "#DEE2E6"
        hover_bg = "#E9ECEF"
        input_bg = "#FFFFFF"
        header_bg = "#F8F9FA"
        second_btn = "#6C757D"
        second_btn_hover = "#5A6268"
        accent_hover = accent.darker(110).name()
        accent_pressed = accent.darker(120).name()
        selection_bg = QColor(accent.red(), accent.green(), accent.blue(), 40).name()
        subtitle_color = "#666666"

    return f"""
    QMainWindow, QDialog, QStackedWidget#rightStack, QWidget#projectView, QWidget#emptyView, QWidget#contentWidget {{ 
        background-color: {bg}; color: {text}; 
    }}
    QWidget#leftPanel {{ background-color: {panel}; }}
    QWidget {{ font-family: {FONT_STACK}; font-size: 13px; }}

    QListWidget {{
        background-color: {input_bg}; border: 1px solid {border}; border-radius: 6px;
        padding: 4px; outline: none; color: {text};
    }}
    QListWidget::item {{ border-radius: 4px; margin: 1px 0; }}
    QListWidget::item:selected {{ background-color: {selection_bg}; border: 1px solid {accent.name()}; color: {text}; }}
    QListWidget::item:hover:!selected {{ background-color: {hover_bg}; }}
    
    QListWidget#settleList::item {{ padding: 8px 12px; }}

    QPushButton {{
        background-color: {accent.name()}; color: #FFFFFF; border: none; border-radius: 6px;
        padding: 7px 16px; font-weight: bold;
    }}
    QPushButton:hover {{ background-color: {accent_hover}; }}
    QPushButton:pressed {{ background-color: {accent_pressed}; }}
    QPushButton:disabled {{ background-color: {border}; color: gray; }}
    QPushButton#secondaryBtn {{ background-color: {second_btn}; }}
    QPushButton#secondaryBtn:hover {{ background-color: {second_btn_hover}; }}
    QPushButton#dangerBtn  {{ background-color: #DC3545; padding: 7px 16px; }}
    QPushButton#dangerBtn:hover {{ background-color: #C82333; }}
    QPushButton#deleteRowBtn {{ background-color: #DC3545; padding: 2px 8px; font-size: 12px; }}
    QPushButton#deleteRowBtn:hover {{ background-color: #C82333; }}

    QPushButton#avatarBtn {{
        background-color: {hover_bg}; color: {text}; border: 2px solid transparent; border-radius: 24px; font-size: 14px; font-weight: bold; padding: 0;
    }}
    QPushButton#avatarBtn:checked {{ background-color: {selection_bg}; border-color: {accent.name()}; color: {text}; }}
    QPushButton#avatarBtn:hover:!checked {{ background-color: {border}; }}
    QPushButton#avatarAddBtn {{
        background-color: transparent; color: {second_btn}; border: 2px dashed {border}; border-radius: 24px; font-size: 18px; padding: 0;
    }}
    QPushButton#avatarAddBtn:hover {{ border-color: {accent.name()}; color: {accent.name()}; background-color: {input_bg}; }}

    QLineEdit, QDateEdit {{
        border: 1px solid {border}; border-radius: 6px; padding: 7px 10px; background-color: {input_bg}; color: {text};
    }}
    QLineEdit:focus, QDateEdit:focus {{ border-color: {accent.name()}; }}
    QLineEdit:disabled, QDateEdit:disabled {{ background-color: {header_bg}; color: {subtitle_color}; border-color: {border}; }}
    QDateEdit::drop-down {{ border: none; padding-right: 5px; }}

    QComboBox {{
        border: 1px solid {border}; border-radius: 6px; padding: 6px 10px; background-color: {input_bg}; color: {text};
    }}
    QComboBox:focus {{ border-color: {accent.name()}; }}
    QComboBox QAbstractItemView, QComboBox QListView {{
        background-color: {input_bg}; color: {text}; selection-background-color: {accent.name()}; selection-color: #FFFFFF;
    }}

    QTableWidget {{
        background-color: {input_bg}; border: 1px solid {border}; border-radius: 6px;
        gridline-color: {border}; color: {text};
    }}
    QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid {border}; }}
    QTableWidget::item:selected {{ background-color: {selection_bg}; color: {text}; }}
    QTableWidget QLineEdit {{ padding: 2px 4px; border: 1px solid {accent.name()}; border-radius: 2px; }}

    QHeaderView::section {{
        background-color: {header_bg}; border: none; border-bottom: 2px solid {border};
        padding: 6px 8px; font-weight: bold; color: {subtitle_color};
    }}

    QLabel {{ background: transparent; color: {text}; }}
    QLabel#headerLabel {{ font-size: 20px; font-weight: bold; color: {text}; }}
    QLabel#sectionLabel {{ font-size: 15px; font-weight: bold; color: {text}; }}
    QLabel#totalLabel {{ font-size: 16px; font-weight: bold; color: {accent.name()}; }}
    QLabel#footerLabel {{ font-size: 11px; color: {subtitle_color}; padding: 6px; }}
    QLabel#subTitleLabel {{ font-size: 11px; color: {subtitle_color}; }}

    QFrame#separator {{ background-color: {border}; max-height: 1px; }}
    QSplitter::handle {{ background-color: {border}; width: 4px; border-radius: 2px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QWidget#avatarContainer {{ background-color: transparent; }}
    """

# ─── Utility Methods ───────────────────────────────────────────────────────────

def create_circular_pixmap(pixmap, size=48):
    target = QPixmap(size, size)
    target.fill(Qt.GlobalColor.transparent)
    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    return target


# ─── Dialogs ───────────────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings_mgr=None):
        super().__init__(parent)
        self.settings_mgr = settings_mgr
        self.setWindowTitle("Settings")
        self.setFixedSize(380, 420)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Theme Section
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_label.setFixedWidth(100)
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        current_theme = self.settings_mgr.get("theme", "system").capitalize()
        self.theme_combo.setCurrentText(current_theme)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # Accent Color Section
        accent_layout = QHBoxLayout()
        accent_label = QLabel("Accent Color:")
        accent_label.setFixedWidth(100)
        accent_layout.addWidget(accent_label)
        
        self.color_hex = self.settings_mgr.get("accent_color", "#4A90D9")
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.setObjectName("secondaryBtn")
        self._update_color_btn_style()
        self.color_btn.clicked.connect(self._pick_color)
        accent_layout.addWidget(self.color_btn)
        layout.addLayout(accent_layout)

        # Project Date Display
        date_layout = QHBoxLayout()
        date_label = QLabel("Project List Date:")
        date_label.setFixedWidth(100)
        date_layout.addWidget(date_label)
        
        self.date_combo = QComboBox()
        self.date_combo.addItems(["Show Last Modified", "Show Created Date"])
        disp_pref = self.settings_mgr.get("project_date_display", "modified")
        self.date_combo.setCurrentIndex(0 if disp_pref == "modified" else 1)
        date_layout.addWidget(self.date_combo)
        layout.addLayout(date_layout)

        # Currency Section
        currency_layout = QHBoxLayout()
        curr_label = QLabel("Currency:")
        curr_label.setFixedWidth(100)
        currency_layout.addWidget(curr_label)
        
        self.curr_combo = QComboBox()
        self.curr_combo.addItems(list(CURRENCIES.keys()))
        current_currency = self.settings_mgr.get("currency", "RM")
        self.curr_combo.setCurrentText(current_currency)
        currency_layout.addWidget(self.curr_combo)
        layout.addLayout(currency_layout)
        
        # Check Updates Button
        update_layout = QHBoxLayout()
        self.update_btn = QPushButton("Check for Updates")
        self.update_btn.setObjectName("secondaryBtn")
        self.update_btn.clicked.connect(self._check_for_updates)
        update_layout.addWidget(self.update_btn)
        layout.addLayout(update_layout)

        layout.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_and_close)
        layout.addWidget(save_btn)

        footer = QLabel(f"2026 Developed by Chen Jin Shen\ncjshen00@gmail.com\n\nVersion {APP_VERSION}")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName("footerLabel")
        layout.addWidget(footer)

    def _update_color_btn_style(self):
        self.color_btn.setStyleSheet(f"background-color: {self.color_hex}; color: #FFFFFF; font-weight: bold;")

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self.color_hex), self, "Select Accent Color")
        if color.isValid():
            self.color_hex = color.name()
            self._update_color_btn_style()

    def _check_for_updates(self):
        self.update_btn.setText("Checking...")
        self.update_btn.setEnabled(False)
        QApplication.processEvents()
        try:
            req = urllib.request.Request(
                "https://github.com/arinltte/Balance-Separator/releases/latest",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response = urllib.request.urlopen(req, timeout=5)
            final_url = response.geturl()
            tag = final_url.split('/')[-1]
            
            current_tag = f"v{APP_VERSION}"
            if tag > current_tag:
                QMessageBox.information(self, "Update Available", f"A new version ({tag}) is available!\nPlease check GitHub to download the latest release.")
            else:
                QMessageBox.information(self, "Up to Date", f"You are running the latest version ({current_tag}).")
        except Exception:
            QMessageBox.warning(self, "Update Check Failed", "Could not connect to GitHub to check for updates.")
        finally:
            self.update_btn.setText("Check for Updates")
            self.update_btn.setEnabled(True)

    def _save_and_close(self):
        self.settings_mgr.set("theme", self.theme_combo.currentText().lower())
        self.settings_mgr.set("accent_color", self.color_hex)
        self.settings_mgr.set("currency", self.curr_combo.currentText())
        self.settings_mgr.set("project_date_display", "modified" if self.date_combo.currentIndex() == 0 else "created")
        
        style = generate_stylesheet(self.settings_mgr.get("theme"), self.color_hex)
        QApplication.instance().setStyleSheet(style)
        self.accept()


class ProjectEditDialog(QDialog):
    def __init__(self, parent, project):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Edit Project Details")
        self.setFixedSize(350, 420)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Project Name:"))
        self.name_input = QLineEdit(project.name)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Start Date:"))
        self.start_input = QDateEdit()
        self.start_input.setCalendarPopup(True)
        if project.start_date:
            self.start_input.setDate(QDate.fromString(project.start_date, Qt.DateFormat.ISODate))
        else:
            self.start_input.setDate(QDate.currentDate())
        layout.addWidget(self.start_input)

        layout.addWidget(QLabel("End Date:"))
        self.end_input = QDateEdit()
        self.end_input.setCalendarPopup(True)
        if project.end_date:
            self.end_input.setDate(QDate.fromString(project.end_date, Qt.DateFormat.ISODate))
        else:
            self.end_input.setDate(QDate.currentDate())
        layout.addWidget(self.end_input)

        layout.addWidget(QLabel("Description (Optional):"))
        self.desc_input = QLineEdit(project.description)
        layout.addWidget(self.desc_input)

        layout.addStretch()

        del_btn = QPushButton("Delete Project")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_project)
        layout.addWidget(del_btn)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)

    def _delete_project(self):
        reply = QMessageBox.question(
            self, "Delete Project", 
            f"Are you sure you want to permanently delete '{self.project.name}'?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.done(2)


class TeammateEditDialog(QDialog):
    def __init__(self, parent, teammate):
        super().__init__(parent)
        self.teammate = teammate
        self.avatar_b64 = teammate.avatar_data
        
        self.setWindowTitle("Edit Teammate")
        self.setFixedSize(380, 400)
        
        layout = QVBoxLayout(self)
        
        av_layout = QHBoxLayout()
        self.pic_label = QLabel()
        self.pic_label.setFixedSize(80, 80)
        self._update_pic_label()
        
        btn_col = QVBoxLayout()
        btn_pic = QPushButton("Upload Photo")
        btn_pic.setObjectName("secondaryBtn")
        btn_pic.clicked.connect(self._choose_picture)
        
        btn_rem = QPushButton("Remove Photo")
        btn_rem.setObjectName("secondaryBtn")
        btn_rem.clicked.connect(self._remove_picture)

        btn_col.addWidget(btn_pic)
        btn_col.addWidget(btn_rem)
        btn_col.addStretch()

        av_layout.addWidget(self.pic_label)
        av_layout.addLayout(btn_col)
        av_layout.addStretch()
        layout.addLayout(av_layout)

        layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(self.teammate.name)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Description (Optional):"))
        self.desc_input = QLineEdit(self.teammate.description)
        layout.addWidget(self.desc_input)

        layout.addStretch()

        del_btn = QPushButton("Delete Teammate")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_teammate)
        layout.addWidget(del_btn)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _update_pic_label(self):
        if self.avatar_b64:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(self.avatar_b64))
            self.pic_label.setPixmap(create_circular_pixmap(pixmap, 80))
        else:
            self.pic_label.setText("No Image")
            self.pic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pic_label.setStyleSheet("border: 1px dashed #AAA; border-radius: 40px;")

    def _choose_picture(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Profile Picture", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            pixmap = QPixmap(path)
            pixmap = pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            pixmap.save(buffer, "JPEG", 80)
            self.avatar_b64 = base64.b64encode(byte_array.data()).decode('utf-8')
            self._update_pic_label()

    def _remove_picture(self):
        self.avatar_b64 = ""
        self._update_pic_label()

    def _delete_teammate(self):
        reply = QMessageBox.question(
            self, "Delete Teammate", 
            f"Are you sure you want to permanently delete '{self.teammate.name}' and all their expenses?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.done(2)


# ─── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings_mgr = SettingsManager()
        self.project_mgr = ProjectManager()
        self.current_project_idx: int = -1
        self.current_teammate_idx: int = -1

        self.avatar_btn_group = QButtonGroup(self)
        self.avatar_btn_group.setExclusive(True)
        self.avatar_btn_group.idClicked.connect(self._on_teammate_changed)

        self._build_ui()
        self._apply_theme()
        self._restore_splitters()
        
        self.showMaximized()
        self._refresh_projects()

    def _apply_theme(self):
        theme = self.settings_mgr.get("theme", "system")
        accent = self.settings_mgr.get("accent_color", "#4A90D9")
        style = generate_stylesheet(theme, accent)
        QApplication.instance().setStyleSheet(style)

    def _format_money(self, amount: float) -> str:
        curr_key = self.settings_mgr.get("currency", "RM")
        prefix, suffix, decs, use_space = CURRENCIES.get(curr_key, ("RM", "", 2, False))
        amt_str = f"{amount:,.{decs}f}"
        space = " " if use_space else ""
        
        if prefix: return f"{prefix}{space}{amt_str}"
        return f"{amt_str}{space}{suffix}"

    def _build_ui(self):
        self.setWindowTitle("Balance Separator")
        self.setMinimumSize(950, 650)

        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QHBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left Panel ──
        left = QWidget()
        left.setObjectName("leftPanel")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(16, 20, 16, 16)
        
        lbl_projects = QLabel("📁  Projects")
        lbl_projects.setObjectName("sectionLabel")
        left_lay.addWidget(lbl_projects)

        self.project_list = QListWidget()
        self.project_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.project_list.currentRowChanged.connect(self._on_project_changed)
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._project_context_menu)
        left_lay.addWidget(self.project_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        btn_new = QPushButton("+ New")
        btn_new.setObjectName("secondaryBtn")
        btn_new.clicked.connect(self._add_project)
        
        btn_import = QPushButton("⬇ Import")
        btn_import.setObjectName("secondaryBtn")
        btn_import.clicked.connect(self._import_project)
        
        btn_layout.addWidget(btn_new)
        btn_layout.addWidget(btn_import)
        left_lay.addLayout(btn_layout)
        
        left.setMinimumWidth(220)

        # ── Right Panel ──
        right = QWidget()
        right.setObjectName("rightPanel")
        right_outer = QVBoxLayout(right)
        right_outer.setContentsMargins(0, 0, 0, 0)

        # Global Top Bar (Always Visible)
        top_bar_widget = QWidget()
        top_bar_widget.setContentsMargins(24, 20, 24, 10)
        top_bar_lay = QHBoxLayout(top_bar_widget)
        top_bar_lay.setContentsMargins(0, 0, 0, 0)
        
        self.global_title = QLabel("Welcome to Balance Separator")
        self.global_title.setObjectName("headerLabel")
        top_bar_lay.addWidget(self.global_title)
        
        self.global_dates = QLabel("")
        self.global_dates.setObjectName("footerLabel")
        top_bar_lay.addWidget(self.global_dates)
        
        top_bar_lay.addStretch()

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setObjectName("secondaryBtn")
        self.settings_btn.setFixedSize(100, 32)
        self.settings_btn.clicked.connect(self._open_settings)
        top_bar_lay.addWidget(self.settings_btn)

        right_outer.addWidget(top_bar_widget)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        right_outer.addWidget(sep)

        # ── Stacked Content Area ──
        self.right_stack = QStackedWidget()
        self.right_stack.setObjectName("rightStack")
        
        # Empty View
        self.empty_view = QWidget()
        self.empty_view.setObjectName("emptyView")
        empty_lay = QVBoxLayout(self.empty_view)
        empty_lbl = QLabel("Select or create a project to begin.")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setObjectName("footerLabel")
        empty_lay.addWidget(empty_lbl)
        self.right_stack.addWidget(self.empty_view)

        # Project View
        self.project_view = QWidget()
        self.project_view.setObjectName("projectView")
        right_lay = QVBoxLayout(self.project_view)
        right_lay.setContentsMargins(24, 10, 24, 20)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.left_col_widget = QWidget()
        self.left_col_layout = QVBoxLayout(self.left_col_widget)
        self.left_col_layout.setContentsMargins(0, 0, 15, 0)
        self._build_teammates_section(self.left_col_layout)
        self._build_expenses_section(self.left_col_layout)
        
        self.right_col_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.top_right_widget = QWidget()
        top_right_layout = QVBoxLayout(self.top_right_widget)
        top_right_layout.setContentsMargins(15, 0, 0, 10)
        self._build_balance_section(top_right_layout)

        self.bottom_right_widget = QWidget()
        bottom_right_layout = QVBoxLayout(self.bottom_right_widget)
        bottom_right_layout.setContentsMargins(15, 10, 0, 0)
        self._build_settlement_section(bottom_right_layout)

        bottom_bar = QHBoxLayout()
        self.total_label = QLabel("Total Expenses:")
        self.total_label.setObjectName("totalLabel")
        bottom_bar.addWidget(self.total_label)
        bottom_bar.addStretch()
        
        btn_export = QPushButton("📄  Export")
        btn_export.setObjectName("secondaryBtn")
        btn_export.clicked.connect(self._show_export_menu)
        bottom_bar.addWidget(btn_export)

        bottom_right_layout.addLayout(bottom_bar)

        self.right_col_splitter.addWidget(self.top_right_widget)
        self.right_col_splitter.addWidget(self.bottom_right_widget)

        self.content_splitter.addWidget(self.left_col_widget)
        self.content_splitter.addWidget(self.right_col_splitter)

        right_lay.addWidget(self.content_splitter)
        self.right_stack.addWidget(self.project_view)
        
        right_outer.addWidget(self.right_stack, 1)

        self.main_splitter.addWidget(left)
        self.main_splitter.addWidget(right)
        outer_layout.addWidget(self.main_splitter)

    # ── Section builders ──

    def _build_teammates_section(self, parent_layout):
        lbl = QLabel("👥  Teammates")
        lbl.setObjectName("sectionLabel")
        parent_layout.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(75)

        avatar_container = QWidget()
        avatar_container.setObjectName("avatarContainer")
        self.avatar_layout = QHBoxLayout(avatar_container)
        self.avatar_layout.setContentsMargins(0, 5, 0, 5)
        self.avatar_layout.setSpacing(12)
        
        scroll.setWidget(avatar_container)
        scroll.setWidgetResizable(True)
        parent_layout.addWidget(scroll)

    def _build_expenses_section(self, parent_layout):
        self.expense_section_label = QLabel("💰  Paid By Selected Teammate")
        self.expense_section_label.setObjectName("sectionLabel")
        parent_layout.addWidget(self.expense_section_label)

        row = QHBoxLayout()
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description (Optional)")
        self.desc_input.installEventFilter(self)
        row.addWidget(self.desc_input, 3)

        self.amt_input = QLineEdit()
        self.amt_input.setMaximumWidth(130)
        self.amt_input.installEventFilter(self)
        row.addWidget(self.amt_input, 1)

        self.add_exp_btn = QPushButton("+  Add")
        self.add_exp_btn.clicked.connect(self._add_expense)
        row.addWidget(self.add_exp_btn)
        parent_layout.addLayout(row)

        self.exp_table = QTableWidget(0, 3)
        self.exp_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.exp_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.exp_table.setHorizontalHeaderLabels(["Description", "Amount", ""])
        header = self.exp_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.exp_table.setColumnWidth(2, 44)
        
        self.exp_table.verticalHeader().setVisible(False)
        self.exp_table.verticalHeader().setDefaultSectionSize(34) 
        
        self.exp_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.exp_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.exp_table.setMinimumHeight(150)
        self.exp_table.cellChanged.connect(self._on_expense_description_changed)
        parent_layout.addWidget(self.exp_table)

    def _build_balance_section(self, parent_layout):
        lbl = QLabel("📊  Balance Summary")
        lbl.setObjectName("sectionLabel")
        parent_layout.addWidget(lbl)

        self.bal_table = QTableWidget(0, 4)
        self.bal_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bal_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bal_table.setHorizontalHeaderLabels(["Name", "Total Paid", "Fair Share", "Balance"])
        self.bal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bal_table.verticalHeader().setVisible(False)
        self.bal_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bal_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bal_table.setMinimumHeight(150)
        parent_layout.addWidget(self.bal_table)

    def _build_settlement_section(self, parent_layout):
        lbl = QLabel("🔄  Settlements (Who Pays Whom)")
        lbl.setObjectName("sectionLabel")
        parent_layout.addWidget(lbl)

        self.settle_list = QListWidget()
        self.settle_list.setObjectName("settleList")
        self.settle_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settle_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settle_list.setMinimumHeight(100)
        self.settle_list.itemChanged.connect(self._on_settlement_checked)
        parent_layout.addWidget(self.settle_list)

    # ── Smart Input Event Filter ──
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if obj == self.amt_input:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._add_expense()
                    return True
                text = event.text()
                if text.isalpha() and self.amt_input.text().strip() == "":
                    self.desc_input.setFocus()
                    self.desc_input.setText(text)
                    return True
                elif text.isalpha():
                    return True 

            elif obj == self.desc_input:
                text = event.text()
                if text.isdigit() and self.desc_input.text().strip() == "":
                    self.amt_input.setFocus()
                    self.amt_input.setText(text)
                    return True
                elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.amt_input.setFocus()
                    return True
        return super().eventFilter(obj, event)

    # ── UI Actions ──
    def _create_project_list_widget(self, project) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(2)
        
        lbl_title = QLabel(project.name)
        lbl_title.setStyleSheet("font-weight: bold;")
        
        disp_pref = self.settings_mgr.get("project_date_display", "modified")
        date_str = project.updated_at if disp_pref == "modified" else project.created_at
        try:
            dt = datetime.fromisoformat(date_str)
            date_label = dt.strftime("%b %d, %Y %H:%M")
        except:
            date_label = "Unknown date"
            
        prefix = "Modified: " if disp_pref == "modified" else "Created: "
        lbl_sub = QLabel(f"{prefix}{date_label}")
        lbl_sub.setObjectName("subTitleLabel")
        
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_sub)
        return widget

    def _refresh_projects(self):
        self.project_list.blockSignals(True)
        self.project_list.clear()
        
        for p in self.project_mgr.projects:
            item = QListWidgetItem()
            item.setSizeHint(QSize(200, 48))
            self.project_list.addItem(item)
            widget = self._create_project_list_widget(p)
            self.project_list.setItemWidget(item, widget)

        self.project_list.blockSignals(False)

        if self.project_mgr.projects:
            self.current_project_idx = max(0, min(self.current_project_idx, len(self.project_mgr.projects) - 1))
            self.project_list.setCurrentRow(self.current_project_idx)
        else:
            self.current_project_idx = -1
            self.global_title.setText("Welcome to Balance Separator")
            self.global_dates.setText("")

        self._refresh_right()

    def _update_project_list_item(self, idx: int):
        """Silently updates the subtitle timestamp of a specific project item without a full list rebuild."""
        item = self.project_list.item(idx)
        if item:
            project = self.project_mgr.get_project(idx)
            new_widget = self._create_project_list_widget(project)
            self.project_list.setItemWidget(item, new_widget)

    def _on_project_changed(self, row: int):
        self.current_project_idx = row
        self.current_teammate_idx = -1
        self._refresh_right()

    def _add_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if ok and name.strip():
            self.project_mgr.add_project(name.strip())
            self.current_project_idx = len(self.project_mgr.projects) - 1
            self._refresh_projects()
            
    def _import_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Project JSON", "", "JSON Files (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Validation check
            if not isinstance(data, dict) or "name" not in data or "teammates" not in data:
                raise ValueError("Invalid project JSON structure.")
                
            proj = self.project_mgr._from_json([data])[0]
            self.project_mgr.projects.append(proj)
            self.project_mgr.save()
            
            self.current_project_idx = len(self.project_mgr.projects) - 1
            self._refresh_projects()
            QMessageBox.information(self, "Import Successful", f"Project '{proj.name}' imported successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Import Failed", f"Could not import file:\n{str(e)}")

    def _project_context_menu(self, pos):
        item = self.project_list.itemAt(pos)
        if not item: return
        row = self.project_list.row(item)
        menu = QMenu(self)
        act_edit = menu.addAction("✏️  Edit Project")
        chosen = menu.exec(self.project_list.mapToGlobal(pos))

        if chosen == act_edit:
            project = self.project_mgr.get_project(row)
            if not project: return
            
            dlg = ProjectEditDialog(self, project)
            res = dlg.exec()
            
            if res == QDialog.DialogCode.Accepted:
                self.project_mgr.update_project(
                    row, 
                    dlg.name_input.text().strip(), 
                    dlg.desc_input.text().strip(),
                    dlg.start_input.date().toString(Qt.DateFormat.ISODate),
                    dlg.end_input.date().toString(Qt.DateFormat.ISODate)
                )
                self._update_project_list_item(row)
                self._refresh_right()
            elif res == 2:
                self.project_mgr.remove_project(row)
                self.current_project_idx = min(self.current_project_idx, len(self.project_mgr.projects) - 1)
                self._refresh_projects()

    def _get_initials(self, name: str) -> str:
        parts = name.strip().split()
        if not parts: return "?"
        if len(parts) == 1: return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def _refresh_teammates(self):
        for btn in self.avatar_btn_group.buttons():
            self.avatar_btn_group.removeButton(btn)

        while self.avatar_layout.count():
            child = self.avatar_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        project = self.project_mgr.get_project(self.current_project_idx)
        if not project: return

        for i, t in enumerate(project.teammates):
            btn = QPushButton()
            btn.setObjectName("avatarBtn")
            btn.setFixedSize(48, 48)
            btn.setCheckable(True)
            
            tooltip = t.name
            if t.description: tooltip += f"\n({t.description})"
            btn.setToolTip(tooltip)
            
            if t.avatar_data:
                pixmap = QPixmap()
                pixmap.loadFromData(base64.b64decode(t.avatar_data))
                btn.setIcon(QIcon(create_circular_pixmap(pixmap, 48)))
                btn.setIconSize(QSize(48, 48))
            else:
                btn.setText(self._get_initials(t.name))
                
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, idx=i, b=btn: self._teammate_context_menu(b.mapToGlobal(pos), idx))
            
            self.avatar_btn_group.addButton(btn, i)
            self.avatar_layout.addWidget(btn)

        add_btn = QPushButton("+")
        add_btn.setObjectName("avatarAddBtn")
        add_btn.setFixedSize(48, 48)
        add_btn.clicked.connect(self._add_teammate)
        self.avatar_layout.addWidget(add_btn)
        self.avatar_layout.addStretch()

        if project.teammates:
            if self.current_teammate_idx < 0 or self.current_teammate_idx >= len(project.teammates):
                self.current_teammate_idx = 0
            selected_btn = self.avatar_btn_group.button(self.current_teammate_idx)
            if selected_btn: selected_btn.setChecked(True)
        else:
            self.current_teammate_idx = -1

        self._update_expense_ui_state()

    def _on_teammate_changed(self, button_id: int):
        self.current_teammate_idx = button_id
        self._update_expense_ui_state()
        self._refresh_expenses()

    def _add_teammate(self):
        name, ok = QInputDialog.getText(self, "Add Teammate", "Teammate name:")
        if ok and name.strip():
            result = self.project_mgr.add_teammate(self.current_project_idx, name.strip())
            if result is None:
                QMessageBox.warning(self, "Duplicate", "A teammate with that name already exists.")
                return
            self._update_project_list_item(self.current_project_idx)
            project = self.project_mgr.get_project(self.current_project_idx)
            self.current_teammate_idx = len(project.teammates) - 1
            self._refresh_right()

    def _teammate_context_menu(self, pos, tidx: int):
        project = self.project_mgr.get_project(self.current_project_idx)
        if not project or tidx >= len(project.teammates): return

        menu = QMenu(self)
        act_edit = menu.addAction("✏️  Edit Teammate")
        chosen = menu.exec(pos)

        if chosen == act_edit:
            dlg = TeammateEditDialog(self, project.teammates[tidx])
            res = dlg.exec()
            
            if res == QDialog.DialogCode.Accepted:
                self.project_mgr.update_teammate(
                    self.current_project_idx, tidx, 
                    dlg.name_input.text().strip(), 
                    dlg.desc_input.text().strip(), 
                    dlg.avatar_b64
                )
                self._update_project_list_item(self.current_project_idx)
                self._refresh_right()
            elif res == 2:
                self.project_mgr.remove_teammate(self.current_project_idx, tidx)
                if self.current_teammate_idx == tidx:
                    self.current_teammate_idx = -1
                elif self.current_teammate_idx > tidx:
                    self.current_teammate_idx -= 1
                self._update_project_list_item(self.current_project_idx)
                self._refresh_right()

    def _update_expense_ui_state(self):
        has_teammate = self.current_teammate_idx >= 0
        self.desc_input.setEnabled(has_teammate)
        self.amt_input.setEnabled(has_teammate)
        self.add_exp_btn.setEnabled(has_teammate)
        
        curr = self.settings_mgr.get("currency", "RM")
        self.amt_input.setPlaceholderText(f"Amount ({curr})")

        if has_teammate:
            project = self.project_mgr.get_project(self.current_project_idx)
            if project and 0 <= self.current_teammate_idx < len(project.teammates):
                self.expense_section_label.setText(f"💰  Paid By {project.teammates[self.current_teammate_idx].name}")
                self.desc_input.setPlaceholderText("Description (Optional)")
        else:
            self.expense_section_label.setText("💰  Paid By Selected Teammate")
            self.desc_input.setPlaceholderText("Select a teammate first...")

    def _refresh_expenses(self):
        self.exp_table.blockSignals(True)
        self.exp_table.setRowCount(0)
        project = self.project_mgr.get_project(self.current_project_idx)
        if not project or self.current_teammate_idx < 0: 
            self.exp_table.blockSignals(False)
            return

        for ei, e in enumerate(project.teammates[self.current_teammate_idx].expenses):
            self._insert_expense_row(self.current_teammate_idx, ei, e.description, e.amount)
        self.exp_table.blockSignals(False)

    def _insert_expense_row(self, ti: int, ei: int, desc: str, amount: float):
        row = self.exp_table.rowCount()
        self.exp_table.insertRow(row)
        
        item_desc = QTableWidgetItem(desc)
        item_desc.setFlags(item_desc.flags() | Qt.ItemFlag.ItemIsEditable)
        self.exp_table.setItem(row, 0, item_desc)

        item_amt = QTableWidgetItem(self._format_money(amount))
        item_amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item_amt.setFlags(item_amt.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.exp_table.setItem(row, 1, item_amt)

        btn = QPushButton("✕")
        btn.setObjectName("deleteRowBtn")
        btn.setFixedSize(34, 24)
        btn.clicked.connect(lambda _, t=ti, idx=ei: self._remove_expense(t, idx))
        self.exp_table.setCellWidget(row, 2, btn)

    def _on_expense_description_changed(self, row, col):
        if col == 0:
            new_desc = self.exp_table.item(row, col).text()
            self.project_mgr.update_expense_description(self.current_project_idx, self.current_teammate_idx, row, new_desc)
            self._update_project_list_item(self.current_project_idx)

    def _add_expense(self):
        desc = self.desc_input.text().strip() or "Undefined"
        
        amt_text = self.amt_input.text().strip()
        for sym in list(CURRENCIES.keys()) + [" ", ","]:
            amt_text = amt_text.replace(sym, "")

        try:
            amt = float(amt_text)
            if amt <= 0: raise ValueError
        except ValueError:
            if amt_text != "":
                QMessageBox.warning(self, "Invalid", "Please enter a valid positive amount.")
            return

        self.project_mgr.add_expense(self.current_project_idx, self.current_teammate_idx, desc, amt)
        self._update_project_list_item(self.current_project_idx)
        
        self.desc_input.clear()
        self.amt_input.clear()
        self.amt_input.setFocus()
        self._refresh_expenses()
        self._refresh_summary()

    def _remove_expense(self, tidx: int, eidx: int):
        self.project_mgr.remove_expense(self.current_project_idx, tidx, eidx)
        self._update_project_list_item(self.current_project_idx)
        self._refresh_expenses()
        self._refresh_summary()

    def _refresh_summary(self):
        project = self.project_mgr.get_project(self.current_project_idx)
        self.bal_table.setRowCount(0)
        
        self.settle_list.blockSignals(True)
        self.settle_list.clear()

        if not project or not project.teammates:
            self.total_label.setText(f"Total Expenses:  {self._format_money(0.0)}")
            self.settle_list.blockSignals(False)
            return

        summary, settlements, total = BalanceCalculator.calculate(project)

        # ── Update Balances ──
        for name, data in summary.items():
            row = self.bal_table.rowCount()
            self.bal_table.insertRow(row)

            c0 = QTableWidgetItem(name)
            self.bal_table.setItem(row, 0, c0)

            c1 = QTableWidgetItem(self._format_money(data['paid']))
            c1.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.bal_table.setItem(row, 1, c1)

            c2 = QTableWidgetItem(self._format_money(data['share']))
            c2.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.bal_table.setItem(row, 2, c2)

            net = data["net"]
            sign = "+" if net > 0 else ""
            c3 = QTableWidgetItem(f"{sign}{self._format_money(abs(net))}")
            c3.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if net > 0: c3.setForeground(QColor("#27AE60"))
            elif net < 0:
                c3.setForeground(QColor("#E74C3C"))
                c3.setText(f"-{self._format_money(abs(net))}")
            self.bal_table.setItem(row, 3, c3)

        # ── Update Settlements ──
        if not settlements:
            item = QListWidgetItem("✅ All settled! No transfers needed.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.settle_list.addItem(item)
        else:
            saved_settlements = self.settings_mgr.get("settlements", {}).get(project.name, [])
            
            for s in settlements:
                # Key is precise integer (cents) to avoid float mismatch persistence bugs
                cents_amt = int(round(s['amount'] * 100))
                key = f"{s['from']}_{s['to']}_{cents_amt}"
                is_settled = key in saved_settlements
                
                text = f"{s['from']}  ➜  {s['to']}:  {self._format_money(s['amount'])}"
                item = QListWidgetItem(text)
                
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if is_settled else Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, key)
                
                font = item.font()
                font.setStrikeOut(is_settled)
                item.setFont(font)
                if is_settled:
                    item.setForeground(QColor("#888888"))
                
                self.settle_list.addItem(item)

        self.settle_list.blockSignals(False)
        self.total_label.setText(f"Total Expenses:  {self._format_money(total)}")

    def _on_settlement_checked(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        checked = item.checkState() == Qt.CheckState.Checked
        
        project = self.project_mgr.get_project(self.current_project_idx)
        if project:
            self.settings_mgr.toggle_settlement(project.name, key, checked)
        
        font = item.font()
        font.setStrikeOut(checked)
        item.setFont(font)
        
        if checked:
            item.setForeground(QColor("#888888"))
        else:
            is_dark = get_actual_theme(self.settings_mgr.get("theme", "system")) == "dark"
            item.setForeground(QColor("#E0E0E0") if is_dark else QColor("#333333"))

    def _refresh_right(self):
        project = self.project_mgr.get_project(self.current_project_idx)
        if not project:
            self.right_stack.setCurrentIndex(0)
            self.global_title.setText("Welcome to Balance Separator")
            self.global_dates.setText("")
            return

        self.right_stack.setCurrentIndex(1)
        self.global_title.setText(project.name)
        
        dates_text = ""
        if project.start_date and project.end_date:
            dates_text = f" ({project.start_date} to {project.end_date})"
        self.global_dates.setText(dates_text)

        self._refresh_teammates()
        self._refresh_expenses()
        self._refresh_summary()

    def _show_export_menu(self):
        project = self.project_mgr.get_project(self.current_project_idx)
        if not project: return
        menu = QMenu(self)
        act_pdf = menu.addAction("📄  Export to PDF")
        act_excel = menu.addAction("📊  Export to Excel")
        act_json = menu.addAction("📦  Export to JSON")
        btn = self.sender()
        chosen = menu.exec(btn.mapToGlobal(btn.rect().topRight()))
        
        if chosen == act_pdf: self._export_pdf(project)
        elif chosen == act_excel: self._export_excel(project)
        elif chosen == act_json: self._export_json(project)

    def _export_json(self, project):
        path, _ = QFileDialog.getSaveFileName(self, "Export Project JSON", f"{project.name}.json", "JSON Files (*.json)")
        if not path: return
        try:
            data = self.project_mgr._to_json([project])[0]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            QMessageBox.information(self, "Export Successful", f"JSON saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Could not export file:\n{str(e)}")

    def _export_pdf(self, project):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"{project.name}_Report.pdf", "PDF Files (*.pdf)")
        if not path: return

        summary, settlements, total = BalanceCalculator.calculate(project)
        dates_html = f"<p><strong>Duration:</strong> {project.start_date} to {project.end_date}</p>" if project.start_date else ""
        desc_html = f"<p><strong>Description:</strong> {project.description}</p>" if project.description else ""

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Helvetica, Arial, sans-serif; color: #333; }}
                h1, h2 {{ color: #2A6099; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f4f4f4; }}
                .right {{ text-align: right; }}
                .green {{ color: #27AE60; }}
                .red {{ color: #E74C3C; }}
                .strike {{ text-decoration: line-through; color: #999; }}
            </style>
        </head>
        <body>
            <h1>{project.name} - Balance Report</h1>
            {desc_html}
            {dates_html}
            <p><strong>Total Project Expenses:</strong> {self._format_money(total)}</p>
            
            <h2>1. Balance Summary</h2>
            <table>
                <tr><th>Name</th><th class="right">Total Paid</th><th class="right">Fair Share</th><th class="right">Balance</th></tr>
        """
        for name, data in summary.items():
            net = data["net"]
            color = "green" if net > 0 else "red" if net < 0 else ""
            sign = "+" if net > 0 else "-" if net < 0 else ""
            html += f"<tr><td>{name}</td><td class='right'>{self._format_money(data['paid'])}</td><td class='right'>{self._format_money(data['share'])}</td><td class='right {color}'>{sign}{self._format_money(abs(net))}</td></tr>"
        html += "</table>"

        html += "<h2>2. Settlements</h2><ul>"
        if not settlements: html += "<li>✅ All settled! No transfers needed.</li>"
        else:
            saved_settlements = self.settings_mgr.get("settlements", {}).get(project.name, [])
            for s in settlements:
                cents_amt = int(round(s['amount'] * 100))
                key = f"{s['from']}_{s['to']}_{cents_amt}"
                css = "class='strike'" if key in saved_settlements else ""
                html += f"<li {css} style='margin-bottom:10px;'><strong>{s['from']}</strong> pays <strong>{s['to']}</strong>: {self._format_money(s['amount'])}</li>"
        html += "</ul>"

        html += """
            <div style="page-break-before: always;"></div>
            <h2>3. Detailed Expenses List</h2>
            <table><tr><th>Paid By</th><th>Description</th><th class="right">Amount</th></tr>
        """
        for t in project.teammates:
            for e in t.expenses:
                html += f"<tr><td>{t.name}</td><td>{e.description}</td><td class='right'>{self._format_money(e.amount)}</td></tr>"
        html += "</table></body></html>"

        doc = QTextDocument()
        doc.setHtml(html)
        writer = QPdfWriter(path)
        doc.print(writer)
        QMessageBox.information(self, "Export Successful", f"PDF saved to:\n{path}")

    def _export_excel(self, project):
        try:
            import pandas as pd
        except ImportError:
            QMessageBox.critical(self, "Missing", "Install via terminal:\npip install pandas openpyxl")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", f"{project.name}_Report.xlsx", "Excel Files (*.xlsx)")
        if not path: return

        summary, settlements, _ = BalanceCalculator.calculate(project)
        curr = self.settings_mgr.get("currency", "RM")

        df_bal = pd.DataFrame([{"Name": k, f"Total Paid ({curr})": v["paid"], f"Fair Share ({curr})": v["share"], f"Balance ({curr})": v["net"]} for k, v in summary.items()])
        
        settle_data = []
        saved_settlements = self.settings_mgr.get("settlements", {}).get(project.name, [])
        for s in settlements:
            cents_amt = int(round(s['amount'] * 100))
            key = f"{s['from']}_{s['to']}_{cents_amt}"
            settle_data.append({"From": s["from"], "To": s["to"], f"Amount ({curr})": s["amount"], "Paid": "Yes" if key in saved_settlements else "No"})
        df_settle = pd.DataFrame(settle_data)

        df_exp = pd.DataFrame([{"Paid By": t.name, "Description": e.description, f"Amount ({curr})": e.amount} for t in project.teammates for e in t.expenses])

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            if not df_bal.empty: df_bal.to_excel(writer, sheet_name="Summary & Settlements", index=False, startrow=0)
            if not df_settle.empty: df_settle.to_excel(writer, sheet_name="Summary & Settlements", index=False, startrow=len(df_bal) + 3)
            if not df_exp.empty: df_exp.to_excel(writer, sheet_name="Detailed Expenses", index=False)
        QMessageBox.information(self, "Export Successful", f"Excel saved to:\n{path}")

    def _open_settings(self):
        if SettingsDialog(self, self.settings_mgr).exec():
            self._apply_theme()
            self._refresh_projects()  # Updates timestamps/currency throughout UI

    def _restore_splitters(self):
        self.main_splitter.setSizes(self.settings_mgr.get("left_panel_sizes", [250, 850]))
        self.content_splitter.setSizes(self.settings_mgr.get("content_splitter_sizes", [400, 400]))
        self.right_col_splitter.setSizes(self.settings_mgr.get("right_col_sizes", [300, 300]))

    def closeEvent(self, event):
        if self.main_splitter.sizes(): self.settings_mgr.set("left_panel_sizes", self.main_splitter.sizes())
        if self.content_splitter.sizes(): self.settings_mgr.set("content_splitter_sizes", self.content_splitter.sizes())
        if self.right_col_splitter.sizes(): self.settings_mgr.set("right_col_sizes", self.right_col_splitter.sizes())
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

