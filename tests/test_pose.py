# -*- coding: utf-8 -*-
"""Item 7 — un widget range ne porte pas de <geometry>, et glisser le reclasse.

Le probleme, tel qu'il est dans le code avant cette correction :
`_write_changed` ecrivait une propriete `geometry` des que `props["geometry"]`
changeait, sans savoir QUI decide la position. Or un <widget> rangé dans un
<item> de <layout> est placé par Qt à l'affichage : la balise écrite là est

  1. ignorée à l'exécution (l'élève déplace, le run ne suit pas),
  2. un écart permanent avec Qt Designer, qui n'en écrit jamais
     (vérifié sur designer_layout.ui : 9 widgets rangés, 0 <geometry> ; seule
     la racine en porte une),
  3. et le glisser donnait donc l'illusion d'un résultat.

La regle verifiee ici, dans l'ordre :

  • la lecture sait dire qui est range (_pose), et l'empreinte de reference
    decrit le FICHIER, pas l'ecran ;
  • un glisser, un redimensionnement ou une frappe dans X/Y ne deplace PAS un
    widget range : la barre d'etat l'explique, et le geste ne coute pas un
    coup d'Annuler ;
  • le panneau rend les quatre champs gris et offre « Libérer la position » ;
  • liberer ecrit la geometrie et-sort l'element de son <item> ; remettre
    detruit la balise et rend l'element a un <item> — meme apres reouverture
    du fichier libere (le piege de la geometrie heritee) ;
  • dans ETAT final, jamais une <geometry> ne se trouve sous un <item> de
    <layout>, sur 60 tirages de poses ;
  • enregistrer reste idempotent et ne casse aucune structure (<item> vides,
    entrees de combo, cellules de tableau, <connections>, <spacer>) ;
  • et la preuve qui compte pour l'eleve : loadUi repose reellement le widget
    libere a la place ecrite.

La tranche 7b, verifiee par la section 13 : la regle 7a refusait tout le geste.
Ici, quand la mise en page est une BOITE LINEAIRE et que le widget a des freres,
glisser ne deplace plus — il RECLASSE. Le modele retient donc trois choses par
widget (``_groupe``, ``_axe``, ``_rang``, poses a la lecture et a l'ajout), le
geste ne touche aucune geometry avant le lacher, ``_applique_l_ordre`` permute
les seuls <item> tenus par des widgets (un <layout> imbrique et un <spacer>
gardent leur place), et le journal — qui snapshote ``widgets_data`` — rend le
reclassement annulable sans travail de plus. Grille, formulaire, pile et frere
unique en restent a refus de 7a. Le fichier doit rester idempotent, sans
<geometry> sous un <item>, et loadUi doit rendre le meme ordre.
"""
import ast
import io
import json
import os
import random
import subprocess
import sys
import tkinter as tk
import types
from tkinter import Tk

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
PLUGIN = r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT_UI = os.path.join(HERE, "designer_layout.ui")
ABS_UI = os.path.join(HERE, "absolute.ui")
HBOX_UI = os.path.join(HERE, "designer_hbox.ui")
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import UIViewer                                          # noqa: E402
from UIViewer import UiViewerPlugin                      # noqa: E402

SOURCE = io.open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
FAILS = []
N = [0]


def check(label, cond, detail=""):
    N[0] += 1
    if not cond:
        FAILS.append("%s  %s" % (label, detail))
    print("%s %s%s" % ("OK  " if cond else "FAIL", label,
                       ("   -> " + str(detail)) if detail else ""))


class boites:
    @staticmethod
    def askyesno(*a, **k):
        return True

    @staticmethod
    def showinfo(*a, **k):
        return None

    @staticmethod
    def showerror(*a, **k):
        return None


UIViewer.messagebox = boites
UIViewer.get_workbench = lambda: None

LIBERE = "Libérer la position"
REMETTRE = "Remettre dans la mise en page"


def ev(x, y):
    return types.SimpleNamespace(x=x, y=y, x_root=x, y_root=y,
                                 widget=None, num=1, delta=0)


# ── lecture / ecriture XML ───────────────────────────────────

def lire(path):
    import xml.etree.ElementTree as ET
    return ET.parse(path).getroot()


def parents_de(racine):
    return {c: p for p in racine.iter() for c in p}


def ranges(el, parents):
    """(item, layout) si l'element est range dans une mise en page."""
    item = parents.get(el)
    if item is None or item.tag != "item":
        return None
    lay = parents.get(item)
    if lay is None or lay.tag != "layout":
        return None
    return item, lay


def porte_geometry(el):
    return el.find("property[@name='geometry']") is not None


def violations(racine):
    """(nom, x) de tout <widget> range dans un <layout> et porteur d'une geometry."""
    parents = parents_de(racine)
    out = []
    for el in list(racine.iter("widget"))[1:]:
        if ranges(el, parents) and porte_geometry(el):
            g = el.find("property[@name='geometry']")
            out.append((el.get("name"), g.findtext("rect/x", "?")))
    return out


def items_vides(racine):
    parents = parents_de(racine)
    return [it for it in racine.iter("item")
            if (parents.get(it) is not None
                and parents[it].tag == "layout"
                and it.find("widget") is None
                and it.find("layout") is None
                and it.find("spacer") is None)]


def doublons(racine):
    """Un meme <widget> ecrit deux fois : le piege d'ElementTree quand on
    ajoute un element sans le retirer de son pere. La verification compte les
    OBJETS, pas les noms — deux widgets peuvent legitiment porter le meme nom
    dans un fichier casse, mais un seul element peut etre le meme objet."""
    vus, doubles = set(), []
    for el in racine.iter("widget"):
        if id(el) in vus:
            doubles.append(el.get("name"))
        vus.add(id(el))
    return doubles


def noms_doublons(racine):
    vus, doubles = {}, []
    for el in racine.iter("widget"):
        n = el.get("name")
        vus[n] = vus.get(n, 0) + 1
    for n, c in vus.items():
        if c > 1:
            doubles.append((n, c))
    return doubles


def par_nom(racine, nom):
    return next(e for e in racine.iter("widget") if e.get("name") == nom)


def compte(path, tag):
    return len(list(lire(path).iter(tag)))


# ── fenetres Tk ──────────────────────────────────────────────

def fenetre(nom):
    top = tk.Toplevel(racine)
    top.title(nom)
    top.geometry("980x680+30+30")
    top.update()
    v = UiViewerPlugin(top)
    v.pack(fill=tk.BOTH, expand=True)
    top.update()
    return top, v


def desc(w, cls):
    out = []
    for c in w.winfo_children():
        if isinstance(c, cls):
            out.append(c)
        out.extend(desc(c, cls))
    return out


def champs_geo(v):
    """Les quatre Entry de X/Y/Largeur/Hauteur, dans l'ordre du panneau."""
    return desc(v.prop_frame, tk.Entry)[1:5]


def bouton_pose(v):
    for v2 in desc(v.prop_frame, tk.Label):
        t = v2.cget("text").strip()
        if t in (LIBERE, REMETTRE):
            return v2, t
    return None, None


def etat_bouton(v):
    b, t = bouton_pose(v)
    return t


def index_de(v, nom):
    return next(i for i, (_c, p) in enumerate(v.widgets_data)
                if p.get("name") == nom)


def props_de(v, nom):
    return v.widgets_data[index_de(v, nom)][1]


def nb(v, tag):
    return sum(1 for _c, p in v.widgets_data if p.get("_pose") == tag)


racine = Tk()
racine.withdraw()

# ── 1. la source ne peut ecrire une geometry que sous garde ──
print("=== 1. la regle est dans le code, pas seulement dans l'usage ===")
check("la source analysee est le fichier du plugin",
      os.path.samefile(os.path.abspath(UIViewer.__file__),
                       os.path.join(PLUGIN, "UIViewer.py")),
      UIViewer.__file__)
arbre = ast.parse(SOURCE)
classe = next(n for n in ast.walk(arbre)
              if isinstance(n, ast.ClassDef) and n.name == "UiViewerPlugin")
meth = {n.name: n for n in classe.body if isinstance(n, ast.FunctionDef)}

def ecrivent_rect():
    """Les methodes qui appellent _set_rect_prop (l'ecrivain de <geometry>)."""
    out = set()
    for m in meth.values():
        if any(isinstance(n, ast.Attribute) and n.attr == "_set_rect_prop"
               for n in ast.walk(m)):
            out.add(m.name)
    return out - {"_set_rect_prop"}


