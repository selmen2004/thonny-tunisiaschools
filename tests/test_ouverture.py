r"""Item 3 : un « Ouvrir » refuse ne doit rien changer a la fenetre en cours.

Le geste est banal : l'eleve a un travail en cours dans le concepteur, il clique
sur Ouvrir, et se trompe de fichier — son `programme.py`, un .ui a demi ecrit, un
document qui n'est pas une forme. Avant le correctif, `load_new_ui_file` notait
le chemin choisi dans `self.ui_file` *avant* de le lire, `_parse_ui` lui rendait
`([], {})` en cas d'echec, et vidait au passage `_source_ui`, c'est-a-dire
l'arbre XML de la fenetre affichee. Deux pertes, toutes les deux mesurees :

  • le modele est vide : les widgets de l'eleve disparaissent de l'ecran ;
  • `self.ui_file` designe desormais le fichier choisi : au prochain
    Enregistrer, le plugin y ecrit du XML. Par-dessus le programme Python de
    l'eleve (mesure : l'octet 0 du fichier est un `<`), ou par-dessus un autre
    .ui qui n'etait pas celui que la vue montrait.

Le troisieme cas, un <ui> bien forme mais sans `<widget>` racine, ne montrait
aucun message : la vue se vidait en silence, et l'enregistrement produisait une
forme vide.

La suite verifie que lire est devenu une operation sans effet de bord tant
qu'elle n'a pas abouti : l'adoption du fichier (chemin, modele, titre, historique,
dessin) n'a lieu qu'une fois la racine trouvee, et un echec dit toujours pourquoi.

Les fichiers utilises s'ecrivent dans `_sortie/ouverture/` : ce dossier est
ignore, et plusieurs tests enregistrent par-dessus leurs propres fixtures.
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import types
from xml.etree import ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
PLUGIN = r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
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
    showerror=lambda *a, **k: dialogues.append(("error",) + a),
    showinfo=lambda *a, **k: dialogues.append(("info",) + a),
    askyesno=lambda *a, **k: True)
UIViewer.get_workbench = lambda: None

racine = tk.Tk()
racine.withdraw()

D = os.path.join(HERE, "_sortie", "ouverture")
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
VIDE_UI = r'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="FormVide">
  <property name="geometry"><rect><x>0</x><y>0</y><width>200</width><height>120</height></rect></property>
  <property name="windowTitle"><string>Rien encore</string></property>
 </widget>
</ui>
'''
SANS_FORME_UI = '<ui version="4.0"><class>Form</class><resources/></ui>\n'
DOCUMENT_XML = '<html><body><p>Bonjour</p></body></html>\n'
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
ecrit(CHEMIN("forme_vide.ui"), VIDE_UI)
ecrit(CHEMIN("sans_forme.ui"), SANS_FORME_UI)
ecrit(CHEMIN("document.xml"), DOCUMENT_XML)
ecrit(CHEMIN("tronque.ui"), NOTE_UI[:600])
ecrit(CHEMIN("zero_octets.ui"), "")
ecrit(CHEMIN("programme.py"), PROGRAMME_PY)
os.mkdir(CHEMIN("dossier"))
ABSENT = CHEMIN("inexistant.ui")

bilan = [0, 0]


def check(cond, msg, detail=None):
    bilan[0] += 1
    print(("  OK   " if cond else "  FAIL ") + msg +
          ("" if cond or detail is None else "  [%s]" % (detail,)))
    if not cond:
        bilan[1] += 1


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
    """Le modele seul, sans vue : suffisant pour parler a l'XML."""
    v = object.__new__(UiViewerPlugin)
    v.widgets_data, v.selected_idx = [], None
    v.widget_counter, v.ui_file = 0, path
    v.root_widget_name, v.root_widget_class = "Form", "QDialog"
    v.root_geometry, v.root_title = (0, 0, 640, 480), "Form"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    v._undo_stack, v._redo_stack = [], []
    return v


