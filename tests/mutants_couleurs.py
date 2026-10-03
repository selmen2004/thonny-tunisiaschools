r"""Notation par mutants du filtre de declarations de couleur (item 11).

`test_couleurs.py` section 8 est verte, mais elle a ete ecrite apres la
correction. Pour qu'elle vaille quelque chose, il faut montrer qu'elle regarde
bien le nom de la propriete et pas autre chose. Chaque mutant ci-dessous est une
faute que ce code a vraiment contenue, ou qu'un refactor honnete aurait pu y
mettre :

  • `sous_chaine_revient` : l'etat d'avant — `css_prop + ":" not in l`, qui
    detruisait « background-color » des qu'on choisissait une couleur de texte ;
  • `sans_minuscules`, `sans_strip_nom` : la normalisation du nom oubliee a
    moitie, une feuille ecrite « COLOR : … » n'est plus reconnue comme la
    couleur du texte et se retrouve doublee ;
  • `couper_au_dernier` : couper au dernier deux-points prend le nom du cote de
    la valeur, ce qui rate toute les feuilles dont la valeur contient un
    deux-points (`qlineargradient(x1:0, …)`) ;
  • `ligne_entiere` : comparer la ligne au lieu du nom ne remplace plus rien,
    chaque choix ajoute une declaration ;
  • `remplace_tout` : le filtre abandonne, les anciennes couleurs restent ;
  • `efface_voisines` : l'exc inverse, a force de vouloir faire propre on
    n'imprime plus que la couleur choisie ;
  • `sans_strip_feuille` : detail d'ecriture, mais l'espace trainant est ce que
    l'eleve lit dans son fichier ;
  • `champs_inverses` : le panneau branche le champ « Texte » sur la propriete
    du fond — le fond de l'eleve est ecrase sans qu'il ait demande ;
  • `lecture_en_sous_chaine`, `lecture_couleur_preferee`,
    `lecture_non_normalisee` : la meme faute de nom, mais dans le sens lecture —
    l'apercu peint alors la teinte d'une autre regle (`alternate-background-color`
    prend la place du fond), ou ne retrouve plus la couleur d'une feuille ecrite
    en majuscules.

Le paquet livre n'est jamais touche : chaque mutant est une copie du dossier,
et la copie s'annonce par TUNISIASCHOOLS_COPIE pour que la suite importe le
fichier mute — et lise ses propres pins de source dans le fichier mute.
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
# la suite proprietaire d'abord, puis les deux autres qui appellent _set_color :
# la notation s'arrete des qu'une faute est vue.
SUITES = ["test_couleurs.py", "test_effacement.py", "test_travail.py"]
ICI = os.path.join(TESTS, "_sortie", "mutants_couleurs")
MUTANTS = os.path.join(ICI, "copies")
LIGNE_ECHEC = re.compile(r"^\s*FAIL[\s:]", re.I)

FILTRE = ('        lines = [l.strip() for l in ss.split(";")\n'
          '                 if l.strip() and self._nom_de_declaration(l) != css_prop]')
NOM = '        return ligne.split(":", 1)[0].strip().lower()'
APPEL_TEXTE = '                self._set_color(idx, "color", c)'
LECTURE_COLOR = '            if nom == "color":'
LECTURE_FOND = '            elif nom in ("background", "background-color"):'
LECTURE_NOM = '            nom = self._nom_de_declaration(part)'

# (nom, [(ancien, nouveau), ...]) — chaque `ancien` doit apparaitre UNE seule fois
LISTE = [
    ("sous_chaine_revient", [
        (FILTRE, '        lines = [l.strip() for l in ss.split(";")\n'
                 '                 if l.strip() and css_prop + ":" not in l]'),
    ]),
    ("sans_minuscules", [
        (NOM, '        return ligne.split(":", 1)[0].strip()'),
    ]),
    ("sans_strip_nom", [
        (NOM, '        return ligne.split(":", 1)[0].lower()'),
    ]),
    ("couper_au_dernier", [
        (NOM, '        return ligne.rsplit(":", 1)[0].strip().lower()'),
    ]),
    ("ligne_entiere", [
        (FILTRE, '        lines = [l.strip() for l in ss.split(";")\n'
                 '                 if l.strip() != css_prop]'),
    ]),
    ("remplace_tout", [
        (FILTRE, '        lines = [l.strip() for l in ss.split(";") if l.strip()]'),
    ]),
    ("efface_voisines", [
        (FILTRE, '        lines = [l.strip() for l in ss.split(";")\n'
                 '                 if l.strip() and self._nom_de_declaration(l) == css_prop]'),
    ]),
    ("sans_strip_feuille", [
        (FILTRE, '        lines = [l for l in ss.split(";")\n'
                 '                 if l.strip() and self._nom_de_declaration(l) != css_prop]'),
    ]),
    ("champs_inverses", [
        (APPEL_TEXTE, '                self._set_color(idx, "background-color", c)'),
    ]),
    # la meme sous-chaine, mais dans le sens lecture : « alternate-background-color »
    # devient la couleur de fond du widget, et l'apercu ment a l'eleve
    ("lecture_en_sous_chaine", [
        (LECTURE_FOND, '            elif "background-color" in nom:'),
    ]),
    # et « selection-color » devient la couleur du texte
    ("lecture_couleur_preferee", [
        (LECTURE_COLOR, '            if "color" in nom:'),
    ]),
    # le nom n'est plus normalise : une feuille ecrite en majuscules ou avec un
    # espace avant les deux-points n'est plus reconnue du tout
    ("lecture_non_normalisee", [
        (LECTURE_NOM, '            nom = part.split(":", 1)[0]'),
    ]),
]


def copier_vers(cible):
    """Le DOSSIER de la copie — c'est lui que les suites attendent dans
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
    """Une copie SANS faute doit rendre les trois suites vertes avant de noter
    quoi que ce soit : sinon c'est le cablage qui est faux, et chaque mutant se
    lirait « SUITE CRASH » sans rien prouver."""
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
        print("HARNAIS CASSE : la copie sans faute ne rend pas les suites vertes.")
        for ligne in casses:
            print("  " + ligne)
        print("\n0 mutant note, %d suite(s) hors service" % len(casses))
        return 1
    print("point de partage : %d suites vertes sur une copie intacte\n" % len(SUITES),
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