ecrivains = ecrivent_rect()
check("_set_rect_prop n'est appele que par les ecrivains connus",
      ecrivains <= {"_write_changed", "_merge_into_source", "_build_fresh_ui",
                    "_insert_added"},
      ecrivains)

wc = io.open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
corps_wc = ast.get_source_segment(wc, meth["_write_changed"])
check("_write_changed garde l'ecriture de geometry derriere _pose",
      '"_pose"' in corps_wc and "_retire_rect" in corps_wc
      and "_set_rect_prop" in corps_wc, corps_wc[corps_wc.find("def"):][:40])
check("la branche « layout » retire toujours la balise",
      "self._retire_rect(el)" in corps_wc.split("elif geom")[0],
      corps_wc.splitlines()[3:8])
check("_pose est pose a la lecture et a l'ajout",
      '"_pose"' in ast.get_source_segment(wc, meth["_parse_ui"]) and
      '"_pose"' in ast.get_source_segment(wc, meth["_add_widget"]))
check("aucune boite de dialogue nait du refus (statut seulement)",
      "messagebox" not in
      ast.get_source_segment(wc, meth["_position_reglee_par_layout"]) +
      ast.get_source_segment(wc, meth["_on_drag"]) +
      ast.get_source_segment(wc, meth["_bascule_position"]))

# ── 2. la lecture sait qui est range ─────────────────────────
print("=== 2. la lecture distingue range et libre ===")
top, v = fenetre("pose-lecture")
v.load_new_ui_file(LAYOUT_UI)
poses = {p["name"]: p.get("_pose") for _c, p in v.widgets_data}
check("les 9 widgets du gabarit Designer sont dits ranges",
      set(poses.values()) == {"layout"} and len(poses) == 9, poses)
r = v.root_geometry
check("leur position affichee est une estimation non nulle",
      all(p.get("geometry") and p["geometry"][2] > 0
          for _c, p in v.widgets_data),
      [p["geometry"] for _c, p in v.widgets_data])
check("_src ne pretend pas que le fichier portait une geometry",
      all(p["_src"].get("geometry") is None for _c, p in v.widgets_data),
      {n: p["_src"].get("geometry")
       for n, p in ((p["name"], p) for _c, p in v.widgets_data)})
check("_est est rempli pour un widget range",
      all(p.get("_est") for _c, p in v.widgets_data),
      [(p["name"], p.get("_est")) for _c, p in v.widgets_data])
top.destroy()

top, v = fenetre("pose-absolu")
v.load_new_ui_file(ABS_UI)
check("un fichier en pose absolue est dit libre",
      all(p.get("_pose") == "libre" for _c, p in v.widgets_data)
      and v.widgets_data,
      {p["name"]: p.get("_pose") for _c, p in v.widgets_data})
check("son empreinte _src porte bien la geometry du fichier",
      all(p["_src"].get("geometry") for _c, p in v.widgets_data))
top.destroy()

# ── 3. le geste refusé ───────────────────────────────────────
print("=== 3. la ou le glisser ne peut rien promettre, il est refuse ===")
# 7b a rendu le glisser fecond dans les boites lineaires (il reclasse) ; il
# reste refuse la ou il n'y a rien a déplacer sans mentir : un widget seul dans
# sa mise en page, et tout ce qu'une grille ou un formulaire range par lignes.
for nom, raison in [("btnQuitter", "seul dans sa boite horizontale"),
                    ("labelClasse", "range par un formulaire")]:
    top, v = fenetre("pose-refus-" + nom)
    v.load_new_ui_file(LAYOUT_UI)
    i_c = index_de(v, nom)
    geometrie_avant = props_de(v, nom)["geometry"]
    v._select(i_c)
    check("%s : %s -> le glisser est refuse" % (nom, raison),
          v._mode_glissement(props_de(v, nom)) == "refus",
          v._mode_glissement(props_de(v, nom)))
    pile_avant = len(v._undo_stack)
    v._on_click(ev(100, 100), i_c)
    v._on_drag(ev(180, 160), i_c)
    v._on_drag(ev(240, 220), i_c)
    v._on_drag_end(ev(240, 220), i_c)
    check("%s : le glisser n'a pas change la position" % nom,
          props_de(v, nom)["geometry"] == geometrie_avant,
          props_de(v, nom)["geometry"])
    check("%s : la barre d'etat explique et nomme l'action" % nom,
          "mise en page" in v._info_lbl.cget("text")
          and LIBERE in v._info_lbl.cget("text"),
          v._info_lbl.cget("text"))
    check("%s : le geste refuse ne coute pas un coup d'Annuler" % nom,
          len(v._undo_stack) == pile_avant, (pile_avant, len(v._undo_stack)))
    check("%s : aucun objet modifie, rien a retablir non plus" % nom,
          not v._redo_stack)

    x, y, w, h = geometrie_avant
    v._resize_start(ev(100, 100), i_c, "se")
    v._resize_drag(ev(200, 180), i_c, "se")
    v._resize_end(ev(200, 180), i_c)
    check("%s : redimensionner est refuse de meme" % nom,
          props_de(v, nom)["geometry"] == geometrie_avant,
          props_de(v, nom)["geometry"])
    check("%s : la taille refusee ne coute pas un Annuler" % nom,
          len(v._undo_stack) == pile_avant, (pile_avant, len(v._undo_stack)))

    champs = champs_geo(v)
    check("%s : le panneau grise les quatre champs de geometrie" % nom,
          len(champs) == 4 and
          all(c.cget("state") == tk.DISABLED for c in champs),
          [c.cget("state") for c in champs])
    check("%s : les champs gris gardent la valeur estimee lisible" % nom,
          v._prop_vars["geo_x"].get() == str(x),
          (v._prop_vars["geo_x"].get(), x))
    check("%s : le panneau propose « %s »" % (nom, LIBERE),
          etat_bouton(v) == LIBERE, etat_bouton(v))
    v._apply_geom("geo_x", tk.StringVar(value=str(x + 300)), i_c)
    check("%s : ecrire dans la variable ne deplace pas non plus" % nom,
          props_de(v, nom)["geometry"] == geometrie_avant,
          props_de(v, nom)["geometry"])
    check("%s : et ne coute toujours pas un Annuler" % nom,
          len(v._undo_stack) == pile_avant, (pile_avant, len(v._undo_stack)))
    top.destroy()

# ── 4. liberer la position ───────────────────────────────────
print("=== 4. « %s » fait du geste une realite ===" % LIBERE)
top, v = fenetre("pose-libere")
v.load_new_ui_file(LAYOUT_UI)
i_le = index_de(v, "lineEdit")
estimee = props_de(v, "lineEdit")["geometry"]
pile_avant = len(v._undo_stack)
v._select(i_le)
b, t = bouton_pose(v)
check("le bouton est cliquable (hand2)", b is not None and
      b.cget("cursor") == "hand2", b and b.cget("cursor"))
pile_avant = len(v._undo_stack)
v._bascule_position(i_le)
check("_pose est passe a « libre »",
      props_de(v, "lineEdit")["_pose"] == "libre")
check("le widget garde la position que le canevas montrait",
      props_de(v, "lineEdit")["geometry"] == estimee,
      (props_de(v, "lineEdit")["geometry"], estimee))
check("liberer coute exactement un coup d'Annuler",
      len(v._undo_stack) == pile_avant + 1,
      (pile_avant, len(v._undo_stack)))
champs = champs_geo(v)
check("les champs sont redevenus editables",
      all(c.cget("state") != tk.DISABLED for c in champs),
      [c.cget("state") for c in champs])
check("le bouton propose maintenant « %s »" % REMETTRE,
      etat_bouton(v) == REMETTRE, etat_bouton(v))
check("la barre d'etat confirme, sans boite de dialogue",
      "libéré" in v._info_lbl.cget("text"), v._info_lbl.cget("text"))
x, y, w, h = props_de(v, "lineEdit")["geometry"]
v._on_click(ev(100, 100), i_le)
v._on_drag(ev(130, 150), i_le)
v._on_drag_end(ev(130, 150), i_le)
check("depuis lors le glisser deplace vraiment",
      props_de(v, "lineEdit")["geometry"] == (x + 30, y + 50, w, h),
      props_de(v, "lineEdit")["geometry"])
check("le glisser admis coute un Annuler",
      len(v._undo_stack) == pile_avant + 2, len(v._undo_stack))
