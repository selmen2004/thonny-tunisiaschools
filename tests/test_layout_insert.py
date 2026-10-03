"""Issue n° 1 : un widget ajoute dans le concepteur doit rejoindre le layout.

Un fichier Qt Designer est presque toujours pilote par un layout : la racine
(f ou le centralWidget) porte un <layout> et ses <item> font office de
positionnement. Or le concepteur ajoutait ses propres widgets en <widget>
frere du <layout>, avec un <geometry> absolu. A l'execution, Qt donne la
geometrie de tout le contenu au layout et ignore celui-la : le widget ajoute
apparait dans le fichier, il est bien present a l'execution... mais pose par
dessus les autres, et le professeur ne retrouve pas son bouton.

Les controles ci-dessous ouvrent de vrais fichiers, ajoutent un widget,
enregistrent, puis verifient l'XML ET le rendu PyQt5 reel (offscreen).
"""
import copy
import os
import sys
import types
from xml.etree import ElementTree as ET

import chemins

BUNDLE = chemins.BUNDLE
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, chemins.PAQUET)

for _name, _attrs in (("thonny", ("get_workbench",)),
                      ("thonny.languages", ("tr",))):
    _m = types.ModuleType(_name)
    for _a in _attrs:
        setattr(_m, _a, lambda *x, **k: x[0] if x else None)
    sys.modules[_name] = _m
sys.modules["thonny"].languages = sys.modules["thonny.languages"]

import UIViewer                                   # noqa: E402
from UIViewer import UiViewerPlugin               # noqa: E402

UIViewer.messagebox = types.SimpleNamespace(      # jamais de fenetre modale ici
    showerror=lambda *a, **k: None, showinfo=lambda *a, **k: None,
    askyesno=lambda *a, **k: True, askopenfilename=lambda *a, **k: "")

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "live", "layout_insert")
os.makedirs(WORK, exist_ok=True)

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + label + (("  <- " + str(detail)) if detail else ""))


DESIGNER = os.path.join(HERE, "designer_layout.ui")     # QDialog + QVBoxLayout


def viewer(path=None):
    """Concepteur sans Tk : uniquement le modele et la partie XML."""
    v = object.__new__(UiViewerPlugin)
    v.widgets_data = []
    v.ui_file = path
    v.widget_counter = 0
    v.selected_idx = None
    v.root_widget_name = "Form"
    v.root_widget_class = "QDialog"
    v.root_geometry = (0, 0, 640, 480)
    v.root_title = "Form"
    v._source_ui = None
    v._source_uids = []
    v._src_root = {}
    v._refresh = lambda: None
    v._select = lambda i: None
    v._show_no_selection = lambda: None
    if path:
        data, info = v._parse_ui(path)
        v.widgets_data = data
        v.root_geometry = info.get("geometry", (0, 0, 640, 480))
        v.root_title = info.get("title", "Form")
    return v


def write(v, name):
    out = os.path.join(WORK, name)
    v._write_ui_file(out)
    return out


def root_of(path):
    return ET.parse(path).getroot().find("widget")


def owner_layout(form, name):
    """(layout_element, item_element) qui portent le widget `name`, ou (None, None)."""
    for lay in form.iter("layout"):
        for item in lay.findall("item"):
            for w in item.findall("widget"):
                if w.get("name") == name:
                    return lay, item
    return None, None


def rect_of(w):
    p = w.find("property[@name='geometry']")
    if p is None:
        return None
    r = p.find("rect")
    return tuple(int(r.findtext(k, "0")) for k in ("x", "y", "width", "height"))


# ── 1. Le fichier Designer : le widget rejoint le layout racine ────────────
v = viewer(DESIGNER)
avant = len(v.widgets_data)
v._add_widget("QPushButton")
nom = v.widgets_data[-1][1]["name"]
chemin = write(v, "ajoute_vbox.ui")

form = root_of(chemin)
lay, item = owner_layout(form, nom)
check("le widget ajoute est porte par un <item> de layout", lay is not None and item is not None,
      ET.tostring(form, encoding="unicode")[:200])
check("c'est bien le layout de premier niveau (QVBoxLayout)",
      lay is not None and lay.get("class") == "QVBoxLayout", lay.get("name") if lay is not None else None)
