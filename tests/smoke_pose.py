# -*- coding: utf-8 -*-
"""Smoke test 7a : la garde de la mise en page, sans Tk."""
import os, sys, types, xml.etree.ElementTree as ET

PLUGIN = r"C:\Users\Selmen\Desktop\projects\tunisiaschools"
BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
UIC = os.path.join(BUNDLE, "python.exe")
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, PLUGIN)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import thonny  # noqa: F401  — le vrai, celui du paquet Thonny
except Exception:
    th = types.ModuleType("thonny"); tl = types.ModuleType("thonny.languages")
    th.languages = tl; th.config = types.ModuleType("thonny.config")
    th.get_workbench = lambda: None
    sys.modules["thonny"] = th
    sys.modules["thonny.languages"] = tl
    sys.modules["thonny.config"] = th.config
    tl.tr = lambda s, *a, **k: s
    tl.set_language = lambda *a, **k: None

import UIViewer as U
assert os.path.samefile(U.__file__, os.path.join(PLUGIN, "UIViewer.py")), U.__file__
U.get_workbench = lambda: None
UiViewerPlugin = U.UiViewerPlugin

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "designer_layout.ui")


def vue():
    v = object.__new__(UiViewerPlugin)
    v.widgets_data = []
    v.root_geometry = (0, 0, 640, 480)
    v.root_title = "Form"
    v.root_widget_name = "Form"
    v.root_widget_class = "QWidget"
    v.ui_file = None
    v.widget_counter = 0
    v.selected_idx = None
    v._source_ui = None
    v._source_uids = []
    v._src_root = {}
    v._undo_stack, v._redo_stack, v._edit_sig, v._gesture = [], [], None, None
    return v


def geometries_sous_item(racine):
    """(nom, parent) de tout <widget> porteur d'une propriete geometry alors
    qu'il est range dans un <item> de <layout>."""
    parents = {c: p for p in racine.iter() for c in p}
    fautives = []
    for el in racine.iter("widget"):
        pere = parents.get(el)
        if pere is None or pere.tag != "item":
            continue
        gp = parents.get(pere)
        if gp is None or gp.tag != "layout":
            continue                      # entree de combo, cellule de tableau
        if el.find("property") is not None and \
           el.find("property[@name='geometry']") is not None:
            fautives.append((el.get("name"), el.find(
                "property[@name='geometry']").findtext("rect/x", "?")))
    return fautives


def orphelins(racine):
    """<item> de <layout> qui ne porte rien."""
    parents = {c: p for p in racine.iter() for c in p}
    vides = []
    for it in racine.iter("item"):
        p = parents.get(it)
        if p is None or p.tag != "layout":
            continue
        if not (it.find("widget") is not None or it.find("layout") is not None
                or it.find("spacer") is not None):
            vides.append(it)
    return vides


def lire(path):
    return ET.parse(path).getroot()


print("=== 1. la lecture sait qui est range ===")
v = vue()
v.widgets_data, info = v._parse_ui(FIX)
for cls, p in v.widgets_data:
    print("   %-14s %-16s pose=%-7s geo=%s" %
          (cls, p.get("name"), p.get("_pose"), p.get("geometry")))
n_layout = sum(1 for _c, p in v.widgets_data if p.get("_pose") == "layout")
n_libre = sum(1 for _c, p in v.widgets_data if p.get("_pose") == "libre")
print("   ranges=%d libres=%d" % (n_layout, n_libre))

print("=== 2. enregistrer sans rien toucher : rien de neuf sous un <item> ===")
out1 = os.path.join(os.path.dirname(FIX), "smoke_out1.ui")
v._write_ui_file(out1)
r1 = lire(out1)
print("   geometries sous item :", geometries_sous_item(r1))
print("   items vides          :", len(orphelins(r1)))
print("   nb <item>=%d <layout>=%d" %
      (len(list(r1.iter("item"))), len(list(r1.iter("layout")))))

print("=== 3. idempotence : reecrire le modele ne change rien ===")
out2 = os.path.join(os.path.dirname(FIX), "smoke_out2.ui")
v._write_ui_file(out2)
a = open(out1, "rb").read()
b = open(out2, "rb").read()
print("   identiques :", a == b, len(a), len(b))

print("=== 4. liberer la position dun widget range ===")
idx = next(i for i, (_c, p) in enumerate(v.widgets_data)
           if p.get("_pose") == "layout")
nom = v.widgets_data[idx][1]["name"]
v.widgets_data[idx][1]["_pose"] = "libre"
v.widgets_data[idx][1]["geometry"] = (123, 45, 60, 25)
out3 = os.path.join(os.path.dirname(FIX), "smoke_out3.ui")
v._write_ui_file(out3)
r3 = lire(out3)
parents3 = {c: p for p in r3.iter() for c in p}
el = next(e for e in r3.iter("widget") if e.get("name") == nom)
p = parents3[el]
g = el.find("property[@name='geometry']")
print("   %s : parent=%s geometry=%s" %
      (nom, p.tag, None if g is None else
       [g.findtext("rect/" + t) for t in ("x", "y", "width", "height")]))
print("   geometries sous item :", geometries_sous_item(r3))
print("   items vides          :", len(orphelins(r3)))

print("=== 5. remettre tous les widgets dans la mise en page ===")
for _c, pr in v.widgets_data:
    pr["_pose"] = "layout"
out4 = os.path.join(os.path.dirname(FIX), "smoke_out4.ui")
v._write_ui_file(out4)
r4 = lire(out4)
libres = [e.get("name") for e in list(r4.iter("widget"))[1:]
          if e.find("property[@name='geometry']") is not None]
print("   %d widgets, %d items, %d geometries sous item, %d items vides" %
      (len(list(r4.iter("widget"))), len(list(r4.iter("item"))),
       len(geometries_sous_item(r4)), len(orphelins(r4))))
print("   porteuses de geometry :", libres)

print("=== 6. rouvrir le fichier libere, puis tout remettre en page ===")
v2 = vue()
v2.widgets_data, _i2 = v2._parse_ui(out3)
print("   poses :", dict(((p["name"], p["_pose"]) for _c, p in v2.widgets_data)))
for _c, pr in v2.widgets_data:
    pr["_pose"] = "layout"
out5 = os.path.join(os.path.dirname(FIX), "smoke_out5.ui")
v2._write_ui_file(out5)
r5 = lire(out5)
print("   geometries sous item :", geometries_sous_item(r5))
print("   widgets porteurs de geometry :",
      [e.get("name") for e in list(r5.iter("widget"))[1:]
       if e.find("property[@name='geometry']") is not None])
print("   items vides : %d   <item>=%d <layout>=%d" %
      (len(orphelins(r5)), len(list(r5.iter("item"))),
       len(list(r5.iter("layout")))))

print("=== 7. loadUi des trois etats ===")
for f in (out1, out3, out4):
    print("   ", os.path.basename(f))
