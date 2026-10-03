r"""Item 8 : la taille d'un tableau n'est plus sans bornes.

Le defaut avait plusieurs bords, et les deux premiers faisaient mal. Saisir
« -1 » dans le champ « Lignes » du panneau passait par-dessus la tete du modele
sans controle : le fichier partait avec <rowCount>-1</rowCount>, et
_adjust_count, appele avec ce nombre, faisait `have[-1:]` — la tranche qui, sur
une liste, designe le DERNIER element : un en-tete de ligne titre (« Eleve 3 »)
disparait a chaque fois (mesure, item 8). Qt, de son cote, lisait ce fichier la
comme un tableau SANS ligne : les titres restes dans le XML n'etaient atteints
par aucune cellule. A l'autre bout, « 10000 » ecrivait dix mille elements <row>,
151 267 octets, et l'eleve qui rouvrait le fichier attendait des minutes.

Le troisieme bord s'est mesure pendant la writing de cette suite : borner le
FICHIER ne suffit pas si son OUVERTURE dessine une case Tk par cellule. Mille
lignes sur mille colonnes — desormais licites sous le plafond — faisaient un
million de Labels dans l'apercu, et la fenetre ne rendait plus la main. Le cap
de dessin est donc une regle distincte du plafond d'ecriture, et les sections 5
et 13 la verifient lune et l'autre.

La correction pose quatre portes, et la suite verifie les quatre :

  • le champ refuse et LE DIT (couleur + explication), comme le champ « Nom »
    depuis l'item 6 — le modele garde la derniere taille qui s'inscrivait, et le
    refus ne coute pas un coup d'Annuler ;
  • l'ecriture borne aussi, independamment de la saisie : le <number> et le
    nombre d'elements <row>/<column> ne peuvent plus se contredire ;
  • un compte qui n'est pas une taille (negatif, vide, du texte) ne se convertit
    pas en « zero lignes » : il ne change rien au fichier, pour ne pas vider un
    tableau qui porte des en-tetes ;
  • l'apercu reste un dessin : le nombre de cases Tk est borne par une regle,
    et le reste du tableau s'annonce par un « … ».

Le plafond, lui, ne descend jamais au-dessous de ce que le document porte deja :
un tableau de 1 200 lignes n'est pas reducible a 1 000 par un geste de saisie,
et le plafond ne se resserre pas apres qu'on l'a reduit — l'eleve peut toujours
revenir a la taille du fichier. L'editeur ne detruit pas ce qu'il n'a pas cree.

Les libelles des controles restent sans accents (l'imprimante de la batterie est
en cp1252), les valeurs affichees peuvent en porter.

    Lancement :
    C:\...\Thonny\python.exe -B tests\test_tailles.py
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
# TUNISIASCHOOLS_COPIE : le dossier d'une COPIE mutee du module, pose par
# tests\mutants_tailles.py. Sans lui, c'est le module livre qui est teste.
PLUGIN = os.environ.get("TUNISIASCHOOLS_COPIE") or \
    r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BUNDLE, "Lib", "site-packages")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")
sys.path.insert(0, SITE)
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Le defaut de cet item etait justement de ne pas rendre la main : un tableau
# trop grand se dessine un million de cases, et la fenetre ne revient plus.
# Une suite qui mesurerait ce chemin sans garde pourrait pendouiller la batterie
# entiere. Ce fil veille : il Echoue la suite, il ne l'attend pas.
EN_MARCHE = [True]
DELAI = int(os.environ.get("TUNISIASCHOOLS_DELAI") or 300)


def _veille():
    debut = time.time()
    while EN_MARCHE[0] and time.time() - debut < DELAI:
        time.sleep(0.5)
    if EN_MARCHE[0]:
        print("  FAIL la suite ne s'est pas terminee au bout de %d s : un "
              "chemin de tableau ne rend plus la main (watchdog, item 8)"
              % DELAI, flush=True)
        os._exit(1)


threading.Thread(target=_veille, daemon=True).start()

import tkinter as tk                                    # noqa: E402
import UIViewer                                        # noqa: E402
from UIViewer import UiViewerPlugin                     # noqa: E402

CHEMIN_SOURCE = getattr(UIViewer, "__file__",
                        os.path.join(PLUGIN, "UIViewer.py"))
source = open(CHEMIN_SOURCE, encoding="utf-8").read()

PLAFOND = UiViewerPlugin.TAILLE_MAX_TABLE

dialogues = []

# La stub messagebox : l'editeur visuel ne doit jamais ouvrir de boite Qt, et
# cette suite n'appelle aucun chemin qui en affiche une. Les dialogues sont
# comptes, jamais affiches.
UIViewer.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: dialogues.append(("error",) + a),
    showwarning=lambda *a, **k: dialogues.append(("warning",) + a),
    showinfo=lambda *a, **k: dialogues.append(("info",) + a),
    askyesno=lambda *a, **k: True,
    askyesnocancel=lambda *a, **k: True)
UIViewer.filedialog = types.SimpleNamespace(
    askopenfilename=lambda **k: "", asksaveasfilename=lambda **k: "")
UIViewer.get_workbench = lambda: None

racine = tk.Tk()
racine.withdraw()

D = os.path.join(HERE, "_sortie", "tailles")
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)


def CHEMIN(nom):
    return os.path.join(D, nom)


def ecrit(nom, texte):
    p = CHEMIN(nom)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)
    return p


def tableau_ui(n_lignes, n_colonnes=2, titres=True):
    lignes = "".join(
        ('  <row><property name="text"><string>Eleve %d</string></property>'
         '</row>' % i) if titres else '  <row/>'
        for i in range(1, n_lignes + 1))
    colonnes = "".join(
        ('  <column><property name="text"><string>Cote %d</string></property>'
         '</column>' % j) if titres else '  <column/>'
        for j in range(1, n_colonnes + 1))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<ui version="4.0">\n'
            ' <class>Notes</class>\n'
            ' <widget class="QWidget" name="Notes">\n'
            '  <property name="geometry"><rect><x>0</x><y>0</y><width>400'
            '</width><height>300</height></rect></property>\n'
            '  <property name="windowTitle"><string>Notes</string></property>\n'
            '  <widget class="QTableWidget" name="tableNotes">\n'
            '   <property name="geometry"><rect><x>20</x><y>20</y><width>300'
            '</width><height>200</height></rect></property>\n'
            '   <property name="rowCount"><number>%d</number></property>\n'
            '   <property name="columnCount"><number>%d</number></property>\n'
            % (n_lignes, n_colonnes)) + lignes + colonnes + \
        '  </widget>\n </widget>\n</ui>\n'


TROIS = ecrit("tableau_trois_lignes.ui", tableau_ui(3))
GROS = ecrit("tableau_mille_deux.ui", tableau_ui(1200))

bilan = [0, 0]
a_l_envers = []


def check(*a):
    """(libelle, condition, detail) — l'ordre officiel du depot."""
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


