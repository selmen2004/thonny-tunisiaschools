"""Fichires malformés : le concepteur ne doit jamais planter ni geler."""
import os
import sys
import time
import types
from xml.etree import ElementTree as ET

import chemins

BUNDLE = chemins.BUNDLE
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, chemins.PAQUET)
for _n, _a in (("thonny", ("get_workbench",)), ("thonny.languages", ("tr",))):
    _m = types.ModuleType(_n)
    for _x in _a:
        setattr(_m, _x, lambda *x, **k: x[0] if x else None)
    sys.modules[_n] = _m
sys.modules["thonny"].languages = sys.modules["thonny.languages"]
from UIViewer import UiViewerPlugin  # noqa: E402
import UIViewer                      # noqa: E402

# Le lecteur refuse un <ui> sans widget racine en le disant : sans ce bouchon,
# la messagebox de Tk reclamerait une fenetre et bloquerait la suite.
dialogues = []
UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: dialogues.append(("error",) + a),
    showinfo=lambda *a, **k: dialogues.append(("info",) + a),
    askyesno=lambda *a, **k: True)
UIViewer.get_workbench = lambda: None

HERE = os.path.dirname(os.path.abspath(__file__))
fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


CASES = {
    "grille_geante": '''<ui version="4.0"><class>Form</class>
 <widget class="QDialog" name="D"><property name="geometry"><rect><x>0</x><y>0</y>
   <width>300</width><height>200</height></rect></property>
  <layout class="QGridLayout" name="g">
   <item row="99999" column="0" rowspan="50" colspan="50">
    <widget class="QLabel" name="a"><property name="text"><string>A</string></property></widget>
   </item></layout></widget></ui>''',
    "layout_vide": '''<ui version="4.0"><class>Form</class>
 <widget class="QDialog" name="D"><layout class="QVBoxLayout" name="v"/></widget></ui>''',
    "item_sans_widget": '''<ui version="4.0"><class>Form</class>
 <widget class="QDialog" name="D"><layout class="QVBoxLayout" name="v">
   <item><property name="alignment"><set>Qt::AlignRight</set></property></item>
   <item><layout class="QHBoxLayout" name="h"/></item></layout></widget></ui>''',
    "colonnes_negatives": '''<ui version="4.0"><class>Form</class>
 <widget class="QDialog" name="D"><layout class="QGridLayout" name="g">
   <item row="-3" column="-2"><widget class="QLabel" name="n"/></item>
   <item row="0" column="0"><widget class="QLabel" name="o"/></item></layout></widget></ui>''',
    "geometry_non_number": '''<ui version="4.0"><class>Form</class>
 <widget class="QDialog" name="D"><property name="geometry"><rect><x>abc</x><y>0</y>
   <width>10</width><height>10</height></rect></property>
   <widget class="QLabel" name="q"/></widget></ui>''',
    "pas_de_widget_racine": '''<ui version="4.0"><class>Form</class></ui>''',
    "imbrique_profond": '''<ui version="4.0"><class>Form</class>
 <widget class="QDialog" name="D"><layout class="QVBoxLayout" name="v"><item>
  <widget class="QGroupBox" name="b"><layout class="QHBoxLayout" name="h"><item>
   <widget class="QGroupBox" name="b2"><layout class="QVBoxLayout" name="v2"><item>
    <widget class="QPushButton" name="fond"><property name="text"><string>Fond</string></property></widget>
   </item></layout></widget></item></layout></widget></item></layout></widget></ui>''',
}

for name, xml in CASES.items():
    path = os.path.join(HERE, "bad_%s.ui" % name)
    out = path + ".out"
    open(path, "w", encoding="utf-8").write(xml)
    v = object.__new__(UiViewerPlugin)
    v.widgets_data, v.selected_idx = [], None
    v.widget_counter, v.ui_file = 0, path
    v.root_widget_name, v.root_widget_class = "D", "QDialog"
    v.root_geometry, v.root_title = (0, 0, 300, 200), "D"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    print("--- %s ---" % name)
    t0 = time.time()
    try:
        data, info = v._parse_ui(path)
        v.widgets_data = data
        v.root_geometry = info.get("geometry", (0, 0, 300, 200))
        v.root_title = info.get("title", "D")
        v._write_ui_file(out)
        again, _i = v._parse_ui(out)
        ET.parse(out)
        ok = time.time() - t0 < 3
        check(ok, "parse + save + relecture en %.2fs, %d widget(s)"
              % (time.time() - t0, len(data)))
    except Exception as e:
        check(False, "exception : %r" % e)

# un <ui> sans widget racine n'est plus avale silencieusement : le lecteur le
# dit, une seule fois, et les autres cas tordus restent muets.
check(len([d for d in dialogues if d[0] == "error"]) == 1,
      "le fichier sans forme a ete refuse avec un message, les autres cas "
      "sans en creer un deuxieme")

# le cas profond doit placement sans superposition
v = object.__new__(UiViewerPlugin)
v.widgets_data, v.selected_idx = [], None
v.widget_counter, v.ui_file = 0, None
v.root_widget_name, v.root_widget_class = "D", "QDialog"
v.root_geometry, v.root_title = (0, 0, 300, 200), "D"
v._source_ui, v._source_uids, v._src_root = None, [], {}
data, info = v._parse_ui(os.path.join(HERE, "bad_imbrique_profond.ui"))
pos = {p["name"]: p.get("geometry") for _c, p in data}
print("--- imbrication profonde : positions ---", pos)
check(all(pos.get(n) for n in ("b", "b2", "fond")),
      "les widgets imbriques sont places, pas empiles en (10,10)")

print()
print("RESULTAT : %d echecs" % len(fails))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
