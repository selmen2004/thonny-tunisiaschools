r"""Item 7 (re-audit) : « Nouveau » ne doit rien laisser de la fenetre d'avant.

Le defaut etait dans les champs que seul le lecteur connait. `load_new_ui_file`
pose quatre choses quand un fichier est lu : les widgets, l'arbre XML, la
graine de numerotation — et l'identite de la fenetre : `root_widget_name`,
`root_widget_class`, `root_title`. « Nouveau » vidait les trois premieres et
oubliait la derniere. L'eleve voyait donc un canevas vide, un onglet
« Sans titre », et enregistrait neanmoins <class>MainWindow</class>, une
<widget class="QMainWindow" name="Gestion"> portant le titre
« Gestion des eleves » du projet precedent (mesure, section 3 et 6). Le pire
n'etait pas le nom herite : la taille, elle, etait bien remise a 640x480, donc
le fichier decrivait une fenetre qui n'existe nulle part — et un QMainWindow
sans centralwidget des que l'eleve y posait un bouton.

Le deuxieme symptome est sous la main de l'eleve : le panneau de proprietes
n'etait jamais lache. Apres « Nouveau », il affichait encore les vingt-trois
champs du widget supprime, « Nom » rempli de btnQuitter ; y taper un nom
changeait ce que la boite affichait sans rien ecrire nulle part — le modele
etait vide et `_apply` avalait l'IndexError en silence.

La regle verifiee ici est double : un document neuf doit ressembler octet pour
octet a ce que produirait une vue qui n'a jamais rien lu (l'oracle), et tout ce
que la lecture ecrit doit etre remis par « Nouveau » — y compris les champs
qu'un futur lecteur apprendra (section 8, par recensement AST).
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import types
from xml.etree import ElementTree as ET

import chemins

BUNDLE = chemins.BUNDLE
# TUNISIASCHOOLS_COPIE : le dossier d'une COPIE mutee du module, pose par
# tests\mutants_nouveau.py. Sans lui, c'est le module livre qui est teste.
PLUGIN = os.environ.get("TUNISIASCHOOLS_COPIE") or \
    chemins.PAQUET
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BUNDLE, "Lib", "site-packages")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")
sys.path.insert(0, SITE)
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tkinter as tk                                   # noqa: E402
import UIViewer                                        # noqa: E402
from UIViewer import UiViewerPlugin                    # noqa: E402

CHEMIN_SOURCE = getattr(UIViewer, "__file__",
                        os.path.join(PLUGIN, "UIViewer.py"))
source = open(CHEMIN_SOURCE, encoding="utf-8").read()

dialogues = []
reponse = [True]
chemin_a_enregistrer = [""]

UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: dialogues.append(("error",) + a),
    showinfo=lambda *a, **k: dialogues.append(("info",) + a),
    askyesno=lambda *a, **k: (dialogues.append(("yesno",) + a), reponse[0])[1],
    askyesnocancel=lambda *a, **k: (dialogues.append(("yesnocancel",) + a),
                                    reponse[0])[1])
UIViewer.filedialog = types.SimpleNamespace(
    askopenfilename=lambda **k: "",
    asksaveasfilename=lambda **k: chemin_a_enregistrer[0])
UIViewer.get_workbench = lambda: None

racine = tk.Tk()
racine.withdraw()

D = os.path.join(HERE, "_sortie", "nouveau")
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)


def CHEMIN(nom):
    return os.path.join(D, nom)


GESTION_UI = r'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Gestion</class>
 <widget class="QMainWindow" name="Gestion">
  <property name="geometry"><rect><x>100</x><y>60</y><width>520</width><height>400</height></rect></property>
  <property name="windowTitle"><string>Gestion des eleves</string></property>
  <widget class="QWidget" name="centralwidget">
   <layout class="QVBoxLayout" name="colonne">
    <item>
     <widget class="QPushButton" name="btnQuitter">
      <property name="text"><string>Quitter</string></property>
     </widget>
    </item>
   </layout>
  </widget>
 </widget>
 <resources/>
 <connections/>
</ui>
'''

SAISIE_UI = r'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Boite</class>
 <widget class="QDialog" name="BoiteSaisie">
  <property name="geometry"><rect><x>0</x><y>0</y><width>300</width><height>150</height></rect></property>
  <property name="windowTitle"><string>Saisie des mots</string></property>
  <widget class="QLineEdit" name="champ">
   <property name="geometry"><rect><x>20</x><y>20</y><width>200</width><height>26</height></rect></property>
   <property name="placeholderText"><string>Le mot</string></property>
  </widget>
 </widget>
</ui>
'''


def ecrit(nom, texte):
    p = CHEMIN(nom)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)
    return p


GESTION = ecrit("gestion.ui", GESTION_UI)
SAISIE = ecrit("saisie.ui", SAISIE_UI)

bilan = [0, 0]
a_l_envers = []


def check(*a):
    """(libelle, condition, detail) — l'ordre officiel du depot ; le controle
    final refuse toute suite ecrite a l'envers (voir test_travail.py)."""
    if isinstance(a[0], str):
        cond, msg, detail = a[1], a[0], (a[2] if len(a) > 2 else None)
    else:
        cond, msg, detail = a[0], a[1], (a[2] if len(a) > 2 else None)
        a_l_envers.append("ligne %d : %s" % (sys._getframe(1).f_lineno, msg))
    bilan[0] += 1
    print(("  OK   " if cond else "  FAIL ") + msg +
          ("" if cond or detail is None else "  [%s]" % (detail,)))
    if not cond:
        bilan[1] += 1


