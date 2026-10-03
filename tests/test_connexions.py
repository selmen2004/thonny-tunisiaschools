r"""Item 1 : un lien vers un widget supprime ne doit pas survivre.

Qt recopie chaque <connection> du .ui en code de setupUi(). Si l'emetteur ou le
destinataire n'existe plus, loadUi() ne previent pas : il leve un AttributeError
sur le nom du widget efface, et c'est toute la fenetre qui refuse de se
construire. Le concepteur supprimait le bouton, enregistrait, et le programme de
l'eleve mourait au demarrage, sans rapport avec ce qu'il venait de faire.

Qt Designer fait le menage en meme temps que la suppression. Cette suite verifie
la meme chose, du geste de l'eleve jusqu'au fichier que Qt relit :

  1. supprimer un widget relie retire bien sa connexion, et ne retire que
     celle-la ;
  2. le menage est compte a la barre d'etat, et le fichier reste chargeable ;
  3. sans suppression, le bloc <connections> sort intact de l'enregistrement ;
  4. les cas tordus (fichier sans bloc, citation vide, un <property
     name="geometry"> qui n'est pas un objet, un nom d'action) ne tournent pas
     en casse ;
  5. la preuve par l'execution : loadUi() accepte le fichier menage et refuse
     exactement celui d'avant le correctif ;
  6. (item 12) l'autre bout du meme fil : un lien dont l'emetteur est une
     action d'un bloc <actions> de racine. Le nom, lui, est dans le fichier -
     le menage de l'item 1 le laisse donc passer - mais `uic` ne lit pas ce
     bloc et ne cree aucun objet pour ces noms-la : la fenetre de l'eleve
     refuse de se construire pour autant. L'ecriture remonte l'action sous le
     formulaire, la seule place que le chargeur connait.

Les fichiers genères s'appellent gen_connexions*.ui : « *.ui » est ignore,
seules les fixtures lues sans jamais etre ecrites sont suivies dans git.
"""
import json
import os
import subprocess
import sys
import types
from xml.etree import ElementTree as ET

import chemins

BUNDLE = chemins.BUNDLE
# La copie sous faute (mutants_actions.py) : sans cette ligne la suite importerait
# le paquet vivant pendant qu'un grade examine une copie mutee, et le verdict ne
# prouverait rien.
PLUGIN = os.environ.get("TUNISIASCHOOLS_COPIE") or \
    chemins.PAQUET
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

SOURCE = os.path.join(HERE, "gen_connexions.ui")
APRES = os.path.join(HERE, "gen_connexions_apres.ui")
APRES2 = os.path.join(HERE, "gen_connexions_apres2.ui")
SECOND = os.path.join(HERE, "gen_connexions_second.ui")
SANS_SUPPRESSION = os.path.join(HERE, "gen_connexions_intact.ui")
SANS_BLOC = os.path.join(HERE, "gen_connexions_sans_bloc.ui")
SANS_BLOC_OUT = os.path.join(HERE, "gen_connexions_sans_bloc_out.ui")
DIRECT = os.path.join(HERE, "gen_connexions_direct.ui")
FIGEUR = os.path.join(HERE, "gen_connexions_figure.ui")
VIDE = os.path.join(HERE, "gen_connexions_vide.ui")
ACTION = os.path.join(HERE, "gen_connexions_action.ui")
ACTION_OUT = os.path.join(HERE, "gen_connexions_action_out.ui")
AVANT_FIX = os.path.join(HERE, "gen_connexions_avant_fix.ui")
# item 12 : les sortieS du menage d'actions
COLLISION = os.path.join(HERE, "gen_connexions_collision.ui")
COLLISION_OUT = os.path.join(HERE, "gen_connexions_collision_out.ui")
DOUBLON = os.path.join(HERE, "gen_connexions_doublon.ui")
DEUX = os.path.join(HERE, "gen_connexions_deux_actions.ui")
BLOC_VIDE = os.path.join(HERE, "gen_connexions_bloc_vide.ui")
BLOC_VIDE_OUT = os.path.join(HERE, "gen_connexions_bloc_vide_out.ui")
SANS_NOM = os.path.join(HERE, "gen_connexions_action_sans_nom.ui")
ETRANGE = os.path.join(HERE, "gen_connexions_bloc_etrange.ui")
FIX_OUT = os.path.join(HERE, "gen_connexions_action_repare.ui")
FIX_OUT2 = os.path.join(HERE, "gen_connexions_action_repare2.ui")
AVANT_ACTIONS = os.path.join(HERE, "gen_connexions_action_avant_fix.ui")

