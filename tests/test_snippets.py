"""Les lignes que le plugin suggere doivent s'executer une fois collees.

Avant ce correctif, le panneau METHODES et le menu PyQt5 inseraient des
modeles a blancs : windows.x.critical(p,titre,msg), setText(texte),
clicked.connect(fn)... Le premier lancer echouait en NameError (ou en
TypeError pour setText sans argument). Ce test execute reellement chaque
ligne proposee contre de vrais widgets PyQt5.
"""
import ast
import os
import sys
import types

BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
sys.path.insert(0, r"C:\Users\Selmen\Desktop\projects\tunisiaschools")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import UIViewer                                    # noqa: E402
from UIViewer import UiViewerPlugin, WIDGET_METHODS  # noqa: E402

FAILS = []
N = [0]


def check(label, cond, detail=""):
    N[0] += 1
    if not cond:
        FAILS.append("%s %s" % (label, detail))
    print("%s %s%s" % ("OK  " if cond else "FAIL", label,
                       (" -> " + str(detail)) if detail else ""))


print("=== 1. forme des modeles proposes ===")
placeholders = {"p", "titre", "msg", "texte", "fn", "r", "c", "t", "ligne"}
allowed = {"windows", "QTableWidgetItem"}
total = 0
for cls, entries in WIDGET_METHODS.items():
    for entry in entries:
        total += 1
        check("%s : entree a 3 champs" % cls, isinstance(entry, tuple) and len(entry) == 3,
              repr(entry))
        desc, template, imp = entry
        check("%s : libelle francais non vide" % desc, bool(desc) and desc[0].isupper())
        check("%s : modele sur une seule ligne" % cls, "\n" not in template)
        code = template.format(obj="windows.bouton1", name="bouton1")
        try:
            tree = ast.parse(code)
            syntax_ok = True
        except SyntaxError as e:
            syntax_ok, tree = e, None
        check("%s : %s" % (cls, "ligne collable = Python valide"), syntax_ok is True,
              code if syntax_ok is not True else "")
        used = set()
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used.add(node.id)
        check("%s : aucun nom invente dans %s" % (cls, code[:34]),
              not (used & placeholders), sorted(used & placeholders))
        extra = {u for u in used if u not in allowed and not u.endswith("_click")}
        check("%s : que des noms que le programme genere definit deja" % cls,
              not extra, sorted(extra))
        if imp:
            check("%s : l'import cite bien la classe utilisee" % cls,
                  imp.split()[-1] in code, imp)
            check("%s : l'import est une vraie ligne d'import" % cls,
                  isinstance(ast.parse(imp).body[0], ast.ImportFrom), imp)
check("aucun modele ne porte un nom de blanc",
      not any(ph in t for e in WIDGET_METHODS.values() for _, t, _i in e
              for ph in ("(p,titre,msg)", "(texte)", "(fn)", "(ligne)")),
      "")
check("toutes les classes de la palette ont des lignes proposees",
      set(WIDGET_METHODS) == {c for c, _l, _i, _t in UIViewer.WIDGET_DEFS},
      sorted(set(WIDGET_METHODS) ^ {c for c, _l, _i, _t in UIViewer.WIDGET_DEFS}))

print("=== 2. les lignes s'executent contre de vrais widgets ===")
from PyQt5 import QtWidgets                            # noqa: E402
from PyQt5.QtWidgets import (QApplication, QLabel, QPushButton, QLineEdit,
                             QTextEdit, QCheckBox, QRadioButton, QComboBox,
                             QListWidget, QTableWidget, QWidget)
app = QApplication.instance() or QApplication([])

label = QLabel("Bonjour")
bouton = QPushButton("Valider")
lineEdit = QLineEdit("Sami")
textEdit = QTextEdit("Une note")
checkBox = QCheckBox("Present")
radioButton = QRadioButton("Garcon")
comboBox = QComboBox()
comboBox.addItems(["1S1", "1S2"])
listWidget = QListWidget()
table = QTableWidget(1, 1)
windows = types.SimpleNamespace(label=label, bouton1=bouton, lineEdit=lineEdit,
                                textEdit=textEdit, checkBox=checkBox,
                                radioButton=radioButton, comboBox=comboBox,
                                listWidget=listWidget, table=table)
calls = []
env = {"windows": windows,
       "QTableWidgetItem": QtWidgets.QTableWidgetItem,
       "bouton1_click": lambda: calls.append("clic")}
before = {"label": label.text(), "lineEdit": lineEdit.text(),
          "list_count": listWidget.count(), "rows": table.rowCount()}
