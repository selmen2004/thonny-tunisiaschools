r"""Notation par mutants du menage d'actions (item 12).

`test_connexions.py` section 6 est verte, mais elle a ete ecrite apres la
correction. Pour qu'elle vaille quelque chose, il faut montrer qu'elle regarde
bien la place de l'action dans l'arbre et pas autre chose. Chaque mutant
ci-dessous est une faute que ce code a vraiment contenue, ou qu'un refactor
honnete aurait pu y mettre :

  • `appel_ote` : l'etat d'avant — l'ecriture ne remontait rien, le fichier
    sortait avec son bloc de racine et l'eleve avait son AttributeError ;
  • `repare_a_laffichage` : le meme menage, appele au mauvais endroit — la
    fusion qui sert a l'affichage. La section 6 verifie que reparer est une
    decision d'ecriture ;
  • `garde_nom_ote` : l'action remonterait sur un nom que le formulaire porte
    deja, et `setupUi()` ecraserait l'un des deux attributs en silence ;
  • `sans_marquer_le_nom`, `doublon_monte_ussi` : la garde-fousse du nom ne
    marche plus qu'a moitie, deux actions du meme nom montent toutes les deux
    et le fichier de l'eleve porte deux declarations identiques ;
  • `greffe_a_la_queue`, `ordre_inverse` : l'action change de place dans le
    formulaire, ou les deux remontees se suivent a l'envers — le fichier ne
    ressemble plus a ce que Designer ecrit ;
  • `bloc_toujours_la` : le bloc vide reste sous `<ui>`, et un fichier repere
    a la main n'est pas plus propre qu'avant ;
  • `sans_exclusion_sans_nom` : une action sans nom est quand meme montee,
    sans rien que le chargeur puisse designer ;
  • `garde_formulaire_inverse` : la garde du formulaire ecrite a l'envers, et
    plus rien ne monte jamais.

Un onzieme avait ete note, `racine_comme_formulaire` (`return 0` remplace par
`form = root` quand il n'y a pas de formulaire) : il est equivalent, c'est-a-dire
qu'il ne change le comportement d'aucun fichier. Sans formulaire, le bloc d'actions
est sous la racine, donc le recensement des noms porte deja ses propres noms, et
toutes les actions sont refusees — comme avec la garde vraie. Un mutant qui ne
peut pas etre vu n'enseigne rien : il est retire de la liste, et la raison reste
ici pour qu'on ne le redecouvre pas.

Le paquet livre n'est jamais touche : chaque mutant est une copie du dossier,
et la copie s'annonce par TUNISIASCHOOLS_COPIE pour que la suite importe le
fichier mute.

Ce fichier ne s'appelle pas `test_*.py` : `run_all.py` ne le glob pas, un grade
n'est pas une suite.
"""
import io
import os
import re
import shutil
import subprocess
import sys

import chemins

RACINE = chemins.PAQUET
SOURCE = os.path.join(RACINE, "UIViewer.py")
TESTS = chemins.TESTS
SUITES = ["test_connexions.py"]
ICI = os.path.join(TESTS, "_sortie", "mutants_actions")
MUTANTS = os.path.join(ICI, "copies")
LIGNE_ECHEC = re.compile(r"^\s*FAIL[\s:]", re.I)

APPEL = '            self._remonte_actions(root)'
BOUCLE = ('        for el in list(bloc):\n'
          '            if el.tag != "action" or not el.get("name"):\n'
          '                continue\n'
          '            if el.get("name") in pris:\n'
          '                continue\n'
          '            bloc.remove(el)\n'
          '            form.insert(index + remontees, el)\n'
          '            pris.add(el.get("name"))\n'
          '            remontees += 1')
GARDE = ('            if el.get("name") in pris:\n'
         '                continue')
MARQUE = '            pris.add(el.get("name"))'
INSERT = '            form.insert(index + remontees, el)'
SANS_NOM = '            if el.tag != "action" or not el.get("name"):'
INDEX = ('        index = next((i for i, fils in enumerate(form)\n'
         '                      if fils.tag in ("widget", "layout", "action")),'
         ' len(form))')
NETTOYAGE = '        if not len(bloc):\n            root.remove(bloc)'
FORM = ('        form = root.find("widget")\n'
        '        if form is None:\n'
        '            return 0')
MERGE_TAIL = ('        if table is not None:\n'
              '            table["rennames"] = rennames\n'
              '            table["liberes"] = liberes\n'
              '        return root')

# l'ecriture d'avant la garde-fousse du nom : les partantes sont choisies d'un
# coup, sur un instantane des noms, et rien ne marque celles qui sont montees
ANCIENNE_PASSE = ('        candidats = [el for el in bloc\n'
                  '                     if el.tag == "action" and el.get("name")\n'
                  '                     and el.get("name") not in pris]\n'
                  '        for k, el in enumerate(candidats):\n'
                  '            bloc.remove(el)\n'
                  '            form.insert(index + k, el)\n'
                  '            pris.add(el.get("name"))\n'
                  '        remontees = len(candidats)')

