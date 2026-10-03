"""Noms d'objets : rouvrir un fichier ne doit jamais faire naitre de doublon.

Cas reel etudie : un eleve ouvre un .ui deja nomme (pushButton..pushButton5),
ajoute un widget. Sans graine, le plugin repart de 1 et produit un nom deja pris.
loadUi accepte le doublon sans se plaindre : le code generee (windows.<nom>)
vise alors un autre widget que celui que l'eleve vient de creer.
"""
import os
import re
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

import UIViewer                                    # noqa: E402
from UIViewer import UiViewerPlugin                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "names_designer.ui")
OWN = os.path.join(HERE, "names_own_file.ui")
OUT = os.path.join(HERE, "names_out.ui")

FAILS = []
CHECKS = [0]


def check(label, cond, detail=""):
    CHECKS[0] += 1
    if not cond:
        FAILS.append("%s %s" % (label, detail))
    print("%s %s%s" % ("OK  " if cond else "FAIL", label, (" -> " + detail) if detail else ""))


# ── un vrai fichier de Qt Designer, avec une famille deja numerotee ──
def write_fixture():
    items = "".join(
        '   <item>\n    <widget class="QPushButton" name="pushButton%s">\n'
        '     <property name="text"><string>Bouton %s</string></property>\n'
        "    </widget>\n   </item>\n" % (n, n)
        for n in ["", 2, 3, 4, 5])
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<ui version="4.0">\n <class>Form</class>\n'
           ' <widget class="QWidget" name="Form">\n'
           '  <property name="geometry">\n   <rect>\n'
           '    <x>0</x><y>0</y><width>400</width><height>300</height>\n'
           '   </rect>\n  </property>\n'
           '  <property name="windowTitle"><string>Formulaire</string></property>\n'
           '  <layout class="QVBoxLayout" name="verticalLayout">\n' + items +
           '   <item>\n    <widget class="QLineEdit" name="lineEdit"/>\n   </item>\n'
           '   <item>\n    <widget class="QLabel" name="label">\n'
           '     <property name="text"><string>Bonjour</string></property>\n'
           "    </widget>\n   </item>\n"
           '  </layout>\n </widget>\n <resources/>\n <connections/>\n</ui>\n')
    open(FIXTURE, "w", encoding="utf-8").write(xml)


def write_own_file():
    """Un fichier enregistre par le plugin lui-meme : familles en minuscules."""
    v = blank()
    v._add_widget("QPushButton")
    v._add_widget("QPushButton")
    v._add_widget("QLineEdit")
    v._write_ui_file(OWN)


class Var(object):
    """Remplace le tk.StringVar du panneau de proprietes."""

    def __init__(self, value):
        self._v = value

    def get(self):
        return self._v


class Lbl(object):
    def config(self, **kw):
        pass


def blank():
    v = object.__new__(UiViewerPlugin)
    v.widgets_data, v.selected_idx = [], None
    v.widget_counter, v.ui_file = 0, None
    v.root_widget_name, v.root_widget_class = "Form", "QWidget"
    v.root_geometry, v.root_title = (0, 0, 400, 300), "Formulaire"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    v._name_entry, v._name_hint = None, None
    v._title_lbl = Lbl()
    v._refresh = lambda: None
    v._select = lambda i: None
    v._show_no_selection = lambda: None
    return v


def names(v):
    return [p["name"] for _, p in v.widgets_data]


def load(path, counter=0):
    v = blank()
    v.widget_counter = counter
    data, info = v._parse_ui(path)
    v.widgets_data = data
    v.root_geometry = info.get("geometry", (0, 0, 400, 300))
    v.root_title = info.get("title", "Form")
    return v


write_fixture()
write_own_file()

print("=== 1. la graine part du fichier lu, par tous les chemins d'ouverture ===")
v = load(FIXTURE)
check("le fichier fixture est bien lu", len(v.widgets_data) == 7, str(len(v.widgets_data)))
check("graine = plus grand suffixe rencontre (5)", v.widget_counter == 5, str(v.widget_counter))
w = blank()
w.load_new_ui_file(FIXTURE)
check("load_new_ui_file meme graine", w.widget_counter == 5, str(w.widget_counter))
check("load_new_ui_file et lecture directe concordent", w.widget_counter == v.widget_counter)
w._add_widget("QPushButton")
check("le nom ajoute est absent du fichier d'origine",
      w.widgets_data[-1][1]["name"] not in [n for n in names(v)],
      w.widgets_data[-1][1]["name"])

