import os
import sys
import subprocess
from datetime import date
from thonny import get_workbench
from thonny.languages import tr
from thonny.ui_utils import select_sequence, askopenfilename
from .UIViewer import UiViewerPlugin

from xml.dom import minidom

global qt_ui_file
qt_ui_file = ""


def usefull_commands(w):
    def add_cmd(w, id, label, fct):
        get_workbench()._publish_command(
            "pyqt_text_" + w.attributes['name'].value + id,
            "PyQt5",
            label + w.attributes['name'].value,
            lambda: get_workbench().get_editor_notebook().get_current_editor().get_code_view().text.insert(
                'insert', "windows." + w.attributes['name'].value + fct)
        )
    add_cmd(w, "text",    "Contenu de ",            ".text()")
    add_cmd(w, "settext", "Changer le contenu de ", ".setText()")
    add_cmd(w, "clear",   "Effacer le contenu de ", ".clear()")
    add_cmd(w, "show",    "Afficher ",              ".show()")


def add_pyqt_code():
    btnstxt = ""
    mytxt = ""
    path = askopenfilename(
        filetypes=[("Fichiers UI", ".ui"), (tr("Tous les fichiers"), ".*")],
        parent=get_workbench()
    )
    if path:
        global qt_ui_file
        qt_ui_file = path
        get_workbench().get_menu("PyQt5").delete(1, "end")
        get_workbench().get_view("UiViewerPlugin").load_new_ui_file(path)
        get_workbench().show_view("UiViewerPlugin", True)
        file = minidom.parse(path)
        widgets = file.getElementsByTagName('widget')
        for w in widgets:
            if w.attributes['class'].value == "QPushButton":
                btnstxt = (btnstxt + "windows." + w.attributes['name'].value
                           + ".clicked.connect ( " + w.attributes['name'].value + "_click )\n")
                mytxt = mytxt + "def " + w.attributes['name'].value + "_click():\n    pass\n"
            elif w.attributes['class'].value in ["QLineEdit", "QLabel"]:
                usefull_commands(w)

        get_workbench().get_editor_notebook().get_current_editor().get_code_view().text.insert(
            '0.0',
            'from PyQt5.uic import loadUi\n'
            'from PyQt5.QtWidgets import QApplication\n'
            '\n' + mytxt + '\n'
            'app = QApplication([])\n'
            'windows = loadUi ("' + path + '")\n'
            'windows.show()\n'
            + btnstxt + '\n'
            'app.exec_()'
        )


def _find_designer():
    """Return the path/command for Qt Designer on the current platform, or None."""
    if sys.platform == "darwin":
        candidates = [
            # pyqt5-tools installs a 'designer' shim next to the Python executable
            os.path.join(os.path.dirname(sys.executable), "designer"),
            # Homebrew Qt5
            "/usr/local/opt/qt5/bin/designer",
            "/opt/homebrew/opt/qt5/bin/designer",
            # Homebrew Qt6
            "/usr/local/opt/qt/bin/designer",
            "/opt/homebrew/opt/qt/bin/designer",
            # Standalone app bundle (fman.io / official Qt)
            "/Applications/Designer.app/Contents/MacOS/Designer",
            # Anything on PATH
            "designer",
        ]
    elif sys.platform == "win32":
        candidates = [
            "pyqt5_qt5_designer.exe",
            r"C:\Program Files (x86)\Qt Designer\designer.exe",
            r"C:\Program Files\Qt Designer\designer.exe",
            "designer.exe",
        ]
    else:  # Linux / other
        candidates = [
            os.path.join(os.path.dirname(sys.executable), "designer"),
            "designer",
            "designer-qt5",
            "qtdesigner",
        ]

    for candidate in candidates:
        if os.path.isabs(candidate):
            if os.path.exists(candidate):
                return candidate
        else:
            # Short name: return it and let Popen resolve via PATH
            return candidate

    return None


def open_in_designer():
    """Open the current .ui file (or just Qt Designer) on any platform."""
    global qt_ui_file

    designer = _find_designer()
    if designer is None:
        print("Error: Qt Designer not found. "
              "Install it with:  pip install pyqt5-tools")
        return False

    cmd = [designer]
    if qt_ui_file:
        cmd.append(qt_ui_file)

    try:
        print("Running:", " ".join(f'"{c}"' for c in cmd), "...")
        subprocess.Popen(cmd)
        return True
    except FileNotFoundError:
        print(f"Error: Designer not found at '{designer}'.\n"
              "Tip: pip install pyqt5-tools")
    except Exception as e:
        print(f"Error launching Designer: {e}")
    return False


def _default_project_dir():
    """Return a platform-appropriate default working directory."""
    year = max(date.today().year, 2024)
    folder = "bac" + str(year)

    if sys.platform == "win32":
        return os.path.join("C:\\", folder)
    elif sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Documents", folder)
    else:
        return os.path.join(os.path.expanduser("~"), folder)


def load_plugin():
    get_workbench().add_view(UiViewerPlugin, tr("QT UI Viewer"), "s")

    image_path          = os.path.join(os.path.dirname(__file__), "res", "qt_16.png")
    designer_image_path = os.path.join(os.path.dirname(__file__), "res", "designer_16.png")

    get_workbench().add_command(
        "selmen_command",
        "PyQt5",
        tr("Ajouter code PyQt5"),
        add_pyqt_code,
        default_sequence=select_sequence("<Control-Shift-B>", "<Command-Shift-B>"),
        include_in_toolbar=True,
        caption="PyQt",
        image=image_path
    )
    get_workbench().add_command(
        "pyqt5_open_in_designer",
        "PyQt5",
        tr("Ouvrir dans Designer"),
        open_in_designer,
        include_in_toolbar=True,
        caption="PyQt",
        image=designer_image_path
    )

    # Cross-platform default working directory
    cwd = _default_project_dir()
    if not os.path.exists(cwd):
        os.makedirs(cwd)
    get_workbench().set_local_cwd(cwd)

    # Don't reopen last files on startup
    get_workbench().set_option("file.current_file", "")
    get_workbench().set_option("file.open_files", "")
