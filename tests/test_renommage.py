r"""Item 4 : le nom saisi dans le panneau doit atteindre le fichier .ui.

Le nom d'un objet n'est pas une propriete : c'est l'attribut XML `name` du
`<widget>`, et c'est lui que l'eleve ecrit dans son programme
(`windows.boutonValider.clicked.connect(...)`). Avant cette suite, `name` etait
valide par le panneau, garde par le modele, affiche par le canevas et la liste
d'objets — et perdu a l'ecriture : `_write_changed` ne patchait que des
`<property>`. Le fichier continuait de porter `ok`, la reouverture faisait
disparaitre le nom, et le code que le panneau suggerait avec le nom saisi ne
designait plus rien a l'execution.

Ecrire le nom au fichier ouvre deux risques que rien n'avait a trainer jusqu'ici :

  • les `<connections>` citent le nom. Le suivre trop tard (apres le menage des
    orphelines) couperait le cable du bouton rebaptise ; le suivre sans savoir
    qui a ete supprime ressusciterait le cable d'un disparu.

  • le fichier porte des noms que le modele ne voit pas : la fenetre elle-meme,
    chaque `<layout>`, chaque `<action>`. `setupUi()` cree un attribut par nom,
    deux objets du meme nom ne peuvent pas coexister — rebaptiser un bouton
    « colonne » ferait disparaitre sa mise en page de son propre code.
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

D = os.path.join(HERE, "_sortie", "renommage")
if os.path.isdir(D):
    shutil.rmtree(D)
os.makedirs(D)


def CHEMIN(nom):
    return os.path.join(D, nom)


FORMULAIRE_UI = r'''<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>FenetreNotes</class>
 <widget class="QDialog" name="FenetreNotes">
  <property name="geometry"><rect><x>0</x><y>0</y><width>360</width><height>300</height></rect></property>
  <property name="windowTitle"><string>Saisie des notes</string></property>
  <action name="effacerTout">
   <property name="text"><string>Tout effacer</string></property>
  </action>
  <layout class="QVBoxLayout" name="colonne">
   <item>
    <widget class="QLineEdit" name="saisie">
     <property name="placeholderText"><string>Nom</string></property>
    </widget>
   </item>
   <item>
    <widget class="QPushButton" name="ok">
     <property name="text"><string>Valider</string></property>
    </widget>
   </item>
   <item>
    <widget class="QPushButton" name="quitter">
     <property name="text"><string>Quitter</string></property>
    </widget>
   </item>
   <item>
    <widget class="QGroupBox" name="cadre">
     <property name="title"><string>Notes</string></property>
     <layout class="QHBoxLayout" name="interne">
      <item>
       <widget class="QLabel" name="info">
        <property name="text"><string>Eleve : </string></property>
       </widget>
      </item>
     </layout>
    </widget>
   </item>
  </layout>
 </widget>
 <connections>
  <connection>
   <sender>ok</sender>
   <signal>clicked()</signal>
   <receiver>FenetreNotes</receiver>
   <slot>close()</slot>
  </connection>
  <connection>
   <sender>saisie</sender>
   <signal>textChanged(QString)</signal>
   <receiver>info</receiver>
   <slot>setText(QString)</slot>
  </connection>
  <connection>
   <sender>quitter</sender>
   <signal>clicked()</signal>
   <receiver>info</receiver>
   <slot>clear()</slot>
  </connection>
 </connections>
 <resources/>
</ui>
'''
# ce que le fichier contenait avant toute ecriture, et l'ordre des objets
NOMS_FICHIER = ["FenetreNotes", "saisie", "ok", "quitter", "cadre", "info"]
NOMS_MODELE = NOMS_FICHIER[1:]
# un nom accentue : identifiant Python 3 valide, donc nom Qt valide
NOM_ACCENTUE = "élan"


def ecrit(chemin, texte):
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)


def octets(chemin):
    with open(chemin, "rb") as f:
        return f.read()


bilan = [0, 0]
a_l_envers = []


def check(*a):
    """Sens officiel : (libelle, condition, detail). Un controle ecrit dans
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
    """Une copie fraiche du gabarit, ouverte dans une vraie vue : c'est le seul
    etat ou l'on peut saisir un nom comme l'eleve (panneau, journal, disque)."""
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