def dessines(v):
    """Les noms peints sur la maquette, dans l'ordre du modele."""
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
        "etiquette": v._title_lbl.cget("text"),
        "peint":     dessines(v),
        "selection": v.selected_idx,
    }


def octets(chemin):
    with open(chemin, "rb") as f:
        return f.read()


def noms_dun_fichier(chemin):
    return [w.get("name") for w in ET.parse(chemin).iter("widget")]


def leve(fn):
    try:
        fn()
    except Exception as e:                       # noqa: BLE001
        return type(e).__name__ + ": " + str(e)
    return None


def cartes_des_uids(v):
    return [p["_uid"] for _c, p in v.widgets_data]


# ── 1. le geste de l'eleve : un mauvais choix, puis Enregistrer ──────────
print("=== 1. ouvrir un programme .py par erreur ne doit rien detruire ===")
top, v = fenetre("ouverture-refus")
v.load_new_ui_file(CHEMIN("note.ui"))
check(cartes_des_uids(v) == ["w0", "w1", "w2"] and
      [p["name"] for _c, p in v.widgets_data] == ["titre", "saisie", "ok"],
      "la fenetre de depart est bien chargee",
      (cartes_des_uids(v), [p["name"] for _c, p in v.widgets_data]))
check(v.ui_file == CHEMIN("note.ui") and dessines(v) == ["titre", "saisie", "ok"],
      "le chemin et le dessin suivent le fichier", (v.ui_file, dessines(v)))

# un travail non enregistre, comme dans la vraie vie : l'eleve ajoute un label
v._add_widget("QLabel")
avec_travail = etat(v)
arbre_charge = v._source_ui
modele_charge = v.widgets_data
check(len(v.widgets_data) == 4 and avec_travail["journal"] == 1,
      "le travail en cours est la, et n'est pas encore enregistre",
      (len(v.widgets_data), avec_travail["journal"]))

programme_avant = octets(CHEMIN("programme.py"))
dialogues.clear()
plantage = leve(lambda: v.load_new_ui_file(CHEMIN("programme.py")))
check(plantage is None, "ouvrir un .py ne fait pas craquer la vue", plantage)
check(etat(v) == avec_travail,
      "apres ce refus, la vue est exactement ce qu'elle etait",
      [(k, avec_travail[k]) for k in avec_travail if etat(v)[k] != avec_travail[k]])
check(v._source_ui is arbre_charge and v.widgets_data is modele_charge,
      "ni l'arbre XML ni le modele n'ont ete remplaces")
check(len(dialogues) == 1 and dialogues[0][0] == "error",
      "un seul message, et c'est une erreur", dialogues)
check("Impossible" in (dialogues[0][1] + dialogues[0][2] if dialogues else ""),
      "il dit que la lecture est impossible", dialogues)
check(octets(CHEMIN("programme.py")) == programme_avant,
      "le programme de l'eleve n'a pas bouge d'un octet")

# la suite du geste : l'eleve enregistre. C'est ici que l'ancien plugin ecrivait
# du XML par-dessus le .py.
dialogues.clear()
v._save()
nom_ajoute = avec_travail["modele"][-1][1]
check(v.ui_file == CHEMIN("note.ui"),
      "Enregistrer reste fidele au fichier de la fenetre", v.ui_file)
check(octets(CHEMIN("programme.py")) == programme_avant and
      programme_avant.startswith(b"from PyQt5"),
      "le .py est toujours le squelette Python de l'eleve",
      octets(CHEMIN("programme.py"))[:24])
check(noms_dun_fichier(CHEMIN("note.ui")) ==
      ["FenetreNote", "titre", "saisie", "ok", nom_ajoute],
      "l'enregistrement a bien ecrit la fenetre, avec le widget ajoute",
      noms_dun_fichier(CHEMIN("note.ui")))
check(len([d for d in dialogues if d[0] == "info"]) == 1,
      "et l'eleve a eu sa confirmation d'enregistrement", dialogues)

