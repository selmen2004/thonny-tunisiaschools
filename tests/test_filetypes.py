"""Les motifs `filetypes` des boites de dialogue Tk doivent porter un joker.

Tk (et la boite Windows sous lui) traite un motif SANS `*` comme un nom
litteral : « .ui » ne designe que un fichier nomme exactement « .ui », donc
la boite n'affiche rien du tout. Le plugin melangeait les deux ecritures :
UIViewer.py mettait "*.ui" / "*.*" (correct) alors qu'__init__.py mettait
".ui" / ".*" / "designer.exe *.exe" (filtres morts). Ce test impose la regle
partout et montre ce que le motif mort produisait reellement.
"""
import ast
import fnmatch
import io
import os
import sys

import chemins

PLUGIN = chemins.PAQUET
FILES = ["__init__.py", "UIViewer.py"]

FAILS = []
N = [0]


def check(label, cond, detail=""):
    N[0] += 1
    if not cond:
        FAILS.append("%s %s" % (label, detail))
    print("%s %s%s" % ("OK  " if cond else "FAIL", label,
                       (" -> " + str(detail)) if detail else ""))


def lists_in(tree):
    """Chaque mot-cle filetypes rencontre, avec le nom de la fonction appelee."""
    found = []

    class V(ast.NodeVisitor):
        def visit_Call(self, node):
            fname = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            for kw in node.keywords:
                if kw.arg == "filetypes":
                    pairs = []
                    for elt in getattr(kw.value, "elts", []):
                        if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                            desc = elt.elts[0]
                            pat = elt.elts[1]
                            # tr("...") est un Call : la chaine est son premier argument
                            if isinstance(desc, ast.Call) and desc.args:
                                desc = desc.args[0]
                            if (isinstance(pat, ast.Constant) and isinstance(pat.value, str)
                                    and isinstance(desc, ast.Constant)):
                                pairs.append((desc.value, pat.value))
                    found.append((fname, pairs))
            self.generic_visit(node)

    V().visit(tree)
    return found


print("=== 1. tous les filetypes du plugin portent un joker ===")
all_pairs = {}
for rel in FILES:
    path = os.path.join(PLUGIN, rel)
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    tree = ast.parse(text)
    hits = lists_in(tree)
    check("%s : au moins une boite a filetypes" % rel, bool(hits) or rel == "UIViewer.py",
          str(len(hits)))
    for fname, pairs in hits:
        for desc, pat in pairs:
            key = "%s:%s(%s)" % (rel, fname, desc)
            all_pairs[key] = pat
            tokens = pat.split()
            bad = [t for t in tokens if "*" not in t and "?" not in t]
            check("%s -> %r : chaque motif contient un joker" % (key, pat), not bad, bad)
            check("%s -> %r : aucun motif ne commence par un point nu" % (key, pat),
                  not [t for t in tokens if t.startswith(".") and not t.startswith("*.")],
                  [t for t in tokens if t.startswith(".")])

check("les dialogues .ui des deux fichiers disent la meme chose",
      all(("*.ui" in p) for k, p in all_pairs.items() if "Fichiers UI" in k),
      {k: v for k, v in all_pairs.items() if "UI" in k})
check("il existe bien un filtre .ui pour le menu PyQt5",
      any(k.startswith("__init__.py") and v == "*.ui" for k, v in all_pairs.items()),
      sorted(all_pairs))
check('et un « tous les fichiers » *.* pour le repli',
      all(v == "*.*" for k, v in all_pairs.items() if "Tous" in k),
      {k: v for k, v in all_pairs.items() if "Tous" in k})
check("plus aucun motif « designer.exe *.exe » melange",
      not [k for k, v in all_pairs.items() if "designer.exe" in v], sorted(all_pairs))

print("=== 2. ce que le motif mort donnait vraiment ===")
fichiers = ["eleve.py", "interface.ui", "bac2027.ui", "note.txt", "designer.exe"]
for vieux, neuf in ((".ui", "*.ui"), (".*", "*.*")):
    a_ancien = [f for f in fichiers if fnmatch.fnmatch(f, vieux)]
    a_nouveau = [f for f in fichiers if fnmatch.fnmatch(f, neuf)]
    check("l'ancien motif %r ne laisse passer aucun fichier" % vieux, a_ancien == [], a_ancien)
    check("le motif %r montre ce qu'on attend" % neuf, bool(a_nouveau), a_nouveau)
check("« *.ui » ne montre que les interfaces",
      [f for f in fichiers if fnmatch.fnmatch(f, "*.ui")] == ["interface.ui", "bac2027.ui"],
      [f for f in fichiers if fnmatch.fnmatch(f, "*.ui")])
melange = [f for f in fichiers if fnmatch.fnmatch(f, "designer.exe")
           or fnmatch.fnmatch(f, "*.exe")]
check("l'ancienne entree Designer montrait deja tous les .exe, rien de plus",
      melange == ["designer.exe"], melange)
check("le motif « *.exe » retient designer.exe : le filtre n'a pas etretréci",
      [f for f in fichiers if fnmatch.fnmatch(f, "*.exe")] == ["designer.exe"],
      [f for f in fichiers if fnmatch.fnmatch(f, "*.exe")])
check("en revanche son « Tous les fichiers » .* etait mort",
      [f for f in fichiers if fnmatch.fnmatch(f, ".*")] == [],
      [f for f in fichiers if fnmatch.fnmatch(f, ".*")])

print("=== 3. les appels restent branches sur le workbench ===")
with io.open(os.path.join(PLUGIN, "__init__.py"), encoding="utf-8") as fh:
    src_init = fh.read()
tree_init = ast.parse(src_init)
opens = []


class FindOpen(ast.NodeVisitor):
    def visit_Call(self, node):
        fname = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if fname in ("askopenfilename", "asksaveasfilename"):
            opens.append((fname, {k.arg for k in node.keywords}))
        self.generic_visit(node)


FindOpen().visit(tree_init)
check("__init__.py ouvre bien deux boites", len(opens) == 2, opens)
for fname, kwargs in opens:
    check("%s : parent donne pour que la boite reste sur Thonny" % fname,
          "parent" in kwargs, sorted(kwargs))
    check("%s : filetypes present" % fname, "filetypes" in kwargs, sorted(kwargs))

print("\n%d checks, %d echecs" % (N[0], len(FAILS)))
for f in FAILS:
    print("ECHEC " + f)
sys.exit(1 if FAILS else 0)
