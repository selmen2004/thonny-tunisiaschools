r"""Item 6 : un nom d'objet doit rester ecrivable dans le programme de l'eleve.

`_valid_qt_name` regardait la FORME du mot : des lettres, des chiffres, « _ », et
pas de chiffre initial. « class », « for », « None » passaient ce controle aux
erreurs — le panneau les acceptait, le modele les gardait, le fichier les ecrivait.
Or un nom d'objet n'existe que pour une chose : devenir « windows.<nom> » dans le
programme. Mesure faite sur le bundle (PyQt5 5.15.11, chargee hors ecran) :

  • « windows.class.setText(...) » — la ligne que le panneau propose juste sous
    le champ — est une SyntaxError. Le widget est dans la fenetre, il est
    inatteignable, et rien ne dit pourquoi.

  • un <widget name="__class__"> est pire : loadUi() le refuse d'un TypeError
    (« __class__ must be set to a class, not 'QPushButton' ») et LA FENETRE
    ENTIERE ne se construit plus. « __dict__ » pareil. « __init__ » se construit
    meme, en remplacant l'initialiseur de la fenetre par un bouton.

Sont donc refuses : le mot-cle et le nom en __double__. Rien d'autre, tout aussi
mesure : « match », « case », « _ » sont des mots-cles SOUPLES (ils ne le sont que
selon la place qu'ils occupent), « print », « id », « list » sont des noms communs
— ces ecritures passent et la fenetre se construit. Un nom accentue reste valide,
comme a l'item 4 : le garde-fou ne doit pas devenir plus strict que le langage.

Quatre portes sont fermées ici :

  • la frappe dans le champ « Nom »  → le champ se colore et explique le vrai motif ;
  • le modele passe par-dessus le panneau → `_save` refuse et nomme l'objet ;
  • le fichier ecrit a la main        → il s'ouvre, il explique, il se repare ;
  • les lignes que le panneau propose → plus de ligne fausse, une consigne.

Et une derniere, pour le code : l'ecrivain de l'attribut XML (`_renomme_le_widget`)
ne reporte pas un nom que le panneau aurait refuse.

Un mot sur la fabrique de noms, pendant obligé de tout cela : `_unique_name`
recommence « base plus un chiffre » tant que le candidat n'est pas valide. Un
garde-fou devenu trop strict ne refuse donc pas un nom de plus : il fait tourner
la recherche sans fin. La section 7 l'appelle sous filet, pour que ce temps mort
devienne un rouge au lieu de bloquer la machine.
"""
import ast
import keyword
import os
import shutil
import sys
import threading
import types
from xml.etree import ElementTree as ET

import chemins

BUNDLE = chemins.BUNDLE
PLUGIN = chemins.PAQUET
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tkinter as tk                                   # noqa: E402
import UIViewer                                        # noqa: E402
from UIViewer import UiViewerPlugin                    # noqa: E402

dialogues = []
UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: dialogues.append(("error",) + a),
    showinfo=lambda *a, **k: dialogues.append(("info",) + a),
    askyesno=lambda *a, **k: dialogues.append(("yesno",) + a))
UIViewer.filedialog = types.SimpleNamespace(
    askopenfilename=lambda **k: "",
    asksaveasfilename=lambda **k: "")
UIViewer.get_workbench = lambda: None

racine = tk.Tk()
racine.withdraw()

D = os.path.join(HERE, "_sortie", "mots_cles")
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)


def CHEMIN(nom):
    return os.path.join(D, nom)


# ── Les deux gabarits ────────────────────────────────────────
# IMPOSSABLE : ce qu'un eleve (ou un copain avec un editeur de texte) peut fort
# bien ecrire a la main : deux mots-cles et un dunder, relies par des cablages que
# le renommage devra suivre.
# LEGAL : les noms que la mesure a trouves praticables, pour que la suite prouve
# aussi que le garde-fou ne mord pas plus loin que le langage.