fenetres = []


def fenetre(nom):
    top = tk.Toplevel(racine)
    top.title(nom)
    top.geometry("980x680+30+30")
    top.update()
    v = UiViewerPlugin(top)
    v.pack(fill=tk.BOTH, expand=True)
    top.update()
    fenetres.append(top)
    return top, v


def octets(chemin):
    with open(chemin, "rb") as f:
        return f.read()


ABSENT = "<attribut jamais pose>"


def champ(v, nom):
    """Un champ de l'identite. Un mutant qui retire l'assignation de la
    definition du document neuf ne doit pas faire planter la suite : l'attribut
    absent devient une valeur qui ne ressemble a rien d'attendu, donc un
    controle rouge (la lecon des suites precedentes : echouer, pas crasher)."""
    return getattr(v, nom, ABSENT)


def identite(v):
    """Les quatre champs que la lecture pose et que « Nouveau » doit remettre."""
    taille = champ(v, "root_geometry")
    try:
        taille = tuple(taille)
    except TypeError:
        pass
    return (champ(v, "root_widget_name"), champ(v, "root_widget_class"),
            champ(v, "root_title"), taille)


def libelle(w):
    """Le texte affiche par un widget Tk. Le panneau de proprietes est rempli
    de champs et de cadres qui n'ont pas d'option « text » — c'est justement ce
    que laisse un « Nouveau » qui ne lache pas le panneau, donc lire ici ne doit
    pas planter non plus."""
    try:
        return w.cget("text")
    except tk.TclError:
        return "<%s sans texte>" % type(w).__name__


def remplit(v, nom, valeur):
    """Tape dans un champ du panneau s'il existe, et dit s'il existait."""
    var = v._prop_vars.get(nom)
    if var is not None:
        var.set(valeur)
    v.update()
    return var is not None


def entetes(chemin):
    """Ce que le fichier dit de SA fenetre : <class>, nom, classe, titre."""
    rac = ET.parse(chemin).getroot()
    form = rac.find("widget")
    titre = None
    if form is not None:
        for p in form.findall("property"):
            if p.get("name") == "windowTitle":
                s = p.find("string")
                titre = None if s is None else s.text
    cls = rac.find("class")
    return {"<class>": None if cls is None else cls.text,
            "name": None if form is None else form.get("name"),
            "class": None if form is None else form.get("class"),
            "windowTitle": titre}