# le cas « <ui> sans forme », qui se vidait et s'enregistrait en silence
avant = etat(v)
dialogues.clear()
plantage = leve(lambda: v.load_new_ui_file(CHEMIN("sans_forme.ui")))
check(plantage is None and etat(v) == avant,
      "un <ui> sans widget racine laisse le modele intact", etat(v)["modele"])
check(len(dialogues) == 1 and "fenetre" in (dialogues[0][2] if dialogues else ""),
      "et le dit : le fichier n'est pas une fenetre", dialogues)
check(v.ui_file == CHEMIN("note.ui"),
      "le fichier en cours n'a pas ete detourne", v.ui_file)
top.destroy()

# ── 2. chaque facon de se tromper de fichier ────────────────────────────
print("=== 2. toutes les entrees refusables, une par une ===")
REFUS = [
    (CHEMIN("programme.py"),   "Impossible", "du Python, pas du XML"),
    (CHEMIN("tronque.ui"),     "Impossible", "un .ui a demi ecrit"),
    (CHEMIN("zero_octets.ui"), "Impossible", "zero octet"),
    (CHEMIN("dossier"),        "Impossible", "un repertoire a la place d'un fichier"),
    (ABSENT,                   "Impossible", "un chemin qui n'existe pas"),
    (CHEMIN("document.xml"),   "fenetre",    "du XML, mais aucune forme"),
    (CHEMIN("sans_forme.ui"),  "fenetre",    "un <ui> sans <widget>"),
]
top, v = fenetre("ouverture-refus-loop")
v.load_new_ui_file(CHEMIN("note.ui"))
avant, arbre = etat(v), v._source_ui
for chemin, attendu, pourquoi in REFUS:
    if chemin is not ABSENT:
        check(os.path.exists(chemin),
              "%s : le fixture existe, le refus vient du contenu" %
              os.path.basename(chemin), chemin)
    dialogues.clear()
    plantage = leve(lambda: v.load_new_ui_file(chemin))
    nom = os.path.basename(chemin) or chemin
    check(plantage is None, "%s (%s) : echoue sans trace back" % (nom, pourquoi),
          plantage)
    check(etat(v) == avant, "%s : rien ne change a l'ecran" % nom,
          [(k, avant[k]) for k in avant if etat(v)[k] != avant[k]])
    check(v._source_ui is arbre, "%s : l'arbre source est conserve" % nom)
    check(len(dialogues) == 1 and dialogues[0][0] == "error",
          "%s : un message, pas deux, pas zero" % nom, dialogues)
    check(attendu in (dialogues[0][2] if dialogues else "") and
          dialogues[0][1] == "Erreur",
          "%s : le message attendu (%s)" % (nom, attendu), dialogues)
top.destroy()

# les memes fichiers, sur une vue vierge : le refus ne doit rien installer
top, v = fenetre("ouverture-refus-vierge")
dialogues.clear()
v.load_new_ui_file(CHEMIN("programme.py"))
check(v.ui_file is None and v.widgets_data == [] and
      v._title_lbl.cget("text") == "Sans titre" and not v._source_uids,
      "sur une vue vierge, rien n'est adopte : ni chemin, ni titre, ni uid",
      (v.ui_file, v._title_lbl.cget("text"), v._source_uids))
top.destroy()

# ── 3. le journal ne doit pas etre efface par un refus ──────────────────
print("=== 3. Annuler apres un refus annule le travail, pas l'ouverture ===")
top, v = fenetre("ouverture-journal")
v.load_new_ui_file(CHEMIN("autre.ui"))
v._add_widget("QPushButton")
check(len(v._undo_stack) == 1, "le widget ajoute vaut un pas d'historique",
      len(v._undo_stack))
dialogues.clear()
v.load_new_ui_file(CHEMIN("programme.py"))
check(len(v._undo_stack) == 1 and len(v._redo_stack) == 0,
      "le refus n'a pas reinitialise le journal",
      (len(v._undo_stack), len(v._redo_stack)))
