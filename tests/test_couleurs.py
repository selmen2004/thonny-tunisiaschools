r"""Item 2 : un fichier colore doit s'ouvrir.

Qt Designer ecrit les couleurs d'une feuille de style a sa maniere —
`color: rgb(0, 128, 0)`, `background-color: palette(base)`, `#f00`, une valeur a
alpha — et l'apercu du viewer passait ce texte tel quel dans `fg=` et `bg=` de
Tk. Tk ne connait aucune de ces ecritures : il leve `TclError: unknown color
name "rgb(0, 128, 0)"`. Comme rien ne capturait l'erreur, un fichier .ui avec un
seul widget colore refusait tout simplement de s'ouvrir — l'eleve ne voyait plus
ni sa fenetre, ni le bouton qu'il avait peint en vert.

Le traducteur s'occupe de l'apercu, et de lui seul : le fichier, lui, garde le
texte de l'eleve mot pour mot. Cette suite verifie les deux moities :

  1. ce que Tk refusait, refuse par Tk lui-meme (témoin negatif) ;
  2. le traducteur, table complete, et la regle absolue : ce qu'il rend est
     affichable par Tk, ou c'est None ;
  3. les noms de couleurs, que seul un Tk reel peut admettre ;
  4. ouvrir le fichier colore : plus d'exception, et l'apercu montre la teinte
     traduite — avec la preuve que l'ancienne version craquait sur le meme
     fichier ;
  5. enregistrer : les mots de Qt ressortent intacts, la traduction ne fuit
     jamais dans le fichier ;
  6. la preuve par l'execution : loadUi() rend la meme teinte que l'apercu ;
  7. le panneau de proprietes : le cache de couleur et la boite de choix
     recoivent une valeur que Tk accepte ;
  8. choisir une couleur (item 11) : la declaration remplacee est celle du
     champ clique, et une seule — « color » n'est pas « background-color », et
     le filtre ne doit pas emporter les voisines au passage.

Les fichiers generes s'appellent gen_couleurs*.ui : « *.ui » est ignore, seules
les fixtures lues sans jamais etre ecrites sont suivies dans git.
"""
import json
import os
import subprocess
import sys
import types
from xml.etree import ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
# La copie sous contrat (mutants_couleurs.py) : sans cette ligne la suite
# importerait le paquet vivant pendant qu'un grade examine une copie mutee, et
# le verdict ne prouverait rien.
PLUGIN = os.environ.get("TUNISIASCHOOLS_COPIE") or \
    r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

for _n, _a in (("thonny", ("get_workbench",)), ("thonny.languages", ("tr",))):
    _m = types.ModuleType(_n)
    for _x in _a:
        setattr(_m, _x, lambda *x, **k: x[0] if x else None)
    sys.modules[_n] = _m
sys.modules["thonny"].languages = sys.modules["thonny.languages"]

import tkinter as tk                                   # noqa: E402
import UIViewer                                        # noqa: E402
from UIViewer import UiViewerPlugin                    # noqa: E402

dialogues = []
UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: dialogues.append(("error",) + a[1:]),
    showinfo=lambda *a, **k: dialogues.append(("info",) + a[1:]),
    askyesno=lambda *a, **k: True)
UIViewer.get_workbench = lambda: None

racine = tk.Tk()
racine.withdraw()

COLORE = os.path.join(HERE, "gen_couleurs.ui")
SAUVE = os.path.join(HERE, "gen_couleurs_out.ui")
SAUVE2 = os.path.join(HERE, "gen_couleurs_out2.ui")

# Huit widgets, huit ecritures de couleur differentes, du plus courant au plus
# exotique. « degrade » et « transparent » sont volontairement intraduisibles :
# l'apercu doit alors reprendre la teinte habituelle du widget, pas exploser.
COLORE_UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="geometry"><rect><x>0</x><y>0</y><width>420</width><height>320</height></rect></property>
  <property name="windowTitle"><string>Colore</string></property>
  <widget class="QLabel" name="vert">
   <property name="geometry"><rect><x>20</x><y>20</y><width>180</width><height>26</height></rect></property>
   <property name="text"><string>Texte vert</string></property>
   <property name="styleSheet"><string notr="true">color: rgb(0, 128, 0);</string></property>
  </widget>
  <widget class="QLabel" name="hsl">
   <property name="geometry"><rect><x>220</x><y>20</y><width>150</width><height>26</height></rect></property>
   <property name="text"><string>Libelle</string></property>
   <property name="styleSheet"><string notr="true">color: hsl(240, 100%%, 50%%);</string></property>
  </widget>
  <widget class="QLabel" name="alphaHex">
   <property name="geometry"><rect><x>20</x><y>56</y><width>180</width><height>26</height></rect></property>
   <property name="text"><string>Violet</string></property>
   <property name="styleSheet"><string notr="true">color: #800080cc;</string></property>
  </widget>
  <widget class="QLineEdit" name="nomme">
   <property name="geometry"><rect><x>220</x><y>56</y><width>150</width><height>26</height></rect></property>
   <property name="styleSheet"><string notr="true">color: darkGreen; background-color: wheat;</string></property>
  </widget>
  <widget class="QPushButton" name="fondBouton">
   <property name="geometry"><rect><x>20</x><y>92</y><width>180</width><height>28</height></rect></property>
   <property name="text"><string>Bouton</string></property>
   <property name="styleSheet"><string notr="true">background-color: palette(button); color: #fff;</string></property>
  </widget>
  <widget class="QLineEdit" name="rouge">
   <property name="geometry"><rect><x>220</x><y>92</y><width>150</width><height>26</height></rect></property>
   <property name="styleSheet"><string notr="true">color: rgba(255, 0, 0, 0.4);</string></property>
  </widget>
  <widget class="QCheckBox" name="degrade">
   <property name="geometry"><rect><x>20</x><y>128</y><width>180</width><height>24</height></rect></property>
   <property name="text"><string>Degrade</string></property>
   <property name="styleSheet"><string notr="true">color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ee00ee, stop:1 #00ee00);</string></property>
  </widget>
  <widget class="QTextEdit" name="transparent">
   <property name="geometry"><rect><x>20</x><y>160</y><width>350</width><height>60</height></rect></property>
   <property name="styleSheet"><string notr="true">background: transparent;</string></property>
  </widget>
 </widget>
 <resources/>
 <connections/>
