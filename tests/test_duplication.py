r"""Item 14 : « Dupliquer » ne doit jamais cesser de rendre la main.

Le geste est anodin : un clic sur « Dupliquer » dans le panneau de proprietes.
`_duplicate` confie a `_unique_name` la base du nom copie
(`props["name"].rstrip("0123456789")`), et la fabrique cherchait un suffixe
jusqu'a ce que le nom soit valide. Or la validite melait deux questions sous un
seul test : la FORME et le statut reserve. Un mot reserve se repare avec un
chiffre (« class1 » passe), un tiret jamais — « mon-bouton1 », « mon-bouton2 »,
... contiennent tous le « - » refuse. La boucle demandait l'impossible et ne
rendait plus la main : le fil principal de Thonny etait avale, sans message, sans
trace, sans CPU libre pour repeindre l'ecran.

Ce nom n'arrivait pas par le panneau, qui refuse deja les deux formes : il venait
du FICHIER. Un `<widget name="mon-bouton">` ecrit a la main (ou par un autre
editeur) entre dans le modele tel quel. Cinq bases sur les neuf testees ici y
passaient.

La reparation se fait en deux temps, et la suite pousse les deux :

  • la forme est testee une seule fois, par `_forme_valide`, et la base est
    reparee AVANT la recherche par `_base_reparee` ; il ne reste a la boucle
    qu'a ajouter des chiffres, ce qui finit toujours par liberer un nom — la base
    reparee est bien formee, donc « base + chiffres » ne peut echouer que sur une
    liste de noms occupes, et cette liste est finie.
  • les noms que le fichier declare hors du modele (la fenetre, chaque `<layout>`,
    chaque `<action>`) comptent comme occupes des la generation. Avant, un clic
    pouvait produire le nom d'une mise en page : `setupUi()` cree un attribut par
    nom, l'objet disparaissait du code de l'eleve, et l'enregistrement refusait le
    fichier apres un geste qui semblait avoir reussi.

Mesurer, pas affirmer : une boucle qui tourne sans fin ne « echoue » pas, elle
pend. Les formes hostiles sont donc jouees sous watchdog (un fil que l'on rejoint
avec un delai), et l'ANCIEN corps de `_unique_name` — repris mot pour mot de
`tr_baseline_UIViewer.py`, le produit d'avant — est rejoue dans un processus
fils, pour que la gel reste une mesure et non un claquement de fenetre.
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import types
from xml.etree import ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
# La copie qu'un notateur de mutants (mutants_duplication.py) lui substitue :
# le pere et le fils de mesure doivent lire le MEME produit, sinon la suite
# jugerait le paquet livre pendant qu'on mute une copie.
PLUGIN = os.environ.get("TUNISIASCHOOLS_COPIE") or \
    r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tkinter as tk                                   # noqa: E402
import UIViewer                                        # noqa: E402
from UIViewer import UiViewerPlugin                    # noqa: E402

dialogues = []
reponse = [True]


def _askyesno(*a, **k):
    dialogues.append(("yesno",) + a)
    return reponse[0]


UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: dialogues.append(("error",) + a),
    showinfo=lambda *a, **k: dialogues.append(("info",) + a),
    askyesno=_askyesno)
UIViewer.filedialog = types.SimpleNamespace(
    askopenfilename=lambda **k: "",
    asksaveasfilename=lambda **k: "")
UIViewer.get_workbench = lambda: None

racine = tk.Tk()
racine.withdraw()

D = os.path.join(HERE, "_sortie", "duplication")
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)
SITE = os.path.join(BUNDLE, "Lib", "site-packages")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")


def CHEMIN(nom):
    return os.path.join(D, nom)


bilan = [0, 0]
a_l_envers = []


def check(*a):
    """Sens officiel : (condition, libelle, detail). Un controle ecrit dans
    l'autre ordre ne dit rien d'autre que « le libelle est une chaine », donc il
    passe toujours — le controle final de la suite l'interdit."""
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


# ── des gabarits ecrits a la main, comme l'eleve qui ouvre un bloc-notes ──

def _rect(x, y, w, h):
    return ('<property name="geometry"><rect><x>%d</x><y>%d</y>'
            '<width>%d</width><height>%d</height></rect></property>'
            % (x, y, w, h))


def _prop(nom_prop, valeur, balise="string"):
    return '<property name="%s"><%s>%s</%s></property>' % (
        nom_prop, balise, valeur, balise)


def _font(taille=9, gras=False):
    return ('<property name="font"><font><pointsize>%d</pointsize>'
            '<bold>%s</bold></font></property>' % (taille, str(gras).lower()))


def un_widget(cls, nom, geom=None, props=(), enfants=""):
    return '<widget class="%s" name="%s">%s%s%s</widget>' % (
        cls, nom, _rect(*geom) if geom else "", "".join(props), enfants)


def mise_en_page(cls, nom, widgets):
    return '<layout class="%s" name="%s">%s</layout>' % (
        cls, nom, "".join("<item>%s</item>" % w for w in widgets))


def une_action(nom, texte):
    return ('<action name="%s"><property name="text"><string>%s</string>'
            '</property></action>' % (nom, texte))


def formulaire(children, cls="QWidget", nom="Form", actions=""):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<ui version="4.0">\n'
            ' <class>%s</class>\n <widget class="%s" name="%s">%s%s'
            '%s</widget>\n</ui>\n'
            % (nom, cls, nom, _rect(0, 0, 420, 320), actions,
               "".join(children)))


def ecrit(chemin, texte):
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)


def octets(chemin):
    with open(chemin, "rb") as f:
        return f.read()


# Les neuf orthographes qu'un fichier peut porter sans passer par le panneau.
NOMS_HOSTILES = ["mon-bouton", "1er", "a.b", "bouton 1", "btnOk",
                 "class", "__init__", "élan", "!!!"]

# Ce que la fabrique doit rendre pour chacune : la base reparee, numerotee.
ATTENDU = {"mon-bouton": "mon_bouton1", "1er": "_1er1", "a.b": "a_b1",
           "bouton 1": "bouton1", "btnOk": "btnOk1", "class": "class1",
           "__init__": "__init__1", "élan": "élan1", "!!!": "widget1"}

