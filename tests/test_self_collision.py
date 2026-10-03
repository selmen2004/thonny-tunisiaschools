"""Cas reel : un eleve rouvre SON propre fichier .ui puis ajoute un widget."""
import os
import sys
import types
from xml.etree import ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, r"C:\Users\Selmen\Desktop\projects\tunisiaschools")
for _n, _a in (("thonny", ("get_workbench",)), ("thonny.languages", ("tr",))):
    m = types.ModuleType(_n)
    for _x in _a:
        setattr(m, _x, lambda *x, **k: x[0] if x else None)
    sys.modules[_n] = m
sys.modules["thonny"].languages = sys.modules["thonny.languages"]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from UIViewer import UiViewerPlugin  # noqa: E402
from PyQt5 import QtWidgets, uic  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
F1 = os.path.join(HERE, "eleve_passe1.ui")
F2 = os.path.join(HERE, "eleve_passe2.ui")
app = QtWidgets.QApplication([])


def blank():
    v = object.__new__(UiViewerPlugin)
    v.widgets_data, v.selected_idx = [], None
    v.widget_counter, v.ui_file = 0, None
    v.root_widget_name, v.root_widget_class = "Form", "QDialog"
    v.root_geometry, v.root_title = (0, 0, 400, 300), "Fenetre"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    v._refresh = lambda: None
    v._select = lambda i: None
    v._show_no_selection = lambda: None
    return v


print("=== passe 1 : un eleve cree deux boutons et enregistre ===")
v = blank()
v._add_widget("QPushButton")
v._add_widget("QPushButton")
v._add_widget("QLineEdit")
print("noms :", [p["name"] for _c, p in v.widgets_data])
v._write_ui_file(F1)

print("=== passe 2 : il rouvre le fichier et ajoute un bouton ===")
w = blank()
data, info = w._parse_ui(F1)
w.widgets_data = data
w.root_geometry = info["geometry"]
w.root_title = info["title"]
print("noms rechus :", [p["name"] for _c, p in w.widgets_data])
w._add_widget("QPushButton")
print("nouveau nom :", w.widgets_data[-1][1]["name"])
w._write_ui_file(F2)

names = [x.get("name") for x in ET.parse(F2).getroot().iter("widget")]
dupes = sorted({n for n in names if names.count(n) > 1})
print("noms en double dans le fichier enregistre :", dupes or "aucun")

try:
    ui = uic.loadUi(F2)
    hits = [n for n in dupes if hasattr(ui, n)]
    print("loadUi : %d nom(s) en double charges %s" % (len(hits), hits))
except Exception as e:
    print("loadUi a refuse le fichier :", repr(e))

# un nom en double se lit bien comme un widget de trop : on ne le teste
# que quand le doublon existe, sinon cette lecture masquerait le resultat
for n in dupes:
    print("le nom %s designe maintenant un %s" % (n, type(getattr(ui, n)).__name__))
print("conclusion :", "aucun doublon, le fichier est utilisable"
      if not dupes else "%s : doublon present" % dupes)