def noms_modele(v):
    return [p["name"] for _c, p in v.widgets_data]


def saisit(v, ancien, nouveau):
    """Le geste exact du clavier : le panneau appelle _apply("name", var, idx)."""
    i = idx_de(v, ancien)
    if i is None:
        return False
    v._apply("name", tk.StringVar(value=nouveau), i)
    return nouveau in noms_modele(v)


def noms_dun_fichier(chemin):
    return [w.get("name") for w in ET.parse(chemin).iter("widget")]


def cites(chemin, balise):
    return [(c.findtext(balise) or "").strip()
            for c in ET.parse(chemin).iter("connection")]


def slots(chemin):
    return [(c.findtext("slot") or "").strip()
            for c in ET.parse(chemin).iter("connection")]


def signaux(chemin):
    return [(c.findtext("signal") or "").strip()
            for c in ET.parse(chemin).iter("connection")]


def nom_layouts(chemin):
    return [l.get("name") for l in ET.parse(chemin).iter("layout")]


def compte(chemin, tag):
    return len(list(ET.parse(chemin).iter(tag)))


def dessines(v):
    return [c.cget("text") for c in v.ui_frame.winfo_children()
            if getattr(c, "_is_label", False)]


# ── 1. le nom saisi atteint le fichier ──────────────────────

print("\n=== 1. le nom saisi atteint le fichier ===")
v, F1 = vue_sur("geste")
check("le fichier s'ouvre avec ses cinq objets", noms_modele(v) == NOMS_MODELE,
      noms_modele(v))
check("le panneau accepte le nom saisi", saisit(v, "ok", "boutonValider"))
check("le modele garde le nom saisi", "boutonValider" in noms_modele(v))
check("l'ancien nom a disparu du modele", "ok" not in noms_modele(v))
check("le canevas est repeint avec le nouveau nom",
      "boutonValider" in dessines(v), dessines(v))
check("renommer est un travail non enregistre", v._travail_non_enregistre())
retires = v._write_ui_file(F1)
check("le fichier porte desormais le nom saisi",
      "boutonValider" in noms_dun_fichier(F1), noms_dun_fichier(F1))
check("l'ancien nom n'est plus ecrit nulle part",
      "ok" not in noms_dun_fichier(F1), noms_dun_fichier(F1))
check("aucune connexion n'a ete retiree pour un renommage", retires == 0, retires)
check("le nom est bien un attribut du <widget>, pas une <property>",
      ET.parse(F1).find(".//widget[@name='boutonValider']") is not None)
check("la classe a suivi sans bouger",
      ET.parse(F1).find(".//widget[@name='boutonValider']").get("class")
      == "QPushButton")
check("les autres objets sont restes a leur place",
      noms_dun_fichier(F1) ==
      ["FenetreNotes", "saisie", "boutonValider", "quitter", "cadre", "info"],
      noms_dun_fichier(F1))
check("les mises en page ont garde leur nom", nom_layouts(F1) == ["colonne", "interne"],
      nom_layouts(F1))
check("la fenetre a garde le sien",
      ET.parse(F1).getroot().find("widget").get("name") == "FenetreNotes")
check("renommer un objet ne renomme pas <class>",
      ET.parse(F1).findtext("class") == "FenetreNotes")
check("le titre de la fenetre est intact",
      ET.parse(F1).findtext(".//property[@name='windowTitle']/string")
      == "Saisie des notes")
check("l'arbre source n'a pas ete touche par l'ecriture",
      'name="ok"' in ET.tostring(v._source_ui, encoding="unicode"))
_avant = octets(F1)
v._write_ui_file(F1)
check("enregistrer deux fois de suite rend les memes octets",
      octets(F1) == _avant)
check("et le renommage n'a rien demande a l'eleve",
      [d for d in dialogues if d[0] == "yesno"] == [], dialogues)

# ── 2. les connexions suivent le nom ────────────────────────

print("\n=== 2. les connexions suivent le nom ===")
check("l'emetteur rebaptise cite le nouveau nom",
      cites(F1, "sender") == ["boutonValider", "saisie", "quitter"],
      cites(F1, "sender"))
check("le destinataire de la fenetre est intact",
      cites(F1, "receiver") == ["FenetreNotes", "info", "info"],
      cites(F1, "receiver"))
