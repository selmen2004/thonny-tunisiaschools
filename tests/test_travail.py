r"""Item 13 : un « Ouvrir » qui reussit ne doit plus effacer un travail non enregistre.

L'item 3 a ferme la porte du fichier refuse : la vue ne bouge plus quand le
lecteur n'a rien reconnu. Il restait le cas d'en face, le plus frequent des deux
— l'eleve a commence une fenetre, il clique Ouvrir, et choisit *le bon* fichier.
`load_new_ui_file` remplacait alors le modele sans un mot : les widgets disparais-
saient de l'ecran, `reset_history()` jetait tout l'historique, et comme aucun
drapeau ne disait si l'ecran avait ete ecrit depuis le disque, rien ne pouvait
poser la question. Le travail d'avant n'etait pas annulable, pas enregistre, pas
signale.

Le concepteur connaissait deja ce risque — « Nouveau » demandait
« Effacer le travail en cours ? » — mais avec une condition qui ne veut rien
dire : `self.widgets_data` est rempli aussi quand la fenetre affichee sort tout
juste du fichier. Deux notions de « travail a perdre » dans le meme fichier, et
la moins juste etait celle qui protegemait le mieux.

La suite verifie la regle neuve : un pas d'historique leve `_travail_modifie`
(`_push`), une ecriture ou une lecture le remise a zero (`_save`,
`reset_history`), et des que le drapeau est leve, remplacer la fenetre demande
l'avis de l'eleve — sur les trois chemins qui ouvrent un fichier, y compris le
bouton « Ajouter Annexe + interface » du menu Thonny. Le refus de l'eleve laisse
tout en place, y compris le fichier que la vue etait en train de montrer.
"""
import ast
import importlib
import os
import shutil
import sys
import types
from xml.etree import ElementTree as ET

import chemins

BUNDLE = chemins.BUNDLE
# TUNISIASCHOOLS_COPIE : le dossier d'une COPIE mutee du paquet, pose par
# tests\mutants_cible.py. Sans lui, c'est le module livre qui est teste. La
# section 8 lit les sources de PLUGIN : si elle lisait le fichier livre pendant
# qu'un mutant est vise, ses pins ne verraient jamais la faute.
PLUGIN = os.environ.get("TUNISIASCHOOLS_COPIE") or \
    chemins.PAQUET
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tkinter as tk                                   # noqa: E402
import UIViewer                                        # noqa: E402
from UIViewer import UiViewerPlugin                    # noqa: E402

# dialogues : ce que le plugin a demande ou annonce, dans l'ordre.
dialogues = []
reponse = [True]       # ce que « l'eleve » repond a Oui/Non
choix = [None]         # le chemin que la fenetre « Ouvrir » va rendre


def _askyesno(*a, **k):
    dialogues.append(("yesno",) + a)
    return reponse[0]


UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: dialogues.append(("error",) + a),
    showinfo=lambda *a, **k: dialogues.append(("info",) + a),
    askyesno=_askyesno)
# Les deux fenetres de fichiers sont bouchonnees : sans elles, une suite lancee
# par run_all resterait bloquee sur une boite modale invisible.
UIViewer.filedialog = types.SimpleNamespace(
    askopenfilename=lambda **k: choix[0],
    asksaveasfilename=lambda **k: "")
UIViewer.get_workbench = lambda: None

racine = tk.Tk()
racine.withdraw()

D = os.path.join(HERE, "_sortie", "travail")
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)


def CHEMIN(nom):
    return os.path.join(D, nom)


NOTE_UI = r'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MaFenetre</class>
 <widget class="QDialog" name="FenetreNote">
  <property name="geometry"><rect><x>0</x><y>0</y><width>360</width><height>220</height></rect></property>
  <property name="windowTitle"><string>Saisie des notes</string></property>
  <widget class="QLabel" name="titre">
   <property name="geometry"><rect><x>20</x><y>16</y><width>200</width><height>24</height></rect></property>
   <property name="text"><string>Eleve</string></property>
  </widget>
  <widget class="QLineEdit" name="saisie">
   <property name="geometry"><rect><x>20</x><y>48</y><width>200</width><height>26</height></rect></property>
   <property name="placeholderText"><string>Nom</string></property>
  </widget>
  <widget class="QPushButton" name="ok">
   <property name="geometry"><rect><x>20</x><y>90</y><width>90</width><height>28</height></rect></property>
   <property name="text"><string>Valider</string></property>
  </widget>
 </widget>
 <resources/>
 <connections/>
