# thonny-tunisiaschools

A Thonny plug-in which offers Tunisian computer science secondary teachers / students some help creating Python & PyQt Applications:

- Loads a QT UI file and:
  - Adds needed code to load that file to the current document
  - Creates empty functions bound to button clicks
  
  ![image](https://github.com/selmen2004/thonny-tunisiaschools/assets/3520243/4e4037a8-3157-4f09-99db-1b4543bb6233)

  - Adds a view that displays the UI inside Thonny (currently supporting Labels, Text inputs and buttons only)

  ![image](https://github.com/selmen2004/thonny-tunisiaschools/assets/3520243/a3bdb491-6f31-4b92-a5eb-d2842eec95f1)

- Adds a new menu (PyQt5) with commands to insert calls to common functions (text, setText, clear, show) for Labels and LineEdits

  ![image](https://github.com/selmen2004/thonny-tunisiaschools/assets/3520243/3bbd2794-c3f1-4425-92d2-6b5b1933f897)

- Changes the default save location for final exams (baccalauréat)
- Disables reopening last open files (to reduce risks of students overwriting each other's work)

---

## Installation

### Windows
Use **Tools → Manage plugins** inside Thonny, search for `thonny-tunisiaschools` and click Install.

### macOS & Linux
1. Download and extract this repository
2. Open a terminal inside the extracted folder
3. Run:
```bash
python3 install_macos.py
```
4. Restart Thonny

To uninstall:
```bash
python3 install_macos.py uninstall
```

> **No sudo required.** The script installs the plugin into your user folder, not a system directory.

### Prerequisite — Qt Designer (macOS)
To use the "Open in Designer" button, install Qt Designer:
```bash
pip3 install pyqt5-tools
```

---

## Supported platforms
- ✅ Windows
- ✅ macOS
- ✅ Linux
