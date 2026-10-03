"""Round-trip test : un fichier type Qt Designer (layouts) traverse le viewer."""
import os
import sys
from xml.etree import ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, r"C:\Users\Selmen\Desktop\projects\tunisiaschools")
HERE = os.path.dirname(os.path.abspath(__file__))

import types  # noqa: E402
for _name, _attrs in (("thonny", ("get_workbench",)),
                      ("thonny.languages", ("tr",))):
    _m = types.ModuleType(_name)
    for _a in _attrs:
        setattr(_m, _a, lambda *x, **k: x[0] if x else None)
    sys.modules[_name] = _m
sys.modules["thonny"].languages = sys.modules["thonny.languages"]

import UIViewer  # noqa: E402,F401
from UIViewer import UiViewerPlugin  # noqa: E402

SRC = os.path.join(HERE, "designer_layout.ui")
OUT1 = os.path.join(HERE, "out_unchanged.ui")
OUT2 = os.path.join(HERE, "out_edited.ui")

fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def fresh():
    """Instance sans Tk : seules les methodes XML sont utilisees."""
    v = object.__new__(UiViewerPlugin)
    v.widgets_data = []
    v.ui_file = None
    v.widget_counter = 0
    v.selected_idx = None
    v.root_widget_name = "Form"
    v.root_widget_class = "QDialog"
    v.root_geometry = (0, 0, 640, 480)
    v.root_title = "Form"
    v._source_ui = None
    v._source_uids = []
    v._src_root = {}
    data, info = v._parse_ui(SRC)
    v.widgets_data = data
    v.root_geometry = info.get("geometry", (0, 0, 640, 480))
    v.root_title = info.get("title", "Form")
    return v


print("=== 1. lecture du fichier a layouts ===")
v = fresh()
names = [p["name"] for _c, p in v.widgets_data]
print("  widgets : %d %s" % (len(names), names))
check(len(v.widgets_data) == 9, "les 9 widgets des layouts sont vus")

rects = {}
for cls, p in v.widgets_data:
    g = p.get("geometry")
    rects[p["name"]] = g
    print("    %-14s %-14s %s" % (cls, p["name"], g))
check(all(r for r in rects.values()), "tous les widgets ont une position")


def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


pairs = [(n1, n2) for i, n1 in enumerate(rects) for n2 in list(rects)[i + 1:]
         # groupNotes contient btnValider + tableNotes : imbrication legitime
         if not (n1 == "groupNotes" or n2 == "groupNotes")]
clash = [pr for pr in pairs if overlap(rects[pr[0]], rects[pr[1]])]
check(not clash, "aucun widget ne se superpose (%s)" % (clash or "rien"))

print("=== 2. enregistrement sans modification ===")
v._write_ui_file(OUT1)
src_txt = open(SRC, encoding="utf-8").read()
out_txt = open(OUT1, encoding="utf-8").read()
s = ET.parse(SRC).getroot()
o = ET.parse(OUT1).getroot()


def count(el, path):
    return len(el.findall(path))


for path in (".//layout", ".//item", ".//connections/connection",
             ".//spacer", ".//resources", ".//attribute"):
    check(count(s, path) == count(o, path),
          "%s : %d -> %d" % (path, count(s, path), count(o, path)))

lab = [w for w in o.find("widget").iter("widget")
       if w.get("name") == "label"][0]
check(lab.find("property") is None or
      all(p.get("name") != "geometry" for p in lab.findall("property")),
      "aucune <geometry> inventee pour un widget pose par un layout")
check("<string>Physique</string>" in out_txt,
      "la cellule du tableau a survécu")
check("Matiere" in out_txt and "Maths" in out_txt,
      "les titres de colonne / ligne ont survécu")

print("=== 3. modification du modele ===")
w = fresh()
by_name = {p["name"]: p for _c, p in w.widgets_data}
by_name["label"]["text"] = "Nom complet :"           # change
# Regle 7a : un widget range dans un <layout> ne se deplace pas — c'est le
# bouton « Libérer la position » du panneau qui le decide (voir test_pose.py).
# On simule ici ce que ce bouton a fait sur le modele, pour que la geometrie
# demandée soit reellement ecrite.
by_name["btnQuitter"]["_pose"] = "libre"
by_name["btnQuitter"]["geometry"] = (5, 5, 200, 40)  # deplace
tbl = by_name["tableNotes"]
tbl["rows"] = 4                                      # + 3 lignes
combo = by_name["comboClasse"]
combo["items"] = ["1ere S", "2eme S", "3eme S"]     # + 1 element
keep = [t for t in w.widgets_data if t[1]["name"] != "labelClasse"]
w.widgets_data = keep                                # supprime un widget
newprops = {"name": "btnAjoute", "geometry": (300, 250, 90, 26),
            "text": "Ajouter", "styleSheet": "",
            "font": {"size": 9, "bold": False, "italic": False, "family": ""}}