</ui>
'''
open(COLORE, "w", encoding="utf-8").write(COLORE_UI % ())

# Les feuilles de style du fichier, suchees a la main pour la section 5 : c'est
# le texte de l'eleve, il doit ressortir a l'identique.
SHEETS = {
    "vert": "color: rgb(0, 128, 0);",
    "hsl": "color: hsl(240, 100%, 50%);",
    "alphaHex": "color: #800080cc;",
    "nomme": "color: darkGreen; background-color: wheat;",
    "fondBouton": "background-color: palette(button); color: #fff;",
    "rouge": "color: rgba(255, 0, 0, 0.4);",
    "degrade": ("color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                "stop:0 #ee00ee, stop:1 #00ee00);"),
    "transparent": "background: transparent;",
}

bilan = [0, 0]


def check(cond, msg, detail=None):
    bilan[0] += 1
    print(("  OK   " if cond else "  FAIL ") + msg +
          ("" if cond or detail is None else "  [%s]" % (detail,)))
    if not cond:
        bilan[1] += 1


def leve(fn):
    try:
        fn()
        return None
    except Exception as e:
        return type(e).__name__ + ": " + str(e)


def octets(c):
    """Les trois octets d'un #rrggbb, ou None si ce n'est pas un #rrggbb.

    Un traducteur qui rendrait le texte brut de Qt ne doit pas faire eclater la
    suite : il doit la faire echouer.
    """
    if not isinstance(c, str) or len(c) != 7 or not c.startswith("#"):
        return None
    try:
        return [int(c[1 + 2 * i:3 + 2 * i], 16) for i in range(3)]
    except ValueError:
        return None


def fenetre(nom):
    top = tk.Toplevel(racine)
    top.title(nom)
    top.geometry("980x680+30+30")
    top.update()
    v = UiViewerPlugin(top)
    v.pack(fill=tk.BOTH, expand=True)
    top.update()
    return top, v


def harnais(path):
    """Le modele seul, sans vue : le traducteur n'a besoin de Tk que pour les
    noms de couleurs, et ces cas-la se jouent dans la section 3."""
    v = object.__new__(UiViewerPlugin)
    v.widgets_data, v.selected_idx = [], None
    v.widget_counter, v.ui_file = 0, path
    v.root_widget_name, v.root_widget_class = "Form", "QWidget"
    v.root_geometry, v.root_title = (0, 0, 420, 320), "Form"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    data, info = v._parse_ui(path)
    v.widgets_data = data
    v.root_geometry = info.get("geometry", (0, 0, 420, 320))
    v.root_title = info.get("title", "Form")
    return v


def index_de(v, nom):
    return next(i for i, (_c, p) in enumerate(v.widgets_data)
                if p["name"] == nom)


def apercu(v, nom):
    """Les couleurs que Tk affiche vraiment pour un widget du canevas.

    Un chargement qui echoue en route laisse un cadre sans interieur : rien ne
    sert alors de faire eclater la suite, elle echoue deja check par check.
    """
    idx = index_de(v, nom)
    outer = next((c for c in v.ui_frame.winfo_children()
                  if getattr(c, "_is_outer", False)
                  and getattr(c, "_widget_idx", None) == idx), None)
    if outer is None or not outer.winfo_children():
        return set(), set()
    inner = outer.winfo_children()[0]
    fg, bg = set(), set()
    file = [inner]
    while file:
        w = file.pop()
        if "fg" in w.keys():
            fg.add(w.cget("fg"))
        if "bg" in w.keys():
            bg.add(w.cget("bg"))
        file.extend(w.winfo_children())
    return fg, bg


def lire(chemin):
    return ET.parse(chemin).getroot()


# Ce que faisait l'ancienne version : recopier le texte de Qt dans fg= / bg=.
# Elle est rejouee telle quelle pour que la suite prouve le bug, pas seulement
# la correction.
ORIGINALE = UiViewerPlugin._parse_ss


def sans_correctif(self, ss):
    fg = bg = None
    for part in (ss or "").split(";"):
        part = part.strip()
        if part.startswith("color:"):
            fg = part.split(":", 1)[1].strip()
        elif "background-color:" in part:
            bg = part.split(":", 1)[1].strip()
        elif part.startswith("background:"):
            bg = part.split(":", 1)[1].strip()
    return fg, bg


def avec_correctif():
    UiViewerPlugin._parse_ss = ORIGINALE


# ── 1. ce que Tk refusait ────────────────────────────────────────────────
print("=== 1. Tk refuse les ecritures de Qt ===")
REFUSEES = ["rgb(0, 128, 0)", "rgba(255, 0, 0, 0.4)", "palette(base)",
            "palette(button)", "#800080cc", "hsl(240, 100%, 50%)",
            "qlineargradient(x1:0)", "#1122334455"]
for valeur in REFUSEES:
    check("TclError" in str(leve(lambda: tk.Label(racine, fg=valeur))),
          "Tk refuse fg=%r" % valeur,
          leve(lambda: tk.Label(racine, fg=valeur)))
for valeur in ["rgb(255, 255, 0)", "palette(base)", "#ff000088"]:
    check("TclError" in str(leve(lambda: tk.Label(racine, bg=valeur))),
          "Tk refuse bg=%r" % valeur,
          leve(lambda: tk.Label(racine, bg=valeur)))
# Ce que Tk accepte, pour que la liste ci-dessus ne soit pas un « tout refuse ».
for valeur in ["#008000", "#ffffff", "darkGreen", "wheat", "#112233"]:
    check(leve(lambda: tk.Label(racine, fg=valeur)) is None,
          "Tk accepte fg=%r" % valeur,
          leve(lambda: tk.Label(racine, fg=valeur)))

top, v = fenetre("couleurs-avant")
UiViewerPlugin._parse_ss = sans_correctif
try:
    plantage = leve(lambda: v.load_new_ui_file(COLORE))
finally:
    avec_correctif()
check("TclError" in str(plantage) and "unknown color" in str(plantage),
      "avant le correctif, ouvrir ce fichier faisait tomber Tk", plantage)
top.destroy()

# ── 2. le traducteur ─────────────────────────────────────────────────────
print("=== 2. le traducteur, sans fenetre ===")
v = harnais(COLORE)

# (feuille de style, fg attendu, bg attendu). None = « rien a previsualiser ».
TABLE = [
    ("color: rgb(255, 0, 0);",                    "#ff0000", None),
    ("color:rgb(0,128,0)",                        "#008000", None),
    ("COLOR: RGB(0, 0, 255);",                    "#0000ff", None),
    ("  color : rgb(0, 0, 255) ;  ",              "#0000ff", None),
    ("background-color: rgb(12, 34, 56);",        None,      "#0c2238"),
    ("color: rgba(255, 0, 0, 0.4);",              "#ff0000", None),
    ("background-color: rgba(0, 0, 0, 40%);",     None,      "#000000"),
    ("color: rgb(300, -20, 0);",                  "#ff0000", None),
    ("color: rgb(inf, 0, 0);",                    "#ff0000", None),
    ("color: rgb(nan, 0, 0);",                    "#000000", None),
    ("color: hsl(240, 100%, 50%);",               "#0000ff", None),
    ("color: hsl(120, 1.0, 0.5);",                "#00ff00", None),
    ("color: hsla(0, 100%, 50%, 0.3);",           "#ff0000", None),
    ("color: #fff;",                              "#ffffff", None),
    ("color: #f00f;",                             None,      None),
    ("color: #ffff0000;",                         "#ff0000", None),
    ("color: #800080cc;",                         "#0080cc", None),
    ("color: #ff000080;",                         "#000080", None),
    ("color: #112233445;",                        "#112344", None),
    ("color: #112233445566;",                     "#113355", None),
    ("color: #008000; background-color: #ffffff;", "#008000", "#ffffff"),
    ("background: palette(base);",                None,      "#ffffff"),
    ("color: palette(WindowText);",               "#000000", None),
    ("background-color: palette( Button );",      None,      "#e1e1e1"),
    ("background-color: palette(Active, Button);", None,     "#e1e1e1"),
    ("color: palette(Window, WindowText);",       "#000000", None),
    ("color: palette(HighlightedText);",          "#ffffff", None),
    # intraduisibles : l'apercu reprend la teinte habituelle, le fichier ne
    # bouge pas d'un octet.
    ("border: 1px solid gray;",                   None,      None),
    ("color: qlineargradient(x1:0, stop:0 #ee00ee);", None,  None),
    ("color: transparent;",                       None,      None),
    ("background-color: none;",                   None,      None),
    ("color:",                                    None,      None),
    ("color: #12g456;",                           None,      None),
    ("color: #1122334455;",                       None,      None),
    ("color: rgb(1, 2);",                         None,      None),
    ("color: rgb(1, 2, x);",                      None,      None),
    ("color: palette(noeur);",                    None,      None),
    # Un nom de propriete qui FINIT comme l'une des deux n'est pas l'une des
    # deux : « alternate-background-color » decrit les lignes alternees d'un
    # tableau, « selection-color » la surbrillance. Les lire comme la couleur du
    # widget afficherait a l'ecran une teinte que l'eleve n'a pas demandee.
    # (Valeurs en rgb(), pas en noms de couleur : le harnais de cette section
    # n'a pas de Tk sous la main, et un nom y devient None quelle que soit la
    # regle — le nom est verifie dans la section 3, avec une vraie fenetre.)
    ("alternate-background-color: rgb(255, 255, 0);",  None,   None),
    ("selection-color: rgb(0, 128, 0);",           None,      None),
    ("ALTERNATE-BACKGROUND-COLOR: RGB(255, 255, 0);", None,   None),
    ("border-color: rgb(255, 0, 0);",              None,      None),
    ("color: rgb(255, 0, 0); alternate-background-color: rgb(0, 255, 0);",
     "#ff0000", None),
    ("",                                          None,      None),
]
for ss, fg_attendu, bg_attendu in TABLE:
    rendu = v._parse_ss(ss)
    check(rendu == (fg_attendu, bg_attendu),
          "_parse_ss(%r) -> %r" % (ss, rendu), rendu)
    for c in rendu:
        if c is not None:
            check(leve(lambda: racine.winfo_rgb(c)) is None,
                  "…et %r est affichable par Tk" % (c,),
                  leve(lambda: racine.winfo_rgb(c)))
check(v._parse_ss(None) == (None, None), "_parse_ss(None) ne casse pas")
# Les pourcentages passent par un arrondi : ce qui est verifie ici, c'est
# l'ordre de grandeur des octets, pas le mode d'arrondi de Python.
fg, _ = v._parse_ss("color: rgb(30%, 40%, 50%);")
check(octets(fg) is not None and all(
    abs(a - attendu) <= 1 for a, attendu in zip(octets(fg), (76.5, 102.0, 127.5))),
    "rgb(30%, 40%, 50%) devient une teinte proportionnelle", fg)
check(v._parse_ss("color: rgb(0, 128, 0); background-color: palette(base);")
      == ("#008000", "#ffffff"), "les deux couleurs d'une meme feuille")
check(v._parse_ss("padding: 4px; color: #ff0000; margin: 2px;")
      == ("#ff0000", None), "une couleur perdue dans d'autres regles")

# ── 3. les noms de couleurs, avec une vraie fenetre ──────────────────────
print("=== 3. les noms de couleurs ===")
top, v = fenetre("couleurs-noms")
check(v._couleur_tk("darkGreen") == "darkGreen",
      "un nom que Tk connait passe tel quel")
check(v._parse_ss("color: darkGreen; background-color: wheat;")
      == ("darkGreen", "wheat"),
      "la feuille de l'eleve, traduite par Tk lui-meme")
check(v._couleur_tk("couleurInvention") is None,
      "un nom que Tk ne connait pas devient None, jamais une exception",
      v._couleur_tk("couleurInvention"))
check(v._couleur_tk("#008000") == "#008000", "une ecriture hexadecimale passe")
check(v._couleur_tk("  ") is None and v._couleur_tk(None) is None,
      "rien dire, c'est None")
top.destroy()

# ── 4. ouvrir le fichier colore ──────────────────────────────────────────
print("=== 4. ouvrir un fichier colore ===")
top, v = fenetre("couleurs-ouverture")
plantage = leve(lambda: v.load_new_ui_file(COLORE))
check(plantage is None, "load_new_ui_file() ne leve plus rien", plantage)
check(len(v.widgets_data) == 8, "les huit widgets sont charges",
      len(v.widgets_data))
check([p["name"] for _c, p in v.widgets_data] ==
      ["vert", "hsl", "alphaHex", "nomme", "fondBouton", "rouge", "degrade",
       "transparent"], "dans l'ordre du fichier",
      [p["name"] for _c, p in v.widgets_data])

qt = UIViewer
ATTENDU = {
    "vert":        ({"#008000"}, {qt.QT_BG}),
    "hsl":         ({"#0000ff"}, {qt.QT_BG}),
    "alphaHex":    ({"#0080cc"}, {qt.QT_BG}),
    "nomme":       ({"darkGreen"}, {"wheat", qt.QT_ENTRY_BG}),
    "fondBouton":  ({"#ffffff"}, {"#e1e1e1"}),
    "rouge":       ({"#ff0000"}, {qt.QT_ENTRY_BG}),
    "degrade":     ({qt.QT_FG}, {qt.QT_BG}),          # intraduisible -> defaut
    "transparent": ({qt.QT_FG}, {qt.QT_ENTRY_BG}),    # idem
}
for nom, (fg_voulu, bg_voulu) in ATTENDU.items():
    fg, bg = apercu(v, nom)
    check(fg == fg_voulu and bg <= bg_voulu | {qt.QT_SEL},
          "%s : l'apercu montre %r / %r" % (nom, sorted(fg_voulu),
                                            sorted(bg_voulu)),
          (sorted(fg), sorted(bg)))
    # et surtout : ce que montre l'apercu est ce que Tk sait afficher
    check(all(leve(lambda c=c: racine.winfo_rgb(c)) is None for c in fg | bg),
          "%s : toutes les couleurs affichees sont legales" % nom)

UiViewerPlugin._parse_ss = sans_correctif
top2, v2 = fenetre("couleurs-avant-canevas")
try:
    plantage = leve(lambda: v2.load_new_ui_file(COLORE))
finally:
    avec_correctif()
check("TclError" in str(plantage),
      "le meme fichier, avec l'ancien traducteur, craque toujours", plantage)
top2.destroy()

# ── 5. le fichier garde les mots de l'eleve ──────────────────────────────
print("=== 5. la traduction ne fuit pas dans le fichier ===")
check([p["styleSheet"] for _c, p in v.widgets_data] ==
      list(SHEETS.values()),
      "les feuilles de style du modele sont celles du fichier",
      [p["styleSheet"] for _c, p in v.widgets_data])
v.ui_file = SAUVE
dialogues.clear()
v._save()
texte = open(SAUVE, encoding="utf-8").read()
for nom, sheet in SHEETS.items():
    check(sheet in texte, "%s : %r est ecrit mot pour mot" % (nom, sheet))
check("color: #ff0000" not in texte and "color: #0000ff" not in texte and
      "color: #0080cc" not in texte and "background-color: #e1e1e1" not in texte,
      "aucune couleur traduite n'a remplace le texte de l'eleve")
check("<string notr=\"true\">" in texte,
      "l'attribut notr de Designer survit a l'enregistrement")
check("<class>Form</class>" in texte and "<string>Colore</string>" in texte,
      "la classe et le titre du fichier sont intacts")
v.ui_file = SAUVE2
v._save()
check(open(SAUVE2, encoding="utf-8").read() == texte,
      "enregistrer deux fois rend exactement le meme fichier")
# Reouvrir le fichier enregistre : l'apercu doit sortir les memes teintes.
top3, v3 = fenetre("couleurs-reouverture")
leve(lambda: v3.load_new_ui_file(SAUVE))
check(all(apercu(v3, nom) == apercu(v, nom) for nom in ATTENDU),
      "reouvrir le fichier enregistre montre les memes couleurs")
top3.destroy()
top.destroy()          # une fenetre oubliee ici derange les suites suivantes

# ── 6. ce que Qt rend vraiment ───────────────────────────────────────────
print("=== 6. la preuve par loadUi() ===")
SONDE = r'''
import json, os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, %r)
from PyQt5 import QtWidgets, QtGui, uic
app = QtWidgets.QApplication([])
out = {"erreur": None, "sheets": {}, "teintes": {}}
try:
    w = uic.loadUi(%r)
    w.show()
    app.processEvents()
    out["charge"] = w.objectName()

    def teintes(obj):
        pal = obj.palette()
        tri = set()
        for role in ("WindowText", "Text", "Button", "Base", "BrightText",
                     "Highlight", "Light", "Mid", "Dark", "Shadow",
                     "Midlight", "AlternateBase", "PlaceholderText"):
            try:
                tri.add(pal.color(getattr(QtGui.QPalette, role)).name())
            except Exception:
                pass
        return sorted(tri)

    for nom in ("vert", "hsl", "alphaHex", "nomme", "fondBouton", "rouge",
               "degrade", "transparent"):
        obj = w.findChild(QtWidgets.QWidget, nom)
        out["sheets"][nom] = obj.styleSheet() if obj is not None else None
        out["teintes"][nom] = teintes(obj) if obj is not None else []
    out["textes"] = [w.vert.text(), w.fondBouton.text(), w.degrade.text()]
    # Le vocabulaire de Qt lui-meme, releve atome par atome : c'est l'autorite
    # pour la grammaire hexadecimal, pas une interpretation du plugin.
    out["hex"] = {}
    for t in ("#fff", "#f00f", "#ffffff", "#ffff0000", "#800080cc",
              "#ff000080", "#112233445", "#112233445566", "#1122334455",
              "#12g456", "darkGreen", "wheat"):
        c = QtGui.QColor(t)
        out["hex"][t] = c.name() if c.isValid() else None