v.undo()
check([p["name"] for _c, p in v.widgets_data] == ["titre", "saisie", "ok"],
      "Annuler retire bien le widget de la fenetre en cours",
      [p["name"] for _c, p in v.widgets_data])
check(v.ui_file == CHEMIN("autre.ui"),
      "et la cible de l'enregistrement n'a pas changee", v.ui_file)
top.destroy()

# ── 4. atomicite de _parse_ui, au niveau du modele ──────────────────────
print("=== 4. _parse_ui ne commit que ce qu'il a fini de lire ===")
v = harnais(CHEMIN("note.ui"))
data, info = v._parse_ui(CHEMIN("note.ui"))
arbre, uids, src_root = v._source_ui, list(v._source_uids), dict(v._src_root)
noms_racine, graine = (v.root_widget_name, v.root_widget_class), v.widget_counter
data, info = v._parse_ui(CHEMIN("programme.py"))
check(data == [] and info == {}, "un echec rend bien ([], {})", (data, info))
check(v._source_ui is arbre and list(v._source_uids) == uids
      and dict(v._src_root) == src_root,
      "l'arbre, les uid et l'empreinte de la fenetre precedente sont intacts",
      (v._source_uids, v._src_root))
check((v.root_widget_name, v.root_widget_class) == noms_racine,
      "le nom et la classe de la racine non plus",
      (v.root_widget_name, v.root_widget_class))
check(v.widget_counter == graine,
      "et la graine des noms n'a pas bouge", v.widget_counter)
data, info = v._parse_ui(CHEMIN("sans_forme.ui"))
check(data == [] and info == {}, "un <ui> sans forme rend ([], {}) aussi")
check(v._source_ui is arbre and list(v._source_uids) == uids,
      "et ne remet plus rien a zero")
data, info = v._parse_ui(ABSENT)
check(data == [] and list(v._source_uids) == uids and v._source_ui is arbre,
      "un chemin absent ne detruit pas l'etat")
widgets = v.widgets_data
data, info = v._parse_ui(CHEMIN("document.xml"))
check(v.widgets_data is widgets,
      "_parse_ui n'ecrit jamais dans widgets_data, meme en echouant")

# une lecture reussie, elle, doit tout remplacer
v = harnais(CHEMIN("note.ui"))
data0, _i0 = v._parse_ui(CHEMIN("note.ui"))
ancien_arbre, ancien_uids = v._source_ui, v._source_uids
v.root_widget_name = "TemoinQuiNeDoitPasSurvivre"
data, info = v._parse_ui(CHEMIN("autre.ui"))
check(len(data) == 3 and v._source_ui is not ancien_arbre,
      "une lecture reussie adopte son propre arbre", len(data))
check(v._source_uids is not ancien_uids,
      "la liste des uid est remplacee, pas prolongee", v._source_uids)
check(list(v._source_uids) == ["w0", "w1", "w2"] and
      [p["_uid"] for _c, p in data] == ["w0", "w1", "w2"],
      "les uid du nouveau fichier sont bien installes",
      (v._source_uids, [p["_uid"] for _c, p in data]))
check(v.root_widget_name == "AutreFenetre" and v.root_widget_class == "QDialog",
      "nom et classe de la nouvelle racine suivent",
      (v.root_widget_name, v.root_widget_class))
check(info.get("geometry") == (0, 0, 360, 220) and
      info.get("title") == "Autre titre",
      "geometry et titre viennent du fichier", info)
check(v._src_root.get("geometry") == (0, 0, 360, 220),
      "l'empreinte de la racine est celle du fichier lu", v._src_root)
check(list(ancien_uids) == [p["_uid"] for _c, p in data0] and bool(ancien_uids),
      "la lecture precedente avait deja installe les siens",
      (ancien_uids, [p["_uid"] for _c, p in data0]))

# ── 5. un plantage du lecteur lui-meme ──────────────────────────────────
print("=== 5. si le lecteur casse en plein parcours ===")
top, v = fenetre("ouverture-panne")
v.load_new_ui_file(CHEMIN("note.ui"))
avant, arbre = etat(v), v._source_ui