deplace = props_de(v, "lineEdit")["geometry"]
out = os.path.join(HERE, "pose_libere_out.ui")
v._write_ui_file(out)
r = lire(out)
el = par_nom(r, "lineEdit")
check("le fichier ne range plus le widget libere",
      ranges(el, parents_de(r)) is None,
      parents_de(r)[el].tag)
check("le fichier porte la position absolue ecrite",
      [int(el.find("property[@name='geometry']").findtext("rect/" + t))
       for t in ("x", "y", "width", "height")] == list(deplace),
      el.find("property[@name='geometry']").find("rect").attrib
      if el.find("property[@name='geometry']") is not None else None)
check("aucune autre geometry ne traine sous un <item>",
      violations(r) == [], violations(r))
check("aucun <item> vide", items_vides(r) == [])
check("le widget libre est ecrit avant le <layout> de son conteneur",
      [c.tag for c in r.find("widget")].index("widget")
      < [c.tag for c in r.find("widget")].index("layout"))
top.destroy()

# ── 5. rendre la position ────────────────────────────────────
print("=== 5. « %s » efface la balise et rend l'element au layout ===" % REMETTRE)
top, v = fenetre("pose-remis")
v.load_new_ui_file(out)
i_le = index_de(v, "lineEdit")
check("la relecture du fichier libere dit « libre »",
      props_de(v, "lineEdit")["_pose"] == "libre")
check("les autres widgets restent ranges",
      nb(v, "layout") == len(v.widgets_data) - 1,
      {p["name"]: p["_pose"] for _c, p in v.widgets_data})
v._select(i_le)
check("le panneau propose bien de le remettre", etat_bouton(v) == REMETTRE,
      etat_bouton(v))
avant = props_de(v, "lineEdit")["geometry"]
v._bascule_position(i_le)
check("_pose est revenu a « layout »",
      props_de(v, "lineEdit")["_pose"] == "layout")
check("la position affichee est re-estimee, plus celle ecrite",
      props_de(v, "lineEdit")["geometry"] != avant,
      (props_de(v, "lineEdit")["geometry"], avant))
check("_est suit la nouvelle estimation",
      props_de(v, "lineEdit")["_est"] == props_de(v, "lineEdit")["geometry"],
      props_de(v, "lineEdit")["_est"])
out2 = os.path.join(HERE, "pose_remis_out.ui")
v._write_ui_file(out2)
r2 = lire(out2)
el2 = par_nom(r2, "lineEdit")
check("l'element a retrouve un <item> de <layout>",
      ranges(el2, parents_de(r2)) is not None,
      parents_de(r2)[el2].tag)
check("la geometrie heritee du fichier a ete detruite",
      not porte_geometry(el2),
      el2.find("property[@name='geometry']") is not None)
check("aucune violation dans le fichier remis", violations(r2) == [],
      violations(r2))
_place = ranges(el2, parents_de(r2))
check("le widget remis n'apparait qu'une fois dans le fichier",
      doublons(r2) == [] and noms_doublons(r2) == [],
      (doublons(r2), noms_doublons(r2)))
check("l'element est revenu en dernier <item> de son layout",
      _place is not None and list(_place[1])[-1] is _place[0],
      [c.tag for c in (_place[1] if _place else [])])
top.destroy()

# ── 6. le piege de la geometrie heritee, dans l'autre sens ───
print("=== 6. liberer puis remettre sans enregistrer ===")
top, v = fenetre("pose-aller-retour")
v.load_new_ui_file(LAYOUT_UI)
i = index_de(v, "labelClasse")
initiale = props_de(v, "labelClasse")["geometry"]
v._bascule_position(i)
v._bascule_position(i)
check("deux bascules ramènent le widget sous un <item>",
      props_de(v, "labelClasse")["_pose"] == "layout")
ok = os.path.join(HERE, "pose_retour.ui")
v._write_ui_file(ok)
r = lire(ok)
el = par_nom(r, "labelClasse")
check("et le fichier n'a pas garde de geometry sous cet <item>",
      ranges(el, parents_de(r)) is not None and not porte_geometry(el),
      (parents_de(r)[el].tag, porte_geometry(el)))
check("aucune violation", violations(r) == [], violations(r))
check("le compte des <item> est revenu a celui du gabarit",
      compte(ok, "item") == compte(LAYOUT_UI, "item"),
      (compte(ok, "item"), compte(LAYOUT_UI, "item")))
check("Annuler deux fois rend la pose initiale",
      (v.undo(), v.undo(),
       props_de(v, "labelClasse")["_pose"] == "layout"
       and props_de(v, "labelClasse")["geometry"] == initiale)[-1],
      props_de(v, "labelClasse"))
top.destroy()

# ── 7. balayage : la regle tient sur toutes les combinaisons ─
print("=== 7. 60 tirages de poses, aucune violation admise ===")
top, v = fenetre("pose-balayage")
v.load_new_ui_file(LAYOUT_UI)
noms = [p["name"] for _c, p in v.widgets_data]
base = {p["name"]: dict(p) for _c, p in v.widgets_data}
tirages = [(True,) * len(noms), (False,) * len(noms)]
rnd = random.Random(20260923)
for _ in range(58):
    tirages.append(tuple(rnd.random() < 0.5 for _n in noms))
chemin = os.path.join(HERE, "pose_balayage.ui")
mauvais, vides, fautes_modele, dupliques = [], [], [], []
for poses in tirages:
    for nom, pose in zip(noms, poses):
        props_de(v, nom)["_pose"] = "layout" if pose else "libre"
        if not pose:
            x, y, _w, _h = base[nom]["geometry"]
            props_de(v, nom)["geometry"] = (x + 7, y + 11, 80, 24)
    v._write_ui_file(chemin)
    r = lire(chemin)
    par = parents_de(r)
    mauvais += violations(r)
    vides += items_vides(r)
    dupliques += noms_doublons(r)
    for nom, pose in zip(noms, poses):
        el = par_nom(r, nom)
        range_ = ranges(el, par) is not None
        if range_ != pose:
            fautes_modele.append((nom, pose, range_))
        if range_ and porte_geometry(el):
            fautes_modele.append((nom, "geometry sous item"))
        if not range_ and not porte_geometry(el):
            fautes_modele.append((nom, "libre sans geometry"))
check("aucune <geometry> sous un <item> de <layout> (60 etats)",
      not mauvais, mauvais[:6])
check("aucun <item> rendu vide (60 etats)", not vides, vides[:6])
check("le fichier raconte la meme pose que le modele (60 etats)",
      not fautes_modele, fautes_modele[:6])
check("aucun widget ecrit deux fois (60 etats)", not dupliques, dupliques[:6])
check("les <layout> sont tous preserves",
      compte(chemin, "layout") == compte(LAYOUT_UI, "layout"),
      (compte(chemin, "layout"), compte(LAYOUT_UI, "layout")))
check("les <spacer> sont preserves",
      compte(chemin, "spacer") == compte(LAYOUT_UI, "spacer"),
      (compte(chemin, "spacer"), compte(LAYOUT_UI, "spacer")))
check("les <connections> sont preserve",
      compte(chemin, "connection") == compte(LAYOUT_UI, "connection"))
top.destroy()

# ── 8. idempotence et structures particulieres ───────────────
print("=== 8. enregistrer deux fois, et menager les faux <item> ===")
top, v = fenetre("pose-idempotence")
v.load_new_ui_file(LAYOUT_UI)
v._bascule_position(index_de(v, "comboClasse"))
a = os.path.join(HERE, "pose_idem_a.ui")
b = os.path.join(HERE, "pose_idem_b.ui")
v._write_ui_file(a)
v._write_ui_file(b)
check("le second enregistrement est identique au premier",
      io.open(a, "rb").read() == io.open(b, "rb").read())
check("les entrees du QComboBox ne sont pas prises pour des mises en page",
      compte(a, "item") == compte(LAYOUT_UI, "item") - 1,
      (compte(a, "item"), compte(LAYOUT_UI, "item")))
ra = lire(a)
combo = par_nom(ra, "comboClasse")
combo_src = par_nom(lire(LAYOUT_UI), "comboClasse")
check("le combo libere a garde ses <item> d'elements",
      len(combo.findall("item")) == len(combo_src.findall("item"))
      and len(combo.findall("item")) >= 2,
      (len(combo.findall("item")), len(combo_src.findall("item"))))