SONDE_QT = r'''
import json, os, sys
sys.path.insert(0, @@SITE@@)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5 import QtWidgets, uic
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
try:
    w = uic.loadUi(@@FICHIER@@)
except Exception as e:
    print(json.dumps({"erreur": type(e).__name__ + ": " + str(e)[:180]}))
    sys.exit(0)
w.show()
r = {"cls": w.metaObject().className(), "nom": w.objectName(),
     "titre": w.windowTitle()}
if hasattr(w, "centralWidget"):
    cw = w.centralWidget()
    r["centralWidget"] = None if cw is None else cw.objectName()
else:
    r["centralWidget"] = "non QMainWindow"
trouves = {}
for nom in @@NOMS@@:
    o = getattr(w, nom, None)
    trouves[nom] = None if o is None else {
        "cls": o.metaObject().className(),
        "texte": o.text() if hasattr(o, "text") else "",
        "parent": None if o.parentWidget() is None
                  else o.parentWidget().metaObject().className()}
r["objets"] = trouves
r["layout"] = None if w.layout() is None else w.layout().objectName()
print(json.dumps(r, ensure_ascii=False))
'''


def mesure_qt(chemin, noms=()):
    if not os.path.exists(chemin):
        return {"erreur": "aucun fichier ecrit : rien que Qt puisse construire"}
    script = (SONDE_QT.replace("@@SITE@@", repr(SITE))
                      .replace("@@FICHIER@@", repr(chemin))
                      .replace("@@NOMS@@", repr(sorted(set(noms)))))
    try:
        p = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", "-c",
                            script], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=ENV,
                           timeout=180)
    except subprocess.TimeoutExpired:
        return {"erreur": "le fils n'a pas rendu la main"}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"erreur": ((p.stdout or "")[-150:] +
                           (p.stderr or "")[-250:])}


# L'oracle : ce qu'ecrit une vue qui n'a JAMAIS rien lu. Tout ce que « Nouveau »
# produit doit se comparer a la, sinon la suite certifierait un choix invente.
top0, VIERGE = fenetre("nouveau-oracle")
ORACLE = CHEMIN("oracle.ui")
VIERGE._write_ui_file(ORACLE)
IDENTITE_ORACLE = identite(VIERGE)
ENTETES_ORACLE = entetes(ORACLE)

print("\n=== 1. la lecture pose bien l'identite du fichier ===")
# Sans cette section, tout le reste pourrait etre vert sans rien tester : si le
# lecteur ne posait pas « Gestion », « Nouveau » n'aurait rien a heriter.
top1, v1 = fenetre("nouveau-lecture")
v1.load_new_ui_file(GESTION)
check("le fichier lu a bien un nom de fenetre qui n'est pas celui d'un document neuf",
      identite(v1)[0] == "Gestion", identite(v1)[0])
check("et une classe qui n'est pas celle d'un document neuf",
      identite(v1)[1] == "QMainWindow", identite(v1)[1])
check("et un titre qui n'est pas celui d'un document neuf",
      identite(v1)[2] == "Gestion des eleves", identite(v1)[2])
check("et une taille qui n'est pas celle d'un document neuf",
      identite(v1)[3] == (100, 60, 520, 400), identite(v1)[3])
check("l'identite lue differe donc de l'oracle sur les quatre champs",
      identite(v1) != IDENTITE_ORACLE, identite(v1))
check("le modele tient le bouton du fichier",
      [p.get("name") for _c, p in v1.widgets_data] == ["btnQuitter"],
      [p.get("name") for _c, p in v1.widgets_data])
check("le nom de la mise en page est sorti du fichier, pas du modele",
      "colonne" in [el.get("name") for el in (v1._source_ui.iter("layout"))]
      if v1._source_ui is not None else False)

print("\n=== 2. Nouveau remet l'identite de la fenetre a zero ===")
# l'eleve a joue avec le fichier lu : la numerotation a avance, donc « Nouveau »
# a quelque chose a remettre (sinon le controle du compteur serait faux positif)
v1._add_widget("QPushButton")
v1._duplicate(len(v1.widgets_data) - 1)
compte_avant = v1.widget_counter
check("la numerotation a bien avance avant « Nouveau »", compte_avant >= 1,
      compte_avant)