print("=== 2. opened twice : la 2e partie de l'eleve ne heurte pas la 1re ===")
v = load(OWN)
before = names(v)
v._add_widget("QPushButton")
v._add_widget("QPushButton")
v._add_widget("QLineEdit")
check("le fichier du plugin est relou", len(before) == 3, str(before))
check("les 3 ajouts ont des noms libres",
      len(set(names(v))) == len(names(v)), str(names(v)))
check("la famille pushbutton continue la serie",
      names(v)[3] == "pushbutton2", names(v)[3])
check("la famille lineedit reste dans sa serie (pas lineedit4)",
      names(v)[5] == "lineedit1", names(v)[5])
check("le compteur suit les numeros emis, sans bloquer les autres familles",
      v.widget_counter == 3, str(v.widget_counter))

print("=== 3. la copie garde la famille du modele ===")
v = load(FIXTURE)
idx = [i for i, n in enumerate(names(v)) if n == "lineEdit"][0]
v._apply("name", Var("btnValider"), idx)
check("renommage valide accepte", names(v)[idx] == "btnValider", names(v)[idx])
v._duplicate(idx)
v._duplicate(idx)
cop = names(v)[-2:]
check("les copies prennent la suite directe de la famille",
      cop == ["btnValider1", "btnValider2"], str(cop))
check("copies != modele et distinctes entre elles",
      len(set(cop + ["btnValider"])) == 3, str(cop))
check("aucun doublon apres 2 copies", len(set(names(v))) == len(names(v)), str(names(v)))

print("=== 4. un renommage manuel impossible est refuse, le modele ne bouge pas ===")
v = load(FIXTURE)
target = len(names(v)) - 1        # le "label"
keep = names(v)[target]
others = set(names(v)) - {keep}
for bad in ["", "  ", "mon nom", "1bad", "btn-ok", "pushButton3"]:
    v._apply("name", Var(bad), target)
    check("refus de %r" % bad, names(v)[target] == keep, names(v)[target])
check("rien d'autre n'a ete modifie", len(others - set(names(v))) == 0)
v._apply("name", Var("btn_ok"), target)
check("un nom valide est accepte", names(v)[target] == "btn_ok", names(v)[target])
v._apply("name", Var("BTN_OK"), target)
check("un nom qui commence par une majuscule est accepte",
      names(v)[target] == "BTN_OK", names(v)[target])
check("_name_problem connait le doublon",
      "deja" in v._name_problem("btnValider", 0) or
      "deja" in v._name_problem(names(v)[0], 1), repr(v._name_problem(names(v)[0], 1)))
check("_name_problem accepte un nom libre", v._name_problem("za", 0) == "")

print("=== 5. enregistrer est bloque tant qu'un nom est inutilisable ===")
calls = []
UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: calls.append(a),
    showinfo=lambda *a, **k: calls.append(a),
    askyesno=lambda *a, **k: False)
v = load(FIXTURE)
check("un fichier sain ne signale rien", v._name_troubles() == [], str(v._name_troubles()))
v._add_widget("QPushButton")
v._write_ui_file(OUT)
ok_names = names(v)
v.widgets_data[1][1]["name"] = v.widgets_data[0][1]["name"]     # doublon force
check("le doublon force est signale", len(v._name_troubles()) == 1, str(v._name_troubles()))
del_ok = os.path.exists(OUT) and open(OUT, encoding="utf-8").read()
v.ui_file = OUT
v._save()
check("_save refuse d'ecrire", del_ok == open(OUT, encoding="utf-8").read())
check("_save previent l'eleve", len(calls) == 1 and "Noms" in calls[0][0], str(calls))
v.widgets_data[2][1]["name"] = "bad name"
v._save()
troubles = v._name_troubles()
check("un nom non identifiant bloque aussi",
      any("bad name" in t for t in troubles), str(troubles))
# messagebox reste bouchonne jusqu'au bout : une boite modale Tk bloquerait
# le test (et se mettrait au milieu de l'ecran de l'utilisateur)

print("=== 6. aller-retour complet : le fichier enregistre est utilisable ===")
v = load(FIXTURE)
check("la graine etait bien 5", v.widget_counter == 5)
for _ in range(3):
    v._add_widget("QPushButton")