def casse(el):
    raise RuntimeError("le lecteur a casse")


v._walk_widgets = casse
dialogues.clear()
plantage = leve(lambda: v.load_new_ui_file(CHEMIN("autre.ui")))
check(plantage is not None and "RuntimeError" in plantage,
      "la panne remonte a l'appelant : elle doit rester visible", plantage)
check(etat(v) == avant and v._source_ui is arbre,
      "mais rien n'a ete adopte : ni chemin, ni modele, ni arbre", etat(v))
check(v.ui_file == CHEMIN("note.ui"),
      "le prochain Enregistrer visera toujours le bon fichier", v.ui_file)
check(not dialogues,
      "le plantage du lecteur n'est pas deguise en fichier casse", dialogues)
del v._walk_widgets
v.load_new_ui_file(CHEMIN("autre.ui"))
check(etat(v)["chemin"] == CHEMIN("autre.ui") and
      [p["name"] for _c, p in v.widgets_data] == ["titre", "saisie", "ok"],
      "et apres la panne, une ouverture valide fonctionne toujours", etat(v))
top.destroy()

# ── 6. ce que le plugin faisait avant, rejoue ──────────────────────────
print("=== 6. la catastrophe d'avant le correctif, prouvee ===")


def ouverture_d_avant(self, path):
    """Le corps de load_new_ui_file avant le correctif, rejoue tel quel, avec la
    remise a zero que _parse_ui faisait alors avant meme d'avoir trouve une
    racine : c'est exactement ce que l'eleve subissait."""
    self.ui_file = path
    self._source_ui = None
    self._source_uids = []
    self._src_root = {}
    self.widgets_data, root_info = self._parse_ui(path)
    self.root_geometry = root_info.get("geometry", (0, 0, 640, 480))
    self.root_title = root_info.get("title", "Form")
    self.selected_idx = None
    self.reset_history()
    self._title_lbl.config(text=os.path.basename(path))
    self._refresh()


ecrit(CHEMIN("programme_avant.py"), PROGRAMME_PY)
ecrit(CHEMIN("note_avant.ui"), NOTE_UI)
top, v = fenetre("ouverture-avant")
v.load_new_ui_file(CHEMIN("note_avant.ui"))
v._add_widget("QLabel")
check(len(v.widgets_data) == 4 and len(v._undo_stack) == 1,
      "le travail de l'eleve est pret a etre perdu",
      (len(v.widgets_data), len(v._undo_stack)))
dialogues.clear()
ouverture_d_avant(v, CHEMIN("programme_avant.py"))
check(v.widgets_data == [],
      "avant : le modele est vide, les widgets ont disparu de l'ecran",
      v.widgets_data)
check(v.ui_file == CHEMIN("programme_avant.py"),
      "avant : le fichier en cours est le .py choisi par erreur", v.ui_file)
check(v._source_ui is None and v._source_uids == [],
      "avant : l'arbre de la fenetre d'avant est jete", v._source_uids)
v._write_ui_file(v.ui_file)
devenu = octets(CHEMIN("programme_avant.py"))
check(devenu != PROGRAMME_PY.encode("utf-8") and
      devenu.lstrip().startswith(b"<?xml"),
      "avant : l'Enregistrer suivant ecrivait du XML par-dessus le programme",
      devenu[:40])
check(b"loadUi" not in devenu,
      "avant : le code de l'eleve n'existe plus", devenu[:80])

ecrit(CHEMIN("programme_avant2.py"), PROGRAMME_PY)
v.load_new_ui_file(CHEMIN("note_avant.ui"))
avant2 = etat(v)
ouverture_d_avant(v, CHEMIN("sans_forme.ui"))
check(v.widgets_data == [] and v.ui_file == CHEMIN("sans_forme.ui"),
      "avant : un <ui> sans forme vidait la vue et devenait le fichier en cours",
      etat(v))
