import os
import uuid
import shutil
import urllib.request
import webbrowser
import requests
import math
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem, 
    QCheckBox, QRadioButton, QTabWidget, QTextEdit, QDateEdit, QTimeEdit, QColorDialog, QFileDialog, 
    QMessageBox, QAbstractItemView, QFrame, QComboBox, QApplication, QWidget, QGridLayout
)
from PyQt6.QtCore import Qt, QDate, QTime, QUrl, QSize
from PyQt6.QtGui import QColor, QDesktopServices, QPixmap, QIcon

from logic_models import Expense, Teammate, Project
from config import ATTACHMENTS_DIR, CURRENCIES, sanitize_filename, safe_path_resolve, APP_VERSION, resource_path

def create_circular_pixmap(pixmap, size=48):
    from PyQt6.QtGui import QPainter, QPainterPath
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

class ShareProjectDialog(QDialog):
    def __init__(self, parent, project_name, net_mgr):
        super().__init__(parent)
        self.net_mgr = net_mgr
        self.setWindowTitle("Share Project to Local Network")
        self.setFixedSize(380, 320)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Discoverable Project Name:"))
        self.name_input = QLineEdit(project_name)
        layout.addWidget(self.name_input)
        
        self.pass_check = QCheckBox("Require Password")
        self.pass_check.toggled.connect(self._toggle_pass)
        layout.addWidget(self.pass_check)
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Enter a password...")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setEnabled(False)
        self.pass_input.returnPressed.connect(self._on_share_click)
        layout.addWidget(self.pass_input)

        layout.addWidget(QLabel("\nVisibility Mode:"))
        self.radio_public = QRadioButton("Public Mode (Auto-discoverable)")
        self.radio_public.setChecked(True)
        self.radio_private = QRadioButton("Private Mode (Hidden from network scans)")
        layout.addWidget(self.radio_public)
        layout.addWidget(self.radio_private)

        from logic_network import CRYPTO_AVAILABLE
        if not CRYPTO_AVAILABLE:
            warn = QLabel("⚠️ 'cryptography' library not installed. Encryption disabled.")
            warn.setStyleSheet("color: #E74C3C; font-size: 11px;")
            layout.addWidget(warn)

        layout.addStretch()
        btn_layout = QHBoxLayout()
        share_btn = QPushButton("Start Sharing")
        share_btn.setDefault(True)
        share_btn.clicked.connect(self._on_share_click)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(share_btn)
        layout.addLayout(btn_layout)

        # Default to requiring a password
        self.pass_check.setChecked(True)

    def _toggle_pass(self, checked):
        self.pass_input.setEnabled(checked)
        if checked: self.pass_input.setFocus()

    def _on_share_click(self):
        target_name = self.name_input.text().strip().lower()
        for p in self.net_mgr.discovered_projects.values():
            if p["name"].lower() == target_name:
                QMessageBox.warning(self, "Name Conflict", "This shared project name is already being used on the network.")
                return
        self.accept()

class ConnectPrivateDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Connect to Private Project")
        self.setFixedSize(320, 180)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Exact Project Name:"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)
        
        layout.addWidget(QLabel("Password (If required):"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.returnPressed.connect(self.accept)
        layout.addWidget(self.pass_input)
        
        layout.addStretch()
        btn_layout = QHBoxLayout()
        conn_btn = QPushButton("Connect")
        conn_btn.setDefault(True)
        conn_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(conn_btn)
        layout.addLayout(btn_layout)

class ExpenseDetailsDialog(QDialog):
    def __init__(self, parent, expense: Expense, project_name: str, is_host: bool, local_peer_id: str):
        super().__init__(parent)
        self.expense = expense
        self.project_name = project_name
        self.is_host = is_host
        self.local_peer_id = local_peer_id
        
        self.setWindowTitle("Expense More Information")
        self.setFixedSize(500, 480)
        
        self.pending_adds = []
        self.pending_removes = []
        self.current_attachments = list(expense.attachments)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        gen_tab = QWidget(); gen_tab.setObjectName("gen_tab")
        gen_lay = QVBoxLayout(gen_tab)
        gen_lay.addWidget(QLabel("Title:"))
        self.title_input = QLineEdit(expense.description)
        gen_lay.addWidget(self.title_input)
        
        date_time_lay = QHBoxLayout()
        date_time_lay.addWidget(QLabel("Date:"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.fromString(expense.date, "yyyy-MM-dd"))
        date_time_lay.addWidget(self.date_input)
        
        date_time_lay.addWidget(QLabel("Time:"))
        self.time_input = QTimeEdit()
        self.time_input.setTime(QTime.fromString(expense.time, "HH:mm"))
        date_time_lay.addWidget(self.time_input)
        gen_lay.addLayout(date_time_lay)
        
        gen_lay.addWidget(QLabel("Detailed Description:"))
        self.details_input = QTextEdit(expense.detailed_description)
        gen_lay.addWidget(self.details_input)
        self.tabs.addTab(gen_tab, "General Information")
        
        att_tab = QWidget(); att_tab.setObjectName("att_tab")
        att_lay = QVBoxLayout(att_tab)
        
        self.att_list = QListWidget()
        self.att_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.att_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.att_list.setIconSize(QSize(100, 100))
        self.att_list.setGridSize(QSize(120, 120))
        self.att_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.att_list.setSpacing(10)
        self.att_list.setWordWrap(True)
        self.att_list.itemDoubleClicked.connect(self._open_attachment)
        
        self._refresh_att_list()
        att_lay.addWidget(self.att_list)
        
        att_btn_lay = QHBoxLayout()
        add_att_btn = QPushButton("Add Attachment")
        add_att_btn.setObjectName("secondaryBtn")
        add_att_btn.clicked.connect(self._add_attachment)
        open_att_btn = QPushButton("Open Selected")
        open_att_btn.setObjectName("secondaryBtn")
        open_att_btn.clicked.connect(self._open_attachment)
        rem_att_btn = QPushButton("Remove Selected")
        rem_att_btn.setObjectName("dangerBtn")
        rem_att_btn.clicked.connect(self._remove_attachment)
        
        att_btn_lay.addWidget(add_att_btn)
        att_btn_lay.addWidget(open_att_btn)
        att_btn_lay.addWidget(rem_att_btn)
        att_lay.addLayout(att_btn_lay)
        self.tabs.addTab(att_tab, "Attachments")
        
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _refresh_att_list(self):
        self.att_list.clear()
        proj_folder = ATTACHMENTS_DIR / sanitize_filename(self.project_name)
        for att in self.current_attachments:
            item = QListWidgetItem()
            try:
                path = att.get("source_path", str(safe_path_resolve(proj_folder, att["saved_name"])))
            except ValueError:
                continue
            
            if os.path.exists(path) and path.lower().endswith(('.png', '.jpg', '.jpeg')):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
            else:
                item.setText(f"📄\n{att['original_name']}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
            item.setToolTip(att['original_name'])
            item.setData(Qt.ItemDataRole.UserRole, att)
            self.att_list.addItem(item)

    def _add_attachment(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Attachments", "", "Images/PDF (*.jpg *.jpeg *.png *.pdf)")
        for p in paths:
            orig_name = os.path.basename(p)
            unique_id = uuid.uuid4().hex[:8]
            saved_name = f"{unique_id}_{sanitize_filename(orig_name)}"
            att_dict = {
                "original_name": orig_name,
                "saved_name": saved_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "source_path": p,
                "owner": self.local_peer_id 
            }
            self.current_attachments.append(att_dict)
            self.pending_adds.append(att_dict)
        self._refresh_att_list()

    def _remove_attachment(self):
        item = self.att_list.currentItem()
        if not item: return
        att = item.data(Qt.ItemDataRole.UserRole)
        
        if not self.is_host and att.get("owner") != self.local_peer_id:
            QMessageBox.warning(self, "Permission Denied", "You can only delete attachments that you uploaded.")
            return
            
        self.current_attachments.remove(att)
        if att in self.pending_adds: self.pending_adds.remove(att)
        else: self.pending_removes.append(att)
        self._refresh_att_list()

    def _open_attachment(self):
        item = self.att_list.currentItem()
        if not item: return
        att = item.data(Qt.ItemDataRole.UserRole)
        try:
            path = att.get("source_path", str(safe_path_resolve(ATTACHMENTS_DIR / sanitize_filename(self.project_name), att["saved_name"])))
            if os.path.exists(path): 
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            else: 
                QMessageBox.warning(self, "File Not Found", "Attachment not fully synced or unavailable.")
        except ValueError:
            QMessageBox.warning(self, "Security Block", "Invalid or unsafe file path requested.")

    def _save(self):
        self.expense.description = self.title_input.text().strip() or "Undefined"
        self.expense.date = self.date_input.date().toString("yyyy-MM-dd")
        self.expense.time = self.time_input.time().toString("HH:mm")
        self.expense.detailed_description = self.details_input.toPlainText()
        
        proj_folder = ATTACHMENTS_DIR / sanitize_filename(self.project_name)
        proj_folder.mkdir(parents=True, exist_ok=True)
        
        for add in self.pending_adds:
            try:
                safe_dest = safe_path_resolve(proj_folder, add["saved_name"])
                shutil.copy2(add["source_path"], safe_dest)
            except Exception: pass
            if "source_path" in add: del add["source_path"]
            
        for rem in self.pending_removes:
            try:
                safe_rem = safe_path_resolve(proj_folder, rem["saved_name"])
                os.remove(safe_rem)
            except Exception: pass
            
        self.expense.attachments = self.current_attachments
        self.accept()

class ManualSettlementDialog(QDialog):
    def __init__(self, parent, teammates: list, currency_prefix: str = "", currency_suffix: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Add Manual Settlement")
        self.setFixedSize(350, 350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        layout.addWidget(QLabel("From (Payer):"))
        self.from_combo = QComboBox()
        self.from_combo.addItems([t.name for t in teammates])
        self.from_combo.setMinimumHeight(30)
        layout.addWidget(self.from_combo)
        
        layout.addWidget(QLabel("To (Payee):"))
        self.to_combo = QComboBox()
        self.to_combo.addItems([t.name for t in teammates])
        if len(teammates) > 1:
            self.to_combo.setCurrentIndex(1)
            self.to_combo.setMinimumHeight(30)
        layout.addWidget(self.to_combo)
        
        amt_label_text = "Amount:"
        if currency_prefix:
            amt_label_text = f"Amount ({currency_prefix}):"
        elif currency_suffix:
            amt_label_text = f"Amount ({currency_suffix}):"
        layout.addWidget(QLabel(amt_label_text))
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        self.amount_input.setMinimumHeight(30)
        layout.addWidget(self.amount_input)
        
        layout.addWidget(QLabel("Description (Optional):"))
        self.desc_input = QLineEdit()
        self.desc_input.setMinimumHeight(30)
        layout.addWidget(self.desc_input)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Settlement")
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._validate_and_accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(add_btn)
        layout.addLayout(btn_layout)
    
    def _validate_and_accept(self):
        try:
            amount = float(self.amount_input.text().strip())
            if not math.isfinite(amount) or amount <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid positive finite amount.")
            return
        if self.from_combo.currentText() == self.to_combo.currentText():
            QMessageBox.warning(self, "Invalid Selection", "Payer and Payee cannot be the same person.")
            return
        self.accept()
    
    def get_data(self) -> dict:
        return {
            "from_person": self.from_combo.currentText(),
            "to_person": self.to_combo.currentText(),
            "amount": round(float(self.amount_input.text().strip()), 2),
            "description": self.desc_input.text().strip()
        }

class SettlementDetailsDialog(QDialog):
    def __init__(self, parent, settlement: dict, project_name: str, is_host: bool, local_peer_id: str):
        super().__init__(parent)
        self.settlement = settlement
        self.project_name = project_name
        self.is_host = is_host
        self.local_peer_id = local_peer_id
        
        self.setWindowTitle("Settlement More Information")
        self.setFixedSize(500, 480)
        
        self.pending_adds = []
        self.pending_removes = []
        self.current_attachments = list(settlement.get("attachments", []))

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        gen_tab = QWidget()
        gen_lay = QVBoxLayout(gen_tab)
        
        from_to_lay = QHBoxLayout()
        from_to_lay.addWidget(QLabel("From:"))
        self.from_label = QLabel(settlement.get("from_person", ""))
        self.from_label.setStyleSheet("font-weight: bold;")
        from_to_lay.addWidget(self.from_label)
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        from_to_lay.addWidget(arrow_label)
        self.to_label = QLabel(settlement.get("to_person", ""))
        self.to_label.setStyleSheet("font-weight: bold;")
        from_to_lay.addWidget(self.to_label)
        from_to_lay.addStretch()
        gen_lay.addLayout(from_to_lay)
        
        gen_lay.addWidget(QLabel("Amount:"))
        self.amount_label = QLabel(f"{settlement.get('amount', 0):.2f}")
        self.amount_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        gen_lay.addWidget(self.amount_label)
        
        if settlement.get("is_manual"):
            manual_badge = QLabel("📋 Manual Settlement")
            manual_badge.setStyleSheet("color: #8E44AD; font-style: italic;")
            gen_lay.addWidget(manual_badge)
        
        if settlement.get("is_completed"):
            completed_badge = QLabel("✅ Completed")
            completed_badge.setStyleSheet("color: #27AE60; font-weight: bold;")
            gen_lay.addWidget(completed_badge)
        
        date_time_lay = QHBoxLayout()
        date_time_lay.addWidget(QLabel("Payment Date:"))
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        if settlement.get("payment_date"):
            self.date_input.setDate(QDate.fromString(settlement["payment_date"], "yyyy-MM-dd"))
        else:
            self.date_input.setDate(QDate.currentDate())
        date_time_lay.addWidget(self.date_input)
        
        date_time_lay.addWidget(QLabel("Payment Time:"))
        self.time_input = QTimeEdit()
        if settlement.get("payment_time"):
            self.time_input.setTime(QTime.fromString(settlement["payment_time"], "HH:mm"))
        else:
            self.time_input.setTime(QTime.currentTime())
        date_time_lay.addWidget(self.time_input)
        gen_lay.addLayout(date_time_lay)
        
        gen_lay.addWidget(QLabel("Notes:"))
        self.notes_input = QTextEdit(settlement.get("detailed_description", ""))
        gen_lay.addWidget(self.notes_input)
        
        self.tabs.addTab(gen_tab, "General Information")
        
        att_tab = QWidget()
        att_lay = QVBoxLayout(att_tab)
        
        self.att_list = QListWidget()
        self.att_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.att_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.att_list.setIconSize(QSize(100, 100))
        self.att_list.setGridSize(QSize(120, 120))
        self.att_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.att_list.setSpacing(10)
        self.att_list.setWordWrap(True)
        self.att_list.itemDoubleClicked.connect(self._open_attachment)
        
        self._refresh_att_list()
        att_lay.addWidget(self.att_list)
        
        att_btn_lay = QHBoxLayout()
        add_att_btn = QPushButton("Add Attachment")
        add_att_btn.setObjectName("secondaryBtn")
        add_att_btn.clicked.connect(self._add_attachment)
        open_att_btn = QPushButton("Open Selected")
        open_att_btn.setObjectName("secondaryBtn")
        open_att_btn.clicked.connect(self._open_attachment)
        rem_att_btn = QPushButton("Remove Selected")
        rem_att_btn.setObjectName("dangerBtn")
        rem_att_btn.clicked.connect(self._remove_attachment)
        
        att_btn_lay.addWidget(add_att_btn)
        att_btn_lay.addWidget(open_att_btn)
        att_btn_lay.addWidget(rem_att_btn)
        att_lay.addLayout(att_btn_lay)
        self.tabs.addTab(att_tab, "Attachments")

        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        btn_layout = QHBoxLayout()
        del_btn = QPushButton("Delete Settlement")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_settlement)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _delete_settlement(self):
        reply = QMessageBox.question(
            self, "Delete Settlement",
            "Are you sure you want to delete this settlement?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.done(3)

    def _refresh_att_list(self):
        self.att_list.clear()
        proj_folder = ATTACHMENTS_DIR / sanitize_filename(self.project_name)
        for att in self.current_attachments:
            item = QListWidgetItem()
            try:
                path = att.get("source_path", str(safe_path_resolve(proj_folder, att["saved_name"])))
            except ValueError:
                continue
            
            if os.path.exists(path) and path.lower().endswith(('.png', '.jpg', '.jpeg')):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
            else:
                item.setText(f"📄\n{att['original_name']}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
            item.setToolTip(att['original_name'])
            item.setData(Qt.ItemDataRole.UserRole, att)
            self.att_list.addItem(item)

    def _add_attachment(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Attachments", "", "Images/PDF (*.jpg *.jpeg *.png *.pdf)")
        for p in paths:
            orig_name = os.path.basename(p)
            unique_id = uuid.uuid4().hex[:8]
            saved_name = f"{unique_id}_{sanitize_filename(orig_name)}"
            att_dict = {
                "original_name": orig_name,
                "saved_name": saved_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "source_path": p,
                "owner": self.local_peer_id 
            }
            self.current_attachments.append(att_dict)
            self.pending_adds.append(att_dict)
        self._refresh_att_list()

    def _remove_attachment(self):
        item = self.att_list.currentItem()
        if not item: return
        att = item.data(Qt.ItemDataRole.UserRole)
        
        if not self.is_host and att.get("owner") != self.local_peer_id:
            QMessageBox.warning(self, "Permission Denied", "You can only delete attachments that you uploaded.")
            return
            
        self.current_attachments.remove(att)
        if att in self.pending_adds: self.pending_adds.remove(att)
        else: self.pending_removes.append(att)
        self._refresh_att_list()

    def _open_attachment(self):
        item = self.att_list.currentItem()
        if not item: return
        att = item.data(Qt.ItemDataRole.UserRole)
        try:
            path = att.get("source_path", str(safe_path_resolve(ATTACHMENTS_DIR / sanitize_filename(self.project_name), att["saved_name"])))
            if os.path.exists(path): 
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            else: 
                QMessageBox.warning(self, "File Not Found", "Attachment not fully synced or unavailable.")
        except ValueError:
            QMessageBox.warning(self, "Security Block", "Invalid or unsafe file path requested.")

    def _save(self):
        self.settlement["payment_date"] = self.date_input.date().toString("yyyy-MM-dd")
        self.settlement["payment_time"] = self.time_input.time().toString("HH:mm")
        self.settlement["detailed_description"] = self.notes_input.toPlainText()
        
        proj_folder = ATTACHMENTS_DIR / sanitize_filename(self.project_name)
        proj_folder.mkdir(parents=True, exist_ok=True)
        
        for add in self.pending_adds:
            try:
                safe_dest = safe_path_resolve(proj_folder, add["saved_name"])
                shutil.copy2(add["source_path"], safe_dest)
            except Exception: pass
            if "source_path" in add: del add["source_path"]
            
        for rem in self.pending_removes:
            try:
                safe_rem = safe_path_resolve(proj_folder, rem["saved_name"])
                os.remove(safe_rem)
            except Exception: pass
            
        self.settlement["attachments"] = self.current_attachments
        self.accept()

class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings_mgr=None):
        super().__init__(parent)
        self.settings_mgr = settings_mgr
        self.setWindowTitle("Settings")
        self.setFixedSize(480, 580)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo = QLabel()
        pixmap = QPixmap(resource_path("assets/BS_logo.png"))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            header_layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)
            
        title = QLabel("Balance Separator")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        version = QLabel(f"Version {APP_VERSION}")
        version.setStyleSheet("color: #888;")
        header_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(version, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(header_layout)
        
        main_layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)
        grid.setColumnStretch(1, 1)

        grid.addWidget(QLabel("Username:"), 0, 0)
        self.user_input = QLineEdit(self.settings_mgr.get("username", ""))
        self.user_input.setPlaceholderText("e.g. John Doe")
        self.user_input.setMinimumHeight(30)
        grid.addWidget(self.user_input, 0, 1)
        
        grid.addWidget(QLabel("List Date:"), 1, 0)
        self.date_combo = QComboBox()
        self.date_combo.addItems(["Show Last Modified", "Show Created Date"])
        self.date_combo.setCurrentIndex(0 if self.settings_mgr.get("project_date_display", "modified") == "modified" else 1)
        grid.addWidget(self.date_combo, 1, 1)

        grid.addWidget(QLabel("Currency:"), 2, 0)
        self.curr_combo = QComboBox()
        self.curr_combo.addItems(list(CURRENCIES.keys()))
        self.curr_combo.setCurrentText(self.settings_mgr.get("currency", "RM"))
        grid.addWidget(self.curr_combo, 2, 1)

        grid.addWidget(QLabel("Theme:"), 3, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        self.theme_combo.setCurrentText(self.settings_mgr.get("theme", "system").capitalize())
        grid.addWidget(self.theme_combo, 3, 1)

        grid.addWidget(QLabel("Accent Color:"), 4, 0)
        self.color_hex = self.settings_mgr.get("accent_color", "#4A90D9")
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.setObjectName("secondaryBtn")
        
        from gui_main import get_contrast_color
        txt_col = get_contrast_color(self.color_hex)
        self.color_btn.setStyleSheet(f"background-color: {self.color_hex}; color: {txt_col}; font-weight: bold;")
        self.color_btn.clicked.connect(self._pick_color)
        grid.addWidget(self.color_btn, 4, 1)
        
        main_layout.addLayout(grid)
        
        self.share_check = QCheckBox("Enable Local Network Sharing")
        self.share_check.setChecked(self.settings_mgr.get("enable_sharing", True))
        main_layout.addWidget(self.share_check)

        main_layout.addStretch()

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        
        self.update_btn = QPushButton("Check for Updates")
        self.update_btn.setObjectName("secondaryBtn")
        self.update_btn.clicked.connect(self._check_for_updates)
        btn_layout.addWidget(self.update_btn)
        
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

        footer = QLabel('🇲🇾 2026 Developed by <a href="https://github.com/arinltte/Balance-Separator" style="color: #4A90D9; text-decoration: none;">arinltte</a> <br>cjshen00@gmail.com</br>')
        footer.setOpenExternalLinks(True)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName("footerLabel")
        main_layout.addWidget(footer)

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self.color_hex), self, "Select Accent Color")
        if color.isValid():
            self.color_hex = color.name()
            from gui_main import get_contrast_color
            txt_col = get_contrast_color(self.color_hex)
            self.color_btn.setStyleSheet(f"background-color: {self.color_hex}; color: {txt_col}; font-weight: bold;")

    def _check_for_updates(self):
        if "Download" in self.update_btn.text():
            webbrowser.open("https://github.com/arinltte/Balance-Separator/releases/latest")
            return

        self.update_btn.setText("Checking...")
        self.update_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            response = requests.get(
                "https://github.com/arinltte/Balance-Separator/releases/latest",
                timeout=8,
                allow_redirects=True
            )
            response.raise_for_status()
            tag = response.url.split('/')[-1]
            
            if tag > f"v{APP_VERSION}":
                self.update_btn.setText(f"Update Available ({tag}) - Click to Download")
                self.update_btn.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold;")
                self.update_btn.setEnabled(True)
            else:
                self.update_btn.setText("Up to Date")
                self.update_btn.setEnabled(False) 
        except Exception: 
            QMessageBox.warning(self, "Update Check Failed", "Could not connect to GitHub to check for updates.")
            self.update_btn.setText("Check for Updates")
            self.update_btn.setEnabled(True)

    def _save_and_close(self):
        self.settings_mgr.set("username", self.user_input.text().strip())
        self.settings_mgr.set("theme", self.theme_combo.currentText().lower())
        self.settings_mgr.set("accent_color", self.color_hex)
        self.settings_mgr.set("currency", self.curr_combo.currentText())
        self.settings_mgr.set("project_date_display", "modified" if self.date_combo.currentIndex() == 0 else "created")
        self.settings_mgr.set("enable_sharing", self.share_check.isChecked())
        from gui_main import generate_stylesheet
        QApplication.instance().setStyleSheet(generate_stylesheet(self.settings_mgr.get("theme"), self.color_hex))
        self.accept()

class ProjectEditDialog(QDialog):
    def __init__(self, parent, project: Project):
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
        if project.start_date: self.start_input.setDate(QDate.fromString(project.start_date, Qt.DateFormat.ISODate))
        else: self.start_input.setDate(QDate.currentDate())
        layout.addWidget(self.start_input)
        layout.addWidget(QLabel("End Date:"))
        self.end_input = QDateEdit()
        self.end_input.setCalendarPopup(True)
        if project.end_date: self.end_input.setDate(QDate.fromString(project.end_date, Qt.DateFormat.ISODate))
        else: self.end_input.setDate(QDate.currentDate())
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
        if QMessageBox.question(self, "Delete Project", f"Are you sure you want to permanently delete '{self.project.name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes: self.done(2)

class TeammateEditDialog(QDialog):
    def __init__(self, parent, teammate: Teammate, project_name: str):
        super().__init__(parent)
        self.teammate = teammate
        self.project_name = project_name
        self.avatar_file = teammate.avatar
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
        if self.avatar_file:
            try:
                path = safe_path_resolve(ATTACHMENTS_DIR / sanitize_filename(self.project_name), self.avatar_file)
                if path.exists():
                    p = QPixmap(str(path))
                    self.pic_label.setPixmap(create_circular_pixmap(p, 80))
                    return
            except ValueError:
                pass
        self.pic_label.setText("No Image")
        self.pic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pic_label.setStyleSheet("border: 1px dashed #AAA; border-radius: 40px;")

    def _choose_picture(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose Profile Picture", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            p = QPixmap(path).scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            fname = f"avatar_{uuid.uuid4().hex[:8]}.jpg"
            save_dir = ATTACHMENTS_DIR / sanitize_filename(self.project_name)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                safe_dest = safe_path_resolve(save_dir, fname)
                p.save(str(safe_dest), "JPEG", 80)
                
                if self.avatar_file:
                    safe_old = safe_path_resolve(save_dir, self.avatar_file)
                    os.remove(safe_old)
            except Exception: pass
                
            self.avatar_file = fname
            self._update_pic_label()

    def _remove_picture(self): 
        if self.avatar_file:
            try: 
                safe_rem = safe_path_resolve(ATTACHMENTS_DIR / sanitize_filename(self.project_name), self.avatar_file)
                os.remove(safe_rem)
            except Exception: pass
        self.avatar_file = ""
        self._update_pic_label()

    def _delete_teammate(self):
        if QMessageBox.question(self, "Delete", f"Are you sure you want to delete '{self.teammate.name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes: self.done(2)
