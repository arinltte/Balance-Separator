import json
import os
import platform
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Optional


# ─── Cross-Platform Data Directory ──────────────────────────────────────────────

def get_app_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path.home() / "Documents" / "BalanceSeparator"
    else:
        # macOS and Linux hidden directory
        return Path.home() / ".balance_separator"

APP_DIR = get_app_dir()
APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APP_DIR / "config.json"
PROJECTS_FILE = APP_DIR / "projects.json"


# ─── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class Expense:
    description: str
    amount: float


@dataclass
class Teammate:
    name: str
    description: str = ""
    avatar_data: str = ""  # Base64 encoded image
    expenses: list = field(default_factory=list)


@dataclass
class Project:
    name: str
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    teammates: list = field(default_factory=list)


# ─── Settings Manager ──────────────────────────────────────────────────────────

class SettingsManager:
    DEFAULTS = {
        "theme": "system",
        "accent_color": "#4A90D9",
        "currency": "RM",
        "project_date_display": "modified",  # 'modified' or 'created'
        "left_panel_sizes": [250, 850],
        "content_splitter_sizes": [400, 400],
        "right_col_sizes": [300, 300],
        "settlements": {}  # Tracks checkbox states per project
    }

    def __init__(self):
        self.settings: dict = self._load()

    def _load(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    return {**self.DEFAULTS, **saved}
            except (json.JSONDecodeError, IOError):
                pass
        return deepcopy(self.DEFAULTS)

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except IOError:
            pass

    def get(self, key: str, default=None):
        return self.settings.get(key, default)

    def set(self, key: str, value):
        self.settings[key] = value
        self.save()

    def toggle_settlement(self, project_name: str, key: str, state: bool):
        s_map = self.get("settlements", {})
        if project_name not in s_map:
            s_map[project_name] = []
            
        if state and key not in s_map[project_name]:
            s_map[project_name].append(key)
        elif not state and key in s_map[project_name]:
            s_map[project_name].remove(key)
            
        self.set("settlements", s_map)


# ─── Project Manager ───────────────────────────────────────────────────────────

class ProjectManager:
    def __init__(self):
        self.projects: list = [] 
        self._load()

    @staticmethod
    def _from_json(data: list) -> list:
        projects = []
        for p in data:
            proj = Project(
                name=p["name"],
                description=p.get("description", ""),
                start_date=p.get("start_date", ""),
                end_date=p.get("end_date", ""),
                created_at=p.get("created_at", datetime.now().isoformat()),
                updated_at=p.get("updated_at", datetime.now().isoformat())
            )
            for t in p.get("teammates", []):
                mate = Teammate(
                    name=t["name"], 
                    description=t.get("description", ""), 
                    avatar_data=t.get("avatar_data", "")
                )
                for e in t.get("expenses", []):
                    mate.expenses.append(Expense(description=e["description"], amount=e["amount"]))
                proj.teammates.append(mate)
            projects.append(proj)
        return projects

    @staticmethod
    def _to_json(projects: list) -> list:
        return [
            {
                "name": p.name,
                "description": p.description,
                "start_date": p.start_date,
                "end_date": p.end_date,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "teammates": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "avatar_data": t.avatar_data,
                        "expenses": [{"description": e.description, "amount": e.amount} for e in t.expenses],
                    }
                    for t in p.teammates
                ],
            }
            for p in projects
        ]

    def _load(self):
        if os.path.exists(PROJECTS_FILE):
            try:
                with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                    self.projects = self._from_json(json.load(f))
            except (json.JSONDecodeError, IOError):
                self.projects = []

    def save(self):
        try:
            with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._to_json(self.projects), f, indent=4)
        except IOError:
            pass

    def _touch(self, idx: int):
        """Updates the modified timestamp of the project and saves."""
        if 0 <= idx < len(self.projects):
            self.projects[idx].updated_at = datetime.now().isoformat()
            self.save()

    def get_project(self, idx: int) -> Optional[Project]:
        if 0 <= idx < len(self.projects):
            return self.projects[idx]
        return None

    def add_project(self, name: str) -> Project:
        project = Project(name=name)
        self.projects.append(project)
        self.save()
        return project

    def update_project(self, idx: int, name: str, desc: str, start_date: str, end_date: str) -> bool:
        if 0 <= idx < len(self.projects):
            self.projects[idx].name = name
            self.projects[idx].description = desc
            self.projects[idx].start_date = start_date
            self.projects[idx].end_date = end_date
            self._touch(idx)
            return True
        return False

    def remove_project(self, idx: int) -> bool:
        if 0 <= idx < len(self.projects):
            del self.projects[idx]
            self.save()
            return True
        return False

    def add_teammate(self, project_idx: int, name: str) -> Optional[Teammate]:
        project = self.get_project(project_idx)
        if project is None: return None
        for t in project.teammates:
            if t.name.lower() == name.lower(): return None
        mate = Teammate(name=name)
        project.teammates.append(mate)
        self._touch(project_idx)
        return mate

    def update_teammate(self, project_idx: int, teammate_idx: int, name: str, desc: str, avatar_data: str):
        project = self.get_project(project_idx)
        if project and 0 <= teammate_idx < len(project.teammates):
            t = project.teammates[teammate_idx]
            t.name = name
            t.description = desc
            t.avatar_data = avatar_data
            self._touch(project_idx)
            return True
        return False

    def remove_teammate(self, project_idx: int, teammate_idx: int) -> bool:
        project = self.get_project(project_idx)
        if project and 0 <= teammate_idx < len(project.teammates):
            del project.teammates[teammate_idx]
            self._touch(project_idx)
            return True
        return False

    def add_expense(self, project_idx: int, teammate_idx: int, description: str, amount: float) -> Optional[Expense]:
        project = self.get_project(project_idx)
        if project and 0 <= teammate_idx < len(project.teammates):
            expense = Expense(description=description, amount=round(amount, 2))
            project.teammates[teammate_idx].expenses.append(expense)
            self._touch(project_idx)
            return expense
        return None

    def remove_expense(self, project_idx: int, teammate_idx: int, expense_idx: int) -> bool:
        project = self.get_project(project_idx)
        if project and 0 <= teammate_idx < len(project.teammates):
            mate = project.teammates[teammate_idx]
            if 0 <= expense_idx < len(mate.expenses):
                del mate.expenses[expense_idx]
                self._touch(project_idx)
                return True
        return False

    def update_expense_description(self, project_idx: int, teammate_idx: int, expense_idx: int, new_desc: str):
        project = self.get_project(project_idx)
        if project and 0 <= teammate_idx < len(project.teammates):
            mate = project.teammates[teammate_idx]
            if 0 <= expense_idx < len(mate.expenses):
                mate.expenses[expense_idx].description = new_desc.strip() or "Undefined"
                self._touch(project_idx)
                return True
        return False


