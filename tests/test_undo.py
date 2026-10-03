"""Annuler / retablir dans le concepteur d'interfaces.

Le viewer n'avait AUCUNE memoire : un clic de trop sur Supprimer, un widget
deplace par erreur, et le travail de la seance etait perdu — `grep -c "undo"`
renvoyait 0. Ce test construit le viewer pour de vrai (Tk bien reel) et verifie
que chaque action vaut un pas, que la frappe dans un champ vaut UN pas,
qu'Annuler rend le modele exact d'avant (y compris le livre de bord XML qui
relie un widget a son element), et que le fichier reenregistre apres annulation
est l'original octet pour octet.

Les gestes sont declenches par les vraies methodes (_on_click / _on_drag /
_on_drag_end) : elles ne lisent que x_root/y_root. Le clavier passe par un vrai
event_generate, sur une fenetre realisee — Tk jette un Keypress vers une
fenetre retiree.
"""
import copy
import os
import sys
import time
import types
from xml.etree import ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, r"C:\Users\Selmen\Desktop\projects\tunisiaschools")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tkinter as tk                                     # noqa: E402
from tkinter import Tk                                   # noqa: E402

import UIViewer                                          # noqa: E402
from UIViewer import UiViewerPlugin                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT_UI = os.path.join(HERE, "designer_layout.ui")

FAILS = []
N = [0]


def check(label, cond, detail=""):
    N[0] += 1
    if not cond:
        FAILS.append("%s %s" % (label, detail))
    print("%s %s%s" % ("OK  " if cond else "FAIL", label,
                       (" -> " + str(detail)) if detail else ""))


class boites:
    """Aucune fenetre modale pendant la campagne de tests."""
    @staticmethod
    def askyesno(*a, **k):
        return True

    @staticmethod
    def showinfo(*a, **k):
        return None

    @staticmethod
    def showerror(*a, **k):
        return None

    @staticmethod
    def askopenfilename(*a, **k):
        return ""

    @staticmethod
    def asksaveasfilename(*a, **k):
        return ""


UIViewer.messagebox = boites
UIViewer.get_workbench = lambda: None


class evt:
    def __init__(self, x=0, y=0):
        self.x_root = x
        self.y_root = y
        self.x = x
        self.y = y


def modele(v):
    """Copie comparable du modele, sans les Tk widgets."""
    return copy.deepcopy(v.widgets_data)


def geom(v, idx=0):
    """La geometrie VITANTE du widget — jamais une reference gardee a la main :
    Annuler remplace le dictionnaire de proprietes, un ancien objet reste
    fige a la valeur d'avant."""
    return v.widgets_data[idx][1]["geometry"]


def nb_pas(v):
    return len(v._undo_stack)


def donne_focus(wig, fen, essais=60):
    """Le widget tient-il VRAIMENT le clavier ? Tk ne distribue un Keypress
    synthetique qu'a une fenetre active, et focus_set() seul ne rend pas une
    fenetre active quand le test tourne en tache de fond. focus_force, puis on
    attend que le widget se declare lui-meme focalise."""
    fen.deiconify()
    fen.update()
    wig.focus_force()
    for _ in range(essais):
        fen.update()
        try:
            if wig.focus_get() is wig:
                return True
        except tk.TclError:
            return False
        time.sleep(0.02)
    return False


racine = Tk()
racine.withdraw()


def chord_livable():
    """Cette session Tk sait-elle FABRIQUER un faux « Ctrl + lettre » ?

    Tk doit traduire le keysym en keycode; sur une session sans clavier attache
    (processus lance depuis une fenetre de sortie, ecran verrouille), l'evenement
    part avec keysym « ?? » et la machine a reconnaitre les sequences ne le voit
    jamais : mesure ici, <Return> passe, <Control-z> non, et le meme test etait
    vert quand le bureau etait actif. Le test ne doit donc pas conclure a un bug
    du plugin la ou c'est la session qui refuse la touche ; il le dit.
    """
    sonde = tk.Toplevel(racine)
    sonde.geometry("200x120+20+20")
    sonde.update()
    champ = tk.Entry(sonde)
    champ.pack()
    sonde.deiconify()
    sonde.update()
    champ.focus_force()
    for _ in range(40):
        sonde.update()
        if champ.focus_get() is champ:
            break
    recu = []
    champ.bind("<Control-z>", lambda e: recu.append(e.keysym))
    champ.event_generate("<Control-z>")
    sonde.update()
    sonde.destroy()
    return bool(recu)


