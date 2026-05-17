import json
import os
import uuid
import base64
from datetime import datetime
from copy import deepcopy
from typing import Optional

from config import CONFIG_FILE, PROJECTS_FILE, ATTACHMENTS_DIR, sanitize_filename
from logic_models import Project, Teammate, Expense

class SettingsManager:
    DEFAULTS = {
        "theme": "system",
        "accent_color": "#4A90D9",
        "currency": "RM",
        "project_date_display": "modified",  
        "enable_sharing": True,
        "username": "",  
        "left_panel_sizes": [250, 850],
        "content_splitter_sizes": [400, 400],
        "right_col_sizes": [300, 300],
        "shared_panel_sizes": [300, 300],
        "settlements": {},
        "settlement_entries": {}
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
        except IOError: pass

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

    def get_settlements(self, project_name: str):
        return self.get("settlements", {}).get(project_name, [])

    # --- Settlement Entry Methods (new) ---

    def get_settlement_entries(self, project_name: str) -> list:
        s_map = self.get("settlement_entries", {})
        return s_map.get(project_name, [])

    def set_settlement_entries(self, project_name: str, entries: list):
        s_map = self.get("settlement_entries", {})
        s_map[project_name] = entries
        self.set("settlement_entries", s_map)

    def add_settlement_entry(self, project_name: str, entry: dict):
        entries = self.get_settlement_entries(project_name)
        entries.append(entry)
        self.set_settlement_entries(project_name, entries)

    def update_settlement_entry(self, project_name: str, entry_id: str, updates: dict):
        entries = self.get_settlement_entries(project_name)
        for entry in entries:
            if entry.get("id") == entry_id:
                entry.update(updates)
                break
        self.set_settlement_entries(project_name, entries)

    def remove_settlement_entry(self, project_name: str, entry_id: str):
        entries = self.get_settlement_entries(project_name)
        entries = [e for e in entries if e.get("id") != entry_id]
        self.set_settlement_entries(project_name, entries)

    def migrate_old_settlements(self, project_name: str, project):
        """Migrate old settlement format (list of completed keys) to new settlement entry format."""
        old_keys = self.get_settlements(project_name)
        if not old_keys:
            return

        existing = self.get_settlement_entries(project_name)
        if existing:
            return  # Already migrated or has new-format data

        _, auto_settlements, _ = BalanceCalculator.calculate(project)
        entries = []

        for key in old_keys:
            parts = key.split("→") if "→" in key else key.split("->")
            if len(parts) == 2:
                from_person = parts[0].strip()
                to_person = parts[1].strip()
                amount = 0
                for s in auto_settlements:
                    if s["from"] == from_person and s["to"] == to_person:
                        amount = s["amount"]
                        break
                entries.append({
                    "from_person": from_person,
                    "to_person": to_person,
                    "amount": amount,
                    "id": str(uuid.uuid4()),
                    "is_completed": True,
                    "is_manual": False,
                    "payment_date": "",
                    "payment_time": "",
                    "detailed_description": "",
                    "attachments": []
                })

        if entries:
            self.set_settlement_entries(project_name, entries)

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
                # Backwards compatibility & Auto-Migration from base64 to file
                avatar_val = t.get("avatar", t.get("avatar_data", ""))
                if len(avatar_val) > 200: # It's a raw Base64 string from older versions
                    proj_dir = ATTACHMENTS_DIR / sanitize_filename(p["name"])
                    proj_dir.mkdir(parents=True, exist_ok=True)
                    fname = f"avatar_{uuid.uuid4().hex[:8]}.jpg"
                    try:
                        with open(proj_dir / fname, "wb") as f:
                            f.write(base64.b64decode(avatar_val))
                        avatar_val = fname
                    except Exception:
                        avatar_val = ""

                mate = Teammate(
                    name=t["name"], 
                    description=t.get("description", ""), 
                    avatar=avatar_val
                )
                for e in t.get("expenses", []):
                    mate.expenses.append(Expense(
                        description=e["description"], 
                        amount=e["amount"],
                        id=e.get("id", str(uuid.uuid4())),
                        date=e.get("date", datetime.now().strftime("%Y-%m-%d")),
                        time=e.get("time", datetime.now().strftime("%H:%M")),
                        detailed_description=e.get("detailed_description", ""),
                        attachments=e.get("attachments", [])
                    ))
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
                        "avatar": t.avatar,
                        "expenses": [
                            {
                                "description": e.description, 
                                "amount": e.amount,
                                "id": e.id,
                                "date": e.date,
                                "time": e.time,
                                "detailed_description": e.detailed_description,
                                "attachments": [{k: v for k, v in att.items() if k != "file_data"} for att in e.attachments]
                            } for e in t.expenses
                        ],
                    } for t in p.teammates
                ],
            } for p in projects
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
        except IOError: pass

    def _touch(self, idx: int):
        if 0 <= idx < len(self.projects):
            self.projects[idx].updated_at = datetime.now().isoformat()
            self.save()

    def update_project(self, idx: int, name: str, description: str, start: str, end: str):
        if 0 <= idx < len(self.projects):
            self.projects[idx].name = name
            self.projects[idx].description = description
            self.projects[idx].start_date = start
            self.projects[idx].end_date = end
            self._touch(idx)

    def get_project(self, idx: int) -> Optional[Project]:
        if 0 <= idx < len(self.projects): return self.projects[idx]
        return None

    def add_project(self, name: str) -> Project:
        project = Project(name=name)
        self.projects.append(project)
        self.save()
        return project

    def remove_project(self, idx: int) -> bool:
        if 0 <= idx < len(self.projects):
            del self.projects[idx]
            self.save()
            return True
        return False

