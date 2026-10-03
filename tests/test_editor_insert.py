"""Controles pour l'issue #6 : les commandes PyQt5 ne doivent plus supposer
qu'un editeur est deja ouvert."""
import importlib
import io
import os
import sys
import types

mod = importlib.import_module("thonnycontrib.tunisiaschools")

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + label + (("  <- " + str(detail)) if detail else ""))


class FakeText:
    def __init__(self, content=""):
        self.events = []
        self.content = [content] if content else []

    def insert(self, pos, text):
        self.events.append(("insert", pos, text))
        self.content.append(text)

    def see(self, pos):
        self.events.append(("see", pos))

    def get(self, a, b):
        return "".join(self.content)


class FakeView:
    def __init__(self, text):
        self.text = text


class FakeEditor:
    def __init__(self, text, view=True):
        self._text = text
        self._view = view
        self.focused = 0

    def get_code_view(self):
        return self._view if self._view is None else FakeView(self._text)

    def focus_set(self):
        self.focused += 1


class FakeNotebook:
    def __init__(self, editors):
        self.editors = list(editors)     # les onglets deja ouverts
        self.created = 0
        self.fail = None

    def get_current_editor(self):
        if self.fail:
            raise self.fail
        return self.editors[-1] if self.editors else None

    def open_new_file(self):
        self.created += 1
        if self.fail:
            raise self.fail
        self.editors.append(FakeEditor(FakeText()))


class FakeMenu:
    """Le menu PyQt5, vu par _clear_dynamic_menu_items."""

    def __init__(self):
        self.items = ["Ajouter Annexe", "Ajouter Annexe + interface", "Ouvrir dans Designer"]

    def index(self, label):
        return self.items.index(label)

    def delete(self, i):
        del self.items[i]


class FakeWB:
    def __init__(self, notebook):
        self.notebook = notebook
        self.commands = {}
        self.views = {}
        self.menu = FakeMenu()

    def get_menu(self, name):
        return self.menu

    def get_editor_notebook(self):
        return self.notebook

    def _publish_command(self, cid, menu, label, handler):
        self.commands[cid] = (label, handler)

    def get_view(self, name, create=True):
        # la signature reelle de Workbench.get_view. Le mot-cle n'est pas un
        # ornement : `create=False` leve sur une vue absente au lieu d'en
        # construire une. Un faux qui l'ignorerait avalerait la question de
        # _vue_concepteur() sans jamais suivre le chemin du produit.
        if name not in self.views:
            if not create:
                raise RuntimeError("View %s not created" % name)
            raise AssertionError("vue inattendue : %s" % name)
        return self.views[name]

    def show_view(self, name, flag):
        pass

    def get_option(self, name, default=None):
        return default

    def set_option(self, name, value):
        pass


class FakeBox:
    def __init__(self):
        self.calls = []

    def showerror(self, title, msg, **kw):
        self.calls.append(("error", title, msg))

    def askyesno(self, *a, **k):
        return True


def install(notebook):
    wb = FakeWB(notebook)
    box = FakeBox()
    mod.get_workbench = lambda: wb
    mod.messagebox = box
    return wb, box


# ── 1. un editeur est deja ouvert : on insere a la souris ─────────────
txt = FakeText()
nb = FakeNotebook([FakeEditor(txt)])
wb, box = install(nb)
ok = mod._insert_in_editor("windows.lineEdit1.text()")
check("avec editeur : insertion reussie", ok is True)
check("avec editeur : aucun onglet cree", nb.created == 0, nb.created)
check("avec editeur : insere a la position du curseur",
      txt.events[0] == ("insert", "insert", "windows.lineEdit1.text()"), str(txt.events))
check("avec editeur : la position reste visible", ("see", "insert") in txt.events, str(txt.events))
check("avec editeur : le focus revient a l'editeur", nb.editors[-1].focused == 1)
check("avec editeur : aucun message d'erreur", box.calls == [], str(box.calls))

# ── 2. aucun onglet : un document neuf est cree, puis rempli ──────────
nb = FakeNotebook([])
wb, box = install(nb)
ok = mod.add_pyqt_template_code()
check("sans editeur : le modele est quand meme insere", ok is True)
check("sans editeur : un document a ete cree", nb.created == 1, nb.created)
new_text = nb.editors[-1].get_code_view().text
check("sans editeur : le texte est le modele PyQt5",
      "".join(new_text.content) == mod.PYQT5_TEMPLATE_CODE, repr("".join(new_text.content))[:60])
