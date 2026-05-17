import uuid
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class Expense:
    description: str
    amount: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M"))
    detailed_description: str = ""
    attachments: list = field(default_factory=list)

@dataclass
class Teammate:
    name: str
    description: str = ""
    avatar: str = ""  
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

@dataclass
class SettlementEntry:
    from_person: str
    to_person: str
    amount: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_completed: bool = False
    is_manual: bool = False
    payment_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    payment_time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M"))
    detailed_description: str = ""
    attachments: list = field(default_factory=list)
