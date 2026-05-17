import sys
import os
import traceback
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox

# Suppress macOS system warnings
os.environ['QT_MAC_WANTS_LAYER'] = '1'

from gui_main import MainWindow

def get_log_path():
    if sys.platform == "darwin":
        log_dir = os.path.expanduser("~/Library/Logs/BalanceSeparator")
    elif sys.platform == "win32":
        log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "BalanceSeparator", "logs")
    else:
        log_dir = os.path.expanduser("~/.balance_separator")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "crash.log")

def exception_hook(exc_type, exc_value, exc_traceback):
    error_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        with open(get_log_path(), "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Crash at {datetime.now().isoformat()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write(f"Executable: {sys.executable}\n")
            f.write(f"{'='*60}\n")
            f.write(error_text)
    except Exception:
        pass
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    try:
        app = QApplication.instance()
        if app:
            QMessageBox.critical(
                None, "Unexpected Error",
                f"The application encountered an error:\n\n{str(exc_value)}\n\n"
                f"Crash log saved to:\n{get_log_path()}"
            )
    except Exception:
        pass

def main():
    sys.excepthook = exception_hook
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
