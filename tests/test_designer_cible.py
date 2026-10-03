r"""Item 9 : « Ouvrir dans Designer » doit désigner le fichier que la vue affiche.

Le défaut n'était pas dans Designer, ni dans la découverte du binaire — il était
dans la question « quel fichier ? ». `__init__.py` tenait un global `qt_ui_file`,
et une seule ligne du paquet l'écrivait : `add_pyqt_code` (« Ajouter Annexe +
interface »). Une seule ligne le lisait : `_current_ui_path()`, qui prépare
l'argument de `designer.exe`. Entre les deux, la vue change de fichier sans
prévenir personne, parce qu'elle le fait elle-même : « Ouvrir » dans son propre
panneau, « Enregistrer » sous un nom neuf, « Nouveau ». La copie restait donc en
arrière, et rien n'était vérifié — l'item 9 était le seul du dossier qui n'avait
été constaté que statiquement.

Mesure d'abord (`tests\_sortie\probe\mesure9.py`, rejouee en sections 2 et 7 de
cette suite) : sur cinq gestes, quatre envoyaient `designer.exe` éditer un autre
fichier que celui de l'écran, ou aucun fichier là où l'élève en regardait un. Les
deux plus méchants ne sont pas symétriques :

  • ouvrir un vieux projet par-dessus le dos de l'élève, qui enregistre dans un
    fichier sans jamais l'avoir affiché ;
  • et le contraire, plus trompeur encore : après un « Ouvrir » depuis la vue,
    Designer se lançait VIDE — l'élève croyait que son interface n'existait pas.

La correction ne répare pas la copie, elle la supprime : `_current_ui_path()`
relit `vue.ui_file`, le seul témoin qui sait ce que l'élève voit, et le module ne
garde plus aucun global à désynchroniser. `get_view(..., create=False)` : demander
« quel fichier affichez-vous ? » n'a pas le droit d'ouvrir l'onglet de l'élève.

Sections :
  1  la commande interroge la vue, et ne la crée pas
  2  les cinq gestes de l'élève, avec une vraie vue
  3  la commande ne se souvient de rien entre deux cliques
  4  plus de copie : ni global, ni écriture, et un faux miroir ne distrait plus
  5  le fichier a disparu, ou n'a jamais existé
  6  un chemin relatif devient absolu
  7  « Ajouter Annexe + interface » et deux refus ne détournent pas la cible
  8  les pins de code : qui demande, quand, et quoi
"""
import ast
import importlib
import io
import os
import shutil
import sys
import types

import chemins

BUNDLE = chemins.BUNDLE
COPIE = os.environ.get("TUNISIASCHOOLS_COPIE")
PKG = "thonnycontrib.tunisiaschools"
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BUNDLE, "Lib", "site-packages")
if SITE not in sys.path:
    sys.path.insert(0, SITE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tkinter as tk                                          # noqa: E402

mod = importlib.import_module(PKG)
# Une note obtenue sur le fichier livre alors que le mutant etait vise ne prouve
# rien : la suite doit savoir quel paquet elle a sous la main.
COPIE_INIT = os.path.abspath(mod.__file__)
COPIE_VUE = os.path.abspath(mod.UIViewer.__file__)

D = os.path.join(HERE, "_sortie", "designer_cible")
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)

results = []
a_l_envers = []


def check(*a):
    """(condition, libelle, detail) ou (libelle, condition, detail) — le second
    ordre est celui du depot ; la section 8 refuse une suite ecrite a l'envers."""
    if isinstance(a[0], str):
        cond, msg, detail = a[1], a[0], (a[2] if len(a) > 2 else None)
    else:
        cond, msg, detail = a[0], a[1], (a[2] if len(a) > 2 else None)
        a_l_envers.append("ligne %d : %s" % (sys._getframe(1).f_lineno, msg))
    detail = "" if detail is None else str(detail)
    if len(detail) > 200:
        detail = detail[:200] + "…"
    results.append((msg, bool(cond), detail))
    print(("PASS  " if cond else "FAIL  ") + msg + (("  <- " + detail) if detail else ""))