v1._new()
check("le nom de la fenetre repart a Form",
      identite(v1)[0] == "Form", identite(v1)[0])
check("la classe repart a celui d'un document neuf",
      identite(v1)[1] == IDENTITE_ORACLE[1], identite(v1)[1])
check("le titre repart a Form, pas a « Gestion des eleves »",
      identite(v1)[2] == "Form", identite(v1)[2])
check("la taille repart a la taille par defaut",
      identite(v1)[3] == IDENTITE_ORACLE[3], identite(v1)[3])
check("les quatre champs sont exactement ceux de l'oracle",
      identite(v1) == IDENTITE_ORACLE, identite(v1))
check("l'onglet est « Sans titre »",
      v1._title_lbl.cget("text") == "Sans titre", v1._title_lbl.cget("text"))
check("aucun widget au modele", v1.widgets_data == [], v1.widgets_data)
check("plus de fichier attache", v1.ui_file is None, v1.ui_file)
check("plus d'arbre XML", v1._source_ui is None, type(v1._source_ui).__name__)
check("plus de reperes de la racine lue", v1._src_root == {}, v1._src_root)
check("plus d'uids", v1._source_uids == [], v1._source_uids)
check("la numerotation repart de zero", v1.widget_counter == 0,
      v1.widget_counter)
check("et la selection aussi", v1.selected_idx is None, v1.selected_idx)

print("\n=== 3. le document d'apres Nouveau s'ecrit comme un document neuf ===")
APRES = CHEMIN("apres_nouveau.ui")
v1._write_ui_file(APRES)
check("octet pour octet identique a ce qu'ecrit une vue qui n'a rien lu",
      octets(APRES) == octets(ORACLE),
      [len(octets(APRES)), len(octets(ORACLE))])
check("le fichier ne contient plus le nom du projet d'avant",
      b"Gestion" not in octets(APRES))
check("ni son titre", b"Gestion des eleves" not in octets(APRES))
check("ni sa classe", b"MainWindow" not in octets(APRES))
check("ni le nom de son widget", b"btnQuitter" not in octets(APRES))
check("ni le nom de sa mise en page", b"colonne" not in octets(APRES))
check("entetes : la classe generee est celle d'un document neuf",
      entetes(APRES)["<class>"] == ENTETES_ORACLE["<class>"],
      entetes(APRES))
check("entetes : le nom de la racine est Form",
      entetes(APRES)["name"] == "Form", entetes(APRES))
check("entetes : la classe de la racine est celle de l'oracle",
      entetes(APRES)["class"] == ENTETES_ORACLE["class"], entetes(APRES))
check("entetes : le titre est Form",
      entetes(APRES)["windowTitle"] == "Form", entetes(APRES))
# et avec un widget pose dessus : les deux documents neufs doivent rester
# jumeaux, sinon l'heritage se cache dans l'ecriture des ajouts
jumeau = CHEMIN("apres_nouveau_avec_bouton.ui")
v1._add_widget("QPushButton")
v1._write_ui_file(jumeau)
VIERGE._add_widget("QPushButton")
ORACLE_BOUTON = CHEMIN("oracle_avec_bouton.ui")
VIERGE._write_ui_file(ORACLE_BOUTON)
check("un bouton pose apres Nouveau porte le meme nom que sur un document neuf",
      [p.get("name") for _c, p in v1.widgets_data] ==
      [p.get("name") for _c, p in VIERGE.widgets_data],
      [p.get("name") for _c, p in v1.widgets_data])
check("et le fichier est encore identique octet pour octet",
      octets(jumeau) == octets(ORACLE_BOUTON),
      [len(octets(jumeau)), len(octets(ORACLE_BOUTON))])

print("\n=== 4. ce que Qt construit vraiment ===")
mesure = mesure_qt(jumeau, ["pushbutton"])
check("Qt charge le document, sans se plaindre",
      "erreur" not in mesure, mesure.get("erreur"))
check("la fenetre est celle d'un document neuf, pas un QMainWindow herite",
      mesure.get("cls") == ENTETES_ORACLE["class"], mesure.get("cls"))