# Quatre widgets, trois liens : un par cas.
#   btnEfface  -> l'emetteur   que l'eleve va supprimer
#   btnRecoit  -> le destinataire que l'eleve va supprimer
#   btnQuitter -> le lien a conserver tel quel
SOURCE_UI = '''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="geometry"><rect><x>0</x><y>0</y><width>400</width><height>300</height></rect></property>
  <property name="windowTitle"><string>Gestion</string></property>
  <widget class="QLabel" name="titre">
   <property name="geometry"><rect><x>20</x><y>15</y><width>200</width><height>30</height></rect></property>
   <property name="text"><string>Bonjour</string></property>
  </widget>
  <widget class="QPushButton" name="btnQuitter">
   <property name="geometry"><rect><x>20</x><y>60</y><width>90</width><height>26</height></rect></property>
   <property name="text"><string>Quitter</string></property>
  </widget>
  <widget class="QPushButton" name="btnEfface">
   <property name="geometry"><rect><x>130</x><y>60</y><width>90</width><height>26</height></rect></property>
   <property name="text"><string>Efface</string></property>
  </widget>
  <widget class="QPushButton" name="btnRecoit">
   <property name="geometry"><rect><x>240</x><y>60</y><width>90</width><height>26</height></rect></property>
   <property name="text"><string>Recoit</string></property>
  </widget>
 </widget>
 <resources/>
 <connections>
  <connection>
   <sender>btnQuitter</sender>
   <signal>clicked()</signal>
   <receiver>Form</receiver>
   <slot>close()</slot>
  </connection>
  <connection>
   <sender>btnEfface</sender>
   <signal>clicked()</signal>
   <receiver>Form</receiver>
   <slot>hide()</slot>
  </connection>
  <connection>
   <sender>btnQuitter</sender>
   <signal>clicked()</signal>
   <receiver>btnRecoit</receiver>
   <slot>hide()</slot>
  </connection>
 </connections>
</ui>
'''
LIENS_SOURCE = [("btnQuitter", "Form"), ("btnEfface", "Form"),
                ("btnQuitter", "btnRecoit")]

# Le meme fichier avec une QAction : un lien dont l'emetteur n'est pas un
# widget. Designer les ecrit, et le menage ne doit pas les manger.
ACTION_UI = SOURCE_UI.replace(
    " <resources/>\n",
    ' <actions>\n  <action name="cacheAction">\n'
    '   <property name="text"><string>Cacher le titre</string></property>\n'
    "  </action>\n </actions>\n <resources/>\n").replace(
    " </connections>",
    '  <connection>\n   <sender>cacheAction</sender>\n'
    "   <signal>triggered()</signal>\n"
    "   <receiver>titre</receiver>\n   <slot>hide()</slot>\n"
    "  </connection>\n </connections>")

# item 12 : les variantes du meme bloc, pour les cas ou le menage doit s'arreter.
UNE_ACTION = ('  <action name="cacheAction">\n'
              '   <property name="text"><string>Cacher le titre</string></property>\n'
              '  </action>\n')
FIN_BLOC = "  </action>\n </actions>"          # la derniere ligne du bloc
ACTION_PRISE = ('  <action name="titre">\n'
                '   <property name="text"><string>Le nom est deja pris</string></property>\n'
                '  </action>\n')
# deux actions du bloc portent le nom d'un objet que le formulaire engage deja
COLLISION_UI = ACTION_UI.replace(FIN_BLOC, "  </action>\n" + ACTION_PRISE +
                                 " </actions>")
# deux actions du bloc portent le meme nom
DOUBLON_UI = ACTION_UI.replace(FIN_BLOC, "  </action>\n" + UNE_ACTION +
                               " </actions>")