check("il n'est PAS frere absolu du layout sous la racine",
      nom not in [w.get("name") for w in form.findall("widget")],
      [w.get("name") for w in form.findall("widget")])
check("aucune <geometry> ecrite : c'est le layout qui place le widget",
      rect_of(next(w for w in form.iter("widget") if w.get("name") == nom)) is None,
      rect_of(next(w for w in form.iter("widget") if w.get("name") == nom)))
check("le nombre d'items du layout racine augmente d'un",
      len(lay.findall("item")) == len(ET.parse(DESIGNER).getroot().find("widget")
                                      .find("layout").findall("item")) + 1)
check("les widgets de depart sont intacts",
      len([w for w in form.iter("widget")]) == avant + 1 + 1,
      len([w for w in form.iter("widget")]))
check("le texte du bouton est bien enregistre",
      '<string>Bouton</string>' in ET.tostring(
          next(w for w in form.iter("widget") if w.get("name") == nom), encoding="unicode"))

# le layout racine n'a pas ete deplace ni casse
check("la structure du fichier d'origine est conservee (QGroupBox/grille preserves)",
      len([l for l in form.iter("layout")]) ==
      len([l for l in root_of(DESIGNER).iter("layout")]) + 0,
      len([l for l in form.iter("layout")]))

# ── 2. Enregistrer deux fois ne duplique pas ───────────────────────────────
second = write(v, "ajoute_vbox2.ui")
check("deux enregistrements successifs sont identiques",
      open(chemin, "rb").read() == open(second, "rb").read())
a1, _ = owner_layout(root_of(chemin), nom)
check("le widget n'apparait qu'une fois",
      len([w for w in root_of(chemin).iter("widget") if w.get("name") == nom]) == 1)

# ── 3. Reouverture : l'ajout est relu comme un widget pose par le layout ───
v2 = viewer(chemin)
relu = [(c, p) for c, p in v2.widgets_data if p["name"] == nom]
check("la relecture retrouve le widget ajoute", len(relu) == 1, [p["name"] for c, p in v2.widgets_data])
p = relu[0][1]
check("il est relu comme pose par le layout (uid + _pose + position estimee)",
      bool(p.get("_uid")) and p.get("_pose") == "layout"
      and p.get("_est") and p.get("geometry") == p.get("_est"),
      (p.get("_uid"), p.get("_pose"), p.get("_est"), p.get("geometry")))
check("et son empreinte ne pretend pas que le fichier portait une geometry "
      "(regle 7a : l'empreinte decrit le FICHIER, pas l'ecran)",
      p.get("_src", {}).get("geometry") is None,
      p.get("_src", {}).get("geometry"))
check("une position d'affichage lui est tout de meme estimee",
      p.get("_est") and p.get("geometry") == p.get("_est"), (p.get("_est"), p.get("geometry")))
re_save = write(v2, "ajoute_vbox_reenregistre.ui")
f2 = root_of(re_save)
check("re-enregistre, il reste dans le layout sans geometry",
      owner_layout(f2, nom)[0] is not None and
      rect_of(next(w for w in f2.iter("widget") if w.get("name") == nom)) is None)
check("le cycle ouvrir/sauver/ouvrir/sauver ne duplique rien",
      len([w for w in f2.iter("widget") if w.get("name") == nom]) == 1)

# ── 3bis. Retirer l'ajout laisse le fichier d'origine intact ───────────────
vdel = viewer(DESIGNER)
vdel._add_widget("QPushButton")
nom_del = vdel.widgets_data[-1][1]["name"]
vdel.widgets_data.pop()                      # l'eleve annule son ajout
chemin_del = write(vdel, "ajout_retire.ui")
fdel = root_of(chemin_del)
check("le widget retire ne laisse aucun <item> orphelin",
      owner_layout(fdel, nom_del)[0] is None and
      len([w for w in fdel.iter("widget")]) == len([w for w in root_of(DESIGNER).iter("widget")]),
      [w.get("name") for w in fdel.iter("widget")])
def structure(el):
    """(tag, attributs) de tout l'arbre, whitespace non compris."""
    return [(e.tag, tuple(sorted(e.attrib.items()))) for e in el.iter()]