check("sans editeur : un seul message d'erreur attendu = rien", box.calls == [], str(box.calls))
check("sans editeur : l'ancien onglet n'a pas ete touche", nb.created == 1)

# ── 3. pannes du tableur d'editeurs ───────────────────────────────────
nb = FakeNotebook([])
nb.fail = RuntimeError("notebook pas pret")
wb, box = install(nb)
try:
    ok = mod._insert_in_editor("x")
    crashed = False
except Exception as e:
    ok, crashed = None, e
check("panne : aucune exception remonte a l'eleve", crashed is False, crashed)
check("panne : renvoie False", ok is False, ok)
check("panne : l'utilisateur voit pourquoi", box.calls and box.calls[0][0] == "error"
      and "Fichier" in box.calls[0][2], str(box.calls))

ed = FakeEditor(FakeText(), view=None)     # editeur sans vue de code
nb = FakeNotebook([ed])
wb, box = install(nb)
check("vue absente : renvoie False sans planter", mod._insert_in_editor("x") is False)
check("vue absente : message visible", any(c[0] == "error" for c in box.calls), str(box.calls))

# open_new_file ne fournit toujours pas d'editeur (cas limite)
class StillEmpty(FakeNotebook):
    def open_new_file(self):
        self.created += 1

nb = StillEmpty([])
wb, box = install(nb)
check("creation inefficace : renvoie False", mod._insert_in_editor("x") is False)
check("creation inefficace : pas de traceback", any(c[0] == "error" for c in box.calls), str(box.calls))

# ── 4. les commandes de menu du fichier UI ────────────────────────────
import xml.dom.minidom as minidom
ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "designer_layout.ui")
doc = minidom.parse(ui_path)
line_edit = [w for w in doc.getElementsByTagName("widget")
             if w.attributes["class"].value == "QLineEdit"][0]
nb = FakeNotebook([])                       # toujours sans editeur au depart
wb, box = install(nb)
mod.usefull_commands(line_edit)
check("menu : 4 commandes publiees", len(wb.commands) == 4, sorted(wb.commands))
labels = [v[0] for v in wb.commands.values()]
name = line_edit.attributes["name"].value
check("menu : libelles French + nom du widget",
      any(l == "Contenu de " + name for l in labels), str(labels))
check("menu : labels enregistres pour le nettoyage",
      all(any(l.endswith(name) for l in mod._dynamic_menu_labels) for l in labels))

handlers = [v[1] for v in wb.commands.values()]
check("menu : un appel ne leve plus jamais AttributeError",
      all(h() is not None for h in handlers))
view_text = nb.editors[-1].get_code_view().text
inserted = "".join(view_text.content)
check("menu : le code insere cible le bon widget",
      all(("windows." + name) in chunk for chunk in view_text.content[1:]),
      str(view_text.content))
check("menu : un seul onglet cree pour 4 clics", nb.created == 1, nb.created)
check("menu : .text() / .setText(...) / .clear() / .show() presents",
      all(s in inserted for s in ("windows." + name + ".text()",
                                  'windows.' + name + '.setText("',
                                  "windows." + name + ".clear()",
                                  "windows." + name + ".show()")), inserted)
# un setText sans argument leve un TypeError des qu'on lance le fichier :
# c'etait le cas de la commande « Changer le contenu de ... »
check("menu : aucune ligne ne collecte un texte vide",
      ".setText()" not in inserted, inserted)


def _compilable(chunk):
    try:
        compile(chunk, "<colle>", "exec")
        return True
    except SyntaxError:
        return False


check("menu : chaque ligne inseree est du Python complet",
      all(_compilable(c) for c in view_text.content), str(view_text.content))

# ── 5. « Ajouter Annexe + interface » sans editeur ouvert ─────────────
nb = FakeNotebook([])
wb, box = install(nb)
mod._dynamic_menu_labels.clear()
mod.askopenfilename = lambda **kw: ui_path
mod.minidom = minidom
# load_new_ui_file rend True quand le fichier est vraiment devenu celui qui
# s'affiche (item 13) : « non » veut dire que la vue n'a rien ouvert, et le
# bouton ne doit alors toucher ni au menu ni a la cible de « Ouvrir dans
# Designer » — laquelle se lit sur la vue depuis l'item 9.
appels_vue = []