check("elle s'appelle Form", mesure.get("nom") == "Form", mesure.get("nom"))
check("elle porte le titre Form", mesure.get("titre") == "Form",
      mesure.get("titre"))
check("le bouton de l'eleve est atteignable sous son nom",
      (mesure.get("objets") or {}).get("pushbutton") is not None,
      mesure.get("objets"))
check("et c'est bien un QPushButton",
      ((mesure.get("objets") or {}).get("pushbutton") or {}).get("cls") ==
      "QPushButton", (mesure.get("objets") or {}).get("pushbutton"))
check("il est porte par la fenetre neuve, pas par un resto du fichier d'avant",
      ((mesure.get("objets") or {}).get("pushbutton") or {}).get("parent") ==
      ENTETES_ORACLE["class"],
      ((mesure.get("objets") or {}).get("pushbutton") or {}).get("parent"))

# Le temoin oppose : rejouer l'ancien « Nouveau » (qui ne remettait rien) et
# laisser Qt le construire. C'est la mesure qui a declenche l'item.
def nouveau_a_l_ancienne(v):
    v.widgets_data.clear()
    v.ui_file = None
    v.widget_counter = 0
    v.selected_idx = None
    v.root_geometry = (0, 0, 640, 480)
    v._source_ui = None
    v._source_uids = []
    v._src_root = {}
    v.reset_history()
    v._title_lbl.config(text="Sans titre")
    v._refresh()


top2, v2 = fenetre("nouveau-temoin")
v2.load_new_ui_file(GESTION)
v2._select(0)
nouveau_a_l_ancienne(v2)
temoin = CHEMIN("temoin_ancien.ui")
v2._add_widget("QPushButton")
v2._write_ui_file(temoin)
check("l'ancien « Nouveau » ecrivait bien une fenetre heritee",
      entetes(temoin)["name"] == "Gestion", entetes(temoin))
check("de classe MainWindow", entetes(temoin)["<class>"] == "MainWindow",
      entetes(temoin))
check("avec le titre du projet d'avant",
      entetes(temoin)["windowTitle"] == "Gestion des eleves", entetes(temoin))
ancien_mesure = mesure_qt(temoin, ["pushbutton"])
check("Qt le construit, mais en QMainWindow sans centralwidget : la forme "
      "que Designer ne produit jamais",
      ancien_mesure.get("cls") == "QMainWindow" and
      ancien_mesure.get("centralWidget") is None,
      {k: ancien_mesure.get(k) for k in ("cls", "centralWidget", "erreur")})
check("le controle porte : le document neuf, lui, n'est pas un QMainWindow",
      mesure.get("cls") != "QMainWindow", mesure.get("cls"))

print("\n=== 5. le panneau de proprietes lache le widget d'avant ===")
top3, v3 = fenetre("nouveau-panneau")
v3.load_new_ui_file(GESTION)
v3._select(0)
check("avant : le panneau tient le bouton lu",
      v3._name_entry is not None and v3._name_entry.get() == "btnQuitter",
      None if v3._name_entry is None else v3._name_entry.get())
check("avant : dix champs d'edition sont branches sur le widget",
      len(v3._prop_vars) == 10, sorted(v3._prop_vars))
v3._new()
check("apres Nouveau : plus de champ « Nom »",
      v3._name_entry is None, None if v3._name_entry is None
      else v3._name_entry.get())
check("plus aucun var branchee sur un widget mort",
      v3._prop_vars == {}, sorted(v3._prop_vars))
check("plus de message d'erreur de nom", v3._name_hint is None,
      type(v3._name_hint).__name__)
enfants = v3.prop_frame.winfo_children()
check("le panneau est revenu a son invitation a cliquer",
      len(enfants) == 1 and "Cliquez" in libelle(enfants[0]),
      [libelle(e)[:24] for e in enfants])
check("le canevas non plus ne montre rien",
      v3.ui_frame.winfo_children() == [], len(v3.ui_frame.winfo_children()))
# et l'ancien comportement, mesure : le champ orphelin survivait
v3.load_new_ui_file(GESTION)
v3._select(0)
nouveau_a_l_ancienne(v3)
orphelin = v3._name_entry is not None
contenu = None if not orphelin else v3._name_entry.get()
if orphelin:
    remplit(v3, "name", "boutonEleve")