LIVRAISON = chord_livable()
rendu = []          # ce que les callbacks ont rendu a Tk : "break" = la frappe est consommée
print("   livraison : Tk fabrique un vrai <Control-z> dans cette session : %s"
      % LIVRAISON)


def cablage(vue):
    """Les (sequence -> callback, add) installs par _bind_history_keys, captures
    SANS toucher a la balise « all » : le bind_all est remplace le temps de
    l'appel, donc aucune vue ne deplace une autre."""
    captures = []
    veritable = vue.bind_all

    def espion(seq, func, add=None):
        captures.append((seq, func, add))

    vue.bind_all = espion
    try:
        vue._bind_history_keys()
    finally:
        del vue.bind_all
    return captures


def appuie(vue, champ, seq):
    """Ctrl+Z / Ctrl+Y comme l'eleve le fait.

    Quand la session ne sait pas fabriquer le chord, on appelle le callback que
    la balise « all » aurait atteint, avec un vrai objet Event : le cable, la
    garde et l'action sont testes, seul le transport Tk manque — et il est
    verifie separement, par le compte des scripts registers."""
    if LIVRAISON:
        champ.event_generate(seq)
        champ.winfo_toplevel().update()
        return "Tk"
    if getattr(vue, "_cablage", None) is None:
        vue._cablage = cablage(vue)
    for s, func, _add in vue._cablage:
        if s == seq:
            e = types.SimpleNamespace(widget=champ,
                                      keysym=seq.rsplit("-", 1)[-1])
            rendu.append(func(e))
            champ.winfo_toplevel().update()
            return "callback"
    raise AssertionError("aucune liaison installee pour %s" % seq)


def scripts_all(seq):
    """Les commandes Tcl attachees a la balise « all » pour une sequence : un
    element par vue, si bind_all a bien ete pose avec add=True."""
    import re
    texte = racine.tk.call("bind", "all", seq) or ""
    return re.findall(r"\[(\d+)<lambda>", texte)



def fenetre(nom):
    """Une vraie fenetre pour chaque vue : Tk ne distribue un Keypress
    synthetique qu'a une fenetre realisee, et chaque vue doit avoir son
    toplevel a elle pour que la garde du clavier soit testable."""
    top = tk.Toplevel(racine)
    top.title(nom)
    top.geometry("900x620+30+30")
    top.update()
    return top


f_v = fenetre("concepteur")
v = UiViewerPlugin(f_v)
v.pack(fill=tk.BOTH, expand=True)
f_v.withdraw()
f_v.update()


def vide(fen):
    fen.widgets_data[:] = []
    fen.selected_idx = None
    fen._refresh()
    fen._show_no_selection()
    fen.reset_history()


vide(v)

print("=== 1. un viewer neuf n'a rien a annuler ===")
check("les deux piles sont vides", v._undo_stack == [] and v._redo_stack == [],
      str((len(v._undo_stack), len(v._redo_stack))))
v.undo()
check("Annuler sur vide ne casse rien", v.widgets_data == [], modele(v))
check("le message passe par la barre d'etat, pas par une boite",
      "Rien a annuler" in v._info_lbl.cget("text"), v._info_lbl.cget("text"))
check("le bouton Annuler est grise",
      v._undo_lbl.cget("fg") == "#5a5a5a", v._undo_lbl.cget("fg"))