except Exception as e:
    out["erreur"] = type(e).__name__ + ": " + str(e)
print(json.dumps(out, ensure_ascii=False))
'''
env = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")
p = subprocess.run(
    [os.path.join(BUNDLE, "python.exe"), "-B", "-c",
     SONDE % (os.path.join(BUNDLE, "Lib", "site-packages"), SAUVE)],
    capture_output=True, text=True, env=env, timeout=180)
try:
    sonde = json.loads(p.stdout.strip().splitlines()[-1])
except Exception:
    sonde = {"erreur": (p.stdout + p.stderr)[-400:]}

check(sonde.get("erreur") is None, "loadUi() ouvre le fichier enregistre",
      sonde.get("erreur"))
check(sonde.get("charge") == "Form", "sous le nom d'objet du fichier",
      sonde.get("charge"))
check(sonde.get("textes") == ["Texte vert", "Bouton", "Degrade"],
      "les textes sont la", sonde.get("textes"))
for nom, sheet in SHEETS.items():
    check(sonde.get("sheets", {}).get(nom) == sheet,
          "%s : Qt relit %r" % (nom, sheet),
          sonde.get("sheets", {}).get(nom))
# Le controle croise : la teinte que l'apercu montre est bien celle que Qt
# applique au widget. « vert » est peint en #008000 par les deux moteurs.
def proche(teintes, hex_attendu):
    """Un role de la palette de Qt a ce hexadecimal a un octet pres.

    Qt range le teinte, la saturation et la luminosite dans des entiers 0..255
    et y arretit sa conversion : hsl(240, 100%, 50%) lui rend #0000fe, pas
    #0000ff. Un octet d'ecart ne se voit pas a l'ecran ; ce qu'on verifie ici,
    c'est que l'apercu ne montre pas une autre couleur.
    """
    def un(c):
        return octets(c)
    cible = un(hex_attendu)
    return any(cible is not None and un(c) is not None
               and all(abs(a - b) <= 1 for a, b in zip(cible, un(c)))
               for c in teintes)


CROISE = [("vert", "#008000"), ("hsl", "#0000ff"), ("alphaHex", "#0080cc"),
          ("rouge", "#ff0000"), ("nomme", "#006400")]
for nom, teinte in CROISE:
    check(proche(sonde.get("teintes", {}).get(nom, []), teinte),
          "%s : Qt rend %s, la teinte que montre l'apercu" % (nom, teinte),
          sonde.get("teintes", {}).get(nom))

# La grammaire hexadecimal, confrontee a Qt atome par atome : ce que QColor lit
# est ce que la feuille de style lit, et le plugin doit suivre, pas deviner.
HEX_QT = {"#fff": "#ffffff", "#f00f": None, "#ffffff": "#ffffff",
          "#ffff0000": "#ff0000", "#800080cc": "#0080cc",
          "#ff000080": "#000080", "#112233445": "#112344",
          "#112233445566": "#113355", "#1122334455": None,
          "#12g456": None}
check(sonde.get("hex", {}) and
      all(sonde["hex"].get(t) == attendu or
          (attendu is not None and proche([sonde["hex"][t]], attendu))
          for t, attendu in HEX_QT.items()),
      "QColor lit les hexadecimaux comme la table les suppose",
      {t: sonde.get("hex", {}).get(t) for t in HEX_QT})
v2 = harnais(COLORE)
for t, attendu in HEX_QT.items():
    check(proche([v2._couleur_tk(t) or ""], attendu) if attendu else
          v2._couleur_tk(t) is None,
          "_couleur_tk(%r) suit Qt" % t, v2._couleur_tk(t))
# Un nom de couleur X11 designe la meme teinte dans les deux moteurs.
check(sonde.get("hex", {}).get("darkGreen") ==
      "#%02x%02x%02x" % tuple(c // 257 for c in racine.winfo_rgb("darkGreen")),
      "darkGreen vaut la meme teinte chez Tk et chez Qt",
      (sonde.get("hex", {}).get("darkGreen"), racine.winfo_rgb("darkGreen")))

# ── 7. le panneau de proprietes ──────────────────────────────────────────
print("=== 7. le panneau de proprietes ===")
top, v = fenetre("couleurs-panneau")
v.load_new_ui_file(COLORE)
initiales = []


def fausse_boite(**kw):
    initiales.append(kw.get("color"))
    return (None, None)   # l'eleve annule : rien n'est ecrit


def descendants(w):
    """Les widgets d'un sous-arbre, dans l'ordre ou Tk les a empiles : la
    liste des boutons du panneau depend de cet ordre."""
    file, sortis = [w], []
    while file:
        x = file.pop(0)
        sortis.append(x)
        file.extend(x.winfo_children())
    return sortis


vraie_boite = UIViewer.colorchooser.askcolor
UIViewer.colorchooser.askcolor = fausse_boite
try:
    v._select(index_de(v, "vert"))
    top.update()
    cases = [w for w in descendants(v.prop_frame)
             if isinstance(w, tk.Label) and str(w.cget("width")) == "3"]
    check(any(w.cget("bg") == "#008000" for w in cases),
          "le cache de couleur du panneau montre la teinte traduite",
          [w.cget("bg") for w in cases])
    affichees = [w.cget("text") for w in descendants(v.prop_frame)
                 if isinstance(w, tk.Label)
                 and "Courier" in str(w.cget("font"))
                 and w.cget("fg") == UIViewer.PROP_FG]
    check("#008000" in affichees,
          "et le texte du panneau est une valeur que Tk accepte", affichees)

    boutons = [w for w in descendants(v.prop_frame)
               if isinstance(w, tk.Label) and w.cget("text") == " ... "]
    check(len(boutons) == 2, "deux boutons de choix de couleur", len(boutons))
    sheet_avant = v.widgets_data[index_de(v, "vert")][1]["styleSheet"]
    for b in boutons:
        b.event_generate("<Button-1>")
        top.update()
    check(len(initiales) == 2,
          "la boite s'est ouverte sur une couleur pour chaque champ",
          initiales)
    check(all(c is None or leve(lambda c=c: racine.winfo_rgb(c)) is None
              for c in initiales),
          "la couleur de depart de la boite est toujours affichable",
          initiales)
    check(initiales == ["#008000", None],
          "le texte est vert, le fond reste a la teinte du widget", initiales)
    check(v.widgets_data[index_de(v, "vert")][1]["styleSheet"] == sheet_avant,
          "annuler la boite ne change rien au fichier")

    # un widget sans couleur : la boite s'ouvre quand meme, sur rien
    initiales.clear()
    v._select(index_de(v, "degrade"))
    top.update()
    for b in [w for w in descendants(v.prop_frame)
              if isinstance(w, tk.Label) and w.cget("text") == " ... "]:
        b.event_generate("<Button-1>")
        top.update()
    check(initiales == [None, None],
          "un widget sans couleur utilisable ouvre la boite sur rien",
          initiales)
finally:
    UIViewer.colorchooser.askcolor = vraie_boite

UiViewerPlugin._parse_ss = sans_correctif
panneau_plante = None
top4, v4 = fenetre("couleurs-avant-panneau")
try:
    v4.load_new_ui_file(COLORE)
    v4._select(index_de(v4, "vert"))
    v4._show_properties(index_de(v4, "vert"))
    top4.update()
except Exception as e:
    panneau_plante = type(e).__name__ + ": " + str(e)
finally:
    avec_correctif()
    top4.destroy()
check("TclError" in str(panneau_plante),
      "avant le correctif, le panneau de proprietes craquait aussi",
      panneau_plante)
top.destroy()

# ── 8. choisir une couleur ne doit jeter aucune voisine ──────────────────
print("=== 8. le choix d'une couleur respecte les voisines ===")
# Item 11. `_set_color` filtrait les declarations existantes avec
# `css_prop + ":" not in l`, or « color: » est une sous-chaine de
# « background-color: » : choisir une couleur de texte supprimait le fond de
# l'eleve — et, dans l'autre sens, emportait « alternate-background-color »,
# « selection-color » ou « border-color ». Le fixture porte donc les deux sens,
# une ecriture en majuscules avec espace avant les deux-points, et un bloc
# « QPushButton { … } » que le modele ne sait pas reecrire.
HOSTILE = os.path.join(HERE, "gen_couleurs_voisines.ui")
PIKEE = os.path.join(HERE, "gen_couleurs_picked.ui")
VOISINES = {
    "nomme": "color: darkGreen; background-color: wheat;",
    "lesdeux": "color: navy; background-color: wheat;",
    "voisines": ("selection-color: green; border-color: blue; "
                 "alternate-background-color: yellow; color: red;"),
    "casse": "COLOR : navy; BACKGROUND-COLOR: wheat ;",
    "bloc": "QPushButton { color: red; background-color: yellow; }",
    # une valeur qui contient elle-meme des deux-points : couper au dernier
    # deux-points prendrait le nom du coté de la valeur, et l'ancienne couleur
    # resterait dans la feuille en meme temps que la nouvelle.
    "degrade": ("color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                "stop:0 #ee00ee, stop:1 #00ee00); background-color: wheat;"),
}

VOISINES_UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="geometry"><rect><x>0</x><y>0</y><width>420</width><height>460</height></rect></property>
  <property name="windowTitle"><string>Voisines</string></property>
%s </widget>
 <resources/>
 <connections/>
</ui>
'''