check("les slots ne sont pas des noms d'objets : rien n'y a ete remplace",
      slots(F1) == ["close()", "setText(QString)", "clear()"], slots(F1))
check("les signaux non plus",
      signaux(F1) == ["clicked()", "textChanged(QString)", "clicked()"],
      signaux(F1))
check("trois connexions avant, trois apres",
      compte(F1, "connection") == 3, compte(F1, "connection"))

check("un objet cite comme destinataire se saisit aussi",
      saisit(v, "info", "etiquetteEleve"))
retires = v._write_ui_file(F1)
check("ses deux lignes de destination ont suivi",
      cites(F1, "receiver") == ["FenetreNotes", "etiquetteEleve",
                                "etiquetteEleve"], cites(F1, "receiver"))
check("l'ancien nom ne reste dans aucune connexion",
      "info" not in cites(F1, "receiver") + cites(F1, "sender"),
      cites(F1, "receiver"))
check("et rien n'a ete coupe pour autant", retires == 0, retires)

# un nom libere par un renommage est repris par un autre objet : les deux
# lignes doivent citer des noms differents, pas le dernier de la table
saisit(v, "saisie", "champ")
saisit(v, "boutonValider", "saisie")
retires = v._write_ui_file(F1)
check("un nom libere peut etre repris dans la meme ecriture",
      "saisie" in noms_modele(v) and "champ" in noms_modele(v), noms_modele(v))
check("chaque connexion suit l'objet qu'elle visait, pas le nom le plus recent",
      cites(F1, "sender") == ["saisie", "champ", "quitter"], cites(F1, "sender"))
check("les trois emetteurs restent distincts",
      len(set(cites(F1, "sender"))) == 3, cites(F1, "sender"))
check("aucune connexion n'est morte la-dedans", retires == 0, retires)
check("le fichier obtenu se relit", ET.parse(F1).getroot().tag == "ui")

# ── 3. reouvrir montre ce qui a ete ecrit ───────────────────

print("\n=== 3. reouvrir montre ce qui a ete ecrit ===")
v2, _c2 = vue_sur("reouverture")
v2.load_new_ui_file(F1)
check("le nom survit a une reouverture",
      noms_modele(v2) == ["champ", "saisie", "quitter", "cadre", "etiquetteEleve"],
      noms_modele(v2))
check("le canevas affiche les noms du fichier",
      set(["champ", "saisie", "etiquetteEleve"]) <= set(dessines(v2)),
      dessines(v2))
check("la vue qui rouvre un fichier n'a rien a demander",
      v2._travail_non_enregistre() is False)
_avant_re = octets(F1)
v2._write_ui_file(F1)
check("enregistrer sans rien changer ne change plus rien", octets(F1) == _avant_re)
check("et ne produit aucun doublon d'objet", len(noms_dun_fichier(F1)) == 6,
      noms_dun_fichier(F1))

# ── 4. l'ancien comportement, rejoue ────────────────────────

print("\n=== 4. l'ancien comportement, rejoue ===")
RENO = UiViewerPlugin._renomme_le_widget
_appels = [0]


def sans_report(self, el, props):
    _appels[0] += 1
    return None


UiViewerPlugin._renomme_le_widget = sans_report
v3, F3 = vue_sur("avant")
marche = saisit(v3, "ok", "boutonValider")
v3._write_ui_file(F3)
UiViewerPlugin._renomme_le_widget = RENO
check("la fusion appelle le rapporteur pour chaque objet",
      _appels[0] >= 5, _appels[0])
check("sans lui, le modele affiche le nom saisi", marche and
      "boutonValider" in noms_modele(v3))
check("et le fichier garde l'ancien : la divergence etait reelle",
      "boutonValider" not in noms_dun_fichier(F3) and
      "ok" in noms_dun_fichier(F3), noms_dun_fichier(F3))
CASS = CHEMIN("cassu.ui")
ecrit(CASS, FORMULAIRE_UI.replace('name="ok"', 'name="boutonValider"'))
check("le fichier « renommage sans connexions » cite un emetteur disparu",
      "ok" in cites(CASS, "sender") and "ok" not in noms_dun_fichier(CASS))

# ── 5. PyQt5 charge ce qui a ete enregistre ─────────────────