check("le combo libere est sorti du layout mais pas de son conteneur",
      ranges(combo, parents_de(ra)) is None
      and parents_de(ra)[combo].tag == "widget")
table = par_nom(ra, "tableNotes")
table_src = par_nom(lire(LAYOUT_UI), "tableNotes")
check("les <item> de cellules du tableau n'ont pas bouge",
      len(table.findall("item")) == len(table_src.findall("item"))
      and len(table.findall("item")) > 0,
      (len(table.findall("item")), len(table_src.findall("item"))))
check("les <column> et <row> du tableau sont conserves",
      (len(table.findall("column")), len(table.findall("row"))) ==
      (len(table_src.findall("column")), len(table_src.findall("row")))
      and len(table_src.findall("column")) > 0,
      (len(table.findall("column")), len(table.findall("row"))))
check("le tableau reste range", ranges(table, parents_de(ra)) is not None)
top.destroy()

# ── 9. journal : la bascule est annulable ────────────────────
print("=== 9. Annuler / retablir suivent la pose ===")
top, v = fenetre("pose-journal")
v.load_new_ui_file(LAYOUT_UI)
i = index_de(v, "btnQuitter")
geometrie_origine = props_de(v, "btnQuitter")["geometry"]
v._select(i)
v._bascule_position(i)
x, y, w, h = props_de(v, "btnQuitter")["geometry"]
v._on_click(ev(90, 90), i)
v._on_drag(ev(190, 140), i)
v._on_drag_end(ev(190, 140), i)
check("apres liberation + glisser, la position a bouge",
      props_de(v, "btnQuitter")["geometry"] == (x + 100, y + 50, w, h),
      props_de(v, "btnQuitter")["geometry"])
v.undo()
check("Annuler rend la position liberee d'avant le glisser",
      props_de(v, "btnQuitter")["geometry"] == (x, y, w, h)
      and props_de(v, "btnQuitter")["_pose"] == "libre",
      props_de(v, "btnQuitter"))
v.undo()
check("Annuler remet aussi la pose « layout »",
      props_de(v, "btnQuitter")["_pose"] == "layout"
      and props_de(v, "btnQuitter")["geometry"] == geometrie_origine,
      props_de(v, "btnQuitter"))
check("la pose annulee se voit dans le panneau (champs gris)",
      all(c.cget("state") == tk.DISABLED for c in champs_geo(v)),
      [c.cget("state") for c in champs_geo(v)])
v.redo()
check("Retablir reimpose la liberation",
      props_de(v, "btnQuitter")["_pose"] == "libre")
v.redo()
check("Retablir reimpose aussi le glisser",
      props_de(v, "btnQuitter")["geometry"] == (x + 100, y + 50, w, h),
      props_de(v, "btnQuitter")["geometry"])
top.destroy()

# ── 10. un widget ajoute rejoint la mise en page ─────────────
print("=== 10. les ajouts respectent la meme regle ===")
top, v = fenetre("pose-ajout")
v.load_new_ui_file(LAYOUT_UI)
n_items_avant = compte(LAYOUT_UI, "item")
v._add_widget("QPushButton")
nom_ajoute = v.widgets_data[-1][1]["name"]
check("un widget ajoute a un fichier range est dit range",
      v.widgets_data[-1][1]["_pose"] == "layout",
      v.widgets_data[-1][1]["_pose"])
out_aj = os.path.join(HERE, "pose_ajout.ui")
v._write_ui_file(out_aj)
ra = lire(out_aj)
el = par_nom(ra, nom_ajoute)
check("il est ecrit dans un <item>", ranges(el, parents_de(ra)) is not None,
      parents_de(ra)[el].tag)
check("il ne porte pas de geometry", not porte_geometry(el))
check("un <item> de plus", compte(out_aj, "item") == n_items_avant + 1,
      (compte(out_aj, "item"), n_items_avant + 1))
check("aucune violation apres ajout", violations(ra) == [], violations(ra))
top.destroy()

top, v = fenetre("pose-ajout-absolu")
v.load_new_ui_file(ABS_UI)
v._add_widget("QLabel")
nom2 = v.widgets_data[-1][1]["name"]
check("dans un fichier sans mise en page, l'ajout reste libre",
      v.widgets_data[-1][1]["_pose"] == "libre")
out_aa = os.path.join(HERE, "pose_ajout_absolu.ui")
v._write_ui_file(out_aa)
el2 = par_nom(lire(out_aa), nom2)
check("et porte bien sa geometry", porte_geometry(el2))
check("le panneau ne propose rien où le remettre",
      bouton_pose(v)[0] is None, bouton_pose(v)[1])
v._select(index_de(v, nom2))
check("et n'affiche pas de bouton pour un fichier sans layout",
      bouton_pose(v)[0] is None, bouton_pose(v)[1])
top.destroy()

# ── 11. la preuve par l'execution : loadUi ───────────────────
print("=== 11. ce que Qt affiche vraiment ===")
top, v = fenetre("pose-execution")
v.load_new_ui_file(LAYOUT_UI)
i_le = index_de(v, "lineEdit")
cible = props_de(v, "lineEdit")["geometry"]      # l'estimation, telle quelle
v._bascule_position(i_le)                        # sans glisser ni taper
check("liberer sans rien changer garde l'estimation pour valeur",
      props_de(v, "lineEdit")["geometry"] == cible,
      props_de(v, "lineEdit")["geometry"])
out_ex = os.path.join(HERE, "pose_execution.ui")
v._write_ui_file(out_ex)
taille_racine = tuple(v.root_geometry[2:])
noms_ranges = {p["name"]: p["geometry"] for _c, p in v.widgets_data
               if p.get("_pose") == "layout"}
top.destroy()

SONDE = r'''
import json, os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, %r)
from PyQt5 import QtWidgets, uic
app = QtWidgets.QApplication([])
w = uic.loadUi(%r)
w.show()
app.processEvents()
out = {"racine": [w.width(), w.height()], "vue": {}}
for n in %r:
    o = w.findChild(QtWidgets.QWidget, n)
    if o is not None:
        out["vue"][n] = [o.x(), o.y(), o.width(), o.height()]
w.btnQuitter.click()
app.processEvents()
out["ferme"] = not w.isVisible()
print(json.dumps(out))
'''
env = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")
p = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", "-c",
                    SONDE % (os.path.join(BUNDLE, "Lib", "site-packages"),
                             out_ex, sorted(noms_ranges) + ["lineEdit"])],
                   capture_output=True, text=True, env=env, timeout=180)
try:
    mesure = json.loads(p.stdout.strip().splitlines()[-1])
except Exception:
    mesure = {}
check("loadUi ouvre le fichier libere sans erreur", bool(mesure),
      (p.stdout[-300:], p.stderr[-300:]))
if mesure:
    vu = mesure.get("vue") or {}
    check("le widget libere est REELLEMENT a la position ecrite",
          tuple(vu.get("lineEdit") or ()) == tuple(cible),
          (vu.get("lineEdit"), cible))
    check("le fichier remanie garde ses <connections> (quit ferme la fenetre)",
          mesure.get("ferme") is True, mesure.get("ferme"))
    print("     lineEdit  ecrit=%s  vu=%s" % (tuple(cible), tuple(vu.get("lineEdit") or ())))
    print("     racine .ui=%s  vue=%s" % (taille_racine, mesure.get("racine")))
    a_cote = []
    for nom, estime in sorted(noms_ranges.items()):
        q = tuple(vu.get(nom) or ())
        print("     %-13s estime=%-18s Qt=%s" % (nom, str(tuple(estime)), str(q)))
        if q and q != tuple(estime):
            a_cote.append(nom)
    check("les widgets restes ranges ne suivent PAS l'estimation "
          "(d'ou l'honnetete du champ grise)", len(a_cote) >= 3, a_cote)

# ── 12. un fichier abîmé par la version precedente se retablit ─
print("=== 12. le fichier ecrit par la version precedente est reparable ===")
# herite_geometry_item.ui = ce que l'ancienne version produisait quand l'eleve
# glissait un widget range : une <geometry> SOUS un <item> de <layout>. Le
# fichier n'est pas illisible (Qt l'ouvre), mais il ment : le concepteur montre
# (123,77), l'execution montre autre chose. La regle 7a doit le retablir.
HERITE = os.path.join(HERE, "herite_geometry_item.ui")
RECT_HERITE = (123, 77, 200, 30)