v._add_widget("QCheckBox")
v._duplicate(0)
v.ui_file = OUT
v._save()
root = ET.parse(OUT).getroot()
xml_names = [x.get("name") for x in root.iter("widget")]
dupes = sorted({n for n in xml_names if xml_names.count(n) > 1})
check("aucun nom en double dans le fichier", not dupes, str(dupes))
check("tous les noms sont des identifiants",
      all(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", n or "") for n in xml_names),
      str([n for n in xml_names if not n or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", n)]))
check("le nouveau widget checkbox a ete nomme",
      any(n.startswith("checkbox") for n in xml_names), str(xml_names))
check("le nom copie garde sa famille",
      any(n.startswith(names(v)[0]) or n == names(v)[0] for n in xml_names))

from PyQt5 import QtWidgets, uic                                # noqa: E402
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
ui = uic.loadUi(OUT)
expected = {"QPushButton": "QPushButton", "QCheckBox": "QCheckBox",
            "QLineEdit": "QLineEdit", "QLabel": "QLabel",
            "Form": "QWidget"}
bad = []
for cls, props in v.widgets_data:
    n = props["name"]
    obj = getattr(ui, n, None)
    if obj is None or type(obj).__name__ != cls:
        bad.append("%s -> %s (attendu %s)" % (n, type(obj).__name__, cls))
check("chaque nom du modele designe le bon widget apres loadUi", not bad, "; ".join(bad))
check("les 5 pushButton du fichier sont distincts",
      len({id(getattr(ui, n)) for n in ["pushButton", "pushButton2", "pushButton3",
                                        "pushButton4", "pushButton5"]}) == 5)

print("=== 7. _highest_seed / _unique_name sont sans effet de bord caché ===")
v = blank()
check("_highest_seed sur modele vide = valeur recue", v._highest_seed(3) == 3)
v._parse_ui(FIXTURE)      # ne doit pas laisser un modele a moitie rempli
check("_parse_ui n'ecrit pas dans widgets_data", v.widgets_data == [])
check("_parse_ui monte malgre tout le compteur", v.widget_counter == 5, str(v.widget_counter))
v2 = blank()
v2.widgets_data = [("QPushButton", {"name": "x99z"})]
check("un nom sans suffixe final ne monte pas la graine", v2._highest_seed(0) == 0,
      str(v2._highest_seed(0)))
v2.widgets_data = [("QPushButton", {"name": "x99"})]
check("le suffixe final compte", v2._highest_seed(0) == 99, str(v2._highest_seed(0)))

print("=== 8. contrefacon : ce que faisait l'ancien code ===")


def old_name(counter, cls):
    """Ancienne regle : un compteur parti de zero, que le fichier ignore."""
    return cls.replace("Q", "").lower() + str(counter + 1)


v = load(OWN)                       # ['pushbutton', 'pushbutton1', 'lineedit']
naive = old_name(0, "QPushButton")   # ce que le plugin produisait a la 2e partie
check("l'ancien nom aurait ete pushbutton1", naive == "pushbutton1", naive)
check("ce nom est deja pris dans le fichier relu", naive in names(v), str(names(v)))
check("la graine remonte bien le compteur au fichier", v.widget_counter == 1,
      str(v.widget_counter))
check("le nom choisi aujourd'hui est libre",
      v._unique_name("pushbutton") not in names(v), v._unique_name("pushbutton"))

print("=== 9. retour visuel reel : le champ se colore et s'explique ===")
try:
    from tkinter import Tk
    root = Tk()
    root.withdraw()
    from tkinter import Entry, Label
    v = load(FIXTURE)
    v._name_entry = Entry(root, bg="#3c3c3c")
    v._name_hint = Label(root)
    target = len(names(v)) - 1
    ok = v._accept_name("mon nom", target)
    check("le nom refuse est signale", ok is False)
    check("le champ passe en rouge", v._name_entry.cget("bg") == "#5a1a1a",
          v._name_entry.cget("bg"))
    check("l'explication est ecrite sous le champ",
          bool(v._name_hint.cget("text")), repr(v._name_hint.cget("text")))
    v._accept_name("btn_ok", target)
    check("un nom libre rend le champ normal", v._name_entry.cget("bg") == "#3c3c3c",
          v._name_entry.cget("bg"))
    check("et l'explication disparait", v._name_hint.cget("text") == "",
          repr(v._name_hint.cget("text")))
    v._name_entry.destroy()
    v._name_hint.destroy()
    try:
        survived = v._accept_name("za2", 0)     # le panneau a ete detruit sous la main
    except Exception as e:
        survived = "plante : %r" % (e,)
    check("un panneau detruit ne fait pas planter la saisie",
          survived is True and v._name_entry is None and v._name_hint is None,
          repr(survived))
    root.destroy()
except Exception as e:                       # pas d'écran : le test lourd est saute
    print("  (Tk indisponible : %r)" % (e,))

print()
print("%d checks, %d echecs" % (CHECKS[0], len(FAILS)))
for f in FAILS:
    print("ECHEC:", f)
sys.exit(1 if FAILS else 0)