print("\n=== 5. loadUi du fichier renomme ===")
from PyQt5 import QtWidgets, uic                       # noqa: E402
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
v4, F4 = vue_sur("qt")
saisit(v4, "ok", "boutonValider")
saisit(v4, "info", "etiquetteEleve")
CHARGE = CHEMIN("charge.ui")
v4._write_ui_file(CHARGE)
try:
    w = uic.loadUi(CHARGE)
    charge = True
except Exception as e:                                # noqa: BLE001
    w, charge = None, False
    check("loadUi charge le fichier renomme", False, repr(e))
if charge:
    check("loadUi charge le fichier renomme", True)
    check("l'objet porte le nom que l'eleve a saisi", hasattr(w, "boutonValider"))
    check("l'ancien nom ne designe plus rien", not hasattr(w, "ok"))
    check("le label rebaptise est joignable sous son nouveau nom",
          hasattr(w, "etiquetteEleve") and not hasattr(w, "info"))
    check("et c'est bien le QPushButton de l'eleve",
          w.boutonValider.metaObject().className() == "QPushButton")
    check("le nom Qt vient du fichier",
          w.boutonValider.objectName() == "boutonValider")
    check("la mise en page n'est pas ecrasee par le renommage",
          w.layout() is not None and w.layout() is not w.boutonValider)
    w.show()
    w.boutonValider.click()
    racine.update()
    check("le cable suit le renommage : le bouton ferme toujours la fenetre",
          not w.isVisible(), w.isVisible())
    w6 = uic.loadUi(CHARGE)
    check("la zone de saisie chargee est bien la sienne",
          w6.saisie.placeholderText() == "Nom", w6.saisie.placeholderText())
    w6.saisie.setText("Ali")
    check("la connexion vers le label rebaptise fonctionne",
          w6.etiquetteEleve.text() == "Ali", w6.etiquetteEleve.text())
try:
    uic.loadUi(CASS)
    check("un fichier qui cite un emetteur supprime doit se refuser a Qt", False)
except Exception as e:                                # noqa: BLE001
    check("un fichier qui cite un emetteur supprime doit se refuser a Qt",
          "ok" in str(e), repr(e))

# ── 6. les noms que le fichier reserve ──────────────────────

print("\n=== 6. les noms que le fichier reserve ===")
v5, F5 = vue_sur("reserve")
check("les noms hors modele sont la fenetre, les layouts et les actions",
      v5._noms_hors_modele() == {"FenetreNotes", "colonne", "interne",
                                 "effacerTout"}, v5._noms_hors_modele())
i_ok = idx_de(v5, "ok")
for nom in ("colonne", "interne", "FenetreNotes", "effacerTout", "saisie",
            "", "2bouton", "mon bouton", "bouton-ok", "ok ok"):
    check("refuse : %r" % (nom,), v5._name_problem(nom, i_ok) != "",
          v5._name_problem(nom, i_ok))
for nom in ("boutonValider", "b2", "_prive", "ChampNom", "valider_tout",
            "ma_classe", "Column1"):
    check("accepte : %r" % (nom,), v5._name_problem(nom, i_ok) == "",
          v5._name_problem(nom, i_ok))
# _valid_qt_name s'appuie sur isalpha/isalnum : elles connaissent l'accent.
# « élan » est un identifiant Python 3 legitime, donc un nom Qt legitime : le
# refuser serait plus strict que le langage, et une suite qui l'aligne sur les
# refus reellement recus le figerait comme un bug.
check("un nom accentue reste un identifiant valide",
      v5._name_problem(NOM_ACCENTUE, i_ok) == "",
      v5._name_problem(NOM_ACCENTUE, i_ok))
check("se renommer soi-meme n'a jamais ete un probleme",
      v5._name_problem("ok", i_ok) == "")
check("le message d'une mise en page occupee explique le vrai risque",
      "mise en page" in v5._name_problem("colonne", i_ok),
      v5._name_problem("colonne", i_ok))

journal_avant = len(v5._undo_stack)
# temoin d'enregistrement : ET.write rend des fin de ligne \r\n la ou le fixture
# est ecrit en \n. Comparer un enregistrement a un enregistrement, jamais au
# texte du fixture, sinon le controle echoue pour une raison qui n'est pas la
# sienne (voir la regle _sortie de ce depot).
v5._write_ui_file(CHEMIN("reserve_ref.ui"))
octets_avant = octets(CHEMIN("reserve_ref.ui"))
saisit(v5, "ok", "colonne")
check("le refus laisse le nom du modele intact",
      v5.widgets_data[idx_de(v5, "ok")][1]["name"] == "ok")