# (nom, [(ancien, nouveau), ...]) — chaque `ancien` doit apparaitre UNE seule fois
LISTE = [
    ("appel_ote", [(APPEL, "            pass")]),
    ("repare_a_laffichage", [
        (APPEL, "            pass"),
        (MERGE_TAIL, MERGE_TAIL.replace(
            "        return root", "        self._remonte_actions(root)\n"
                                   "        return root")),
    ]),
    ("garde_nom_ote", [(GARDE, "            pass")]),
    ("sans_marquer_le_nom", [(MARQUE, "            pass")]),
    ("doublon_monte_ussi", [(BOUCLE, ANCIENNE_PASSE)]),
    ("greffe_a_la_queue", [(INDEX, "        index = len(form)")]),
    ("ordre_inverse", [(INSERT, "            form.insert(index, el)")]),
    ("bloc_toujours_la", [(NETTOYAGE, "        # le bloc reste, vide ou non")]),
    ("sans_exclusion_sans_nom", [(SANS_NOM, '            if el.tag != "action":')]),
    ("garde_formulaire_inverse", [(FORM, FORM.replace("if form is None:",
                                                      "if form is not None:"))]),
]


def copier_vers(cible):
    """Le DOSSIER de la copie — c'est lui que la suite attend dans
    TUNISIASCHOOLS_COPIE, pas le chemin d'un fichier."""
    if os.path.isdir(cible):
        shutil.rmtree(cible, ignore_errors=True)
    os.makedirs(cible)
    for nom in os.listdir(RACINE):
        source = os.path.join(RACINE, nom)
        if os.path.isfile(source) and nom.endswith(".py"):
            shutil.copy2(source, os.path.join(cible, nom))
    return cible


def mutiler(nom, editions):
    source = io.open(SOURCE, encoding="utf-8").read()
    for ancien, nouveau in editions:
        n = source.count(ancien)
        if n != 1:
            return None, "FRAPPE A COTE (%dx) : %r" % (n, ancien[:70])
        source = source.replace(ancien, nouveau, 1)
    if source == io.open(SOURCE, encoding="utf-8").read():
        return None, "FRAPPE A COTE (aucun changement)"
    cible = os.path.join(MUTANTS, nom)
    chemin = os.path.join(copier_vers(cible), "UIViewer.py")
    with io.open(chemin, "w", encoding="utf-8") as fh:
        fh.write(source)
    return cible, None


def bilan_de(sortie):
    """(controles, echecs) lu sur la derniere ligne qui en porte un.

    L'ancre en debut de ligne est indispensable : « les echecs, un par un » est
    un titre de section dans certaines suites, pas un total.
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
    p = subprocess.run([sys.executable, "-B", os.path.join(TESTS, suite)],
                       cwd=TESTS, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, env=env)
    sortie = (p.stdout or "") + (p.stderr or "")
    echouees = []
    for l in sortie.splitlines():
        if LIGNE_ECHEC.match(l):
            t = l.split("  <-")[0].split("  [")[0].strip()
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
            vus.append(suite + " (TIMEOUT)")
            break
        if tuee:
            vus.append("%s (%s)" % (suite, "; ".join(exemples))[:170])
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
    """Une copie SANS faute doit rendre la suite verte avant de noter quoi que ce
    soit : sinon c'est le cablage qui est faux, et chaque mutant se lirait
    « SUITE CRASH » sans rien prouver."""
    copie = os.path.join(MUTANTS, "point_de_partage")
    source = io.open(SOURCE, encoding="utf-8").read()
    with io.open(os.path.join(copier_vers(copie), "UIViewer.py"),
                 "w", encoding="utf-8") as fh:
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
    casses = point_de_partage()
    if casses:
        print("HARNAIS CASSE : la copie sans faute ne rend pas la suite verte.")
        for ligne in casses:
            print("  " + ligne)
        print("\n0 mutant note, %d suite(s) hors service" % len(casses))
        return 1
    print("point de partage : %d suite verte sur une copie intacte\n" % len(SUITES),
          flush=True)
    incidents = []
    for entree in LISTE:
        nom, verdict, detail = une(*entree)
        if verdict in ("SURVIVANT", "FRAPPE A COTE", "SUITE CRASH"):
            incidents.append(nom)
        print("%-24s %-13s %s" % (nom, verdict, detail), flush=True)
    shutil.rmtree(ICI, ignore_errors=True)
    print("\n%d mutants, %d survivants ou incidents" % (len(LISTE), len(incidents)))
    return 0 if not incidents else 1


if __name__ == "__main__":
    sys.exit(main())