def mesure_qt(chemin, noms):
    q = subprocess.run(
        [os.path.join(BUNDLE, "python.exe"), "-B", "-c",
         SONDE % (os.path.join(BUNDLE, "Lib", "site-packages"),
                  chemin, sorted(set(noms)))],
        capture_output=True, text=True, env=env, timeout=180)
    try:
        return json.loads(q.stdout.strip().splitlines()[-1])
    except Exception:
        return {}


def rect_ecrite(el):
    prop = el.find("property[@name='geometry']")
    if prop is None:
        return None
    return tuple(int(prop.findtext("rect/" + t))
                 for t in ("x", "y", "width", "height"))


check("le fichier abîmé est bien ce qu'on croit (geometry sous un <item>)",
      violations(lire(HERITE)) == [("lineEdit", "123")],
      violations(lire(HERITE)))
avant_reparation = mesure_qt(HERITE, ["lineEdit"])
check("le fichier abîmé s'ouvre neanmoins", bool(avant_reparation),
      avant_reparation)
if avant_reparation:
    vu_abime = (avant_reparation.get("vue") or {}).get("lineEdit")
    check("et Qt IGNORE la balise ecrite la : c'est le fosse que la version "
          "precedente laissait a l'eleve",
          tuple(vu_abime or ()) != RECT_HERITE, (vu_abime, RECT_HERITE))
    print("     abîme   ecrit=%s  vu=%s" % (RECT_HERITE, tuple(vu_abime or ())))

top, v = fenetre("pose-herite")
v.load_new_ui_file(HERITE)
i_h = index_de(v, "lineEdit")
p_h = props_de(v, "lineEdit")
check("la lecture appelle le widget « libre » : il porte sa propre geometry",
      p_h["_pose"] == "libre", p_h["_pose"])
check("l'empreinte raconte le FICHIER : la balise est deja consideree ecrite",
      tuple(p_h.get("_src", {}).get("geometry") or ()) == RECT_HERITE,
      p_h.get("_src", {}).get("geometry"))
check("le widget abîmé est le seul a se dire libre",
      nb(v, "libre") == 1 and nb(v, "layout") == len(v.widgets_data) - 1,
      {q["name"]: q["_pose"] for _c, q in v.widgets_data})
v._select(i_h)
check("les champs de position sont modifiables des l'ouverture",
      all(c.cget("state") != tk.DISABLED for c in champs_geo(v)),
      [c.cget("state") for c in champs_geo(v)])
check("le panneau propose de le rendre a la mise en page",
      etat_bouton(v) == REMETTRE, etat_bouton(v))
out_h = os.path.join(HERE, "herite_repare.ui")
n_items_abime = compte(HERITE, "item")
v._write_ui_file(out_h)
r_h = lire(out_h)
el_h = par_nom(r_h, "lineEdit")
check("ouvrir puis enregistrer, sans aucun geste, sort l'element de son <item>",
      ranges(el_h, parents_de(r_h)) is None, parents_de(r_h)[el_h].tag)
check("en conservant la position que l'eleve avait ecrite",
      rect_ecrite(el_h) == RECT_HERITE, rect_ecrite(el_h))
check("l'element repare n'apparait qu'une fois",
      doublons(r_h) == [] and noms_doublons(r_h) == [],
      (doublons(r_h), noms_doublons(r_h)))
check("aucune violation ni <item> vide dans le fichier repare",
      violations(r_h) == [] and items_vides(r_h) == [],
      (violations(r_h), items_vides(r_h)))
check("juste un <item> de moins que dans le fichier abîmé",
      compte(out_h, "item") == n_items_abime - 1,
      (compte(out_h, "item"), n_items_abime))
check("le widget repare est pose avant le <layout> de son conteneur",
      [c.tag for c in r_h.find("widget")].index("widget")
      < [c.tag for c in r_h.find("widget")].index("layout"),
      [c.tag for c in r_h.find("widget")])
apres_reparation = mesure_qt(out_h, ["lineEdit", "btnQuitter"])
check("le fichier repare s'ouvre", bool(apres_reparation), apres_reparation)
if apres_reparation:
    vu_repare = (apres_reparation.get("vue") or {}).get("lineEdit")
    check("et Qt pose DESORMAIS le widget exactement où le fichier le dit",
          tuple(vu_repare or ()) == RECT_HERITE, (vu_repare, RECT_HERITE))
    check("le reste du fichier fonctionne (quit ferme toujours)",
          apres_reparation.get("ferme") is True,
          apres_reparation.get("ferme"))
    print("     repare  ecrit=%s  vu=%s" % (RECT_HERITE,
                                            tuple(vu_repare or ())))
check("la vue du canevas et l'execution sont d'accord",
      tuple(p_h["geometry"]) == RECT_HERITE, p_h["geometry"])

# et l'eleve qui veut quand meme revenir au net, sans position absolue :
v._bascule_position(i_h)
check("« %s » sur le fichier abîmé le remet range" % REMETTRE,
      props_de(v, "lineEdit")["_pose"] == "layout")
out_n = os.path.join(HERE, "herite_net.ui")
v._write_ui_file(out_n)
r_n = lire(out_n)
el_n = par_nom(r_n, "lineEdit")
check("et le fichier obtenu ne porte plus aucune geometry heritee",
      ranges(el_n, parents_de(r_n)) is not None
      and not porte_geometry(el_n),
      (parents_de(r_n)[el_n].tag, porte_geometry(el_n)))
check("le fichier ramene au net ne viole rien",
      violations(r_n) == [] and items_vides(r_n) == [],
      (violations(r_n), items_vides(r_n)))
check("ses <item> sont revenus a ceux du gabarit",
      compte(out_n, "item") == compte(LAYOUT_UI, "item"),
      (compte(out_n, "item"), compte(LAYOUT_UI, "item")))
check("aucun doublon apres le trajet abîme -> libre -> range",
      doublons(r_n) == [] and noms_doublons(r_n) == [],
      (doublons(r_n), noms_doublons(r_n)))
top.destroy()

# ── 13. glisser reclasse la mise en page (tranche 7b) ────────
print("=== 13. dans une boite lineaire, glisser reclasse au lieu de deplacer ===")


def ordre_item(source):
    """Le contenu, dans l'ordre, des <item> de la boite verticale racine."""
    r = source if hasattr(source, "iter") else lire(source)
    lay = r.find("widget").find("layout")
    out = []
    for it in lay.findall("item"):
        w, l2, s = it.find("widget"), it.find("layout"), it.find("spacer")
        out.append(w.get("name") if w is not None else
                   ("layout:" + (l2.get("name") or "?")) if l2 is not None else
                   "spacer" if s is not None else "?")
    return out


def carte(e):
    return {p["name"]: (p.get("_groupe"), p.get("_axe"), p.get("_rang"))
            for _c, p in e.widgets_data}


def rangs(e, nom):
    freres = e._freres_mobiles(props_de(e, nom))
    return [p["name"] for p in freres], [p.get("_rang") for p in freres]


top, v = fenetre("reordre-lecture")
v.load_new_ui_file(LAYOUT_UI)
c13 = carte(v)
CLE_V = c13["label"][0]
corps_ordre = ast.get_source_segment(wc, meth["_applique_l_ordre"])
appels_ordre = [m.name for m in meth.values()
                if any(isinstance(n, ast.Attribute)
                       and n.attr == "_applique_l_ordre"
                       for n in ast.walk(m)) if m.name != "_applique_l_ordre"]
check("le reclassement n'a qu'un seul ecrivain, appele par la fusion",
      "_applique_l_ordre" in ast.get_source_segment(wc, meth["_merge_into_source"])
      and appels_ordre == ["_merge_into_source"], appels_ordre)
check("et l'ordre est applique APRES la pose : un widget libere n'a plus de rang",
      wc.find("self._applique_la_pose(root, by_uid)")
      < wc.find("self._applique_l_ordre(root, by_uid"),
      (wc.find("self._applique_la_pose(root, by_uid)"),
       wc.find("self._applique_l_ordre(root, by_uid")))
check("le geste « reordonner » n'ecrit la geometry nulle part dans _on_drag",
      sum(1 for n in ast.walk(meth["_on_drag"])
          if isinstance(n, ast.Assign)
          and any(isinstance(t, ast.Subscript)
                  and getattr(t.value, "id", "") == "props"
                  and getattr(t.slice, "value", None) == "geometry"
                  for t in n.targets)) == 1,
      ast.get_source_segment(wc, meth["_on_drag"]).count('props["geometry"] ='))
