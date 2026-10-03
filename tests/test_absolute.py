"""Fichier a positions absolues (pas de layout) : le merge ne doit rien casser."""
import os
import sys
from xml.etree import ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, r"C:\Users\Selmen\Desktop\projects\tunisiaschools")
import types  # noqa: E402
for _n, _a in (("thonny", ("get_workbench",)), ("thonny.languages", ("tr",))):
    _m = types.ModuleType(_n)
    for _x in _a:
        setattr(_m, _x, lambda *x, **k: x[0] if x else None)
    sys.modules[_n] = _m
sys.modules["thonny"].languages = sys.modules["thonny.languages"]
from UIViewer import UiViewerPlugin  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "absolute.ui")
OUT = os.path.join(HERE, "absolute_out.ui")

open(SRC, "w", encoding="utf-8").write('''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="geometry"><rect><x>0</x><y>0</y><width>500</width><height>400</height></rect></property>
  <property name="windowTitle"><string>Bac 2026</string></property>
  <widget class="QLabel" name="titre">
   <property name="geometry"><rect><x>20</x><y>15</y><width>200</width><height>30</height></rect></property>
   <property name="text"><string>Bonjour</string></property>
   <property name="font"><font><pointsize>12</pointsize><weight>75</weight><bold>true</bold><kerning>0</kerning></font></property>
  </widget>
  <widget class="QPushButton" name="ok">
   <property name="geometry"><rect><x>20</x><y>60</y><width>90</width><height>26</height></rect></property>
   <property name="text"><string>OK</string></property>
   <property name="cursor"><cursorShape>PointingHandCursor</cursorShape></property>
  </widget>
  <widget class="QLineEdit" name="saisie">
   <property name="geometry"><rect><x>140</x><y>60</y><width>150</width><height>22</height></rect></property>
  </widget>
 </widget>
 <resources/>
</ui>
''')

fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


v = object.__new__(UiViewerPlugin)
v.widgets_data, v.selected_idx = [], None
v.widget_counter, v.ui_file = 0, SRC
v.root_widget_name, v.root_widget_class = "Form", "QWidget"
v.root_geometry, v.root_title = (0, 0, 640, 480), "Form"
data, info = v._parse_ui(SRC)
v.widgets_data = data
v.root_geometry = info["geometry"]
v.root_title = info["title"]

print("=== lecture ===")
for cls, p in v.widgets_data:
    print("   %-14s %-8s %s est_absolu=%s" % (cls, p["name"], p["geometry"],
                                              p["_src"]["geometry"] is not None))
check(all(p["_src"]["geometry"] for _c, p in v.widgets_data),
      "les 3 widgets sont en position absolue")

print("=== edition : texte, police, suppression, ajout ===")
byname = {p["name"]: p for _c, p in v.widgets_data}
byname["titre"]["text"] = "Au revoir"
byname["ok"]["checked"] = True              # ne doit rien ecrire sur un bouton
del byname["saisie"]
v.widgets_data = [(c, p) for c, p in v.widgets_data if p["name"] != "saisie"]
v.widgets_data.append(("QCheckBox", {
    "name": "case", "geometry": (300, 100, 100, 22), "text": "Coche",
    "checked": True, "styleSheet": "",
    "font": {"size": 9, "bold": False, "italic": False, "family": ""}}))
v._write_ui_file(OUT)

txt = open(OUT, encoding="utf-8").read()
r = ET.parse(OUT).getroot()
widgets = {w.get("name"): w for w in r.iter("widget")}
check("Au revoir" in txt, "texte modifie ecrit")
check("saisie" not in txt, "widget supprime retire")
check("case" in widgets and "QCheckBox" == widgets["case"].get("class"),
      "nouveau widget ajout")
check(widgets["ok"].find("property/cursorShape") is not None or
      "PointingHandCursor" in txt, "propriete inconnue (cursor) conservee")
check("kerning" in txt, "champ <kerning> de la police conserve")
check("<weight>75</weight>" in txt, "champ <weight> conserve")
check("PointingHandCursor" in txt, "cursor du bouton conserve")
def props_of(w, name):
    return [p for p in w.findall("property") if p.get("name") == name]


check(len(props_of(widgets["ok"], "geometry")) == 1,
      "une seule geometry sur le bouton")
g = props_of(widgets["titre"], "geometry")[0].find("rect")
check(g.findtext("width") == "200" and g.findtext("height") == "30",
      "geometry du label inchangee : %sx%s" % (g.findtext("width"),
                                               g.findtext("height")))
check(not props_of(widgets["ok"], "checked"),
      "pas de <checked> ecrit sur un QPushButton")
check(props_of(widgets["Form"], "windowTitle")[0].findtext("string")
      == "Bac 2026", "titre de la racine conserve")
check(len(r.findall("resources")) == 1, "<resources> conserve")

print("=== relecture ===")
v2 = object.__new__(UiViewerPlugin)
v2.widget_counter = 0        # __init__ ne tourne pas dans ce harnais
d2, i2 = v2._parse_ui(OUT)
n2 = {p["name"]: p for _c, p in d2}
check(set(n2) == {"titre", "ok", "case"}, "noms rechus : %s" % sorted(n2))
check(n2["titre"]["text"] == "Au revoir", "texte rechu")
check(n2["titre"]["font"]["bold"] is True and n2["titre"]["font"]["size"] == 12,
      "police rechue : %s" % n2["titre"]["font"])
check(n2["case"]["checked"] is True, "case cochee rechue")
check(i2["title"] == "Bac 2026", "titre de fenetre rechu")

print("=== nouveau cycle : re-enregistrer sans rien changer ===")
v2.widgets_data = d2
v2.root_geometry = i2["geometry"]
v2.root_title = i2["title"]
v2._write_ui_file(OUT + "2")
t_a = open(OUT, encoding="utf-8").read()
t_b = open(OUT + "2", encoding="utf-8").read()
check(t_a == t_b, "enregistrer deux fois de suite ne change rien au fichier")

print()
print("RESULTAT : %d echecs" % len(fails))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