check("un refus ne coute pas de pas d'annulation",
      len(v5._undo_stack) == journal_avant, len(v5._undo_stack))
v5._write_ui_file(F5)
check("un refus n'ecrit donc rien de dangereux", octets(F5) == octets_avant)

# le panneau n'est pas le seul chemin possible vers le modele : un nom saisi
# par-dessus le controle doit quand meme trouver un garde-fou au moment
# d'enregistrer, sinon le fichier part avec un objet efface par setupUi()
i_ok = idx_de(v5, "ok")
v5.widgets_data[i_ok][1]["name"] = "colonne"
dialogues.clear()
v5._save()
check("un nom de mise en page passe au travers du panneau : _save le refuse",
      [d[0] for d in dialogues] == ["error"], dialogues)
check("et l'avis nomme l'objet en cause et le vrai risque",
      "colonne" in str(dialogues) and "mise en page" in str(dialogues),
      str(dialogues)[:160])
check("rien n'est ecrit pendant que le nom est reserve",
      octets(F5) == octets_avant)
v5.widgets_data[i_ok][1]["name"] = "ok"
dialogues.clear()
v5._save()
check("le nom rendu libre, plus rien ne s'oppose a l'enregistrement",
      [d[0] for d in dialogues] == ["info"], dialogues)
check("et le fichier porte bien le nom de l'objet",
      "ok" in noms_dun_fichier(F5), noms_dun_fichier(F5))

# le nom d'un objet SUPPRIME est libre : ce n'est pas un nom reserve
v5._delete(idx_de(v5, "quitter"))
check("le nom du disparu est sorti du modele",
      "quitter" not in noms_modele(v5), noms_modele(v5))
check("et il redevient libre pour un autre objet",
      v5._name_problem("quitter", idx_de(v5, "ok")) == "",
      v5._name_problem("quitter", idx_de(v5, "ok")))
saisit(v5, "ok", "quitter")
retires = v5._write_ui_file(F5)
check("un renommage sur un nom libere par une suppression ne ressuscite rien",
      retires == 1, retires)
check("la connexion du disparu est partie avec lui",
      slots(F5) == ["close()", "setText(QString)"], slots(F5))
check("le survivant n'a pas herite du cable du mort",
      cites(F5, "sender") == ["quitter", "saisie"], cites(F5, "sender"))
check("et le fichier ne porte ce nom qu'une fois",
      noms_dun_fichier(F5).count("quitter") == 1, noms_dun_fichier(F5))
check("cinq <widget> dans le fichier, la racine comprise, apres la suppression",
      compte(F5, "widget") == 5, compte(F5, "widget"))

# ── 7. Annuler et retablir un renommage ─────────────────────

print("\n=== 7. journal ===")
v6, F6 = vue_sur("journal")
# temoin : un enregistrement sans renommage. Les octets de reference viennent
# d'un enregistrement, pas du fixture (\r\n d'un cote, \n de l'autre).
v6._write_ui_file(F6)
AVANT_J = octets(F6)
saisit(v6, "ok", "boutonValider")
check("le renommage est annulable", v6._undo_stack != [])
v6.undo()
check("Annuler rend l'ancien nom au modele",
      v6.widgets_data[idx_de(v6, "ok")][1]["name"] == "ok", noms_modele(v6))
v6._write_ui_file(F6)
check("Annuler puis enregistrer rend le fichier tel qu'il etait",
      octets(F6) == AVANT_J, octets(F6)[:150])
v6.redo()
check("Retablir rend le nom saisi", "boutonValider" in noms_modele(v6))
v6._write_ui_file(F6)
check("Retablir puis enregistrer retrouve le fichier renomme",
      "boutonValider" in noms_dun_fichier(F6))
check("l'arbre source n'a jamais ete modifie par un renommage",
      'name="ok"' in ET.tostring(v6._source_ui, encoding="unicode"))
check("rien n'a ete demande pendant tout cela",
      [d for d in dialogues if d[0] == "yesno"] == [], dialogues)