def un_widget(nom, sheet, y):
    return ('  <widget class="QPushButton" name="%s">\n'
            '   <property name="geometry"><rect><x>20</x><y>%d</y>'
            '<width>220</width><height>40</height></rect></property>\n'
            '   <property name="text"><string>%s</string></property>\n'
            '   <property name="styleSheet"><string notr="true">%s</string>'
            '</property>\n  </widget>\n' % (nom, y, nom, sheet))


open(HOSTILE, "w", encoding="utf-8").write(
    VOISINES_UI % "".join(un_widget(n, s, 20 + 70 * i)
                          for i, (n, s) in enumerate(VOISINES.items())))


def feuille(vue, nom):
    return vue.widgets_data[index_de(vue, nom)][1]["styleSheet"]


def nom_de(ligne):
    """L'oracle du suite : le nom de la propriete, sans les espaces ni la casse.

    Reecrit ici plutot qu'emprunte au produit : une attente calculee par le code
    sous test est un detecteur de mutant qui ne peut pas echouer.
    """
    return ligne.split(":", 1)[0].strip().lower()


def nb_declarations(sheet, prop):
    return sum(1 for l in sheet.split(";") if l.strip() and nom_de(l) == prop)


def ancienne_set_color(sheet, prop, couleur):
    """Ce que faisait le produit avant l'item 11, rejoue tel quel."""
    lignes = [l for l in sheet.split(";") if l.strip() and prop + ":" not in l]
    lignes.append("%s: %s" % (prop, couleur))
    return "; ".join(lignes) + ";"