ecrit_apres_ancien = CHEMIN("ancien_sans_panneau.ui")
v3._write_ui_file(ecrit_apres_ancien)
check("l'ancien « Nouveau » laissait le champ Nom affiche, plein du widget mort",
      orphelin and contenu == "btnQuitter", (orphelin, contenu))
check("la frappe de l'eleve ne partait nulle part : le modele est reste vide",
      orphelin and v3.widgets_data == [], v3.widgets_data)
check("et le fichier n'avait rien de son nom tape",
      b"boutonEleve" not in octets(ecrit_apres_ancien))
check("le controle n'est pas creux : c'est bien le champ qui a ete rempli",
      orphelin, orphelin)

print("\n=== 6. Nouveau ne reecrit aucun fichier ===")
top4, v4 = fenetre("nouveau-disque")
v4.load_new_ui_file(GESTION)
sur_disque = CHEMIN("sur_disque.ui")
v4.ui_file = sur_disque
v4._write_ui_file(sur_disque)
_avant = octets(sur_disque)
carte_avant = sorted(os.listdir(D))
v4._select(0)
remplit(v4, "text", "Partir")
v4._new()
check("le fichier precedemment enregistre est intact",
      octets(sur_disque) == _avant,
      [len(octets(sur_disque)), len(_avant)])
check("et « Nouveau » n'a ecrit aucun nouveau fichier en passant",
      sorted(os.listdir(D)) == carte_avant,
      sorted(set(os.listdir(D)) - set(carte_avant)))

print("\n=== 7. la question de l'item 13 reste posee AVANT de tout jeter ===")
top5, v5 = fenetre("nouveau-question")
v5.load_new_ui_file(GESTION)
v5._select(0)
remplit(v5, "text", "Partir")
check("le travail en cours est signale non enregistre",
      v5._travail_non_enregistre(), v5._travail_modifie)
identite_avant = identite(v5)
dialogues[:] = []
reponse[0] = False
v5._new()
check("repondre « non » laisse l'identite de la fenetre entiere",
      identite(v5) == identite_avant, identite(v5))
check("laisse ses widgets", len(v5.widgets_data) == 1, v5.widgets_data)
check("laisse le fichier qu'il etait en train de montrer",
      v5.ui_file == GESTION, v5.ui_file)
check("laisse son panneau", v5._name_entry is not None and
      v5._name_entry.get() == "btnQuitter",
      None if v5._name_entry is None else v5._name_entry.get())
check("et une seule question, pas deux",
      len([d for d in dialogues if d[0] == "yesno"]) == 1, dialogues)
check("la question est bien celle de « Nouveau »",
      any(d[0] == "yesno" and d[1] == "Nouveau" for d in dialogues),
      dialogues[:1])
dialogues[:] = []
reponse[0] = True
v5._new()
check("repondre « oui » remet toute l'identite",
      identite(v5) == IDENTITE_ORACLE, identite(v5))
check("« oui » n'a pose qu'une question",
      len([d for d in dialogues if d[0] == "yesno"]) == 1, dialogues)
dialogues[:] = []
v5._new()
check("un second Nouveau d'affilee ne demande rien",
      dialogues == [], dialogues)
check("le drapeau est retombe, un ajout le relve",
      not v5._travail_non_enregistre(), v5._travail_modifie)
v5._add_widget("QLabel")
check("donc « Nouveau » redemandera a l'eleve qui a pose un widget",
      v5._travail_non_enregistre(), v5._travail_modifie)

print("\n=== 8. tout ce que la lecture ecrit est remis par Nouveau ===")
# Le controle generalisable : un futur lecteur qui apprend un cinquieme champ a
# la racine doit etre rattrape ici, sinon l'item 7 revient sous un autre nom.
arbre = ast.parse(source)
classe = next((n for n in arbre.body if isinstance(n, ast.ClassDef)), None)
meth = ({n.name: n for n in classe.body if isinstance(n, ast.FunctionDef)}
        if classe is not None else {})


