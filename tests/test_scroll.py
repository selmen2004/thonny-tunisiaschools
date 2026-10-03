"""Item 5 — la zone defilable du canevas de conception n'a qu'un seul maitre.

Le probleme, tel qu'il a ete MESURE (probe_scroll.py) et non devine : deux
ecrivains se disputaient canvas["scrollregion"].

  • _refresh()   posait (0, 0, largeur+44, hauteur+44) — la region du document.
  • _on_canvas_resize, lie a <Configure> sur le canevas, reposait
    canvas.bbox("all") — la region calculee sur la taille REALISEE du cadre.

Les deux se contredisaient dans les deux sens, et le gagnant dependait de
l'ordre des evenements :

  1. viewer neuf, fenetre realisee  -> sr '20 20 25 25'   (le cadre demande 1 px)
  2. apres _refresh (640x480)       -> sr '0 0 684 524', bbox (20,20,668,508)
  3. apres un VRAI redimensionnement -> sr '20 20 668 508' : la marge est partie
  4. canevas vide                    -> bbox("all") vaut None, et
                                        configure(scrollregion=None) laisse la
                                        propriete a '' — plus de zone defilable.

Consequence pour l'eleve : des qu'il reduisait la fenetre Thonny, le coin bas
droit de sa forme sortait de la zone defilable et il ne pouvait plus attraper
les widgets qu'il y avait poses.

La regle verifiee ici : bbox("all") ne decide JAMAIS de la zone du canevas de
conception (il reste correct pour le panneau de proprietes, ou le cadre est
bien plein de champs a faire defiler). La zone = document + marge, et rien
d'autre.
"""
import ast
import io
import os
import sys
import tkinter as tk
from tkinter import Tk

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
PLUGIN = r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import UIViewer                                          # noqa: E402
from UIViewer import UiViewerPlugin                      # noqa: E402

SOURCE = io.open(os.path.join(PLUGIN, "UIViewer.py"), encoding="utf-8").read()
HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT_UI = os.path.join(HERE, "designer_layout.ui")

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

MARGE = 44          # 20 px de position + l'ombre decalee de 4 px + 20


def zone(v):
    """canvas["scrollregion"] en quatre entiers."""
    return tuple(int(float(x)) for x in str(v.canvas.cget("scrollregion")).split())


def attendu(v):
    _, _, rw, rh = v.root_geometry
    return (0, 0, rw + MARGE, rh + MARGE)


def bbox(v):
    return v.canvas.bbox("all")


def fenetre(nom):
    top = tk.Toplevel(racine)
    top.title(nom)
    top.geometry("900x620+40+40")
    top.update()
    v = UiViewerPlugin(top)
    v.pack(fill=tk.BOTH, expand=True)
    top.update()
    return top, v


racine = Tk()
racine.withdraw()

# ── 1. la source n'a qu'un seul ecrivain ────────────────────
print("=== 1. un seul ecrivain dans la source ===")
check("la source analysee est bien le fichier du plugin"
      " (pas le lien symbolique, pas un .pyc)",
      os.path.samefile(os.path.abspath(UIViewer.__file__),
                       os.path.join(PLUGIN, "UIViewer.py")),
      UIViewer.__file__)
arbre = ast.parse(SOURCE)
classe = next(n for n in ast.walk(arbre)
              if isinstance(n, ast.ClassDef) and n.name == "UiViewerPlugin")

methodes = {n.name for n in classe.body if isinstance(n, ast.FunctionDef)}
check("_on_canvas_resize a disparu de la classe",
      "_on_canvas_resize" not in methodes, sorted(m for m in methodes if "canvas" in m))
check("_zone_defilable existe", "_zone_defilable" in methodes)


def ecrivains_scrollregion(noeud):
    """Toutes les ecritures de scrollregion, avec celui qui les passe."""
    sorts = []
    for n in ast.walk(noeud):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "configure":
            for kw in n.keywords:
                if kw.arg == "scrollregion":
                    destinataire = ast.unparse(n.func.value)
                    valeur = ast.unparse(kw.value)
                    ligne = getattr(n, "lineno", 0)
                    sorts.append((destinataire, valeur, ligne))
        if isinstance(n, ast.Assign):
            for c in n.targets:
                if isinstance(c, ast.Subscript) and isinstance(c.slice, ast.Constant) \
                        and c.slice.value == "scrollregion":
                    sorts.append((ast.unparse(c.value), ast.unparse(n.value), n.lineno))
    return sorts


design = [e for e in ecrivains_scrollregion(classe) if e[0] == "self.canvas"]
props = [e for e in ecrivains_scrollregion(classe) if "prop_canvas" in e[0]]
check("le canevas de conception a UN seul ecrivain", len(design) == 1, design)
check("cet ecrivain est dans _refresh", design and design[0][2] > 1480, design)
check("il ecrit self._zone_defilable()",
      design and design[0][1] == "self._zone_defilable()", design)
check("bbox(\"all\") n'est plus jamais passe au canevas de conception",
      all("bbox" not in e[1] for e in design), design)