demandees = []


def boite_qui_repond(couleur):
    def _boite(**kw):
        demandees.append(kw.get("color"))
        return (None, couleur)
    return _boite


def clique(vue, top, nom, champ, couleur):
    """Le vrai geste de l'eleve : le bouton « ... » du panneau, champ 0 = texte."""
    vue._select(index_de(vue, nom))
    top.update()
    boutons = [w for w in descendants(vue.prop_frame)
               if isinstance(w, tk.Label) and w.cget("text") == " ... "]
    vraie = UIViewer.colorchooser.askcolor
    UIViewer.colorchooser.askcolor = boite_qui_repond(couleur)
    try:
        boutons[champ].event_generate("<Button-1>")
        top.update()
    finally:
        UIViewer.colorchooser.askcolor = vraie
    return len(boutons)


top8, v8 = fenetre("couleurs-voisines")
v8.load_new_ui_file(HOSTILE)
check([p["styleSheet"] for _c, p in v8.widgets_data] == list(VOISINES.values()),
      "les six feuilles sont lues telles qu'ecrites",
      [p["styleSheet"] for _c, p in v8.widgets_data])
# Le meme nom de propriete pris pour un autre, cote lecture : la section 2 le
# verifie sur le traducteur, ici c'est ce que Tk peint vraiment sous les yeux.
fg0, bg0 = apercu(v8, "voisines")
check("yellow" not in bg0 and "blue" not in bg0,
      "alternate-background-color et border-color ne colorent pas le widget",
      (sorted(fg0), sorted(bg0)))