# deux actions du bloc, deux noms libres : les deux doivent monter, dans l'ordre
ACTION_SECONDE = ('  <action name="majAction">\n'
                  '   <property name="text"><string>Tout cacher</string></property>\n'
                  '  </action>\n')
DEUX_UI = ACTION_UI.replace(FIN_BLOC, "  </action>\n" + ACTION_SECONDE +
                            " </actions>")
# un bloc <actions> qui ne declare rien
BLOC_VIDE_UI = SOURCE_UI.replace(" <resources/>\n",
                                 " <actions></actions>\n <resources/>\n")
# une action sans nom d'objet : rien a montrer au chargeur
SANS_NOM_UI = SOURCE_UI.replace(
    " <resources/>\n",
    ' <actions>\n  <action>\n'
    '   <property name="text"><string>Sans cle</string></property>\n'
    "  </action>\n </actions>\n <resources/>\n")
# une action noyee dans un enfant que le format ne connait pas
ETRANGE_UI = SOURCE_UI.replace(
    " <resources/>\n",
    ' <actions>\n  <thing name="machin"/>\n' + UNE_ACTION +
    " </actions>\n <resources/>\n")

for _chemin, _contenu in ((SOURCE, SOURCE_UI), (ACTION, ACTION_UI),
                          (COLLISION, COLLISION_UI), (DOUBLON, DOUBLON_UI),
                          (BLOC_VIDE, BLOC_VIDE_UI), (SANS_NOM, SANS_NOM_UI),
                          (ETRANGE, ETRANGE_UI), (DEUX, DEUX_UI)):
    open(_chemin, "w", encoding="utf-8").write(_contenu)

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
    v.root_widget_name, v.root_widget_class = "Form", "QWidget"
    v.root_geometry, v.root_title = (0, 0, 640, 480), "Form"
    v._source_ui, v._source_uids, v._src_root = None, [], {}
    data, info = v._parse_ui(path)
    v.widgets_data = data
    v.root_geometry = info.get("geometry", (0, 0, 640, 480))
    v.root_title = info.get("title", "Form")
    return v


def index_de(v, nom):
    return next(i for i, (_c, p) in enumerate(v.widgets_data)
                if p["name"] == nom)


def liens(racine_ui):
    """Les <connection> d'un arbre, sous forme (emetteur, destinataire)."""
    return [((c.findtext("sender") or "").strip(),
             (c.findtext("receiver") or "").strip())
            for c in racine_ui.iter("connection")]


def widgets(racine_ui):
    return [w.get("name") for w in racine_ui.iter("widget")]


def lire(chemin):
    return ET.parse(chemin).getroot()


# ── 1. le geste de l'eleve : supprimer un bouton relie ──────────────────
print("=== 1. supprimer deux widgets relies ===")
check(liens(lire(SOURCE)) == LIENS_SOURCE,
      "le fichier de depart porte bien trois liens, un par cas",
      liens(lire(SOURCE)))
top, v = fenetre("connexions-suppression")
v.load_new_ui_file(SOURCE)
check([p["name"] for _c, p in v.widgets_data] ==
      ["titre", "btnQuitter", "btnEfface", "btnRecoit"],
      "les quatre widgets du fichier sont bien charges",
      [p["name"] for _c, p in v.widgets_data])
v._delete(index_de(v, "btnEfface"))      # l'emetteur d'un lien
v._delete(index_de(v, "btnRecoit"))      # le destinataire d'un autre
v.ui_file = APRES
dialogues.clear()
v._save()
ecrit = lire(APRES)
check(widgets(ecrit) == ["Form", "titre", "btnQuitter"],
      "les deux widgets ont disparu du fichier", widgets(ecrit))
check(liens(ecrit) == [("btnQuitter", "Form")],
      "seuls les deux liens morts sont retires, l'autre reste tel quel",
      liens(ecrit))
texte = open(APRES, encoding="utf-8").read()
check("<sender>btnEfface</sender>" not in texte and
      "<receiver>btnRecoit</receiver>" not in texte,
      "plus aucune ligne ne cite un objet supprime")
check("<resources" in texte and "<class>Form</class>" in texte and
      "<string>Gestion</string>" in texte,
      "le menage ne touche ni <resources> ni <class> ni le titre")