check("le panneau de proprietes garde sa recette (hors scope)",
      len(props) == 1 and "bbox" in props[0][1], props)
check("aucun <Configure> n'est lie sur le canevas de conception",
      'self.canvas.bind("<Configure>"' not in SOURCE,
      [l for l in SOURCE.splitlines() if 'self.canvas.bind("<Conf' in l])

init = next(n for n in classe.body
            if isinstance(n, ast.FunctionDef) and n.name == "__init__")
appelle_refresh = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr == "_refresh" for n in ast.walk(init))
check("__init__ peint le document des la construction", appelle_refresh)

# ── 2. la zone existe des la premiere peinture ──────────────
print("=== 2. premiere peinture ===")
top1, v = fenetre("concepteur")
vide = (0, 0, 640 + MARGE, 480 + MARGE)
check("viewer neuf realise : la zone couvre deja la forme 640x480",
      zone(v) == vide, (zone(v), vide))
check("elle commence au coin haut gauche", zone(v)[:2] == (0, 0), zone(v))
b = bbox(v)
print("    bbox(\"all\") a cet instant :", b)
check("bbox(\"all\") ne part jamais de (0, 0) : il ne peut pas decrire la zone",
      b is not None and b[:2] == (20, 20), b)
check("bbox(\"all\") rend toujours 16 px de moins que le document : la marge"
      " disparaitrait a chaque Configure",
      b is not None and b[2] == zone(v)[2] - 16 and b[3] == zone(v)[3] - 16,
      (b, zone(v)))
check("la zone ne le suit pas", zone(v)[2] != b[2], (zone(v), b))

# L'effondrement mesure avant la correction : un cadre pose sur un canevas,
# tant que personne ne lui a impose sa taille, ne demande que 1 px.
c_piege = tk.Canvas(racine, width=300, height=200)
c_piege.create_window(20, 20, anchor="nw", window=tk.Frame(c_piege, bg="#fff"))
c_piege.update_idletasks()
petit = c_piege.bbox("all")
print("    bbox d'un cadre non dimensionne :", petit)
check("un cadre non dimensionne effondre bbox a quelques pixels"
      " (le '20 20 25 25' du sonde)",
      petit is not None and petit[2] - petit[0] < 30 and petit[3] - petit[1] < 30,
      petit)
c_piege.destroy()

top0 = tk.Toplevel(racine)
top0.title("jamais realise")
v_nul = UiViewerPlugin(top0)      # pas de pack, pas d'update : vue retiree
v_nul.pack(fill=tk.BOTH, expand=True)
check("vue jamais realisee a aussi sa zone (Thonny cree la vue avant de l'afficher)",
      zone(v_nul) == vide, zone(v_nul))
check("_zone_defilable ne depend pas de l'affichage",
      v_nul._zone_defilable() == vide, v_nul._zone_defilable())
top0.destroy()

# ── 3. redimensionner la fenetre ne doit RIEN changer ───────
print("=== 3. l'eleve reduit la fenetre Thonny ===")
v._add_widget("QPushButton")
v._refresh()
avant = zone(v)
for geo in ("520x360+60+60", "1400x900+20+20", "300x220+80+80", "900x620+40+40"):
    top1.geometry(geo)
    top1.update()
    print("    viewport %-12s -> scrollregion %s" % (geo, str(zone(v))))
check("la zone a survive aux quatre redimensionnements", zone(v) == avant,
      (avant, zone(v)))
check("elle vaut toujours document + marge", zone(v) == attendu(v), (zone(v), attendu(v)))

print("=== 3b. temoin negatif : l'ancien handler, rejoue a l'identique ===")
top2, v_old = fenetre("témoin")
v_old._add_widget("QPushButton")


def ancien_handler(event):
    v_old.canvas.configure(scrollregion=v_old.canvas.bbox("all"))


v_old.canvas.bind("<Configure>", ancien_handler)
v_old.canvas.configure(scrollregion=v_old.canvas.bbox("all"))
region_initiale = zone(v_old)
top2.geometry("520x360+60+60")
top2.update()
apres = zone(v_old)
print("    avant %s / apres %s (attendu %s)" % (region_initiale, apres, attendu(v_old)))
check("le vieux handler detruit bien la marge : le piege est reel",
      apres != attendu(v_old), (apres, attendu(v_old)))
check("et le nouveau code ne bouge pas au meme geste",
      zone(v) == attendu(v), zone(v))
top2.destroy()

# ── 4. la zone contient toujours le contenu ─────────────────
print("=== 4. la zone englobe le document, dans chaque etat ===")


def englobe(v, titre):
    sr = zone(v)
    b = bbox(v)
    ok = sr[:2] == (0, 0) and b is not None and sr[2] >= b[2] and sr[3] >= b[3]
    check("%s : scrollregion %s contient bbox %s" % (titre, sr, b), ok)
    check("%s : identique a document + marge" % titre, sr == attendu(v),
          (sr, attendu(v)))