def ecrits(nom):
    """Les attributs de self que cette methode ecrit, ou None si elle a disparu."""
    noeud = meth.get(nom)
    if noeud is None:
        return None
    noms = set()
    for x in ast.walk(noeud):
        if (isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and
                x.value.id == "self" and isinstance(x.ctx, ast.Store)):
            noms.add(x.attr)
        if (isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and
                x.func.attr in ("clear", "append", "extend", "pop", "remove",
                                "update", "setdefault") and
                isinstance(x.func.value, ast.Attribute) and
                isinstance(x.func.value.value, ast.Name) and
                x.func.value.value.id == "self"):
            noms.add(x.func.value.attr)
    return noms


def appellees(nom):
    noeud = meth.get(nom)
    if noeud is None:
        return set()
    return {x.func.attr for x in ast.walk(noeud)
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and
            isinstance(x.func.value, ast.Name) and x.func.value.id == "self"}


lu_par_la_lecture = (ecrits("_parse_ui") or set()) | (ecrits("load_new_ui_file") or set())
remis = ecrits("_new") or set()
for m in appellees("_new"):
    remis |= (ecrits(m) or set())
oubli = sorted(n for n in lu_par_la_lecture if n not in remis)
check("la methode _new est toujours la, donc son controle porte",
      "_new" in meth, sorted(meth)[:6])
check("la lecture ecrit bien des champs (le controle n'est pas creux)",
      len(lu_par_la_lecture) >= 6, sorted(lu_par_la_lecture))
check("tout ce qu'un fichier pose est remis a zero par « Nouveau »",
      oubli == [], oubli)
check("les trois champs de l'item 7 sont du nombre",
      {"root_widget_name", "root_widget_class", "root_title"}
      <= lu_par_la_lecture, sorted(lu_par_la_lecture))

print("\n=== 9. une seule definition du document neuf ===")
def corps(nom):
    """Le source d'une methode, ou '' si elle a disparu : un mutant qui la
    supprime doit faire une CHECK rouge, pas une exception sans bilan."""
    noeud = meth.get(nom)
    if noeud is None:
        return ""
    return ast.get_source_segment(source, noeud) or ""


neuf = meth.get("_racine_neuve")
check("le document neuf a un endroit ou il est defini",
      neuf is not None, sorted(meth)[:8])
corps_neuve = corps("_racine_neuve")
check("et cet endroit ecrit les quatre champs",
      all(("self." + c) in corps_neuve for c in
          ("root_widget_name", "root_widget_class", "root_geometry",
           "root_title")),
      None if neuf is None else corps_neuve[:260])
check("le constructeur passe par la, il ne reecrit pas les defauts a la main",
      "_racine_neuve()" in corps("__init__"), corps("__init__")[:120])
check("« Nouveau » passe par la aussi",
      "_racine_neuve()" in corps("_new"))
check("la valeur par defaut du nom de racine n'est ecrite qu'une fois au module",
      source.count('self.root_widget_name = "Form"') == 1,
      source.count('self.root_widget_name = "Form"'))
check("et le titre par defaut non plus",
      source.count('self.root_title = "Form"') == 1,
      source.count('self.root_title = "Form"'))
corps_new = corps("_new")
check("« Nouveau » rend la main au panneau de proprietes",
      "_show_no_selection()" in corps_new, corps_new[:300])
if neuf is not None and meth.get("_new") is not None:
    ligne_garde = next((n.lineno for n in meth["_new"].body
                        if isinstance(n, ast.If)), 10 ** 6)
    ligne_neuve = next((n.lineno for n in ast.walk(meth["_new"])
                        if isinstance(n, ast.Call) and
                        isinstance(n.func, ast.Attribute) and
                        n.func.attr == "_racine_neuve"), 10 ** 6)
    check("la remise a zero vient APRES la question, pas avant",
          ligne_neuve > ligne_garde, (ligne_garde, ligne_neuve))
else:
    check("la remise a zero vient APRES la question, pas avant", False,
          "methode absente")