IMPOSSABLE_UI = r'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Gestion</class>
 <widget class="QDialog" name="Gestion">
  <property name="geometry"><rect><x>0</x><y>0</y><width>320</width><height>260</height></rect></property>
  <property name="windowTitle"><string>Salle des profs</string></property>
  <layout class="QVBoxLayout" name="colonne">
   <item>
    <widget class="QLabel" name="titre">
     <property name="text"><string>Rencontre</string></property>
    </widget>
   </item>
   <item>
    <widget class="QPushButton" name="class">
     <property name="text"><string>Ouvrir</string></property>
    </widget>
   </item>
   <item>
    <widget class="QLineEdit" name="for">
     <property name="placeholderText"><string>Saisir</string></property>
    </widget>
   </item>
   <item>
    <widget class="QLabel" name="__class__">
     <property name="text"><string>Score</string></property>
    </widget>
   </item>
   <item>
    <widget class="QPushButton" name="ok">
     <property name="text"><string>Valider</string></property>
    </widget>
   </item>
  </layout>
 </widget>
 <connections>
  <connection>
   <sender>class</sender>
   <signal>clicked()</signal>
   <receiver>Gestion</receiver>
   <slot>close()</slot>
  </connection>
  <connection>
   <sender>for</sender>
   <signal>textChanged(QString)</signal>
   <receiver>titre</receiver>
   <slot>clear()</slot>
  </connection>
 </connections>
 <resources/>
</ui>
'''

LEGAL_UI = r'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Gestion</class>
 <widget class="QDialog" name="Gestion">
  <property name="geometry"><rect><x>0</x><y>0</y><width>320</width><height>260</height></rect></property>
  <property name="windowTitle"><string>Salle des profs</string></property>
  <layout class="QVBoxLayout" name="colonne">
   <item>
    <widget class="QLabel" name="print">
     <property name="text"><string>Rencontre</string></property>
    </widget>
   </item>
   <item>
    <widget class="QPushButton" name="boutonOuvrir">
     <property name="text"><string>Ouvrir</string></property>
    </widget>
   </item>
   <item>
    <widget class="QLineEdit" name="case">
     <property name="placeholderText"><string>Saisir</string></property>
    </widget>
   </item>
   <item>
    <widget class="QLabel" name="_x">
     <property name="text"><string>Score</string></property>
    </widget>
   </item>
   <item>
    <widget class="QPushButton" name="match">
     <property name="text"><string>Valider</string></property>
    </widget>
   </item>
  </layout>
 </widget>
 <connections>
  <connection>
   <sender>boutonOuvrir</sender>
   <signal>clicked()</signal>
   <receiver>Gestion</receiver>
   <slot>close()</slot>
  </connection>
  <connection>
   <sender>case</sender>
   <signal>textChanged(QString)</signal>
   <receiver>print</receiver>
   <slot>clear()</slot>
  </connection>
 </connections>
 <resources/>
</ui>
'''

NOMS_IMPOSSABLES = ["titre", "class", "for", "__class__", "ok"]
NOMS_LEGAUX = ["print", "boutonOuvrir", "case", "_x", "match"]
MOTS_IMPOSSABLES = ["class", "for", "__class__"]


def ecrit(chemin, texte):
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)


def octets(chemin):
    with open(chemin, "rb") as f:
        return f.read()


bilan = [0, 0]
a_l_envers = []


def check(*a):
    """Sens officiel : (libelle, condition, detail)."""
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


def vue_sur(nom, texte):
    """Le gabarit, ecrit frais puis ouvert dans une vraie vue : le seul etat ou
    l'on puisse taper dans le champ « Nom », refuser un enregistrement et lire ce
    que le panneau propose."""
    chemin = CHEMIN(nom + ".ui")
    ecrit(chemin, texte)
    dialogues.clear()
    _top, v = fenetre(nom)
    v.load_new_ui_file(chemin)
    return v, chemin


def idx_de(v, nom):
    for i, (_c, props) in enumerate(v.widgets_data):
        if props.get("name") == nom:
            return i
    return None


def props_de(v, nom):
    i = idx_de(v, nom)
    return v.widgets_data[i][1] if i is not None else None


def noms_modele(v):
    return [p["name"] for _c, p in v.widgets_data]


def noms_fichier(chemin):
    return [w.get("name") for w in ET.parse(chemin).iter("widget")]


def _textes(chemin, balise):
    out = []
    for c in ET.parse(chemin).iter("connection"):
        el = c.find(balise)
        out.append(el.text if el is not None else None)
    return out


def sendeurs(chemin):
    return _textes(chemin, "sender")


def receivers(chemin):
    return _textes(chemin, "receiver")


def tape(v, ancien, nouveau):
    """Le geste du clavier dans le champ « Nom » : la trace du StringVar appelle
    _apply("name", var, idx) — pas d'appel direct, c'est le panneau qu'on teste."""
    i = idx_de(v, ancien)
    if i is None:
        return None
    v._show_properties(i)
    v._prop_vars["name"].set(nouveau)
    return v.widgets_data[i][1].get("name")