HOSTILES = CHEMIN("hostiles.ui")
ecrit(HOSTILES, formulaire([
    un_widget("QPushButton", n, geom=(20, 20 + 36 * i, 120, 30),
              props=[_prop("text", "Bonjour")])
    for i, n in enumerate(NOMS_HOSTILES)]))

# Le fichier du geste : une seule orthographe hostile, pour voir ce que le clic
# produit vraiment (la copie, pas le modele theorique).
GESTE = CHEMIN("geste.ui")
ecrit(GESTE, formulaire([
    un_widget("QPushButton", "mon-bouton", geom=(40, 40, 120, 30),
              props=[_prop("text", "Bonjour"),
                     _prop("styleSheet", "color: rgb(255, 0, 0);"),
                     _font(12, True)]),
    un_widget("QLineEdit", "saisie", geom=(40, 90, 160, 30),
              props=[_prop("placeholderText", "Nom")]),
]))

# Un fichier range par un layout, avec une mise en page imbriquee, une action et
# un bouton deja numerote : tout ce que le fichier declare sans le passer au
# modele, plus une famille de noms en cours.
COLONNE = CHEMIN("colonne.ui")
ecrit(COLONNE, formulaire(
    [mise_en_page("QVBoxLayout", "colonne", [
        un_widget("QPushButton", "btnUn", props=[_prop("text", "Un")]),
        un_widget("QPushButton", "btnDeux", props=[_prop("text", "Deux")]),
        un_widget("QPushButton", "cadre1", props=[_prop("text", "Cadre")]),
        un_widget("QGroupBox", "groupe", props=[_prop("title", "Notes")],
                  enfants=mise_en_page("QHBoxLayout", "cadre", [
                      un_widget("QLabel", "etiquette",
                                props=[_prop("text", "Eleve :")])]))])],
    actions=une_action("btnUn1", "Effacer")))

CONTENU = CHEMIN("contenu.ui")
ecrit(CONTENU, formulaire([
    un_widget("QCheckBox", "caseA", geom=(20, 20, 120, 30),
              props=[_prop("text", "Accepte"), _prop("checked", "true", "bool"),
                     _prop("styleSheet", "background-color: rgb(1, 2, 3);"),
                     _font(14, True)]),
    un_widget("QPushButton", "class", geom=(20, 60, 120, 30),
              props=[_prop("text", "Reserve")]),
    un_widget("QPushButton", "élan", geom=(20, 100, 120, 30),
              props=[_prop("text", "Accentue")]),
]))


# ── le harnais sans vue, et la vue reelle ────────────────────

def harnais(chemin):
    """Le modele seul, sans Tk : la fabrique de noms ne regarde que les noms du
    modele et l'arbre lu. `_parse_ui` pose lui-meme _source_ui, _source_uids et
    _src_root ; il ne range son travail qu'en valeur de retour."""
    v = object.__new__(UiViewerPlugin)
    v.widgets_data, v.selected_idx = [], None
    v.widget_counter, v.ui_file = 0, chemin
    v.root_widget_name, v.root_widget_class = "Form", "QWidget"
    v.root_geometry, v.root_title = (0, 0, 420, 320), "Form"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    data, _info = v._parse_ui(chemin)
    v.widgets_data = data
    return v


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


def idx_de(v, nom):
    for i, (_c, props) in enumerate(v.widgets_data):
        if props.get("name") == nom:
            return i
    return None


def noms_modele(v):
    return [p["name"] for _c, p in v.widgets_data]


def saisit(v, ancien, nouveau, cle="name"):
    """Le geste exact du clavier : le panneau appelle _apply(cle, var, idx)."""
    i = idx_de(v, ancien)
    if i is None:
        return False
    v._apply(cle, tk.StringVar(value=nouveau), i)
    if cle == "name":
        return nouveau in noms_modele(v)
    return v.widgets_data[i][1].get(cle) == nouveau


def dessines(v):
    return [c.cget("text") for c in v.ui_frame.winfo_children()
            if getattr(c, "_is_label", False)]


def champ_nom(v):
    """Le fond du champ « Nom » du panneau, ou None quand aucun widget n'est
    selectionne. Un geste que la suite a decide de ne pas tenter (fabrique
    muette) laisse le panneau vide : lire l'objet directement ferait planter la
    suite, et une suite qui plante ne rend pas son bilan — donc ne note rien."""
    entry = getattr(v, "_name_entry", None)
    try:
        return entry.cget("bg")
    except (AttributeError, tk.TclError):
        return None


def tige(nom, cls="QPushButton"):
    """La base que _duplicate confie a la fabrique, mot pour mot : le nom copie
    degage de ses chiffres, la classe derivee si le nom etait vide."""
    return nom.rstrip("0123456789") or cls.replace("Q", "").lower()


def en_file(f, delai):
    """Le resultat d'un calcul fait dans un fil, ou None s'il ne revient pas.

    Un garde-fou qui refuse une forme que les chiffres ne reparent pas ne se
    voit pas a l'oeil : il pend. Le delai transforme la pendaison en echec."""
    boite = []
    fil = threading.Thread(target=lambda: boite.append(f()), daemon=True)
    t0 = time.time()
    fil.start()
    fil.join(delai)
    return (boite[0] if boite else None), round(time.time() - t0, 2)


# Des que la fabrique s'est tue, plus rien n'est tente par la suite. Un calcul
# qui pend ne se « note » pas : la suite ne rendrait plus son bilan, et le
# mutant serait compte survivant alors que c'est exactement le gel de l'item 14.
FABRIQUE = [True]


def rend_la_main(f, delai=20):
    if not FABRIQUE[0]:
        return None
    rendu, _secondes = en_file(f, delai)
    if rendu is None:
        FABRIQUE[0] = False
    return rendu


def duplique(v, idx):
    """Un clic sur « Dupliquer » : le geste reel, dans le fil de Tk (un appel
    Tcl depuis un autre fil est refuse), mais seulement si la fabrique a deja
    montre qu'elle rend la main sur ces formes."""
    if idx is None or not FABRIQUE[0] or not GESTE_AUTORISE:
        return False
    v._duplicate(idx)
    return True


def ajoute(v, cls):
    """Pareil pour un widget ajoute : _add_widget passe aussi par la fabrique."""
    if not FABRIQUE[0] or not GESTE_AUTORISE:
        return False
    v._add_widget(cls)
    return True