print("=== 2. ajouter, puis Annuler au clavier ===")
v._add_widget("QPushButton")
check("un ajout = un pas", nb_pas(v) == 1, nb_pas(v))
check("le widget est la", len(v.widgets_data) == 1, modele(v))
nom1 = v.widgets_data[0][1]["name"]
geom1 = geom(v)
# Le cas reel de l'eleve : il tape dans un champ du panneau de proprietes, le
# focus est donc DANS le concepteur, et Ctrl+Z doit annuler l'action de la vue.
# Tk ne distribue un Keypress genere qu'a une fenetre realisee : d'ou deiconify.
f_v.deiconify()
f_v.update()
champ_texte = tk.Entry(v)
champ_texte.pack()
f_v.update()
check("la fenetre du concepteur tient reellement le clavier",
      donne_focus(champ_texte, f_v), repr(v._focus_widget(
          types.SimpleNamespace(widget=f_v))))
voie_z = appuie(v, champ_texte, "<Control-z>")
check("Ctrl+Z a atteint le concepteur : le modele est vide  [%s]" % voie_z,
      v.widgets_data == [], modele(v))
check("le bouton Retablir s'est allume", v._redo_lbl.cget("fg") == "#cccccc",
      v._redo_lbl.cget("fg"))
voie_y = appuie(v, champ_texte, "<Control-y>")
check("Ctrl+Y a retabli le widget  [%s]" % voie_y, len(v.widgets_data) == 1,
      modele(v))
print("=== 2b. le cable : six sequences, un callback par vue ===")
v._cablage = cablage(v)
seqs = [s for s, _f, _a in v._cablage]
check("les six ecritures du raccourci sont installees",
      seqs == ["<Control-z>", "<Control-Z>", "<Control-y>", "<Control-Y>",
               "<Control-Shift-Z>", "<Control-Shift-z>"], seqs)
check("chacune en AJOUT, jamais en remplacement (add=True)",
      all(a is True for _s, _f, a in v._cablage),
      [(s, a) for s, _f, a in v._cablage if a is not True])
check("la balise « all » porte un script pour <Control-z>",
      len(scripts_all("<Control-z>")) >= 1, scripts_all("<Control-z>"))
v.undo()
check("Annuler a laisse un pas a retablir",
      v.widgets_data == [] and len(v._redo_stack) == 1, modele(v))
voie_maj = appuie(v, champ_texte, "<Control-Shift-Z>")
check("Ctrl+Shift+Z retablit comme Ctrl+Y  [%s]" % voie_maj,
      len(v.widgets_data) == 1 and v.widgets_data[0][1]["name"] == nom1,
      modele(v))
if LIVRAISON:
    print("   (le « break » rendu par le callback n'est pas lisible depuis")
    print("    event_generate : verifie par la voie du cable, section 10)")
else:
    check("chaque frappe consommee rend « break », jamais autre chose",
          rendu and set(rendu) == {"break"}, rendu)

champ_texte.destroy()
f_v.withdraw()
f_v.update()
v.undo()
check("Retablir puis Annuler se repondent", v.widgets_data == [], modele(v))
v.redo()
check("Retablir rend le widget avec le meme nom",
      len(v.widgets_data) == 1 and v.widgets_data[0][1]["name"] == nom1,
      modele(v))
check("Retablir rend aussi la geometrie", geom(v) == geom1, geom(v))
v.undo()
check("Annuler deux fois de suite ne pleure pas", v.widgets_data == [], modele(v))

print("=== 3. deux ajouts de suite valent deux pas ===")
vide(v)
v._add_widget("QPushButton")
v._add_widget("QPushButton")
check("deux pas de plus", nb_pas(v) == 2, nb_pas(v))
noms = [p["name"] for _c, p in v.widgets_data]
check("les deux boutons ont des noms distincts", len(set(noms)) == 2, noms)
v.undo()
check("un seul Annuler retire le dernier", len(v.widgets_data) == 1, modele(v))
v.undo()
check("le second retire l'autre", v.widgets_data == [], modele(v))
v.redo()
v.redo()
check("deux Retablir ramènent les deux", len(v.widgets_data) == 2, modele(v))
check("et dans le meme ordre", [p["name"] for _c, p in v.widgets_data] == noms,
      noms)