def champ(v):
    """(fond, explication) tels que l'eleve les voit."""
    e = getattr(v, "_name_entry", None)
    h = getattr(v, "_name_hint", None)
    return (e.cget("bg") if e is not None else None,
            h.cget("text") if h is not None else None)


def legendes(v):
    """Tout le texte affiche par le panneau de droite, dans l'ordre."""
    out = []
    file = list(v.prop_frame.winfo_children())
    while file:
        el = file.pop(0)
        try:
            if isinstance(el, tk.Label):
                out.append(el.cget("text"))
            file.extend(el.winfo_children())
        except tk.TclError:
            pass
    return out


APP = None
CHARGEES = []


def charge(chemin):
    """Un loadUi hors ecran : ce que le programme de l'eleve montrerait.
    QApplication et la fenetre doivent rester attaches a une variable, sinon le
    process meurt sans message (0xC0000409) ou l'objet C++ est rendu trop tot."""
    global APP
    from PyQt5 import QtWidgets, uic                   # noqa: E402
    if APP is None:
        APP = QtWidgets.QApplication([])
    w = uic.loadUi(chemin)
    CHARGEES.append(w)
    return w


def charge_ou_le_message(chemin):
    """None si la fenetre se construit, sinon la premiere ligne du refus."""
    try:
        charge(chemin)
        return None
    except Exception as e:                            # noqa: BLE001
        return "%s : %s" % (type(e).__name__, str(e).splitlines()[0][:90])


def nom_libre(v, base, delai=25):
    """Le nom que le plugin inventerait pour « base », avec un filet.

    `_unique_name` recommence « base plus un chiffre » tant que le candidat ne
    passe pas le controle. Si le controle refusait une forme que les chiffres ne
    reparent jamais — tout ce qui commence par « __ », par exemple — la boucle ne
    finirait pas. Le filet ne juge pas le produit : il rend un rouge a la place
    d'une machine bloquee. Le modele seul est lu ici, aucun widget Tk n'est touche
    depuis ce fil, donc l'appel reste sur.
    """
    boite = []

    def travailler():
        try:
            boite.append(v._unique_name(base))
        except Exception as e:                        # noqa: BLE001
            boite.append("exception : %s" % e)

    fil = threading.Thread(target=travailler, daemon=True)
    fil.start()
    fil.join(delai)
    return boite[0] if boite else None


def position_ou(texte, motif):
    """La place d'un motif dans un texte, ou None quand il a disparu.

    Les pinces d'ordre de la section 9 compareraient deux « .index() » : des
    qu'un mutant supprime la raison reservee, le premier leverait une ValueError,
    la suite mourrait avant son bilan, et la note du mutant ne serait plus
    lisible. Une absence doit rendre un rouge, pas un plantage.
    """
    i = texte.find(motif)
    return i if i >= 0 else None


# ── 1. la table des noms ─────────────────────────────────────

print("\n=== 1. ce que « nom valide » veut dire ===")
valide = UiViewerPlugin._valid_qt_name
reserve = UiViewerPlugin._reserve_python

check("tous les mots-cles de Python sont examines", len(keyword.kwlist) >= 33,
      len(keyword.kwlist))
laisses = [n for n in keyword.kwlist if valide(n)]
check("aucun mot-cle ne passe le controle du nom", laisses == [], laisses)
mauvaise_raison = [n for n in keyword.kwlist if reserve(n) != "mot-cle"]
check("et chacun est refuse pour ce qu'il est, pas pour sa forme",
      mauvaise_raison == [], mauvaise_raison)
for n in ("class", "None", "import", "lambda", "for"):
    check("le nom de l'enonce « %s » est refuse" % n,
          not valide(n) and reserve(n) == "mot-cle", reserve(n))

soupies = [n for n in ("match", "case", "type", "_") if not valide(n)]
check("les mots-cles souples restent des noms valides", soupies == [], soupies)
check("« match » est bien un souple et non un reserve",
      keyword.issoftkeyword("match") and not keyword.iskeyword("match"))
names_ = [n for n in ("print", "id", "list", "str", "input", "open")
          if not valide(n)]
check("les noms de builtins restent des noms valides", names_ == [], names_)

dunders = [n for n in ("__init__", "__class__", "__dict__", "__file__",
                       "__name__", "__slots__") if valide(n)]