check("<property name=\"text\">" in texte and "<string>Quitter</string>" in texte,
      "les proprietes des widgets gardes sont intactes")
top.destroy()

# ── 2. c'est dit a l'eleve, et l'arbre lu reste entier ──────────────────
print("=== 2. ce que l'eleve apprend ===")
top, v = fenetre("connexions-avis")
v.load_new_ui_file(SOURCE)
v._delete(index_de(v, "btnEfface"))
v._delete(index_de(v, "btnRecoit"))
v.ui_file = APRES2
dialogues.clear()
v._save()
check("Connexions retirées du fichier : 2" in v._info_lbl.cget("text"),
      "la barre d'etat compte les liens retires",
      repr(v._info_lbl.cget("text")))
check(any(d[0] == "info" for d in dialogues),
      "la boite « Enregistre » est toujours la", dialogues)
check(not any(d[0] == "error" for d in dialogues),
      "et rien ne sonne comme une erreur", dialogues)
# L'arbre lu du fichier n'est jamais modifie : un second enregistrement refait
# le meme menage au lieu de dependre du premier.
check(len(list(v._source_ui.iter("connection"))) == 3,
      "l'arbre lu garde ses trois liens : on n'ecrit jamais dedans",
      len(list(v._source_ui.iter("connection"))))
v.ui_file = SECOND
v._save()
check(open(SECOND, encoding="utf-8").read() ==
      open(APRES2, encoding="utf-8").read(),
      "enregistrer deux fois rend exactement le meme fichier")
check("Connexions retirées du fichier : 2" in v._info_lbl.cget("text"),
      "le second menage est compte pareil", repr(v._info_lbl.cget("text")))
top.destroy()

# ── 3. sans suppression, rien ne bouge ──────────────────────────────────
print("=== 3. un simple enregistrement ===")
top, v = fenetre("connexions-sans-suppression")
v.load_new_ui_file(SOURCE)
v.widgets_data[0][1]["text"] = "Bonjour tout le monde"   # une propriete, pas un lien
v.ui_file = SANS_SUPPRESSION
dialogues.clear()
v._save()
check(liens(lire(SANS_SUPPRESSION)) == LIENS_SOURCE,
      "les trois liens sortent dans le meme ordre",
      liens(lire(SANS_SUPPRESSION)))
check("Connexions retir" not in v._info_lbl.cget("text"),
      "la barre d'etat ne parle pas de menage quand il n'y en a pas",
      repr(v._info_lbl.cget("text")))
check("Bonjour tout le monde" in open(SANS_SUPPRESSION,
                                      encoding="utf-8").read(),
      "la vraie modification, elle, est bien ecrite")
top.destroy()

# ── 4. les cas ou le menage doit rester sage ────────────────────────────
print("=== 4. les cas tordus ===")

# un fichier qui n'a pas de bloc <connections> du tout
open(SANS_BLOC, "w", encoding="utf-8").write(
    SOURCE_UI.split("<connections>")[0] + "</ui>\n")
v = harnais(SANS_BLOC)
check(v._write_ui_file(SANS_BLOC_OUT) == 0,
      "un fichier sans <connections> n'invente aucun menage")
check("<connections" not in open(SANS_BLOC_OUT, encoding="utf-8").read(),
      "et aucun bloc <connections> n'est ajoute par erreur")
check(len(v.widgets_data) == 4, "les widgets passent quand meme",
      len(v.widgets_data))

# le nombre rendu par _write_ui_file, pris directement
v = harnais(SOURCE)
v.widgets_data = [(c, p) for c, p in v.widgets_data
                  if p["name"] not in ("btnEfface", "btnRecoit")]
check(v._write_ui_file(DIRECT) == 2,
      "_write_ui_file rend le nombre de liens retires")

# un <property name="geometry"> porte le meme attribut XML qu'un objet sans en
# etre un : « geometry » comme emetteur doit passer pour ce qu'il est, un lien
# vers rien.
open(FIGEUR, "w", encoding="utf-8").write(
    SOURCE_UI.replace("<sender>btnEfface</sender>", "<sender>geometry</sender>"))