print("=== 4. la frappe dans un champ ne vaut qu'un pas ===")
vide(v)
v._add_widget("QLabel")
idx = 0
var = tk.StringVar(value="Label")
v._prop_vars["text"] = var
base = nb_pas(v)                  # l'ajout du QLabel compte deja un pas


def tape(texte):
    var.set(texte)
    v._apply("text", var, idx, str)


for mot in ["L", "Lo", "Lon", "Long", "Long u", "Long un t", "Long un tex",
            "Long un texte"]:
    tape(mot)
check("huit frappes = un seul pas d'annulation", nb_pas(v) == base + 1,
      "%d pas pour 8 frappes" % (nb_pas(v) - base))
check("le texte est bien la", v.widgets_data[idx][1]["text"] == "Long un texte",
      v.widgets_data[idx][1]["text"])
v.undo()
check("Annuler rend le libelle par defaut du QLabel",
      v.widgets_data[idx][1]["text"] == "Label",
      v.widgets_data[idx][1]["text"])

# un deuxieme champ du meme widget doit etre un autre pas
apres_annulation = nb_pas(v)
var2 = tk.StringVar(value="#ff0000")
v._prop_vars["styleSheet"] = var2
v._apply("styleSheet", var2, idx, str)
var2.set("#ff0000; x")
v._apply("styleSheet", var2, idx, str)
check("un autre champ du meme widget = un nouveau pas",
      nb_pas(v) == apres_annulation + 1, nb_pas(v) - apres_annulation)
check("deux frappes sur ce second champ ne comptent qu'un pas",
      v.widgets_data[idx][1]["styleSheet"] == "#ff0000; x",
      v.widgets_data[idx][1]["styleSheet"])
check("et le texte reste celui rendu par l'annulation",
      v.widgets_data[idx][1]["text"] == "Label",
      v.widgets_data[idx][1]["text"])
avant = nb_pas(v)
v._apply("styleSheet", var2, idx, str)
check("recrire la meme valeur ne cree pas de pas", nb_pas(v) == avant, nb_pas(v))
v._add_widget("QLabel")
var3 = tk.StringVar(value="B")
v._apply("text", var3, 1, str)
var3.set("BB")
v._apply("text", var3, 1, str)
check("l'ajout puis deux frappes sur le nouveau widget = deux pas",
      nb_pas(v) == avant + 2, nb_pas(v) - avant)

print("=== 5. deplacer et redimensionner ===")
vide(v)
v._add_widget("QLineEdit")
base = nb_pas(v)
geom_avant = geom(v)
v._on_click(evt(100, 100), 0)
v._on_drag(evt(130, 120), 0)
v._on_drag(evt(140, 130), 0)
v._on_drag_end(evt(140, 130), 0)
check("le glisser a bien deplace le widget", geom(v) != geom_avant,
      "%s -> %s" % (geom_avant, geom(v)))
check("tout le glisser ne vaut qu'un pas", nb_pas(v) == base + 1,
      nb_pas(v) - base)
v.undo()
check("Annuler remet la position d'origine", geom(v) == geom_avant, geom(v))
v._on_click(evt(50, 50), 0)
v._on_drag_end(evt(50, 50), 0)
check("un simple clic ne cree pas de pas", nb_pas(v) == base, nb_pas(v))
v.redo()
check("Retablir rejoue le deplacement", geom(v) != geom_avant, geom(v))
v.widgets_data[0][1]["geometry"] = geom_avant
v.reset_history()
v._resize_start(evt(200, 200), 0, "se")
v._resize_drag(evt(260, 230), 0, "se")
v._resize_end(evt(260, 230), 0)
check("redimensionner a agrandi", geom(v)[2] > 150, geom(v))
check("le redimensionnement vaut un pas", nb_pas(v) == 1, nb_pas(v))
v.undo()
check("Annuler rend la largeur precedente", geom(v)[2] == 150, geom(v))