check("la permutation detache avant de reposer (le piege d'ElementTree)",
      "lay.remove(c)" in corps_ordre and "lay.append(c)" in corps_ordre,
      [l.strip() for l in corps_ordre.splitlines()
       if "remove" in l or "append" in l])
check("aucun reclassement ne passe par une boite de dialogue",
      "messagebox" not in ast.get_source_segment(wc, meth["_reclasse"])
      + ast.get_source_segment(wc, meth["_on_drag_end"]),
      "messagebox")
check("la lecture donne un rang, et lui seule",
      '"_rang"' in ast.get_source_segment(wc, meth["_parse_ui"])
      and '"_rang"' in ast.get_source_segment(wc, meth["_positionne_un_ajout"]),
      "")
check("la lecture retient dans quelle mise en page chaque widget est range",
      CLE_V is not None and c13["lineEdit"][0] == CLE_V
      and c13["groupNotes"][0] == CLE_V, c13)
check("et la place qu'il y occupe, dans l'ordre du fichier",
      [c13[n][2] for n in ("label", "lineEdit", "groupNotes")] == [0, 1, 2]
      and c13["label"][1] == "v",
      [c13[n] for n in ("label", "lineEdit", "groupNotes")])
check("une autre boite est un autre groupe, avec son axe",
      c13["btnQuitter"][0] == "bottomLayout|QHBoxLayout|"
      and c13["btnQuitter"][1] == "h" and c13["btnQuitter"][2] == 0,
      c13["btnQuitter"])
check("un widget range par un formulaire ou une grille n'a pas de rang a vendre",
      c13["labelClasse"] == (None, None, None)
      and c13["btnValider"] == (None, None, None),
      (c13["labelClasse"], c13["btnValider"]))
check("le geste promis se lit sur le modele",
      v._mode_glissement(props_de(v, "lineEdit")) == "reordonner"
      and v._mode_glissement(props_de(v, "labelClasse")) == "refus"
      and v._mode_glissement(props_de(v, "btnQuitter")) == "refus",
      {n: v._mode_glissement(props_de(v, n))
       for n in ("lineEdit", "labelClasse", "btnQuitter")})
freres_le, rangs_le = rangs(v, "lineEdit")
check("les freres mobiles sont les widgets ranges de la meme boite, tries",
      freres_le == ["label", "lineEdit", "groupNotes"] and rangs_le == [0, 1, 2],
      (freres_le, rangs_le))

le, i_le = props_de(v, "lineEdit"), index_de(v, "lineEdit")
x, y, w, h = le["geometry"]
pile_avant = len(v._undo_stack)
geom_avant = le["geometry"]
v._on_click(ev(x + 5, y + 5), i_le)
v._on_drag(ev(x + 5, y + 150), i_le)
check("pendant le geste, la position du modele n'est pas ecrite",
      le["geometry"] == geom_avant, le["geometry"])
check("le geste annonce une place, pas des coordonnees",
      "position 3 sur 3" in v._info_lbl.cget("text")
      and "mise en page" in v._info_lbl.cget("text"),
      v._info_lbl.cget("text"))
check("un trait marque la place ou le widget tomberait",
      v._repere is not None, v._repere)
check("rien n'est journalise tant que la souris roule",
      len(v._undo_stack) == pile_avant, (pile_avant, len(v._undo_stack)))
check("et rien n'est reclasse non plus",
      le["_rang"] == 1, le["_rang"])
v._on_drag_end(ev(x + 5, y + 150), i_le)
check("laché, le rang du modele suit la demande", le["_rang"] == 2, le["_rang"])
freres_apres, rangs_apres = rangs(v, "lineEdit")
check("l'ordre demande est rendu",
      freres_apres == ["label", "groupNotes", "lineEdit"]
      and rangs_apres == [0, 1, 2], (freres_apres, rangs_apres))
check("le geste n'a pas ecrit de position absolue",
      le["geometry"] != geom_avant and le["_pose"] == "layout"
      and le.get("_est") == le["geometry"], le["geometry"])
check("le reclassement coute exactement un coup d'Annuler",
      len(v._undo_stack) == pile_avant + 1, (pile_avant, len(v._undo_stack)))
check("la barre d'etat dit ce qui vient d'etre fait",
      "reclassé" in v._info_lbl.cget("text")
      and "lineEdit" in v._info_lbl.cget("text"), v._info_lbl.cget("text"))
check("le trait indicateur a ete retire", v._repere is None, v._repere)
check("les champs de position restent gris : la place n'appartient "
      "toujours pas au widget",
      all(c.cget("state") == tk.DISABLED for c in champs_geo(v)),
      [c.cget("state") for c in champs_geo(v)])

out_r = os.path.join(HERE, "reordre.ui")
v._write_ui_file(out_r)
r_r = lire(out_r)
check("le fichier reclasse ne porte AUCUNE geometry sous un <item>",
      violations(r_r) == [], violations(r_r))
check("la permutation ne touche que les places des widgets : <layout> imbrique "
      "et <spacer> gardent la leur",
      [o for o in ordre_item(r_r)
       if o.startswith("layout:") or o == "spacer"]
      == [o for o in ordre_item(LAYOUT_UI)
          if o.startswith("layout:") or o == "spacer"],
      (ordre_item(r_r), ordre_item(LAYOUT_UI)))
check("et l'ordre des widgets ranges est celui demande",
      [o for o in ordre_item(r_r) if not o.startswith("layout:")
       and o != "spacer"] == ["label", "groupNotes", "lineEdit"],
      ordre_item(r_r))
check("aucun <item> vide, aucun element ecrit deux fois",
      items_vides(r_r) == [] and doublons(r_r) == [],
      (items_vides(r_r), doublons(r_r)))
check("le nombre de <item> et de <widget> est inchange",
      compte(out_r, "item") == compte(LAYOUT_UI, "item")
      and compte(out_r, "widget") == compte(LAYOUT_UI, "widget"),
      (compte(out_r, "item"), compte(LAYOUT_UI, "item")))
out_r2 = os.path.join(HERE, "reordre2.ui")
v._write_ui_file(out_r2)
check("enregistrer deux fois reste identique",
      io.open(out_r, "rb").read() == io.open(out_r2, "rb").read(),
      "les deux ecritures different")
check("le fichier reclasse a toujours ses connections",
      len(list(r_r.iter("connection"))) == 1)

# le geste qui ne change rien ne doit rien couter
avant2 = len(v._undo_stack)
x2, y2, w2, h2 = le["geometry"]
v._on_click(ev(x2 + 5, y2 + 5), i_le)
v._on_drag(ev(x2 + 5, y2 + 3), i_le)
v._on_drag_end(ev(x2 + 5, y2 + 3), i_le)
check("laché a la meme place ne classe personne et ne coute rien",
      len(v._undo_stack) == avant2 and le["_rang"] == 2,
      (avant2, len(v._undo_stack), le["_rang"]))
v._resize_start(ev(x2, y2), i_le, "se")
v._resize_drag(ev(x2 + 90, y2 + 60), i_le, "se")
v._resize_end(ev(x2 + 90, y2 + 60), i_le)
check("redimensionner un widget range reste refuse, rang compris",
      len(v._undo_stack) == avant2 and le["_rang"] == 2
      and "mise en page" in v._info_lbl.cget("text"),
      (avant2, len(v._undo_stack), v._info_lbl.cget("text")))

# ── 13b. Annuler / Retablir suivent le reclassement ──────────
print("=== 13b. le reclassement est annulable, et le file net revient ===")
v.undo()
freres_annule, _ = rangs(v, "lineEdit")
check("Annuler rend l'ordre precedent",
      freres_annule == ["label", "lineEdit", "groupNotes"]
      and props_de(v, "lineEdit")["_rang"] == 1,
      (freres_annule, props_de(v, "lineEdit")["_rang"]))
out_annule = os.path.join(HERE, "reordre_annule.ui")
v._write_ui_file(out_annule)
top, v_net = fenetre("reordre-net")
v_net.load_new_ui_file(LAYOUT_UI)
out_net = os.path.join(HERE, "reordre_net.ui")
v_net._write_ui_file(out_net)
top.destroy()
check("le fichier rendu a l'ordre d'ouverture est identique a un fichier "
      "jamais touche",
      io.open(out_annule, "rb").read() == io.open(out_net, "rb").read(),
      "Annuler laisse une trace dans le fichier")