check("green" not in fg0, "selection-color n'est pas la couleur du texte",
      sorted(fg0))
check("red" in fg0, "et la vraie couleur du texte est bien lue",
      (sorted(fg0), sorted(bg0)))

# Le defect, prouve par la mesure et non par le raisonnement.
avant_ancien = ancienne_set_color(VOISINES["nomme"], "color", "#123456")
check("background-color" not in avant_ancien,
      "avant le correctif, choisir le texte detruisait le fond", avant_ancien)
check("alternate-background-color" not in
      ancienne_set_color(VOISINES["voisines"], "background-color", "#00ff00"),
      "et choisir le fond detruisait alternate-background-color")

# 8a. le geste de l'eleve, dans le sens qui faisait le menage.
check(clique(v8, top8, "nomme", 0, "#123456") == 2,
      "deux champs de couleur pour ce widget")
check(demandees == ["darkGreen"],
      "la boite s'est ouverte sur la couleur du texte, dans l'ordre du panneau",
      demandees)
s = feuille(v8, "nomme")
check("background-color: wheat" in s,
      "choisir le texte laisse le fond de l'eleve en place", s)
check("darkGreen" not in s and "color: #123456" in s,
      "et remplace bien l'ancienne couleur du texte", s)
check(nb_declarations(s, "color") == 1,
      "une seule declaration color, pas une pile", s)