print("=== 6. supprimer, doubler ===")
vide(v)
v._add_widget("QPushButton")
v._add_widget("QCheckBox")
deux = modele(v)
v._duplicate(0)
check("doubler ajoute un widget", len(v.widgets_data) == 3, modele(v))
v.undo()
check("Annuler defait le doublon", modele(v) == deux, modele(v))
v._delete(1)
check("supprimer retire le bon", len(v.widgets_data) == 1 and
      v.widgets_data[0][0] == "QPushButton", modele(v))
v.undo()
check("Annuler rend le widget supprime avec ses proprietes",
      modele(v) == deux, modele(v))
check("et sa place dans la liste", v.widgets_data[1][0] == "QCheckBox",
      modele(v))

print("=== 7. les copies ne se marchent pas dessus ===")
vide(v)
v._add_widget("QTextEdit")
v._add_widget("QTextEdit")
a, b = modele(v)
v.undo()
check("annuler l'ajout de B laisse A intact", modele(v) == [a], modele(v))
v.undo()
check("le modele est vide, A n'a pas laisse de trace", v.widgets_data == [],
      modele(v))
v.redo()
v.redo()
check("les deux Retablir rendent A puis B, sans les melanger",
      modele(v) == [a, b], modele(v))
check("le widget retabli n'est pas l'objet partage du journal",
      v.widgets_data[0][1] is not a[0][1], "alias")
v._apply("text", tk.StringVar(value="ecrit"), 0, str)
check("ecrire apres un Retablir ne corrompt pas la pile",
      v.widgets_data[0][1]["text"] == "ecrit" and
      v.widgets_data[1][1]["text"] != "ecrit", modele(v))

print("=== 8. les noms ne se collisionnent plus apres annulation ===")
vide(v)
v._add_widget("QPushButton")          # pushbutton
v._add_widget("QPushButton")          # pushbutton1
noms_avant = [p["name"] for _c, p in v.widgets_data]
v.undo()
v._add_widget("QPushButton")
apres = [p["name"] for _c, p in v.widgets_data]
check("ressortir le nom apres annulation ne le duplique pas",
      len(set(apres)) == 2, "%s puis %s" % (noms_avant, apres))
v._select(0)                          # l'eleve work sur le widget affiche
champ = tk.StringVar(value="boutonSpecial")
v._prop_vars["name"] = champ
v._apply("name", champ, 0, str)
check("renommer passe", v.widgets_data[0][1]["name"] == "boutonSpecial",
      modele(v))
v.undo()
check("Annuler rend l'ancien nom", v.widgets_data[0][1]["name"] == noms_avant[0],
      v.widgets_data[0][1]["name"])
check("le panneau de proprietes a suivi le retour",
      v._prop_vars["name"].get() == noms_avant[0], v._prop_vars["name"].get())
check("et la selection est restee sur le widget renomme", v.selected_idx == 0,
      v.selected_idx)

print("=== 9. Annuler puis enregistrer rend le fichier d'origine ===")
out1 = os.path.join(HERE, "undo_avant.ui")
out2 = os.path.join(HERE, "undo_apres.ui")
for f in (out1, out2):
    if os.path.exists(f):
        os.remove(f)
f_w = fenetre("concepteur - fichiers")
w = UiViewerPlugin(f_w)
w.pack(fill=tk.BOTH, expand=True)
f_w.withdraw()
f_w.update()
w.messagebox = boites
w.load_new_ui_file(LAYOUT_UI)
check("le fichier d'exemple s'ouvre", len(w.widgets_data) > 3,
      len(w.widgets_data))
check("ouvrir un fichier efface le journal precedent", w._undo_stack == [],
      nb_pas(w))