# Le gate des gestes. Un clic se joue dans le fil de Tk, la ou un delai ne peut
# rien : une seconde boucle ecrite dans _duplicate y rependrait la suite entiere,
# sans bilan — exactement le gel de l'item 14. Alors le code du clic est lu AVANT
# de cliquer : ni _duplicate ni _add_widget ne doivent contenir de « while ». La
# fabrique de noms, elle, se mesure sous delai (en_file, rend_la_main).
CHEMIN_SOURCE = getattr(UIViewer, "__file__",
                        os.path.join(PLUGIN, "UIViewer.py"))
try:
    METHODES = {n.name: n for n in ast.walk(ast.parse(
        open(CHEMIN_SOURCE, encoding="utf-8").read()))
        if isinstance(n, ast.FunctionDef)}
except Exception:
    METHODES = {}


def boucle_dans(*noms):
    """Un « while » dans l'une de ces methodes, ou une methode introuvable :
    dans les deux cas, on ne clique pas."""
    for nom in noms:
        methode = METHODES.get(nom)
        if methode is None or any(isinstance(x, ast.While)
                                  for x in ast.walk(methode)):
            return True
    return False


GESTE_AUTORISE = not boucle_dans("_duplicate", "_add_widget")
check("le code du clic n'a pas de boucle a lui : on peut cliquer",
      GESTE_AUTORISE, [n for n in METHODES if n in ("_duplicate", "_add_widget")])


# ── 1. la forme et le reserve sont deux questions differentes ────────
print("\n=== 1. ce qu'un chiffre repare, et ce qu'il ne repare pas ===")

FORMES_VALIDES = ["bouton", "_prive", "btnOk", "b2", "classe1", "élan",
                  "__init__", "match", "print"]
FORMES_BOITEUSES = ["mon-bouton", "bouton 1", "1er", "a.b", "!!!", "", "2cases",
                    "case-ok", "camel Case"]
for nom in FORMES_VALIDES:
    check("forme acceptee : %s" % (nom,), UiViewerPlugin._forme_valide(nom))
for nom in FORMES_BOITEUSES:
    check("forme refusee : %r" % (nom,), not UiViewerPlugin._forme_valide(nom))

# Le mot-cle est bien forme : c'est son statut qui gene, et un chiffre le leve.
check("un mot reserve est pourtant de forme parfaite",
      UiViewerPlugin._forme_valide("class") and
      not UiViewerPlugin._valid_qt_name("class"))
check("la forme seule, elle, l'accepte : c'est la regle reservee qui le bloque",
      UiViewerPlugin._reserve_python("class") == "mot-cle")
check("un dunder non plus n'a besoin que d'un numero",
      UiViewerPlugin._forme_valide("__init__") and
      not UiViewerPlugin._valid_qt_name("__init__") and
      UiViewerPlugin._valid_qt_name("__init__1"))

# Les cles sont les BASES telles que _duplicate les calcule (un espace de fin
# survit a rstrip, un espace du milieu devient un « _ » : les deux sont
# numerotables, ce qui est la seule chose que la fabrique exige).
REPARATIONS = {"mon-bouton": "mon_bouton", "bouton ": "bouton",
               "bouton 1": "bouton_1", "1er": "_1er", "a.b": "a_b",
               "case-ok": "case_ok", "!!": "widget", "@@@": "widget",
               "": "widget", "  espace  ": "espace",
               "a..b": "a_b", "!!!": "widget",
               "tres.long.nom.avec.des.points": "tres_long_nom_avec_des_points"}
for donnee, voulu in REPARATIONS.items():
    rendu = UiViewerPlugin._base_reparee(donnee)
    check("repare : %r -> %s" % (donnee, voulu), rendu == voulu, rendu)
for donnee in REPARATIONS:
    check("la base reparee est toujours numerotable : %r" % (donnee,),
          UiViewerPlugin._forme_valide(UiViewerPlugin._base_reparee(donnee)))
# Une base deja bien formee ressort telle quelle : le numero, pas la traduction,
# est ce qui rend un mot reserve libre.
for nom in ("class", "élan", "btnOk", "mon_bouton", "_1er", "widget"):
    check("deja forme, donc pas traduite : %r" % (nom,),
          UiViewerPlugin._base_reparee(nom) == nom)
check("le repli est une famille, pas un mot invente",
      UiViewerPlugin.NOM_DE_RECHANGE == "widget" and
      UiViewerPlugin._forme_valide(UiViewerPlugin.NOM_DE_RECHANGE))

# ── 2. la fabrique rend la main, et son nom est libre ────────────────
print("\n=== 2. generer un nom, sur un fichier ecrit a la main ===")
v2 = harnais(HOSTILES)
check("les neuf orthographes hostiles sont bien entrees dans le modele",
      noms_modele(v2) == NOMS_HOSTILES, noms_modele(v2))
table, secondes = en_file(
    lambda: {n: v2._unique_name(tige(n)) for n in NOMS_HOSTILES}, 20)
check("la fabrique rend la main sur les neuf formes (%.2fs)" % secondes,
      table is not None, secondes)
if table is None:
    print("     ===== la gel est revenue : la suite ne tentera plus aucun geste =====")
    FABRIQUE[0] = False
    table = {}
for nom in NOMS_HOSTILES:
    rendu = table.get(nom)
    check("  %s  ->  %s" % (nom, ATTENDU[nom]), rendu == ATTENDU[nom], rendu)
occupes = set(noms_modele(v2)) | v2._noms_hors_modele()
heurtes = [n for n in table.values() if n in occupes]
check("aucun nom genere ne heurte un nom du fichier", heurtes == [], heurtes)
boiteux = [n for n in table.values() if not UiViewerPlugin._valid_qt_name(n)]
check("chaque nom genere est un nom Qt valide", boiteux == [], boiteux)
pas_ident = [n for n in table.values() if not n.isidentifier()]
check("chaque nom genere est un identifiant Python", pas_ident == [], pas_ident)


def ligne_secours(nom):
    try:
        ast.parse("windows.%s.setText('x')" % nom)
        return True
    except SyntaxError:
        return False


refuses = [n for n in table.values() if not ligne_secours(n)]
check("la ligne que le panneau propose se compile pour chaque nom",
      refuses == [], refuses)
check("generer ne renommme rien : le modele a garde les noms du fichier",
      noms_modele(v2) == NOMS_HOSTILES, noms_modele(v2))