check("les noms en __double__ sont refuses", dunders == [], dunders)
mauvais_dunder = [n for n in ("__init__", "__class__", "__dict__")
                  if reserve(n) != "dunder"]
check("refuses pour la bonne raison", mauvais_dunder == [], mauvais_dunder)
courts = [n for n in ("__", "___", "_x", "x_") if not valide(n)]
check("« __ », « ___ » et « _x » ne sont pas des noms en __double__",
      courts == [], courts)

check("un nom accentue reste valide, comme a l'item 4", valide("élan"))
check("un nom d'eleve normal reste valide", valide("boutonValider"))
for n in ("1er", "mon bouton", "a-b", "-"):
    check("la forme est toujours refusee : « %s »" % n,
          not valide(n) and reserve(n) is None, reserve(n))
check("le nom vide n'est pas un nom reserve : il garde son propre message",
      reserve("") is None and not valide(""))

nu = object.__new__(UiViewerPlugin)
check("la raison du nom vide n'a pas change",
      nu._name_problem("", 0) == "Le nom d'objet ne peut pas etre vide.",
      nu._name_problem("", 0))
check("la raison d'une forme boiteuse n'a pas change non plus",
      "lettres, chiffres" in nu._name_problem("1er", 0), nu._name_problem("1er", 0))

# ── 2. la frappe dans le panneau ─────────────────────────────

print("\n=== 2. ce que l'eleve voit pendant qu'il tape ===")
v2, F2 = vue_sur("legal", LEGAL_UI)
check("le fichier legal s'ouvre avec ses cinq objets",
      noms_modele(v2) == NOMS_LEGAUX, noms_modele(v2))
check("aucun de ces noms ne le rend inutilisable", v2._name_troubles() == [],
      v2._name_troubles())

journal = len(v2._ensure_history())
avant2 = octets(F2)
nom2 = tape(v2, "boutonOuvrir", "class")
fond, raison = champ(v2)
check("le mot-cle est refuse : le modele garde l'ancien nom",
      nom2 == "boutonOuvrir", nom2)
check("le mot-cle est refuse : le champ se colore", fond == "#5a1a1a", fond)
check("et l'explication nomme le mot en cause", "class" in raison, raison)
check("elle dit que c'est un mot reserve de Python", "mot reserve" in raison,
      raison)
check("elle ne renvoie pas l'eleve a une faute de frappe",
      "lettres, chiffres" not in raison, raison)
check("elle nomme la ligne que son programme ne peut pas ecrire",
      "windows.class" in raison, raison)
check("ce que l'eleve a tape n'est pas efface de son champ",
      v2._prop_vars["name"].get() == "class", v2._prop_vars["name"].get())
check("un refus ne coute aucune etape d'Annuler",
      len(v2._undo_stack) == journal, len(v2._undo_stack))
check("et ne leve pas le drapeau de travail perdu",
      v2._travail_modifie is False, v2._travail_modifie)
check("aucun octet n'a bouge sur le disque", octets(F2) == avant2)

nom2b = tape(v2, "boutonOuvrir", "__class__")
fond, raison = champ(v2)
check("le dunder est refuse aussi", nom2b == "boutonOuvrir", nom2b)
check("pour une autre raison : le nom est reserve par Python",
      "__double__" in raison, raison)
check("et cette raison-la dit que la fenetre entiere ne se construirait pas",
      "construire" in raison, raison)

# « type » : un mot-cle souple, et un nom que le fichier de ce test ne porte pas
# (le fixture, lui, emploie « match » — le renommage en « match » serait refuse
# pour doublon, ce qui est une autre regle, verifiee a l'item 4).
nom2c = tape(v2, "boutonOuvrir", "type")
fond, raison = champ(v2)
check("le mot-cle souple, lui, est accepte", nom2c == "type", nom2c)
check("le champ reprend sa couleur normale", fond == "#3c3c3c", fond)
check("l'explication a disparu", raison == "", raison)
check("accepter ce nom-la coute bien une etape d'Annuler",
      len(v2._undo_stack) == journal + 1, len(v2._undo_stack))
check("et leve le drapeau", v2._travail_modifie is True, v2._travail_modifie)
v2.undo()
check("Annuler rend le nom de depart",
      "boutonOuvrir" in noms_modele(v2) and "type" not in noms_modele(v2),
      noms_modele(v2))
check("le refus d'avant n'avait rien a annuler",
      len(v2._undo_stack) == journal, len(v2._undo_stack))
