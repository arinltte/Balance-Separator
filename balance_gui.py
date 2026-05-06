"""
balance_gui.py
PyQt6 GUI for the Balance Separator app.
Imports all business logic from balance_logic.
"""

import sys
import base64
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QInputDialog, QMessageBox, QAbstractItemView, QMenu, QScrollArea,
    QFrame, QStackedWidget, QButtonGroup, QDialog, QComboBox, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, QByteArray, QBuffer, QEvent
from PyQt6.QtGui import QColor, QTextDocument, QPdfWriter, QPixmap, QIcon, QPainter, QPainterPath

from balance_logic import SettingsManager, ProjectManager, BalanceCalculator

# ─── Stylesheets ───────────────────────────────────────────────────────────────

FONT_STACK = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

LIGHT_STYLE = f"""
QMainWindow, QDialog, QStackedWidget#rightStack, QWidget#projectView, QWidget#emptyView, QWidget#contentWidget {{ 
    background-color: #FFFFFF; color: #333333; 
}}
QWidget#leftPanel {{ background-color: #F8F9FA; }}
QWidget {{ font-family: {FONT_STACK}; font-size: 13px; }}

QListWidget {{
    background-color: #FFFFFF; border: 1px solid #DEE2E6; border-radius: 6px;
    padding: 4px; outline: none; color: #333333;
}}
QListWidget::item {{ padding: 8px 12px; border-radius: 4px; margin: 1px 0; }}
QListWidget::item:selected {{ background-color: #4A90D9; color: #FFFFFF; }}
QListWidget::item:hover:!selected {{ background-color: #E9ECEF; }}

QPushButton {{
    background-color: #4A90D9; color: #FFFFFF; border: none; border-radius: 6px;
    padding: 7px 16px; font-weight: bold;
}}
QPushButton:hover {{ background-color: #357ABD; }}
QPushButton:pressed {{ background-color: #2A6099; }}
QPushButton:disabled {{ background-color: #ADB5BD; }}
QPushButton#secondaryBtn {{ background-color: #6C757D; }}
QPushButton#secondaryBtn:hover {{ background-color: #5A6268; }}
QPushButton#dangerBtn  {{ background-color: #DC3545; padding: 7px 16px; }}
QPushButton#dangerBtn:hover {{ background-color: #C82333; }}
QPushButton#deleteRowBtn {{ background-color: #DC3545; padding: 2px 8px; font-size: 12px; }}
QPushButton#deleteRowBtn:hover {{ background-color: #C82333; }}

QPushButton#avatarBtn {{
    background-color: #E9ECEF; color: #333333; border: 2px solid transparent; border-radius: 24px; font-size: 14px; font-weight: bold; padding: 0;
}}
QPushButton#avatarBtn:checked {{ background-color: #D6E4F0; border-color: #4A90D9; color: #2A6099; }}
QPushButton#avatarBtn:hover:!checked {{ background-color: #DEE2E6; }}
QPushButton#avatarAddBtn {{
    background-color: transparent; color: #6C757D; border: 2px dashed #CED4DA; border-radius: 24px; font-size: 18px; padding: 0;
}}
QPushButton#avatarAddBtn:hover {{ border-color: #4A90D9; color: #4A90D9; background-color: #F8F9FA; }}

QLineEdit {{
    border: 1px solid #DEE2E6; border-radius: 6px; padding: 7px 10px; background-color: #FFFFFF; color: #333333;
}}
QLineEdit:focus {{ border-color: #4A90D9; }}
QLineEdit:disabled {{ background-color: #F8F9FA; color: #ADB5BD; }}

QComboBox {{
    border: 1px solid #DEE2E6; border-radius: 6px; padding: 6px 10px; background-color: #FFFFFF; color: #333333;
}}
QComboBox:focus {{ border-color: #4A90D9; }}
QComboBox QAbstractItemView, QComboBox QListView {{
    background-color: #FFFFFF; color: #333333; selection-background-color: #4A90D9; selection-color: #FFFFFF;
}}

QTableWidget {{
    background-color: #FFFFFF; border: 1px solid #DEE2E6; border-radius: 6px;
    gridline-color: #E9ECEF; color: #333333;
}}
QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid #F0F2F5; }}
QTableWidget::item:selected {{ background-color: #D6E4F0; color: #333333; }}
QTableWidget QLineEdit {{ padding: 2px 4px; border: 1px solid #4A90D9; border-radius: 2px; }}

QHeaderView::section {{
    background-color: #F8F9FA; border: none; border-bottom: 2px solid #DEE2E6;
    padding: 6px 8px; font-weight: bold; color: #555555;
}}

QLabel {{ background: transparent; color: #333333; }}
QLabel#headerLabel {{ font-size: 20px; font-weight: bold; color: #222222; }}
QLabel#sectionLabel {{ font-size: 15px; font-weight: bold; color: #444444; }}
QLabel#totalLabel {{ font-size: 16px; font-weight: bold; color: #4A90D9; }}
QLabel#footerLabel {{ font-size: 11px; color: #888888; padding: 6px; }}

QFrame#separator {{ background-color: #DEE2E6; max-height: 1px; }}
QSplitter::handle {{ background-color: #DEE2E6; width: 4px; border-radius: 2px; }}
QScrollArea {{ border: none; background: transparent; }}
QWidget#avatarContainer {{ background-color: transparent; }}
"""

