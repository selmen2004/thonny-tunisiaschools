r"""Item 5 : ce que l'eleve efface doit disparaitre du fichier .ui.

Le panneau accepte une chaine vide — le champ se vide, le modele garde `""`, le
canevas affiche vide. Les ecrivains, eux, testaient `if val` : une valeur vide
se lisait comme « rien a ecrire ». L'ancien texte restait donc dans le fichier,
la reouverture le rendait, et `loadUi` le repeignait : l'eleve enregistrait une
fenetre qu'il ne voyait plus a l'ecran, et son programme affichait encore
« Nom : » sur une etiquette qu'il avait vidée.

Le garde-fou a corriger est double, et la correction ne doit rien casser :

  • une valeur VIDE est une demande — elle doit atteindre le fichier ;

  • une clef ABSENTE du modele n'est pas une demande : la classe du widget n'a pas
    ce champ (un QPushButton n'a pas de « title »), ou le champ etait deja vide a
    l'ouverture et n'a pas ete touche. Ecrire la moindree aurait rempli le
    fichier d'eleve de proprietes vides.

  • un document qui n'existait pas avant (`_build_fresh_ui`) n'a rien a corriger :
    la propriete absente vaut deja la chaine vide pour Qt. Ce filtre-la reste,
    et la suite le Prouve plutot que de le changer.
"""
import ast
import os
import shutil
import sys
import types
from xml.etree import ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
PLUGIN = r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
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

D = os.path.join(HERE, "_sortie", "effacement")
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)


def CHEMIN(nom):
    return os.path.join(D, nom)


FORMULAIRE_UI = r'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>FenetreNotes</class>
 <widget class="QDialog" name="FenetreNotes">
  <property name="geometry"><rect><x>0</x><y>0</y><width>360</width><height>320</height></rect></property>
  <property name="windowTitle"><string>Saisie des notes</string></property>
  <layout class="QVBoxLayout" name="colonne">
   <item>
    <widget class="QLabel" name="etiquette">
     <property name="text"><string>Nom :</string></property>
    </widget>
   </item>
   <item>
    <widget class="QLineEdit" name="saisie">
     <property name="placeholderText"><string>Nom</string></property>
     <property name="styleSheet"><string notr="true">color: rgb(0, 0, 255);</string></property>
    </widget>
   </item>
   <item>
    <widget class="QPushButton" name="ok">
     <property name="text"><string>Valider</string></property>
    </widget>
   </item>
   <item>
    <widget class="QCheckBox" name="case">
     <property name="text"><string>Accepter</string></property>
     <property name="checked"><bool>true</bool></property>
    </widget>
   </item>
   <item>
    <widget class="QGroupBox" name="cadre">
     <property name="title"><string>Notes</string></property>
    </widget>
   </item>
   <item>
    <widget class="QLabel" name="vide">
     <property name="text"><string /></property>
    </widget>
   </item>
   <item>
    <widget class="QLabel" name="nu">
    </widget>
   </item>
  </layout>
 </widget>
 <resources/>