check("l'arbre lu par la fenetre n'a pas ete touche non plus",
      "boutonOuvrir" in [w.get("name") for w in v2._source_ui.iter("widget")],
      noms_fichier(F2))

# la regle regarde le mot entier, pas une de ses lettres
check("« for_x » reste un nom valide",
      valide("for_x") and reserve("for_x") is None)
check("« for_x » est accepte au clavier",
      tape(v2, "boutonOuvrir", "for_x") == "for_x", noms_modele(v2))

# ── 3. la derniere ligne avant le disque ─────────────────────

print("\n=== 3. le panneau n'est pas la seule porte ===")
v3, F3 = vue_sur("contournement", LEGAL_UI)
avant3 = octets(F3)
props_de(v3, "print")["name"] = "if"
troubles3 = v3._name_troubles()
dialogues.clear()
v3._save()
check("un mot-cle passe par-dessus le panneau : la feuille de noms le voit",
      any("if" in t for t in troubles3), troubles3)
check("et nomme le risque, pas la forme",
      any("mot reserve" in t for t in troubles3), troubles3)
check("l'enregistrement refuse : un seul avis, rien d'ecrit",
      [d[0] for d in dialogues] == ["error"], dialogues)
check("le fichier n'a pas bouge d'un octet", octets(F3) == avant3)
check("l'avis nomme l'objet en cause", "if" in str(dialogues),
      str(dialogues)[:160])
check("le widget garde son vrai nom dans le fichier",
      "print" in noms_fichier(F3), noms_fichier(F3))
nom3 = tape(v3, "if", "etiquette")
check("repare au clavier, le modele suit", nom3 == "etiquette", nom3)
dialogues.clear()
v3._save()
check("alors l'enregistrement passe", [d[0] for d in dialogues] == ["info"],
      dialogues)
check("et le nom repare est sur le disque", "etiquette" in noms_fichier(F3),
      noms_fichier(F3))
ref3 = octets(F3)
v3._write_ui_file(F3)
check("enregistrer deux fois ne change rien", octets(F3) == ref3)

props_de(v3, "match")["name"] = "__dict__"
dialogues.clear()
v3._save()
check("un dunder force dans le modele arrete aussi l'enregistrement",
      [d[0] for d in dialogues] == ["error"] and "__dict__" in str(dialogues),
      str(dialogues)[:160])
check("et le fichier n'est pas ecrit", octets(F3) == ref3)
check("la reparation au clavier rouvre l'enregistrement",
      tape(v3, "__dict__", "boutonValider") == "boutonValider", noms_modele(v3))

# ── 4. un fichier ecrit a la main ────────────────────────────

print("\n=== 4. le fichier du copain qui a tape « class » dans un editeur ===")
v4, F4 = vue_sur("impossible", IMPOSSABLE_UI)
check("il s'ouvre sans crasher, avec ses cinq objets",
      noms_modele(v4) == NOMS_IMPOSSABLES, noms_modele(v4))
troubles4 = v4._name_troubles()
check("le panneau sait des le depart qui est impossible",
      all(any(n in t for t in troubles4) for n in MOTS_IMPOSSABLES), troubles4)
check("les trois seulement", len(troubles4) == 3, troubles4)
check("les deux mots-cles portent la meme raison",
      len([t for t in troubles4 if "mot reserve" in t]) == 2, troubles4)
check("le dunder porte la sienne",
      len([t for t in troubles4 if "__double__" in t]) == 1, troubles4)
check("aucun nom sain n'est traine dans la liste",
      not any(n in t for t in troubles4 for n in ("titre", "ok")), troubles4)

# ce que le programme de l'eleve obtient de ce fichier : la fenetre ne se
# construit pas, a cause du dunder — mesure, pas opinion
erreur4 = charge_ou_le_message(F4)
check("loadUi refuse ce fichier tel quel (cause : __class__)",
      erreur4 is not None and "__class__" in erreur4, erreur4)

avant4 = octets(F4)
dialogues.clear()
v4._save()
check("le plugin ne le recopie donc pas tel quel : il refuse",
      [d[0] for d in dialogues] == ["error"] and len(dialogues) == 1, dialogues)
check("l'avis cite les trois noms",
      all(n in str(dialogues) for n in MOTS_IMPOSSABLES), str(dialogues)[:220])
check("et le fichier reste ce qu'il etait", octets(F4) == avant4)

for ancien, nouveau in (("class", "boutonOuvrir"), ("for", "saisie"),
                        ("__class__", "score")):
    tape(v4, ancien, nouveau)