# ─── Balance Calculator ────────────────────────────────────────────────────────

class BalanceCalculator:
    @staticmethod
    def calculate(project: Optional[Project]):
        if not project or not project.teammates:
            return {}, [], 0.0

        n = len(project.teammates)
        paid_map_cents = {}
        total_cents = 0
        
        for t in project.teammates:
            cents = sum(int(round(e.amount * 100)) for e in t.expenses)
            paid_map_cents[t.name] = cents
            total_cents += cents

        base_share_cents = total_cents // n
        remainder_cents = total_cents % n

        summary = {}

        for i, t in enumerate(project.teammates):
            name = t.name
            paid_cents = paid_map_cents[name]
            assigned_share = base_share_cents + (1 if i < remainder_cents else 0)
            net_cents = paid_cents - assigned_share

            summary[name] = {
                "paid": paid_cents / 100.0,
                "share": assigned_share / 100.0,
                "net": net_cents / 100.0,
            }

        settlements = []
        names = list(paid_map_cents.keys())
        
        for i in range(n):
            for j in range(i + 1, n):
                name_a = names[i]
                name_b = names[j]
                
                paid_a = paid_map_cents[name_a]
                paid_b = paid_map_cents[name_b]
                
                diff = paid_a - paid_b
                transfer_cents = round(diff / n)
                
                if transfer_cents > 0:
                    settlements.append({"from": name_b, "to": name_a, "amount": transfer_cents / 100.0})
                elif transfer_cents < 0:
                    settlements.append({"from": name_a, "to": name_b, "amount": abs(transfer_cents) / 100.0})

        # Sort settlements specifically grouped by "From" (who pays whom)
        settlements.sort(key=lambda x: (x["from"], x["to"]))
        
        total_float = total_cents / 100.0
        return summary, settlements, total_float
