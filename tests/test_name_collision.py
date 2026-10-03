"""Collision de noms : un widget ajoute peut porter le nom d'un widget du fichier."""
import os
import sys
import types
from xml.etree import ElementTree as ET

import chemins

BUNDLE = chemins.BUNDLE
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, chemins.PAQUET)
for _n, _a in (("thonny", ("get_workbench",)), ("thonny.languages", ("tr",))):
    m = types.ModuleType(_n)
    for _x in _a:
        setattr(m, _x, lambda *x, **k: x[0] if x else None)
    sys.modules[_n] = m
sys.modules["thonny"].languages = sys.modules["thonny.languages"]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from UIViewer import UiViewerPlugin  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "designer_layout.ui")
OUT = os.path.join(HERE, "collide.ui")

v = object.__new__(UiViewerPlugin)
v.widgets_data, v.selected_idx = [], None
v.widget_counter, v.ui_file = 0, SRC
v.root_widget_name, v.root_widget_class = "Dialog", "QDialog"
v.root_geometry, v.root_title = (0, 0, 400, 300), "D"
v._source_ui, v._source_uids, v._src_root = None, [], {}
v._refresh = lambda: None            # pas de Tk dans ce test
v._select = lambda i: None
v._show_no_selection = lambda: None

data, info = v._parse_ui(SRC)
v.widgets_data = data
v.root_geometry = info["geometry"]
v.root_title = info["title"]
loaded = [p["name"] for _c, p in data]
print("noms du fichier :", loaded)

# le concepteur cree le nomme pushButton1 : le compteur repart de zero
v._add_widget("QPushButton")
added = v.widgets_data[-1][1]["name"]
print("widget ajoute  :", added)
v._write_ui_file(OUT)

txt = open(OUT, encoding="utf-8").read()
names = [w.get("name") for w in ET.fromstring(txt).iter("widget")]
dupes = sorted({n for n in names if names.count(n) > 1})
print("noms en double dans le fichier :", dupes or "aucun")

from PyQt5 import QtWidgets, uic  # noqa: E402
app = QtWidgets.QApplication([])
try:
    w = uic.loadUi(OUT)
    target = getattr(w, added)
    print("loadUi ok, %s -> %s" % (added, type(target).__name__))
    is_button = isinstance(target, QtWidgets.QPushButton)
    print("le nom pointe vers le bouton ajoute :", is_button)
    print("le code genere viserait donc :", "LE MAUVAIS widget" if not is_button
          else "le bon widget")
except Exception as e:
    print("loadUi a echoue :", repr(e))