def CHEMIN(nom):
    return os.path.join(D, nom)


FORME = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>%s</class>
 <widget class="QDialog" name="%s">
  <property name="geometry"><rect><x>0</x><y>0</y><width>300</width><height>150</height></rect></property>
  <property name="windowTitle"><string>%s</string></property>
  <widget class="QPushButton" name="btnValider">
   <property name="geometry"><rect><x>20</x><y>20</y><width>100</width><height>30</height></rect></property>
   <property name="text"><string>%s</string></property>
  </widget>
 </widget>
</ui>
'''


def ecrire_ui(nom, classe, titre):
    p = CHEMIN(nom)
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(FORME % (classe, classe, titre, titre))
    return p


A = ecrire_ui("a.ui", "FormA", "Fenetre A")
B = ecrire_ui("b.ui", "FormB", "Fenetre B")
C = CHEMIN("c.ui")                     # n'existe qu'apres le premier _save()
PROGRAMME = CHEMIN("programme.py")
with io.open(PROGRAMME, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("print('bonjour')\n")

EXE = CHEMIN("designer.exe")
with open(EXE, "wb") as fh:
    fh.write(b"MZ faux designer")


# ── les faux de service ───────────────────────────────────────────────────
class Boite:
    """Les boites de Tk, enregistrees ; les reponses aux questions se pilotent
    a la file — une file vide ne doit jamais repondre « oui » par defaut (la
    lecon de test_designer.py : un refus silencieux passait pour un accord)."""

    def __init__(self):
        self.calls = []
        self.reponses = []

    def puis(self, *reponses):
        self.reponses = list(reponses)
        return self

    def showerror(self, titre, msg, **kw):
        self.calls.append(("error", titre, msg))

    showwarning = showerror
    showinfo = showerror

    def askyesno(self, titre, msg, **kw):
        self.calls.append(("ask", titre, msg))
        if not self.reponses:
            raise AssertionError("une question a ete posee sans reponse preparee")
        return self.reponses.pop(0)


dialogues = Boite()
lances = []


def faux_popen(args, **kw):
    lances.append({"args": list(args), "kw": kw})
    return types.SimpleNamespace(wait=lambda: 0, poll=lambda: None,
                                 terminate=lambda: None, kill=lambda: None)


mod.subprocess = types.SimpleNamespace(Popen=faux_popen,
                                       run=lambda *a, **k: None)
mod.messagebox = dialogues
mod.find_designer = lambda: os.path.abspath(EXE)
mod.askopenfilename = lambda **kw: ""

# La vue se construit avec le module qui l'herberge : `import UIViewer` se
# chargerait d'une SECONDE copie du fichier, que la commande ne verrait pas.
UIMOD = mod.UIViewer
UIMOD.messagebox = dialogues
UIMOD.filedialog = types.SimpleNamespace(
    askopenfilename=lambda **kw: "",
    asksaveasfilename=lambda **kw: C)
UIMOD.get_workbench = lambda: None
UiViewerPlugin = UIMOD.UiViewerPlugin


class FauxMenu:
    """Le menu PyQt5, vu par `_clear_dynamic_menu_items` : la section 7 clique le
    bouton « Ajouter Annexe + interface », qui y touche vraiment."""

    def __init__(self):
        self.items = ["Ajouter Annexe", "Ajouter Annexe + interface",
                      "Ouvrir dans Designer"]

    def index(self, label):
        return self.items.index(label)

    def delete(self, i):
        del self.items[i]


class WB:
    """La workbench, autant que la commande la regarde.

    `get_view` imite le vrai Thonny : `create=False` sur une vue jamais ouverte
    leve une RuntimeError, et `create=True` construit le widget. Un faux qui
    accepterait n'importe quel appel laisserait passer la faute que la section 1
    cherche : ouvrir l'onglet de l'eleve pour lui demander une information.
    """

    def __init__(self, vue=None):
        self.vue = vue
        self.demandes = []
        self.crees = []
        self.montrees = []
        self.opts = {}
        self.menu = FauxMenu()
        self.commands = {}

    def get_view(self, nom, create=True):
        self.demandes.append((nom, create))
        if self.vue is None:
            if create:
                self.crees.append(nom)
                raise AssertionError("la workbench factice ne sait pas creer la vue")
            raise RuntimeError("View %s not created" % nom)
        return self.vue

    def show_view(self, nom, visible=True):
        self.montrees.append(nom)

    def get_menu(self, nom):
        return self.menu

    def _publish_command(self, cid, menu, label, handler=None):
        self.commands[cid] = label

    def get_option(self, nom, defaut=None):
        return self.opts.get(nom, defaut)

    def set_option(self, nom, valeur):
        self.opts[nom] = valeur


wb = WB()
mod.get_workbench = lambda: wb


def lance():
    """Un « Ouvrir dans Designer » mesure : ce que le processus recoit, et ce
    que l'eleve a du lire pendant."""
    del lances[:]
    del dialogues.calls[:]
    ok = mod.open_in_designer()
    args = lances[0]["args"] if lances else None
    recu = (args[1] if args and len(args) > 1 else "")
    return {"ok": ok, "args": args, "recu": recu, "boites": list(dialogues.calls),
            "nb": len(lances)}


def vise(mesure):
    """Le fichier recu, normalise pour la comparaison (ou "")."""
    return os.path.abspath(mesure["recu"]) if mesure["recu"] else ""


def pareil(mesure, attendu):
    if not attendu:
        return not mesure["recu"]
    return bool(mesure["recu"]) and os.path.abspath(attendu) == vise(mesure)


def nom(chemin):
    return os.path.basename(chemin) if chemin else "(rien)"


racine = tk.Tk()
racine.withdraw()
fenetres = []


def fenetre(nom_fenetre):
    top = tk.Toplevel(racine)
    top.title(nom_fenetre)
    top.geometry("980x680+30+30")
    top.update()
    v = UiViewerPlugin(top)
    v.pack(fill=tk.BOTH, expand=True)
    top.update()
    fenetres.append(top)
    return top, v


print("=== 1. la commande interroge la vue, et ne la cree pas ===")
check("paquet vise : %s" % COPIE_INIT,
      (not COPIE) or COPIE_INIT == os.path.abspath(os.path.join(COPIE, "__init__.py")),
      "TUNISIASCHOOLS_COPIE=%s" % COPIE)
check("la vue vient du meme paquet que le module",
      (not COPIE) or COPIE_VUE == os.path.abspath(os.path.join(COPIE, "UIViewer.py")),
      COPIE_VUE)
top0, v0 = fenetre("cible-vierge")
wb.vue = v0
m = lance()
check("vierge : Designer part sans fichier et sans question",
      m["ok"] is True and m["recu"] == "" and m["boites"] == [] and m["nb"] == 1, m)
check("vierge : la vue a ete interrogee, jamais creee",
      wb.demandes and all(create is False for _, create in wb.demandes), wb.demandes)
check("vierge : aucun onglet fabrique pour repondre a une question",
      wb.crees == [], wb.crees)
check("vierge : c'est bien la vue du concepteur qui est interrogee",
      set(nomVue for nomVue, _ in wb.demandes) == {"UiViewerPlugin"}, wb.demandes)
wb.vue = None
m = lance()
check("aucune vue ouverte : rien a ouvrir, et la commande tient",
      m["ok"] is True and m["recu"] == "" and m["boites"] == [], m)


class WB_SansGet(WB):
    def get_view(self, *a, **k):
        raise AttributeError("'Workbench' object has no attribute 'get_view'")


wb = WB_SansGet()
m = lance()
check("une workbench sans get_view ne fait pas tomber la commande",
      m["ok"] is True and m["recu"] == "", m)
wb = WB(v0)
mod.get_workbench = lambda: wb

print("\n=== 2. les gestes de l'eleve, avec une vraie vue ===")
top1, v1 = fenetre("cible-gestes")
wb.vue = v1
gestes = [
    ("a. rien d'ouvert encore", lambda: None, ""),
    ("b. Ouvrir a.ui dans la vue", lambda: v1.load_new_ui_file(A), A),
    ("c. Ouvrir b.ui dans la vue", lambda: v1.load_new_ui_file(B), B),
    ("d. Nouveau", lambda: v1._new(), ""),
]
for etiquette, geste, attendu in gestes:
    geste()
    m = lance()
    check("%s : Designer recoit le fichier de l'ecran" % etiquette,
          pareil(m, attendu), (nom(m["recu"]), nom(attendu)))
    check("%s : le nom passe a Popen est absolu" % etiquette,
          not m["recu"] or os.path.isabs(m["recu"]), m["recu"])
    check("%s : aucune question n'est posee au passage" % etiquette,
          m["boites"] == [], [c[0] for c in m["boites"]])
    check("%s : un seul processus par clique" % etiquette, m["nb"] == 1, m["nb"])
    check("%s : l'executable reste la premiere moitie de la ligne" % etiquette,
          bool(m["args"]) and os.path.abspath(m["args"][0]) == os.path.abspath(EXE),
          m["args"])
# e. « Enregistrer » sous un nom neuf, depuis le document neuf du geste d.
v1._add_widget("QPushButton")
v1._save()
m = lance()
check("e. Enregistrer sous c.ui : le nom neuf part a Designer",
      pareil(m, C) and os.path.isfile(C), (nom(m["recu"]), v1.ui_file))
check("e. et la vue le reconnait aussi", v1.ui_file == C, v1.ui_file)
check("e. le fichier que l'ancien temoin aurait designe n'est plus jamais vise",
      vise(m) != os.path.abspath(A), nom(m["recu"]))

print("\n=== 3. la commande ne se souvient de rien entre deux cliques ===")
top2, v2 = fenetre("cible-deux-vues")
v2.load_new_ui_file(A)
wb.vue = v2
check("premiere clique : le fichier de la vue montree",
      pareil(lance(), A), nom(lance()["recu"]))
wb.vue = v1
check("deuxieme clique sur l'autre vue : la cible a suivi, sans memoire",
      pareil(lance(), C), nom(lance()["recu"]))
wb.vue = v2
check("retour a la premiere vue : la cible revient avec elle",
      pareil(lance(), A), nom(lance()["recu"]))

print("\n=== 4. plus de copie, et un faux miroir ne distrait plus rien ===")
check("le module n'a plus d'attribut qt_ui_file a rater",
      not hasattr(mod, "qt_ui_file"), getattr(mod, "qt_ui_file", None))
init_src = io.open(os.path.join(os.path.dirname(COPIE_INIT), "__init__.py"),
                   encoding="utf-8").read()
check("et le nom n'apparait plus nulle part dans le fichier",
      "qt_ui_file" not in init_src,
      [l.strip() for l in init_src.splitlines() if "qt_ui_file" in l][:3])
arbre = ast.parse(init_src)
globaux = {nomme for n in ast.walk(arbre) if isinstance(n, ast.Global)
           for nomme in n.names}
check("plus aucun `global` dans le module : rien a synchroniser",
      globaux == set(), globaux)
# le geste de l'ancien bug, rejoue avec un nom qui y ressemble : la commande ne
# doit plus du tout le regarder.
mod.qt_ui_file = A
v2.ui_file = B
m = lance()
check("un faux miroir tendu a la commande ne la detourne pas",
      pareil(m, B), (nom(m["recu"]), nom(A)))
del mod.qt_ui_file
check("et la commande n'a pas cree l'attribut par erreur en relisant",
      not hasattr(mod, "qt_ui_file"), getattr(mod, "qt_ui_file", None))

print("\n=== 5. le fichier a disparu, ou n'a jamais existe ===")
v2.load_new_ui_file(A)
check("sur place : la cible est bien le fichier charge",
      pareil(lance(), A), nom(lance()["recu"]))
deplace = CHEMIN("a_deplace.ui")
os.replace(A, deplace)
m = lance()
check("deplace : Designer s'ouvre sans argument, sans question, sans erreur",
      m["ok"] is True and m["recu"] == "" and m["boites"] == [],
      (nom(m["recu"]), [c[0] for c in m["boites"]]))
os.replace(deplace, A)
m = lance()
check("remis en place : ni la vue ni la commande n'ont rien perdu",
      pareil(m, A), nom(m["recu"]))
top3, v3 = fenetre("cible-sans-titre")
wb.vue = v3
v3._add_widget("QPushButton")
v3._add_widget("QLineEdit")
m = lance()
check("jamais enregistre : deux widgets a l'ecran et pourtant pas d'argument",
      m["recu"] == "" and len(v3.widgets_data) == 2, (nom(m["recu"]), len(v3.widgets_data)))
check("jamais enregistre : rien n'est demande a l'eleve pour autant",
      m["boites"] == [], [c[0] for c in m["boites"]])

print("\n=== 6. un chemin relatif devient absolu ===")
top4, v4 = fenetre("cible-relatif")
wb.vue = v4
v4.load_new_ui_file(A)
CWD_ORIG = os.getcwd()
os.chdir(D)
try:
    # un ui_file relatif est un etat possible (un chemin rendu par une autre
    # brique) : ce qui part a Popen ne doit jamais dependre du dossier courant.
    v4.ui_file = os.path.relpath(A, D)
    m = lance()
    check("relatif dans ui_file : Popen recoit un absolu",
          os.path.isabs(m["recu"]) and os.path.samefile(m["recu"], A),
          (v4.ui_file, nom(m["recu"])))
    v4.ui_file = os.path.join("sous_dossier_absent", "fantome.ui")
    m = lance()
    check("relatif et absent : pas d'argument, pas de plantage",
          m["ok"] is True and m["recu"] == "", nom(m["recu"]))
finally:
    os.chdir(CWD_ORIG)

print("\n=== 7. « Ajouter Annexe + interface » et deux refus ===")
top5, v5 = fenetre("cible-annexe")
wb_annexe = WB(v5)
wb_annexe.get_view = lambda nom_vue, create=True: v5     # le bouton cree la vue
mod.get_workbench = lambda: wb_annexe
mod.askopenfilename = lambda **kw: B
insere = []
mod._insert_in_editor = lambda code, pos="insert": insere.append(code)
v5.load_new_ui_file(A)
check("annexe : avant le bouton, la cible vient de la vue",
      pareil(lance(), A), nom(lance()["recu"]))
mod.add_pyqt_code()
m = lance()
check("annexe acceptee : la cible a suivi la vue, sans que le module ecrive",
      pareil(m, B), (nom(m["recu"]), v5.ui_file))
check("annexe acceptee : la vue montre bien le second fichier",
      v5.ui_file == B, v5.ui_file)
chemin_inserre = ""
if insere and 'loadUi ("' in insere[0]:
    chemin_inserre = insere[0].split('loadUi ("')[1].split('")')[0]
check("annexe acceptee : le code colle nomme le MEME fichier que Designer",
      bool(chemin_inserre) and os.path.isfile(chemin_inserre.replace("/", os.sep))
      and os.path.samefile(chemin_inserre.replace("/", os.sep), B),
      chemin_inserre)
# refus du lecteur : le fichier choisi n'est pas une fenetre
mod.askopenfilename = lambda **kw: PROGRAMME
mod.add_pyqt_code()
m = lance()
check("annexe refusee par le lecteur : la cible reste au fichier affiche",
      pareil(m, B), nom(m["recu"]))
check("annexe refusee par le lecteur : la vue n'a pas bouge",
      v5.ui_file == B, v5.ui_file)
# refus de l'eleve (item 13) : un travail en cours protege la fenetre affichee
v5._add_widget("QLabel")
mod.askopenfilename = lambda **kw: A
dialogues.puis(False)
mod.add_pyqt_code()
# les boites de LA gesture : `lance()` remet la liste a zero, et la question est
# posee pendant que le bouton travaille, pas pendant que Designer s'ouvre.
pendant = list(dialogues.calls)
m = lance()
check("annexe refusee par l'eleve : la question a bien ete posee",
      any(c[0] == "ask" for c in pendant), [c[0] for c in pendant])
check("annexe refusee par l'eleve : une seule question, pas de bolee",
      [c[0] for c in pendant] == ["ask"], [c[0] for c in pendant])
m = lance()
check("annexe refusee par l'eleve : Designer vise toujours le fichier a l'ecran",
      pareil(m, B), nom(m["recu"]))
check("annexe refusee par l'eleve : le fichier refuse n'a pas ete adopte",
      v5.ui_file == B, v5.ui_file)
mod.askopenfilename = lambda **kw: ""
mod.get_workbench = lambda: wb
wb.vue = v5

print("\n=== 8. les pins de code : qui demande, quand, et quoi ===")
fonctions = {n.name: n for n in ast.walk(arbre) if isinstance(n, ast.FunctionDef)}


def corps(nom_fonction):
    n = fonctions.get(nom_fonction)
    return ast.get_source_segment(init_src, n) if n else ""


cible = corps("_current_ui_path")
check("_current_ui_path existe et relit la vue",
      cible and "ui_file" in cible and "_vue_concepteur()" in cible, cible[:200])
check("_current_ui_path ne connait aucun global a reconcilier",
      cible and "global" not in cible and "qt_ui" not in cible, cible[:200])
check("_current_ui_path verifie que le fichier existe encore",
      cible and "os.path.isfile" in cible, cible[:200])
demandeur = corps("_vue_concepteur")
check("_vue_concepteur passe create=False", demandeur and "create=False" in demandeur,
      demandeur[:200])
check("_vue_concepteur ne laisse rien remonter d'une workbench absente",
      demandeur and "except" in demandeur and "return None" in demandeur, demandeur[:220])
ouverture = corps("open_in_designer")
check("open_in_designer demande le fichier au moment du lancement",
      ouverture and "_current_ui_path()" in ouverture, ouverture[:200])
check("et seulement apres avoir trouve le binaire",
      ouverture and 0 <= ouverture.index("find_designer()") < ouverture.index(
          "_current_ui_path()"),
      [l.strip() for l in (ouverture or "").splitlines()
       if "find_designer" in l or "_current_ui_path" in l])
add = corps("add_pyqt_code")
check("add_pyqt_code n'annonce plus aucun fichier",
      add and "qt_ui_file" not in add, add[:200])
check("et attend toujours la reponse de la vue avant de toucher au menu",
      add and 0 <= add.index("load_new_ui_file") < add.index(
          "_clear_dynamic_menu_items"),
      [l.strip() for l in (add or "").splitlines()
       if "load_new_ui_file" in l or "_clear_dynamic_menu_items" in l])
run = corps("_run_designer")
check("_run_designer reste muet sur le fond : l'executable, puis le fichier s'il y en a",
      run and "[exe] + ([ui_path] if ui_path else [])" in run, run[:200])
check("aucune boite Qt dans le greffon", init_src.count("QMessageBox") == 0,
      init_src.count("QMessageBox"))

for top in fenetres:
    top.destroy()
racine.update()
shutil.rmtree(D, ignore_errors=True)

check("aucun controle de cette suite n'est ecrit dans l'autre sens",
      a_l_envers == [], a_l_envers)

fails = [r for r in results if not r[1]]
print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
for label, ok, detail in fails:
    print("FAIL  %s  <- %s" % (label, detail))
sys.exit(1 if fails else 0)