class BalanceCalculator:
    @staticmethod
    def calculate(project: Optional[Project], settlement_entries: list = None):
        if not project or not project.teammates: return {}, [], 0.0

        settlement_entries = settlement_entries or []

        n = len(project.teammates)
        paid_map_cents = {}
        total_cents = 0
        for t in project.teammates:
            cents = sum(int(round(e.amount * 100)) for e in t.expenses)
            paid_map_cents[t.name] = cents
            total_cents += cents

        base_share_cents = total_cents // n
        remainder_cents = total_cents % n

        net_cents_map = {}
        summary = {}
        for i, t in enumerate(project.teammates):
            name = t.name
            paid_cents = paid_map_cents[name]
            assigned_share = base_share_cents + (1 if i < remainder_cents else 0)
            net_cents_map[name] = paid_cents - assigned_share
            
            summary[name] = {
                "paid": paid_cents / 100.0, 
                "share": assigned_share / 100.0, 
                "net": 0.0
            }

        # Apply completed settlements to net balances
        for entry in (settlement_entries or []):
            if entry.get("is_completed"):
                f_p = entry.get("from_person")
                t_p = entry.get("to_person")
                amt_cents = int(round(entry.get("amount", 0) * 100))
                
                if f_p in net_cents_map: net_cents_map[f_p] += amt_cents
                if t_p in net_cents_map: net_cents_map[t_p] -= amt_cents

        # Update summary with adjusted net balances
        for name in summary:
            summary[name]["net"] = net_cents_map[name] / 100.0

        # Generate minimal remaining auto-settlements (Greedy Algorithm)
        settlements = []
        debtors = []
        creditors = []
        
        for name, net in net_cents_map.items():
            if net < 0: debtors.append({"name": name, "amount": -net})
            elif net > 0: creditors.append({"name": name, "amount": net})
            
        debtors.sort(key=lambda x: x["name"])
        creditors.sort(key=lambda x: x["name"])
        
        i = 0
        j = 0
        while i < len(debtors) and j < len(creditors):
            debtor = debtors[i]
            creditor = creditors[j]
            
            transfer = min(debtor["amount"], creditor["amount"])
            if transfer > 0:
                settlements.append({
                    "from": debtor["name"],
                    "to": creditor["name"],
                    "amount": transfer / 100.0
                })
            
            debtor["amount"] -= transfer
            creditor["amount"] -= transfer
            
            if debtor["amount"] == 0: i += 1
            if creditor["amount"] == 0: j += 1

        settlements.sort(key=lambda x: (x["from"], x["to"]))
        return summary, settlements, total_cents / 100.0

    @staticmethod
    def compute_display_settlements(project: Optional[Project], settlement_entries: list) -> list:
        """
        Compute the full list of settlements to display, supporting incremental logic.
        
        - All stored entries (completed and pending) are included as-is.
        - For each auto-calculated pair, a remaining-amount entry is added only if
          the total stored amount for that pair is less than the auto-calculated amount.
        - This ensures completed settlements stay as historical records, and new
          expenses after completion automatically generate new pending lines for
          the remaining balance only.
        """
        if not project or not project.teammates:
            return [dict(e) for e in settlement_entries if e.get("is_manual")]

        _, auto_settlements, _ = BalanceCalculator.calculate(project)

        # Track total stored amount and completed amount per (from, to) pair
        stored_by_pair = {}
        completed_by_pair = {}
        display_list = []

        for entry in settlement_entries:
            pair_key = (entry.get("from_person", ""), entry.get("to_person", ""))
            stored_by_pair[pair_key] = stored_by_pair.get(pair_key, 0) + entry.get("amount", 0)
            if entry.get("is_completed"):
                completed_by_pair[pair_key] = completed_by_pair.get(pair_key, 0) + entry.get("amount", 0)
            display_list.append(dict(entry))

        # For each auto-calculated settlement, compute remaining after stored entries
        for s in auto_settlements:
            pair_key = (s["from"], s["to"])
            total_stored = stored_by_pair.get(pair_key, 0)
            remaining = round(s["amount"] - total_stored, 2)

            if remaining > 0.005:
                display_list.append({
                    "from_person": s["from"],
                    "to_person": s["to"],
                    "amount": remaining,
                    "id": "",
                    "is_completed": False,
                    "is_manual": False,
                    "payment_date": "",
                    "payment_time": "",
                    "detailed_description": "",
                    "attachments": []
                })

        return display_list