check("le compteur a retenu le plus grand numero emis",
      v2.widget_counter == 1, v2.widget_counter)
# Une base qu'il a fallu reparer garde neanmoins un numero : « mon_bouton » doit
# rester libre, c'est justement l'orthographe propre sur laquelle l'eleve va
# vouloir reporter son « mon-bouton ».
check("une base reparee est numerotee meme si la place propre etait libre",
      table.get("mon-bouton") == "mon_bouton1" and
      "mon_bouton" not in occupes, table.get("mon-bouton"))

# ── 3. l'ancien corps, rejoue dans un processus fils ──────────────────
print("\n=== 3. l'ancien corps rejoue : la gel etait bien la ===")
# Le corps de _unique_name TEL QUEL dans le produit d'avant (tr_baseline_
# UIViewer.py). Rien d'autre n'est ancien : _valid_qt_name (qui connait les mots
# reserves depuis l'item 6), _used_names et _next_seed restent ceux du produit,
# donc ce fils mesure exactement les deux lignes que l'item 14 a changees.
ANCIEN_BOUCL = '''        used = self._used_names(exclude_idx)
        name = base
        if name in used or not self._valid_qt_name(name):
            suffix = self._next_seed(base)
            name = f"{base}{suffix}"
            while name in used or not self._valid_qt_name(name):
                suffix += 1
                name = f"{base}{suffix}"
            # le compteur reste la memoire du plus grand numero emis, pour
            # qu'un outil exterieur puisse lire l'etat sans se fier aux noms
            self.widget_counter = max(self.widget_counter, suffix)
        return name'''
BASELINE = open(os.path.join(HERE, "tr_baseline_UIViewer.py"),
                encoding="utf-8").read()
check("le corps rejoue est mot pour mot celui du produit d'avant",
      ANCIEN_BOUCL in BASELINE)

FILS = r'''
import os, sys, threading, time, types
from xml.etree import ElementTree as ET
sys.path.insert(0, @@SITE@@)
sys.path.insert(0, @@PLUGIN@@)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import UIViewer
from UIViewer import UiViewerPlugin
UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: None, showinfo=lambda *a, **k: None,
    askyesno=lambda *a, **k: False)
UIViewer.filedialog = types.SimpleNamespace(
    askopenfilename=lambda **k: "", asksaveasfilename=lambda **k: "")
UIViewer.get_workbench = lambda: None


def ancien(self, base, exclude_idx=None):
@@ANCIEN@@


ANCIEN = ancien
NOUVEAU = UiViewerPlugin._unique_name
DELAI = @@DELAI@@


def harnais(chemin):
    v = object.__new__(UiViewerPlugin)
    v.widgets_data, v.selected_idx = [], None
    v.widget_counter, v.ui_file = 0, chemin
    v.root_widget_name, v.root_widget_class = "Form", "QWidget"
    v.root_geometry, v.root_title = (0, 0, 420, 320), "Form"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    data, _info = v._parse_ui(chemin)
    v.widgets_data = data
    return v


def une_fois(f, chemin, base):
    v = harnais(chemin)
    boite = []
    # un fil daemon qui ne rend pas ne retient pas le processus : c'est voulu,
    # la gel d'hier est ce qu'on mesure ici, pas ce qu'on subit.
    fil = threading.Thread(target=lambda: boite.append(f(v, base)), daemon=True)
    fil.start()
    fil.join(DELAI)
    return boite[0] if boite else "BOUCLE"


for clef, chemin, base in @@CAS@@:
    avant = une_fois(ANCIEN, chemin, base)
    apres = une_fois(NOUVEAU, chemin, base)
    sys.stdout.write("CAS|%s|%s|ANCIEN=%s|NOUVEAU=%s\n"
                     % (clef, base, avant, apres))
    sys.stdout.flush()
'''

CAS_FILS = [(n, HOSTILES, tige(n)) for n in NOMS_HOSTILES] + [
    ("cadre1", COLONNE, tige("cadre1")),
    ("btnUn", COLONNE, tige("btnUn")),
]
REJOUe = CHEMIN("rejoue_ancien.py")
# repr(), pas des guillemets poses a la main : un chemin Windows contient des
# « \U » que Python lirait comme un echappement unicode dans un litteral "C:\...".
ecrit(REJOUe, FILS.replace("@@SITE@@", repr(SITE))
                     .replace("@@PLUGIN@@", repr(PLUGIN))
                     .replace("@@ANCIEN@@", ANCIEN_BOUCL)
                     .replace("@@DELAI@@", "3")
                     .replace("@@CAS@@", repr(CAS_FILS)))
t0 = time.time()
sortie_fils, erreur_fils = "", ""
try:
    fils = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", REJOUe],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ENV, cwd=HERE, timeout=240)
    sortie_fils, erreur_fils = fils.stdout, fils.stderr
except subprocess.TimeoutExpired:
    print("     le fils de mesure a depasse son delai")
rendus = {}
for ligne in (sortie_fils or "").splitlines():
    morceaux = ligne.split("|")
    if len(morceaux) == 5 and morceaux[0] == "CAS":
        rendus[morceaux[1]] = dict(x.split("=", 1) for x in morceaux[3:])
check("le fils de mesure a rendu ses onze lignes (%.0fs)" % (time.time() - t0),
      len(rendus) == len(CAS_FILS),
      (len(rendus), (erreur_fils or sortie_fils or "")[-300:]))

SANS_ISSUE = ["mon-bouton", "1er", "a.b", "bouton 1", "!!!"]
for clef in SANS_ISSUE:
    check("  avant, %r ne rendait jamais la main" % (clef,),
          rendus.get(clef, {}).get("ANCIEN") == "BOUCLE", rendus.get(clef))
    check("  maintenant, %r rend %s" % (clef, ATTENDU[clef]),
          rendus.get(clef, {}).get("NOUVEAU") == ATTENDU[clef], rendus.get(clef))
for clef in ("btnOk", "class", "__init__", "élan"):
    check("  avant, %r s'en sortait deja : un chiffre leve le reserve" % (clef,),
          rendus.get(clef, {}).get("ANCIEN") == ATTENDU[clef], rendus.get(clef))
    check("  et le produit rend la meme chose : rien n'a change ici",
          rendus.get(clef, {}).get("NOUVEAU") == ATTENDU[clef], rendus.get(clef))