v._write_ui_file(CHEMIN("sans_forme.ui"))
relu = open(CHEMIN("sans_forme.ui"), encoding="utf-8").read()
check(noms_dun_fichier(CHEMIN("sans_forme.ui")) == ["FenetreNote"] and
      relu.count("<widget") == 1,
      "avant : et l'enregistrement ecrivait une forme vide a la place du "
      "fichier de l'eleve", noms_dun_fichier(CHEMIN("sans_forme.ui")))
check("titre" not in relu,
      "avant : les widgets que montrait la vue ont disparu du fichier", relu[:80])
check(avant2["modele"] != [],
      "le travail rejoue etait bien reel", avant2["modele"])
top.destroy()

# ── 7. un succes doit rester un succes complet ──────────────────────────
print("=== 7. garde-fou : l'adoption n'est pas devenue timide ===")
top, v = fenetre("ouverture-succes")
v.load_new_ui_file(CHEMIN("note.ui"))
v._add_widget("QLabel")
v._select(1)
dialogues.clear()
v.load_new_ui_file(CHEMIN("autre.ui"))
apres = etat(v)
check(not dialogues, "une ouverture reussie n'affiche aucune erreur", dialogues)
check(apres["chemin"] == CHEMIN("autre.ui") and
      apres["etiquette"] == "autre.ui",
      "le chemin et le titre de la barre suivent le nouveau fichier", apres)
check(apres["racine"] == ("AutreFenetre", "QDialog") and
      apres["titre"] == "Autre titre",
      "la racine et le titre viennent du nouveau fichier",
      (apres["racine"], apres["titre"]))
check([n for _c, n in apres["modele"]] == ["titre", "saisie", "ok"],
      "les widgets du nouveau fichier remplacent les anciens", apres["modele"])
check(apres["journal"] == 0 and apres["selection"] is None,
      "le journal et la selection repartent de zero",
      (apres["journal"], apres["selection"]))
check(apres["peint"] == ["titre", "saisie", "ok"],
      "l'ecran est redessine avec le nouveau fichier", apres["peint"])
check(apres["src_root"].get("title") == "Autre titre",
      "l'empreinte de la racine est celle du fichier adopte", apres["src_root"])
check(v.widgets_data and all(p.get("_src") is not None
                             for _c, p in v.widgets_data),
      "et l'empreinte de reference est bien celle du fichier lu")

# une forme sans aucun widget interieur reste une forme : le garde-fou ne doit
# pas la refuser, sinon l'eleve ne pourrait plus ouvrir un fichier neuf.
dialogues.clear()
v.load_new_ui_file(CHEMIN("forme_vide.ui"))
check(not dialogues and v.widgets_data == [] and
      etat(v)["racine"] == ("FormVide", "QWidget") and
      etat(v)["titre"] == "Rien encore",
      "une forme vide s'ouvre : le refus ne porte que sur les non-formes",
      (dialogues, etat(v)))
check(etat(v)["geometrie"] == (0, 0, 200, 120) and dessines(v) == [],
      "et sa taille vient du fichier, sans widget a peindre",
      (etat(v)["geometrie"], dessines(v)))

# ouvre puis enregistre sans rien changer : la fidelite ne doit pas en patir
enregistre = CHEMIN("autre_recopie.ui")
v.load_new_ui_file(CHEMIN("autre.ui"))
v.ui_file = enregistre
dialogues.clear()
v._save()
une_fois = octets(enregistre)
dialogues.clear()
v._save()
check(une_fois == octets(enregistre),
      "double enregistrement identique : la carte uid/properties est stable")
check(noms_dun_fichier(enregistre) == ["AutreFenetre", "titre", "saisie", "ok"],
      "le fichier recopie porte toujours la meme fenetre",
      noms_dun_fichier(enregistre))
top.destroy()