v.redo()
freres_retabli, _ = rangs(v, "lineEdit")
check("Retablir reclasse de nouveau",
      freres_retabli == ["label", "groupNotes", "lineEdit"]
      and props_de(v, "lineEdit")["_rang"] == 2,
      (freres_retabli, props_de(v, "lineEdit")["_rang"]))
out_retabli = os.path.join(HERE, "reordre_retabli.ui")
v._write_ui_file(out_retabli)
check("Retablir ecrit le meme fichier que le geste original",
      io.open(out_retabli, "rb").read() == io.open(out_r, "rb").read(),
      "le retablissement ne reproduit pas le geste")

# vers le haut, et au-dela du bord
le = props_de(v, "lineEdit")             # le journal a remplace le dictionnaire
x3, y3, w3, h3 = le["geometry"]
v._on_click(ev(x3 + 5, y3 + 5), i_le)
v._on_drag(ev(x3 + 5, y3 - 400), i_le)
check("viser avant le premier widget se peut aussi",
      v._glissement is not None and v._glissement[1] == 0, v._glissement)
v._on_drag_end(ev(x3 + 5, y3 - 400), i_le)
freres_haut, rangs_haut = rangs(v, "lineEdit")
check("et classe le widget en premier",
      freres_haut[0] == "lineEdit" and rangs_haut == [0, 1, 2],
      (freres_haut, rangs_haut))
v.undo()

# ── 13c. un widget AJOUTE se reclasse pareil ─────────────────
print("=== 13c. les ajouts ont un rang, et il est ecrit ===")
top, v = fenetre("reordre-ajout")
v.load_new_ui_file(LAYOUT_UI)
v._add_widget("QPushButton")
n_aj = v.widgets_data[-1][1]["name"]
p_aj = v.widgets_data[-1][1]
check("un widget ajoute rejoint le groupe de la boite racine, en derniere place",
      p_aj.get("_groupe") == carte(v)[n_aj][0] == CLE_V
      and p_aj["_axe"] == "v" and p_aj["_rang"] == 3, carte(v)[n_aj])
check("il est donc reclassable des sa creation",
      v._mode_glissement(p_aj) == "reordonner", v._mode_glissement(p_aj))
v._add_widget("QLabel")
n_aj2 = v.widgets_data[-1][1]["name"]
p_aj2 = v.widgets_data[-1][1]
check("deux ajouts ne se disputent pas la meme place",
      p_aj2["_rang"] == 4 and p_aj["_rang"] == 3
      and p_aj2["_groupe"] == p_aj["_groupe"], (p_aj["_rang"], p_aj2["_rang"]))
out_aj = os.path.join(HERE, "reordre_ajout.ui")
v._write_ui_file(out_aj)
check("l'enregistrement rend la place promise aux ajouts (pas de retour en "
      "fin de file)",
      ordre_item(out_aj)[-2:] == [n_aj, n_aj2], ordre_item(out_aj))
check("les rangs demandes sont denses et sans trou apres ecriture",
      [p["_rang"] for p in v._freres_mobiles(p_aj)] == [0, 1, 2, 3, 4],
      [p.get("_rang") for p in v._freres_mobiles(p_aj)])
x4, y4, w4, h4 = p_aj["geometry"]
i_aj = index_de(v, n_aj)
v._on_click(ev(x4 + 5, y4 + 5), i_aj)
v._on_drag(ev(x4 + 5, y4 - 200), i_aj)
v._on_drag_end(ev(x4 + 5, y4 - 200), i_aj)
freres_aj, _ = rangs(v, n_aj)
check("un ajout peut passer devant les widgets venus du fichier",
      freres_aj.index(n_aj) < freres_aj.index("groupNotes"), freres_aj)
v._write_ui_file(out_aj)
r_aj = lire(out_aj)
check("et le fichier dit la meme chose que le canevas",
      [o for o in ordre_item(r_aj)
       if not o.startswith("layout:") and o != "spacer"] == freres_aj,
      (ordre_item(r_aj), freres_aj))
check("toujours aucune violation avec des ajoutes reclASSES",
      violations(r_aj) == [] and items_vides(r_aj) == []
      and doublons(r_aj) == [],
      (violations(r_aj), items_vides(r_aj), doublons(r_aj)))
check("le fichier a gagne exactement deux <item>",
      compte(out_aj, "item") == compte(LAYOUT_UI, "item") + 2,
      (compte(out_aj, "item"), compte(LAYOUT_UI, "item") + 2))

top_rouv, v2 = fenetre("reordre-rouvert")
v2.load_new_ui_file(out_aj)
check("reouvert, le fichier raconte le meme ordre",
      [p["name"] for p in v2._freres_mobiles(props_de(v2, n_aj))] == freres_aj,
      [p["name"] for p in v2._freres_mobiles(props_de(v2, n_aj))])
check("les rangs reapparus sont denses",
      [p.get("_rang") for p in v2._freres_mobiles(props_de(v2, n_aj))]
      == [0, 1, 2, 3, 4],
      [p.get("_rang") for p in v2._freres_mobiles(props_de(v2, n_aj))])
out_rouv = os.path.join(HERE, "reordre_rouvert.ui")
v2._write_ui_file(out_rouv)
check("et la re-sauvegarde n'y change rien",
      io.open(out_rouv, "rb").read() == io.open(out_aj, "rb").read(),
      "rouvrir un fichier reclasse le remet ailleurs")
top.destroy()
v2._select(index_de(v2, "lineEdit"))
v2._bascule_position(index_de(v2, "lineEdit"))
check("liberer un widget range le sort du groupe",
      props_de(v2, "lineEdit").get("_groupe") is None
      and v2._mode_glissement(props_de(v2, "lineEdit")) == "libre",
      carte(v2)["lineEdit"])
out_libre = os.path.join(HERE, "reordre_libre.ui")
v2._write_ui_file(out_libre)
check("le fichier libere reste propre",
      violations(lire(out_libre)) == []
      and items_vides(lire(out_libre)) == []
      and doublons(lire(out_libre)) == [],
      (violations(lire(out_libre)), items_vides(lire(out_libre)),
       doublons(lire(out_libre))))
v2._bascule_position(index_de(v2, "lineEdit"))
check("remis en page, il reclaime une place sans que rien casse",
      props_de(v2, "lineEdit")["_pose"] == "layout"
      and v2._mode_glissement(props_de(v2, "lineEdit")) in
      ("reordonner", "refus"),
      (carte(v2)["lineEdit"], v2._mode_glissement(props_de(v2, "lineEdit"))))
check("et les rangs de la boite restent denses, sans doublon",
      sorted(q["_rang"] for _c, q in v2.widgets_data
             if q.get("_groupe") == carte(v2)["lineEdit"][0]
             and isinstance(q.get("_rang"), int))
      == [0, 1, 2, 3, 4],
      sorted([q.get("_rang") for _c, q in v2.widgets_data
              if q.get("_groupe") == carte(v2)["lineEdit"][0]]))
out_re = os.path.join(HERE, "reordre_remis.ui")
v2._write_ui_file(out_re)
r_re = lire(out_re)
check("le fichier remis au net ne porte ni geometry heritee ni item vide",
      violations(r_re) == [] and items_vides(r_re) == []
      and doublons(r_re) == [], (violations(r_re), items_vides(r_re),
                                 doublons(r_re)))
i_suppr = index_de(v2, n_aj)
v2._select(i_suppr)
n_items_avant_suppr = compte(out_re, "item")
v2._delete(i_suppr)
out_suppr = os.path.join(HERE, "reordre_suppr.ui")
v2._write_ui_file(out_suppr)
r_sup = lire(out_suppr)
check("supprimer un ajout reclassé ne laisse pas de <item> orphelin",
      items_vides(r_sup) == []
      and compte(out_suppr, "item") == n_items_avant_suppr - 1,
      (items_vides(r_sup), compte(out_suppr, "item"), n_items_avant_suppr))
gardes = [p["name"] for p in v2._freres_mobiles(props_de(v2, "lineEdit"))]
dans_le_fichier = [o for o in ordre_item(r_sup)
                   if not o.startswith("layout:") and o != "spacer"]
check("et l'ordre des survivants reste coherent entre canevas et fichier",
      [o for o in dans_le_fichier if o in gardes] == gardes,
      (ordre_item(r_sup), gardes))