ran, modal = 0, 0
ATTR = {"QLabel": "label", "QPushButton": "bouton1", "QLineEdit": "lineEdit",
        "QTextEdit": "textEdit", "QCheckBox": "checkBox",
        "QRadioButton": "radioButton", "QComboBox": "comboBox",
        "QListWidget": "listWidget", "QTableWidget": "table"}
for cls, entries in WIDGET_METHODS.items():
    for desc, template, imp in entries:
        if "QMessageBox" in template:
            modal += 1
            continue                      # une boite modale bloquerait le test
        code = template.format(obj="windows." + ATTR[cls], name=ATTR[cls])
        try:
            exec(compile(code, "<colle>", "exec"), env)
            ok, err = True, ""
        except Exception as e:
            ok, err = False, repr(e)
        ran += 1
        check("%s execute : %s" % (cls, code[:44]), ok, err)
check("au moins 15 lignes reellement lancees", ran >= 15, ran)
check("aucune ligne proposee n'ouvre de boite modale", modal == 0, modal)

print("=== 3. et font ce qu'elles promettent ===")
check("setText a change le libelle", label.text() == "Nouveau texte", label.text())
check("l'assignation .text() a recupere le contenu",
      env.get("titre") == "Nouveau texte" or env.get("saisie") is not None,
      repr({k: v for k, v in env.items() if k in ("titre", "saisie")}))
check("lineEdit a bien ete vide par clear(), apres son setText",
      lineEdit.text() == "", repr(lineEdit.text()))
check("textEdit est rempli puis vide", textEdit.toPlainText() == "")
check("isChecked lu est un booleen", isinstance(env.get("coche"), bool),
      repr(env.get("coche")))
check("currentText lu est une chaine", isinstance(env.get("choix"), str),
      repr(env.get("choix")))
check("addItem a bien ajoute un element",
      (exec('windows.listWidget.addItem("Nouvel element")', env),
       listWidget.count() == 1)[1], listWidget.count())
check("clear() a vide la liste",
      (exec("windows.listWidget.clear()", env), listWidget.count() == 0)[1],
      listWidget.count())
check("setItem a ecrit la cellule", table.item(0, 0) is not None and
      table.item(0, 0).text() == "Texte",
      table.item(0, 0).text() if table.item(0, 0) else None)
check("insertRow(rowCount()) a ajoute une ligne", table.rowCount() == before["rows"] + 1,
      table.rowCount())
bouton.click()
check("clicked.connect branche vraiment l'evenement", calls == ["clic"], calls)
check("le gestionnaire s'appelle comme le veut la convention du plugin",
      WIDGET_METHODS["QPushButton"][0][1].format(obj="windows.bouton1",
                                                 name="bouton1")
      == "windows.bouton1.clicked.connect(bouton1_click)",
      WIDGET_METHODS["QPushButton"][0][1])

print("=== 4. QMessageBox a quitte l'editeur visuel ===")
SRC = r"C:\Users\Selmen\Desktop\projects\tunisiaschools\UIViewer.py"
with open(SRC, encoding="utf-8") as fh:
    source = fh.read()
check("UIViewer.py ne mentionne plus du tout QMessageBox",
      "QMessageBox" not in source, source.count("QMessageBox"))
check("la palette ne propose plus de boite de message",
      "QMessageBox" not in [c for c, _l, _i, _t in UIViewer.WIDGET_DEFS],
      str([c for c, _l, _i, _t in UIViewer.WIDGET_DEFS]))
check("WIDGET_METHODS n'a plus d'entree MessageBox",
      "QMessageBox" not in WIDGET_METHODS, sorted(WIDGET_METHODS))
check("_QMSGBOX a disparu du module", not hasattr(UIViewer, "_QMSGBOX"))
check("l'apercu n'a plus de branche MessageBox",
      "elif cls == \"QMessageBox\"" not in source)