# ── 8. la preuve par Qt ─────────────────────────────────────────────────
print("=== 8. ce que Qt relit, apres un refus puis un enregistrement ===")
ecrit(CHEMIN("note_qt.ui"), NOTE_UI)
ecrit(CHEMIN("programme_qt.py"), PROGRAMME_PY)
programme_avant = octets(CHEMIN("programme_qt.py"))
top, v = fenetre("ouverture-qt")
v.load_new_ui_file(CHEMIN("note_qt.ui"))
v._add_widget("QLabel")
nom_ajoute = v.widgets_data[-1][1]["name"]
dialogues.clear()
v.load_new_ui_file(CHEMIN("programme_qt.py"))
dialogues.clear()
v._save()
check(v.ui_file == CHEMIN("note_qt.ui") and
      octets(CHEMIN("programme_qt.py")) == programme_avant,
      "l'enregistrement d'apres le refus a ecrit dans le .ui, pas dans le .py",
      (v.ui_file, octets(CHEMIN("programme_qt.py"))[:20]))

SONDE = r'''
import json, os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, %r)
from PyQt5 import QtWidgets, uic
from PyQt5.uic.properties import QtGui, QtCore
app = QtWidgets.QApplication([])
out = {"charge": None, "classe": None, "erreur": None, "vue": []}
try:
    w = uic.loadUi(%r)
    w.show()
    app.processEvents()
    out["charge"] = w.objectName()
    out["classe"] = type(w).__name__
    out["vue"] = [w.titre.text(), w.ok.text(),
                  w.findChild(QtWidgets.QLabel, %r) is not None]
except Exception as e:
    out["erreur"] = type(e).__name__ + ": " + str(e)
print(json.dumps(out))
'''
env = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")
p = subprocess.run(
    [os.path.join(BUNDLE, "python.exe"), "-B", "-c",
     SONDE % (os.path.join(BUNDLE, "Lib", "site-packages"),
              CHEMIN("note_qt.ui"), nom_ajoute)],
    capture_output=True, text=True, env=env, timeout=180)
try:
    qt = json.loads(p.stdout.strip().splitlines()[-1])
except Exception:
    qt = {"charge": None, "erreur": (p.stdout + p.stderr)[-300:]}
check(qt.get("charge") == "FenetreNote" and qt.get("classe") == "QDialog",
      "loadUi() ouvre le fichier survécu au refus", qt)
check(qt.get("vue", [])[:3] == ["Eleve", "Valider", True],
      "avec le widget que l'eleve avait ajoute", qt.get("vue"))
top.destroy()

# ── 9. les deux ordonnancements qui portent le correctif ────────────────
print("=== 9. la structure du correctif, dans le fichier vivant ===")
source = open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
arbre_vif = ast.parse(source)
meth = {n.name: n for n in ast.walk(arbre_vif) if isinstance(n, ast.FunctionDef)}
lu = ast.get_source_segment(source, meth["_parse_ui"])
adopte = ast.get_source_segment(source, meth["load_new_ui_file"])
check("self._source_ui = None" not in lu and "self._src_root = {}" not in lu,
      "_parse_ui ne remet plus l'etat a zero avant d'avoir lu",
      [l.strip() for l in lu.splitlines() if "_source_ui = None" in l])
check(lu.index("root_elem = tree_root.find") <
      lu.index("self._source_ui = tree_root"),
      "il ne commit l'arbre lu qu'apres avoir trouve la racine")
check(lu.rindex("self._source_ui = tree_root") < lu.rindex("return data, root_info"),
      "et le commit reste le dernier geste de la lecture")
check(lu.index("self._source_uids") > lu.index("for i, w in enumerate(ordered)"),
      "la liste des uid se construit a cote, puis se pose au commit")
check(adopte.index("self._parse_ui(path)") < adopte.index("self.ui_file = path"),
      "load_new_ui_file lit avant de declarer le fichier en cours", adopte[:160])
check("if not root_info:" in adopte, "et il refuse d'adopter sans racine")
check(source.count("QMessageBox") == 0,
      "et l'editeur reste sans aucun QMessageBox")

print()
print("%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)
