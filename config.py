import sys
import os
import platform
import re
from pathlib import Path

APP_VERSION = "0.4.0"
FONT_STACK = "'Helvetica Neue', 'Segoe UI', Arial, sans-serif"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_app_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path.home() / "Documents" / "BalanceSeparator"
    else:
        return Path.home() / ".balance_separator"

APP_DIR = get_app_dir()
APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APP_DIR / "config.json"
PROJECTS_FILE = APP_DIR / "projects.json"
ATTACHMENTS_DIR = APP_DIR / "attachments"
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

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

def sanitize_filename(name: str) -> str:
    # Safely neutralize any path traversals and remove illegal characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name).strip()
    return sanitized.replace("..", "_")

def safe_path_resolve(base_dir: Path, filename: str) -> Path:
    """ Resolves a file securely, verifying it does not escape the targeted base directory. """
    safe_name = sanitize_filename(filename)
    if not safe_name:
        raise ValueError("Invalid filename.")
        
    target = (base_dir / safe_name).resolve()
    
    # Strictly ensure the path is confined inside base_dir to completely block traversal
    if not str(target).startswith(str(base_dir.resolve())):
        raise ValueError(f"CRITICAL: Path traversal attempt detected and blocked: {filename}")
        
    return target
