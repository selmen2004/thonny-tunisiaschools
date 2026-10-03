r"""Notation par mutants de la cible de « Ouvrir dans Designer » (item 9).

`test_designer_cible.py` est verte : elle a été écrite après la correction, et
une suite écrite après ne prouve qu'une chose — qu'elle ne laisse pas le défaut
revenir. Encore faut-il montrer qu'elle *regarde* le bon bout du fil. Chaque
mutant ci-dessous est donc une faute que ce code a vraiment contenue, ou qu'un
refactor honeste aurait pu introduire :

  • `miroir_revenant` : l'état d'avant, quand `__init__.py` tenait son propre
    `qt_ui_file` et que seule « Ajouter Annexe + interface » le remplissait ;
  • `cible_memoisee` : la même distraction sous une forme neuve — un cache qui a
    l'air innocent puisqu'il est rempli depuis la vue ;
  • `sans_ancrage` : le `create=False` oublié, qui ouvre l'onglet de l'élève pour
    lui demander une information ;
  • `sans_verif_fichier`, `laisse_le_relatif`, `argument_jete` : les trois façons
    de transmettre un chemin qui n'est pas celui de l'écran ;
  • `menu_vide_apres_refus`, `onglet_monte_apres_refus` : les gestes d'à côté du
    refus, que l'item 13 a séparés et que l'item 9 a rendus visibles.

Un mutant survivant signale une règle qu'aucune des quatre suites ne voit.
C'est pourquoi la notation les lance toutes : la cible de l'item 9 traverse le
menu (« Ajouter Annexe + interface », test_editor_insert), le panneau de la vue
(test_travail) et la commande elle-même (test_designer, test_designer_cible).

Le paquet livré n'est jamais touché : chaque mutant est une copie, chargée par un
fils qui lance la suite, et la copie s'annonce par TUNISIASCHOOLS_COPIE pour que
les pins de source lisent le fichier mutilé, pas le fichier livre.
"""
import io
import os
import re
import shutil
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(RACINE, "__init__.py")
TESTS = os.path.join(RACINE, "tests")
# les suites qui peuvent voir une cible detournee, dans cet ordre : la moins
# chere d'abord, et on s'arrete des qu'une faute est vue. test_designer_live.py
# n'est pas dans la liste : elle demarre un vrai processus et depend du poste
# (Designer installe ou non) — elle a ete rearmee comme les autres et se lance
# dans la batterie, mais un mutant ne doit pas etre juge sur un poste.
SUITES = ["test_editor_insert.py", "test_designer_cible.py", "test_travail.py",
          "test_designer.py"]
# copies mutilees et fils qui les chargent restent dans le tiroir ignore
ICI = os.path.join(TESTS, "_sortie", "mutants_cible")
MUTANTS = os.path.join(ICI, "copies")
RUNNER = os.path.join(ICI, "_mut_run.py")
# le meme sens que run_all.py : un FAIL se compte depuis le debut de ligne, les
# blancs de devant compris — «   FAIL  ... » (test_travail) etait invisible
LIGNE_ECHEC = re.compile(r"^\s*FAIL[\s:]", re.I)

EN_TETE = "_dynamic_menu_labels = []"
LIT_LA_VUE = '    path = getattr(_vue_concepteur(), "ui_file", None) or ""'
GARDE_ET_MENU = ('        if not vue.load_new_ui_file(path):\n'
                 '            return\n'
                 '        _clear_dynamic_menu_items()')
TOUT_LE_BLOC = (GARDE_ET_MENU +
                '\n        get_workbench().show_view("UiViewerPlugin",True)')