v = harnais(FIGEUR)
arbre = v._merge_into_source()
check(v._purge_orphelines(arbre) == 1,
      "le nom d'une propriete ne sauve pas un lien mort", liens(arbre))
check(liens(arbre) == [l for l in LIENS_SOURCE if l[0] != "btnEfface"],
      "les deux liens encore valides restent", liens(arbre))

# une citation vide n'est pas une citation morte : on ne detruit pas ce qu'on
# ne comprend pas.
open(VIDE, "w", encoding="utf-8").write(
    SOURCE_UI.replace("<sender>btnEfface</sender>", "<sender></sender>"))
v = harnais(VIDE)
arbre = v._merge_into_source()
check(v._purge_orphelines(arbre) == 0,
      "un <sender> vide laisse le lien en place", liens(arbre))
check(len(liens(arbre)) == 3,
      "et le bloc sort entier, avec ses trois liens", liens(arbre))

# un emetteur d'action : l'action est un objet du fichier, pas une propriete.
v = harnais(ACTION)
out = v._write_ui_file(ACTION_OUT)
check(out == 0, "les liens d'une QAction ne sont pas orphelins", out)
check("<sender>cacheAction</sender>" in open(ACTION_OUT, encoding="utf-8").read(),
      "le menage laisse le cable de l'action entier : le nom, lui, est bien la "
      "(ou doit aller l'action, c'est la section 6)")
check(liens(lire(ACTION_OUT)) == LIENS_SOURCE + [("cacheAction", "titre")],
      "et son lien ressort dans l'ordre", liens(lire(ACTION_OUT)))
# supprime le widget qui porte l'autre bout du lien : lui seul part.
v = harnais(ACTION)
v.widgets_data = [(c, p) for c, p in v.widgets_data
                  if p["name"] != "titre"]
out = v._write_ui_file(ACTION_OUT)
check(out == 1 and liens(lire(ACTION_OUT)) == LIENS_SOURCE,
      "le lien dont le destinataire a disparu part, celui de l'action reste",
      (out, liens(lire(ACTION_OUT))))

# ── 5. la preuve par l'execution ────────────────────────────────────────
print("=== 5. ce que Qt relit vraiment ===")
# Ce que le plugin ecrivait AVANT le correctif : les widgets en moins, les liens
# en trop. On le refait a la main pour que la suite prouve le bug, pas seulement
# la correction.
arbre_avant = lire(SOURCE)
form = arbre_avant.find("widget")
for nom in ("btnEfface", "btnRecoit"):
    el = next(w for w in form.findall("widget") if w.get("name") == nom)
    form.remove(el)
ET.indent(arbre_avant, space="  ")
ET.ElementTree(arbre_avant).write(AVANT_FIX, encoding="utf-8",
                                  xml_declaration=True)
check(liens(lire(AVANT_FIX)) == LIENS_SOURCE,
      "le fichier d'avant le correctif garde ses trois liens morts",
      liens(lire(AVANT_FIX)))

SONDE = r'''
import json, os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, %r)
from PyQt5 import QtWidgets, uic
from PyQt5.uic.properties import QtGui, QtCore
app = QtWidgets.QApplication([])
out = {"charge": None, "erreur": None, "vue": []}
try:
    w = uic.loadUi(%r)
    w.show()
    app.processEvents()
    out["charge"] = w.objectName()
    out["classe"] = type(w).__name__
    out["vue"] = [w.titre.text(),
                  w.findChild(QtWidgets.QWidget, "btnQuitter") is not None,
                  w.findChild(QtWidgets.QWidget, "btnEfface") is not None,
                  w.findChild(QtWidgets.QWidget, "btnRecoit") is not None]
    w.btnQuitter.click()
    app.processEvents()
    out["bouton_ferme"] = not w.isVisible()
except Exception as e:
    out["erreur"] = type(e).__name__ + ": " + str(e)
print(json.dumps(out))
'''
env = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")


def sonde(chemin):
    p = subprocess.run(
        [os.path.join(BUNDLE, "python.exe"), "-B", "-c",
         SONDE % (os.path.join(BUNDLE, "Lib", "site-packages"), chemin)],
        capture_output=True, text=True, env=env, timeout=180)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"charge": None, "erreur": (p.stdout + p.stderr)[-300:],
                "code": p.returncode}