# Un .ui ecrit a la main peut toujours contenir une boite de message : le
# concepteur ne la propose plus, il ne doit pas pour autant refuser le fichier.
BASE = os.path.dirname(os.path.abspath(__file__))
MSG_UI = os.path.join(BASE, "msgbox_handwrite.ui")
MSG_BACK = os.path.join(BASE, "msgbox_handwrite_out.ui")
open(MSG_UI, "w", encoding="utf-8").write("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="windowTitle"><string>Form</string></property>
  <layout class="QVBoxLayout" name="verticalLayout">
   <item>
    <widget class="QLabel" name="label">
     <property name="text"><string>Bonjour</string></property>
    </widget>
   </item>
   <item>
    <widget class="QMessageBox" name="messageBox">
     <property name="text"><string>Attention</string></property>
    </widget>
   </item>
  </layout>
 </widget>
 <resources/>
 <connections/>
</ui>
""")


def bare(path):
    """Un viewer sans Tk ni workbench : uniquement le chemin .ui."""
    v = object.__new__(UiViewerPlugin)
    v.widgets_data = []
    v.ui_file = path
    v.widget_counter = 0
    v.selected_idx = None
    v.root_widget_name = "Form"
    v.root_widget_class = "QWidget"
    v.root_geometry = (0, 0, 640, 480)
    v.root_title = "Form"
    v._source_ui = None
    v._source_uids = []
    v._src_root = {}
    v._refresh = lambda: None
    v._select = lambda i: None
    v._show_no_selection = lambda: None
    data, info = v._parse_ui(path)
    v.widgets_data = data
    v.root_geometry = info.get("geometry", (0, 0, 640, 480))
    v.root_title = info.get("title", "Form")
    return v


try:
    vh = bare(MSG_UI)
    opened = True
except Exception as e:
    vh, opened = None, e
check("un .ui contenant un QMessageBox s'ouvre toujours", opened is True, opened)
if opened:
    classes = [c for c, _p in vh.widgets_data]
    check("le QMessageBox lu reste dans le modele", "QMessageBox" in classes, classes)
    check("son texte est conserve",
          any(p.get("text") == "Attention" for _c, p in vh.widgets_data
              if _c == "QMessageBox"),
          [p for c, p in vh.widgets_data if c == "QMessageBox"])
    try:
        vh.ui_file = MSG_BACK
        vh._write_ui_file(MSG_BACK)
        saved = True
    except Exception as e:
        saved = e
    check("il se reenregistre sans exception", saved is True, saved)
    back = open(MSG_BACK, encoding="utf-8").read() if saved is True else ""
    check("le QMessageBox est rendu au fichier", 'class="QMessageBox"' in back, back[:200])
    check("le layout d'origine n'a pas eclate", back.count("<item>") == 2, back)
    check("enregistrer ne reinserte pas de proposition de code",
          "QMessageBox.critical" not in source)


print("=== 5. _copy_code : collable seul, et l'import une seule fois ===")


class FakeText:
    """Un Text Tk minimal : _copy_code lit le fichier et insere au curseur.

    Le curseur est simule en fin de contenu, sur sa propre ligne, sauf quand
    on lui donne une derniere ligne deja occupee (le cas qui soudait deux
    lignes de code)."""

    def __init__(self, content=""):
        self.events = []
        self.content = content

    def insert(self, pos, text):
        self.events.append((pos, text))
        if pos == "1.0":
            self.content = text + self.content
        else:
            self.content += text

    def get(self, a, b):
        if a == "1.0":
            return self.content
        if a == "insert linestart":
            return self.content.rsplit("\n", 1)[-1]
        if a == "insert" and b == "insert lineend":
            return ""
        return self.content

    def see(self, pos):
        pass


class FakeView:
    def __init__(self, text):
        self.text = text


class FakeEditor:
    def __init__(self, text):
        self._v = FakeView(text)

    def get_code_view(self):
        return self._v


class FakeNotebook:
    def __init__(self, editor):
        self.editor = editor

    def get_current_editor(self):
        return self.editor


class FakeWB:
    def __init__(self, editor):
        self.nb = FakeNotebook(editor)

    def get_editor_notebook(self):
        return self.nb


def viewer(editor):
    v = object.__new__(UiViewerPlugin)
    v.clip = []
    v.clipboard_clear = lambda: v.clip.append("clear")
    v.clipboard_append = lambda s: v.clip.append(s)
    UIViewer.get_workbench = lambda: FakeWB(editor)
    return v


code = 'windows.table.setItem(0, 0, QTableWidgetItem("Texte"))'
imp = UIViewer._QITEM

txt = FakeText("from PyQt5.QtWidgets import QApplication\nwindows = loadUi(f)\n")
v = viewer(FakeEditor(txt))
v._copy_code(code, imp)
check("l'import manque est inserere en tete",
      txt.events[0][0] == "1.0" and txt.events[0][1] == imp + "\n", str(txt.events))
check("la ligne va a la position du curseur",
      txt.events[1][0] == "insert", str(txt.events))
check("le presse-papiers est autonome (ligne precedee de son import)",
      v.clip[-1] == imp + "\n" + code, repr(v.clip[-1]))

txt2 = FakeText("from PyQt5.QtWidgets import QApplication, QTableWidgetItem\nx = 1\n")
v2 = viewer(FakeEditor(txt2))
v2._copy_code(code, imp)
check("un import deja present n'est pas duplique",
      all(imp not in pos_text for _pos, pos_text in txt2.events), str(txt2.events))
check("la ligne est quand meme inseree",
      txt2.events == [("insert", code)], str(txt2.events))
check("et le presse-papiers colle alors la ligne seule", v2.clip[-1] == code, repr(v2.clip[-1]))

txt3 = FakeText("windows = loadUi(f)\n")
v3 = viewer(FakeEditor(txt3))
v3._copy_code('windows.lineEdit.clear()')
check("une ligne sans classe particuliere ne promene aucun import",
      txt3.events == [("insert", "windows.lineEdit.clear()")] and v3.clip[-1] ==
      "windows.lineEdit.clear()", str(txt3.events) + repr(v3.clip[-1]))

txt6 = FakeText('windows.show()')          # curseur en fin de ligne occupee
v6 = viewer(FakeEditor(txt6))
v6._copy_code('windows.label.clear()')
check("colle en fin de ligne : la suggestion ne se soude pas au code existant",
      txt6.events == [("insert", "\nwindows.label.clear()")], str(txt6.events))
try:
    compile(txt6.content, "<fichier>", "exec")
    ok = True
except SyntaxError as e:
    ok = e
check("le fichier obtenu reste du Python valide", ok is True, ok)

v4 = viewer(None)
UIViewer.get_workbench = lambda: FakeWB(None)
try:
    v4._copy_code(code, imp)
    crashed = False
except Exception as e:
    crashed = e
check("aucun editeur ouvert : la copie reussit sans planter",
      crashed is False and v4.clip[-1] == imp + "\n" + code, crashed or repr(v4.clip[-1]))

try:
    UIViewer.get_workbench = lambda: 1 / 0
    v5 = viewer(None)
    v5._copy_code("x = 1")
    ok = v5.clip[-1] == "x = 1"
except Exception as e:
    ok = e
check("workbench indisponible : le presse-papiers est quand meme rempli", ok is True, ok)

print("=== 6. le menu PyQt5 du fichier UI ne collecte plus de blancs ===")
import importlib                                            # noqa: E402
mod = importlib.import_module("thonnycontrib.tunisiaschools")
import xml.dom.minidom as minidom                           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
doc = minidom.parse(os.path.join(HERE, "designer_layout.ui"))
le = [w for w in doc.getElementsByTagName("widget")
      if w.attributes["class"].value == "QLineEdit"][0]
name = le.attributes["name"].value
published = {}


class MenuWB:
    def _publish_command(self, cid, menu, label, handler):
        published[cid] = (label, handler)


mod.get_workbench = lambda: MenuWB()
mod._insert_in_editor = lambda code, pos="insert": (got.append(code), True)[1]
got = []
mod.usefull_commands(le)
check("4 commandes publiees", len(published) == 4, sorted(published))
inserted = []
for _label, handler in published.values():
    handler()
for chunk in got:
    try:
        ast.parse(chunk)
        ok = True
    except SyntaxError as e:
        ok = e
    check("colle et lance sans erreur de syntaxe : %s" % chunk, ok is True, ok)
    bad = [ph for ph in ("(p,titre,msg)", "setText()", "(texte)", "(fn)") if ph in chunk]
    check("aucun blanc dans %s" % chunk, not bad, bad)
check("setText recoit bien un texte",
      any('windows.%s.setText("' % name in c for c in got), str(got))
check("lire le contenu va dans une variable",
      any(c.startswith("saisie = ") for c in got), str(got))
check("le nom du widget est conserve dans chaque ligne",
      all(("windows." + name) in c or ("= windows." + name) in c for c in got), str(got))

# et l'effet reel, sur un vrai QLineEdit cette fois
edit = QLineEdit("Bonjour")
ns = types.SimpleNamespace(**{name: edit})
for chunk in got:
    exec(compile(chunk, "<colle>", "exec"), {"windows": ns})
check("les 4 lignes du menu s'executent sur un vrai widget, dans l'ordre du menu",
      edit.text() == "", repr(edit.text()))
exec(compile('windows.%s.setText("Rebonjour")' % name, "<colle>", "exec"), {"windows": ns})
check("le setText du menu ecrit vraiment dans le champ",
      edit.text() == "Rebonjour", edit.text())

print("=== 7. le panneau METHODES tel que l'eleve le clique (vrai Tk) ===")
import tkinter as tk                                  # noqa: E402
from tkinter import Tk                               # noqa: E402

root = Tk()
root.withdraw()
editor_text = tk.Text(root)


class RealView:
    text = editor_text


class RealEditor:
    def get_code_view(self):
        return RealView()


UIViewer.get_workbench = lambda: FakeWB(RealEditor())
v7 = UiViewerPlugin(root)
for cls in [c for c, _l, _i, _t in UIViewer.WIDGET_DEFS]:
    v7._add_widget(cls)


def code_rows(v):
    """Les etiquettes de code du panneau, dans l'ordre affiche."""
    rows = []
    for child in v.prop_frame.winfo_children():
        for lbl in child.winfo_children():
            if (isinstance(lbl, tk.Label) and "Courier" in str(lbl.cget("font"))
                    and lbl.cget("fg") == "#7ab8f5"
                    and lbl.cget("bg") in (UIViewer.PROP_EVEN, UIViewer.PROP_ODD)):
                rows.append((child, lbl))
    return rows


for i, (cls, props) in enumerate(v7.widgets_data):
    v7._select(i)                       # construit le panneau pour de vrai
    root.update()                       # sans cela, le premier clic est perdu
    wname = props["name"]
    rows = code_rows(v7)
    expected = WIDGET_METHODS.get(cls, [])
    check("%s : le panneau affiche toutes ses lignes" % cls,
          len(rows) == len(expected), "%d affichees, %d attendues" % (len(rows), len(expected)))
    for (row, lbl), (desc, template, imp) in zip(rows, expected):
        want = template.format(obj="windows." + wname, name=wname)
        shown = lbl.cget("text").strip()
        check("%s : l'etiquette montre le code reel" % cls,
              want.startswith(shown.rstrip(".")) or shown == want, "%r vs %r" % (shown, want))
        editor_text.delete("1.0", "end")
        row.event_generate("<Button-1>")
        root.update()
        pasted = editor_text.get("1.0", "end-1c")
        check("%s : le clic insere la ligne complete" % cls,
              want in pasted, repr(pasted))
        try:
            compile(pasted, "<panneau>", "exec")
            ok = True
        except SyntaxError as e:
            ok = e
        check("%s : ce qui est insere se lance" % cls, ok is True, ok)
        if imp:
            check("%s : l'import accompagne la ligne" % cls, imp in pasted, repr(pasted[:80]))

# deux lignes de tableau a la suite : l'import ne doit apparaitre qu'une fois
editor_text.delete("1.0", "end")
editor_text.insert("1.0", 'windows = loadUi("x.ui")\n')
v7._select([j for j, (c, _p) in enumerate(v7.widgets_data) if c == "QTableWidget"][0])
root.update()
tbl_rows = code_rows(v7)
for row, _lbl in tbl_rows:
    row.event_generate("<Button-1>")
    root.update()
buffer_text = editor_text.get("1.0", "end-1c")
check("l'import QTableWidgetItem insere une seule fois pour %d clics" % len(tbl_rows),
      buffer_text.count("import QTableWidgetItem") == 1,
      str(buffer_text.count("import QTableWidgetItem")))
check("les lignes du tableau sont dans le fichier",
      all(m in buffer_text for m in ("setItem(", "insertRow(")), buffer_text)
try:
    compile(buffer_text, "<fichier>", "exec")
    ok = True
except SyntaxError as e:
    ok = e
check("le fichier obtenu est du Python valide", ok is True, ok)

# et le QMessageBox survit en tant qu'etiquette genérique, plus en tant que widget
check("le concepteur n'a jamais ajoute de QMessageBox",
      "QMessageBox" not in [c for c, _p in v7.widgets_data],
      str([c for c, _p in v7.widgets_data]))
try:
    probe_w = v7._make_qt_widget(tk.Frame(root), "QMessageBox", {}, 260, 28)
    fell_back = True
except Exception as e:
    probe_w, fell_back = None, e
check("une classe que le viewer ne connait plus tombe sur l'apercu generique",
      fell_back is True and "QMessageBox" in str(probe_w.cget("text")),
      fell_back if fell_back is not True else probe_w.cget("text"))

print("=== 8. own_line sur un vrai Text : la suggestion reste seule ===")
probe = tk.Text(root)
# (contenu, curseur, texte attendu, le fichier doit-il se lancer)
cases = [("", "1.0", "code", True),
         ("x = 1\n", "end", "code", True),
         ("x = 1", "end", "\ncode", True),
         ("a = 1\nb = 2", "2.0", "code\n", True),
         ("a = 1", "1.0", "code\n", True),
         ("a = 1\nb = 2", "1.4", "\ncode\n", False)]   # la ligne etait deja cassee
for content, mark, expect, runs in cases:
    probe.delete("1.0", "end")
    probe.insert("1.0", content)
    probe.mark_set("insert", mark)
    got = UIViewer.own_line(probe, "code")
    check("curseur %s sur %r -> %r" % (mark, content, expect), got == expect, repr(got))
    probe.delete("1.0", "end")
    probe.insert("1.0", content)
    probe.mark_set("insert", mark)
    probe.insert("insert", got)
    buffer_text = probe.get("1.0", "end-1c")
    try:
        compile(buffer_text, "<fichier>", "exec")
        ok = True
    except SyntaxError as e:
        ok = False
    check("  fichier obtenu %r : executable = %s" % (buffer_text, runs), ok is runs, ok)
probe.destroy()
root.destroy()

print("=== 9. le squelette « Ajouter Annexe » montre le branchement et laisse ses trois blancs ===")
# Le menu « Ajouter Annexe » (sans fichier .ui) collecte PYQT5_TEMPLATE_CODE : trois
# blancs a remplacer par l'eleve, Nom_Interface.ui, Nom_Bouton et Nom_Module. La
# ligne windows.Nom_Bouton.clicked.connect (Nom_Module) est le geste a montrer : un
# bouton, un clic, une fonction. L'item 2 avait juge ce texte casse parce que
# Nom_Module n'y etait pas defini — le fichier colle tel quel s'arretait la avec un
# NameError — et y avait ecrit le gestionnaire. La decision du 2026-10-02 retire ce
# gestionnaire (def, commentaire « A completer », pass) et LAISSE la ligne de
# branchement : le nom du rappel redevient un blanc, a l'eleve de l'ecrire. Ce que
# la sonde doit donc prouver n'est plus « colle et lance », mais deux choses : tout
# ce qui precede le blanc s'execute vraiment (application, fenetre, affichage), et
# l'arret nomme justement le blanc oublie — et disparait des que l'eleve a ecrit sa
# fonction, sans que le branchement ait eu a changer d'un caractere.
import builtins                                     # noqa: E402
import json                                         # noqa: E402
import subprocess                                   # noqa: E402

# Le texte tel que la distribution le collait avant l'item 2 : la decision du
# 2026-10-02 y rend mot pour mot le squelette, ce qui est verifie plus bas.
SQUELETTE_D_ORIGINE = (
    "from PyQt5.uic import loadUi\n"
    "from PyQt5.QtWidgets import QApplication\n"
    "\n\n\n"
    "app = QApplication([])\n"
    'windows = loadUi ("Nom_Interface.ui")\n'
    "windows.show()\n"
    "windows.Nom_Bouton.clicked.connect (Nom_Module)\n"
    "app.exec_()\n"
)


def noms_inventes(code):
    """Les noms que ce programme utilise sans les definir ni les importer."""
    a = ast.parse(code)
    definis = set(dir(builtins))
    for n in ast.walk(a):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definis.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            definis.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names:
                definis.add((al.asname or al.name).split(".")[0])
        elif isinstance(n, ast.arg):
            definis.add(n.arg)
    employes = {n.id for n in ast.walk(a)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return sorted(employes - definis)


def attributs_de_windows(code):
    """Ce que le programme demande a l'objet `windows` : le squelette ne doit
    demander que le bouton qu'il nomme comme blanc, et de s'afficher."""
    return sorted({n.attr for n in ast.walk(ast.parse(code))
                   if isinstance(n, ast.Attribute)
                   and isinstance(n.value, ast.Name) and n.value.id == "windows"})


BLANCS = ("Nom_Interface.ui", "Nom_Bouton", "Nom_Module")
tpl = mod.PYQT5_TEMPLATE_CODE
check("le squelette rendu est mot pour mot celui d'avant l'item 2",
      tpl == SQUELETTE_D_ORIGINE, repr(tpl)[:120])
try:
    compile(tpl, "annexe.py", "exec")
    sintax = True
except SyntaxError as e:
    sintax = e
check("le squelette se compile", sintax is True, sintax)
check("les trois blancs de l'eleve sont la, un exemplaire chacun",
      all(tpl.count(b) == 1 for b in BLANCS), dict((b, tpl.count(b)) for b in BLANCS))
check("et aucun quatrieme nom Nom_ n'a ete invente au passage",
      tpl.count("Nom_") == 3, [l for l in tpl.splitlines() if "Nom_" in l])
check("le seul nom que l'eleve doit fournir est son blanc Nom_Module",
      noms_inventes(tpl) == ["Nom_Module"], noms_inventes(tpl))
corps = ast.parse(tpl)
fns = [n for n in ast.walk(corps) if isinstance(n, ast.FunctionDef)]
check("le squelette ne definit aucune fonction : l'eleve ecrit la sienne",
      fns == [], [f.name for f in fns])
check("le bloc retire n'est jamais revenu : ni pass, ni commentaire a trous",
      "pass" not in tpl.split() and "compléter" not in tpl,
      [l for l in tpl.splitlines() if "compl" in l or l.strip() == "pass"])
check("il ne demande a windows que son bouton blanc et de s'afficher",
      attributs_de_windows(tpl) == ["Nom_Bouton", "show"], attributs_de_windows(tpl))
branchements = [n for n in ast.walk(corps) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == "connect"]
check("une seule ligne de branchement, celle que l'eleve doit lire",
      len(branchements) == 1, len(branchements))
check("elle branche le clic du bouton blanc sur le rappel, sans l'appeler",
      len(branchements) == 1
      and isinstance(branchements[0].args[0], ast.Name)
      and branchements[0].args[0].id == "Nom_Module"
      and branchements[0].func.value.attr == "clicked"
      and branchements[0].func.value.value.attr == "Nom_Bouton",
      [type(getattr(branchements[0], "args", [None])[0]).__name__
       if branchements else None])
ETAPES = ["from PyQt5.uic import loadUi", "from PyQt5.QtWidgets import QApplication",
          "app = QApplication([])", 'windows = loadUi ("Nom_Interface.ui")',
          "windows.show()", "windows.Nom_Bouton.clicked.connect (Nom_Module)",
          "app.exec_()"]
check("le geste complet de l'eleve reste ecrit, dans l'ordre",
      all(e in tpl for e in ETAPES)
      and [tpl.index(e) for e in ETAPES] == sorted(tpl.index(e) for e in ETAPES),
      [tpl.index(e) for e in ETAPES])

# ── et surtout : ce que le squelette fait vraiment quand on le lance ──
# Sonde lancee dans le bundle : elle colle le squelette dans un namespace, lui
# fait ouvrir le Nom_Interface.ui de l'eleve, et dit ou il s'arrete. La derniere
# ligne (app.exec_()) bloque l'evenementiel : on la retire, ce qui laisse quand
# meme voir si tout ce qui la precede est passe. L'etat est releve APRES l'arret
# aussi : un texte qui s'interrompt sur son blanc doit quand meme dire ce qui a
# fonctionne avant lui.
SONDE_SQUELETTE = r'''
import json, os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, @SITE@)
from PyQt5.QtWidgets import QApplication
os.chdir(@DOSSIER@)
verdict = {"erreur": None, "app": False, "visible": False, "rappel": False,
           "receivers": -1, "marque": [], "clic": None}
ns = {"__name__": "__main__", "__file__": "annexe.py"}
def etat():
    verdict["app"] = isinstance(ns.get("app"), QApplication)
    fenetre = ns.get("windows")
    verdict["visible"] = bool(fenetre.isVisible()) if fenetre is not None else False
    verdict["rappel"] = callable(ns.get("Nom_Module"))
try:
    lignes = @CODE@.splitlines(True)
    corps = "".join(l for l in lignes if l.strip() != "app.exec_()")
    exec(compile(corps, "annexe.py", "exec"), ns)
    w = ns["windows"]
    b = w.Nom_Bouton
    # receivers(sign) n'accepte que l'objet de signal lui-meme en PyQt5 5.15 :
    # SIGNAL("clicked()") a disparu de QtCore.
    verdict["receivers"] = b.receivers(b.clicked)
    b.click()
    verdict["clic"] = "ok"
    verdict["marque"] = list(ns.get("marque", []))
except Exception as e:
    verdict["erreur"] = "%s: %s" % (type(e).__name__, e)
etat()
print("VERDICT " + json.dumps(verdict))
'''

DOSSIER = os.path.join(BASE, "_sortie", "annexe")
if not os.path.isdir(DOSSIER):
    os.makedirs(DOSSIER)
NOM_UI = os.path.join(DOSSIER, "Nom_Interface.ui")
open(NOM_UI, "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<ui version="4.0">\n'
    " <class>Dialog</class>\n"
    ' <widget class="QDialog" name="Dialog">\n'
    "  <property name=\"windowTitle\"><string>Annexe</string></property>\n"
    '  <layout class="QVBoxLayout" name="verticalLayout">\n'
    "   <item>\n"
    '    <widget class="QPushButton" name="Nom_Bouton">\n'
    "     <property name=\"text\"><string>Cliquer</string></property>\n"
    "    </widget>\n"
    "   </item>\n"
    "  </layout>\n"
    " </widget>\n"
    " <resources/>\n"
    " <connections/>\n"
    "</ui>\n")

env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
SITE = os.path.join(BUNDLE, "Lib", "site-packages")


def sonde(code, dossier):
    src = (SONDE_SQUELETTE.replace("@SITE@", repr(SITE))
           .replace("@DOSSIER@", repr(dossier)).replace("@CODE@", repr(code)))
    p = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", "-c", src],
                       capture_output=True, text=True, env=env, timeout=180)
    for ligne in (p.stdout or "").splitlines():
        if ligne.startswith("VERDICT "):
            return json.loads(ligne[len("VERDICT "):]), p
    # pas de verdict = la sonde elle-meme a rendu l'ame avant le try
    return {"erreur": "aucun verdict: %s" % (p.stderr or "")[-160:], "app": False,
            "visible": False, "rappel": False, "receivers": -1, "marque": [],
            "clic": None}, p


v, pv = sonde(tpl, DOSSIER)
check("colle tel quel, le squelette s'arrete a sa ligne de branchement",
      v["erreur"] is not None and "NameError" in v["erreur"]
      and "Nom_Module" in v["erreur"], (v, pv.stderr[-200:]))
check("et tout ce qui precede le blanc s'est vraiment execute : application, "
      "fenetre, affichage", v["app"] is True and v["visible"] is True, v)
check("le nom manque est nomme, c'est la seule chose qu'on lui reproche",
      v["rappel"] is False and v["receivers"] == -1, v)
print("     l'eleve qui oublie sa fonction voit : %s" % v["erreur"])

# L'eleve ecrit sa fonction : le branchement, lui, ne bouge pas d'un caractere.
SQUELETTE_ELEVE = tpl.replace(
    "app = QApplication([])",
    "marque = []\n"
    "def Nom_Module():\n"
    "    marque.append('clic')\n"
    "\n"
    "app = QApplication([])")
lignes_eleve = [l for l in SQUELETTE_ELEVE.splitlines() if l.strip()]
check("le geste de l'eleve est trois lignes de plus, pas une de retiree",
      lignes_eleve == ([l for l in tpl.splitlines() if l.strip()][:2]
                       + ["marque = []", "def Nom_Module():",
                          "    marque.append('clic')"]
                       + [l for l in tpl.splitlines() if l.strip()][2:]),
      lignes_eleve)
ve, pe = sonde(SQUELETTE_ELEVE, DOSSIER)
check("avec sa fonction ecrite, plus aucune exception", ve["erreur"] is None,
      (ve, pe.stderr[-200:]))
check("le bouton porte UN rappel, et c'est le sien",
      ve["receivers"] == 1 and ve["rappel"] is True, ve)
check("un clic l'atteint vraiment", ve["clic"] == "ok" and ve["marque"] == ["clic"], ve)

# L'etat que l'item 2 avait ecrit, pour memoire : il se lancait sans rien laisser
# a nommer a l'eleve. Le commentaire « A completer » est omis ci-dessous, il ne
# pese rien dans la comparaison.
SQUELETTE_ITEM2 = tpl.replace(
    "app = QApplication([])",
    "def Nom_Module():\n    pass\n\napp = QApplication([])", 1)
v1, _p1 = sonde(SQUELETTE_ITEM2, DOSSIER)
check("le squelette de l'item 2 se lancait, lui aussi, sans exception",
      v1["erreur"] is None and v1["receivers"] == 1, v1)
BLOC_DU_GESTIONNAIRE = ["def Nom_Module():", "    pass"]
check("la difference avec celui d'aujourd'hui tient au seul bloc def/pass",
      [l for l in SQUELETTE_ITEM2.splitlines()
       if l.strip() and l not in BLOC_DU_GESTIONNAIRE]
      == [l for l in tpl.splitlines() if l.strip()],
      SQUELETTE_ITEM2)

VIDE = os.path.join(BASE, "_sortie", "annexe_sans_ui")
if not os.path.isdir(VIDE):
    os.makedirs(VIDE)
v2, _p2 = sonde(tpl, VIDE)
check("le blanc qui mord en premier est le fichier, pas le nom du rappel",
      v2["erreur"] is not None and "Nom_Interface.ui" in v2["erreur"]
      and "Nom_Module" not in v2["erreur"], v2)
print("     l'eleve qui n'a pas enregistre son .ui voit : %s" % v2["erreur"])

print()
print("%d checks, %d echecs" % (N[0], len(FAILS)))
for f in FAILS:
    print("ECHEC:", f)
sys.exit(1 if FAILS else 0)