# (nom, [(ancien, nouveau), ...]) — chaque `ancien` doit apparaitre UNE seule fois
LISTE = [
    # l'etat d'avant, rejoue tel quel : le module a son propre avis sur le
    # fichier de l'eleve, et seule la commande du menu le met a jour
    ("miroir_revenant", [
        (EN_TETE, EN_TETE + '\n\nqt_ui_file = ""'),
        ("def add_pyqt_code():\n    \n    btnstxt = \"\"",
         "def add_pyqt_code():\n    global qt_ui_file\n    btnstxt = \"\""),
        (LIT_LA_VUE, "    global qt_ui_file\n    path = qt_ui_file"),
        (GARDE_ET_MENU, GARDE_ET_MENU.replace("        _clear_dynamic_menu_items()",
                                              "        qt_ui_file = path\n"
                                              "        _clear_dynamic_menu_items()")),
    ]),
    # le cache qui parait inoffensif : il demande bien a la vue, une fois
    ("cible_memoisee", [
        (EN_TETE, EN_TETE + "\n_cible_memoire = None"),
        (LIT_LA_VUE,
         "    global _cible_memoire\n"
         "    if _cible_memoire is None:\n"
         '        _cible_memoire = getattr(_vue_concepteur(), "ui_file", None) or ""\n'
         "    path = _cible_memoire"),
    ]),
    # create=False oublie : la workbench construit l'onglet pour repondre
    ("sans_ancrage", [
        ('        return workbench.get_view("UiViewerPlugin", create=False)',
         '        return workbench.get_view("UiViewerPlugin")'),
    ]),
    # le fichier que l'eleve a ferme hors de Thonny est quand meme transmis
    ("sans_verif_fichier", [
        ("    if path and os.path.isfile(path):", "    if path:"),
    ]),
    # un chemin relatif de la vue part tel quel dans la ligne de commande
    ("laisse_le_relatif", [
        (LIT_LA_VUE + "\n    if path and os.path.isfile(path):\n"
         "        return os.path.abspath(path)",
         LIT_LA_VUE + "\n    if path and os.path.isfile(path):\n        return path"),
    ]),
    # le chemin est bien lu, puis jete avant d'atteindre designer.exe
    ("argument_jete", [
        ("        _run_designer(exe, ui_path)", '        _run_designer(exe, "")'),
    ]),
    # le menu est vide avant meme que la vue ait dit oui (l'item 13, a l'envers)
    ("menu_vide_apres_refus", [
        (GARDE_ET_MENU,
         "        _clear_dynamic_menu_items()\n"
         "        if not vue.load_new_ui_file(path):\n"
         "            return"),
    ]),
    # et l'onglet monte alors que la vue n'a rien ouvert
    ("onglet_monte_apres_refus", [
        (TOUT_LE_BLOC,
         '        get_workbench().show_view("UiViewerPlugin",True)\n'
         + GARDE_ET_MENU),
    ]),
]


def ecrire_runner():
    with io.open(RUNNER, "w", encoding="utf-8") as fh:
        fh.write(
            "import importlib.util, os, runpy, sys, types\n"
            "mut_init = sys.argv[1]\n"
            "mut_dir = os.path.dirname(mut_init)\n"
            "parent = types.ModuleType('thonnycontrib')\n"
            "parent.__path__ = [os.path.dirname(mut_dir)]\n"
            "sys.modules['thonnycontrib'] = parent\n"
            "spec = importlib.util.spec_from_file_location(\n"
            "    'thonnycontrib.tunisiaschools', mut_init, submodule_search_locations=[mut_dir])\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules[spec.name] = mod\n"
            "spec.loader.exec_module(mod)\n"
            "runpy.run_path(sys.argv[2], run_name='__main__')\n"
        )


def copier_vers(cible):
    """Une copie du paquet livre, sans les tests ni les traces."""
    if os.path.isdir(cible):
        shutil.rmtree(cible, ignore_errors=True)
    os.makedirs(cible)
    for nom in os.listdir(RACINE):
        source = os.path.join(RACINE, nom)
        if os.path.isfile(source) and nom.endswith(".py"):
            shutil.copy2(source, os.path.join(cible, nom))
    return os.path.join(cible, "__init__.py")


def mutiler(nom, editions):
    """Le dossier de la copie mutilee, ou la raison pour laquelle elle n'a pas
    pu etre ecrite. C'est le DOSSIER que les suites attendent dans
    TUNISIASCHOOLS_COPIE — pas le chemin de `__init__.py` : le passer par
    megarde double le nom de fichier et ne mute rien, tous les fils meurent en
    FileNotFoundError et chaque mutant se lit « SUITE CRASH »."""
    source = io.open(SOURCE, encoding="utf-8").read()
    for ancien, nouveau in editions:
        n = source.count(ancien)
        if n != 1:
            # une ancre qui manque ou qui tombe deux fois ne mute rien : elle
            # rendrait un verdict menteur (« survit » alors que rien n'a change)
            return None, "FRAPPE A COTE (%dx) : %r" % (n, ancien[:60])
        source = source.replace(ancien, nouveau, 1)
    if source == io.open(SOURCE, encoding="utf-8").read():
        return None, "FRAPPE A COTE (aucun changement)"
    cible = os.path.join(MUTANTS, nom)
    chemin = copier_vers(cible)
    with io.open(chemin, "w", encoding="utf-8") as fh:
        fh.write(source)
    return cible, None