def accord(chemin):
    """Ce que le fichier dit de la taille, et ce qu'il en porte d'elements.

    L'invariant de l'item 8 est la : le <number> et le compte des <row> ne
    peuvent plus se contredire, et aucun des deux n'est negatif ni demesure.

    Lu de facon tolérante : un produit qui ne rend pas un fichier lisible est
    une FAUTE a compter, pas un accident qui arrete la suite entiere (la regle
    des mutants : echouer, ne pas tomber).
    """
    vide = {"rowCount": "", "columnCount": "", "row": -1, "column": -1,
            "titres row": [], "titres column": [], "octets": 0}
    try:
        rac = ET.parse(chemin).getroot()
    except Exception:
        return vide
    t = next((w for w in rac.iter("widget")
              if w.get("class") == "QTableWidget"), None)
    if t is None:
        # un produit qui ecrit un fichier sans tableau n'a pas de quoi repondre :
        # la meme clef vide, pour que la suite lise un dictionnaire partout.
        return vide
    compte = {}
    for p in t.findall("property"):
        if p.get("name") in ("rowCount", "columnCount"):
            n = p.find("number")
            compte[p.get("name")] = None if n is None else n.text
    titres = {}
    for tag in ("row", "column"):
        titres[tag] = []
        for el in t.findall(tag):
            s = el.find("property/string")
            titres[tag].append(None if s is None else s.text)
    return {"rowCount": compte.get("rowCount"),
            "columnCount": compte.get("columnCount"),
            "row": len(titres["row"]), "column": len(titres["column"]),
            "titres row": titres["row"], "titres column": titres["column"],
            "octets": os.path.getsize(chemin)}


ABSENT = "<attribut jamais pose>"


def nombre(texte):
    """Un <number> du fichier rendu en entier, ou None s'il n'en est pas un.

    Lire un fichier que le produit a mué ne doit jamais faire tomber la suite :
    la comparaison echoue, elle ne s'interrompt pas.
    """
    return int(texte) if str(texte or "").isdigit() else None


def attendu_pour(donnee, deja):
    """L'oracle de la suite : ce que le FICHIER doit porter pour cette demande.

    Il est ecrit ici, en toutes lettres, et non demande au produit : un mutant
    qui deplacerait sa propre borne resterait d'accord avec lui-meme et
    survivrait. Une valeur qui n'est pas une taille (texte vide, mot, nombre
    negatif) ne change rien au fichier ; au-dessus du plafond, c'est le plafond
    qui s'ecrit — sauf si le tableau porte deja plus, auquel cas il le garde.
    """
    try:
        n = int(donnee)
    except (TypeError, ValueError):
        return deja
    if n < 0:
        return deja
    return min(n, max(PLAFOND, deja))


def saisis(top, v, cle, texte):
    """Tape dans le champ du panneau, comme l'eleve, et rend ce qui en resulte.

    Tout est lu de facon tolérante : un mutant qui casse la porte doit faire
    ECHOUER le controle, pas tomber la suite entiere.
    """
    var = (getattr(v, "_prop_vars", None) or {}).get(cle)
    if var is not None:
        var.set(texte)
    top.update()
    modele = ABSENT
    donnees = getattr(v, "widgets_data", None) or []
    if donnees:
        modele = donnees[0][1].get(cle, ABSENT)
    couleur = None
    entry = (getattr(v, "_taille_champs", None) or {}).get(cle)
    if entry is not None:
        try:
            couleur = entry.cget("bg")
        except tk.TclError:
            couleur = None
    hint = getattr(v, "_taille_hint", None)
    explication = None
    if hint is not None:
        try:
            explication = hint.cget("text") or ""
        except tk.TclError:
            explication = None
    return {"modele": modele, "couleur": couleur, "explication": explication,
            "champ": var is not None}


def taille(v, cle):
    """La taille que le modele porte, lue sans supposer que rien ne casse."""
    donnees = getattr(v, "widgets_data", None) or []
    return donnees[0][1].get(cle, ABSENT) if donnees else ABSENT


def dit(r):
    """L'explication posee sous les champs, en texte toujours exploitable."""
    return r["explication"] or ""


def ecrire(v, p, nom):
    """Appuie sur « Enregistrer » sans jamais faire tomber la suite.

    Un produit qui leve sur une ecriture est note, il n'interrompt pas les 250
    controles qui suivent : le check n'est emis QUE si le produit a leve, pour
    qu'une suite propre garde exactement le meme nombre de controles.
    """
    try:
        v._write_ui_file(p)
    except Exception as e:
        check("%s : l'ecriture traverse le produit sans lever" % (nom,), False,
              "%s: %s" % (type(e).__name__, str(e)[:60]))


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
t = w.findChild(QtWidgets.QTableWidget, "tableNotes")
if t is None:
    # un tableau pose par l'editeur porte le nom que la fabrique lui a donne,
    # pas celui du fixture : c'est le premier QTableWidget qui compte ici
    t = w.findChild(QtWidgets.QTableWidget)
