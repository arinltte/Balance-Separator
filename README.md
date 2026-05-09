# Balance Separator ⚖️💸

Balance Separator is a fast, offline, cross-platform desktop application built with Python and PyQt6. It is designed to effortlessly calculate group expenses, figure out everyone's fair share, and generate precise pairwise settlements so you know exactly **who owes whom**. 

Perfect for road trips, shared house expenses, or collaborative projects!

![Balance Separator Screenshot](assets/BS_img1.png)

## ✨ Features

### 🧮 Flawless Financial Logic
* **Zero Precision Errors:** Background calculations are performed entirely in integers (cents) to prevent floating-point rounding errors. 
* **Pairwise Settlements:** Automatically calculates exact proportional debts between specific individuals (e.g., "Person A owes Person B exactly RM12.36").
* **Payment Tracking:** Tick the checkbox next to a settlement to mark it as paid. This state is persistent and saved automatically.
* **Global Currencies:** Supports formatting for multiple international currencies (`$`, `€`, `£`, `¥`, `RM`, `C$`, `A$`, `CHF`, etc.).

### 🎨 Modern & Customizable UI
* **Dynamic Theme Engine:** Fully supports Light, Dark, and System modes (automatically syncing with your OS appearance).
* **Custom Accent Colors:** Personalize the application by picking your own accent color for buttons and highlights.
* **Fluid Layout:** The interface features resizable splitters. Your layout preferences are saved automatically.
* **Smart Input Navigation:** Typing numbers in the description field jumps to the Amount field. Typing letters in an empty Amount field jumps to Description.

### 💾 Data Portability & Privacy
* **100% Offline:** No cloud, no sign-ups. Your data stays on your machine.
* **PDF & Excel Export:** Generate clean 2-page PDF reports or formatted Excel (`.xlsx`) sheets with a single click.
* **JSON Backups:** Export individual projects as `.json` files to share with friends or backup, and import them right back into the app.

---

## 🚀 Installation & Setup

This application requires a modern Python 3.x environment (Tested on Python 3.10+).

### 1. Clone the repository
```bash
git clone https://github.com/arinltte/Balance-Separator.git
cd Balance-Separator
```

### 2. Create a Virtual Environment (Recommended)
**For macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```
**For Windows:**
```cmd
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
Install the required libraries using `pip`:
```bash
pip install PyQt6 pandas openpyxl
```
or
```bash
pip install -r requirements.txt
```
*Note: `PyQt6` is used for the Graphical User Interface. `pandas` and `openpyxl` are required for exporting data to Excel.*

### 4. Run the Application
```bash
python balance_gui.py
```

---

## 📂 File Structure & Data Storage

The application code is split into two main files:
* **`balance_gui.py`**: Contains all UI rendering, stylesheets, and window logic.
* **`balance_logic.py`**: The backend logic. Handles data models, file I/O, and the core mathematical algorithms.

**Where is my data saved?**
To ensure cross-platform compatibility without requiring admin privileges, your data (`projects.json` and `config.json`) is safely stored in your user directory:
* **macOS/Linux:** `~/.balance_separator/`
* **Windows:** `C:\Users\YourName\Documents\BalanceSeparator\`

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](../../issues). 

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

<p align="center">
  <i>2026 Developed by Chen Jin Shen, cjshen00@gmail.com</i>
</p>