apres = sonde(APRES)
check(apres.get("charge") == "Form",
      "loadUi() ouvre le fichier menage, sous le nom d'objet du fichier",
      apres)
check(apres.get("vue") == ["Bonjour", True, False, False],
      "les deux widgets supprimes sont absents, les autres sont la",
      apres.get("vue"))
check(apres.get("bouton_ferme") is True,
      "le lien conserve btnQuitter -> close() ferme vraiment la fenetre",
      apres)

avant = sonde(AVANT_FIX)
check(avant.get("charge") is None,
      "le fichier tel que l'ecrivait le plugin avant le correctif ne se "
      "charge toujours pas", avant)
check("AttributeError" in (avant.get("erreur") or "") and
      ("btnEfface" in (avant.get("erreur") or "") or
       "btnRecoit" in (avant.get("erreur") or "")),
      "et il meurt bien sur le nom du widget que l'eleve a supprime",
      avant.get("erreur"))

# ── 6. (item 12) l'action que le chargeur de l'eleve ne voit pas ────────
print("=== 6. une action declaree dans le bloc <actions> de racine ===")
# Le format .ui que Qt ecrit aujourd'hui ne connait l'action que comme enfant
# d'un <widget>. Le bloc <actions> au niveau <ui> vient des formulaires anciens
# ou ecrits a la main, et `uic` ne le lit pas : le nom reste dans le fichier —
# le menage de l'item 1 ne peut donc rien contre lui — mais l'objet, lui,
# manque, et `setupUi()` meurt d'un AttributeError sec. L'ecriture remet donc
# l'action a la seule place que le chargeur connait.

check(ACTION_UI.count(UNE_ACTION) == 1 and ACTION_UI.count(FIN_BLOC) == 1 and
      COLLISION_UI != ACTION_UI and DOUBLON_UI != ACTION_UI,
      "les variantes du bloc <actions> sont baties sur un ancrage unique",
      (ACTION_UI.count(UNE_ACTION), ACTION_UI.count(FIN_BLOC)))
check(lire(ACTION).find("actions") is not None and
      lire(ACTION).find("widget").find("action") is None,
      "le fichier de depart declare bien son action au niveau <ui>")

# Ce que l'item 1 en voit : rien de mort. C'est justement le fond du probleme.
v = harnais(ACTION)
arbre = v._merge_into_source()
check(v._purge_orphelines(arbre) == 0,
      "le menage de l'item 1 ne coupe aucun cable ici : le nom est dans le "
      "fichier, c'est l'objet qui manque")
check(arbre.find("actions") is not None,
      "la fusion seule laisse le bloc ou il etait : l'affichage n'a rien a "
      "reparer, reparer est une decision d'ecriture")

# Le menage, appele seul.
check(v._remonte_actions(arbre) == 1,
      "_remonte_actions rend le nombre d'actions remontees")
check(arbre.find("actions") is None,
      "le bloc vide de ses actions disparait de la racine")
portes = [el.tag for el in arbre.find("widget")
          if el.tag in ("action", "widget", "layout")]
check(portes[0] == "action" and portes.count("action") == 1,
      "l'action est passee avant le premier objet du formulaire, comme la fait "
      "Qt Designer", portes)

# Le menage, par l'ecriture.
v = harnais(ACTION)
retires = v._write_ui_file(FIX_OUT)
r = lire(FIX_OUT)
texte_fix = open(FIX_OUT, encoding="utf-8").read()
check(retires == 0, "l'objet rendu par _write_ui_file reste le nombre de cables "
                    "coupes : rien de plus", retires)
check(r.find("actions") is None,
      "le fichier ecrit n'a plus de bloc <actions> de racine")
check(r.find("widget").find("action") is not None,
      "et il declare son action sous le formulaire")
check(liens(r) == LIENS_SOURCE + [("cacheAction", "titre")],
      "le cable n'a pas bouge, ni de place ni de nom", liens(r))
check("<string>Cacher le titre</string>" in texte_fix,
      "l'action remonte avec ses proprietes, pas vide")