# La seconde moitie de l'item 14 : avant, la recherche ne regardait que le
# modele, donc un clic pouvait produire le nom d'une mise en page ou d'une action.
check("  avant, « cadre1 » duplique prenait le nom de la mise en page « cadre »",
      rendus.get("cadre1", {}).get("ANCIEN") == "cadre", rendus.get("cadre1"))
check("  maintenant il prend cadre2, la mise en page garde son nom",
      rendus.get("cadre1", {}).get("NOUVEAU") == "cadre2", rendus.get("cadre1"))
check("  avant, « btnUn » duplique prenait le nom de l'action « btnUn1 »",
      rendus.get("btnUn", {}).get("ANCIEN") == "btnUn1", rendus.get("btnUn"))
check("  maintenant il prend btnUn2, l'action garde son nom",
      rendus.get("btnUn", {}).get("NOUVEAU") == "btnUn2", rendus.get("btnUn"))

# ── 4. le geste, dans une vraie fenetre ──────────────────────────────
print("\n=== 4. le geste : un clic sur Dupliquer ===")
_top, v = fenetre("duplication-geste")
v.load_new_ui_file(GESTE)
i_original = idx_de(v, "mon-bouton")
check("le nom ecrit a la main entre dans le modele tel quel",
      v.widgets_data[i_original][1]["name"] == "mon-bouton")
check("et le panneau le signale comme un probleme avant meme de cliquer",
      any("mon-bouton" in p for p in v._name_troubles()), v._name_troubles())
pile_avant = len(v._undo_stack)
t0 = time.time()
geste_fait = duplique(v, i_original)
duree = time.time() - t0
copie = v.widgets_data[-1][1]
original = v.widgets_data[i_original][1]
check("Dupliquer rend la main (%.2fs)" % duree, duree < 5 and geste_fait, duree)
check("la copie s'appelle mon_bouton1", copie["name"] == "mon_bouton1",
      copie["name"])
check("l'original n'est PAS repare d'autorite : il garde mon-bouton",
      original["name"] == "mon-bouton", original["name"])
check("les deux noms sont distincts",
      len(set(noms_modele(v))) == len(v.widgets_data), noms_modele(v))
check("le panneau affiche le nom de la copie",
      v._name_entry is not None and v._name_entry.get() == "mon_bouton1",
      getattr(v._name_entry, "get", lambda: None)())
check("et son champ est noir : le nom genere est accepte tel quel",
      champ_nom(v) == "#3c3c3c", champ_nom(v))
check("la copie est selectionnee",
      v.selected_idx == len(v.widgets_data) - 1, v.selected_idx)
check("elle est décalée de 20 pixels en x et en y",
      copie["geometry"] == (60, 60, 120, 30), copie["geometry"])
check("l'original n'a pas bouge", original["geometry"] == (40, 40, 120, 30),
      original["geometry"])
check("la copie n'herite d'aucun element XML : elle sera ajoutee en propre",
      not any(cle in copie for cle in ("_uid", "_src", "_est")),
      sorted(k for k in copie if k.startswith("_")))
check("le canevas dessine les deux noms",
      set(["mon-bouton", "mon_bouton1"]) <= set(dessines(v)), dessines(v))
check("dupliquer est un travail non enregistre", v._travail_non_enregistre())
check("le geste coute exactement un pas d'annulation",
      len(v._undo_stack) == pile_avant + 1, len(v._undo_stack))
v.undo()
check("un seul Annuler retire la copie",
      noms_modele(v) == ["mon-bouton", "saisie"], noms_modele(v))
check("et le journal est revenu vide", len(v._undo_stack) == pile_avant,
      len(v._undo_stack))
check("l'orthographe d'origine est toujours la, a corriger",
      any("mon-bouton" in p for p in v._name_troubles()), v._name_troubles())

# ── 5. dupliquer plusieurs fois ──────────────────────────────────────
print("\n=== 5. la meme orthographe hostile, dupliquee trois fois ===")
_top5, v5 = fenetre("duplication-filet")
v5.load_new_ui_file(GESTE)
t0 = time.time()
trois = [duplique(v5, idx_de(v5, "mon-bouton")),
         duplique(v5, idx_de(v5, "mon_bouton1")),
         duplique(v5, idx_de(v5, "mon_bouton"))]
check("trois clics rendent la main (%.2fs)" % (time.time() - t0),
      all(trois) and time.time() - t0 < 10, (trois, round(time.time() - t0, 2)))
check("le fichier de depart a deux widgets, trois clics en font cinq",
      len(v5.widgets_data) == 5, len(v5.widgets_data))
check("et cinq noms distincts",
      len(set(noms_modele(v5))) == 5, noms_modele(v5))
check("la famille suit l'ordre des clics, le voisin n'est pas deplace",
      noms_modele(v5) == ["mon-bouton", "saisie", "mon_bouton1", "mon_bouton",
                          "mon_bouton2"], noms_modele(v5))
troubles = v5._name_troubles()
check("les trois copies sont propres : seule l'orthographe d'origine gene",
      len(troubles) == 1 and "mon-bouton" in troubles[0], troubles)

# ── 6. la copie garde la classe et le contenu ────────────────────────
print("\n=== 6. ce que la copie emporte avec elle ===")
_top6, v6 = fenetre("duplication-contenu")
v6.load_new_ui_file(CONTENU)
i_case = idx_de(v6, "caseA")
case_dupliquee = duplique(v6, i_case)
cls_copie, c = v6.widgets_data[-1]
o = v6.widgets_data[i_case][1]
check("le geste a pu etre tente", case_dupliquee)
check("la classe est copiee", cls_copie == "QCheckBox", cls_copie)
check("l'etat coche est copie", c.get("checked") is True and o.get("checked") is True)
check("le texte est copie", c.get("text") == "Accepte", c.get("text"))
check("la feuille de style est copiee", c.get("styleSheet") == o.get("styleSheet"),
      c.get("styleSheet"))
check("la police est copiee", c.get("font") == {"size": 14, "bold": True,
                                                "italic": False, "family": ""},
      c.get("font"))
check("la copie est un autre dict, avec ses propres sous-objets",
      c is not o and c["font"] is not o["font"])