DARK_STYLE = f"""
QMainWindow, QDialog, QStackedWidget#rightStack, QWidget#projectView, QWidget#emptyView, QWidget#contentWidget {{ 
    background-color: #121212; color: #E0E0E0; 
}}
QWidget#leftPanel {{ background-color: #1A1A1A; }}
QWidget {{ font-family: {FONT_STACK}; font-size: 13px; }}

QListWidget {{
    background-color: #1E1E1E; border: 1px solid #333333; border-radius: 6px;
    padding: 4px; outline: none; color: #E0E0E0;
}}
QListWidget::item {{ padding: 8px 12px; border-radius: 4px; margin: 1px 0; }}
QListWidget::item:selected {{ background-color: #4A90D9; color: #FFFFFF; }}
QListWidget::item:hover:!selected {{ background-color: #2C2C2C; }}

QPushButton {{
    background-color: #4A90D9; color: #FFFFFF; border: none; border-radius: 6px;
    padding: 7px 16px; font-weight: bold;
}}
QPushButton:hover {{ background-color: #357ABD; }}
QPushButton:pressed {{ background-color: #2A6099; }}
QPushButton:disabled {{ background-color: #444444; color: #777777; }}
QPushButton#secondaryBtn {{ background-color: #333333; }}
QPushButton#secondaryBtn:hover {{ background-color: #444444; }}
QPushButton#dangerBtn  {{ background-color: #DC3545; padding: 7px 16px; }}
QPushButton#dangerBtn:hover {{ background-color: #C82333; }}
QPushButton#deleteRowBtn {{ background-color: #DC3545; padding: 2px 8px; font-size: 12px; }}
QPushButton#deleteRowBtn:hover {{ background-color: #C82333; }}

QPushButton#avatarBtn {{
    background-color: #2C2C2C; color: #E0E0E0; border: 2px solid transparent; border-radius: 24px; font-size: 14px; font-weight: bold; padding: 0;
}}
QPushButton#avatarBtn:checked {{ background-color: #2C4A6B; border-color: #6BB5FF; color: #FFFFFF; }}
QPushButton#avatarBtn:hover:!checked {{ background-color: #3A3A3A; }}
QPushButton#avatarAddBtn {{
    background-color: transparent; color: #888888; border: 2px dashed #444444; border-radius: 24px; font-size: 18px; padding: 0;
}}
QPushButton#avatarAddBtn:hover {{ border-color: #6BB5FF; color: #6BB5FF; background-color: #1E1E1E; }}

QLineEdit {{
    border: 1px solid #333333; border-radius: 6px; padding: 7px 10px; background-color: #1E1E1E; color: #E0E0E0;
}}
QLineEdit:focus {{ border-color: #4A90D9; }}
QLineEdit:disabled {{ background-color: #161616; color: #666666; border-color: #2A2A2A; }}

QComboBox {{
    border: 1px solid #444444; border-radius: 6px; padding: 6px 10px; background-color: #1E1E1E; color: #E0E0E0;
}}
QComboBox:focus {{ border-color: #4A90D9; }}
QComboBox QAbstractItemView, QComboBox QListView {{
    background-color: #1E1E1E; color: #E0E0E0; selection-background-color: #4A90D9; selection-color: #FFFFFF;
}}

QTableWidget {{
    background-color: #1E1E1E; border: 1px solid #333333; border-radius: 6px;
    gridline-color: #2A2A2A; color: #E0E0E0;
}}
QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid #2A2A2A; }}
QTableWidget::item:selected {{ background-color: #2C4A6B; color: #FFFFFF; }}
QTableWidget QLineEdit {{ padding: 2px 4px; border: 1px solid #4A90D9; border-radius: 2px; }}

QHeaderView::section {{
    background-color: #161616; border: none; border-bottom: 2px solid #333333;
    padding: 6px 8px; font-weight: bold; color: #AAAAAA;
}}

QLabel {{ background: transparent; color: #E0E0E0; }}
QLabel#headerLabel {{ font-size: 20px; font-weight: bold; color: #F0F0F0; }}
QLabel#sectionLabel {{ font-size: 15px; font-weight: bold; color: #CCCCCC; }}
QLabel#totalLabel {{ font-size: 16px; font-weight: bold; color: #6BB5FF; }}
QLabel#footerLabel {{ font-size: 11px; color: #666666; padding: 6px; }}

QFrame#separator {{ background-color: #333333; max-height: 1px; }}
QSplitter::handle {{ background-color: #444444; width: 4px; border-radius: 2px; }}
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
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_label.setFixedWidth(60)
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        current_theme = self.settings_mgr.get("theme", "light").capitalize()
        self.theme_combo.setCurrentText(current_theme)
        theme_layout.addWidget(self.theme_combo)
        
        layout.addLayout(theme_layout)
        layout.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_and_close)
        layout.addWidget(save_btn)

    def _save_and_close(self):
        selected_theme = self.theme_combo.currentText().lower()
        self.settings_mgr.set("theme", selected_theme)
        QApplication.instance().setStyleSheet(DARK_STYLE if selected_theme == "dark" else LIGHT_STYLE)
        self.accept()


class TeammateEditDialog(QDialog):
    def __init__(self, parent, teammate):
        super().__init__(parent)
        self.teammate = teammate
        self.avatar_b64 = teammate.avatar_data
        
        self.setWindowTitle("Edit Teammate")
        self.setFixedSize(380, 400)
        
        layout = QVBoxLayout(self)
        
        # Avatar Section
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

        # Fields
        layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit(self.teammate.name)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Description (Optional):"))
        self.desc_input = QLineEdit(self.teammate.description)
        layout.addWidget(self.desc_input)

        layout.addStretch()

        # Delete Section
        del_btn = QPushButton("Delete Teammate")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_teammate)
        layout.addWidget(del_btn)

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Save/Cancel
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
            self.done(2)  # Custom return code 2 indicates deletion


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
        QApplication.instance().setStyleSheet(DARK_STYLE if self.settings_mgr.get("theme", "light") == "dark" else LIGHT_STYLE)
        self._restore_splitters()
        
        self.showMaximized()
        self._refresh_projects()

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

        btn_new = QPushButton("+  New Project")
        btn_new.setObjectName("secondaryBtn")
        btn_new.clicked.connect(self._add_project)
        left_lay.addWidget(btn_new)
        left.setMinimumWidth(200)

        # ── Right Panel ──
        right = QWidget()
        right.setObjectName("rightPanel")
        right_outer = QVBoxLayout(right)
        right_outer.setContentsMargins(0, 0, 0, 0)

        self.right_stack = QStackedWidget()
        self.right_stack.setObjectName("rightStack")
        
        # Empty View
        self.empty_view = QWidget()
        self.empty_view.setObjectName("emptyView")
        empty_lay = QVBoxLayout(self.empty_view)
        empty_title = QLabel("Welcome to Balance Separator")
        empty_title.setObjectName("headerLabel")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lay.addWidget(empty_title)
        self.right_stack.addWidget(self.empty_view)

        # Project View
        self.project_view = QWidget()
        self.project_view.setObjectName("projectView")
        right_lay = QVBoxLayout(self.project_view)
        right_lay.setContentsMargins(24, 20, 24, 20)

        top_bar = QHBoxLayout()
        self.project_title = QLabel("Project Title")
        self.project_title.setObjectName("headerLabel")
        top_bar.addWidget(self.project_title)
        top_bar.addStretch()

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setObjectName("secondaryBtn")
        self.settings_btn.setFixedSize(100, 32)
        self.settings_btn.clicked.connect(self._open_settings)
        top_bar.addWidget(self.settings_btn)
        right_lay.addLayout(top_bar)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        right_lay.addWidget(sep)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.left_col_widget = QWidget()
        self.left_col_layout = QVBoxLayout(self.left_col_widget)
        self.left_col_layout.setContentsMargins(0, 10, 15, 0)
        self._build_teammates_section(self.left_col_layout)
        self._build_expenses_section(self.left_col_layout)
        
        self.right_col_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.top_right_widget = QWidget()
        top_right_layout = QVBoxLayout(self.top_right_widget)
        top_right_layout.setContentsMargins(15, 10, 0, 10)
        self._build_balance_section(top_right_layout)

        self.bottom_right_widget = QWidget()
        bottom_right_layout = QVBoxLayout(self.bottom_right_widget)
        bottom_right_layout.setContentsMargins(15, 10, 0, 0)
        self._build_settlement_section(bottom_right_layout)

        bottom_bar = QHBoxLayout()
        self.total_label = QLabel("Total Expenses:  RM0.00")
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
        
        # Append stack to the right outer panel
        right_outer.addWidget(self.right_stack, 1)

        # App Footer (Strictly at the bottom of Right Panel)
        footer = QLabel("2026 Developed by Chen Jin Shen, cjshen00@gmail.com")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName("footerLabel")
        right_outer.addWidget(footer)

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
        self.amt_input.setPlaceholderText("Amount (RM)")
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
        self.exp_table.verticalHeader().setDefaultSectionSize(34)  # <-- Fixes text cutoff when editing
        
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
    def _refresh_projects(self):
        self.project_list.blockSignals(True)
        self.project_list.clear()
        for p in self.project_mgr.projects:
            self.project_list.addItem(p.name)
        self.project_list.blockSignals(False)

        if self.project_mgr.projects:
            self.current_project_idx = max(0, min(self.current_project_idx, len(self.project_mgr.projects) - 1))
            self.project_list.setCurrentRow(self.current_project_idx)
        else:
            self.current_project_idx = -1

        self._refresh_right()

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

    def _project_context_menu(self, pos):
        item = self.project_list.itemAt(pos)
        if not item: return
        row = self.project_list.row(item)
        menu = QMenu(self)
        act_rename = menu.addAction("✏️  Rename")
        act_delete = menu.addAction("🗑️  Delete")
        chosen = menu.exec(self.project_list.mapToGlobal(pos))

        if chosen == act_rename:
            new_name, ok = QInputDialog.getText(self, "Rename Project", "New name:", text=item.text())
            if ok and new_name.strip():
                self.project_mgr.rename_project(row, new_name.strip())
                self._refresh_projects()
        elif chosen == act_delete:
            reply = QMessageBox.question(self, "Delete Project", f"Delete project '{item.text()}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
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
                self._refresh_right()
            elif res == 2:  # Custom Delete code
                self.project_mgr.remove_teammate(self.current_project_idx, tidx)
                if self.current_teammate_idx == tidx:
                    self.current_teammate_idx = -1
                elif self.current_teammate_idx > tidx:
                    self.current_teammate_idx -= 1
                self._refresh_right()

    def _update_expense_ui_state(self):
        has_teammate = self.current_teammate_idx >= 0
        self.desc_input.setEnabled(has_teammate)
        self.amt_input.setEnabled(has_teammate)
        self.add_exp_btn.setEnabled(has_teammate)
        
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

        item_amt = QTableWidgetItem(f"RM{amount:,.2f}")
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

    def _add_expense(self):
        desc = self.desc_input.text().strip() or "Undefined"
        amt_text = self.amt_input.text().strip().replace("RM", "").replace(",", "")

        try:
            amt = float(amt_text)
            if amt <= 0: raise ValueError
        except ValueError:
            if amt_text != "":
                QMessageBox.warning(self, "Invalid", "Please enter a valid positive amount.")
            return

        self.project_mgr.add_expense(self.current_project_idx, self.current_teammate_idx, desc, amt)
        self.desc_input.clear()
        self.amt_input.clear()
        self.amt_input.setFocus()
        self._refresh_expenses()
        self._refresh_summary()

    def _remove_expense(self, tidx: int, eidx: int):
        self.project_mgr.remove_expense(self.current_project_idx, tidx, eidx)
        self._refresh_expenses()
        self._refresh_summary()

    def _refresh_summary(self):
        project = self.project_mgr.get_project(self.current_project_idx)
        self.bal_table.setRowCount(0)
        
        self.settle_list.blockSignals(True)
        self.settle_list.clear()

        if not project or not project.teammates:
            self.total_label.setText("Total Expenses:  RM0.00")
            self.settle_list.blockSignals(False)
            return

        summary, settlements, total = BalanceCalculator.calculate(project)

        # ── Update Balances ──
        for name, data in summary.items():
            row = self.bal_table.rowCount()
            self.bal_table.insertRow(row)

            c0 = QTableWidgetItem(name)
            self.bal_table.setItem(row, 0, c0)

            c1 = QTableWidgetItem(f"RM{data['paid']:,.2f}")
            c1.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.bal_table.setItem(row, 1, c1)

            c2 = QTableWidgetItem(f"RM{data['share']:,.2f}")
            c2.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.bal_table.setItem(row, 2, c2)

            net = data["net"]
            sign = "+" if net > 0 else ""
            c3 = QTableWidgetItem(f"{sign}RM{abs(net):,.2f}")
            c3.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if net > 0: c3.setForeground(QColor("#27AE60"))
            elif net < 0:
                c3.setForeground(QColor("#E74C3C"))
                c3.setText(f"-RM{abs(net):,.2f}")
            self.bal_table.setItem(row, 3, c3)

        # ── Update Settlements ──
        if not settlements:
            item = QListWidgetItem("✅ All settled! No transfers needed.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.settle_list.addItem(item)
        else:
            for s in settlements:
                key = f"{s['from']}_{s['to']}_{s['amount']}"
                is_settled = key in project.settled_debts
                
                text = f"{s['from']}  ➜  {s['to']}:  RM{s['amount']:,.2f}"
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
        self.total_label.setText(f"Total Expenses:  RM{total:,.2f}")

    def _on_settlement_checked(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        checked = item.checkState() == Qt.CheckState.Checked
        
        self.project_mgr.toggle_settlement(self.current_project_idx, key, checked)
        
        font = item.font()
        font.setStrikeOut(checked)
        item.setFont(font)
        
        if checked:
            item.setForeground(QColor("#888888"))
        else:
            is_dark = self.settings_mgr.get("theme", "light") == "dark"
            item.setForeground(QColor("#E0E0E0") if is_dark else QColor("#333333"))

    def _refresh_right(self):
        project = self.project_mgr.get_project(self.current_project_idx)
        if not project:
            self.right_stack.setCurrentIndex(0)
            return

        self.right_stack.setCurrentIndex(1)
        self.project_title.setText(project.name)
        self._refresh_teammates()
        self._refresh_expenses()
        self._refresh_summary()

    def _show_export_menu(self):
        project = self.project_mgr.get_project(self.current_project_idx)
        if not project: return
        menu = QMenu(self)
        act_pdf = menu.addAction("📄  Export to PDF")
        act_excel = menu.addAction("📊  Export to Excel")
        btn = self.sender()
        chosen = menu.exec(btn.mapToGlobal(btn.rect().topRight()))
        if chosen == act_pdf: self._export_pdf(project)
        elif chosen == act_excel: self._export_excel(project)

    def _export_pdf(self, project):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"{project.name}_Report.pdf", "PDF Files (*.pdf)")
        if not path: return

        summary, settlements, total = BalanceCalculator.calculate(project)

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
            <p><strong>Total Project Expenses:</strong> RM{total:,.2f}</p>
            
            <h2>1. Balance Summary</h2>
            <table>
                <tr><th>Name</th><th class="right">Total Paid</th><th class="right">Fair Share</th><th class="right">Balance</th></tr>
        """
        for name, data in summary.items():
            net = data["net"]
            color = "green" if net > 0 else "red" if net < 0 else ""
            sign = "+" if net > 0 else "-" if net < 0 else ""
            html += f"<tr><td>{name}</td><td class='right'>RM{data['paid']:,.2f}</td><td class='right'>RM{data['share']:,.2f}</td><td class='right {color}'>{sign}RM{abs(net):,.2f}</td></tr>"
        html += "</table>"

        html += "<h2>2. Settlements</h2><ul>"
        if not settlements: html += "<li>✅ All settled! No transfers needed.</li>"
        else:
            for s in settlements:
                key = f"{s['from']}_{s['to']}_{s['amount']}"
                css = "class='strike'" if key in project.settled_debts else ""
                html += f"<li {css} style='margin-bottom:10px;'><strong>{s['from']}</strong> pays <strong>{s['to']}</strong>: RM{s['amount']:,.2f}</li>"
        html += "</ul>"

        html += """
            <div style="page-break-before: always;"></div>
            <h2>3. Detailed Expenses List</h2>
            <table><tr><th>Paid By</th><th>Description</th><th class="right">Amount</th></tr>
        """
        for t in project.teammates:
            for e in t.expenses:
                html += f"<tr><td>{t.name}</td><td>{e.description}</td><td class='right'>RM{e.amount:,.2f}</td></tr>"
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

        df_bal = pd.DataFrame([{"Name": k, "Total Paid (RM)": v["paid"], "Fair Share (RM)": v["share"], "Balance (RM)": v["net"]} for k, v in summary.items()])
        
        settle_data = []
        for s in settlements:
            key = f"{s['from']}_{s['to']}_{s['amount']}"
            settle_data.append({"From": s["from"], "To": s["to"], "Amount (RM)": s["amount"], "Paid": "Yes" if key in project.settled_debts else "No"})
        df_settle = pd.DataFrame(settle_data)

        df_exp = pd.DataFrame([{"Paid By": t.name, "Description": e.description, "Amount (RM)": e.amount} for t in project.teammates for e in t.expenses])

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            if not df_bal.empty: df_bal.to_excel(writer, sheet_name="Summary & Settlements", index=False, startrow=0)
            if not df_settle.empty: df_settle.to_excel(writer, sheet_name="Summary & Settlements", index=False, startrow=len(df_bal) + 3)
            if not df_exp.empty: df_exp.to_excel(writer, sheet_name="Detailed Expenses", index=False)
        QMessageBox.information(self, "Export Successful", f"Excel saved to:\n{path}")

    def _open_settings(self):
        SettingsDialog(self, self.settings_mgr).exec()

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