if t is None:
    print(json.dumps({"erreur": "aucun QTableWidget dans la fenetre"}))
    sys.exit(0)
titres = []
for i in range(t.rowCount()):
    it = t.verticalHeaderItem(i)
    titres.append(None if it is None else it.text())
print(json.dumps({"rowCount": t.rowCount(), "columnCount": t.columnCount(),
                  "titres": titres}, ensure_ascii=False))
'''


def mesure_qt(chemin):
    if not os.path.exists(chemin):
        return {"erreur": "aucun fichier ecrit : rien que Qt puisse construire"}
    script = (SONDE_QT.replace("@@SITE@@", repr(SITE))
                      .replace("@@FICHIER@@", repr(chemin)))
    try:
        p = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", "-c",
                            script], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=ENV,
                           timeout=180)
    except subprocess.TimeoutExpired:
        return {"erreur": "le fils Qt n'a pas rendu de resultat"}
    lignes = (p.stdout or "").strip().splitlines()
    for ligne in reversed(lignes):
        try:
            return json.loads(ligne)
        except ValueError:
            continue
    return {"erreur": "aucun resultat JSON : " + (p.stderr or "")[-160:]}


# ————— 1. la porte refuse le negatif, et le dit —————
print("\n=== 1. un nombre negatif de lignes n'est pas une taille ===")
top1, v1 = fenetre("tailles-porte")
v1.load_new_ui_file(TROIS)
v1._select(0)
check("le tableau lu fait bien trois lignes (le controle n'est pas creux)",
      taille(v1, "rows") == 3, taille(v1, "rows"))
check("deux colonnes", taille(v1, "columns") == 2, taille(v1, "columns"))
check("les deux champs de taille sont branches",
      sorted(getattr(v1, "_taille_champs", None) or {}) == ["columns", "rows"],
      sorted(getattr(v1, "_taille_champs", None) or {}))
r = saisis(top1, v1, "rows", "-1")
check("repondre a -1 : le modele garde les trois lignes", r["modele"] == 3,
      r["modele"])
check("le champ se colore, l'eleve voit que son nombre n'est pas passe",
      r["couleur"] == "#5a1a1a", r["couleur"])
check("et une explication s'ecrit sous les champs",
      "negatif" in dit(r), dit(r)[:70])
check("l'explication parle bien des lignes", "ligne" in dit(r), dit(r)[:70])
r = saisis(top1, v1, "rows", "-0")
check("-0 est zero, pas un signe : il passe", r["modele"] == 0, r["modele"])
check("et le champ reprend sa couleur normale", r["couleur"] == "#3c3c3c",
      r["couleur"])
check("l'explication s'efface quand la valeur passe", r["explication"] == "",
      repr(r["explication"]))
saisis(top1, v1, "rows", "3")
check("revenue a 3, la taille est la bonne", taille(v1, "rows") == 3,
      taille(v1, "rows"))

# ————— 2. la porte refuse au-dessus du plafond —————
print("\n=== 2. et un nombre demesure non plus ne s'ecrit pas ===")
r = saisis(top1, v1, "rows", "10000")
check("10000 lignes refusees : le modele reste a 3", r["modele"] == 3,
      r["modele"])
check("le champ est colorie", r["couleur"] == "#5a1a1a", r["couleur"])
check("l'explication cite le plafond de l'editeur",
      str(PLAFOND) in dit(r), dit(r)[:80])
check("et dit pourquoi : une ligne XML par ligne reclamee",
      "ligne XML" in dit(r), dit(r)[:80])
for n in (0, 1, 2, 3, PLAFOND - 1, PLAFOND):
    r = saisis(top1, v1, "rows", str(n))
    check("%d lignes acceptee" % n, r["modele"] == n, r["modele"])
    check("    sans coloration ni explication pour %d" % n,
          r["couleur"] == "#3c3c3c" and r["explication"] == "",
          (r["couleur"], dit(r)[:40]))
r = saisis(top1, v1, "rows", str(PLAFOND + 1))
check("%d lignes refusee, on reste a %d" % (PLAFOND + 1, PLAFOND),
      r["modele"] == PLAFOND, r["modele"])
r = saisis(top1, v1, "columns", "-1")
check("la meme porte garde aussi les colonnes", r["modele"] == 2, r["modele"])
check("et l'explication parle de colonnes", "colonnes" in dit(r), dit(r)[:70])
saisis(top1, v1, "rows", "3")
saisis(top1, v1, "columns", "2")

# ————— 3. les en-tetes titres ne disparaissent plus —————
print("\n=== 3. ce que le refus laisse dans le fichier ===")
AVANT = CHEMIN("accord_apres_refus.ui")
ecrire(v1, AVANT, "3 : apres les refus")
_refus = accord(AVANT)
check("un refus n'ecrit rien de contradictoire", _refus["rowCount"] == "3"
      and _refus["row"] == 3, _refus)
check("aucun <rowCount>-1</rowCount> dans le fichier",
      _refus["rowCount"] != "-1", _refus["rowCount"])
check("les trois titres d'eleve sont toujours la",
      _refus["titres row"] == ["Eleve 1", "Eleve 2", "Eleve 3"],
      _refus["titres row"])
saisis(top1, v1, "rows", "-1")
APRES = CHEMIN("accord_apres_refus_bis.ui")
ecrire(v1, APRES, "3 : le geste refuse ne change rien")
check("le fichier est identique avant et apres le geste refuse",
      accord(APRES) == _refus, [accord(APRES), _refus])
mes = mesure_qt(APRES)
check("Qt construit bien trois lignes, pas zero", mes.get("rowCount") == 3, mes)
check("et atteint les trois titres que l'eleve avait ecrits",
      mes.get("titres") == ["Eleve 1", "Eleve 2", "Eleve 3"], mes.get("titres"))

# ————— 4. l'ancienne tranche, mesuree : le -1 qui mangeait le dernier titre —————
print("\n=== 4. la faute que la garde peche ===")
_el = ET.fromstring(
    '<widget class="QTableWidget" name="t">'
    '<row><property name="text"><string>Eleve 1</string></property></row>'
    '<row><property name="text"><string>Eleve 3</string></property></row>'
    '</widget>')


def ancienne_adjust(el, tag, want):
    """Le corps d'_adjust_count AVANT l'item 8, rejoue ici : c'est la mesure,
    pas une hypothese — `have[-1:]` designe le DERNIER element de la liste."""
    have = el.findall(tag)
    for extra in have[want:]:
        el.remove(extra)
    for _ in range(want - len(have)):
        ET.SubElement(el, tag)
    return [e.find("property/string").text for e in el.findall(tag)]


perdus = ancienne_adjust(ET.fromstring(ET.tostring(_el)), "row", -1)
check("l'ancienne tranche sur -1 effacait bien un titre",
      perdus == ["Eleve 1"], perdus)
v1._adjust_count(_el, "row", -1)
check("la version livree ne mange plus la fin de la liste",
      [e.find("property/string").text for e in _el.findall("row")]
      == ["Eleve 1", "Eleve 3"],
      [e.find("property/string").text for e in _el.findall("row")])
check("et ne vide pas le tableau non plus : un compte negatif n'est pas une "
      "taille qu'on peut dessiner", len(_el.findall("row")) == 2,
      len(_el.findall("row")))
_elN = ET.fromstring('<widget class="QTableWidget" name="t">'
                     '<row><property name="text"><string>Eleve 1</string>'
                     '</property></row></widget>')
for absurde in ("abc", None, ""):
    try:
        v1._adjust_count(_elN, "row", absurde)
        leve = None
    except Exception as e:
        leve = "%s: %s" % (type(e).__name__, str(e)[:40])
    check("%r ne detruit aucune ligne existante et ne leve pas" % (absurde,),
          leve is None and len(_elN.findall("row")) == 1,
          (leve, len(_elN.findall("row"))))
_el2 = ET.fromstring('<widget class="QTableWidget" name="t"><row/></widget>')
v1._adjust_count(_el2, "row", 0)
check("vouloir zero ligne reste zero ligne, pas une de plus",
      len(_el2.findall("row")) == 0, len(_el2.findall("row")))
_el3 = ET.fromstring('<widget class="QTableWidget" name="t"><row/></widget>')
v1._adjust_count(_el3, "row", 3)
check("et grandir ajoute bien la difference",
      len(_el3.findall("row")) == 3, len(_el3.findall("row")))

# ————— 5. l'ecriture borne, meme sans passer par le champ —————
print("\n=== 5. le <number> et les elements ne peuvent plus se contredire ===")
# Ces valeurs n'atteignent jamais le modele par le panneau, qui les refuse :
# elles y entrent par un autre chemin (une restauration d'annulation, un
# fichier ecrit a la main, un futur lecteur qui croirait <rowCount>). L'ecriture
# doit les rattraper toute seule.
HOSTILES = [-7, -1, 0, 1, 4, PLAFOND, PLAFOND + 1, 999999, "abc", None, "",
            "3.5", True]
top_r, v_r = fenetre("tailles-relecture")
for donnee in HOSTILES:
    nom = str(donnee) if str(donnee) else "vide"
    top, v = fenetre("tailles-mur-%s" % (nom,))
    v.load_new_ui_file(TROIS)
    v._select(0)
    v.widgets_data[0][1]["rows"] = donnee
    v.widgets_data[0][1]["columns"] = donnee
    p = CHEMIN("mur_%s.ui" % (nom.replace(".", "_").replace("'", ""),))
    try:
        v._write_ui_file(p)
        leve = None
    except Exception as e:
        leve = "%s: %s" % (type(e).__name__, str(e)[:60])
    check("%s : l'ecriture rend la main" % (nom,), leve is None, leve)
    a = accord(p) if os.path.exists(p) else None
    if a is None:
        # un mutant peut legalement refuser d'ecrire : la suite Echoue alors ce
        # controle, elle ne s'arrete pas la
        a = {"rowCount": "", "columnCount": "", "row": -1, "column": -1,
             "titres row": [], "titres column": [], "octets": 0}
    # un texte qui n'est pas une taille ne doit JAMAIS atteindre le fichier :
    # le tableau y reste ce que le fichier avait deja pose. L'attente est calculee
    # ICI, pas par le produit jugé : un mutant qui deplacerait sa propre borne
    # continuerait d'etre d'accord avec lui-meme et survivrait.
    attendu_lignes = attendu_pour(donnee, 3)
    attendu_colonnes = attendu_pour(donnee, 2)
    check("%s : le fichier ne sort jamais un <rowCount> inexistant" % (nom,),
          a["rowCount"] not in (None, ""), a)
    check("%s : ni un nombre negatif" % (nom,),
          str(a["rowCount"]).lstrip("-").isdigit() and int(a["rowCount"]) >= 0,
          a["rowCount"])
    check("%s : le compte ecrit est celui que l'editeur sait porter" % (nom,),
          str(a["rowCount"]).isdigit() and int(a["rowCount"]) == attendu_lignes,
          (a["rowCount"], attendu_lignes))
    check("%s : et le nombre d'elements <row> est d'accord avec lui" % (nom,),
          a["row"] == int(attendu_lignes), (a["row"], attendu_lignes))
    check("%s : les colonnes non plus ne divergent pas" % (nom,),
          a["column"] == int(attendu_colonnes)
          and str(a["columnCount"]).isdigit()
          and int(a["columnCount"]) == attendu_colonnes,
          (a["column"], a["columnCount"], attendu_colonnes))
    check("%s : le fichier reste de la taille d'un exercice" % (nom,),
          a["octets"] < 60000, a["octets"])
    if os.path.exists(p):
        v_r.load_new_ui_file(p)
        check("%s : rouvert, le modele compte les elements que le fichier porte"
              % (nom,),
              taille(v_r, "rows") == a["row"]
              and taille(v_r, "columns") == a["column"],
              (taille(v_r, "rows"), a["row"], taille(v_r, "columns"),
               a["column"]))
check("le mur ne se declenche que sur une demande explicite : le nombre "
      "d'elements du tableau lu n'a pas bouge", accord(AVANT)["row"] == 3,
      accord(AVANT)["row"])
# Un cote invalide ne doit pas empecher l'autre de passer au fichier : la porte
# se traite par champ, pas par tableau.
top_m, v_m = fenetre("tailles-mur-melange")
v_m.load_new_ui_file(TROIS)
v_m._select(0)
v_m.widgets_data[0][1]["rows"] = "abc"
v_m.widgets_data[0][1]["columns"] = 5
MELANGE = CHEMIN("mur_melange.ui")
ecrire(v_m, MELANGE, "5b : un cote texte, un cote nombre")
a = accord(MELANGE)
check("le cote qui n'est pas une taille ne sort pas : le fichier garde ses "
      "trois lignes", a["rowCount"] == "3" and a["row"] == 3,
      (a["rowCount"], a["row"]))
check("et le cote valide, lui, atteint bien le fichier",
      a["columnCount"] == "5" and a["column"] == 5,
      (a["columnCount"], a["column"]))
check("les deux cotes restent d'accord chacun chez soi",
      a["row"] == nombre(a["rowCount"])
      and a["column"] == nombre(a["columnCount"]), a)

# ————— 6. un tableau deja grand ne se fait pas detruire —————
print("\n=== 6. le plafond monte avec ce que le fichier porte deja ===")
top6, v6 = fenetre("tailles-grand")
v6.load_new_ui_file(GROS)
v6._select(0)
check("1200 lignes lues : le modele les tient toutes",
      taille(v6, "rows") == 1200, taille(v6, "rows"))
r = saisis(top6, v6, "rows", "1199")
check("les reduire a 1199 est accepte", r["modele"] == 1199, r["modele"])
r = saisis(top6, v6, "rows", "1300")
check("mais pas les faire grossir au-dessus de ce qu'ils etaient",
      r["modele"] == 1199, r["modele"])
check("et le refus est explique", "ligne XML" in dit(r), dit(r)[:60])
check("en citant le plafond qui s'applique a CE fichier, pas un autre",
      "1200" in dit(r), dit(r)[-60:])
r = saisis(top6, v6, "rows", "1200")
check("reduire ne resserre pas la porte : revenir a 1200 passe",
      r["modele"] == 1200, r["modele"])
r = saisis(top6, v6, "rows", "1301")
check("mais le plafond du fichier lu reste la", r["modele"] == 1200,
      r["modele"])
saisis(top6, v6, "rows", "1199")
GROS_SORTIE = CHEMIN("grand_sortie.ui")
ecrire(v6, GROS_SORTIE, "6 : le grand tableau reduit")
a = accord(GROS_SORTIE)
check("le fichier sortant porte bien 1199 elements, pas 1000",
      a["row"] == 1199 and a["rowCount"] == "1199", (a["rowCount"], a["row"]))
check("et le premier titre est toujours la",
      a["titres row"][:1] == ["Eleve 1"],
      a["titres row"][:2])
check("les titres qui restent sont dans l'ordre, jusqu'au 1199e",
      a["titres row"][-1:] == ["Eleve 1199"] and len(a["titres row"]) == 1199,
      a["titres row"][-2:])
top7, v7 = fenetre("tailles-grand-sans-geste")
v7.load_new_ui_file(GROS)
GROS_INTEGRE = CHEMIN("grand_touche.ui")
ecrire(v7, GROS_INTEGRE, "6 : le grand tableau qu'on ne touche pas")
check("un grand tableau qu'on ne touche pas ressort tel quel",
      accord(GROS_INTEGRE)["row"] == 1200, accord(GROS_INTEGRE)["row"])

# ————— 7. le texte de l'eleve qui n'est pas un nombre —————
print("\n=== 7. ce qui n'est pas un nombre ne passe pas la porte ===")
top8, v8 = fenetre("tailles-texte")
v8.load_new_ui_file(TROIS)
v8._select(0)
# La porte tient le texte BRUT : un « abc » ne doit pas s'evanouir dans le
# ValueError du cast, il doit se refuser et s'expliquer comme le reste.
for texte in ("", "   ", "abc", "3.5", "1e3", "deux", "- 1"):
    r = saisis(top8, v8, "rows", texte)
    check("%r ne change pas la taille du modele" % (texte,),
          r["modele"] == 3, r["modele"])
    check("%r est refuse visiblement" % (texte,), r["couleur"] == "#5a1a1a",
          (r["couleur"], dit(r)[:50]))
    check("%r s'explique plutot que de disparaitre" % (texte,), dit(r) != "",
          dit(r)[:60])
r = saisis(top8, v8, "rows", "abc")
check("le mot explique un texte : il parle de chiffres", "chiffres" in dit(r),
      dit(r)[:70])
r = saisis(top8, v8, "rows", "")
check("le mot explique un champ vide : il dit qu'il est vide", "vide" in dit(r),
      dit(r)[:70])
for texte, attendu in (("+5", 5), (" 4 ", 4), ("007", 7)):
    r = saisis(top8, v8, "rows", texte)
    check("%r vaut %d et passe" % (texte, attendu), r["modele"] == attendu,
          r["modele"])
    check("    %r laisse le champ calme" % (texte,),
          r["couleur"] == "#3c3c3c" and dit(r) == "",
          (r["couleur"], dit(r)[:40]))
saisis(top8, v8, "rows", "3")
check("retour a trois lignes", taille(v8, "rows") == 3, taille(v8, "rows"))

# ————— 8. un refus ne coute pas un coup d'Annuler —————
print("\n=== 8. un refus ne coute pas un coup d'Annuler ===")
top9, v9 = fenetre("tailles-journal")
v9.load_new_ui_file(TROIS)
v9._select(0)
piles = len(getattr(v9, "_undo_stack", []) or [])
saisis(top9, v9, "rows", "-1")
saisis(top9, v9, "rows", "99999")
check("rien au journal pour deux refus",
      len(getattr(v9, "_undo_stack", []) or []) == piles,
      (piles, len(getattr(v9, "_undo_stack", []) or [])))
check("et le modele n'a pas bouge", taille(v9, "rows") == 3, taille(v9, "rows"))
saisis(top9, v9, "rows", "6")
check("une taille acceptee coute exactement un pas",
      len(getattr(v9, "_undo_stack", []) or []) == piles + 1,
      (piles, len(getattr(v9, "_undo_stack", []) or [])))
v9.undo()
check("Annuler rend la taille d'avant", taille(v9, "rows") == 3,
      taille(v9, "rows"))
saisis(top9, v9, "rows", "-1")
haussier = len(getattr(v9, "_redo_stack", []) or [])
saisis(top9, v9, "rows", "abc")
check("un refus ne deplace ni l'Annuler ni le Retablir",
      len(getattr(v9, "_undo_stack", []) or []) == piles
      and len(getattr(v9, "_redo_stack", []) or []) == haussier,
      (piles, len(getattr(v9, "_undo_stack", []) or []), haussier,
       len(getattr(v9, "_redo_stack", []) or [])))

# ————— 9. le panneau ne garde pas de champ menteur —————
print("\n=== 9. le panneau lache les champs de taille ===")
top10, v10 = fenetre("tailles-panneau")
v10.load_new_ui_file(TROIS)
v10._select(0)
saisis(top10, v10, "rows", "-1")
champ_rows = (getattr(v10, "_taille_champs", None) or {}).get("rows")
teinte = None
if champ_rows is not None:
    try:
        teinte = champ_rows.cget("bg")
    except tk.TclError:
        teinte = None
check("le tableau a bien un champ colorie", teinte == "#5a1a1a", teinte)
v10._add_widget("QPushButton")
v10._select(len(v10.widgets_data) - 1)
check("un bouton n'a pas de champs de taille",
      "rows" not in (getattr(v10, "_prop_vars", None) or {})
      and "columns" not in (getattr(v10, "_prop_vars", None) or {}),
      sorted(getattr(v10, "_prop_vars", None) or {}))
check("un autre widget : plus aucun champ de taille ne traine",
      (getattr(v10, "_taille_champs", None) or {}) == {},
      sorted(getattr(v10, "_taille_champs", None) or {}))
check("et plus d'explication sous la main",
      getattr(v10, "_taille_hint", None) is None,
      getattr(v10, "_taille_hint", None))
v10._deselect()
try:
    v10._dit_taille("rows", "encore une")
    casse = None
except tk.TclError as e:
    casse = str(e)[:60]
except Exception as e:
    casse = "%s: %s" % (type(e).__name__, str(e)[:60])
check("ecrire une explication dans un panneau vide ne leve pas", casse is None,
      casse)
v10._new()
check("Nouveau n'herite pas d'un champ de taille du document d'avant",
      getattr(v10, "_taille_champs", None) == {}
      and getattr(v10, "_taille_hint", None) is None,
      (sorted(getattr(v10, "_taille_champs", None) or {}),
       getattr(v10, "_taille_hint", None)))

# ————— 10. un tableau ajoute de zero —————
print("\n=== 10. un tableau pose par l'eleve part a trois lignes ===")
top11, v11 = fenetre("tailles-ajoute")
v11._new()
v11._add_widget("QTableWidget")
check("par defaut : trois lignes et trois colonnes",
      (taille(v11, "rows"), taille(v11, "columns")) == (3, 3),
      (taille(v11, "rows"), taille(v11, "columns")))
AJOUTE = CHEMIN("ajoute.ui")
ecrire(v11, AJOUTE, "10 : le tableau pose par l'eleve")
a = accord(AJOUTE)
check("le fichier d'un tableau ajoute est en accord avec lui-meme",
      a["rowCount"] == "3" and a["row"] == 3 and a["columnCount"] == "3"
      and a["column"] == 3, a)
v11._select(0)
saisis(top11, v11, "rows", str(PLAFOND + 500))
check("et son plafond n'est pas monte faute de fichier",
      taille(v11, "rows") == 3, taille(v11, "rows"))
saisis(top11, v11, "rows", str(PLAFOND))
ecrire(v11, AJOUTE, "10 : mille lignes d'un tableau neuf")
a = accord(AJOUTE)
check("mille lignes demandees d'un tableau neuf : mille elements, pas plus",
      a["row"] == PLAFOND and a["rowCount"] == str(PLAFOND),
      (a["rowCount"], a["row"], a["octets"]))
check("et le fichier tient dans une taille raisonnable", a["octets"] < 40000,
      a["octets"])
mes = mesure_qt(AJOUTE)
check("Qt construit le mille lignes reclame", mes.get("rowCount") == PLAFOND,
      {k: mes.get(k) for k in ("rowCount", "columnCount", "erreur")})
# Le chemin d'un document NEUF n'est pas celui d'un fichier lu : il a son propre
# ecrivain, et il doit porter les MEMES bornes.
v11.widgets_data[0][1]["rows"] = -5
v11.widgets_data[0][1]["columns"] = 4000
HOSTILE_FRAIS = CHEMIN("ajoute_hostile.ui")
ecrire(v11, HOSTILE_FRAIS, "10 : un modele neuf hors bornes")
a = accord(HOSTILE_FRAIS)
check("un tableau neuf dont le modele porte un compte absurde ne l'ecrit pas",
      a["rowCount"] == "0" and a["row"] == 0, (a["rowCount"], a["row"]))
check("et le cote demesure est borne au plafond, pas ecrit tel quel",
      nombre(a["columnCount"]) == PLAFOND and a["column"] == PLAFOND,
      (a["columnCount"], a["column"]))

# ————— 11. les bornes sont une seule definition —————
print("\n=== 11. une seule idee, trois portes ===")
arbre = ast.parse(source)
classe = next((n for n in arbre.body if isinstance(n, ast.ClassDef)), None)
meth = ({n.name: n for n in classe.body if isinstance(n, ast.FunctionDef)}
        if classe is not None else {})
LIGNES = source.splitlines()


def corps(nom_methode):
    """Le TEXTE de la methode, pas son arbre : les punaises lisent ce que
    l'eleve lirait, et un docstring ne peut pas se faire passer pour une
    regle ecrite dans le code."""
    noeud = meth.get(nom_methode)
    if noeud is None:
        return ""
    return "\n".join(LIGNES[noeud.lineno - 1: noeud.end_lineno])


def dans(nom_methode, texte):
    return texte in corps(nom_methode)


def litteraux_negatifs(nom_methode):
    """Les nombres ecrits en negatif dans le CODE (un docstring n'en est pas
    un : c'est precisement ainsi que le defaut etait nomme)."""
    noeud = meth.get(nom_methode)
    if noeud is None:
        return []
    trouves = []
    for n in ast.walk(noeud):
        if (isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub)
                and isinstance(n.operand, ast.Constant)
                and isinstance(n.operand.value, (int, float))):
            trouves.append(ast.unparse(n))
    return trouves


check("la methode _taille_admissible est la", "_taille_admissible" in meth,
      sorted(meth)[:6])
check("_sync_table appelle la borne", dans("_sync_table", "_taille_admissible"),
      corps("_sync_table")[:80])
check("_build_fresh_ui appelle la meme borne",
      dans("_build_fresh_ui", "_taille_admissible"), None)
check("_adjust_count refuse les comptes qui ne sont pas des tailles",
      dans("_adjust_count", "if want < 0") and dans("_adjust_count",
                                                    "if want is None"), None)
check("et _apply tient la porte pour les deux champs",
      dans("_apply", '("rows", "columns")') and dans("_apply", "_accept_taille"),
      None)
check("la porte tient le texte brut, avant la conversion",
      dans("_apply", "_accept_taille(key, saisi"), None)
porte = corps("_apply").find("_accept_taille")
journal = corps("_apply").find("_record")
check("la porte vient AVANT que quoi que ce soit ne soit journalise",
      0 <= porte < journal, (porte, journal))
check("_clear_props rend les champs et l'explication",
      dans("_clear_props", "_taille_champs") and dans("_clear_props",
                                                     "_taille_hint"), None)
check("le plafond n'est ecrit qu'une fois dans le module",
      source.count("TAILLE_MAX_TABLE = ") == 1,
      source.count("TAILLE_MAX_TABLE = "))
check("et la borne basse n'est pas recopiee a la main dans _sync_table",
      corps("_sync_table").count("max(0,") == 0,
      corps("_sync_table").count("max(0,"))
check("le plafond qui s'applique est demande a une seule methode",
      source.count("def _taille_deja") == 1
      and dans("_accept_taille", "_taille_deja"), None)
check("aucune des trois portes n'ecrit de nombre negatif",
      not (litteraux_negatifs("_taille_admissible")
           + litteraux_negatifs("_accept_taille")
           + litteraux_negatifs("_adjust_count")
           + litteraux_negatifs("_sync_table")),
      [litteraux_negatifs(n) for n in ("_taille_admissible", "_accept_taille",
                                       "_adjust_count", "_sync_table")])
check("aucun QMessageBox dans l'editeur visuel", "QMessageBox" not in source)
check("la borne brute ne leve jamais sur un texte absurde",
      UiViewerPlugin._taille_brute("abc") == 0
      and UiViewerPlugin._taille_brute(None) == 0
      and UiViewerPlugin._taille_brute(-5) == 0
      and UiViewerPlugin._taille_brute("7") == 7, None)
check("et _taille_admissible rend None quand ce n'est pas un nombre",
      UiViewerPlugin._taille_admissible("abc", 0) is None
      and UiViewerPlugin._taille_admissible(None, 0) is None, None)
check("le plafond suit ce que le fichier porte deja : un grand tableau peut "
      "garder sa taille sans la depasser",
      UiViewerPlugin._taille_admissible(1500, 1200) == 1200
      and UiViewerPlugin._taille_admissible(1500, 3) == PLAFOND
      and UiViewerPlugin._taille_admissible(1200, 1200) == 1200
      and UiViewerPlugin._taille_admissible(-2, 1200) is None,
      [UiViewerPlugin._taille_admissible(1500, 1200),
       UiViewerPlugin._taille_admissible(1500, 3),
       UiViewerPlugin._taille_admissible(-2, 1200)])
check("un compte negatif n'est pas une taille : il ne devient pas zero lignes",
      UiViewerPlugin._taille_admissible(-1, 3) is None
      and UiViewerPlugin._taille_admissible(-7, 3) is None,
      UiViewerPlugin._taille_admissible(-1, 3))
check("et l'ecriture traite les deux cotes separement",
      dans("_sync_table", "if ncols is not None")
      and dans("_sync_table", "if nrows is not None"), None)
check("et ce que le tableau porte deja regarde le fichier lu, pas la saisie",
      UiViewerPlugin._taille_deja("rows", {"rows": 500,
                                          "_src": {"rows": 1200}}) == 1200
      and UiViewerPlugin._taille_deja("rows", {"rows": 900}) == 900,
      UiViewerPlugin._taille_deja("rows", {"rows": 500,
                                           "_src": {"rows": 1200}}))
check("le dessin du tableau est borne par une regle, pas par le nombre",
      dans("_make_table", "APERCU_MAX_LIGNES")
      and dans("_make_table", "APERCU_MAX_COLONNES"), None)
check("et le cap de dessin est ecrit une seule fois",
      source.count("APERCU_MAX_LIGNES = ") == 1
      and source.count("APERCU_MAX_COLONNES = ") == 1,
      (source.count("APERCU_MAX_LIGNES = "),
       source.count("APERCU_MAX_COLONNES = ")))
check("l'apercu passe par la meme lecture tolérante que le reste",
      dans("_make_table", "_taille_brute"), None)

# ————— 12. et le reste du viewer n'a pas bouge —————
print("\n=== 12. rien d'autre n'est touche ===")
top12, v12 = fenetre("tailles-voisins")
v12.load_new_ui_file(TROIS)
v12._select(0)
AVANT_TEXTE = dict(v12.widgets_data[0][1])
saisis(top12, v12, "rows", "4")
check("changer la taille ne change pas le nom du widget",
      v12.widgets_data[0][1]["name"] == AVANT_TEXTE["name"],
      v12.widgets_data[0][1]["name"])
check("ni ce que l'eleve avait saisi ailleurs",
      v12.widgets_data[0][1]["geometry"] == AVANT_TEXTE["geometry"],
      v12.widgets_data[0][1]["geometry"])
VOISIN = CHEMIN("voisin.ui")
ecrire(v12, VOISIN, "12 : le voisin tape")
a = accord(VOISIN)
check("quatre lignes ecrites, quatre elements", a["row"] == 4 and
      a["rowCount"] == "4", a)
check("les trois titres de depart ont survecu a la croissance",
      a["titres row"][:3] == ["Eleve 1", "Eleve 2", "Eleve 3"], a["titres row"])
check("et la quatrieme ligne est ajoutee, pas inseree devant les autres",
      a["titres row"][:3] == ["Eleve 1", "Eleve 2", "Eleve 3"]
      and len(a["titres row"]) == 4, a["titres row"])
mes = mesure_qt(VOISIN)
check("Qt voit les quatre lignes et leurs titres",
      mes.get("rowCount") == 4 and mes.get("titres", [])[:3] ==
      ["Eleve 1", "Eleve 2", "Eleve 3"], mes)
check("le texte d'un bouton voisin n'a pas bouge",
      v12.widgets_data[0][1].get("text", AVANT_TEXTE.get("text"))
      == AVANT_TEXTE.get("text"), None)

# ————— 13. l'apercu ne suit jamais le nombre reclame —————
print("\n=== 13. le dessin d'un tableau reste un dessin ===")
# Ce bord-la etait le plus mechant du defaut : borner le fichier ne sert a rien
# si son ouverture dessine une case Tk par cellule. Mille lignes sur mille
# colonnes faisaient un million de Labels et la fenetre ne revenait plus — la
# suite elle-meme en est tombee victime en relisant son propre fichier (mesure,
# item 8). Le cap de dessin est une regle distincte du plafond d'ecriture.
top13, v13 = fenetre("tailles-apercu")


def dessin(n_lignes, n_colonnes):
    """Le nombre de cases Tk que l'apercu fabrique pour cette taille."""
    cadre = tk.Frame(racine)
    tbl = v13._make_table(cadre, n_lignes, n_colonnes, ("TkDefaultFont", 8))
    n = len(tbl.winfo_children())
    tbl.destroy()
    cadre.destroy()
    return n


check("trois sur trois se dessine entierement", dessin(3, 3) == 16, dessin(3, 3))
check("le cap lui-meme (8 sur 6) se dessine entierement",
      dessin(8, 6) == 63, dessin(8, 6))
check("une rangee et une colonne de plus s'annoncent au lieu de se dessiner",
      dessin(9, 7) == 80, dessin(9, 7))
carre = dessin(PLAFOND, PLAFOND)
check("mille sur mille ne dessine pas un million de cases", carre <= 120, carre)
check("et le compte de cases est le MEME qu'a neuf sur sept",
      carre == dessin(9, 7), (carre, dessin(9, 7)))
check("un tableau sans ligne se dessine quand meme, sans exception",
      dessin(0, 0) == 4, dessin(0, 0))
check("un texte a la place du nombre ne fait pas tomber l'apercu",
      dessin("abc", None) == 4, dessin("abc", None))
check("mille deux cents lignes sur deux colonnes restent bornees",
      dessin(1200, 2) == 30, dessin(1200, 2))
CARRE = CHEMIN("mur_%d.ui" % PLAFOND)
debut = time.time()
top14, v14 = fenetre("tailles-carre-ouvert")
try:
    v14.load_new_ui_file(CARRE)
    leve = None
except Exception as e:
    leve = "%s: %s" % (type(e).__name__, str(e)[:60])
duree = time.time() - debut
check("rouvrir le mille par mille se termine", duree < 25 and leve is None,
      leve or "%.1f s" % duree)
check("et le modele a garde les mille lignes reclamees",
      taille(v14, "rows") == PLAFOND and taille(v14, "columns") == PLAFOND,
      (taille(v14, "rows"), taille(v14, "columns")))
a = accord(CARRE)
check("le cap de dessin ne change rien a ce que le fichier porte",
      a["row"] == PLAFOND and a["column"] == PLAFOND, (a["row"], a["column"]))

check("aucun controle de cette suite n'est ecrit dans l'autre sens",
      not a_l_envers, a_l_envers)

EN_MARCHE[0] = False
for top in fenetres:
    try:
        top.destroy()
    except tk.TclError:
        pass
racine.destroy()

print("\n%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(0 if bilan[1] == 0 else 1)