check(v._remonte_actions(lire(FIX_OUT)) == 0,
      "une action deja sous le formulaire n'est pas redemenee")
v2 = harnais(FIX_OUT)
v2._write_ui_file(FIX_OUT2)
check(open(FIX_OUT2, encoding="utf-8").read() == texte_fix,
      "rouvrir le fichier repare et le relaisser rend exactement le meme "
      "fichier : le menage n'est pas une chasse qui recommence")

# Les deux garde-fous : un nom deja porte, et un nom en double.
v = harnais(COLLISION)
arbre = v._merge_into_source()
check(v._remonte_actions(arbre) == 1,
      "sur deux actions dont une seule a un nom libre, une seule monte")
bloc = arbre.find("actions")
check(bloc is not None and [a.get("name") for a in bloc] == ["titre"],
      "l'action qui porte le nom d'un widget du formulaire reste dans le bloc : "
      "setupUi() cree un attribut par nom, les deux s'ecraseraient en silence",
      [a.get("name") for a in bloc] if bloc is not None else None)
v = harnais(COLLISION)
v._write_ui_file(COLLISION_OUT)
r = lire(COLLISION_OUT)
check(r.find("actions") is not None and
      r.find("widget").find("action") is not None,
      "le fichier ecrit melange les deux : la libre enfantee, l'autre au bloc",
      [el.tag for el in r])
check(("cacheAction", "titre") in liens(r),
      "et le cable de l'action remontee tient toujours")

v = harnais(DOUBLON)
arbre = v._merge_into_source()
check(v._remonte_actions(arbre) == 1,
      "deux actions du meme nom : la premiere seule est remontee")
check([a.get("name") for a in arbre.find("actions")] == ["cacheAction"],
      "la seconde reste au bloc, son nom est desormais porte par le formulaire",
      [a.get("name") for a in arbre.find("actions")])

# Deux noms libres : c'est le fichier d'un vrai formulaire QMainWindow ancien.
v = harnais(DEUX)
arbre = v._merge_into_source()
check(v._remonte_actions(arbre) == 2,
      "deux actions au nom libre montent toutes les deux")
check(arbre.find("actions") is None,
      "et le bloc vide disparait quand son dernier enfant part")
montees = [el.get("name") for el in arbre.find("widget") if el.tag == "action"]
check(montees == ["cacheAction", "majAction"],
      "dans l'ordre ou le fichier les declare : le menage ne remelange rien",
      montees)

# Ce que le menage ne touche pas : ce qu'il ne comprend pas.
v = harnais(BLOC_VIDE)
check(v._write_ui_file(BLOC_VIDE_OUT) == 0,
      "un bloc <actions> vide n'invente aucune remontee")
check("<actions" in open(BLOC_VIDE_OUT, encoding="utf-8").read(),
      "et il sort tel qu'il est entre, vide avec lui")

v = harnais(SANS_NOM)
arbre = v._merge_into_source()
check(v._remonte_actions(arbre) == 0 and arbre.find("actions") is not None,
      "une action sans nom n'est pas remontee : rien a designer sous le "
      "formulaire")

v = harnais(ETRANGE)
arbre = v._merge_into_source()
check(v._remonte_actions(arbre) == 1,
      "l'action d'un bloc qui porte aussi un enfant inconnu est remontee "
      "malgre tout")
check(arbre.find("actions") is not None and
      arbre.find("actions").find("thing") is not None,
      "le bloc reste puisqu'il reste quelque chose dedans")

main = ET.Element("ui", version="4.0")
ET.SubElement(main, "class").text = "Form"
ET.SubElement(main, "actions").append(
    ET.Element("action", name="cacheAction"))
check(v._remonte_actions(main) == 0 and main.find("actions") is not None,
      "sans formulaire sous la racine, rien n'est deplace : on ne devine pas "
      "ou loger l'action")

# ── 6 bis. la preuve par l'execution, sur les deux etats du fichier ──────
# L'etat d'avant le correctif, refait a la main avec les memes morceaux que
# l'ecriture : fusion, menage des cables, puis l'ancien saut de la remontee.
v = harnais(ACTION)
arbre_avant = v._merge_into_source()
v._purge_orphelines(arbre_avant)
ET.indent(arbre_avant, space="  ")
ET.ElementTree(arbre_avant).write(AVANT_ACTIONS, encoding="utf-8",
                                  xml_declaration=True)