w.widgets_data.append(("QPushButton", newprops))
w._write_ui_file(OUT2)

t2 = open(OUT2, encoding="utf-8").read()
r2 = ET.parse(OUT2).getroot()
check("Nom complet :" in t2, "le texte modifie est ecrit")
check("labelClasse" not in t2, "le widget supprime a disparu")
check(t2.count("<item") == r2.find("widget").findall(".//item").__len__()
      and "verticalSpacer" in t2, "le spacer est toujours present")
check("btnAjoute" in t2, "le widget ajoute est present")
check("<string>3eme S</string>" in t2, "l'element de combo ajoute est present")
check(t2.count("Physique") == 1, "les cellules du tableau ne se multiplient pas")
lay = len(r2.findall(".//layout"))
check(lay == 4, "les 4 layouts d'origine sont conserves (%d)" % lay)
check(len(r2.findall(".//connections/connection")) == 1,
      "la connexion btnQuitter->close est conservee")

tabs = [x for x in r2.iter("widget") if x.get("name") == "tableNotes"][0]
check(len(tabs.findall("row")) == 4 and len(tabs.findall("column")) == 2,
      "table re-ecrite : %d lignes x %d colonnes"
      % (len(tabs.findall("row")), len(tabs.findall("column"))))
check([p.findtext("number") for p in tabs.findall("property")
       if p.get("name") == "rowCount"] == ["4"], "rowCount = 4")
cell = [i for i in tabs.findall("item") if i.get("row") == "0"]
check(cell and cell[0].findtext("property/string") == "Physique",
      "la cellule reste rattachee a son tableau")
q = [x for x in r2.iter("widget") if x.get("name") == "btnQuitter"][0]
gp = [p for p in q.findall("property") if p.get("name") == "geometry"]
check(bool(gp), "un widget dont on a libere la position recoit sa geometry")
check(gp and [int(gp[0].findtext("rect/" + t, "-1"))
              for t in ("x", "y", "width", "height")] == [5, 5, 200, 40],
      "et la position ecrite est celle demandee  -> %s"
      % (gp[0].findtext("rect/x") if gp else None))
peres = {c: p for p in r2.iter() for c in p}
check(peres.get(q) is not None and peres[q].tag == "widget",
      "et il ne reste sous aucun <item> de <layout>  -> %s"
      % (peres.get(q) is not None and peres[q].tag))
# l'invariant 7a sur tout le fichier : aucune geometry sous un <item>
sous_item = [e.get("name") for e in r2.iter("widget")
             if e.find("property[@name='geometry']") is not None
             and peres.get(e) is not None and peres[e].tag == "item"]
check(sous_item == [],
      "aucun widget range ne porte de geometry dans le fichier ecrit  -> %s"
      % sous_item)
check("verticalSpacer" in t2 and
      len([x for x in r2.iter("spacer")]) == 1, "spacer unique conserve")
sp = [x for x in r2.iter("spacer")][0] if len(r2.findall(".//spacer")) else None
if sp is not None:
    check(sp.get("name") == "verticalSpacer", "le spacer n'a pas ete deplace")

print("=== 4. relecture du fichier enregistre ===")
again, info = w._parse_ui(OUT2)
gn = {p["name"]: p for _c, p in again}
check("labelClasse" not in gn and "btnAjoute" in gn, "relecture fidele")
check(gn["label"]["text"] == "Nom complet :", "texte rechu")
check(gn["comboClasse"]["items"] == ["1ere S", "2eme S", "3eme S"],
      "items rechus")
check(gn["tableNotes"]["rows"] == 4, "lignes rechues")
check(info.get("title") == "Gestion des eleves", "titre de fenetreachu")

print("=== 5. duplicer un widget pose par un layout ===")
d = fresh()
src_count = len(open(OUT1, encoding="utf-8").read().split("<widget"))
d.widgets_data.append(("QCheckBox", dict(
    d.widgets_data[4][1], name="copie", _uid=None, _src=None, _est=None,
    geometry=(120, 20, 100, 22), text="Copie")))
d._write_ui_file(os.path.join(HERE, "out_dup.ui"))
dtxt = open(os.path.join(HERE, "out_dup.ui"), encoding="utf-8").read()
dr = ET.fromstring(dtxt)
dnames = [x.get("name") for x in dr.iter("widget")]
check(dnames.count("checkPresent") == 1, "l'original n'est pas duplique")
check("copie" in dnames, "la copie est appendue")
check(len(dr.findall(".//layout")) == 4, "les layouts survivent a la copie")

print()
print("RESULTAT : %d echecs" % len(fails))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