check("les trois repares au clavier",
      noms_modele(v4) == ["titre", "boutonOuvrir", "saisie", "score", "ok"],
      noms_modele(v4))
check("plus rien a signaler", v4._name_troubles() == [], v4._name_troubles())
dialogues.clear()
v4._save()
check("l'enregistrement passe maintenant", [d[0] for d in dialogues] == ["info"],
      dialogues)
check("le fichier porte les noms repares",
      noms_fichier(F4)[1:] == ["titre", "boutonOuvrir", "saisie", "score", "ok"],
      noms_fichier(F4))
check("les cablages ont suivi les nouveaux noms",
      sendeurs(F4) == ["boutonOuvrir", "saisie"], sendeurs(F4))
check("et leurs recepteurs n'ont pas bouge",
      receivers(F4) == ["Gestion", "titre"], receivers(F4))
check("la classe de la fenetre et son titre ont survécu au passage",
      ET.parse(F4).find("class").text == "Gestion"
      and v4._src_root.get("title") == "Salle des profs",
      ET.parse(F4).find("class").text)
erreur4b = charge_ou_le_message(F4)
check("le fichier repare se construit", erreur4b is None, erreur4b)
if erreur4b is None:
    f4 = CHARGEES[-1]
    check("le bouton repare est bien un bouton qui porte son texte",
          type(f4.boutonOuvrir).__name__ == "QPushButton"
          and f4.boutonOuvrir.text() == "Ouvrir", f4.boutonOuvrir.text())
    check("l'etiquette sortie du dunder est bien une etiquette",
          type(f4.score).__name__ == "QLabel" and f4.score.text() == "Score",
          f4.score.text())
    f4.show()
    visible_avant = f4.isVisible()
    f4.boutonOuvrir.click()
    check("le cable renomme ferme toujours la fenetre",
          visible_avant and not f4.isVisible(),
          (visible_avant, f4.isVisible()))
    f4.show()
    f4.saisie.setText("Note 12")
    check("le second cable, renomme lui aussi, vide bien l'etiquette",
          f4.titre.text() == "", f4.titre.text())
else:
    check("le fichier repare se construit (suite arretée : bouton absent)", False)
    check("le fichier repare se construit (suite arretée : etiquette absente)",
          False)
ref4 = octets(F4)
v4._write_ui_file(F4)
check("double enregistrement identique apres reparation", octets(F4) == ref4)

_top4b, v4b = fenetre("relecture")
v4b.pack(fill=tk.BOTH, expand=True)
v4b.master.update()
v4b.load_new_ui_file(F4)
check("rouvrir le fichier repare ne signale plus rien",
      v4b._name_troubles() == [], v4b._name_troubles())
check("et le canevas porte les noms ecrits",
      noms_modele(v4b) == ["titre", "boutonOuvrir", "saisie", "score", "ok"],
      noms_modele(v4b))

# ── 5. les lignes que le panneau propose ─────────────────────

print("\n=== 5. aucune ligne proposee ne nomme un objet inatteignable ===")
v5, F5 = vue_sur("suggestions", IMPOSSABLE_UI)
v5._show_properties(idx_de(v5, "class"))
textes5 = legendes(v5)
proposees = [t for t in textes5 if "windows." in t]
check("le panneau ne propose plus « windows.class » nulle part",
      not proposees, proposees[:3])
check("il dit quoi faire a la place",
      any("Corrigez le nom" in t for t in textes5),
      [t for t in textes5 if "windows." in t or "Corrigez" in t][:3])
v5._show_properties(idx_de(v5, "ok"))
textes5b = legendes(v5)
check("un objet sain garde toutes ses lignes",
      any("windows.ok" in t for t in textes5b),
      [t for t in textes5b if "windows." in t][:3])
check("et n'a rien a corriger",
      not any("Corrigez le nom" in t for t in textes5b))
tape(v5, "class", "boutonOuvrir")
v5._show_properties(idx_de(v5, "boutonOuvrir"))
textes5c = legendes(v5)
check("le nom repare rouvre les propositions",
      any("windows.boutonOuvrir" in t for t in textes5c),
      [t for t in textes5c if "windows." in t][:3])
check("l'avertissement a disparu avec le nom impossible",
      not any("Corrigez le nom" in t for t in textes5c))

# ── 6. la liberte des noms legaux tient jusqu'a Qt ───────────