</ui>
'''
AUTRE_UI = NOTE_UI.replace("FenetreNote", "AutreFenetre") \
    .replace("<string>Saisie des notes</string>", "<string>Autre titre</string>")
PROGRAMME_PY = (
    "from PyQt5.uic import loadUi\n"
    "from PyQt5.QtWidgets import QApplication\n"
    "\n"
    "app = QApplication([])\n"
    'windows = loadUi("note.ui")\n'
    "windows.show()\n"
    "app.exec_()\n"
)


def ecrit(chemin, texte):
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)


ecrit(CHEMIN("note.ui"), NOTE_UI)
ecrit(CHEMIN("autre.ui"), AUTRE_UI)
ecrit(CHEMIN("programme.py"), PROGRAMME_PY)

bilan = [0, 0]
a_l_envers = []


def check(*a):
    """L'ordre des arguments est la premiere source de faux controles de ce
    depot : un libelle passe avant la condition la rend toujours vraie (voir
    test_pose.py et test_tr.py, qui l'ecrivent ainsi). Ici le sens officiel est
    (libelle, condition, detail), et le controle final exige que la suite entiere
    s'y tienne — sinon un controle ecrit a l'envers se lit comme un succes."""
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


def harnais(path):
    """Le modele seul, sans vue : pour parler a l'XML et au drapeau."""
    v = object.__new__(UiViewerPlugin)
    v.widgets_data, v.selected_idx = [], None
    v.widget_counter, v.ui_file = 0, path
    v.root_widget_name, v.root_widget_class = "Form", "QDialog"
    v.root_geometry, v.root_title = (0, 0, 640, 480), "Form"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    v._undo_stack, v._redo_stack = [], []
    return v


def dessines(v):
    return [c.cget("text") for c in v.ui_frame.winfo_children()
            if getattr(c, "_is_label", False)]


def etat(v):
    """Tout ce qu'un Ouvrir est cense remplacer — et rien d'autre."""
    return {
        "chemin":    v.ui_file,
        "modele":    [(c, p["name"]) for c, p in v.widgets_data],
        "racine":    (v.root_widget_name, v.root_widget_class),
        "titre":     v.root_title,
        "geometrie": tuple(v.root_geometry),
        "graine":    v.widget_counter,
        "uids":      list(v._source_uids),
        "src_root":  dict(v._src_root),
        "journal":   len(v._undo_stack),
        "retabli":   len(v._redo_stack),
        "etiquette": v._title_lbl.cget("text"),
        "peint":     dessines(v),
        "selection": v.selected_idx,
        "drapeau":   v._travail_non_enregistre(),
    }


def octets(chemin):
    with open(chemin, "rb") as f:
        return f.read()


def noms_dun_fichier(chemin):
    return [w.get("name") for w in ET.parse(chemin).iter("widget")]


def questions():
    return [d for d in dialogues if d[0] == "yesno"]


def la_question(numer=0):
    """La question Oui/Non numero `numer`, ou une question vide si le plugin n'en
    a pose aucune. Et c'est bien le cas a ecrire : l'absence de question EST le
    defaut que l'item 13 corrige. Un controle qui lirait `questions()[0]`
    planterait la suite sur un IndexError, et le bilan — comme tout ce qui vient
    apres — disparaitrait avec lui."""
    qs = questions()
    return qs[numer] if numer < len(qs) else ("yesno", "AUCUNE QUESTION POSEE", "")


def une_ouverture(v, chemin, oui=True):
    """Le geste complet : bouton Ouvrir de la barre d'outils, chemin choisi dans
    la fenetre de fichiers, reponse a la question eventuelle. Rend la valeur que
    le plugin donne a l'eleve."""
    dialogues.clear()
    reponse[0] = oui
    choix[0] = chemin
    v._open()
    return list(dialogues)


# ── 1. le geste : ouvrir par-dessus un travail, l'eleve dit oui ───────────
print("=== 1. ouvrir par-dessus un travail en cours, c'est demande ===")
top, v = fenetre("travail-1")
check("une fenetre qui sort du fichier n'a rien a perdre",
      v.load_new_ui_file(CHEMIN("note.ui")) is True and
      not v._travail_non_enregistre(), v._travail_non_enregistre())
check("et un modele de trois widgets, peint",
      len(v.widgets_data) == 3 and dessines(v) == ["titre", "saisie", "ok"],
      dessines(v))
v._add_widget("QLabel")
check("des qu'un widget est ajoute, l'ecran ne correspond plus au fichier",
      v._travail_non_enregistre() is True)
dialogues.clear()
note_avant, autre_avant = octets(CHEMIN("note.ui")), octets(CHEMIN("autre.ui"))
appels = une_ouverture(v, CHEMIN("autre.ui"), oui=True)
check("le plugin a pose une seule question, pas deux",
      len([a for a in appels if a[0] == "yesno"]) == 1, appels)
q = la_question()
check("la question est un Oui/Non titre « Ouvrir »", q[0] == "yesno" and q[1] == "Ouvrir", q)
check("elle nomme le fichier que l'eleve a choisi",
      "autre.ui" in q[2], q[2])
check("elle dit que le travail en cours n'est pas enregistre",
      "enregistre" in q[2] and "travail" in q[2], q[2])
check("et qu'il faut l'enregistrer avant, pas apres coup",
      "enregistrez" in q[2], q[2])
check("le fichier s'ouvre apres l'accord",
      v.ui_file == CHEMIN("autre.ui") and v.root_widget_name == "AutreFenetre",
      (v.ui_file, v.root_widget_name))
check("le titre de la vue a suivi",
      v._title_lbl.cget("text") == "autre.ui", v._title_lbl.cget("text"))
check("l'ajout de l'eleve a laisse la place aux trois widgets du fichier",
      [p["name"] for _c, p in v.widgets_data] == ["titre", "saisie", "ok"],
      [p["name"] for _c, p in v.widgets_data])
check("un fichier qui s'ouvre ne laisse aucun pas derriere lui",
      v._undo_stack == [] and v._redo_stack == [],
      (len(v._undo_stack), len(v._redo_stack)))
check("et n'est plus « modifie », donc la prochaine ouverture ne demandera rien",
      v._travail_non_enregistre() is False)
check("ouvrir n'ecrit dans aucun des deux fichiers",
      octets(CHEMIN("note.ui")) == note_avant and
      octets(CHEMIN("autre.ui")) == autre_avant)

# ── 2. l'eleve dit non : la fenetre ne bouge pas d'un pixel ───────────────
print("=== 2. « Non » veut dire que rien n'est remplace ===")
top, v = fenetre("travail-2")
v.load_new_ui_file(CHEMIN("note.ui"))
v._add_widget("QLabel")
avant = etat(v)
arbre_avant = v._source_ui
note_avant = octets(CHEMIN("note.ui"))
autre_avant = octets(CHEMIN("autre.ui"))
appels = une_ouverture(v, CHEMIN("autre.ui"), oui=False)
check("la question a bien ete posee", len(questions()) == 1, appels)
check("etat par etat, la vue est exactement celle d'avant", etat(v) == avant,
      {k: (avant[k], etat(v)[k]) for k in avant if avant[k] != etat(v)[k]})
# Le piege propre a l'item 13 : la question vient APRES une lecture reussie, donc
# _parse_ui a deja commit l'arbre, les uid, la racine et la graine du fichier
# refuse. Un « non » qui ne rendrait pas ces reperes laisserait l'eleve ecrire ses
# widgets dans l'arbre XML de l'autre fichier — mesure au premier essai de cette
# suite : note.ui enregistrée avec la racine « AutreFenetre ».
check("l'arbre adopte est rendu a la fenetre affichee, pas garde du fichier refuse",
      v._source_ui is arbre_avant and v.root_widget_name == "FenetreNote" and
      list(v._source_uids) == avant["uids"] and dict(v._src_root) == avant["src_root"],
      (v._source_ui is arbre_avant, v.root_widget_name, list(v._source_uids)))
check("le fichier en cours reste le premier", v.ui_file == CHEMIN("note.ui"), v.ui_file)
check("le quatrieme widget est toujours a l'ecran", len(v.widgets_data) == 4,
      len(v.widgets_data))
check("l'historique aussi : Annuler est encore possible",
      avant["journal"] == 1 and len(v._undo_stack) == 1, len(v._undo_stack))
check("aucune des deux fenetres n'a ete ouverte par-derriere",
      octets(CHEMIN("autre.ui")) == autre_avant and
      octets(CHEMIN("note.ui")) == note_avant)
v._save()
check("le prochain Enregistrer vise toujours le fichier affiche",
      v.ui_file == CHEMIN("note.ui"), v.ui_file)
check("le fichier que l'eleve a refuse n'a rien recu",
      octets(CHEMIN("autre.ui")) == autre_avant,
      noms_dun_fichier(CHEMIN("autre.ui")))
# L'index se lit avec un filet : un mutant qui ne pose jamais la question aura
# adopte le fichier refuse, et la suite doit alors rougir, pas planter sur un
# IndexError (le bilan et tout ce qui suit disparaitraient avec la trace).
nom_ajoute = (v.widgets_data[3][1]["name"] if len(v.widgets_data) > 3
              else "AUCUN QUATRIEME WIDGET")
check("le travail de l'eleve est bien passe dans note.ui",
      noms_dun_fichier(CHEMIN("note.ui")) ==
      ["FenetreNote", "titre", "saisie", "ok", nom_ajoute],
      noms_dun_fichier(CHEMIN("note.ui")))
racine_ecrite = ET.parse(CHEMIN("note.ui")).getroot().find("widget")
check("et c'est bien sa fenetre, pas celle du fichier refuse",
      racine_ecrite.get("name") == "FenetreNote" and
      racine_ecrite.get("class") == "QDialog",
      (racine_ecrite.get("name"), racine_ecrite.get("class")))
check("le titre du fichier refuse n'a pas glisse dans l'en-tete",
      racine_ecrite.find("./property[@name='windowTitle']/string") is not None and
      "Autre titre" not in open(CHEMIN("note.ui"), encoding="utf-8").read(),
      open(CHEMIN("note.ui"), encoding="utf-8").read()[:400])
ecrit(CHEMIN("note.ui"), NOTE_UI)
ecrit(CHEMIN("autre.ui"), AUTRE_UI)

# ── 3. un ecran propre ne merite aucune question ─────────────────────────
print("=== 3. rien a perdre = aucune question ===")
top, v = fenetre("travail-3")
dialogues.clear()
check("ouvrir une fenetre vide ne demande rien",
      v.load_new_ui_file(CHEMIN("note.ui")) is True and dialogues == [],
      dialogues)
check("ouvrir un deuxieme fichier par-dessus un premier intact ne demande pas plus",
      v.load_new_ui_file(CHEMIN("autre.ui")) is True and dialogues == [],
      dialogues)
v._add_widget("QLabel")
check("la, le drapeau est leve", v._travail_non_enregistre() is True)
dialogues.clear()
v._save()
check("Enregistrer remet le drapeau a zero",
      v._travail_modifie is False and v._travail_non_enregistre() is False)
check("et la question ne se pose plus",
      v.load_new_ui_file(CHEMIN("note.ui")) is True and questions() == [],
      questions())
dialogues.clear()
check("Nouveau sur un document deja enregistre ne demande rien non plus",
      (v._new() or True) and questions() == [] and v.widgets_data == [],
      (questions(), len(v.widgets_data)))
check("le drapeau est reste baisse apres Nouveau",
      v._travail_non_enregistre() is False)
ecrit(CHEMIN("note.ui"), NOTE_UI)
ecrit(CHEMIN("autre.ui"), AUTRE_UI)

# ── 4. ce qui leve le drapeau, ce qui l'eteint ───────────────────────────
print("=== 4. le drapeau suit l'ecran, pas l'impression ===")
reponse[0] = True          # « Supprimer ce widget ? » doit se laisser repondre
top, v = fenetre("travail-4")
v.load_new_ui_file(CHEMIN("note.ui"))
check("la lecture seule du fichier laisse le drapeau baisse",
      v._travail_modifie is False)
check("lire le XML sans ouvrir ne leve rien : _parse_ui n'ecrit pas le drapeau",
      v._parse_ui(CHEMIN("autre.ui"))[0] != [] and v._travail_modifie is False)
for nom, geste in [
        ("un ajout", lambda: v._add_widget("QPushButton")),
        ("une copie", lambda: v._duplicate(0)),
        ("un texte change", lambda: v._apply("text", tk.StringVar(value="Oups"), 0)),
        ("une couleur", lambda: v._set_color(0, "color", "#ff0000")),
        ("une suppression", lambda: v._delete(1))]:
    v._travail_modifie = False
    geste()
    check("%s leve le drapeau" % nom, v._travail_modifie is True)
v._travail_modifie = False
v.undo()
check("un simple clic sur une etiquette de la barre n'est pas une modification",
      v._travail_modifie is False)
v._travail_modifie = False
v.redo()
check("et un Retablir non plus : le journal ne s'accuse pas lui-meme",
      v._travail_modifie is False)
v._travail_modifie = True
v.reset_history()
check("reset_history est le seul autre endroit qui l'eteint",
      v._travail_modifie is False)
# Le faux positif assume : le contenu est revenu identique au fichier, le
# drapeau reste leve. Une question de trop est une question, pas une perte.
top, v = fenetre("travail-4b")
v.load_new_ui_file(CHEMIN("note.ui"))
v._add_widget("QLabel")
v.undo()
check("annuler son dernier geste ne rend pas le droit de tout jeter sans le dire",
      v._travail_non_enregistre() is True and len(v.widgets_data) == 3,
      (len(v.widgets_data), v._travail_non_enregistre()))
check("la question sera donc posee, pour rien peut-etre, mais pas pour rien",
      len(une_ouverture(v, CHEMIN("autre.ui"), oui=True)) >= 1 and
      v.ui_file == CHEMIN("autre.ui"))
n = object.__new__(UiViewerPlugin)
n.widgets_data = [("QLabel", {"name": "l", "geometry": (0, 0, 10, 10)})]
n._undo_stack, n._redo_stack = [], []
check("un objet construit hors du constructeur n'a pas de faux souvenir",
      n._travail_non_enregistre() is False)
n._step()
check("et que le premier pas lui leve le drapeau quand meme",
      n._travail_modifie is True)

# ── 5. Nouveau et Ouvrir appliquent la meme regle ────────────────────────
print("=== 5. le meme mot « travail en cours » veut la meme chose partout ===")
top, v = fenetre("travail-5")
v.load_new_ui_file(CHEMIN("note.ui"))
v._add_widget("QLabel")
avant = etat(v)
dialogues.clear()
reponse[0] = False
v._new()
check("Nouveau demande, avec son propre titre",
      len(questions()) == 1 and la_question()[1] == "Nouveau", questions())
check("et le meme libelle qu'avant l'item 13",
      "Effacer le travail en cours ?" in la_question()[2], questions())
check("repondre non laisse les quatre widgets et le fichier",
      len(v.widgets_data) == 4 and v.ui_file == CHEMIN("note.ui"),
      (len(v.widgets_data), v.ui_file))
check("le drapeau n'a pas ete efface par la reponse",
      v._travail_non_enregistre() is True)
check("et la vue est identique, peinture comprise", etat(v) == avant,
      {k: (avant[k], etat(v)[k]) for k in avant if avant[k] != etat(v)[k]})
reponse[0] = True
v._new()
check("repondre oui vide le modele et baisse le drapeau",
      v.widgets_data == [] and v.ui_file is None and
      v._travail_modifie is False and v._title_lbl.cget("text") == "Sans titre",
      (len(v.widgets_data), v.ui_file, v._title_lbl.cget("text")))
# Ce que le vieux garde-fou faisait de trop : une fenetre sortant du fichier,
# donc intacte, n'a rien a demander, meme si elle est pleine de widgets.
top, v = fenetre("travail-5b")
v.load_new_ui_file(CHEMIN("note.ui"))
dialogues.clear()
reponse[0] = True
v._new()
check("Nouveau ne demande plus de vider une fenetre qui sort du disque",
      questions() == [] and v.widgets_data == [], (questions(), v.widgets_data))
check("l'eleve peut la rouvrir, le fichier est intact",
      v.load_new_ui_file(CHEMIN("note.ui")) is True and len(v.widgets_data) == 3)

# ── 6. le fichier refuse ne demande rien ─────────────────────────────────
print("=== 6. on ne demande pas la permission de perdre pour un fichier illisible ===")
top, v = fenetre("travail-6")
v.load_new_ui_file(CHEMIN("note.ui"))
v._add_widget("QLabel")
avant = etat(v)
appels = une_ouverture(v, CHEMIN("programme.py"), oui=True)
check("un choix refuse par le lecteur ne pose aucune question",
      questions() == [], appels)
check("l'eleve est prevenu par le message de l'item 3",
      len([a for a in appels if a[0] == "error"]) == 1, appels)
check("la vue n'a pas bouge", etat(v) == avant,
      {k: (avant[k], etat(v)[k]) for k in avant if avant[k] != etat(v)[k]})
check("le drapeau est toujours leve", v._travail_non_enregistre() is True)
check("et le travail de l'eleve aussi", len(v.widgets_data) == 4, len(v.widgets_data))
appels = une_ouverture(v, CHEMIN("inexistant.ui"), oui=True)
check("un chemin introuvable ne demande pas plus",
      questions() == [] and [a for a in appels if a[0] == "error"], appels)
check("le fichier en cours n'a pas change de mains",
      v.ui_file == CHEMIN("note.ui"), v.ui_file)

# ── 7. le bouton du menu Thonny, lui aussi, demande ──────────────────────
print("=== 7. « Ajouter Annexe + interface » passe par la meme porte ===")
mod = importlib.import_module("thonnycontrib.tunisiaschools")


class FauxWB:
    def __init__(self, vue):
        self.vue = vue
        self.vues_demandees = []
        self.montrees = []
        self.commands = {}

    def get_view(self, name, create=True):
        # la signature reelle de Workbench.get_view : la commande du bouton
        # demande la vue (create par defaut) et _vue_concepteur() la relit avec
        # create=False. Un faux qui ignorerait le mot-cle ne suivrait pas le
        # meme chemin que Thonny, et l'item 9 passerait inapercu.
        self.vues_demandees.append((name, create))
        if name != "UiViewerPlugin":
            raise AssertionError("vue inattendue : %s" % name)
        return self.vue

    def show_view(self, name, flag):
        self.montrees.append(name)

    def get_menu(self, name):
        return []

    def _publish_command(self, cid, menu, label, handler=None):
        self.commands[cid] = label


def bouton(v, chemin, oui):
    """Le geste du menu Thonny : la vraie commande, un vrai travail en cours,
    une reponse differente. Rend ce que le bouton a fait, tel qu'on pouvait le
    voir pendant qu'il le faisait."""
    insere = []
    ancien = (mod.get_workbench, mod.askopenfilename, mod._insert_in_editor,
              list(mod._dynamic_menu_labels))
    wb = FauxWB(v)
    mod.get_workbench = lambda: wb
    mod.askopenfilename = lambda **k: chemin
    mod._insert_in_editor = lambda code, pos="insert": insere.append(code)
    dialogues.clear()
    reponse[0] = oui
    vu = {}
    # ce que Designer editerait avant le clic : la mesure de comparaison, prise
    # par la meme porte que la commande (rien de consomme par le bouton).
    cible_avant = mod._current_ui_path()
    try:
        mod.add_pyqt_code()
        # ces trois-la se lisent pendant que le bouton tient encore le stylo
        # `cible` : ce que « Ouvrir dans Designer » editerait si l'eleve
        # cliquait maintenant. Depuis l'item 9, la vue en est la seule source.
        vu["cible"] = mod._current_ui_path()
        vu["labels"] = list(mod._dynamic_menu_labels)
        vu["montrees"] = list(wb.montrees)
    finally:
        (mod.get_workbench, mod.askopenfilename,
         mod._insert_in_editor) = ancien[:3]
        del mod._dynamic_menu_labels[:]
        mod._dynamic_menu_labels.extend(ancien[3])
    return {"insere": insere, "vue": (v.ui_file, len(v.widgets_data)),
            "dialogues": list(dialogues), "wb": wb, "vu": vu,
            "cible_avant": cible_avant, "labels_avant": list(ancien[3])}


top, v = fenetre("travail-7")
v.load_new_ui_file(CHEMIN("note.ui"))
v._add_widget("QLabel")          # un travail en cours, comme dans la salle
check("le drapeau est leve avant de toucher au menu",
      v._travail_non_enregistre() is True)
# pas besoin de poser un faux « fichier precedent » : la vue a deja le sien,
# note par le vrai load_new_ui_file de la ligne precedente, et c'est lui que
# « Ouvrir dans Designer » editerait si l'eleve cliquait maintenant.
r = bouton(v, CHEMIN("autre.ui"), oui=False)
qs7 = [d for d in r["dialogues"] if d[0] == "yesno"]
check("le bouton demande a la vue, pas au fichier",
      len(qs7) == 1 and bool(qs7) and qs7[0][1] == "Ouvrir", r["dialogues"])
check("refuser n'insere aucun code dans l'editeur", r["insere"] == [], r["insere"])
check("refuser ne change pas le fichier que Designer editerait",
      r["vu"]["cible"] == r["cible_avant"] == os.path.abspath(CHEMIN("note.ui")),
      (r["cible_avant"], r["vu"]["cible"]))
check("refuser ne publie aucune commande de plus",
      r["vu"]["labels"] == r["labels_avant"], r["vu"]["labels"])
check("refuser ne ramene meme pas le concepteur au premier plan",
      r["vu"]["montrees"] == [], r["vu"]["montrees"])
check("la vue montre toujours la fenetre de l'eleve",
      r["vue"] == (CHEMIN("note.ui"), 4), r["vue"])
r = bouton(v, CHEMIN("autre.ui"), oui=True)
check("accepter ouvre le fichier et donne le code",
      r["vue"][0] == CHEMIN("autre.ui") and len(r["insere"]) == 1 and
      "loadUi (" in r["insere"][0], (r["vue"], r["insere"]))
check("le menu annonce desormais le fichier que la vue affiche",
      r["vu"]["cible"] == os.path.abspath(CHEMIN("autre.ui"))
      and os.path.abspath(r["vue"][0]) == r["vu"]["cible"], r["vu"])
check("et les commandes des widgets du nouveau fichier sont publiees",
      len(r["vu"]["labels"]) > len(r["labels_avant"]),
      (r["labels_avant"], r["vu"]["labels"]))
top, v = fenetre("travail-7b")
v.load_new_ui_file(CHEMIN("note.ui"))
r = bouton(v, CHEMIN("note.ui"), oui=True)
check("un ecran propre n'est pas retenu par une question",
      r["dialogues"] == [] and len(r["insere"]) == 1, (r["dialogues"], r["insere"]))

# ── 8. ce qui est ecrit dans le fichier ──────────────────────────────────
print("=== 8. les regles sont dans le code, pas seulement dans les tests ===")
source = open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
arbre = ast.parse(source)
meth = {}
for n in ast.walk(arbre):
    if isinstance(n, ast.FunctionDef):
        meth.setdefault(n.name, n)
corps_push = ast.get_source_segment(source, meth["_push"])
check("_push leve le drapeau : un pas d'historique est un pas par-dessus le fichier",
      "self._travail_modifie = True" in corps_push, corps_push)
corps_reset = ast.get_source_segment(source, meth["reset_history"])
check("reset_history l'eteint", "self._travail_modifie = False" in corps_reset,
      corps_reset)
corps_save = ast.get_source_segment(source, meth["_save"])
check("_save l'eteint apres l'ecriture",
      "self._travail_modifie = False" in corps_save and
      corps_save.index("_write_ui_file") < corps_save.index("_travail_modifie = False"),
      corps_save)
check("_save ne l'eteint pas dans ses deux branches de refus",
      corps_save.count("self._travail_modifie = False") == 1, corps_save)
etat_keys = ast.get_source_segment(
    source, [n for n in ast.walk(arbre) if isinstance(n, ast.Assign)
             and getattr(n.targets[0], "id", "") == "STATE_KEYS"][0])
# Le piege, a pincer : une entree de journal copie l'etat AVANT la modification.
# Si le drapeau etait archive avec le reste, le premier Annuler le rendrait a sa
# valeur « non modifie » et l'eleve pourrait ouvrir un autre fichier sans qu'on
# le previenne, alors que rien n'est enregistre.
check("le drapeau n'est pas une cle du journal", "_travail_modifie" not in etat_keys,
      etat_keys)
check("le drapeau n'est pas non plus restaure par _restore",
      "_travail_modifie" not in ast.get_source_segment(source, meth["_restore"]),
      ast.get_source_segment(source, meth["_restore"]))
adopte = ast.get_source_segment(source, meth["load_new_ui_file"])
check("la question vient apres la lecture, pas avant",
      adopte.index("self._parse_ui(path)") < adopte.index("_travail_non_enregistre()"),
      adopte[:80])
check("et avant toute adoption du fichier",
      adopte.index("_travail_non_enregistre()") < adopte.index("self.ui_file = path"),
      adopte[adopte.index("_travail_non_enregistre"):][:120])
entre = adopte[adopte.index("_travail_non_enregistre()"):adopte.index("self.ui_file = path")]
check("un refus de l'eleve sort sans avoir rien ecrit",
      "return False" in entre and "self.widgets_data = data" not in entre, entre)
check("le drapeau se baisse par reset_history, pas par un troisieme chemin",
      adopte.count("_travail_modifie") == 0, adopte.count("_travail_modifie"))
nouveau = ast.get_source_segment(source, meth["_new"])
check("Nouveau se fie au drapeau et plus a la presence de widgets",
      "_travail_non_enregistre()" in nouveau and
      "self.widgets_data and" not in nouveau, nouveau[:200])
check("les deux questions sont distinctes, chacune dans sa methode",
      "messagebox.askyesno" in nouveau and "messagebox.askyesno" in adopte)
check("aucune boite Qt dans le concepteur", source.count("QMessageBox") == 0,
      source.count("QMessageBox"))
init_src = open(os.path.join(PLUGIN, "__init__.py"), encoding="utf-8").read()
arbre_init = ast.parse(init_src)
add = [n for n in ast.walk(arbre_init)
       if isinstance(n, ast.FunctionDef) and n.name == "add_pyqt_code"][0]
corps_add = ast.get_source_segment(init_src, add)
check("le bouton du menu attend la reponse de la vue avant de toucher au menu",
      corps_add.index("load_new_ui_file") < corps_add.index("_clear_dynamic_menu_items"),
      [l.strip() for l in corps_add.splitlines() if "menu" in l or "load_new" in l])
check("le bouton ne tient plus de copie du fichier de l'eleve",
      "qt_ui_file" not in corps_add and "global" not in corps_add,
      [l.strip() for l in corps_add.splitlines() if "global" in l or "ui_file" in l])
check("et il sort tout de suite si la vue n'a rien ouvert",
      "if not vue.load_new_ui_file(path):" in corps_add, corps_add[:500])
open_ = ast.get_source_segment(source, meth["_open"])
check("le bouton Ouvrir de la barre d'outils passe bien par load_new_ui_file",
      "load_new_ui_file(path)" in open_, open_)
check("un seul point de question : la question n'est pas duplicate dans _open",
      "askyesno" not in open_, open_)

for top in fenetres:
    top.destroy()
racine.update()

check("aucun controle de cette suite n'est ecrit dans l'autre sens",
      a_l_envers == [], a_l_envers)

print("\n%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)