class_dupliquee = duplique(v6, idx_de(v6, "class"))
check("un nom reserve garde son orthographe, il prend juste un numero",
      class_dupliquee and v6.widgets_data[-1][1].get("name") == "class1",
      v6.widgets_data[-1][1].get("name"))
check("et la classe copiee reste celle de l'original",
      class_dupliquee and v6.widgets_data[-1][0] == "QPushButton",
      v6.widgets_data[-1][0])
elan_dupliquee = duplique(v6, idx_de(v6, "élan"))
check("l'accent du nom survit a la fabrique : rien n'est translitere",
      elan_dupliquee and v6.widgets_data[-1][1].get("name") == "élan1",
      v6.widgets_data[-1][1].get("name"))
liste_ajoutee = ajoute(v6, "QComboBox")
i_liste = len(v6.widgets_data) - 1
liste_dupliquee = duplique(v6, i_liste)
liste_origine = liste_copie = None
if liste_ajoutee and liste_dupliquee:
    liste_origine = v6.widgets_data[i_liste][1].get("items")
    liste_copie = v6.widgets_data[-1][1].get("items")
check("les elements d'une liste copiee sont une copie, pas le meme objet",
      liste_origine is not None and liste_origine == liste_copie and
      liste_origine is not liste_copie, (liste_origine, liste_copie))
if liste_copie is not None and liste_origine is not None and \
        liste_copie is not liste_origine:
    liste_copie.append("Ajoute dans la copie")
check("ecrire dans la liste de la copie ne remplit pas l'original",
      liste_copie is not None and "Ajoute dans la copie" not in liste_origine,
      (liste_origine, liste_copie))

# ── 7. dans un fichier piloté par un layout ──────────────────────────
print("\n=== 7. la copie d'un widget range ===")
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
objets = {}
for nom in @@NOMS@@:
    o = getattr(w, nom, None)
    objets[nom] = None if o is None else {
        "cls": o.metaObject().className(),
        "texte": o.text() if hasattr(o, "text") else "",
        "id": id(o),
    }
rang = []
lay = w.layout()
if lay is not None:
    for i in range(lay.count()):
        it = lay.itemAt(i)
        if it.widget() is not None:
            rang.append(it.widget().objectName())
        elif it.layout() is not None:
            rang.append("<layout>")
        else:
            rang.append("<item>")