print("\n=== 10. deuxieme document dans la meme session ===")
top6, v6 = fenetre("nouveau-deuxieme")
v6.load_new_ui_file(GESTION)
v6._new()
v6.load_new_ui_file(SAISIE)
check("un fichier lu apres Nouveau reprend son identite a lui",
      identite(v6) == ("BoiteSaisie", "QDialog", "Saisie des mots",
                       (0, 0, 300, 150)), identite(v6))
second = CHEMIN("deuxieme_lu.ui")
v6._write_ui_file(second)
check("et son enregistrement garde les siens",
      entetes(second)["name"] == "BoiteSaisie", entetes(second))
deuxieme_nouveau = CHEMIN("deuxieme_nouveau.ui")
v6._new()
v6._write_ui_file(deuxieme_nouveau)
check("re-Nouveau remet l'identite, une seconde fois",
      identite(v6) == IDENTITE_ORACLE, identite(v6))
check("le second document neuf est identique au premier",
      octets(deuxieme_nouveau) == octets(ORACLE),
      [len(octets(deuxieme_nouveau)), len(octets(ORACLE))])
v6._new()
check("Nouveau sur un document deja neuf ne casse rien",
      identite(v6) == IDENTITE_ORACLE and v6.widgets_data == [],
      identite(v6))
trois = CHEMIN("trois_nouveau.ui")
v6._write_ui_file(trois)
check("et son fichier ne change pas au troisieme clic",
      octets(trois) == octets(ORACLE))

print("\n=== 11. l'enregistrement d'apres Nouveau est un vrai Enregistrer ===")
top7, v7 = fenetre("nouveau-enregistrer")
v7.load_new_ui_file(GESTION)
v7._select(0)
remplit(v7, "text", "Partir")
reponse[0] = True
dialogues[:] = []
CIBLE = CHEMIN("enregistre_apres_nouveau.ui")
chemin_a_enregistrer[0] = CIBLE
v7._new()
v7._add_widget("QPushButton")
v7._save()
chemin_a_enregistrer[0] = ""
check("l'enregistrement est alle au fichier que l'eleve a choisi",
      os.path.exists(CIBLE), CIBLE)
check("et ce fichier est celui d'un document neuf avec son bouton",
      octets(CIBLE) == octets(ORACLE_BOUTON), entetes(CIBLE))
check("l'onglet porte desormais le nom du nouveau fichier",
      v7._title_lbl.cget("text") == os.path.basename(CIBLE),
      v7._title_lbl.cget("text"))
check("rien du projet d'avant n'a suivi",
      b"Gestion" not in octets(CIBLE) and b"Quitter" not in octets(CIBLE))
check("le travail vient d'etre ecrit : plus rien a prevenir",
      not v7._travail_non_enregistre(), v7._travail_modifie)
mesure_enregistree = mesure_qt(CIBLE, ["pushbutton"])
check("Qt le charge et y trouve le bouton",
      "erreur" not in mesure_enregistree and
      (mesure_enregistree.get("objets") or {}).get("pushbutton") is not None,
      mesure_enregistree.get("erreur"))

print("\n=== 12. rien de visible ne subsite de l'edition precedente ===")
check("le texte du widget lu n'est plus dans le panneau",
      v7._prop_vars.get("text") is None or
      v7._prop_vars.get("text").get() != "Partir",
      None if v7._prop_vars.get("text") is None
      else v7._prop_vars.get("text").get())
check("il porte a la place le nom du widget que l'eleve a pose ici",
      v7._prop_vars.get("name") is not None and
      v7._prop_vars["name"].get() == "pushbutton",
      None if v7._prop_vars.get("name") is None
      else v7._prop_vars["name"].get())
check("le modele n'a que ce widget-la",
      [p.get("name") for _c, p in v7.widgets_data] == ["pushbutton"],
      [p.get("name") for _c, p in v7.widgets_data])
check("aucun QMessageBox dans l'editeur visuel", "QMessageBox" not in source)

for top in fenetres:
    top.destroy()
racine.update()

check("aucun controle de cette suite n'est ecrit dans l'autre sens",
      a_l_envers == [], a_l_envers)

print("\n%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)
