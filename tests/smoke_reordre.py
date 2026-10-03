# -*- coding: utf-8 -*-
"""Fumee 7b : un glisser reclasse la mise en page, sans ecrire de <geometry>."""
import io
import os
import subprocess
import sys
import tkinter as tk
import types

import chemins

BUNDLE = chemins.BUNDLE
PLUGIN = chemins.PAQUET
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

print("=== ce que la lecture dit ===")
for _c, p in v.widgets_data:
    print("   %-13s pose=%-7s axe=%-5s rang=%s groupe=%s"
          % (p["name"], p.get("_pose"), p.get("_axe"), p.get("_rang"),
             p.get("_groupe")))

print("=== mode de glisser ===")
for _c, p in v.widgets_data:
    print("   %-13s %s" % (p["name"], v._mode_glissement(p)))


def ev(x, y):
    return types.SimpleNamespace(x=x, y=y, x_root=x, y_root=y,
                                 widget=None, num=1, delta=0)


def index_de(nom):
    return next(i for i, (_c, p) in enumerate(v.widgets_data)
                if p["name"] == nom)


def props_de(nom):
    return v.widgets_data[index_de(nom)][1]


i_le = index_de("lineEdit")
le = props_de("lineEdit")
x, y, w, h = le["geometry"]
print("\n=== glisser lineEdit vers le bas (au-dela de groupNotes) ===")
print("   de %s" % (le["geometry"],))
v._on_click(ev(x + 5, y + 5), i_le)
v._on_drag(ev(x + 5, y + 150), i_le)
print("   info: %s" % v._info_lbl.cget("text"))
v._on_drag_end(ev(x + 5, y + 150), i_le)
print("   apres: %s  rang=%s" % (le["geometry"], le["_rang"]))
print("   ordre modele:", [p["name"] for p in v._freres_mobiles(le)])

out = os.path.join(HERE, "reordre_smoke.ui")
v._write_ui_file(out)
import xml.etree.ElementTree as ET                                  # noqa: E702
r = ET.parse(out).getroot()
form = r.find("widget")
lay = form.find("layout")
print("   ordre fichier:", [(it.find("widget").get("name")
                            if it.find("widget") is not None
                            else (it.find("layout").get("name")
                                  if it.find("layout") is not None else "?"))
                           for it in lay.findall("item")])
sous_item = [(e.get("name"),) for e in r.iter("widget")
             if e.find("property[@name='geometry']") is not None
             and r.find("widget") is not e]
print("   geometry sous un item ?", sous_item)
print("   <item>:", len(list(r.iter("item"))), " <widget>:",
      len(list(r.iter("widget"))))

print("=== idempotence ===")
a = os.path.join(HERE, "reordre_a.ui")
b = os.path.join(HERE, "reordre_b.ui")
v._write_ui_file(a)
v._write_ui_file(b)
print("   identiques:", io.open(a, "rb").read() == io.open(b, "rb").read())

print("=== journal ===")
n0 = len(v._undo_stack)
v.undo()
print("   apres Annuler:", [p["name"] for p in v._freres_mobiles(
    props_de("lineEdit"))], "pile", n0, "->", len(v._undo_stack))
v.redo()
print("   apres Retablir:", [p["name"] for p in v._freres_mobiles(
    props_de("lineEdit"))])
top.destroy()

print("=== loadUi ===")
SONDE = r'''
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
    o = lay.itemAt(i).widget()
    out.append(None if o is None else (o.objectName(), o.x(), o.y()))
print(json.dumps(out))
'''
env = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen")
q = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", "-c",
                    SONDE % (os.path.join(BUNDLE, "Lib", "site-packages"), out)],
                   capture_output=True, text=True, env=env, timeout=180)
print("   ", q.stdout.strip()[-400:], q.stderr.strip()[-300:])
root.destroy()