class VueQuiOuvre:
    """La vue du concepteur, reduite aux deux choses que le bouton lui demande :
    ouvrir un fichier, dire si elle l'a vraiment affiche. Elle note le fichier
    affiche comme le fait le vrai `load_new_ui_file` (UIViewer.py) : c'est ce
    releve qui designe la cible de « Ouvrir dans Designer »."""

    def __init__(self, ui_file=""):
        self.ui_file = ui_file

    def load_new_ui_file(self, path):
        appels_vue.append(path)
        self.ui_file = path
        return True


class VueQuiRefuse(VueQuiOuvre):
    """Meme vue, mais le fichier ne devient pas celui qui s'affiche : le lecteur
    l'a refuse (item 3) ou l'eleve a dit « non » (item 13). Elle a donc garde sa
    reponse precedente, `ui_file` compris — c'est ce que le geste suivant de
    l'eleve, « Ouvrir dans Designer », doit retrouver."""

    def load_new_ui_file(self, path):
        appels_vue.append(path)
        return False


viewer = VueQuiOuvre()
wb.views["UiViewerPlugin"] = viewer
ok = mod.add_pyqt_code()
check("annexe+interface : la vue recoit le fichier choisi",
      appels_vue == [ui_path], str(appels_vue))
text = nb.editors[-1].get_code_view().text
check("annexe+interface : un document cree", nb.created == 1, nb.created)
check("annexe+interface : insertion en debut de fichier",
      text.events and text.events[0][1] == "1.0", str(text.events[:1]))
body = "".join(text.content)
check("annexe+interface : le programme genere est complet",
      body.startswith("from PyQt5.uic import loadUi")
      and "app = QApplication([])" in body and body.rstrip().endswith("app.exec_()"), body[-60:])
check("annexe+interface : loadUi pointe sur le fichier choisi",
      ui_path.replace("\\", "/") in body or ui_path in body, body[:200])
check("annexe+interface : les boutons sont branches",
      ".clicked.connect (" in body, body)
check("annexe+interface : aucune exception", box.calls == [], str(box.calls))
# la cible de « Ouvrir dans Designer » se lit sur la vue (item 9) : le fichier
# que le bouton vient de faire ouvrir doit etre celui que designer.exe recevra.
check("annexe+interface : le fichier ouvert devient la cible de Designer",
      viewer.ui_file == ui_path
      and mod._current_ui_path() == os.path.abspath(ui_path),
      (viewer.ui_file, mod._current_ui_path()))

# le chemin doit rester un litteral Python valide : Tk rend des antislashes
# Windows, et "\Users" ou "\tunisiaschools" collés dans une chaîne forment des
# sequences d'echappement que Python refuse (ou pire, remplace par un tab).
import ast as _ast
snippet = [l for l in body.splitlines() if "loadUi (" in l][0]
try:
    compile(snippet, "<genere>", "exec")
    valide = True
except SyntaxError as e:
    valide = e
check("annexe+interface : la ligne loadUi est du Python valide", valide is True, snippet)

# valider ne suffit pas : "C:\temp\x.ui" est valide et faux. On relit le litteral.
_lit = _ast.literal_eval(_ast.parse(snippet).body[0].value.args[0])
check("annexe+interface : aucun echappement cache dans le chemin",
      isinstance(_lit, str) and "\t" not in _lit and "\r" not in _lit and "\n" not in _lit,
      repr(_lit))
check("annexe+interface : le chemin genere designe le fichier choisi",
      os.path.isfile(_lit) and os.path.samefile(_lit, ui_path), repr(_lit))
check("annexe+interface : le chemin genere tient sur une seule ligne",
      snippet.count("\n") == 0 and _lit.count("\\") == 0, snippet)