check("le reste du fichier est structurellement l'original",
      structure(fdel) == structure(root_of(DESIGNER)),
      [(a, b) for a, b in zip(structure(fdel), structure(root_of(DESIGNER))) if a != b][:3])

# ── 4. QMainWindow : le layout est sur le centralWidget ────────────────────
MAIN = os.path.join(WORK, "mainwindow.ui")
open(MAIN, "w", encoding="utf-8").write("""<?xml version="1.0"?>
<ui version="4.0"><class>MainWindow</class><widget class="QMainWindow" name="MainWindow">
 <property name="geometry"><rect><x>0</x><y>0</y><width>400</width><height>300</height></rect></property>
 <property name="windowTitle"><string>MainWindow</string></property>
 <widget class="QWidget" name="centralwidget">
  <layout class="QVBoxLayout" name="verticalLayout">
   <item><widget class="QLabel" name="titre"><property name="text"><string>Bonjour</string></property></widget></item>
  </layout>
 </widget>
</widget></ui>
""")
v3 = viewer(MAIN)
v3._add_widget("QLineEdit")
nom3 = v3.widgets_data[-1][1]["name"]
f3 = root_of(write(v3, "mainwindow_ajout.ui"))
lay3, item3 = owner_layout(f3, nom3)
check("QMainWindow : l'ajout va dans le layout du centralWidget",
      lay3 is not None and lay3.get("class") == "QVBoxLayout", lay3.get("name") if lay3 is not None else None)
check("QMainWindow : pas de <widget> frere de centralwidget",
      [w.get("name") for w in f3.findall("widget")] == ["centralwidget"],
      [w.get("name") for w in f3.findall("widget")])

# ── 5. Grille et formulaire : ligne/colonne calculees ─────────────────────
GRID = os.path.join(WORK, "grille.ui")
open(GRID, "w", encoding="utf-8").write("""<?xml version="1.0"?>
<ui version="4.0"><class>Dialog</class><widget class="QDialog" name="Dialog">
 <property name="geometry"><rect><x>0</x><y>0</y><width>400</width><height>300</height></rect></property>
 <layout class="QGridLayout" name="gridLayout">
  <item row="0" column="0"><widget class="QLabel" name="l0"/></item>
  <item row="0" column="1"><widget class="QLineEdit" name="e0"/></item>
  <item row="2" column="0"><widget class="QLabel" name="l2"/></item>
  <item row="2" column="1"><widget class="QLineEdit" name="e2"/></item>
 </layout>
</widget></ui>
""")
v4 = viewer(GRID)
v4._add_widget("QPushButton")
f4 = root_of(write(v4, "grille_ajout.ui"))
lay4, item4 = owner_layout(f4, v4.widgets_data[-1][1]["name"])
check("QGridLayout : l'item recoit la ligne libre suivante (3, apres row=2)",
      item4 is not None and item4.get("row") == "3" and item4.get("column") == "0",
      (item4.get("row"), item4.get("column")) if item4 is not None else None)
v4._add_widget("QPushButton")
f4b = root_of(write(v4, "grille_ajout2.ui"))
_, item4b = owner_layout(f4b, v4.widgets_data[-1][1]["name"])
check("deuxieme ajout : la ligne suivante encore (4)",
      item4b is not None and item4b.get("row") == "4", item4b.get("row") if item4b is not None else None)

FORM = os.path.join(WORK, "formulaire.ui")
open(FORM, "w", encoding="utf-8").write("""<?xml version="1.0"?>
<ui version="4.0"><class>Dialog</class><widget class="QDialog" name="Dialog">
 <property name="geometry"><rect><x>0</x><y>0</y><width>400</width><height>300</height></rect></property>
 <layout class="QFormLayout" name="formLayout">
  <item row="0" column="0"><widget class="QLabel" name="ln"/></item>
  <item row="0" column="1"><widget class="QLineEdit" name="le"/></item>
 </layout>
</widget></ui>
""")
v5 = viewer(FORM)
v5._add_widget("QCheckBox")
lay5, item5 = owner_layout(root_of(write(v5, "formulaire_ajout.ui")), v5.widgets_data[-1][1]["name"])
check("QFormLayout : nouvelle ligne, column 0",
      item5 is not None and item5.get("row") == "1", (item5.get("row"), item5.get("column"))
      if item5 is not None else None)