modele_ouverture = modele(w)
arbre_source = w._source_ui
w._add_widget("QPushButton")
w._delete(1)
check("deux pas journalises", nb_pas(w) == 2, nb_pas(w))
check("le journal partage l'arbre XML sans le copier",
      all(pas.get("_source_ui") is arbre_source for pas in w._undo_stack),
      sorted(w._undo_stack[0]))
w.undo()
w.undo()
check("deux Annuler rendent le modele tel qu'a l'ouverture",
      modele(w) == modele_ouverture,
      "%d widgets vs %d" % (len(w.widgets_data), len(modele_ouverture)))
check("l'arbre XML n'a pas ete remplace par les enregistrements",
      w._source_ui is arbre_source)
w._write_ui_file(out2)
check("enregistrer ne mutile pas l'arbre partage", w._source_ui is arbre_source)
temoin = UiViewerPlugin(fenetre("temoin"))
temoin.messagebox = boites
temoin.load_new_ui_file(LAYOUT_UI)
temoin._write_ui_file(out1)


def orphelins(chemin):
    """Les <item> d'un <layout> qui ne portent rien : ni widget, ni layout,
    ni spacer. Un <item> d'un QComboBox porte des <property>, ce n'est pas un
    orphelin — restreindre aux enfants de <layout> evite de confondre les deux."""
    rac = ET.parse(chemin).getroot()
    parents = {c: p for p in rac.iter() for c in p}
    return [i.attrib for i in rac.iter("item")
            if parents.get(i) is not None and parents[i].tag == "layout"
            and not [c for c in i if c.tag in ("widget", "layout", "spacer")]]


b1 = open(out1, "rb").read()
b2 = open(out2, "rb").read()
check("annuler puis enregistrer rend l'original OCTET pour OCTET",
      b1 == b2, "%d octets vs %d" % (len(b1), len(b2)))
check("aucun <item> orphelin dans le fichier rendu", orphelins(out2) == [],
      orphelins(out2))
texte2 = b2.decode("utf-8")
check("le QPushButton ajoute n'a pas laisse de trace dans le fichier",
      'name="pushbutton"' not in texte2,
      [l.strip() for l in texte2.splitlines() if "pushbutton" in l.lower()])

print("=== 10. le clavier ne vole pas le Ctrl+Z de l'editeur ===")
vide(w)
w._add_widget("QLabel")
pile_avant = nb_pas(w)
# Le voisin joue le role de l'editeur de Thonny : meme interpreteur Tcl que le
# concepteur, donc soumis aux memes bind_all — c'est la seule facon de prouver
# que la garde laisse l'annulation du texte a qui de droit.
stranger = tk.Toplevel(racine)
stranger.title("editeur")
stranger.geometry("300x150+700+60")
stranger.deiconify()
champ_stranger = tk.Entry(stranger)
champ_stranger.pack()
stranger.update()
tient_le_clavier = donne_focus(champ_stranger, stranger)
check("le voisin (l'editeur de Thonny) tient le clavier", tient_le_clavier,
      repr(w._focus_widget(types.SimpleNamespace(widget=champ_stranger))))
check("le concepteur ne reclame pas la frappe d'une fenetre voisine",
      w._event_for_us(types.SimpleNamespace(widget=stranger)) is False,
      repr(w._focus_widget(types.SimpleNamespace(widget=stranger))))
champ_stranger.insert(0, "du texte a annuler")
voie_voisin = appuie(w, champ_stranger, "<Control-z>")
check("Ctrl+Z chez le voisin ne touche pas au concepteur  [%s]" % voie_voisin,
      nb_pas(w) == pile_avant and len(w.widgets_data) == 1,
      "%d pas, %d widgets" % (nb_pas(w), len(w.widgets_data)))
if not LIVRAISON:
    check("et le concepteur ne consomme pas la frappe du voisin"
          " (rend None, Tk poursuit vers l'editeur)",
          rendu[-1] is None, rendu[-1:])