check(lire(AVANT_ACTIONS).find("actions") is not None and
      liens(lire(AVANT_ACTIONS)) == LIENS_SOURCE + [("cacheAction", "titre")],
      "le fichier d'avant le correctif a son bloc, son cable et rien d'autre")

SONDE_ACTIONS = r'''
import io, json, os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, %r)
from PyQt5 import QtWidgets, uic
from PyQt5.uic.properties import QtGui, QtCore
app = QtWidgets.QApplication([])
out = {}
def genere(chemin, cle):
    tampon = io.StringIO()
    try:
        uic.compileUi(chemin, tampon)
    except Exception as e:
        out[cle] = "ECHEC " + type(e).__name__ + ": " + str(e)
        return
    out[cle] = [l.strip() for l in tampon.getvalue().splitlines()
                if "cacheAction" in l]
def charge(chemin, cle):
    try:
        w = uic.loadUi(chemin)
    except Exception as e:
        out[cle] = {"erreur": type(e).__name__ + ": " + str(e)}
        return
    w.show()
    app.processEvents()
    action = getattr(w, "cacheAction", None)
    r = {"charge": w.objectName(),
         "classe": type(action).__name__ if action is not None else None,
         "cache_avant": w.titre.isHidden()}
    try:
        action.trigger()
        app.processEvents()
        r["cache_apres"] = w.titre.isHidden()
    except Exception as e:
        r["declenchement"] = type(e).__name__ + ": " + str(e)
    out[cle] = r
genere(%r, "genere_avant")
genere(%r, "genere_apres")
charge(%r, "avant")
charge(%r, "apres")
print(json.dumps(out))
'''


def sonde_actions():
    p = subprocess.run(
        [os.path.join(BUNDLE, "python.exe"), "-B", "-c",
         SONDE_ACTIONS % (os.path.join(BUNDLE, "Lib", "site-packages"),
                          AVANT_ACTIONS, FIX_OUT, AVANT_ACTIONS, FIX_OUT)],
        capture_output=True, text=True, env=env, timeout=300)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"erreur_sonde": (p.stdout + p.stderr)[-400:]}


mesure = sonde_actions()
genere_avant = mesure.get("genere_avant")
genere_apres = mesure.get("genere_apres")


def cree_action(etat):
    """uic cree-t-il un objet pour « cacheAction » dans le code qu'il genere ?"""
    return isinstance(etat, list) and any("QAction(" in l for l in etat)


check(isinstance(genere_apres, list) and cree_action(genere_apres) and
      any("triggered" in l for l in genere_apres),
      "le code que uic genere pour le fichier repare cree l'objet QAction et "
      "cable son signal : la place sous le formulaire est celle qu'il connait",
      (genere_apres, mesure.get("erreur_sonde")))
check(cree_action(genere_avant) is False,
      "le meme cable, l'action restee au bloc de racine, ne lui fait toujours "
      "aucun objet", genere_avant)
check(not cree_action(genere_avant) and
      "triggered" in str(genere_avant),
      "et uic le dit a sa facon : il s'arrete sur le signal d'un objet qu'il "
      "ne connait pas", genere_avant)
avant_actions = mesure.get("avant") or {}
check(avant_actions.get("charge") is None and
      "AttributeError" in (avant_actions.get("erreur") or "") and
      "cacheAction" in (avant_actions.get("erreur") or ""),
      "le fichier tel que l'ecrivait le plugin avant le correctif ne se charge "
      "toujours pas, sur le nom de l'action", avant_actions)
apres_actions = mesure.get("apres") or {}
check(apres_actions.get("charge") == "Form" and
      apres_actions.get("classe") == "QAction",
      "le fichier repare se charge, et l'eleve y trouve un objet QAction",
      (apres_actions, mesure.get("erreur_sonde")))
check(apres_actions.get("cache_avant") is False and
      apres_actions.get("cache_apres") is True,
      "declencher l'action cache bien le label : le cable mene quelque part",
      apres_actions)

print()
print("%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)