# un fichier a l'ancienne : item sans attribut row, position en proprietes
OLDGRID = os.path.join(WORK, "grille_ancienne.ui")
open(OLDGRID, "w", encoding="utf-8").write("""<?xml version="1.0"?>
<ui version="4.0"><class>Dialog</class><widget class="QDialog" name="Dialog">
 <property name="geometry"><rect><x>0</x><y>0</y><width>400</width><height>300</height></rect></property>
 <layout class="QGridLayout" name="gridLayout">
  <item><property name="top"><number>0</number></property><property name="left"><number>0</number></property><widget class="QLabel" name="a"/></item>
  <item><property name="top"><number>5</number></property><property name="left"><number>1</number></property><widget class="QLabel" name="b"/></item>
 </layout>
</widget></ui>
""")
v6 = viewer(OLDGRID)
v6._add_widget("QPushButton")
_, item6 = owner_layout(root_of(write(v6, "grille_ancienne_apres.ui")), v6.widgets_data[-1][1]["name"])
check("grille a l'ancien style Designer : la ligne max est lue dans <top> (6)",
      item6 is not None and item6.get("row") == "6", item6.get("row") if item6 is not None else None)

# ── 6. La pose absolue reste la bonne reponse quand il n'y a pas de layout ─
ABS = os.path.join(WORK, "absolu.ui")
open(ABS, "w", encoding="utf-8").write("""<?xml version="1.0"?>
<ui version="4.0"><class>Dialog</class><widget class="QDialog" name="Dialog">
 <property name="geometry"><rect><x>0</x><y>0</y><width>400</width><height>300</height></rect></property>
 <widget class="QLabel" name="un"><property name="geometry"><rect><x>20</x><y>20</y><width>100</width><height>20</height></rect></property></widget>
 <widget class="QLabel" name="deux"><property name="geometry"><rect><x>20</x><y>60</y><width>100</width><height>20</height></rect></property></widget>
 <widget class="QGroupBox" name="groupe">
  <property name="geometry"><rect><x>20</x><y>100</y><width>200</width><height>120</height></rect></property>
  <layout class="QVBoxLayout" name="insideLayout"/>
 </widget>
</widget></ui>
""")
v7 = viewer(ABS)
v7._add_widget("QPushButton")
nom7 = v7.widgets_data[-1][1]["name"]
f7 = root_of(write(v7, "absolu_apres.ui"))
check("sans layout a la racine : retour a la pose absolue sous la racine",
      nom7 in [w.get("name") for w in f7.findall("widget")],
      [w.get("name") for w in f7.findall("widget")])
check("le widget absolu porte bien une <geometry>",
      rect_of(next(w for w in f7.iter("widget") if w.get("name") == nom7)) is not None)
lay7, _ = owner_layout(f7, nom7)
check("un QGroupBox voisin avec son propre layout ne vole pas l'ajout",
      lay7 is None, lay7.get("name") if lay7 is not None else None)
check("le layout interieur du groupe reste vide",
      len(f7.find(".//layout[@name='insideLayout']").findall("item")) == 0)

# ── 7. Position d'affichage dans le concepteur ─────────────────────────────
v8 = viewer(DESIGNER)
boite_avant = max(q["geometry"][1] + q["geometry"][3] for _c, q in v8.widgets_data)
gauche = min(q["geometry"][0] for _c, q in v8.widgets_data)
hauteur = v8.root_geometry[3]
v8._add_widget("QPushButton")
nx, ny, nw, nh = v8.widgets_data[-1][1]["geometry"]
check("fichier a layout : l'ajout se place sous le contenu, a la marge gauche",
      nx == gauche and ny == min(boite_avant + 6, hauteur - 34), (nx, ny, boite_avant, hauteur))
check("et reste a l'interieur de la fenetre (le layout depasse ici les 300 px)",
      ny + nh <= hauteur, (ny, nh, hauteur))
v8b = viewer(MAIN)                      # un grand vide sous le seul label : de la place
bas_label = max(q["geometry"][1] + q["geometry"][3] for _c, q in v8b.widgets_data)
v8b._add_widget("QPushButton")
nx2, ny2, nw2, nh2 = v8b.widgets_data[-1][1]["geometry"]
check("l'ancre applique la regle « sous le contenu, bornee au bas de la fenetre »",
      ny2 == min(bas_label + 6, v8b.root_geometry[3] - 34), (ny2, bas_label, v8b.root_geometry[3]))