print("\n=== 6. ce qui reste legal tient jusqu'a l'execution ===")
v6, F6 = vue_sur("toujours_legal", LEGAL_UI)
dialogues.clear()
v6._save()
check("aucun de ces noms n'arrete l'enregistrement",
      [d[0] for d in dialogues] == ["info"], dialogues)
check("le fichier les a tous gardes", noms_fichier(F6)[1:] == NOMS_LEGAUX,
      noms_fichier(F6))
erreur6 = charge_ou_le_message(F6)
check("et la fenetre se construit telle quelle", erreur6 is None, erreur6)
if erreur6 is None:
    f6 = CHARGEES[-1]
    check("« case », mot-cle souple, designe bien le champ qu'il etait",
          type(f6.case).__name__ == "QLineEdit", type(f6.case).__name__)
    check("« match » designe le bouton du fichier",
          type(f6.match).__name__ == "QPushButton", type(f6.match).__name__)
    check("« print », nom de builtin, designe l'etiquette",
          type(f6.print).__name__ == "QLabel" and f6.print.text() == "Rencontre",
          type(f6.print).__name__)
    check("« _x » designe l'autre etiquette",
          type(f6._x).__name__ == "QLabel" and f6._x.text() == "Score",
          type(f6._x).__name__)
    cassees = []
    for nom in NOMS_LEGAUX:
        ligne = "windows." + nom + '.setText("x")'
        try:
            compile(ligne, "<eleve>", "exec")
        except SyntaxError as e:
            cassees.append("%s -> %s" % (ligne, e.msg))
    check("chaque ligne que l'eleve ecrira compile", cassees == [], cassees)
else:
    for attente in ("« case », mot-cle souple, designe bien le champ qu'il etait",
                    "« match » designe le bouton du fichier",
                    "« print », nom de builtin, designe l'etiquette",
                    "« _x » designe l'autre etiquette"):
        check(attente + " (fenetre absente)", False)
    check("chaque ligne que l'eleve ecrira compile (fenetre absente)", False)
ref6 = octets(F6)
v6._write_ui_file(F6)
check("enregistrer deux fois ne change rien", octets(F6) == ref6)
check("et les noms legaux n'ont laisse aucune connexion sur le carreau",
      sendeurs(F6) == ["boutonOuvrir", "case"], sendeurs(F6))

# ── 7. les noms que le plugin fabrique lui-meme ──────────────

print("\n=== 7. ce que le plugin nomme tout seul ===")
v7, F7 = vue_sur("palette", LEGAL_UI)
mauvais = []
for cls, _lbl, _ico, _desc in UIViewer.WIDGET_DEFS:
    n = len(v7.widgets_data)
    v7._add_widget(cls)
    nom = v7.widgets_data[n][1]["name"]
    if not valide(nom):
        mauvais.append("%s -> %s" % (cls, nom))
check("chaque classe de la palette recoit un nom ecrivable",
      mauvais == [], mauvais)
check("neuf widgets ont bien ete ajoutes",
      len(v7.widgets_data) == len(noms_modele(v7)) == 5 + len(UIViewer.WIDGET_DEFS),
      len(v7.widgets_data))
check("et aucun ne se bat avec un nom deja dans le fichier",
      v7._name_troubles() == [], v7._name_troubles())
# la base d'un nom ne peut pas devenir un mot-cle ; si elle le devenait un jour,
# _unique_name doit s'en sortir sans boucler
empeche = nom_libre(v7, "class")
check("une base mot-cle est repelee par un suffixe, sans boucle",
      empeche == "class1" and valide(empeche), empeche)
empeche2 = nom_libre(v7, "__init__")
check("une base en __double__ aussi",
      empeche2 == "__init__1" and valide(empeche2), empeche2)
check("et la recherche d'un nom s'arrete toujours : aucun appel n'a dure",
      empeche is not None and empeche2 is not None, (empeche, empeche2))

# ── 8. l'ecrivain de l'attribut XML ──────────────────────────

print("\n=== 8. l'ecrivain du nom refuse ce que le panneau a refuse ===")
v8, F8 = vue_sur("ecrivain", LEGAL_UI)
i8 = idx_de(v8, "boutonOuvrir")
p8 = v8.widgets_data[i8][1]
el8 = None
for el in v8._source_ui.iter("widget"):
    if el.get("name") == "boutonOuvrir":
        el8 = el
