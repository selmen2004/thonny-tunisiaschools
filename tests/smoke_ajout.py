# -*- coding: utf-8 -*-
"""Fumee 7b (2) : un widget AJOUTE peut etre reclassé, et n'est pas remis en fin
de file a l'enregistrement."""
import io
import os
import sys
import tkinter as tk
import types
import xml.etree.ElementTree as ET

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
PLUGIN = r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import UIViewer                                          # noqa: E402
from UIViewer import UiViewerPlugin                      # noqa: E402


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

LAYOUT_UI = os.path.join(HERE, "designer_layout.ui")
root = tk.Tk()
root.withdraw()
top = tk.Toplevel(root)
top.geometry("980x680+30+30")
top.update()
v = UiViewerPlugin(top)
v.pack(fill=tk.BOTH, expand=True)
top.update()
v.load_new_ui_file(LAYOUT_UI)


def ev(x, y):
    return types.SimpleNamespace(x=x, y=y, x_root=x, y_root=y,
                                 widget=None, num=1, delta=0)


def index_de(nom):
    return next(i for i, (_c, p) in enumerate(v.widgets_data)
                if p["name"] == nom)


def props_de(nom):
    return v.widgets_data[index_de(nom)][1]


def ordre_fichier(chemin):
    r = ET.parse(chemin).getroot()
    lay = r.find("widget").find("layout")
    out = []
    for it in lay.findall("item"):
        w = it.find("widget")
        l2 = it.find("layout")
        s = it.find("spacer")
        out.append(w.get("name") if w is not None else
                   ("layout:" + (l2.get("name") or "")) if l2 is not None else
                   "spacer" if s is not None else "?")
    return out


def cart(e):
    return {p["name"]: (p.get("_groupe"), p.get("_axe"), p.get("_rang"))
            for _c, p in e.widgets_data}


print("=== ajout 1 ===")
v._add_widget("QPushButton")
n1 = v.widgets_data[-1][1]["name"]
p1 = v.widgets_data[-1][1]
print("   %s pose=%s groupe=%s axe=%s rang=%s mode=%s"
      % (n1, p1.get("_pose"), p1.get("_groupe"), p1.get("_axe"),
         p1.get("_rang"), v._mode_glissement(p1)))
print("   freres:", [p["name"] for p in v._freres_mobiles(p1)])

out = os.path.join(HERE, "ajout_smoke.ui")
v._write_ui_file(out)
print("   ordre fichier:", ordre_fichier(out))
print("   apres ecriture:", p1.get("_rang"), cart(v).get(n1))

print("=== ajout 2, puis reclasser les deux ===")
v._add_widget("QLabel")
n2 = v.widgets_data[-1][1]["name"]
p2 = v.widgets_data[-1][1]
print("   %s rang=%s groupe=%s (identique a %s ? %s)"
      % (n2, p2.get("_rang"), p2.get("_groupe"), n1,
         p2.get("_groupe") == p1.get("_groupe")))
v._write_ui_file(out)
print("   ordre apres ajout 2:", ordre_fichier(out))
print("   rangs:", cart(v).get(n1), cart(v).get(n2))

# lineEdit (rang 1) vers la fin : les ajouts doivent suivre l'ordre demande
le = props_de("lineEdit")
x, y, w, h = le["geometry"]
v._on_click(ev(x + 5, y + 5), index_de("lineEdit"))
v._on_drag(ev(x + 5, y + 260), index_de("lineEdit"))
print("   info:", v._info_lbl.cget("text"))
v._on_drag_end(ev(x + 5, y + 260), index_de("lineEdit"))
print("   ordre modele:", [p["name"] for p in v._freres_mobiles(le)])
v._write_ui_file(out)
print("   ordre fichier:", ordre_fichier(out))
print("   rangs:", {n: cart(v)[n] for n in (n1, n2, "lineEdit")})

# reclasser un ajout par-dessus un widget du fichier
a1 = props_de(n1)
x, y, w, h = a1["geometry"]
i1 = index_de(n1)
avant = len(v._undo_stack)
v._on_click(ev(x + 5, y + 5), i1)
v._on_drag(ev(x + 5, y - 60), i1)
print("   info ajout:", v._info_lbl.cget("text"))
v._on_drag_end(ev(x + 5, y - 60), i1)
print("   ordre modele:", [p["name"] for p in v._freres_mobiles(a1)])
print("   undo cout:", avant, "->", len(v._undo_stack))
v._write_ui_file(out)
print("   ordre fichier:", ordre_fichier(out))
r = ET.parse(out).getroot()
par = {c: p for p in r.iter() for c in p}


def range_dans_item(el):
    it = par.get(el)
    return it is not None and it.tag == "item" and par.get(it) is not None \
        and par[it].tag == "layout"


print("   violation (geometry sous un item):",
      [e.get("name") for e in r.iter("widget")
       if e.find("property[@name='geometry']") is not None
       and range_dans_item(e)])

print("=== idempotence ===")
a = os.path.join(HERE, "ajout_a.ui")
b = os.path.join(HERE, "ajout_b.ui")
v._write_ui_file(a)
v._write_ui_file(b)
print("   identiques:", io.open(a, "rb").read() == io.open(b, "rb").read())

print("=== reouverture ===")
top2, v2 = None, None
t2 = tk.Toplevel(root)
t2.geometry("980x680+30+30")
t2.update()
v2 = UiViewerPlugin(t2)
v2.pack(fill=tk.BOTH, expand=True)
t2.update()
v2.load_new_ui_file(out)
print("   ordre modele:", [p["name"] for _c, p in v2.widgets_data])
print("   rangs:", cart(v2))
c = os.path.join(HERE, "ajout_c.ui")
v2._write_ui_file(c)
print("   re-sauvegarde identique:",
      io.open(c, "rb").read() == io.open(out, "rb").read())
print("   <item>:", len(list(ET.parse(c).getroot().iter("item"))),
      "<widget>:", len(list(ET.parse(c).getroot().iter("widget"))))
top.destroy()
t2.destroy()
root.destroy()