check("une frappe dans le champ nom ne coute qu'un seul pas",
      len(v6._undo_stack) == 1, len(v6._undo_stack))

# ── 8. ajoute puis renomme avant la premiere ecriture ───────

print("\n=== 8. objet ajoute ===")
v7, F7 = vue_sur("ajoute")
v7._add_widget("QCheckBox")
auto = noms_modele(v7)[-1]
check("le nom automatique est un identifiant",
      bool(auto) and (auto[0].isalpha() or auto[0] == "_") and
      all(c.isalnum() or c == "_" for c in auto), auto)
check("le panneau l'accepte tel quel",
      v7._name_problem(auto, len(v7.widgets_data) - 1) == "")
saisit(v7, auto, "casePresent")
retires = v7._write_ui_file(F7)
check("l'objet ajoute porte le nom saisi des la premiere ecriture",
      "casePresent" in noms_dun_fichier(F7), noms_dun_fichier(F7))
check("il n'est pas ecrit deux fois",
      noms_dun_fichier(F7).count("casePresent") == 1)
check("il est reste range dans la mise en page du fichier",
      compte(F7, "item") == 6, compte(F7, "item"))
check("et sans <geometry> heritee",
      ET.parse(F7).find(".//widget[@name='casePresent']").find(
          "property[@name='geometry']") is None)
check("les six objets du fichier sont ceux du modele",
      noms_dun_fichier(F7) == ["FenetreNotes"] + noms_modele(v7),
      noms_dun_fichier(F7))
check("aucune connexion perdue pour un ajout renomme", retires == 0, retires)
check("le fichier obtenu se charge avec son objet renomme",
      hasattr(uic.loadUi(F7), "casePresent"))

v8, _F8 = vue_sur("neuf")
v8._new()
v8._add_widget("QPushButton")
i8 = len(v8.widgets_data) - 1
check("sur une fenetre neuve, aucun nom n'est reserve",
      v8._noms_hors_modele() == set(), v8._noms_hors_modele())
check("le nom d'une mise en page est donc libre ici",
      v8._name_problem("colonne", i8) == "", v8._name_problem("colonne", i8))
NEUF = CHEMIN("neuf.ui")
v8.ui_file = NEUF
saisit(v8, noms_modele(v8)[i8], "colonne")
retires = v8._write_ui_file(NEUF)
check("le fichier neuf porte ce nom", "colonne" in noms_dun_fichier(NEUF),
      noms_dun_fichier(NEUF))
check("un fichier neuf n'a rien a menager", retires == 0, retires)
check("et son objet rebaptise se charge", hasattr(uic.loadUi(NEUF), "colonne"))

# ── 9. le reste du fichier survit ───────────────────────────

print("\n=== 9. le reste du fichier survit ===")
v9, F9 = vue_sur("survie")
saisit(v9, "cadre", "boiteNotes")
v9._write_ui_file(F9)
check("la mise en page imbriquee du groupe est intacte",
      nom_layouts(F9) == ["colonne", "interne"], nom_layouts(F9))
check("l'objet range dans cette mise en page a garde son nom",
      "info" in noms_dun_fichier(F9))
check("l'action du fichier n'a pas ete renommee par accident",
      "effacerTout" in [a.get("name") for a in ET.parse(F9).iter("action")],
      [a.get("name") for a in ET.parse(F9).iter("action")])
check("le titre du QGroupBox a survecu",
      ET.parse(F9).findtext(".//property[@name='title']/string") == "Notes")
check("le placeholder de la zone de saisie aussi",
      ET.parse(F9).findtext(".//property[@name='placeholderText']/string") == "Nom")
check("les textes des boutons aussi",
      ET.parse(F9).findtext(".//widget[@name='quitter']/property[@name='text']/string")
      == "Quitter")
check("le fichier commence toujours par la declaration XML",
      octets(F9)[:5] == b"<?xml", octets(F9)[:20])
check("et <resources> est toujours la",
      b"<resources" in octets(F9))
check("le fichier obtenu se charge", hasattr(uic.loadUi(F9), "boiteNotes"))
check("les trois connexions d'origine sont toujours la",
      compte(F9, "connection") == 3, compte(F9, "connection"))
check("le nom du groupe est dans le fichier et pas seulement a l'ecran",
      "boiteNotes" in noms_dun_fichier(F9) and "cadre" not in noms_dun_fichier(F9),
      noms_dun_fichier(F9))