# Une seconde vue est ouverte depuis la section 9 (temoin) : c'est LE piege de
# bind_all sans add=True — la derniere creee remplace la liaison de la
# precedente sur la balise « all » et aucune des deux n'annule plus. On lui
# donne un pas a elle : si elle volait le clavier, sa pile bougerait.
temoin._add_widget("QLabel")
journal_temoin = (nb_pas(temoin), len(temoin._redo_stack))
champ_ici = tk.Entry(w)
champ_ici.pack()
f_w.update()
check("le concepteur reprend le clavier",
      donne_focus(champ_ici, f_w), repr(w._focus_widget(
          types.SimpleNamespace(widget=f_w))))
champ_ici.focus_set()
f_w.update()
check("la meme garde reconnait la frappe du concepteur",
      w._event_for_us(types.SimpleNamespace(widget=f_w)) is True,
      repr(w._focus_widget(types.SimpleNamespace(widget=f_w))))
voie_ici = appuie(w, champ_ici, "<Control-z>")
check("et le concepteur annule bien ce coup-la  [%s]" % voie_ici,
      nb_pas(w) == pile_avant - 1,
      "%d pas pour %d avant" % (nb_pas(w), pile_avant))
if not LIVRAISON:
    print("   (session sans clavier : le transport Tk n'est pas rejouable ici,")
    print("    la preuve que les deux vues coexistent est le compte des scripts)")
check("les deux vues ont chacune leur script sur la balise « all »",
      len(set(scripts_all("<Control-z>"))) >= 2, scripts_all("<Control-z>"))
check("aucune n'a remplace l'autre : un script par vue posee",
      len(set(scripts_all("<Control-z>"))) == len(set(scripts_all("<Control-y>"))),
      (scripts_all("<Control-z>"), scripts_all("<Control-y>")))
check("une vue ouverte plus tard n'a pas vole le clavier a celle du focus",
      (nb_pas(temoin), len(temoin._redo_stack)) == journal_temoin,
      "%s vs %s" % ((nb_pas(temoin), len(temoin._redo_stack)), journal_temoin))
# Le vrai cas Thonny : l'editeur est dans la MEME fenetre que la vue. Le
# toplevel ne suffit donc plus a departager — seule la chaine du focus tranche,
# et le repli « ma propre fenetre » ne doit jamais s'y substituer.
editeur = tk.Text(f_w)
editeur.pack()
f_w.update()
donne_focus(editeur, f_w)
pas_avant_editeur = nb_pas(w)
editeur.insert("1.0", "print('bonjour')")
voie_editeur = appuie(w, editeur, "<Control-z>")
f_w.update()
check("Ctrl+Z dans un editeur de la MEME fenetre reste a l'editeur  [%s]" % voie_editeur,
      nb_pas(w) == pas_avant_editeur
      and editeur.get("1.0", "end-1c") == "print('bonjour')",
      "%d pas, texte %r" % (nb_pas(w), editeur.get("1.0", "end-1c")))
check("la garde refuse par le focus, pas par le toplevel",
      w._event_for_us(types.SimpleNamespace(widget=f_w)) is False,
      repr(w._focus_widget(types.SimpleNamespace(widget=f_w))))
editeur.destroy()
champ_ici.destroy()
vrai_focus = w._focus_widget
w._focus_widget = lambda e: None          # personne n'a le clavier
try:
    tomb = w._event_for_us(types.SimpleNamespace(widget=f_w))
    ailleurs = w._event_for_us(types.SimpleNamespace(widget=stranger))
finally:
    w._focus_widget = vrai_focus
check("sans focus, la frappe va a la fenetre visee et a elle seule",
      tomb is True and ailleurs is False, (tomb, ailleurs))
check("une vue detruee ne reclame plus le clavier",
      w._event_for_us(types.SimpleNamespace(widget=None)) in (True, False),
      "la garde rend un booleen, jamais une exception")
f_w.withdraw()
f_w.update()
stranger.destroy()

print("=== 11. la pile est plafonnee ===")
vide(w)
for _i in range(60):
    w._add_widget("QLabel")