</ui>
'''
# les objets du fichier, dans l'ordre ou l'eleve les voit
NOMS_FICHIER = ["etiquette", "saisie", "ok", "case", "cadre", "vide", "nu"]
# ce que le fichier portait avant toute ecriture
AVAIENT = {"etiquette": ("text", "Nom :"),
           "saisie": ("placeholderText", "Nom"),
           "ok": ("text", "Valider"),
           "case": ("text", "Accepter"),
           "cadre": ("title", "Notes")}


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


def vue_sur(nom):
    """Une copie fraiche du gabarit, dans une vraie vue : le seul etat ou l'on
    peut vider un champ comme l'eleve (panneau, journal, disque)."""
    chemin = CHEMIN(nom + ".ui")
    ecrit(chemin, FORMULAIRE_UI)
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


def efface(v, nom, cle):
    """Le geste du clavier : tout selectionner puis supp. Le panneau appelle
    _apply(cle, var, idx) avec une chaine vide — c'est lui qui doit l'accepter."""
    i = idx_de(v, nom)
    if i is None:
        return False
    v._apply(cle, tk.StringVar(value=""), i)
    return props_de(v, nom).get(cle, "") == ""


def saisit(v, nom, cle, valeur):
    i = idx_de(v, nom)
    if i is None:
        return False
    v._apply(cle, tk.StringVar(value=valeur), i)
    return props_de(v, nom).get(cle) == valeur


def element(chemin, nom):
    for w in ET.parse(chemin).iter("widget"):
        if w.get("name") == nom:
            return w
    return None


def porte(chemin, nom, cle):
    el = element(chemin, nom)
    return el is not None and any(p.get("name") == cle
                                  for p in el.findall("property"))


def valeur(chemin, nom, cle):
    """Le texte de la propriete, ou None si le fichier ne la porte pas."""
    el = element(chemin, nom)
    if el is None:
        return None
    for p in el.findall("property"):
        if p.get("name") == cle:
            s = p.find("string")
            return (s.text or "") if s is not None else None
    return None


def clefs(chemin, nom):
    el = element(chemin, nom)
    return [p.get("name") for p in el.findall("property")] \
        if el is not None else []


def compte_proprietes(chemin, nom, cle):
    el = element(chemin, nom)
    if el is None:
        return 0
    return len([p for p in el.findall("property") if p.get("name") == cle])


def compte(chemin, tag):
    return len(list(ET.parse(chemin).iter(tag)))


def affiche(v, nom):
    """Tout ce que le canevas montre de cet objet : sa legende (le nom) puis les
    textes des widgets Tk qui le composent, recursivement."""
    i = idx_de(v, nom)
    acc = []

    def collecte(el):
        try:
            if isinstance(el, tk.Label):
                acc.append(el.cget("text"))
            elif isinstance(el, tk.Entry):
                acc.append(el.get())
            elif isinstance(el, tk.Text):
                acc.append(el.get("1.0", tk.END).strip())
        except tk.TclError:
            return
        for c in el.winfo_children():
            collecte(c)

    if i is None:
        return acc
    for child in v.ui_frame.winfo_children():
        if getattr(child, "_widget_idx", None) == i:
            collecte(child)
    return acc


APP = None
CHARGEES = []


def charge(chemin):
    """Un loadUi hors ecran : ce que le programme de l'eleve montrerait.

    Deux pieges a connaitre, tous deux mortels sans trace visible :

      • QApplication doit rester attache a une variable. Construit dans une
        expression sans nom, il est rendu aussitot, et loadUi travaille alors
        sur une application detruite (0xC0000409 sur Windows, le process
        s'arrete sans aucun message).

      • la fenetre chargee aussi : rendue comme simple temporary, son objet
        C/C++ meurt avant la lecture du controle, et PyQt5 repond
        « RuntimeError: wrapped C/C++ object ... has been deleted ».
    """
    global APP
    from PyQt5 import QtWidgets, uic                   # noqa: E402
    if APP is None:
        APP = QtWidgets.QApplication([])
    w = uic.loadUi(chemin)
    CHARGEES.append(w)
    return w


# ── 1. le geste : effacer un texte ───────────────────────────

print("\n=== 1. effacer un texte ===")
v, F1 = vue_sur("geste")
check("le fichier s'ouvre avec ses sept objets", noms_modele(v) == NOMS_FICHIER,
      noms_modele(v))
for nom, (cle, attendu) in AVAIENT.items():
    check("%s porte %r au fichier" % (nom, attendu),
          valeur(F1, nom, cle) == attendu, valeur(F1, nom, cle))
check("le modele a bien lu le texte de l'etiquette",
      props_de(v, "etiquette").get("text") == "Nom :",
      props_de(v, "etiquette"))
check("le canevas le montre", "Nom :" in affiche(v, "etiquette"),
      affiche(v, "etiquette"))
ordre_avant = clefs(F1, "etiquette")
check("le champ vide est accepte par le panneau", efface(v, "etiquette", "text"))
check("le modele garde la chaine vide", props_de(v, "etiquette")["text"] == "")
check("le canevas ne montre plus l'ancien texte",
      "Nom :" not in affiche(v, "etiquette"), affiche(v, "etiquette"))
check("effacer est un travail non enregistre", v._travail_non_enregistre())
v._write_ui_file(F1)
check("le fichier rend le texte efface", valeur(F1, "etiquette", "text") == "",
      repr(valeur(F1, "etiquette", "text")))
check("la propriete reste presente, seulement videe",
      porte(F1, "etiquette", "text"))
check("elle n'est pas doublee", compte_proprietes(F1, "etiquette", "text") == 1,
      clefs(F1, "etiquette"))
check("elle n'a pas bouge parmi les voisines",
      clefs(F1, "etiquette") == ordre_avant, clefs(F1, "etiquette"))
check("le reste du fichier est intact",
      [valeur(F1, "saisie", "placeholderText"), valeur(F1, "saisie", "styleSheet"),
       valeur(F1, "ok", "text"), valeur(F1, "case", "text"),
       valeur(F1, "cadre", "title")]
      == ["Nom", "color: rgb(0, 0, 255);", "Valider", "Accepter", "Notes"],
      [valeur(F1, "saisie", "placeholderText"), valeur(F1, "ok", "text")])
ref1 = octets(F1)
v._write_ui_file(F1)
check("enregistrer deux fois de suite rend les memes octets", octets(F1) == ref1)
check("et aucun effacement ne demande l'avis de l'eleve",
      [d for d in dialogues if d[0] == "yesno"] == [], dialogues)

# le geste complet, jusqu'au bouton Enregistrer de la barre d'outils
v1b, F1b = vue_sur("enregistrement")
efface(v1b, "etiquette", "text")
efface(v1b, "saisie", "placeholderText")
dialogues.clear()
v1b._save()
check("enregistrer un texte efface ne se refuse pas",
      [d[0] for d in dialogues] == ["info"], dialogues)
check("le fichier enregistre porte les deux effacements",
      valeur(F1b, "etiquette", "text") == "" and
      valeur(F1b, "saisie", "placeholderText") == "",
      [valeur(F1b, "etiquette", "text"), valeur(F1b, "saisie", "placeholderText")])

# ── 2. les quatre champs de la meme famille ──────────────────

print("\n=== 2. les quatre champs ===")
v2, F2 = vue_sur("quatre")
check("le placeholder se vide par le panneau", efface(v2, "saisie", "placeholderText"))
check("la feuille de style se vide dans le modele",
      efface(v2, "saisie", "styleSheet"))
check("le titre du groupe se vide dans le modele", efface(v2, "cadre", "title"))
check("le texte d'une case a cocher se vide aussi", efface(v2, "case", "text"))
v2._write_ui_file(F2)
for nom, cle in (("saisie", "placeholderText"), ("case", "text"),
                 ("cadre", "title")):
    check("%s : %s est vide au fichier" % (nom, cle),
          valeur(F2, nom, cle) == "", repr(valeur(F2, nom, cle)))
check("la feuille de style effacee est vide au fichier",
      valeur(F2, "saisie", "styleSheet") == "", repr(valeur(F2, "saisie", "styleSheet")))
check("et non supprimee de l'element", porte(F2, "saisie", "styleSheet"))
check("le bouton que l'eleve n'a pas touche a garde son texte",
      valeur(F2, "ok", "text") == "Valider", valeur(F2, "ok", "text"))
check("la case reste cochee : booleen n'est pas chaine",
      ET.parse(F2).findtext(".//widget[@name='case']/property[@name='checked']/bool")
      == "true",
      ET.parse(F2).findtext(".//widget[@name='case']/property[@name='checked']/bool"))
# le titre n'a pas de champ dans le panneau : la route du modele est donc la
# seule qui existe aujourd'hui, et la suite doit le dire plutot que le cacher.
v2._select(idx_de(v2, "cadre"))
racine.update()
check("le panneau ne propose aucun champ pour un titre de groupe",
      "title" not in v2._prop_vars, sorted(v2._prop_vars))
v2._select(idx_de(v2, "etiquette"))
racine.update()
check("il en propose un pour le texte", "text" in v2._prop_vars,
      sorted(v2._prop_vars))
v2._select(idx_de(v2, "saisie"))
racine.update()
check("et un pour le placeholder", "placeholderText" in v2._prop_vars,
      sorted(v2._prop_vars))

# ── 3. ce que Qt rend a l'ecran ──────────────────────────────

print("\n=== 3. loadUi du fichier efface ===")
vq, _c = vue_sur("qt")
for nom, cle in (("etiquette", "text"), ("saisie", "placeholderText"),
                 ("saisie", "styleSheet"), ("cadre", "title"),
                 ("case", "text")):
    efface(vq, nom, cle)
QQ = CHEMIN("qt_apres.ui")
vq._write_ui_file(QQ)
w = charge(QQ)
check("loadUi ne repeint pas le texte efface", w.etiquette.text() == "",
      repr(w.etiquette.text()))
check("le placeholder efface ne revient pas", w.saisie.placeholderText() == "",
      repr(w.saisie.placeholderText()))
check("le titre efface non plus", w.cadre.title() == "", repr(w.cadre.title()))
check("la couleur effacee n'est plus appliquee", w.saisie.styleSheet() == "",
      repr(w.saisie.styleSheet()))
check("le texte de la case est vide mais la case reste cochee",
      w.case.text() == "" and w.case.isChecked(), (w.case.text(),
                                                   w.case.isChecked()))
check("un objet que l'eleve n'a pas touche est intact",
      w.ok.text() == "Valider", repr(w.ok.text()))
check("la fenetre a garde son titre", w.windowTitle() == "Saisie des notes",
      repr(w.windowTitle()))
check("la mise en page est toujours la sienne",
      w.layout() is not None and w.layout().count() == 7,
      w.layout().count() if w.layout() else None)
check("et les objets vides sont toujours la",
      hasattr(w, "etiquette") and hasattr(w, "cadre"))

# ── 4. reouvrir montre ce qui a ete ecrit ────────────────────

print("\n=== 4. reouverture ===")
v3, _c3 = vue_sur("reouverture")
v3.load_new_ui_file(QQ)
check("la reouverture ne ressuscite pas le texte",
      props_de(v3, "etiquette").get("text", "") == "",
      props_de(v3, "etiquette").get("text"))
check("ni le placeholder",
      props_de(v3, "saisie").get("placeholderText", "") == "")
check("ni le titre du groupe", props_de(v3, "cadre").get("title", "") == "")
check("ni la feuille de style", props_de(v3, "saisie")["styleSheet"] == "")
check("le canevas reste vide", "Nom :" not in affiche(v3, "etiquette"),
      affiche(v3, "etiquette"))
v3._select(idx_de(v3, "etiquette"))
racine.update()
check("le champ du panneau repart vide, pas avec l'ancien texte",
      v3._prop_vars["text"].get() == "", repr(v3._prop_vars["text"].get()))
v3._select(idx_de(v3, "saisie"))
racine.update()
check("le champ placeholder aussi",
      v3._prop_vars["placeholderText"].get() == "",
      repr(v3._prop_vars["placeholderText"].get()))
check("la vue qui rouvre un fichier n'a rien a demander",
      v3._travail_non_enregistre() is False)
ref3 = octets(QQ)
v3._write_ui_file(QQ)
check("enregistrer sans rien changer ne change rien", octets(QQ) == ref3)
check("la propriete vide est toujours presente apres ce sauvetage",
      porte(QQ, "etiquette", "text") and valeur(QQ, "etiquette", "text") == "")
check("aucun texte n'est apparu par accident",
      valeur(QQ, "ok", "text") == "Valider" and
      valeur(QQ, "case", "text") == "")

# ── 5. une clef absente n'est pas une demande ────────────────

print("\n=== 5. le silence d'une clef absente ===")
v4, F4 = vue_sur("silence")
v4._write_ui_file(CHEMIN("silence_ref.ui"))
REF4 = octets(CHEMIN("silence_ref.ui"))
check("un label lu du fichier ne porte pas de clef placeholderText",
      "placeholderText" not in props_de(v4, "etiquette"),
      sorted(k for k in props_de(v4, "etiquette") if not k.startswith("_")))
check("ni de clef title", "title" not in props_de(v4, "etiquette"))
check("un bouton ne porte pas de clef title", "title" not in props_de(v4, "ok"))
# quelqu'un (une autre route que le panneau) depose une chaine vide sur un champ
# que la classe n'a pas : ce n'est pas une modification, rien ne doit paraitre
props_de(v4, "etiquette")["placeholderText"] = ""
props_de(v4, "etiquette")["title"] = ""
props_de(v4, "ok")["title"] = ""
props_de(v4, "vide")["placeholderText"] = ""
v4._write_ui_file(F4)
check("aucune propriete placeholderText n'est apparue sur le label",
      not porte(F4, "etiquette", "placeholderText"), clefs(F4, "etiquette"))
check("aucune propriete title n'est apparue sur le label",
      not porte(F4, "etiquette", "title"), clefs(F4, "etiquette"))
check("aucune propriete title n'est apparue sur le bouton",
      not porte(F4, "ok", "title"), clefs(F4, "ok"))
check("aucune sur le label qui portait deja une chaine vide",
      not porte(F4, "vide", "placeholderText"), clefs(F4, "vide"))
check("le texte de l'etiquette non touchee est reste au fichier",
      valeur(F4, "etiquette", "text") == "Nom :", valeur(F4, "etiquette", "text"))
check("et le fichier n'a pas bouge d'un octet", octets(F4) == REF4,
      [clefs(F4, "etiquette"), clefs(F4, "ok")])
check("aucune feuille de style n'est inventee pour un objet sans couleur",
      not porte(F4, "etiquette", "styleSheet") and
      not porte(F4, "ok", "styleSheet"),
      [clefs(F4, "etiquette"), clefs(F4, "ok")])
check("et un objet sans aucune propriete text n'en recoit pas une",
      not porte(F4, "nu", "text"), clefs(F4, "nu"))

# une vraie chaine, elle, s'ecrit bien sur tous les champs de la famille
v4b, F4b = vue_sur("pleine")
saisit(v4b, "etiquette", "text", "Prenom :")
saisit(v4b, "saisie", "placeholderText", "Votre nom")
saisit(v4b, "cadre", "title", "Moyenne")
v4b._write_ui_file(F4b)
check("un texte saisi atteint le fichier",
      valeur(F4b, "etiquette", "text") == "Prenom :",
      valeur(F4b, "etiquette", "text"))
check("un placeholder saisi aussi",
      valeur(F4b, "saisie", "placeholderText") == "Votre nom",
      valeur(F4b, "saisie", "placeholderText"))
check("un titre saisi egalement", valeur(F4b, "cadre", "title") == "Moyenne",
      valeur(F4b, "cadre", "title"))
check("remplacer un texte existant ne laisse pas l'ancien",
      compte_proprietes(F4b, "etiquette", "text") == 1, clefs(F4b, "etiquette"))

# Le modele peut perdre la clef elle-meme (une route autre que le panneau, un
# futur import de fichier partiel). Le fichier, lui, porte encore une valeur :
# le silence du modele ne doit pas la revider — « pas de clef » n'est pas «
# clef vide », et c'est exactement la distinction que porte le garde-fou.
v4c, F4c = vue_sur("clef_perdue")
v4c._write_ui_file(CHEMIN("clef_perdue_ref.ui"))
REF4C = octets(CHEMIN("clef_perdue_ref.ui"))
props_de(v4c, "etiquette").pop("text")
check("le modele ne parle plus du texte de l'etiquette",
      "text" not in props_de(v4c, "etiquette"), sorted(
          k for k in props_de(v4c, "etiquette") if not k.startswith("_")))
v4c._write_ui_file(F4c)
check("une clef que le modele a perdue ne revide pas le fichier",
      valeur(F4c, "etiquette", "text") == "Nom :", valeur(F4c, "etiquette", "text"))
check("et le fichier reste octet pour octet celui d'un enregistrement pur",
      octets(F4c) == REF4C, clefs(F4c, "etiquette"))

# ── 6. ce qui etait deja vide au fichier ─────────────────────

print("\n=== 6. une chaine deja vide au fichier ===")
v5, F5 = vue_sur("deja_vide")
check("le fixture porte une propriete text vide",
      porte(F5, "vide", "text") and valeur(F5, "vide", "text") == "",
      [porte(F5, "vide", "text"), repr(valeur(F5, "vide", "text"))])
check("le modele la lit comme une chaine vide",
      props_de(v5, "vide").get("text", "") == "", props_de(v5, "vide").get("text"))
check("le canevas n'invente rien", "None" not in affiche(v5, "vide"),
      affiche(v5, "vide"))
v5._write_ui_file(F5)
REF5 = octets(F5)
check("enregistrer un fichier a chaine vide la laisse vide",
      porte(F5, "vide", "text") and valeur(F5, "vide", "text") == "",
      repr(valeur(F5, "vide", "text")))
saisit(v5, "vide", "text", "Apparait")
v5._write_ui_file(F5)
check("la saisir la remplit au fichier", valeur(F5, "vide", "text") == "Apparait",
      valeur(F5, "vide", "text"))
efface(v5, "vide", "text")
v5._write_ui_file(F5)
check("la revider rend le fichier tel qu'apres la premiere ecriture",
      octets(F5) == REF5, repr(valeur(F5, "vide", "text")))
check("le texte efface n'est jamais ecrit « None » dans le fichier",
      "None" not in octets(F5).decode("utf-8"),
      [l for l in octets(F5).decode("utf-8").splitlines() if "None" in l])
check("un objet que l'eleve laisse en paix ne recoit aucune propriete text",
      not porte(F5, "nu", "text"), clefs(F5, "nu"))
saisit(v5, "nu", "text", "Une absence qui parle")
v5._write_ui_file(F5)
check("le meme objet, si l'eleve y ecrit, recoit bien la propriete",
      valeur(F5, "nu", "text") == "Une absence qui parle", valeur(F5, "nu", "text"))
efface(v5, "nu", "text")
v5._write_ui_file(F5)
check("et la rend quand il revide : le retour au vide est complet",
      valeur(F5, "nu", "text") is None and not porte(F5, "nu", "text"),
      [repr(valeur(F5, "nu", "text")), clefs(F5, "nu")])
check("le fichier redevient octet pour octet ce qu'il etait avant la saisie",
      octets(F5) == REF5, clefs(F5, "nu"))
w5 = charge(F5)
check("Qt rend la chaine vide, pas une chaine par defaut",
      w5.vide.text() == "" and w5.nu.text() == "",
      [repr(w5.vide.text()), repr(w5.nu.text())])

# ── 7. objet ajoute, objet duplique ─────────────────────────

print("\n=== 7. ajoute et duplique ===")
v6, F6 = vue_sur("ajoute")
v6._add_widget("QLabel")
nom6 = noms_modele(v6)[-1]
check("un objet ajoute part avec un texte par defaut",
      props_de(v6, nom6).get("text") == "Label", props_de(v6, nom6).get("text"))
check("le geste du clavier l'accepte vide", efface(v6, nom6, "text"))
v6._write_ui_file(F6)
check("l'objet ajoute est bien dans le fichier", nom6 in
      [w.get("name") for w in ET.parse(F6).iter("widget")])
check("vide, il ne recoit aucune propriete text",
      not porte(F6, nom6, "text"), clefs(F6, nom6))
check("et Qt le rend vide neanmoins", getattr(charge(F6), nom6).text() == "",
      repr(getattr(charge(F6), nom6).text()))
saisit(v6, nom6, "text", "Note")
v6._write_ui_file(F6)
check("rempli, sa propriete apparait", valeur(F6, nom6, "text") == "Note",
      valeur(F6, nom6, "text"))
check("range dans la mise en page du fichier", compte(F6, "item") == 8,
      compte(F6, "item"))

v7, F7 = vue_sur("duplique")
i7 = idx_de(v7, "etiquette")
efface(v7, "etiquette", "text")
v7._duplicate(i7)
copie = noms_modele(v7)[-1]
check("la copie part avec le texte vide du modele",
      props_de(v7, copie).get("text", "") == "",
      props_de(v7, copie).get("text"))
v7._write_ui_file(F7)
check("la copie n'herite d'aucun texte fantome",
      not porte(F7, copie, "text"), clefs(F7, copie))
check("l'original garde sa propriete videe",
      porte(F7, "etiquette", "text") and valeur(F7, "etiquette", "text") == "")
check("le fichier obtenu se charge avec les deux",
      hasattr(charge(F7), copie) and charge(F7).etiquette.text() == "")

# ── 8. journal : annuler un effacement ───────────────────────

print("\n=== 8. journal ===")
v8, F8 = vue_sur("journal")
v8._write_ui_file(F8)
AVANT8 = octets(F8)
i8 = idx_de(v8, "etiquette")
check("le texte est la avant l'effacement", valeur(F8, "etiquette", "text") == "Nom :")
v8._apply("text", tk.StringVar(value=""), i8)
v8._apply("text", tk.StringVar(value="Prenom"), i8)
v8._apply("text", tk.StringVar(value=""), i8)
check("les frappes successives du meme champ ne coutent qu'un pas",
      len(v8._undo_stack) == 1, len(v8._undo_stack))
v8._write_ui_file(F8)
check("le fichier est vide", valeur(F8, "etiquette", "text") == "")
v8.undo()
check("Annuler rend le texte du fichier au modele",
      props_de(v8, "etiquette").get("text") == "Nom :",
      props_de(v8, "etiquette").get("text"))
v8._write_ui_file(F8)
check("Annuler puis enregistrer rend le fichier d'origine", octets(F8) == AVANT8)
v8.redo()
check("Retablir efface de nouveau",
      props_de(v8, "etiquette").get("text", "") == "")
v8._write_ui_file(F8)
check("Retablir puis enregistrer retrouve le fichier vide",
      valeur(F8, "etiquette", "text") == "")
check("un effacement annule ne laisse rien de travers dans l'arbre source",
      "Nom :" in ET.tostring(v8._source_ui, encoding="unicode"))
check("rien n'a ete demande pendant tout cela",
      [d for d in dialogues if d[0] == "yesno"] == [], dialogues)

# ── 9. fenetre neuve : rien a corriger ───────────────────────

print("\n=== 9. document neuf ===")
v9, _c9 = vue_sur("neuf")
dialogues.clear()
reponse[0] = True
v9._new()
racine.update()
v9._add_widget("QLabel")
nom9 = noms_modele(v9)[-1]
NEUVE = CHEMIN("neuve.ui")
v9.ui_file = NEUVE
check("le champ texte se vide sur la fenetre neuve",
      efface(v9, nom9, "text"), props_de(v9, nom9).get("text"))
v9._write_ui_file(NEUVE)
check("un document neuf n'ecrit pas de texte vide",
      not porte(NEUVE, nom9, "text"), clefs(NEUVE, nom9))
check("il n'ecrit pas non plus de titre ni de placeholder vides",
      not porte(NEUVE, nom9, "title") and
      not porte(NEUVE, nom9, "placeholderText"), clefs(NEUVE, nom9))
w9 = charge(NEUVE)
check("Qt rend neanmoins la chaine vide", getattr(w9, nom9).text() == "",
      repr(getattr(w9, nom9).text()))
v9b, _c9b = vue_sur("neuve_rous")
v9b.load_new_ui_file(NEUVE)
check("la reouverture garde le champ vide",
      props_de(v9b, nom9).get("text", "") == "", props_de(v9b, nom9))
check("la vue rouverte n'a rien a demander",
      v9b._travail_non_enregistre() is False)
saisit(v9b, nom9, "text", "Bonjour")
NEUVE2 = CHEMIN("neuve2.ui")
v9b._write_ui_file(NEUVE2)
check("la premiere saisie sur un objet neuf s'ecrit",
      valeur(NEUVE2, nom9, "text") == "Bonjour", valeur(NEUVE2, nom9, "text"))
efface(v9b, nom9, "text")
v9b._write_ui_file(NEUVE2)
check("et son effacement le retire a nouveau",
      not porte(NEUVE2, nom9, "text"), clefs(NEUVE2, nom9))
check("le fichier obtenu se charge", getattr(charge(NEUVE2), nom9).text() == "")

# ── 10. ce que le code dit ───────────────────────────────────

print("\n=== 10. le code ===")
source = open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
arb = ast.parse(source)
meth = {n.name: n for n in ast.walk(arb) if isinstance(n, ast.FunctionDef)}
seg = lambda n: ast.get_source_segment(source, meth[n])                   # noqa: E731

wc = seg("_write_changed")
check("une seule boucle ecrit les champs de texte",
      wc.count("_set_string_prop(") == 1, wc.count("_set_string_prop("))
check("elle porte sur les quatre clefs de la famille",
      'for key in ("text", "placeholderText", "title", "styleSheet"):' in wc)
check("la feuille de style n'a plus son test separe",
      'props["styleSheet"] != src.get("styleSheet")' not in wc)
check("une clef absente du modele ne dit rien",
      "if val is None:" in wc and "continue" in wc)
check("une clef presente, meme vide, se compare",
      '(val or "") != (src.get(key) or "")' in wc)
check("plus aucun filtre « si la valeur » dans l'ecrivain",
      "if val and" not in wc and "if props.get(key)" not in wc)
check("la raison du filtre est ecrite a cote du code",
      "Une valeur vide est une demande" in wc)
check("l'ecrivain ne s'occupe toujours pas du nom",
      'el.set("name"' not in wc)

fresh = seg("_build_fresh_ui")
check("le document neuf garde son filtre : rien a corriger ici",
      "if props.get(key):" in fresh)
check("et la raison est ecrite", "vaut la chaine vide pour Qt" in fresh)

lecture = seg("read_props")
check("la lecture d'une chaine vide ne cree pas de clef",
      "if s is not None and s.text:" in lecture)
check("c'est pour cela que l'ecrivain distingue absence et vide",
      "if val is None:" in wc)

fusion = seg("_merge_into_source")
check("le titre de la fenetre n'est pas touche par la boucle",
      'if title and title != self._src_root.get("title"):' in fusion)
check("aucun champ du panneau n'atteint root_title",
      "root_title" not in seg("_show_properties"))
check("la feuille de style passe toujours par l'unique ecrivain de chaine",
      "styleSheet" in wc and "_set_string_prop(el, key, val)" in wc)
check("aucun QMessageBox dans l'editeur visuel", "QMessageBox" not in source)

for top in fenetres:
    top.destroy()
racine.update()

check("aucun controle de cette suite n'est ecrit dans l'autre sens",
      a_l_envers == [], a_l_envers)

print("\n%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)