def bilan_de(sortie):
    """(controles, echecs) lu sur la derniere ligne qui en porte un, ou None.

    L'ancre en debut de ligne est indispensable : la sortie de test_designer.py
    contient un titre de section, « === 5. les echecs, un par un === », qui
    s'est lu comme un total et a declare chaque mutant tue.
    """
    for ligne in reversed(sortie.splitlines()):
        t = ligne.strip()
        m = re.match(r"(\d+)/(\d+) checks passed", t, re.I)
        if m:
            fait, total = int(m.group(1)), int(m.group(2))
            return total, total - fait
        m = re.match(r"(\d+) (?:checks|controles?),\s*(\d+) echecs", t, re.I)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def jouer(suite, copie):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", TUNISIASCHOOLS_COPIE=copie)
    p = subprocess.run([sys.executable, "-B", RUNNER, os.path.join(copie, "__init__.py"),
                        os.path.join(TESTS, suite)],
                       cwd=TESTS, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, env=env)
    sortie = (p.stdout or "") + (p.stderr or "")
    # « FAIL » compte depuis le debut de ligne, blancs compris : test_travail
    # imprime «   FAIL  ... », et la ligne n'aurait jamais ete vue.
    echouees = []
    for l in sortie.splitlines():
        if LIGNE_ECHEC.match(l):
            t = l.split("  <-")[0].strip()
            if t not in echouees:
                echouees.append(t)
    rendu = bilan_de(sortie)
    total = "" if not rendu else ("%d echecs / %d controles" % (rendu[1], rendu[0]))
    if echouees:
        return True, False, (echouees[:3] + [total]) if total else echouees[:3], \
            p.returncode, sortie
    if rendu and rendu[1]:
        return True, False, [total], p.returncode, sortie
    if rendu:
        return False, False, [], p.returncode, sortie
    # aucune ligne de bilan : la suite n'est pas arrivee au bout
    return False, True, [], p.returncode, sortie


def une(nom, editions):
    copie, raison = mutiler(nom, editions)
    if copie is None:
        return nom, "FRAPPE A COTE", raison
    vus, incidents = [], []
    for suite in SUITES:
        try:
            tuee, crash, exemples, code, sortie = jouer(suite, copie)
        except subprocess.TimeoutExpired:
            # une suite qui ne rend plus l'eleve attend encore : la faute est vue
            vus.append(suite + " (TIMEOUT)")
            break
        if tuee:
            vus.append("%s (%s)" % (suite, "; ".join(exemples))[:160])
            break
        if crash or code:
            incidents.append("%s : %s" % (suite, (sortie.strip().splitlines()
                                                  or ["(aucune sortie)"])[-1][:100]))
    if vus:
        return nom, "TUE", vus[-1]
    if incidents:
        return nom, "SUITE CRASH", "%d suite(s) ; %s" % (len(incidents), incidents[0])
    return nom, "SURVIVANT", ""


def point_de_partage():
    """Le harnais d'abord, les mutants ensuite.

    Une copie SANS faute, jouee contre les quatre suites, doit rendre quatre
    suites vertes. Si elle ne rend que des crashes, c'est la cablage qui est
    faux — le chemin de la copie, l' injection du module, la variable
    d'environnement — et tous les mutants se liraient « SUITE CRASH » sans que
    rien ne soit prouve de la valeur des suites. (Mesure : la premiere version
    de ce fichier donnait le chemin de `__init__.py` la ou les suites attendent
    le dossier, et les huit mutants ont rendu le meme crash identique.)"""
    copie = os.path.join(MUTANTS, "point_de_partage")
    source = io.open(SOURCE, encoding="utf-8").read()
    with io.open(copier_vers(copie), "w", encoding="utf-8") as fh:
        fh.write(source)
    casses = []
    for suite in SUITES:
        try:
            tuee, crash, exemples, code, sortie = jouer(suite, copie)
        except subprocess.TimeoutExpired:
            casses.append("%s : TIMEOUT" % suite)
            continue
        if tuee or crash or code:
            dernier = (sortie.strip().splitlines() or ["(aucune sortie)"])[-1]
            casses.append("%s : %s" % (suite, (exemples or [dernier])[0])[:140])
    return casses


def main():
    if os.path.isdir(ICI):
        shutil.rmtree(ICI, ignore_errors=True)
    os.makedirs(ICI)
    ecrire_runner()
    casses = point_de_partage()
    if casses:
        shutil.rmtree(ICI, ignore_errors=True)
        print("HARNAIS CASSE : la copie sans faute ne rend pas les suites vertes.")
        for ligne in casses:
            print("  " + ligne)
        print("\n0 mutant note, %d suite(s) hors service" % len(casses))
        return 1
    print("point de partage : %d suites vertes sur une copie intacte\n" % len(SUITES),
          flush=True)
    survivants = []
    for entree in LISTE:
        nom, verdict, detail = une(*entree)
        if verdict in ("SURVIVANT", "FRAPPE A COTE", "SUITE CRASH"):
            survivants.append(nom)
        print("%-26s %-13s %s" % (nom, verdict, detail), flush=True)
    shutil.rmtree(ICI, ignore_errors=True)
    print("\n%d mutants, %d survivants ou incidents" % (len(LISTE), len(survivants)))
    return 0 if not survivants else 1


if __name__ == "__main__":
    sys.exit(main())