fg, bg = apercu(v8, "nomme")
check("#123456" in fg and "wheat" in bg,
      "l'apercu montre le texte choisi et le fond conserve", (sorted(fg), sorted(bg)))

demandees.clear()
clique(v8, top8, "nomme", 1, "#00ff00")
check(demandees == ["wheat"],
      "le panneau rouvre le champ du fond sur la teinte qu'il vient de garder",
      demandees)
s = feuille(v8, "nomme")
check("color: #123456" in s,
      "choisir le fond laisse le texte deja choisi", s)
check(nb_declarations(s, "background-color") == 1,
      "le fond est remplace, pas ajoute", s)

# 8b. le geste ecrit une feuille canonique, et un second clic identique est
#     un sans-faute : ni le texte ni le drapeau ne bougent.
clique(v8, top8, "lesdeux", 0, "#123456")
s = feuille(v8, "lesdeux")
check(s == "background-color: wheat; color: #123456;",
      "la feuille attendue, ecrite sans espaces trainants", s)
v8._travail_modifie = False
clique(v8, top8, "lesdeux", 0, "#123456")
check(feuille(v8, "lesdeux") == s,
      "choisir la couleur deja ecrite ne change rien a la feuille",
      feuille(v8, "lesdeux"))
check(v8._travail_modifie is False,
      "et ne leve pas le drapeau de travail non plus")