check("l'element du fichier existe avant l'essai", el8 is not None)
p8["name"] = "return"
resultat = v8._renomme_le_widget(el8, p8)
check("le mot-cle n'est pas reporte sur l'attribut XML",
      resultat is None and el8.get("name") == "boutonOuvrir",
      (resultat, el8.get("name")))
p8["name"] = "boutonValider"
resultat2 = v8._renomme_le_widget(el8, p8)
check("un nom correct l'est toujours",
      resultat2 == ("boutonOuvrir", "boutonValider")
      and el8.get("name") == "boutonValider", (resultat2, el8.get("name")))
# l'element passe ici vient de l'arbre lu : le nom que l'essai ecrit expres
# (boutonValider) s'y reporte, c'est le contrat de _renomme_le_widget. Ce que la
# ligne verifie, c'est que RIEN D'AUTRE n'a bouge dans cet arbre.
check("l'arbre source n'a pas ete bouleverse ailleurs",
      [w.get("name") for w in v8._source_ui.iter("widget")]
      == ["Gestion", "print", "boutonValider", "case", "_x", "match"],
      [w.get("name") for w in v8._source_ui.iter("widget")])
check("les cinq objets du fichier sont toujours tous la",
      len([w.get("name") for w in v8._source_ui.iter("widget")]) == 6,
      [w.get("name") for w in v8._source_ui.iter("widget")])

# ── 9. attache au fichier : les ancres du controle ───────────

print("\n=== 9. le code est ecrit pour durer ===")
source = open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
arbre9 = ast.parse(source)
meth = {n.name: n for n in ast.walk(arbre9) if isinstance(n, ast.FunctionDef)}
seg = lambda n: ast.get_source_segment(source, meth[n])                   # noqa: E731

check("le module importe la regle de Python elle-meme", "import keyword" in source)
r9 = seg("_reserve_python")
check("le mot-cle vient de keyword.iskeyword, pas d'une liste maison",
      "keyword.iskeyword(name)" in r9)
check("le dunder est reconnu par sa forme, pas par une liste de noms",
      'name.startswith("__")' in r9 and 'name.endswith("__")' in r9)
v9 = seg("_valid_qt_name")
check("le controle du nom appelle la regle reservee", "_reserve_python(name)" in v9)
# depuis l'item 14, la forme a son propre nom : « class » est bien forme mais
# reserve (un chiffre le rend libre), alors que « mon-bouton » est mal forme et
# qu'aucun chiffre n'y change rien. Les deux questions ne peuvent plus etre
# melees la ou la fabrique de noms doit repondre a la seconde seulement.
f9 = seg("_forme_valide")
check("le controle du nom appelle la regle de forme, il ne la remplace pas",
      "_forme_valide(name)" in v9, v9[-160:])
check("il ne s'est pas substitue a la forme : la forme reste testee, chez elle",
      "first.isalpha()" in f9, f9[-160:])
b9 = seg("_base_reparee")
check("la fabrique de noms repare sur la MEME regle de forme, pas une copie",
      "_forme_valide(base)" in b9 and "_forme_valide(reparee)" in b9)
p9 = seg("_name_problem")
avant = position_ou(p9, "mot-cle")
apres = position_ou(p9, "lettres, chiffres")
check("le panneau donne la raison reservee AVANT la raison de forme",
      avant is not None and apres is not None and avant < apres,
      (avant, apres))
check("les deux raisons sont distinctes",
      "__double__" in p9 and "windows.%s" in p9)
t9 = seg("_name_troubles")
check("la derniere ligne avant le disque connait les deux aussi",
      "mot reserve" in t9 and "__double__" in t9)
avant_t = position_ou(t9, "mot reserve")
apres_t = position_ou(t9, "lettres, chiffres")
check("et elle les pose avant le controle de forme",
      avant_t is not None and apres_t is not None and avant_t < apres_t,
      (avant_t, apres_t))
pan9 = seg("_show_properties")
check("la rangee de methodes se vide pour un nom impossible",
      "methodes = [] if reserve" in pan9)
check("et l'eleve recoit une consigne, pas une page blanche",
      "Corrigez le nom ci-dessus" in pan9)
w9 = seg("_write_changed")
check("l'ecrivain des proprietes ne s'occupe toujours pas du nom",
      'el.set("name"' not in w9)
check("aucun QMessageBox dans l'editeur visuel", "QMessageBox" not in source)

for top in fenetres:
    top.destroy()
racine.update()

check("aucun controle de cette suite n'est ecrit dans l'autre sens",
      a_l_envers == [], a_l_envers)

print("\n%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)
