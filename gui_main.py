import uuid
import json
import base64
import os
import threading
import math
import urllib.request
from copy import deepcopy
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QInputDialog, QMessageBox, QAbstractItemView, QMenu, QScrollArea,
    QFrame, QStackedWidget, QButtonGroup, QStyledItemDelegate, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt, QSize, QEvent, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QColor, QTextDocument, QPdfWriter, QPixmap, QIcon, QKeyEvent, QKeySequence, QShortcut

from config import CURRENCIES, FONT_STACK, APP_VERSION, ATTACHMENTS_DIR, sanitize_filename, safe_path_resolve
from logic_models import Expense, Teammate
from logic_project import SettingsManager, ProjectManager, BalanceCalculator
from logic_network import NetworkSignals, NetworkManager
from gui_dialogs import (
    ShareProjectDialog, ConnectPrivateDialog, ExpenseDetailsDialog, 
    SettingsDialog, ProjectEditDialog, TeammateEditDialog, create_circular_pixmap, ManualSettlementDialog, SettlementDetailsDialog
)

# --- Action Dictionary Helpers ---
def _expense_to_dict(exp: Expense) -> dict:
    return {
        "id": exp.id, "description": exp.description, "amount": exp.amount,
        "date": exp.date, "time": exp.time, "detailed_description": exp.detailed_description,
        "attachments": deepcopy(exp.attachments)
    }

def _dict_to_expense(d: dict) -> Expense:
    return Expense(id=d.get("id"), description=d.get("description", ""), amount=d.get("amount", 0.0),
                   date=d.get("date", ""), time=d.get("time", ""), detailed_description=d.get("detailed_description", ""),
                   attachments=d.get("attachments", []))

class UpdateCheckerSignals(QObject):
    update_available = pyqtSignal(str)

def get_actual_theme(theme_setting):
    if theme_setting.lower() == "system":
        if QApplication.instance():
            scheme = QApplication.styleHints().colorScheme()
            return "dark" if scheme == Qt.ColorScheme.Dark else "light"
        return "light"
    return theme_setting.lower()

def get_contrast_color(hex_color):
    color = QColor(hex_color)
    r, g, b = color.redF(), color.greenF(), color.blueF()
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminance > 0.5 else "#FFFFFF"

def generate_stylesheet(theme_setting, accent_hex):
    actual_theme = get_actual_theme(theme_setting)
    accent = QColor(accent_hex)
    contrast_text = get_contrast_color(accent_hex)
    
    tick_svg_white = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIzIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg=="
    tick_svg_black = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIzIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIj48L3BvbHlsaW5lPjwvc3ZnPg=="
    tick_base64 = tick_svg_black if contrast_text == "#000000" else tick_svg_white

    if actual_theme == "dark":
        bg = "#121212"; panel = "#1A1A1A"; text = "#E0E0E0"; border = "#333333"
        hover_bg = "#2C2C2C"; input_bg = "#1E1E1E"; header_bg = "#161616"
        second_btn = "#333333"; second_btn_hover = "#444444"
        accent_hover = accent.lighter(115).name()
        accent_pressed = accent.lighter(130).name()
        selection_bg = QColor(accent.red(), accent.green(), accent.blue(), 60).name()
        subtitle_color = "#AAAAAA"; total_color = "#FFFFFF" 
        checkbox_border = "#E0E0E0"
    else:
        bg = "#FFFFFF"; panel = "#F8F9FA"; text = "#333333"; border = "#DEE2E6"
        hover_bg = "#E9ECEF"; input_bg = "#FFFFFF"; header_bg = "#F8F9FA"
        second_btn = "#6C757D"; second_btn_hover = "#5A6268"
        accent_hover = accent.darker(110).name()
        accent_pressed = accent.darker(120).name()
        selection_bg = QColor(accent.red(), accent.green(), accent.blue(), 40).name()
        subtitle_color = "#666666"; total_color = "#000000" 
        checkbox_border = "#333333"

    return f"""
    QMainWindow, QDialog, QStackedWidget#rightStack, QWidget#projectView, QWidget#emptyView, QWidget#contentWidget {{ 
        background-color: {bg}; color: {text}; 
    }}
    QWidget#leftPanel {{ background-color: {panel}; }}
    QWidget {{ font-family: {FONT_STACK}; font-size: 13px; color: {text}; }}
    
    QListWidget {{ background-color: {input_bg}; border: 1px solid {border}; border-radius: 6px; padding: 4px; outline: none; color: {text}; }}
    QListWidget::item {{ border-radius: 4px; margin: 1px 0; }}
    QListWidget::item:selected {{ background-color: {selection_bg}; border: 1px solid {accent.name()}; color: {contrast_text}; }}
    QListWidget::item:hover:!selected {{ background-color: {hover_bg}; }}
    QListWidget#settleList::item {{ padding: 8px 12px; }}
    
    QPushButton {{ background-color: {accent.name()}; color: {contrast_text}; border: none; border-radius: 6px; padding: 7px 16px; font-weight: bold; }}
    QPushButton:hover {{ background-color: {accent_hover}; }}
    QPushButton:pressed {{ background-color: {accent_pressed}; }}
    QPushButton:disabled {{ background-color: {border}; color: gray; }}
    QPushButton#secondaryBtn {{ background-color: {second_btn}; color: #FFFFFF; }}
    QPushButton#secondaryBtn:hover {{ background-color: {second_btn_hover}; }}
    QPushButton#dangerBtn  {{ background-color: #DC3545; color: #FFFFFF; padding: 7px 16px; }}
    QPushButton#dangerBtn:hover {{ background-color: #C82333; }}
    QPushButton#activeShareBtn {{ background-color: #DC3545; color: #FFFFFF; }}
    QPushButton#activeShareBtn:hover {{ background-color: #C82333; }}
    QPushButton#deleteRowBtn {{ background-color: #DC3545; color: #FFFFFF; padding: 2px 8px; font-size: 12px; }}
    QPushButton#deleteRowBtn:hover {{ background-color: #C82333; }}
    QPushButton#smallSecondaryBtn {{ background-color: {second_btn}; color: #FFFFFF; padding: 2px; font-size: 14px; font-weight: bold; border-radius: 6px; }}
    QPushButton#smallSecondaryBtn:hover {{ background-color: {second_btn_hover}; }}
    QPushButton#avatarBtn {{ background-color: {hover_bg}; color: {text}; border: 2px solid transparent; border-radius: 24px; font-size: 14px; font-weight: bold; padding: 0; }}
    QPushButton#avatarBtn:checked {{ background-color: {selection_bg}; border-color: {accent.name()}; color: {contrast_text}; }}
    QPushButton#avatarBtn:hover:!checked {{ background-color: {border}; }}
    QPushButton#avatarAddBtn {{ background-color: transparent; color: {second_btn}; border: 2px dashed {border}; border-radius: 24px; font-size: 18px; padding: 0; }}
    QPushButton#avatarAddBtn:hover {{ border-color: {accent.name()}; color: {accent.name()}; background-color: {input_bg}; }}
    
    QCheckBox, QRadioButton {{ color: {text}; background: transparent; padding: 2px; }}
    QCheckBox::indicator, QListView::indicator {{ width: 16px; height: 16px; background-color: {input_bg}; border: 2px solid {checkbox_border}; border-radius: 4px; }}
    QCheckBox::indicator:checked, QListView::indicator:checked {{ background-color: {accent.name()}; border: 2px solid {accent.name()}; image: url(data:image/svg+xml;base64,{tick_base64}); }}
    
    QLineEdit, QDateEdit, QTimeEdit, QTextEdit {{ border: 1px solid {border}; border-radius: 6px; padding: 7px 10px; background-color: {input_bg}; color: {text}; }}
    QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QTextEdit:focus {{ border-color: {accent.name()}; }}
    QLineEdit:disabled, QDateEdit:disabled, QTimeEdit:disabled {{ background-color: {header_bg}; color: {subtitle_color}; border-color: {border}; }}
    
    QComboBox {{ border: 1px solid {border}; border-radius: 6px; padding: 6px 10px; background-color: {input_bg}; color: {text}; }}
    QComboBox:focus {{ border-color: {accent.name()}; }}
    QComboBox QAbstractItemView {{ background-color: {input_bg}; color: {text}; selection-background-color: {accent.name()}; selection-color: {contrast_text}; border: 1px solid {border}; outline: none; }}
    
    QTableWidget {{ background-color: {input_bg}; border: 1px solid {border}; border-radius: 6px; gridline-color: {border}; color: {text}; }}
    QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid {border}; }}
    QTableWidget::item:selected {{ background-color: {selection_bg}; color: {contrast_text}; }}
    QTableWidget QLineEdit {{ padding: 0px 4px; margin: 0px; border: 1px solid {accent.name()}; border-radius: 2px; height: 100%; }}
    QHeaderView::section {{ background-color: {header_bg}; border: none; border-bottom: 2px solid {border}; padding: 6px 8px; font-weight: bold; color: {subtitle_color}; }}
    
    QDialog QTabWidget::pane {{ border: 1px solid {border}; background-color: {bg}; border-radius: 6px; top: -1px; }}
    QDialog QTabBar::tab {{ background: {input_bg}; color: {text}; border: 1px solid {border}; padding: 6px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
    QDialog QTabBar::tab:selected {{ background: {accent.name()}; color: {contrast_text}; border-color: {accent.name()}; }}
    QDialog QWidget#gen_tab, QDialog QWidget#att_tab {{ background-color: {bg}; color: {text}; }}
    
    QLabel {{ background: transparent; color: {text}; }}
    QLabel#headerLabel {{ font-size: 20px; font-weight: bold; color: {text}; }}
    QLabel#sectionLabel {{ font-size: 15px; font-weight: bold; color: {text}; }}
    QLabel#totalLabel {{ font-size: 16px; font-weight: bold; color: {total_color}; }}
    QLabel#footerLabel {{ font-size: 11px; color: {subtitle_color}; padding: 6px; }}
    QLabel#subTitleLabel {{ font-size: 11px; color: {subtitle_color}; }}
    QFrame#separator {{ background-color: {border}; max-height: 1px; }}
    QSplitter::handle {{ background-color: {border}; width: 4px; border-radius: 2px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QWidget#avatarContainer {{ background-color: transparent; }}

    QMenu {{ background-color: {input_bg}; color: {text}; border: 1px solid {border}; }}
    QMenu::item {{ padding: 6px 24px 6px 24px; background-color: transparent; }}
    QMenu::item:selected {{ background-color: {accent.name()}; color: {contrast_text}; }}
    """

class MarginDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setContentsMargins(0,0,0,0)
        return editor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings_mgr = SettingsManager()
        self.project_mgr = ProjectManager()
        self.current_project_idx: int = -1
        self.current_teammate_idx: int = -1
        
        self.active_view = "local" 
        self.remote_project = None
        self.remote_settlements = []
        
        self.password_cache = {}  
        self.undo_stack = []

        self.avatar_btn_group = QButtonGroup(self)
        self.avatar_btn_group.setExclusive(True)
        self.avatar_btn_group.idClicked.connect(self._on_teammate_changed)
        
        self.net_signals = NetworkSignals()
        self.net_signals.discovered.connect(self._refresh_discovered_projects)
        
        self.net_signals.host_received_action.connect(self._on_host_received_action)
        self.net_signals.host_clients_updated.connect(self._on_host_clients_updated)
        
        self.net_signals.client_connected.connect(self._on_client_connected)
        self.net_signals.client_received_update.connect(self._on_client_received_update)
        self.net_signals.client_disconnected.connect(self._on_client_disconnected)
        self.net_mgr = NetworkManager(self.net_signals, self.settings_mgr)

        self.update_signals = UpdateCheckerSignals()
        self.update_signals.update_available.connect(self._on_update_available)

        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self._undo_last_delete)

        self._build_ui()
        self._apply_theme()
        self._restore_splitters()
        
        self.showMaximized()
        self._refresh_projects()
        self._apply_network_settings()
        self._start_background_update_check()

    def _start_background_update_check(self):
        def check():
            try:
                req = urllib.request.Request("https://github.com/arinltte/Balance-Separator/releases/latest", headers={'User-Agent': 'Mozilla/5.0'})
                tag = urllib.request.urlopen(req, timeout=5).geturl().split('/')[-1]
                if tag > f"v{APP_VERSION}":
                    self.update_signals.update_available.emit(tag)
            except Exception: pass
        threading.Thread(target=check, daemon=True).start()

    def _on_update_available(self, version_tag):
        self.settings_btn.setText("Settings (Update)")
        self.settings_btn.setStyleSheet("color: #E74C3C; font-weight: bold;")
        self.settings_btn.setToolTip(f"A new version ({version_tag}) is available!")

    def _apply_theme(self):
        theme = self.settings_mgr.get("theme", "system")
        accent = self.settings_mgr.get("accent_color", "#4A90D9")
        QApplication.instance().setStyleSheet(generate_stylesheet(theme, accent))

    def _apply_network_settings(self):
        if self.settings_mgr.get("enable_sharing", True):
            self.net_mgr.start()
            self.shared_widget.show()
            if self.active_view == "local" and self.current_project_idx >= 0:
                self.share_top_btn.show()
        else:
            self.net_mgr.stop()
            self.shared_widget.hide()
            self.share_top_btn.hide()

    def _format_money(self, amount: float) -> str:
        curr = self.settings_mgr.get("currency", "RM")
        prefix, suffix, decs, spc = CURRENCIES.get(curr, ("RM", "", 2, False))
        amt_str = f"{amount:,.{decs}f}"
        return f"{prefix}{' ' if spc else ''}{amt_str}" if prefix else f"{amt_str}{' ' if spc else ''}{suffix}"

    def _build_ui(self):
        self.setWindowTitle("Balance Separator")
        self.setMinimumSize(1000, 650)
        central = QWidget(); self.setCentralWidget(central)
        outer_layout = QHBoxLayout(central)
        outer_layout.setContentsMargins(0,0,0,0); outer_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget(); left_panel.setObjectName("leftPanel")
        left_outer_lay = QVBoxLayout(left_panel); left_outer_lay.setContentsMargins(16,20,16,16)
        self.left_inner_splitter = QSplitter(Qt.Orientation.Vertical)
        
        local_widget = QWidget(); local_lay = QVBoxLayout(local_widget); local_lay.setContentsMargins(0,0,0,0)
        lbl_projects = QLabel("📁  Local Projects"); lbl_projects.setObjectName("sectionLabel"); local_lay.addWidget(lbl_projects)

        self.project_list = QListWidget()
        self.project_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.project_list.currentRowChanged.connect(self._on_project_changed)
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._project_context_menu)
        local_lay.addWidget(self.project_list, 2)

        btn_layout = QHBoxLayout()
        btn_new = QPushButton("+ New"); btn_new.setObjectName("secondaryBtn"); btn_new.clicked.connect(self._add_project)
        btn_import = QPushButton("⬇ Import"); btn_import.setObjectName("secondaryBtn"); btn_import.clicked.connect(self._import_project)
        btn_layout.addWidget(btn_new); btn_layout.addWidget(btn_import)
        local_lay.addLayout(btn_layout); local_lay.addSpacing(14)
        
        self.shared_widget = QWidget(); shared_lay = QVBoxLayout(self.shared_widget); shared_lay.setContentsMargins(0,10,0,0)
        shared_lbl = QLabel("🌐  Shared Projects"); shared_lbl.setObjectName("sectionLabel"); shared_lay.addWidget(shared_lbl)
        
        self.shared_list = QListWidget()
        self.shared_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.shared_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.shared_list.itemClicked.connect(self._on_shared_project_clicked)
        shared_lay.addWidget(self.shared_list, 1)
        
        self.conn_priv_btn = QPushButton("Connect to Private Project"); self.conn_priv_btn.setObjectName("secondaryBtn"); self.conn_priv_btn.clicked.connect(self._connect_private)
        shared_lay.addWidget(self.conn_priv_btn)
        
        self.left_inner_splitter.addWidget(local_widget); self.left_inner_splitter.addWidget(self.shared_widget)
        left_outer_lay.addWidget(self.left_inner_splitter)
        left_panel.setMinimumWidth(260)

        right = QWidget(); right.setObjectName("rightPanel")
        right_outer = QVBoxLayout(right); right_outer.setContentsMargins(0,0,0,0)

        top_bar_widget = QWidget(); top_bar_widget.setContentsMargins(24,20,24,10)
        top_bar_lay = QHBoxLayout(top_bar_widget); top_bar_lay.setContentsMargins(0,0,0,0)
        
        self.global_title = QLabel("Welcome"); self.global_title.setObjectName("headerLabel"); top_bar_lay.addWidget(self.global_title)
        self.global_dates = QLabel(""); self.global_dates.setObjectName("footerLabel"); top_bar_lay.addWidget(self.global_dates)
        
        self.connected_users_widget = QWidget()
        self.connected_users_layout = QHBoxLayout(self.connected_users_widget)
        self.connected_users_layout.setContentsMargins(15, 0, 0, 0)
        self.connected_users_layout.setSpacing(8)
        top_bar_lay.addWidget(self.connected_users_widget)

        top_bar_lay.addStretch()

        self.share_top_btn = QPushButton("Share Project")
        self.share_top_btn.setFixedSize(130, 32)
        self.share_top_btn.clicked.connect(self._toggle_share_current)
        self.share_top_btn.hide()
        top_bar_lay.addWidget(self.share_top_btn)

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setObjectName("secondaryBtn"); self.settings_btn.setFixedSize(140, 32); self.settings_btn.clicked.connect(self._open_settings)
        top_bar_lay.addWidget(self.settings_btn)
        right_outer.addWidget(top_bar_widget)

        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine); sep.setFixedHeight(1)
        right_outer.addWidget(sep)

        self.right_stack = QStackedWidget(); self.right_stack.setObjectName("rightStack")
        
        self.empty_view = QWidget(); self.empty_view.setObjectName("emptyView")
        empty_lay = QVBoxLayout(self.empty_view)
        empty_lbl = QLabel("Select or create a project to begin."); empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); empty_lbl.setObjectName("footerLabel"); empty_lay.addWidget(empty_lbl)
        self.right_stack.addWidget(self.empty_view)

        self.project_view = QWidget(); self.project_view.setObjectName("projectView")
        right_lay = QVBoxLayout(self.project_view); right_lay.setContentsMargins(24,10,24,20)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_col_widget = QWidget(); self.left_col_layout = QVBoxLayout(self.left_col_widget); self.left_col_layout.setContentsMargins(0,0,15,0)
        self._build_teammates_section(self.left_col_layout)
        self._build_expenses_section(self.left_col_layout)
        
        self.right_col_splitter = QSplitter(Qt.Orientation.Vertical)
        self.top_right_widget = QWidget(); top_right_layout = QVBoxLayout(self.top_right_widget); top_right_layout.setContentsMargins(15,0,0,10)
        self._build_balance_section(top_right_layout)

        self.bottom_right_widget = QWidget(); bottom_right_layout = QVBoxLayout(self.bottom_right_widget); bottom_right_layout.setContentsMargins(15,10,0,0)
        self._build_settlement_section(bottom_right_layout)

        bottom_bar = QHBoxLayout()
        self.total_label = QLabel("Total Expenses:")
        self.total_label.setObjectName("totalLabel")
        bottom_bar.addWidget(self.total_label); bottom_bar.addStretch()
        
        btn_export = QPushButton("📄  Export")
        btn_export.setObjectName("secondaryBtn"); btn_export.clicked.connect(self._show_export_menu)
        bottom_bar.addWidget(btn_export)

        bottom_right_layout.addLayout(bottom_bar)
        self.right_col_splitter.addWidget(self.top_right_widget); self.right_col_splitter.addWidget(self.bottom_right_widget)
        self.content_splitter.addWidget(self.left_col_widget); self.content_splitter.addWidget(self.right_col_splitter)
        right_lay.addWidget(self.content_splitter)
        self.right_stack.addWidget(self.project_view)
        right_outer.addWidget(self.right_stack, 1)

        self.main_splitter.addWidget(left_panel); self.main_splitter.addWidget(right)
        outer_layout.addWidget(self.main_splitter)

    def _ensure_username_set(self, prompt_text: str) -> bool:
        username = self.settings_mgr.get("username", "").strip()
        if not username:
            name_input, ok = QInputDialog.getText(self, "Setup Name", prompt_text)
            if ok and name_input.strip():
                self.settings_mgr.set("username", name_input.strip())
                return True
            return False
        return True

    def _get_current_project(self):
        if self.active_view == "remote": 
            return self.remote_project
        return self.project_mgr.get_project(self.current_project_idx)

    def _switch_to_local_view(self):
        if self.active_view == "remote":
            self.net_mgr.disconnect_client()
            self.remote_project = None
            self.remote_settlements = []
        self.active_view = "local"

    def _update_connected_users_ui(self, client_names):
        while self.connected_users_layout.count():
            child = self.connected_users_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        if not client_names:
            return

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFrameShadow(QFrame.Shadow.Plain)
        actual_theme = get_actual_theme(self.settings_mgr.get("theme", "system"))
        line_color = "#333333" if actual_theme == "dark" else "#DEE2E6"
        vline.setStyleSheet(f"color: {line_color}; margin: 0 8px;")
        self.connected_users_layout.addWidget(vline)
            
        accent = self.settings_mgr.get("accent_color", "#4A90D9")
        contrast = get_contrast_color(accent)
        
        for name in client_names:
            lbl = QLabel(self._get_initials(name))
            lbl.setFixedSize(48, 48)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setToolTip(name)
            lbl.setStyleSheet(f"background-color: {accent}; color: {contrast}; border-radius: 24px; font-weight: bold; font-size: 16px;")
            self.connected_users_layout.addWidget(lbl)

    def _on_host_clients_updated(self, share_key: str, client_names: list):
        if self.active_view == "local" and self.current_project_idx >= 0:
            project = self.project_mgr.get_project(self.current_project_idx)
            if project and project.name == share_key:
                self._update_connected_users_ui(client_names)

    def _dispatch_action(self, action_type: str, action_data: dict, local_callback):
        project = self._get_current_project()
        if not project: return
        
        local_callback(project)
        
        if self.active_view == "remote":
            self.net_mgr.send_client_action(project.name, action_type, action_data)
        else:
            self.project_mgr._touch(self.current_project_idx)
            if project.name in self.net_mgr.active_shares:
                self.net_mgr.host_broadcast_update(project)

    def _on_host_received_action(self, share_key: str, action_type: str, action_data: dict):
        idx = next((i for i, p in enumerate(self.project_mgr.projects) if p.name == share_key), -1)
        if idx == -1: return
        project = self.project_mgr.projects[idx]

        try:
            if action_type == "add_expense":
                tidx = action_data["teammate_idx"]
                exp = _dict_to_expense(action_data["expense"])
                if 0 <= tidx < len(project.teammates):
                    project.teammates[tidx].expenses.append(exp)

            elif action_type == "insert_expense":
                tidx = action_data["teammate_idx"]
                eidx = action_data["expense_idx"]
                exp = _dict_to_expense(action_data["expense"])
                if 0 <= tidx < len(project.teammates):
                    safe_idx = min(eidx, len(project.teammates[tidx].expenses))
                    project.teammates[tidx].expenses.insert(safe_idx, exp)

            elif action_type == "update_expense":
                tidx = action_data["teammate_idx"]
                eidx = action_data["expense_idx"]
                exp = _dict_to_expense(action_data["expense"])
                if 0 <= tidx < len(project.teammates) and 0 <= eidx < len(project.teammates[tidx].expenses):
                    project.teammates[tidx].expenses[eidx] = exp

            elif action_type == "delete_expense":
                tidx = action_data["teammate_idx"]
                eidx = action_data["expense_idx"]
                if 0 <= tidx < len(project.teammates) and 0 <= eidx < len(project.teammates[tidx].expenses):
                    del project.teammates[tidx].expenses[eidx]

            elif action_type == "add_teammate":
                tdata = action_data["teammate"]
                project.teammates.append(Teammate(name=tdata["name"], description=tdata["description"], avatar=tdata["avatar"]))

            elif action_type == "update_teammate":
                tidx = action_data["teammate_idx"]
                tdata = action_data["teammate"]
                if 0 <= tidx < len(project.teammates):
                    project.teammates[tidx].name = tdata["name"]
                    project.teammates[tidx].description = tdata["description"]
                    project.teammates[tidx].avatar = tdata["avatar"]

            elif action_type == "delete_teammate":
                tidx = action_data["teammate_idx"]
                if 0 <= tidx < len(project.teammates):
                    del project.teammates[tidx]

            elif action_type == "update_project":
                project.name = action_data["name"]
                project.description = action_data["description"]
                project.start_date = action_data["start_date"]
                project.end_date = action_data["end_date"]

            elif action_type == "update_settlements":
                self.settings_mgr.set_settlement_entries(share_key, action_data["settlement_entries"])

            self.project_mgr._touch(idx)
            self.net_mgr.host_broadcast_update(project)

            if self.current_project_idx == idx and self.active_view == "local":
                self._update_project_list_item(idx)
                self._refresh_right()

        except Exception as e:
            pass 

    def _create_project_list_widget(self, project, is_selected=False) -> QWidget:
        widget = QWidget(); widget.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(widget); lay.setContentsMargins(8, 4, 8, 4); lay.setSpacing(2)
        
        accent = self.settings_mgr.get("accent_color", "#4A90D9")
        contrast = get_contrast_color(accent)
        actual_theme = get_actual_theme(self.settings_mgr.get("theme", "system"))
        
        if is_selected:
            title_color = contrast
            date_color = contrast
        else:
            title_color = "#E0E0E0" if actual_theme == "dark" else "#333333"
            date_color = "#AAAAAA" if actual_theme == "dark" else "#666666"
        
        lbl_title = QLabel(project.name)
        lbl_title.setStyleSheet(f"font-weight: bold; color: {title_color};")
        
        disp_pref = self.settings_mgr.get("project_date_display", "modified")
        date_str = project.updated_at if disp_pref == "modified" else project.created_at
        try: date_label = datetime.fromisoformat(date_str).strftime("%b %d, %Y %H:%M")
        except: date_label = "Unknown date"
        prefix = "Modified: " if disp_pref == "modified" else "Created: "
        
        if project.name in self.net_mgr.active_shares:
            sd = self.net_mgr.active_shares[project.name]
            date_label += " — Sharing" if sd["custom_name"] == project.name else f" — Sharing as {sd['custom_name']}"
                
        lbl_sub = QLabel(f"{prefix}{date_label}")
        lbl_sub.setObjectName("subTitleLabel")
        lbl_sub.setStyleSheet(f"color: {date_color};")
        
        lay.addWidget(lbl_title); lay.addWidget(lbl_sub)
        return widget

    def _create_shared_project_list_widget(self, p_data, is_selected=False) -> QWidget:
        widget = QWidget(); widget.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(widget); lay.setContentsMargins(8, 4, 8, 4); lay.setSpacing(2)
        
        accent = self.settings_mgr.get("accent_color", "#4A90D9")
        contrast = get_contrast_color(accent)
        actual_theme = get_actual_theme(self.settings_mgr.get("theme", "system"))
        
        if is_selected:
            title_color = contrast
            sub_color = contrast
        else:
            title_color = "#E0E0E0" if actual_theme == "dark" else "#333333"
            sub_color = "#AAAAAA" if actual_theme == "dark" else "#666666"
        
        lock = "🔒 " if p_data.get("auth") else ""
        lbl_title = QLabel(f"{lock}{p_data['name']}")
        lbl_title.setStyleSheet(f"font-weight: bold; color: {title_color};")
        
        lbl_sub = QLabel(f"Shared by {p_data.get('host_name', 'Unknown')}")
        lbl_sub.setObjectName("subTitleLabel")
        lbl_sub.setStyleSheet(f"color: {sub_color};")
        
        lay.addWidget(lbl_title); lay.addWidget(lbl_sub)
        return widget

    def _refresh_discovered_projects(self, projects):
        self.shared_list.blockSignals(True)
        self.shared_list.clear()
        for p in projects:
            if p.get("visibility") == "public":
                item = QListWidgetItem()
                item.setSizeHint(QSize(200, 48))
                item.setToolTip(f"Host IP: {p['ip']}")
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.shared_list.addItem(item)
                is_selected = (self.active_view == "remote" and self.net_mgr.connected_share_name == p["name"])
                self.shared_list.setItemWidget(item, self._create_shared_project_list_widget(p, is_selected))
                if is_selected:
                    item.setSelected(True)
        self.shared_list.blockSignals(False)

    def _on_shared_project_clicked(self, item):
        if not self._ensure_username_set("Enter your name to identify yourself to the host:"):
            self.shared_list.clearSelection()
            return
            
        data = item.data(Qt.ItemDataRole.UserRole)
        self.project_list.blockSignals(True)
        self.project_list.setCurrentRow(-1)
        self.project_list.blockSignals(False)
        self.active_view = "remote"

        self._refresh_local_project_widgets()
        self._refresh_shared_project_widgets()

        if self.net_mgr.connected_share_name == data["name"]:
            self._refresh_right()
            return
            
        pwd = ""
        if data["auth"]:
            if data["name"] in self.password_cache:
                pwd = self.password_cache[data["name"]]
            else:
                pwd, ok = QInputDialog.getText(self, "Password Required", f"Enter password for '{data['name']}':", QLineEdit.EchoMode.Password)
                if not ok: 
                    self._switch_to_local_view()
                    self._refresh_projects()
                    return
                    
        fallback_host = data.get("host_name", "Unknown Host")
        self._connect_to_host(data["ip"], data["port"], data["name"], pwd, fallback_host)

    def _connect_private(self):
        if not self._ensure_username_set("Enter your name to identify yourself to the host:"):
            return
            
        dlg = ConnectPrivateDialog(self)
        if dlg.exec():
            name = dlg.name_input.text().strip()
            pwd = dlg.pass_input.text()
            found = False
            for p in self.net_mgr.discovered_projects.values():
                if p["name"].lower() == name.lower():
                    self.active_view = "remote"
                    fallback_host = p.get("host_name", "Unknown Host")
                    self._connect_to_host(p["ip"], p["port"], p["name"], pwd, fallback_host)
                    found = True; break
            if not found:
                QMessageBox.warning(self, "Not Found", "Project not found on local network.\nEnsure the host is actively sharing.")

    def _connect_to_host(self, ip, port, name, pwd, fallback_host_name="Unknown Host"):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.net_mgr.connect_client(ip, port, name, pwd, fallback_host_name):
                self.password_cache[name] = pwd
        except Exception as e:
            if name in self.password_cache:
                del self.password_cache[name]
            self._switch_to_local_view()
            QMessageBox.critical(self, "Connection Failed", f"Could not connect:\n{str(e)}")
        finally:
            QApplication.restoreOverrideCursor()

    def _on_client_connected(self, project, settlements, settlement_entries):
        self.remote_project = project
        self.remote_settlements = settlements
        self.undo_stack.clear()
        if settlement_entries:
            self.settings_mgr.set_settlement_entries(project.name, settlement_entries)
        if self.active_view == "remote":
            self.current_project_idx = -1
            self.project_list.blockSignals(True)
            self.project_list.setCurrentRow(-1)
            self.project_list.blockSignals(False)
            self._refresh_right()
            self._refresh_local_project_widgets()
            self._refresh_shared_project_widgets()

    def _on_client_received_update(self, project, settlements, settlement_entries):
        self.remote_project = project
        self.remote_settlements = settlements
        if settlement_entries:
            self.settings_mgr.set_settlement_entries(project.name, settlement_entries)
        if self.active_view == "remote":
            self._refresh_right()

    def _on_client_disconnected(self):
        if self.active_view == "remote":
            QMessageBox.information(self, "Connection Closed", "The host has stopped sharing this project or you have been disconnected.\nConnection closed.")
            self._switch_to_local_view()
            self.undo_stack.clear()
            self.current_project_idx = max(0, min(self.current_project_idx, len(self.project_mgr.projects) - 1))
            self._refresh_projects()
            self._refresh_shared_project_widgets()

    def _toggle_share_current(self):
        if not self._ensure_username_set("Enter your name to show when sharing:"):
            QMessageBox.information(self, "Required", "A username is required to share projects.")
            return

        project = self.project_mgr.get_project(self.current_project_idx)
        if not project: return
        
        if project.name in self.net_mgr.active_shares:
            if QMessageBox.question(self, "Stop Sharing", "Stop sharing this project?\nOther users will lose access to this session.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.net_mgr.stop_sharing(project.name)
                self._update_share_btn_state()
                self._update_project_list_item(self.current_project_idx)
                self.connected_users_widget.hide()
        else:
            dlg = ShareProjectDialog(self, project.name, self.net_mgr)
            if dlg.exec():
                self.net_mgr.share_project(project=project, custom_name=dlg.name_input.text().strip(), password=dlg.pass_input.text(), is_public=dlg.radio_public.isChecked())
                self._update_share_btn_state()
                self._update_project_list_item(self.current_project_idx)
                self.connected_users_widget.show()
                self._update_connected_users_ui([])

    def _update_share_btn_state(self):
        project = self.project_mgr.get_project(self.current_project_idx)
        if project and project.name in self.net_mgr.active_shares:
            self.share_top_btn.setText("Stop Sharing")
            self.share_top_btn.setObjectName("activeShareBtn")
        else:
            self.share_top_btn.setText("Share Project")
            self.share_top_btn.setObjectName("")
        self.share_top_btn.style().unpolish(self.share_top_btn)
        self.share_top_btn.style().polish(self.share_top_btn)

    def _build_teammates_section(self, parent_layout):
        lbl = QLabel("👥  Teammates"); lbl.setObjectName("sectionLabel"); parent_layout.addWidget(lbl)
        scroll = QScrollArea(); scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); scroll.setFixedHeight(75)
        avatar_container = QWidget(); avatar_container.setObjectName("avatarContainer")
        self.avatar_layout = QHBoxLayout(avatar_container); self.avatar_layout.setContentsMargins(0, 5, 0, 5); self.avatar_layout.setSpacing(12)
        scroll.setWidget(avatar_container); scroll.setWidgetResizable(True); parent_layout.addWidget(scroll)

    def _build_expenses_section(self, parent_layout):
        self.expense_section_label = QLabel("💰  Paid By Selected Teammate"); self.expense_section_label.setObjectName("sectionLabel"); parent_layout.addWidget(self.expense_section_label)
        row = QHBoxLayout()
        self.desc_input = QLineEdit(); self.desc_input.setPlaceholderText("Description (Optional)"); self.desc_input.installEventFilter(self); row.addWidget(self.desc_input, 3)
        self.amt_input = QLineEdit(); self.amt_input.setMaximumWidth(130); self.amt_input.installEventFilter(self); row.addWidget(self.amt_input, 1)
        self.add_exp_btn = QPushButton("+  Add"); self.add_exp_btn.clicked.connect(self._add_expense); row.addWidget(self.add_exp_btn)
        parent_layout.addLayout(row)
        
        self.exp_table = QTableWidget(0, 3)
        self.exp_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.exp_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.exp_table.setHorizontalHeaderLabels(["Description", "Amount", ""])
        header = self.exp_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.exp_table.setColumnWidth(2, 44)
        self.exp_table.verticalHeader().setVisible(False)
        self.exp_table.verticalHeader().setDefaultSectionSize(38) 
        self.exp_table.setItemDelegate(MarginDelegate(self.exp_table))
        self.exp_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.exp_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.exp_table.setMinimumHeight(150)
        
        self.exp_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.exp_table.customContextMenuRequested.connect(self._exp_context_menu)
        self.exp_table.cellChanged.connect(self._on_expense_description_changed)
        parent_layout.addWidget(self.exp_table)

    def _exp_context_menu(self, pos):
        item = self.exp_table.itemAt(pos)
        if not item: return
        row = item.row()
        menu = QMenu(self)
        act_more = menu.addAction("🔍  More Information")
        chosen = menu.exec(self.exp_table.viewport().mapToGlobal(pos))
        
        if chosen == act_more:
            project = self._get_current_project()
            expense = project.teammates[self.current_teammate_idx].expenses[row]
            dlg = ExpenseDetailsDialog(self, expense, project.name, self.active_view == "local", self.net_mgr.peer_id)
            if dlg.exec():
                action_data = {"teammate_idx": self.current_teammate_idx, "expense_idx": row, "expense": _expense_to_dict(expense)}
                self._dispatch_action("update_expense", action_data, lambda p: None)
                if self.active_view == "local": self._update_project_list_item(self.current_project_idx)
                self._refresh_expenses()
                self._refresh_summary()

    def _build_balance_section(self, parent_layout):
        lbl = QLabel("📊  Balance Summary"); lbl.setObjectName("sectionLabel"); parent_layout.addWidget(lbl)
        self.bal_table = QTableWidget(0, 4)
        self.bal_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.bal_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bal_table.setHorizontalHeaderLabels(["Name", "Total Paid", "Fair Share", "Balance"])
        self.bal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bal_table.verticalHeader().setVisible(False)
        self.bal_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bal_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bal_table.setMinimumHeight(150)
        parent_layout.addWidget(self.bal_table)

    def _build_settlement_section(self, parent_layout):
        settlement_header = QHBoxLayout()
        settlement_title = QLabel("🔄  Settlements (Who Pays Whom)")
        settlement_title.setObjectName("sectionLabel")
        settlement_header.addWidget(settlement_title)
        settlement_header.addStretch()
        
        self.add_settlement_btn = QPushButton("+")
        self.add_settlement_btn.setFixedSize(28, 28)
        self.add_settlement_btn.setToolTip("Add Manual Settlement")
        self.add_settlement_btn.setObjectName("smallSecondaryBtn")
        self.add_settlement_btn.clicked.connect(self._add_manual_settlement)
        settlement_header.addWidget(self.add_settlement_btn)
        
        parent_layout.addLayout(settlement_header)
        
        self.settlement_list = QListWidget()
        self.settlement_list.setObjectName("settleList")
        self.settlement_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settlement_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settlement_list.setMinimumHeight(100)
        self.settlement_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.settlement_list.customContextMenuRequested.connect(self._show_settlement_context_menu)
        self.settlement_list.itemChanged.connect(self._on_settlement_toggled)
        parent_layout.addWidget(self.settlement_list)

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
                if obj == self.amt_input:
                    if event.key() in (Qt.Key.Key_Return.value, Qt.Key.Key_Enter.value):
                        self._add_expense(); return True
                    text = event.text()
                    if text.isalpha() and self.amt_input.text().strip() == "":
                        self.desc_input.setFocus(); self.desc_input.setText(text); return True
                    elif text.isalpha(): return True 
                elif obj == self.desc_input:
                    text = event.text()
                    if text.isdigit() and self.desc_input.text().strip() == "":
                        self.amt_input.setFocus(); self.amt_input.setText(text); return True
                    elif event.key() in (Qt.Key.Key_Return.value, Qt.Key.Key_Enter.value):
                        self.amt_input.setFocus(); return True
        except Exception: pass
        return super().eventFilter(obj, event)

    def _refresh_projects(self):
        self.project_list.blockSignals(True)
        self.project_list.clear()
        for i, p in enumerate(self.project_mgr.projects):
            item = QListWidgetItem()
            item.setSizeHint(QSize(200, 48))
            self.project_list.addItem(item)
            is_selected = (i == self.current_project_idx and self.active_view == "local")
            self.project_list.setItemWidget(item, self._create_project_list_widget(p, is_selected))
        self.project_list.blockSignals(False)
        if self.project_mgr.projects:
            if self.active_view == "local":
                self.current_project_idx = max(0, min(self.current_project_idx, len(self.project_mgr.projects) - 1))
                self.project_list.setCurrentRow(self.current_project_idx)
        else:
            if self.active_view == "local":
                self.current_project_idx = -1
                self.global_title.setText("Welcome")
                self.global_dates.setText("")
        self._refresh_right()

    def _update_project_list_item(self, idx: int):
        if idx < 0 or idx >= len(self.project_mgr.projects):
            return
        item = self.project_list.item(idx)
        if item:
            is_selected = (self.active_view == "local" and idx == self.project_list.currentRow())
            self.project_list.setItemWidget(item, self._create_project_list_widget(self.project_mgr.get_project(idx), is_selected))

    def _refresh_local_project_widgets(self):
        for i in range(self.project_list.count()):
            self._update_project_list_item(i)

    def _refresh_shared_project_widgets(self):
        for i in range(self.shared_list.count()):
            item = self.shared_list.item(i)
            if item:
                p_data = item.data(Qt.ItemDataRole.UserRole)
                is_selected = (self.active_view == "remote" and self.net_mgr.connected_share_name == p_data["name"])
                self.shared_list.setItemWidget(item, self._create_shared_project_list_widget(p_data, is_selected))
                item.setSelected(is_selected)

    def _on_project_changed(self, row: int):
        if row < 0:
            return
        self._switch_to_local_view()
        self.current_project_idx = row
        self.current_teammate_idx = -1
        self.shared_list.clearSelection()
        self.undo_stack.clear()

        self._refresh_local_project_widgets()
        self._refresh_shared_project_widgets()
        self._refresh_right()

    def _add_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if ok and name.strip():
            self.project_mgr.add_project(name.strip())
            self._switch_to_local_view()
            self.current_project_idx = len(self.project_mgr.projects) - 1
            self.shared_list.clearSelection()
            self._refresh_projects()
            
    def _import_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Project JSON", "", "JSON Files (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)
            if not isinstance(data, dict) or "name" not in data or "teammates" not in data: raise ValueError("Invalid project JSON structure.")
            proj = self.project_mgr._from_json([data])[0]
            self.project_mgr.projects.append(proj)
            self.project_mgr.save()
            self._switch_to_local_view()
            self.current_project_idx = len(self.project_mgr.projects) - 1
            self.shared_list.clearSelection()
            self._refresh_projects()
            QMessageBox.information(self, "Import Successful", f"Project '{proj.name}' imported successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Import Failed", f"Could not import file:\n{str(e)}")

    def _project_context_menu(self, pos):
        if self.active_view == "remote": return
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
            if dlg.exec() == QDialog.DialogCode.Accepted:
                old_name = project.name
                
                # IMPORTANT: Automatically stop sharing to explicitly disconnect 
                # all clients prior to updating project identity logic to prevent phantom leaks
                if old_name in self.net_mgr.active_shares:
                    self.net_mgr.stop_sharing(old_name)
                    
                new_name = dlg.name_input.text().strip()
                new_desc = dlg.desc_input.text().strip()
                new_start = dlg.start_input.date().toString(Qt.DateFormat.ISODate)
                new_end = dlg.end_input.date().toString(Qt.DateFormat.ISODate)
                
                def _local(p):
                    # Handle renaming the physical attachment folder cleanly
                    if old_name != new_name:
                        old_dir = ATTACHMENTS_DIR / sanitize_filename(old_name)
                        new_dir = ATTACHMENTS_DIR / sanitize_filename(new_name)
                        if old_dir.exists() and not new_dir.exists():
                            try:
                                os.rename(old_dir, new_dir)
                            except Exception: pass
                            
                    p.name = new_name; p.description = new_desc; p.start_date = new_start; p.end_date = new_end
                
                action_data = {"name": new_name, "description": new_desc, "start_date": new_start, "end_date": new_end}
                self._dispatch_action("update_project", action_data, _local)
                
                self._update_project_list_item(row)
                self._refresh_right()
                
            elif dlg.result() == 2:
                if project.name in self.net_mgr.active_shares: 
                    self.net_mgr.stop_sharing(project.name)
                self.project_mgr.remove_project(row)
                self.current_project_idx = min(self.current_project_idx, len(self.project_mgr.projects) - 1)
                self._refresh_projects()

    def _get_initials(self, name: str) -> str:
        parts = name.strip().split()
        if not parts: return "?"
        return parts[0][:2].upper() if len(parts) == 1 else (parts[0][0] + parts[-1][0]).upper()

    def _refresh_teammates(self):
        for btn in self.avatar_btn_group.buttons(): self.avatar_btn_group.removeButton(btn)
        while self.avatar_layout.count():
            child = self.avatar_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        project = self._get_current_project()
        if not project: return
        
        for i, t in enumerate(project.teammates):
            btn = QPushButton(); btn.setObjectName("avatarBtn"); btn.setFixedSize(48, 48); btn.setCheckable(True)
            tooltip = t.name
            if t.description: tooltip += f"\n({t.description})"
            btn.setToolTip(tooltip)
            if t.avatar:
                try:
                    path = safe_path_resolve(ATTACHMENTS_DIR / sanitize_filename(project.name), t.avatar)
                    if path.exists():
                        p = QPixmap(str(path))
                        btn.setIcon(QIcon(create_circular_pixmap(p, 44))); btn.setIconSize(QSize(44, 44))
                    else:
                        btn.setText(self._get_initials(t.name))
                except ValueError:
                    btn.setText(self._get_initials(t.name))
            else:
                btn.setText(self._get_initials(t.name))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, idx=i, b=btn: self._teammate_context_menu(b.mapToGlobal(pos), idx))
            self.avatar_btn_group.addButton(btn, i)
            self.avatar_layout.addWidget(btn)
            
        add_btn = QPushButton("+"); add_btn.setObjectName("avatarAddBtn"); add_btn.setFixedSize(48, 48); add_btn.clicked.connect(self._add_teammate)
        self.avatar_layout.addWidget(add_btn); self.avatar_layout.addStretch()
        
        if project.teammates:
            if self.current_teammate_idx < 0 or self.current_teammate_idx >= len(project.teammates): self.current_teammate_idx = 0
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
            t = Teammate(name=name.strip())
            
            def _local(p):
                for existing_t in p.teammates:
                    if existing_t.name.lower() == name.strip().lower(): return
                p.teammates.append(t)
                
            action_data = {"teammate": {"name": t.name, "description": t.description, "avatar": t.avatar, "expenses": []}}
            self._dispatch_action("add_teammate", action_data, _local)
            
            if self.active_view == "local": self._update_project_list_item(self.current_project_idx)
            self.current_teammate_idx = len(self._get_current_project().teammates) - 1
            self._refresh_right()

    def _teammate_context_menu(self, pos, tidx: int):
        project = self._get_current_project()
        if not project or tidx >= len(project.teammates): return
        menu = QMenu(self)
        act_edit = menu.addAction("✏️  Edit Teammate")
        if menu.exec(pos) == act_edit:
            dlg = TeammateEditDialog(self, project.teammates[tidx], project.name)
            res = dlg.exec()
            if res == QDialog.DialogCode.Accepted:
                new_name = dlg.name_input.text().strip()
                new_desc = dlg.desc_input.text().strip()
                new_avatar = dlg.avatar_file
                
                def _local(p):
                    p.teammates[tidx].name = new_name
                    p.teammates[tidx].description = new_desc
                    p.teammates[tidx].avatar = new_avatar
                    
                action_data = {"teammate_idx": tidx, "teammate": {"name": new_name, "description": new_desc, "avatar": new_avatar, "expenses": []}}
                self._dispatch_action("update_teammate", action_data, _local)
                
                if self.active_view == "local": self._update_project_list_item(self.current_project_idx)
                self._refresh_right()
            elif res == 2:
                def _local(p): del p.teammates[tidx]
                action_data = {"teammate_idx": tidx}
                self._dispatch_action("delete_teammate", action_data, _local)
                
                if self.current_teammate_idx == tidx: self.current_teammate_idx = -1
                elif self.current_teammate_idx > tidx: self.current_teammate_idx -= 1
                if self.active_view == "local": self._update_project_list_item(self.current_project_idx)
                self._refresh_right()

    def _update_expense_ui_state(self):
        has_teammate = self.current_teammate_idx >= 0
        self.desc_input.setEnabled(has_teammate)
        self.amt_input.setEnabled(has_teammate)
        self.add_exp_btn.setEnabled(has_teammate)
        curr = self.settings_mgr.get("currency", "RM")
        self.amt_input.setPlaceholderText(f"Amount ({curr})")
        if has_teammate:
            project = self._get_current_project()
            if project and 0 <= self.current_teammate_idx < len(project.teammates):
                self.expense_section_label.setText(f"💰  Paid By {project.teammates[self.current_teammate_idx].name}")
                self.desc_input.setPlaceholderText("Description (Optional)")
        else:
            self.expense_section_label.setText("💰  Paid By Selected Teammate")
            self.desc_input.setPlaceholderText("Select a teammate first...")

    def _refresh_expenses(self):
        self.exp_table.blockSignals(True)
        self.exp_table.setRowCount(0)
        project = self._get_current_project()
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
        btn = QPushButton("✕"); btn.setObjectName("deleteRowBtn"); btn.setFixedSize(34, 24)
        btn.clicked.connect(lambda _, t=ti, idx=ei: self._remove_expense(t, idx))
        self.exp_table.setCellWidget(row, 2, btn)

    def _on_expense_description_changed(self, row, col):
        if col == 0:
            new_desc = self.exp_table.item(row, col).text()
            project = self._get_current_project()
            
            def _local(p): p.teammates[self.current_teammate_idx].expenses[row].description = new_desc.strip() or "Undefined"
            
            exp_dict = _expense_to_dict(project.teammates[self.current_teammate_idx].expenses[row])
            exp_dict["description"] = new_desc.strip() or "Undefined"
            
            action_data = {"teammate_idx": self.current_teammate_idx, "expense_idx": row, "expense": exp_dict}
            self._dispatch_action("update_expense", action_data, _local)
            
            if self.active_view == "local": self._update_project_list_item(self.current_project_idx)

    def _add_expense(self):
        desc = self.desc_input.text().strip() or "Undefined"
        amt_text = self.amt_input.text().strip()
        for sym in list(CURRENCIES.keys()) + [" ", ","]: amt_text = amt_text.replace(sym, "")
        try:
            amt = float(amt_text)
            if not math.isfinite(amt) or amt <= 0: raise ValueError
        except ValueError:
            if amt_text != "": QMessageBox.warning(self, "Invalid", "Please enter a valid positive finite amount.")
            return
            
        exp = Expense(description=desc, amount=round(amt,2))
        
        def _local(p): p.teammates[self.current_teammate_idx].expenses.append(exp)
        
        action_data = {"teammate_idx": self.current_teammate_idx, "expense": _expense_to_dict(exp)}
        self._dispatch_action("add_expense", action_data, _local)
        
        if self.active_view == "local": self._update_project_list_item(self.current_project_idx)
        
        self.desc_input.clear(); self.amt_input.clear(); self.amt_input.setFocus()
        self._refresh_expenses(); self._refresh_summary(); self._refresh_settlements()

    def _remove_expense(self, tidx: int, eidx: int):
        project = self._get_current_project()
        if not project or tidx >= len(project.teammates) or eidx >= len(project.teammates[tidx].expenses):
            return
        
        exp_copy = deepcopy(project.teammates[tidx].expenses[eidx])
        self.undo_stack.append({
            "teammate_idx": tidx,
            "expense_idx": eidx,
            "expense": exp_copy
        })
        if len(self.undo_stack) > 30: self.undo_stack.pop(0)

        def _local(p): del p.teammates[tidx].expenses[eidx]
        action_data = {"teammate_idx": tidx, "expense_idx": eidx}
        
        self._dispatch_action("delete_expense", action_data, _local)
        
        if self.active_view == "local": self._update_project_list_item(self.current_project_idx)
        self._refresh_expenses(); self._refresh_summary(); self._refresh_settlements()

    def _undo_last_delete(self):
        if not self.undo_stack: return
        action = self.undo_stack.pop()
        tidx = action["teammate_idx"]
        eidx = action["expense_idx"]
        exp = action["expense"]
        
        def _local(p):
            if tidx < len(p.teammates):
                safe_idx = min(eidx, len(p.teammates[tidx].expenses))
                p.teammates[tidx].expenses.insert(safe_idx, exp)
                
        action_data = {"teammate_idx": tidx, "expense_idx": eidx, "expense": _expense_to_dict(exp)}
        self._dispatch_action("insert_expense", action_data, _local)
        
        if self.active_view == "local": self._update_project_list_item(self.current_project_idx)
        
        if self.current_teammate_idx == tidx:
            self._refresh_expenses()
        self._refresh_summary(); self._refresh_settlements()

    def _refresh_summary(self):
        project = self._get_current_project()
        self.bal_table.setRowCount(0)
        
        if not project or not project.teammates:
            self.total_label.setText(f"Total Expenses:  {self._format_money(0.0)}")
            return

        stored_entries = self.settings_mgr.get_settlement_entries(project.name)
        summary, settlements, total = BalanceCalculator.calculate(project, stored_entries)
        
        for name, data in summary.items():
            row = self.bal_table.rowCount(); self.bal_table.insertRow(row)
            self.bal_table.setItem(row, 0, QTableWidgetItem(name))
            c1 = QTableWidgetItem(self._format_money(data['paid']))
            c1.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.bal_table.setItem(row, 1, c1)
            
            c2 = QTableWidgetItem(self._format_money(data['share']))
            c2.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.bal_table.setItem(row, 2, c2)
            
            net = data["net"]
            c3 = QTableWidgetItem(f"{'+' if net>0 else ''}{self._format_money(abs(net))}")
            c3.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if net > 0: c3.setForeground(QColor("#27AE60"))
            elif net < 0: c3.setForeground(QColor("#E74C3C")); c3.setText(f"-{self._format_money(abs(net))}")
            self.bal_table.setItem(row, 3, c3)

        self.total_label.setText(f"Total Expenses:  {self._format_money(total)}")

    def _migrate_old_settlements(self, project):
        if self.active_view == "remote": return
        old_keys = self.settings_mgr.get("settlements", {}).get(project.name, [])
        if not old_keys: return
        
        stored_entries = self.settings_mgr.get_settlement_entries(project.name)
        for key in old_keys:
            parts = key.split("_")
            if len(parts) == 3:
                from_p, to_p, cents_str = parts[0], parts[1], parts[2]
                try:
                    amt = int(cents_str) / 100.0
                    exists = any(e["from_person"] == from_p and e["to_person"] == to_p and abs(e.get("amount", 0) - amt) < 0.01 for e in stored_entries)
                    if not exists:
                        self.settings_mgr.add_settlement_entry(project.name, {
                            "from_person": from_p,
                            "to_person": to_p,
                            "amount": amt,
                            "id": str(uuid.uuid4()),
                            "is_completed": True,
                            "is_manual": False,
                            "payment_date": "",
                            "payment_time": "",
                            "detailed_description": "Migrated from previous version",
                            "attachments": []
                        })
                except ValueError: pass
        
        s_map = self.settings_mgr.get("settlements", {})
        if project.name in s_map:
            del s_map[project.name]
            self.settings_mgr.set("settlements", s_map)

    def _refresh_settlements(self):
        self.settlement_list.blockSignals(True)
        self.settlement_list.clear()
        
        project = self._get_current_project()
        if not project or not project.teammates:
            self.settlement_list.blockSignals(False)
            return

        self._migrate_old_settlements(project)
        stored_entries = self.settings_mgr.get_settlement_entries(project.name)
        summary, auto_settlements, total = BalanceCalculator.calculate(project, stored_entries)
        
        for entry in stored_entries:
            if entry.get("is_completed") or entry.get("is_manual"):
                amount = entry.get("amount", 0)
                is_settled = entry.get("is_completed", False)
                is_manual = entry.get("is_manual", False)
                
                prefix = "[Manual] " if is_manual else "[Paid] " if is_settled else ""
                txt = f"{prefix}{entry['from_person']}  ➜  {entry['to_person']}:  {self._format_money(amount)}"

                item = QListWidgetItem(txt)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if is_settled else Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, {
                    "key": entry.get("id", ""),
                    "from_person": entry["from_person"],
                    "to_person": entry["to_person"],
                    "amount": amount,
                    "id": entry.get("id", ""),
                    "is_manual": is_manual
                })
                
                font = item.font()
                font.setStrikeOut(is_settled)
                item.setFont(font)
                if is_settled:
                    item.setForeground(QColor("#888888"))
                else:
                    txt_c = QColor("#E0E0E0") if get_actual_theme(self.settings_mgr.get("theme", "system")) == "dark" else QColor("#333333")
                    item.setForeground(txt_c)
                self.settlement_list.addItem(item)
                
        uncompleted_autos = [e for e in stored_entries if not e.get("is_completed") and not e.get("is_manual")]
        
        for s in auto_settlements:
            amount = s["amount"]
            if amount <= 0: continue
            
            matched_entry = next((e for e in uncompleted_autos if e["from_person"] == s["from"] and e["to_person"] == s["to"]), None)
            entry_id = matched_entry["id"] if matched_entry else ""
            
            txt = f"{s['from']}  ➜  {s['to']}:  {self._format_money(amount)}"
            item = QListWidgetItem(txt)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, {
                "key": entry_id,
                "from_person": s["from"],
                "to_person": s["to"],
                "amount": amount,
                "id": entry_id,
                "is_manual": False
            })
            
            txt_c = QColor("#E0E0E0") if get_actual_theme(self.settings_mgr.get("theme", "system")) == "dark" else QColor("#333333")
            item.setForeground(txt_c)
            self.settlement_list.addItem(item)
            
        if self.settlement_list.count() == 0:
            item = QListWidgetItem("✅ All settled! No transfers needed.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.settlement_list.addItem(item)
            
        self.settlement_list.blockSignals(False)

    def _on_settlement_toggled(self, item):
        settlement = item.data(Qt.ItemDataRole.UserRole)
        if not settlement: return
        
        checked = item.checkState() == Qt.CheckState.Checked
        project = self._get_current_project()
        if not project: return
        
        entry_id = settlement.get("id", "")
        is_manual = settlement.get("is_manual", False)
        
        if not entry_id and not is_manual:
            new_entry = {
                "from_person": settlement["from_person"],
                "to_person": settlement["to_person"],
                "amount": settlement["amount"],
                "id": str(uuid.uuid4()),
                "is_completed": checked,
                "is_manual": False,
                "payment_date": "",
                "payment_time": "",
                "detailed_description": "",
                "attachments": []
            }
            self.settings_mgr.add_settlement_entry(project.name, new_entry)
        elif entry_id:
            self.settings_mgr.update_settlement_entry(project.name, entry_id, {"is_completed": checked})
        
        self._sync_settlement_update()
        self._refresh_summary()
        self._refresh_settlements()

    def _show_settlement_context_menu(self, pos):
        item = self.settlement_list.itemAt(pos)
        if not item:
            return
        
        settlement = item.data(Qt.ItemDataRole.UserRole)
        if not settlement:
            return
        
        menu = QMenu(self)
        more_info_action = menu.addAction("ℹ️ More Information")
        
        action = menu.exec(self.settlement_list.mapToGlobal(pos))
        if action == more_info_action:
            self._show_settlement_details(settlement)

    def _show_settlement_details(self, settlement):
        project = self._get_current_project()
        if not project:
            return
        
        entry_id = settlement.get("id", "")
        
        if not entry_id:
            new_entry = {
                "from_person": settlement["from_person"],
                "to_person": settlement["to_person"],
                "amount": settlement["amount"],
                "id": str(uuid.uuid4()),
                "is_completed": False,
                "is_manual": False,
                "payment_date": "",
                "payment_time": "",
                "detailed_description": "",
                "attachments": []
            }
            self.settings_mgr.add_settlement_entry(project.name, new_entry)
            entry_id = new_entry["id"]
        
        stored_entries = self.settings_mgr.get_settlement_entries(project.name)
        full_entry = next((e for e in stored_entries if e.get("id") == entry_id), None)
        if not full_entry:
            return
        
        is_host = (self.active_view == "local")
        local_peer_id = self.net_mgr.peer_id
        
        dlg = SettlementDetailsDialog(self, full_entry, project.name, is_host, local_peer_id)
        res = dlg.exec()
        if res == QDialog.DialogCode.Accepted:
            self.settings_mgr.update_settlement_entry(project.name, entry_id, {
                "payment_date": full_entry.get("payment_date", ""),
                "payment_time": full_entry.get("payment_time", ""),
                "detailed_description": full_entry.get("detailed_description", ""),
                "attachments": full_entry.get("attachments", [])
            })
            self._refresh_settlements()
            self._sync_settlement_update()
        elif res == 3:
            self.settings_mgr.remove_settlement_entry(project.name, entry_id)
            self._refresh_settlements()
            self._sync_settlement_update()

    def _sync_settlement_update(self):
        project = self._get_current_project()
        if not project:
            return
            
        settlement_entries = self.settings_mgr.get_settlement_entries(project.name)
        if self.active_view == "remote":
            self.net_mgr.send_client_action(project.name, "update_settlements", {"settlement_entries": settlement_entries})
        elif self.active_view == "local" and project.name in self.net_mgr.active_shares:
            self.net_mgr.host_broadcast_update(project)

    def _add_manual_settlement(self):
        project = self._get_current_project()
        if not project:
            return
            
        curr = self.settings_mgr.get("currency", "RM")
        prefix, suffix, _, _ = CURRENCIES.get(curr, ("RM", "", 2, False))
        
        dlg = ManualSettlementDialog(self, project.teammates, currency_prefix=prefix, currency_suffix=suffix)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            new_entry = {
                "from_person": data["from_person"],
                "to_person": data["to_person"],
                "amount": data["amount"],
                "id": str(uuid.uuid4()),
                "is_completed": False,
                "is_manual": True,
                "payment_date": "",
                "payment_time": "",
                "detailed_description": data["description"],
                "attachments": []
            }
            self.settings_mgr.add_settlement_entry(project.name, new_entry)
            self._refresh_settlements()
            self._sync_settlement_update()

    def _refresh_right(self):
        project = self._get_current_project()
        if not project:
            self.right_stack.setCurrentIndex(0)
            self.global_title.setText("Welcome")
            self.global_dates.setText("")
            self.share_top_btn.hide()
            self.connected_users_widget.hide()
            return

        self.right_stack.setCurrentIndex(1)
        
        if self.active_view == "remote":
            host_name = getattr(self.net_mgr, 'connected_host_name', 'Unknown Host')
            if not host_name: host_name = "Unknown Host"
            self.global_title.setText(f"{project.name} ({host_name}'s Project)")
            self.share_top_btn.hide()
            self.connected_users_widget.hide()
        else:
            self.global_title.setText(project.name)
            if self.settings_mgr.get("enable_sharing", True):
                self.share_top_btn.show()
                self._update_share_btn_state()
                
            if project.name in self.net_mgr.active_shares:
                self.connected_users_widget.show()
                client_names = list(self.net_mgr.active_shares[project.name]["clients"].values())
                self._update_connected_users_ui(client_names)
            else:
                self.connected_users_widget.hide()

        dates_text = f" ({project.start_date} to {project.end_date})" if project.start_date and project.end_date else ""
        self.global_dates.setText(dates_text)

        self._refresh_teammates()
        self._refresh_expenses()
        self._refresh_summary()
        self._refresh_settlements()

    def _show_export_menu(self):
        project = self._get_current_project()
        if not project: return
        menu = QMenu(self)
        act_pdf = menu.addAction("📄  Export to PDF")
        act_excel = menu.addAction("📊  Export to Excel")
        act_json = menu.addAction("📦  Export to JSON")
        chosen = menu.exec(self.sender().mapToGlobal(self.sender().rect().topRight()))
        if chosen == act_pdf: self._export_pdf(project)
        elif chosen == act_excel: self._export_excel(project)
        elif chosen == act_json: self._export_json(project)

    def _export_json(self, project):
        path, _ = QFileDialog.getSaveFileName(self, "Export Project JSON", f"{project.name}.json", "JSON Files (*.json)")
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f: json.dump(ProjectManager._to_json([project])[0], f, indent=4)
            QMessageBox.information(self, "Export Successful", f"JSON saved to:\n{path}")
        except Exception as e: QMessageBox.warning(self, "Export Failed", f"Could not export file:\n{str(e)}")

    def _export_pdf(self, project):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", f"{project.name}_Report.pdf", "PDF Files (*.pdf)")
        if not path: return
        stored_entries = self.settings_mgr.get_settlement_entries(project.name)
        summary, auto_settlements, total = BalanceCalculator.calculate(project, stored_entries)
        dates_html = f"<p><strong>Duration:</strong> {project.start_date} to {project.end_date}</p>" if project.start_date else ""
        desc_html = f"<p><strong>Description:</strong> {project.description}</p>" if project.description else ""
        html = f"<html><head><style>body {{ font-family: sans-serif; color: #333; }} h1, h2 {{ color: #2A6099; }} table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }} th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }} th {{ background-color: #f4f4f4; }} .right {{ text-align: right; }} .green {{ color: #27AE60; }} .red {{ color: #E74C3C; }} .strike {{ text-decoration: line-through; color: #999; }}</style></head><body><h1>{project.name} - Balance Report</h1><p><strong>Total Project Expenses:</strong> {self._format_money(total)}</p><h2>1. Balance Summary</h2><table><tr><th>Name</th><th class='right'>Total Paid</th><th class='right'>Fair Share</th><th class='right'>Balance</th></tr>"
        for name, data in summary.items():
            net = data["net"]
            html += f"<tr><td>{name}</td><td class='right'>{self._format_money(data['paid'])}</td><td class='right'>{self._format_money(data['share'])}</td><td class='right {'green' if net>0 else 'red' if net<<0 else ''}'>{'+' if net>0 else '-' if net<<0 else ''}{self._format_money(abs(net))}</td></tr>"
        
        html += "</table><h2>2. Settlements</h2><ul>"
        display_items = []
        for entry in stored_entries:
            if entry.get("is_completed") or entry.get("is_manual"):
                amount = entry.get("amount", 0)
                is_settled = entry.get("is_completed", False)
                is_manual = entry.get("is_manual", False)
                prefix = "[Manual] " if is_manual else "[Paid] " if is_settled else ""
                css = "class='strike'" if is_settled else ""
                display_items.append(f"<li {css}>{prefix}<strong>{entry['from_person']}</strong> pays <strong>{entry['to_person']}</strong>: {self._format_money(amount)}</li>")
                
        for s in auto_settlements:
            amount = s["amount"]
            if amount > 0:
                display_items.append(f"<li><strong>{s['from']}</strong> pays <strong>{s['to']}</strong>: {self._format_money(amount)}</li>")
                
        if not display_items:
            html += "<li>✅ All settled! No transfers needed.</li>"
        else:
            html += "".join(display_items)

        html += "</ul><div style='page-break-before: always;'></div><h2>3. Detailed Expenses List</h2><table><tr><th>Paid By</th><th>Date</th><th>Description</th><th class='right'>Amount</th></tr>"
        for t in project.teammates:
            for e in t.expenses: html += f"<tr><td>{t.name}</td><td>{e.date}</td><td>{e.description}</td><td class='right'>{self._format_money(e.amount)}</td></tr>"
        html += "</table></body></html>"
        doc = QTextDocument(); doc.setHtml(html); doc.print(QPdfWriter(path))
        QMessageBox.information(self, "Export Successful", f"PDF saved to:\n{path}")

    def _export_excel(self, project):
        try: import pandas as pd
        except ImportError:
            QMessageBox.critical(self, "Missing", "Install via terminal:\npip install pandas openpyxl"); return
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", f"{project.name}_Report.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        stored_entries = self.settings_mgr.get_settlement_entries(project.name)
        summary, auto_settlements, _ = BalanceCalculator.calculate(project, stored_entries)
        curr = self.settings_mgr.get("currency", "RM")
        
        df_bal = pd.DataFrame([{"Name": k, f"Total Paid ({curr})": v["paid"], f"Fair Share ({curr})": v["share"], f"Balance ({curr})": v["net"]} for k, v in summary.items()])
        
        settlement_data = []
        for entry in stored_entries:
            if entry.get("is_completed") or entry.get("is_manual"):
                settlement_data.append({
                    "From": entry["from_person"], 
                    "To": entry["to_person"], 
                    f"Amount ({curr})": entry.get("amount", 0), 
                    "Paid": "Yes" if entry.get("is_completed") else "No",
                    "Type": "Manual" if entry.get("is_manual") else "Historical"
                })
        for s in auto_settlements:
            if s["amount"] > 0:
                settlement_data.append({
                    "From": s["from"], 
                    "To": s["to"], 
                    f"Amount ({curr})": s["amount"], 
                    "Paid": "No",
                    "Type": "Auto"
                })
                
        df_settle = pd.DataFrame(settlement_data)
        df_exp = pd.DataFrame([{"Paid By": t.name, "Date": e.date, "Time": e.time, "Description": e.description, "Notes": e.detailed_description, f"Amount ({curr})": e.amount} for t in project.teammates for e in t.expenses])
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            if not df_bal.empty: df_bal.to_excel(writer, sheet_name="Summary", index=False, startrow=0)
            if not df_settle.empty: df_settle.to_excel(writer, sheet_name="Summary", index=False, startrow=len(df_bal) + 3)
            if not df_exp.empty: df_exp.to_excel(writer, sheet_name="Detailed Expenses", index=False)
        QMessageBox.information(self, "Export Successful", f"Excel saved to:\n{path}")

    def _open_settings(self):
        if SettingsDialog(self, self.settings_mgr).exec():
            self._apply_theme()
            self._refresh_projects()
            self._apply_network_settings()

    def _restore_splitters(self):
        self.main_splitter.setSizes(self.settings_mgr.get("left_panel_sizes", [250, 850]))
        self.left_inner_splitter.setSizes(self.settings_mgr.get("shared_panel_sizes", [300, 300]))
        self.content_splitter.setSizes(self.settings_mgr.get("content_splitter_sizes", [400, 400]))
        self.right_col_splitter.setSizes(self.settings_mgr.get("right_col_sizes", [300, 300]))

    def closeEvent(self, event):
        self.net_mgr.stop()
        if self.main_splitter.sizes(): self.settings_mgr.set("left_panel_sizes", self.main_splitter.sizes())
        if self.left_inner_splitter.sizes(): self.settings_mgr.set("shared_panel_sizes", self.left_inner_splitter.sizes())
        if self.content_splitter.sizes(): self.settings_mgr.set("content_splitter_sizes", self.content_splitter.sizes())
        if self.right_col_splitter.sizes(): self.settings_mgr.set("right_col_sizes", self.right_col_splitter.sizes())
        event.accept()