check("le menage n'a rien casse : toujours aucune violation",
      violations(r_sup) == [] and doublons(r_sup) == [],
      (violations(r_sup), doublons(r_sup)))
top_rouv.destroy()

# ── 13e. et dans une boite HORIZONTALE ? ─────────────────────
print("=== 13e. une boite horizontale se reclasse sur son axe ===")
HBOX = os.path.join(HERE, "designer_hbox.ui")
top, vh = fenetre("reordre-hbox")
vh.load_new_ui_file(HBOX)
ch = carte(vh)
check("la lecture a vu une seule boite, horizontale, de trois rangs",
      len({ch[n][0] for n in ("btnUn", "btnDeux", "btnTrois")}) == 1
      and ch["btnUn"][0] and ch["btnUn"][1] == "h"
      and [ch[n][2] for n in ("btnUn", "btnDeux", "btnTrois")] == [0, 1, 2],
      ch)
deux = props_de(vh, "btnDeux")
xd, yd, wd, hd = deux["geometry"]
vh._on_click(ev(xd + 5, yd + 5), index_de(vh, "btnDeux"))
vh._on_drag(ev(xd + 5, yd + 400), index_de(vh, "btnDeux"))
check("glisser HORS de l'axe de la boite ne classe rien",
      vh._glissement is not None and vh._glissement[1] == 1, vh._glissement)
vh._on_drag(ev(xd + 260, yd + 400), index_de(vh, "btnDeux"))
check("le long de l'axe, la cible suit la main",
      vh._glissement[1] == 2 and "position 3 sur 3"
      in vh._info_lbl.cget("text"), (vh._glissement,
                                     vh._info_lbl.cget("text")))
check("et la position du modele n'est toujours pas ecrite",
      deux["geometry"] == (xd, yd, wd, hd), deux["geometry"])
vh._on_drag_end(ev(xd + 260, yd + 400), index_de(vh, "btnDeux"))
freres_h, rangs_h = rangs(vh, "btnDeux")
check("laché, la boite horizontale a change d'ordre",
      freres_h == ["btnUn", "btnTrois", "btnDeux"] and rangs_h == [0, 1, 2],
      (freres_h, rangs_h))
out_h = os.path.join(HERE, "reordre_hbox.ui")
vh._write_ui_file(out_h)
r_h = lire(out_h)
check("le fichier rend le meme ordre, sans une seule <geometry>",
      ordre_item(out_h) == ["btnUn", "btnTrois", "btnDeux"]
      and violations(r_h) == [], (ordre_item(out_h), violations(r_h)))
check("trois <item>, trois <widget>, rien de plus",
      compte(out_h, "item") == compte(HBOX, "item")
      and compte(out_h, "widget") == compte(HBOX, "widget"),
      (compte(out_h, "item"), compte(out_h, "widget")))
out_h2 = os.path.join(HERE, "reordre_hbox2.ui")
vh._write_ui_file(out_h2)
check("enregistrer deux fois reste identique",
      io.open(out_h, "rb").read() == io.open(out_h2, "rb").read())
top_h, vhr = fenetre("reordre-hbox-rouvert")
vhr.load_new_ui_file(out_h)
check("reouvert, l'ordre est lu tel quel",
      [p.get("_rang") for p in vhr._freres_mobiles(props_de(vhr, "btnDeux"))]
      == [0, 1, 2] and carte(vhr)["btnDeux"][2] == 2, carte(vhr))
top.destroy()
top_h.destroy()

# ── 13f. deux mises en page du meme nom : on ne devine pas ───
print("=== 13f. une clef ambigue est exclue, pas devinee ===")
AMBIGU = os.path.join(HERE, "hbox_ambigu.ui")
top, va = fenetre("reordre-ambigu")
va.load_new_ui_file(AMBIGU)
check("le fichier est lisible : les quatre boutons sont ranges",
      len(va.widgets_data) == 4 and nb(va, "layout") == 4,
      {p["name"]: p.get("_pose") for _c, p in va.widgets_data})
check("mais aucun n'a de groupe : la clef (nom, classe, hote) n'est pas unique",
      all(p.get("_groupe") is None and p.get("_rang") is None
          for _c, p in va.widgets_data),
      carte(va))
check("le geste promis est donc le refus de 7a, pas un reclassement au hasard",
      {n: va._mode_glissement(props_de(va, n))
       for n in ("btnA", "btnB", "btnC", "btnD")} ==
      {"btnA": "refus", "btnB": "refus", "btnC": "refus", "btnD": "refus"},
      {n: va._mode_glissement(props_de(va, n)) for n in ("btnA", "btnC")})
xa, ya, wa, ha = props_de(va, "btnA")["geometry"]
pile_amb = len(va._undo_stack)
va._select(index_de(va, "btnA"))
va._on_click(ev(xa + 5, ya + 5), index_de(va, "btnA"))
va._on_drag(ev(xa + 200, ya + 5), index_de(va, "btnA"))
va._on_drag_end(ev(xa + 200, ya + 5), index_de(va, "btnA"))
check("glisser ne deplace rien, ne reclasse rien et ne coute rien",
      props_de(va, "btnA")["geometry"] == (xa, ya, wa, ha)
      and len(va._undo_stack) == pile_amb
      and "mise en page" in va._info_lbl.cget("text"),
      (props_de(va, "btnA")["geometry"], pile_amb, len(va._undo_stack),
       va._info_lbl.cget("text")))
ordre_avant = [e.get("name") for e in lire(AMBIGU).iter("widget")]
out_amb = os.path.join(HERE, "reordre_ambigu.ui")
va._write_ui_file(out_amb)
r_amb = lire(out_amb)
check("l'enregistrement ne derange personne : meme ordre qu'a l'ouverture",
      [e.get("name") for e in r_amb.iter("widget")] == ordre_avant,
      ordre_item(out_amb))
check("et le fichier garde ses deux rangees sans violer la regle",
      ordre_item(r_amb) == ["layout:rowLayout", "layout:rowLayout"]
      and violations(r_amb) == [] and items_vides(r_amb) == []
      and doublons(r_amb) == [],
      (ordre_item(r_amb), violations(r_amb), items_vides(r_amb)))
top.destroy()

# ── 13d. la preuve par l'execution : Qt rend l'ordre reclasse ─
print("=== 13d. ce que Qt affiche apres un reclassement ===")
SONDE_ORDRE = r'''
import json, os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, %r)
from PyQt5 import QtWidgets, uic
app = QtWidgets.QApplication([])
w = uic.loadUi(%r)
w.show()
app.processEvents()
lay = w.layout()
out = []
for i in range(lay.count()):
    it = lay.itemAt(i)
    o = it.widget()
    if o is None:
        o = it.layout()
    out.append(None if o is None else (o.objectName() or o.metaObject().className()))
print(json.dumps(out))
'''
q = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", "-c",
                    SONDE_ORDRE % (os.path.join(BUNDLE, "Lib", "site-packages"),
                                   out_r)],
                   capture_output=True, text=True, env=env, timeout=180)
try:
    ordre_qt = json.loads(q.stdout.strip().splitlines()[-1])
except Exception:
    ordre_qt = []
check("Qt ouvre le fichier reclasse", bool(ordre_qt),
      (q.stdout[-200:], q.stderr[-200:]))
if ordre_qt:
    vu_mobiles = [o for o in ordre_qt
                  if o in ("label", "lineEdit", "groupNotes")]
    check("et range les widgets dans l'ordre que l'eleve a demande",
          vu_mobiles == ["label", "groupNotes", "lineEdit"],
          (ordre_qt, vu_mobiles))
    print("     Qt: %s" % ordre_qt)

qh = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", "-c",
                     SONDE_ORDRE % (os.path.join(BUNDLE, "Lib", "site-packages"),
                                    out_h)],
                    capture_output=True, text=True, env=env, timeout=180)
try:
    ordre_qt_h = json.loads(qh.stdout.strip().splitlines()[-1])
except Exception:
    ordre_qt_h = []
check("Qt rend de meme la boite horizontale reclassee",
      [o for o in ordre_qt_h if o] == ["btnUn", "btnTrois", "btnDeux"],
      (ordre_qt_h, qh.stderr[-200:]))
print("     Qt (hbox): %s" % ordre_qt_h)

print("=== bilan ===")
print("%d checks, %d echecs" % (N[0], len(FAILS)))
for f in FAILS:
    print("  FAIL " + f)
racine.destroy()
sys.exit(1 if FAILS else 0)