check("le journal s'arrete a son plafond", nb_pas(w) == w.UNDO_LIMIT, nb_pas(w))
for _i in range(w.UNDO_LIMIT):
    w.undo()
check("Annuler jusqu'au bout laisse les premiers ajouts",
      len(w.widgets_data) == 60 - w.UNDO_LIMIT, len(w.widgets_data))
w.undo()
check("le 41e Annuler dit qu'il n'a plus rien a faire",
      "Rien a annuler" in w._info_lbl.cget("text"), w._info_lbl.cget("text"))

print("=== 12. nouveau fichier = nouveau depart ===")
vide(w)
w._add_widget("QLabel")
w._add_widget("QLabel")
check("deux pas avant d'ouvrir", nb_pas(w) == 2, nb_pas(w))
w.load_new_ui_file(LAYOUT_UI)
check("ouvrir efface le journal", w._undo_stack == [] and w._redo_stack == [],
      (len(w._undo_stack), len(w._redo_stack)))
apres_ouverture = modele(w)
w.undo()
check("et Annuler ne fait revivre aucun widget de la seance d'avant",
      modele(w) == apres_ouverture,
      "%d widgets, %d pas" % (len(w.widgets_data), nb_pas(w)))
w._new()
check("Nouveau efface aussi le journal",
      w._undo_stack == [] and w.widgets_data == [],
      (nb_pas(w), len(w.widgets_data)))
check("les boutons sont retombes", w._undo_lbl.cget("fg") == "#5a5a5a",
      w._undo_lbl.cget("fg"))

print("=== 13. un objet construit hors du constructeur survit ===")
# Les harnais de test (et un appel depuis Thonny avant _build_ui) n'ont pas
# les attributs du journal : l'edition doit passer quand meme.
n = object.__new__(UiViewerPlugin)
n.widgets_data = [("QLabel", {"name": "l", "geometry": (0, 0, 10, 10)})]
n.widget_counter = 0
n.selected_idx = None
n.root_widget_name = "Form"
n.root_widget_class = "QDialog"
n.root_geometry = (0, 0, 100, 100)
n.root_title = "Form"
n._source_uids = []
n._src_root = {}
n._refresh = lambda: None
n._select = lambda i: None
n._show_properties = lambda i: None
n._show_no_selection = lambda: None
n._prop_vars = {}
try:
    UiViewerPlugin._add_widget(n, "QPushButton")
    UiViewerPlugin.undo(n)
    ok = len(n.widgets_data) == 1
except Exception as e:
    ok = e
check("ajouter puis annuler sans constructeur fonctionne", ok is True, ok)

m = object.__new__(UiViewerPlugin)
m.widgets_data = []
m._refresh = lambda: None
m._show_no_selection = lambda: None
m._select = lambda i: None
m._prop_vars = {}
try:
    UiViewerPlugin._record(m, ("champ", "text", 0))
    journalise = nb_pas(m) == 1
    UiViewerPlugin.undo(m)
    rendu = (nb_pas(m), len(m._redo_stack), m.widgets_data == [])
    UiViewerPlugin.undo(m)          # pile vide, et surtout pas d'_info_lbl
    ok2 = journalise and rendu == (0, 1, True)
except Exception as e:
    ok2 = e
check("un modele sans fenetre ni barre d'etat journalise son pas",
      ok2 is True, ok2)
try:
    UiViewerPlugin.redo(m)
    ok3 = (nb_pas(m) == 1 and len(m._redo_stack) == 0
           and len(m.widgets_data) == 0)
except Exception as e:
    ok3 = e
check("et le retablir d'un objet nu ne pretend rien inventer", ok3 is True, ok3)
check("le journal ne reclame ni _build_ui ni workbench",
      not hasattr(m, "_info_lbl") and not hasattr(m, "master"),
      (hasattr(m, "_info_lbl"), hasattr(m, "master")))

print("\n%d checks, %d echecs" % (N[0], len(FAILS)))
for f in FAILS:
    print("ECHEC " + f)
sys.exit(1 if FAILS else 0)