print(json.dumps({"objets": objets, "colonne": rang}, ensure_ascii=False))
'''


def mesure_qt(chemin, noms):
    script = (SONDE_QT.replace("@@SITE@@", repr(SITE))
                      .replace("@@FICHIER@@", repr(chemin))
                      .replace("@@NOMS@@", repr(sorted(set(noms)))))
    p = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", "-c", script],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV, timeout=180)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"erreur": (p.stdout or "")[-200:] + (p.stderr or "")[-300:]}


_top7, v7 = fenetre("duplication-range")
v7.load_new_ui_file(COLONNE)
i_un = idx_de(v7, "btnUn")
range_dupliquee = duplique(v7, i_un)
cls7, range_copie = v7.widgets_data[-1]
check("la copie d'un widget range est dite rangee",
      range_dupliquee and range_copie.get("_pose") == "layout",
      range_copie.get("_pose"))
check("elle rejoint la boite qui range l'original",
      range_dupliquee and bool(range_copie.get("_groupe")) and
      range_copie.get("_groupe") == v7.widgets_data[i_un][1].get("_groupe"),
      range_copie.get("_groupe"))
check("elle herite de son axe",
      range_dupliquee and range_copie.get("_axe") == "v",
      range_copie.get("_axe"))
check("elle prend la place libre en fin de colonne",
      range_dupliquee and range_copie.get("_rang") == 4,
      range_copie.get("_rang"))
check("le nom genere saute le nom de l'action",
      range_dupliquee and range_copie.get("name") == "btnUn2",
      range_copie.get("name"))
RANGE = CHEMIN("range_apres.ui")
v7._write_ui_file(RANGE)
arbre = ET.parse(RANGE).getroot()
peres = {id(fils): pere for pere in arbre.iter() for fils in pere}
nommes = [el.get("name") for el in arbre.iter("widget")]
check("les cinq widgets du fichier sont ceux du modele",
      nommes == ["Form"] + noms_modele(v7), nommes)
el_copie = arbre.find(".//widget[@name='btnUn2']")
check("la copie est écrite dans le fichier", el_copie is not None)
if el_copie is not None:
    check("elle est portee par un <item>, comme les autres ranges",
          peres[id(el_copie)].tag == "item", peres[id(el_copie)].tag)
    check("elle n'a pas de <geometry> heritee : c'est le layout qui la place",
          el_copie.find("property[@name='geometry']") is None)
_avant = octets(RANGE)
v7._write_ui_file(RANGE)
check("enregistrer deux fois rend exactement les memes octets",
      octets(RANGE) == _avant)
mesure = mesure_qt(RANGE, ["btnUn", "btnDeux", "cadre1", "groupe", "btnUn2"])
check("Qt charge le fichier sans erreur", "erreur" not in mesure, mesure)
if "objets" in mesure:
    colonne_qt = mesure.get("colonne") or []
    check("les widgets ranges gardent l'ordre du fichier, la copie en derniere place",
          colonne_qt == ["btnUn", "btnDeux", "cadre1", "groupe", "btnUn2"],
          colonne_qt)
    copie_qt = (mesure["objets"] or {}).get("btnUn2") or {}
    original_qt = (mesure["objets"] or {}).get("btnUn") or {}
    check("windows.btnUn2 designe bien un QPushButton",
          copie_qt.get("cls") == "QPushButton", copie_qt)
    check("et il porte le texte de l'original", copie_qt.get("texte") == "Un",
          copie_qt)
    check("la copie est un objet distinct de l'original",
          copie_qt.get("id") != original_qt.get("id"), (copie_qt, original_qt))
    check("la mise en page imbriquee du groupe a survécu a la copie",
          (mesure["objets"].get("groupe") or {}).get("cls") == "QGroupBox",
          mesure["objets"].get("groupe"))

# ── 8. les noms que le fichier reserve hors du modele ────────────────
print("\n=== 8. la fenetre, les mises en page et les actions comptent ===")
v8 = harnais(COLONNE)
check("les noms hors modele sont la fenetre, les layouts et l'action",
      v8._noms_hors_modele() == {"Form", "colonne", "cadre", "btnUn1"},
      v8._noms_hors_modele())
check("les noms des widgets du modele ne sont pas comptes deux fois",
      not ({"btnUn", "btnDeux", "cadre1", "groupe", "etiquette"} &
           v8._noms_hors_modele()), v8._noms_hors_modele())
libres = rend_la_main(lambda: [v8._unique_name(tige(n)) for n in
                              ("btnUn", "btnDeux", "cadre1", "groupe",
                               "etiquette")])
print("     noms generes : %s" % (libres,))
check("la fabrique rend la main sur les cinq bases ranges",
      libres is not None and len(libres) == 5, libres)
check("aucun nom genere ne reprend un nom reserve par le fichier",
      libres is not None and
      not (set(libres) & v8._noms_hors_modele()), libres)
check("et aucun ne reprend un nom deja porte par un widget",
      libres is not None and
      len(set(libres) & set(noms_modele(v8))) == 0, libres)
v8b = harnais(COLONNE)
v8b.widgets_data[idx_de(v8b, "cadre1")][1]["name"] = "cadre"
genere = [p for p in v8b._name_troubles() if "cadre" in p]
check("le nom que l'ancienne fabrique choisissait est refuse a l'enregistrement",
      len(genere) == 1 and "mise en page" in genere[0], genere)

# ── 9. l'eleve s'en sort : il corrige l'orthographe d'origine ────────
print("\n=== 9. la sortie de l'eleve, jusqu'au fichier que Qt charge ===")
_top9, v9 = fenetre("duplication-save")
v9.load_new_ui_file(GESTE)
neuvieme = duplique(v9, idx_de(v9, "mon-bouton"))
SAUVEGARDE = CHEMIN("geste_apres.ui")
v9.ui_file = SAUVEGARDE
dialogues.clear()
v9._save()
check("la copie est valide, l'orthographe d'origine non : _save refuse",
      neuvieme and [d[0] for d in dialogues] == ["error"], dialogues)
check("et l'avis nomme l'objet en cause",
      "mon-bouton" in str(dialogues), str(dialogues)[:200])
check("rien n'est ecrit pendant que le nom d'origine reste boiteux",
      not os.path.exists(SAUVEGARDE))
check("le travail reste annonce comme non enregistre",
      v9._travail_non_enregistre())
check("renommer l'original sur la place propre est accepte",
      saisit(v9, "mon-bouton", "mon_bouton"))
check("la copie garde son numero : les deux noms restent distincts",
      noms_modele(v9) == ["mon_bouton", "saisie", "mon_bouton1"], noms_modele(v9))
check("l'eleve peut donner un texte different a chacun",
      saisit(v9, "mon_bouton", "Original", cle="text"))
dialogues.clear()
v9._save()
check("repasse au propre, le fichier s'ecrit",
      [d[0] for d in dialogues] == ["info"], dialogues)
check("et plus rien n'est annonce comme perdu", not v9._travail_non_enregistre())
# Le fichier peut ne jamais avoir ete ecrit : si la fabrique a rendu un nom qui
# heurte un autre, le second _save() refuse encore. Le lire quand meme ferait
# planter la suite sur un FileNotFoundError, et un crash ne se note pas.
if os.path.exists(SAUVEGARDE):
    nommes = [el.get("name") for el in ET.parse(SAUVEGARDE).iter("widget")]
    mesure = mesure_qt(SAUVEGARDE, ["mon_bouton", "mon_bouton1", "saisie"])
else:
    nommes = None
    mesure = {"erreur": "aucun fichier ecrit : rien que Qt puisse construire"}
check("le fichier porte l'original corrige et sa copie",
      nommes == ["Form", "mon_bouton", "saisie", "mon_bouton1"], nommes)
check("Qt construit le fichier corrige", "erreur" not in mesure, mesure)
if "objets" in mesure:
    a = mesure["objets"].get("mon_bouton") or {}
    b = mesure["objets"].get("mon_bouton1") or {}
    check("les deux noms designent deux boutons distincts",
          a.get("cls") == "QPushButton" and b.get("cls") == "QPushButton" and
          a.get("id") != b.get("id"), (a, b))
    check("chacun a son propre texte : la copie n'est pas l'original",
          a.get("texte") == "Original" and b.get("texte") == "Bonjour", (a, b))
    check("windows.mon_bouton1 est bien joignable depuis le code",
          b.get("cls") == "QPushButton", b)

# ── 10. ce qui ne doit jamais finir par s'eteindre ───────────────────
print("\n=== 10. une famille pleine, et une generation qui s'enchaine ===")
v10 = harnais(GESTE)
v10.widgets_data = [("QPushButton", {"name": n})
                    for n in ["bouton"] +
                              ["bouton%d" % i for i in range(1, 121)]]
pleine = rend_la_main(lambda: v10._unique_name(tige("bouton120")))
repli = rend_la_main(lambda: v10._unique_name("!!!"))
check("cent vingt places prises, la fabrique rend bouton121",
      pleine == "bouton121", pleine)
# Le compteur ne sert plus a NOMMER — c'est le modele qui decide — mais il reste
# la memoire du plus grand numero emis, et un outil exterieur ne peut lire l'etat
# que par lui. Un « bouton121 » rendu sans que le compteur le sache est un
# compteur faux.
check("le compteur a retenu le numero emis, pour un outil qui lit l'etat",
      pleine == "bouton121" and v10.widget_counter == 121, v10.widget_counter)
check("une base qui ne laisse aucune lettre tombe sur la famille de repli",
      repli == "widget1", repli)


def enchaine(v, base, fois):
    if not FABRIQUE[0]:
        return None
    rendus = []
    for _ in range(fois):
        nom = v._unique_name(base)
        v.widgets_data.append(("QPushButton", {"name": nom}))
        rendus.append(nom)
    return rendus


suite, secondes = en_file(lambda: enchaine(v10, "bouton", 200), 30)
check("deux cents generations d'affilee rendent la main (%.1fs)" % secondes,
      suite is not None, secondes)
if suite:
    check("les deux cents noms sont distincts", len(set(suite)) == 200,
          (len(set(suite)), suite[:3]))
    check("et ils restent dans la famille numerotee",
          suite[0] == "bouton121" and suite[-1] == "bouton320",
          (suite[0], suite[-1]))
    check("le compteur a suivi la famille jusqu'au bout",
          v10.widget_counter == 320, v10.widget_counter)
v11 = harnais(HOSTILES)
v11._source_ui = None
check("sans arbre lu du tout, la fabrique tourne quand meme",
      rend_la_main(lambda: v11._unique_name(tige("mon-bouton"))) == "mon_bouton1")
check("et le repli reste disponible",
      rend_la_main(lambda: v11._unique_name("!!!")) == "widget1")
v12 = harnais(GESTE)
check("le nom de la fenetre elle-meme est compte comme occupe",
      rend_la_main(lambda: v12._unique_name("Form")) == "Form1")

# ── 11. ce que le code dit ───────────────────────────────────────────
print("\n=== 11. le code ===")
source = open(getattr(UIViewer, "__file__",
                      os.path.join(PLUGIN, "UIViewer.py")),
              encoding="utf-8").read()
arb = ast.parse(source)
meth = {n.name: n for n in ast.walk(arb) if isinstance(n, ast.FunctionDef)}


def seg(nom):
    """Le texte d'une methode, ou None si elle a disparu du produit."""
    noeud = meth.get(nom)
    return ast.get_source_segment(source, noeud) if noeud is not None else None


def avant(texte, premier, second):
    """True si `premier` apparait avant `second`. find() et non index(), et
    presence verifiee DEDANS le controle : un mutant qui efface la ligne ferait
    lever ValueError par .index(), et la suite perdrait son bilan — donc sa note."""
    if texte is None:
        return None
    a, b = texte.find(premier), texte.find(second)
    if a < 0 or b < 0:
        return None
    return a < b


def apres(texte, marque, cherche):
    """Le nombre d'apparitions de `cherchee` apres la premiere `marque`, ou None
    si la marque a disparu."""
    if texte is None:
        return None
    i = texte.find(marque)
    return None if i < 0 else texte[i:].count(cherche)


def dit(texte, morceau):
    """`morceau` est ecrit dans `texte` — et `texte` existe. Un simple
    `morceau in texte` sur une methode que le mutant a supprimee leverait
    TypeError : la suite doit echouer, pas s'eteindre."""
    return texte is not None and morceau in texte


def appeles(nom):
    """Les identifiants que le CORPS d'une methode appelle, docstring exclue.
    « _unique_name n'apparait pas dans le texte » echouerait sur la phrase de
    commentaire qui raconte, justement, que la reparation n'appelle personne."""
    noeud = meth.get(nom)
    if noeud is None:
        return set()
    corps = list(noeud.body)
    if (corps and isinstance(corps[0], ast.Expr) and
            isinstance(corps[0].value, ast.Constant) and
            isinstance(corps[0].value.value, str)):
        corps = corps[1:]
    return {getattr(x, "id", None) or getattr(x, "attr", None)
            for e in corps
            for x in ast.walk(e)
            if isinstance(x, (ast.Name, ast.Attribute))}


fabrique, repare = seg("_unique_name"), seg("_base_reparee")
forme, valid, dup = seg("_forme_valide"), seg("_valid_qt_name"), seg("_duplicate")
for texte, ou in ((fabrique, "_unique_name"), (valid, "_valid_qt_name"),
                  (dup, "_duplicate"), (forme, "_forme_valide"),
                  (repare, "_base_reparee")):
    check("la methode %s est toujours la, donc ses controles portent" % ou,
          texte is not None)
check("la forme n'est ecrite qu'a un seul endroit",
      source.count("first.isalpha()") == 1, source.count("first.isalpha()"))
check("le controle du nom appelle la forme, il ne la recopie pas",
      valid is not None and "_forme_valide(name)" in valid
      and "first.isalpha()" not in valid)
check("le controle du nom appelle aussi la regle reservee",
      valid is not None and "_reserve_python(name)" in valid)
check("la fabrique repare la base AVANT de chercher",
      avant(fabrique, "_base_reparee(base)", "while name in used") is True,
      (avant(fabrique, "_base_reparee(base)", "while name in used"),))
check("elle ne repare plus rien PENDANT la recherche",
      apres(fabrique, "while name in used", "_base_reparee") == 0,
      apres(fabrique, "while name in used", "_base_reparee"))
check("la boucle n'ajoute que des chiffres a la meme base",
      dit(fabrique, "suffix += 1") and dit(fabrique, 'name = f"{base}{suffix}"'))
check("une seule boucle de recherche dans tout le produit",
      source.count("while name in used") == 1, source.count("while name in used"))
check("la reparation ne numerote pas et ne s'appelle pas elle-meme",
      not {"_next_seed", "_unique_name", "suffix"} & appeles("_base_reparee"),
      sorted(x for x in appeles("_base_reparee") if x))
NOEUD_REPARE = meth.get("_base_reparee")
BOUCLES = [] if NOEUD_REPARE is None else [
    n for n in ast.walk(NOEUD_REPARE) if isinstance(n, ast.While)]
check("le seul tour de boucle de la reparation replie les deux « _ » consecutifs",
      len(BOUCLES) == 1 and
      "__" in {c.value for c in ast.walk(BOUCLES[0].test)
               if isinstance(c, ast.Constant)},
      (len(BOUCLES),
       ast.dump(BOUCLES[0].test) if BOUCLES else None))
check("le repli est une famille toujours numerotable",
      dit(repare, "NOM_DE_RECHANGE") and 'NOM_DE_RECHANGE = "widget"' in source)
check("la fabrique consulte les noms que le fichier reserve hors du modele",
      dit(fabrique, "_noms_hors_modele()"))
check("une base reparee garde neanmoins un numero", dit(fabrique, "a_repare"))
check("le drapeau de reparation se calcule sur la base donnee, pas sur la base reparee",
      dit(fabrique, "donnee = base") and dit(fabrique, "base != donnee"))
check("_duplicate passe toujours par la fabrique",
      dit(dup, "_unique_name(stem)") and not dit(dup, "_base_reparee"))
check("_duplicate ne s'est pas invente une seconde boucle",
      dup is not None and "while" not in dup)
check("aucun QMessageBox dans l'editeur visuel", "QMessageBox" not in source)

for top in fenetres:
    top.destroy()
racine.update()

check("aucun controle de cette suite n'est ecrit dans l'autre sens",
      a_l_envers == [], a_l_envers)

print("\n%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)