# ── 10. ce que le code dit ──────────────────────────────────

print("\n=== 10. le code ===")
source = open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
arb = ast.parse(source)
meth = {n.name: n for n in ast.walk(arb) if isinstance(n, ast.FunctionDef)}
seg = lambda n: ast.get_source_segment(source, meth[n])          # noqa: E731
fusion, ecriture, report = seg("_merge_into_source"), seg("_write_ui_file"), seg("_renomme_le_widget")
purge, probleme, reserve = seg("_purge_orphelines"), seg("_name_problem"), seg("_noms_hors_modele")

check("_merge_into_source reporte le nom sur l'element",
      "_renomme_le_widget(" in fusion)
check("le report du nom se fait apres les proprietes, pas a la place",
      fusion.index("_write_changed(") < fusion.index("_renomme_le_widget("))
check("la fusion rend ses comptes via la table",
      'table["rennames"] = rennames' in fusion and
      'table["liberes"] = liberes' in fusion)
check("un seul endroit touche les connexions : _purge_orphelines",
      "_renomme_connexions" not in source and
      source.count('("sender", "receiver")') == 1)
check("_write_ui_file passe les renommages et les noms libres au menage",
      'recueil.get("rennames")' in ecriture and 'recueil.get("liberes")' in ecriture)
check("et le menage tourne apres la fusion",
      ecriture.index("_merge_into_source") < ecriture.index("_purge_orphelines"))
check("_renomme_le_widget ecrit l'attribut name de l'element",
      'el.set("name", nouveau)' in report)
check("il refuse un nom vide", "if not nouveau" in report)
check("il refuse un nom qui n'est pas un identifiant",
      "_valid_qt_name(nouveau)" in report)
def cites_de(nom):
    """Les identifiants que le corps d'une methode ecrit, hors docstring :
    « _source_ui n'apparait pas dans le texte » echoue sur une phrase de
    commentaire qui dit justement le contraire."""
    n = meth[nom]
    corps = n.body
    if corps and isinstance(corps[0], ast.Expr) and \
            isinstance(corps[0].value, ast.Constant) and \
            isinstance(corps[0].value.value, str):
        corps = corps[1:]
    return {getattr(x, "id", None) or getattr(x, "attr", None)
            for e in corps
            for x in ast.walk(e)
            if isinstance(x, (ast.Name, ast.Attribute))}


check("il ne touche jamais l'arbre source",
      "_source_ui" not in cites_de("_renomme_le_widget"),
      sorted(x for x in cites_de("_renomme_le_widget") if "source" in str(x)))
check("_write_changed ne s'occupe pas du nom : un seul ecrivain",
      'el.set("name"' not in seg("_write_changed"))
check("_purge_orphelines resout avant de reecrire",
      purge.index("rennames.get(nom, nom)") < purge.index("fils.text = nouveau"))
check("un nom libere par une suppression frappe la connexion de mort",
      "if nom in liberes" in purge)
check("les signal et slot ne sont jamais des cibles de remplacement",
      '"signal"' not in purge and '"slot"' not in purge)
check("la fusion des noms vivants ignore les <property> (le piege de item 1)",
      '("widget", "action")' in purge)
check("_name_problem consulte les noms reserves du fichier",
      "_noms_hors_modele()" in probleme)
check("_name_troubles, la derniere ligne avant le disque, les consulte aussi",
      "_noms_hors_modele()" in seg("_name_troubles"))
check("_name_troubles, le controle de _save, les connait aussi",
      "_noms_hors_modele()" in seg("_name_troubles"))
check("les noms reserves viennent de <layout>, <action> et de la racine",
      '("layout", "action")' in reserve and 'find("widget")' in reserve)
check("et le controle des widgets reste dans _used_names",
      "widgets_data" not in reserve)
check("aucun QMessageBox dans l'editeur visuel", "QMessageBox" not in source)
check("le texte lisible du refus est en francais",
      "mise en page" in probleme)

for top in fenetres:
    top.destroy()
racine.update()

check("aucun controle de cette suite n'est ecrit dans l'autre sens",
      a_l_envers == [], a_l_envers)

print("\n%d checks, %d echecs" % (bilan[0], bilan[1]))
sys.exit(1 if bilan[1] else 0)