v9 = viewer(ABS)
n = len(v9.widgets_data)
v9._add_widget("QPushButton")
check("dans un fichier sans layout, la cascade de creation est conservee",
      v9.widgets_data[-1][1]["geometry"][:2] == (10 + (n % 10) * 14,) * 2,
      v9.widgets_data[-1][1]["geometry"])

# ── 8. La preuve a l'execution, avec PyQt5 reel ────────────────────────────
from PyQt5.QtCore import QRect                                    # noqa: E402
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget   # noqa: E402
from PyQt5.uic import loadUi                                    # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)

d = loadUi(chemin)
bouton = d.findChild(QPushButton, nom)
check("loadUi retrouve le widget ajoute", bouton is not None, nom)
check("il est bien l'objet de la bonne classe", isinstance(bouton, QPushButton), type(bouton))
index = d.layout().indexOf(bouton) if d.layout() else -1
check("LE POINT DU BUG : le layout le prend en charge (indexOf >= 0)",
      index >= 0, index)
check("il est en derniere position de la colonne",
      index == d.layout().count() - 1, (index, d.layout().count()))
d.resize(420, 420)
d.show()
app.processEvents()
occupe = bouton.geometry()
check("Qt lui a attribue une position (pas celle du fichier)",
      occupe.height() > 0 and occupe.width() > 0, occupe.getRect())


def collisions(fenetre, cible):
    """Noms des widgets de premier plan qui chevauchent `cible` (memes parents)."""
    zone = QRect(cible.geometry())
    genants = []
    for w in fenetre.findChildren(QWidget):
        if w is cible or w.parent() is not fenetre or not w.isVisible():
            continue
        if zone.intersects(w.geometry()):
            genants.append(w.objectName())
    return genants


check("aucun widget de la fenetre ne se retrouve pose par-dessus lui",
      collisions(d, bouton) == [], collisions(d, bouton))
check("il est visible a l'execution et rattache a la fenetre",
      bouton.isVisible() and bouton.parent() is d,
      (bouton.isVisible(), bouton.parent()))

# contre-factuel : l'ancienne facon d'ecrire, rejouee sur le meme fichier
v10 = viewer(DESIGNER)
v10._add_widget("QPushButton")
nom_old = v10.widgets_data[-1][1]["name"]
racine_old = copy.deepcopy(ET.parse(DESIGNER).getroot())   # le fichier d'origine
form_old = racine_old.find("widget")
el_old = ET.SubElement(form_old, "widget", {"class": "QPushButton", "name": nom_old})
v10._set_rect_prop(el_old, (10, 10, 90, 26))
old_path = os.path.join(WORK, "ancienne_methode.ui")
old_root = ET.ElementTree(racine_old)
ET.indent(old_root, space="  ")
old_root.write(old_path, encoding="utf-8", xml_declaration=True)
d_old = loadUi(old_path)
b_old = d_old.findChild(QPushButton, nom_old)
check("l'ancien code produisait bien un widget hors layout (indexOf == -1)",
      b_old is not None and (d_old.layout().indexOf(b_old) if d_old.layout() else -1) < 0,
      d_old.layout().indexOf(b_old) if d_old.layout() else None)
d_old.resize(420, 420)
d_old.show()
app.processEvents()
check("et que sa geometrie restait celle du fichier, pose par-dessus le contenu",
      b_old.geometry().getRect() == (10, 10, 90, 26), b_old.geometry().getRect())
premier = d_old.layout().itemAt(0).widget()
check("il chevauchait le premier widget de la colonne",
      premier is not None and QRect(b_old.geometry()).intersects(premier.geometry()),
      (b_old.geometry().getRect(), premier.geometry().getRect() if premier is not None else None))
check("mesure : l'ancien code empilait les widgets, le nouveau non",
      collisions(d_old, b_old) != [] and collisions(d, bouton) == [],
      (collisions(d_old, b_old), collisions(d, bouton)))

fails = [r for r in results if not r[1]]
print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
for label, ok in fails:
    print("  echec : " + label)
sys.exit(1 if fails else 0)