englobe(v, "forme vide avec un bouton")
v.root_geometry = (0, 0, 400, 300)
v._refresh()
englobe(v, "racine ramenee a 400x300")
v.root_geometry = (0, 0, 1200, 900)
v._refresh()
englobe(v, "racine agrandie a 1200x900")

# un widget colle au coin bas droit : il doit rester atteignable
v.widgets_data[0][1]["geometry"] = (1160, 860, 40, 40)
v._refresh()
englobe(v, "widget colle au coin bas droit")
sr = zone(v)
w = v.canvas.winfo_width()
print("    canevas %dx%d, zone %s -> le coin du document est a %d px, "
      "donc hors champ sans zone defilable" % (v.canvas.winfo_width(),
                                               v.canvas.winfo_height(), sr, sr[2]))
v.canvas.xview_moveto(1.0)
v.canvas.yview_moveto(1.0)
check("defiler jusqu'a la fin du document fonctionne",
      v.canvas.xview()[1] == 1.0 and v.canvas.yview()[1] == 1.0,
      (v.canvas.xview(), v.canvas.yview()))

# ── 5. ouvrir / nouveau : la zone suit le document ──────────
print("=== 5. ouvrir un fichier, puis Nouveau ===")
v.widgets_data[:] = []
v.root_geometry = (0, 0, 640, 480)
v.load_new_ui_file(LAYOUT_UI)
sr_ouvert = zone(v)
print("    %s -> racine %s, zone %s" % (os.path.basename(LAYOUT_UI),
                                         v.root_geometry, sr_ouvert))
check("la zone vient du fichier ouvert", sr_ouvert == attendu(v),
      (sr_ouvert, attendu(v)))
check("le fichier de test fait bien 400x300", v.root_geometry == (0, 0, 400, 300),
      v.root_geometry)
top1.geometry("640x480+50+50")
top1.update()
check("ouvrir puis reduire la fenetre : la zone ne budge pas",
      zone(v) == sr_ouvert, (zone(v), sr_ouvert))
englobe(v, "fichier de l'eleve charge")

v._new()
check("Nouveau remet la zone aux dimensions par defaut",
      zone(v) == vide, (zone(v), vide))
check("Nouveau ne laisse pas la propriete a ''", str(v.canvas.cget("scrollregion")) != "",
      repr(v.canvas.cget("scrollregion")))

# ── 6. le piege du canevas vide ─────────────────────────────
print("=== 6. bbox(\"all\") ne peut pas servir de verite ===")
c_vide = tk.Canvas(racine, width=200, height=100)
check("un canevas sans objet rend bbox None (l'ancien code ecrivait '')",
      c_vide.bbox("all") is None, c_vide.bbox("all"))
c_vide.configure(scrollregion=c_vide.bbox("all"))
check("configure(scrollregion=None) laisse la propriete vide",
      str(c_vide.cget("scrollregion")) == "", repr(str(c_vide.cget("scrollregion"))))
check("notre helper ne rend jamais une valeur vide",
      len(v._zone_defilable()) == 4 and all(
          isinstance(x, int) for x in v._zone_defilable()), v._zone_defilable())
c_vide.destroy()

# ── 7. Annuler / retablir garde la meme regle ───────────────
print("=== 7. le journal ne reinvite pas bbox(\"all\") ===")
v._add_widget("QPushButton")
v._add_widget("QLabel")
zone_apres_ajouts = zone(v)
v.undo()
check("apres Annuler : zone = document + marge", zone(v) == attendu(v),
      (zone(v), attendu(v)))
v.redo()
check("apres Retablir : idem", zone(v) == zone_apres_ajouts,
      (zone(v), zone_apres_ajouts))
top1.geometry("420x300+70+70")
top1.update()
check("Annuler puis reduire : toujours la zone du document",
      zone(v) == zone_apres_ajouts, zone(v))

# ── 8. deux vues cote a cote ────────────────────────────────
print("=== 8. deux concepteurs ouverts en meme temps ===")
top_a, va = fenetre("vue A")
top_b, vb = fenetre("vue B")
va.load_new_ui_file(LAYOUT_UI)
vb.root_geometry = (0, 0, 300, 200)
vb._refresh()
check("chacune sa zone : A", zone(va) == attendu(va), (zone(va), attendu(va)))
check("chacune sa zone : B", zone(vb) == attendu(vb), (zone(vb), attendu(vb)))
top_a.geometry("400x300+20+20")
top_a.update()
top_b.geometry("1200x800+10+10")
top_b.update()
check("A reduite, B agrandie : A garde sa zone", zone(va) == attendu(va), zone(va))
check("B garde la sienne", zone(vb) == attendu(vb), zone(vb))
check("les deux zones sont bien differentes (pas de partage d'etat)",
      zone(va) != zone(vb), (zone(va), zone(vb)))
top_a.destroy()
top_b.destroy()

print("\n%d controles, %d echecs" % (N[0], len(FAILS)))
for f in FAILS:
    print("  ECHEC " + f)
sys.exit(1 if FAILS else 0)