# ── 5b. la vue n'a rien ouvert : le bouton doit rester les bras croises ───
# Deux cas rendent load_new_ui_file() False : le fichier choisi n'est pas une
# fenetre (le lecteur le refuse, item 3), et l'eleve a repondu « non » a la
# question qui protege son travail affiche (item 13). Avant, le bouton avait
# deja vide le menu et note le fichier choisi dans une copie du module :
# l'eleve se retrouvait avec les commandes d'un fichier que le concepteur
# refusait de montrer, et son « Ouvrir dans Designer » pointait dessus. La
# copie n'existe plus (item 9) : la cible se lit sur la vue, et c'est donc la
# vue qu'on installe ici avec son fichier a l'ecran.
nb = FakeNotebook([])
wb, box = install(nb)
mod._dynamic_menu_labels.clear()
mod.usefull_commands(line_edit)        # le menu du fichier qui marche
labels_avant = list(mod._dynamic_menu_labels)
# Dans le vrai Thonny, ces etiquettes sont aussi dans le menu : sans elles,
# _clear_dynamic_menu_items() n'aurait rien a effacer et le controle suivant
# passerait meme si le bouton vidait le menu.
wb.menu.items += labels_avant
menu_avant = list(wb.menu.items)
commandes_avant = dict(wb.commands)
# le .ui que l'eleve regarde avant de cliquer : un vrai fichier, sinon
# _current_ui_path() repondrait « rien » pour la mauvaise raison.
A_L_ECRAN = os.path.join(os.path.dirname(ui_path), "_sortie", "editor_insert",
                         "a_l_ecran.ui")
os.makedirs(os.path.dirname(A_L_ECRAN), exist_ok=True)
with open(A_L_ECRAN, "w", encoding="utf-8") as fh:
    fh.write('<?xml version="1.0"?>\n<ui version="4.0">\n <class>Precedent</class>\n</ui>\n')
parses = []


class MinidomQuiTriturle:
    @staticmethod
    def parse(p):
        parses.append(p)
        raise AssertionError("le fichier refuse ne doit meme pas etre relance")


mod.askopenfilename = lambda **kw: ui_path
mod.minidom = MinidomQuiTriturle
vue_refusee = VueQuiRefuse(A_L_ECRAN)
wb.views["UiViewerPlugin"] = vue_refusee
mod.add_pyqt_code()
check("refuse : aucun editeur n'est cree", nb.created == 0, nb.created)
check("refuse : le menu a garde les commandes du fichier precedent",
      wb.menu.items == menu_avant, (wb.menu.items, menu_avant))
check("refuse : la liste des etiquettes a nettoyer est intacte",
      mod._dynamic_menu_labels == labels_avant, str(mod._dynamic_menu_labels))
check("refuse : aucune commande neuve publiee",
      dict(wb.commands) == commandes_avant, sorted(wb.commands))
check("refuse : la vue a garde son fichier a l'ecran",
      vue_refusee.ui_file == A_L_ECRAN, vue_refusee.ui_file)
check("refuse : Designer viserait encore le fichier de l'ecran, pas le refuse",
      mod._current_ui_path() == os.path.abspath(A_L_ECRAN), mod._current_ui_path())
check("refuse : le XML n'est pas meme relu", parses == [], str(parses))
check("refuse : le bouton reste muet, c'est la vue qui a deja parle",
      box.calls == [], str(box.calls))

# ── 6. avec un vrai Tk.Text : les indices 'insert' et '1.0' fonctionnent
import tkinter as tk
root = tk.Tk()
root.withdraw()


class RealEditor(FakeEditor):
    pass


class RealNotebook(FakeNotebook):
    def open_new_file(self):
        self.created += 1
        self.editors.append(FakeEditor(None))

    def _mk(self):
        pass


real_text = tk.Text(root)
nb = FakeNotebook([FakeEditor(real_text)])
wb, box = install(nb)


class RealView:
    text = real_text


nb.editors[0].get_code_view = lambda: RealView()
ok = mod._insert_in_editor("ligne A\n")
check("vrai Tk : insertion a la position du curseur",
      ok is True and real_text.get("1.0", "end-1c").startswith("ligne A"),
      repr(real_text.get("1.0", "end")))
ok = mod._insert_in_editor("debut\n", "1.0")
check("vrai Tk : index '1.0' accepte", ok is True and real_text.get("1.0", "2.0").startswith("debut"), repr(real_text.get("1.0", "end-1c")))

# le curseur est en fin d'une ligne deja occupee : la commande du menu ne
# doit pas coller son code a celle de l'eleve
real_text.insert("end", "windows.show()")
mod._insert_in_editor('windows.label.setText("x")')
final = real_text.get("1.0", "end-1c")
check("vrai Tk : une insertion au curseur ne soude pas deux lignes",
      "windows.show()windows" not in final and 'windows.label.setText("x")' in final,
      repr(final))
check("vrai Tk : la ligne inseree reste seule",
      'windows.label.setText("x")' in [l for l in final.splitlines()], repr(final))
root.destroy()

fails = [r for r in results if not r[1]]
print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
sys.exit(1 if fails else 0)