# 8c. les voisines dont le nom contient « color ».
clique(v8, top8, "voisines", 0, "#123456")
s = feuille(v8, "voisines")
for voisine in ("selection-color: green", "border-color: blue",
                "alternate-background-color: yellow"):
    check(voisine in s, "%s survit au choix du texte" % voisine, s)
check("color: red" not in s and "color: #123456" in s,
      "la seule changee est la declaration plate du texte", s)
clique(v8, top8, "voisines", 1, "#00ff00")
s = feuille(v8, "voisines")
check("alternate-background-color: yellow" in s and "selection-color: green" in s,
      "le choix du fond laisse les proprietes qui finissent par -color", s)
check(nb_declarations(s, "background-color") == 1,
      "et n'ecrit qu'une declaration de fond", s)

# 8d. la casse et les espaces ne trompent pas le remplacement.
clique(v8, top8, "casse", 0, "#123456")
s = feuille(v8, "casse")
check(nb_declarations(s, "color") == 1,
      "une ecriture en majuscules est remplacee, pas doublee", s)
check("BACKGROUND-COLOR: wheat" in s,
      "et le fond ecrit en majuscules reste intact", s)

# 8d bis. une valeur qui contient elle-meme des deux-points : le nom s'arrete
#     au premier deux-points, pas au dernier.
clique(v8, top8, "degrade", 0, "#123456")
s = feuille(v8, "degrade")
check(nb_declarations(s, "color") == 1,
      "une valeur pleine de deux-points est remplacee, pas doublee", s)
check("qlineargradient" not in s and "background-color: wheat" in s,
      "le degrade cede la place et le fond de l'eleve reste", s)

# 8e. un bloc : le modele ne sait pas reecrire l'interieur, mais ne jette rien.
clique(v8, top8, "bloc", 0, "#123456")
s = feuille(v8, "bloc")
check(VOISINES["bloc"] in s, "le bloc de l'eleve ressort mot pour mot", s)
check(s.count("{") == s.count("}") == 1,
      "et ses accolades restent equilibrees : la feuille est toujours legale", s)
check(nb_declarations(s, "color") == 1,
      "le panneau n'ajoute que sa propre declaration plate", s)

# 8f. le journal rend la feuille complete, voisines comprises.
avant = feuille(v8, "lesdeux")
clique(v8, top8, "lesdeux", 0, "#eeeeee")
check(feuille(v8, "lesdeux") != avant, "le choix est journalise")
v8.undo()
check(feuille(v8, "lesdeux") == avant,
      "Annuler rend la feuille telle qu'elle etait, fond compris",
      feuille(v8, "lesdeux"))
v8.redo()
check("color: #eeeeee" in feuille(v8, "lesdeux")
      and "background-color: wheat" in feuille(v8, "lesdeux"),
      "Retablir remet la couleur choisie sans rien retirer d'autre",
      feuille(v8, "lesdeux"))

# 8g. le fichier, pas seulement le modele.
v8.undo()
v8.ui_file = PIKEE
dialogues.clear()
leve(lambda: v8._save())
texte = open(PIKEE, encoding="utf-8").read()
# Les widgets du fichier sont les enfants du <widget> racine, pas des enfants
# de <ui> : findall("widget") sur la racine ne renverrait que le formulaire.
form = ET.parse(PIKEE).getroot().find("widget")
ecrites = dict((w.get("name"),
                (w.find("property[@name='styleSheet']/string").text or ""))
               for w in form.findall("widget")
               if w.find("property[@name='styleSheet']") is not None)
for nom in VOISINES:
    check(ecrites.get(nom) == feuille(v8, nom),
          "%s : le fichier rend exactement la feuille du modele" % nom,
          (ecrites.get(nom), feuille(v8, nom)))
check("COLOR : navy" not in texte and "BACKGROUND-COLOR: wheat" in texte,
      "la feuille en majuscules a ete remplacee sans perdre son fond")
top9, v9 = fenetre("couleurs-voisines-reouverte")
leve(lambda: v9.load_new_ui_file(PIKEE))
check(apercu(v9, "lesdeux") == apercu(v8, "lesdeux"),
      "reouvrir le fichier montre les memes deux couleurs",
      (apercu(v9, "lesdeux"), apercu(v8, "lesdeux")))
check("selection-color: green" in feuille(v9, "voisines")
      and "alternate-background-color: yellow" in feuille(v9, "voisines"),
      "les voisines exotiques sont revenues avec le fichier",
      feuille(v9, "voisines"))
top9.destroy()
top8.destroy()

# 8h. la cible : le produit compare bien des noms de propriete.
source = open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
check("css_prop + \":\" not in l" not in source,
      "cible : le filtre par sous-chaine a disparu du produit")
check("def _nom_de_declaration" in source
      and "self._nom_de_declaration(l) != css_prop" in source,
      "cible : la comparaison porte sur le nom de la declaration")

print()
print("%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)
