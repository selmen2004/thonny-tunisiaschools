r"""Notation par mutants de « Nouveau » (item 7 du re-audit).

Une suite verte ne prouve pas qu'elle regarde. Chaque mutant ci-dessous est une
faute que ce code a vraiment pu contenir : la remise a zero de l'identite
oubliee ou partielle (un seul des quatre champs), placee AVANT la question de
l'item 13, le panneau de proprietes qui n'est pas lache, deux endroits qui
decident ce qu'est un document neuf et qui ne sont plus d'accord, l'arbre XML
qui survit, le canevas qui n'est pas repeint. Un mutant survivant signale une
regle que test_nouveau.py ne voit pas.

Le paquet livre n'est jamais touche : chaque mutant est une COPIE de UIViewer.py
posee dans tests\_sortie\mutants_nouveau\, chargee par un fils qui lance la
suite. La suite lit le produit depuis la variable d'environnement
TUNISIASCHOOLS_COPIE, donc elle et ses probes Qt jugent la MEME copie.

Un ancrage compte, pas seulement « present » : une ancre qui frappe deux fois
muerait a cote du but en silence (la lecon de mutants_designer.py).

    Lancement :
    C:\...\Thonny\python.exe -B tests\mutants_nouveau.py
"""
import io
import os
import re
import shutil
import subprocess
import sys
import time

import chemins

RACINE = chemins.PAQUET
SOURCE = os.path.join(RACINE, "UIViewer.py")
SUITE = os.path.join(chemins.TESTS, "test_nouveau.py")
BUNDLE = chemins.BUNDLE
SITE = os.path.join(BUNDLE, "Lib", "site-packages")
ICI = os.path.join(chemins.TESTS, "_sortie", "mutants_nouveau")
MUTANTS = os.path.join(ICI, "copies")
RUNNER = os.path.join(ICI, "_mut_run.py")
DELAI = 600

REMISER = ("        # voir _racine_neuve.\n"
           "        self._racine_neuve()\n")
LACHE_PANNEAU = ("        # dans le fichier, il etait sous la main de l'eleve.\n"
                 "        self._show_no_selection()\n")
DEFAUTS_CONSTRUCTEUR = (
    "        # Identite de la fenetre d'un document neuf : nom, classe, taille, "
    "titre.\n"
    "        # Un seul endroit la decide (voir _racine_neuve), parce que le\n"
    "        # constructeur et \u00ab Nouveau \u00bb doivent poser la MEME fenetre vide.\n"
    "        self._racine_neuve()\n")
# la MEME chose, mais recopiee a la main dans le constructeur : c'est le geste
# qui laisse « Nouveau » decider seul d'un champ de plus.
DEFAUTS_LITTERAUX = (
    '        self.root_widget_name = "Form"\n'
    '        self.root_widget_class = "QDialog"\n'
    "        self.root_geometry = (0, 0, 640, 480)\n"
    '        self.root_title = "Form"\n')

# (nom, [(texte a remplacer, remplacement), ...])
LISTE = [
    # le defaut de l'item 7, pur : rien n'est remis
    ("identite_jamais_remise", [(REMISER, "")]),
    # remise partielle : seule la taille repart, comme avant la correction
    ("que_la_taille", [(REMISER,
                        "        self.root_geometry = (0, 0, 640, 480)\n")]),
    # le nom seul repart
    ("nom_seul_repare", [(REMISER,
                          '        self.root_widget_name = "Form"\n')]),
    # un des quatre champs manque dans la definition du document neuf. Le
    # constructeur garde ses quatre litteraux (sinon c'est UIViewer qui plante
    # sur sa propre lecture de self.root_geometry, et un crash du produit n'est
    # pas une note) : « Nouveau » seul oublie le champ, et il le laisse donc
    # herite du fichier. L'ordre des deux gestes importe : la suppression se
    # fait AVANT la copie, sinon replace(…, 1) effacerait le litteral du
    # constructeur, qui est plus haut dans le fichier, et non celui de
    # _racine_neuve.
    ("nom_oublie", [('        self.root_widget_name = "Form"\n', ""),
                    (DEFAUTS_CONSTRUCTEUR, DEFAUTS_LITTERAUX)]),
    ("classe_oubliee", [('        self.root_widget_class = "QDialog"\n', ""),
                        (DEFAUTS_CONSTRUCTEUR, DEFAUTS_LITTERAUX)]),
    ("titre_oublie", [('        self.root_title = "Form"\n', ""),
                      (DEFAUTS_CONSTRUCTEUR, DEFAUTS_LITTERAUX)]),
    ("taille_oubliee", [("        self.root_geometry = (0, 0, 640, 480)\n", ""),
                        (DEFAUTS_CONSTRUCTEUR, DEFAUTS_LITTERAUX)]),
    # le panneau de proprietes garde le widget supprime sous la main de l'eleve
    ("panneau_non_lache", [(LACHE_PANNEAU, "        pass\n")]),
    # la remise a zero arrive AVANT la question : « non » a vide la fenetre
    ("avant_la_question", [
        (REMISER, ""),
        ("    def _new(self):\n",
         "    def _new(self):\n        self._racine_neuve()\n")]),
    # deux endroits decident le document neuf, et ils ne sont plus d'accord
    ("deux_defauts_differents", [(
        DEFAUTS_CONSTRUCTEUR,
        '        self.root_widget_name = "Form"\n'
        '        self.root_widget_class = "QDialog"\n'
        "        self.root_geometry = (0, 0, 640, 480)\n"
        '        self.root_title = "Nouvelle fenetre"\n')]),
    # l'arbre XML du fichier precedent survit : la prochaine ecriture fusionne
    ("arbre_source_garde", [("        self._source_ui = None\n", "")]),
    # l'onglet continue d'afficher le nom de l'ancien fichier
    ("onglet_garde", [('        self._title_lbl.config(text="Sans titre")\n',
                       "")]),
    # la numerotation heritee du fichier precedent reste
    ("compteur_garde", [("        self.widget_counter = 0\n"
                         "        self.selected_idx = None\n",
                         "        self.selected_idx = None\n")]),
    # la selection heritee reste pointee sur un widget qui n'existe plus
    ("selection_gardee", [("        self.widget_counter = 0\n"
                           "        self.selected_idx = None\n",
                           "        self.widget_counter = 0\n")]),
    # l'historique et le drapeau « non enregistre » survivent au Nouveau
    ("historique_garde", [("        self.reset_history()\n"
                           '        self._title_lbl.config(text="Sans titre")\n',
                           '        self._title_lbl.config(text="Sans titre")\n')]),
    # le canevas n'est pas repeint : les anciens rectangles restent poses
    ("canevas_non_repeint", [("        self._refresh()\n"
                              "        # Le panneau de proprietes lache aussi",
                              "        # Le panneau de proprietes lache aussi")]),
]

BILAN = re.compile(r"(\d+) checks?,\s*(\d+) echecs", re.I)
LIGNE_ECHEC = re.compile(r"^\s*FAIL[\s:]")


def ecrire_runner():
    with io.open(RUNNER, "w", encoding="utf-8") as fh:
        fh.write(
            "import os, runpy, sys\n"
            "copie = os.path.abspath(sys.argv[1])\n"
            "sys.path.insert(0, %r)\n"
            "sys.path.insert(0, copie)\n"
            "os.environ['TUNISIASCHOOLS_COPIE'] = copie\n"
            "import UIViewer\n"
            "assert os.path.abspath(UIViewer.__file__) == "
            "os.path.join(copie, 'UIViewer.py'), UIViewer.__file__\n"
            "print('COPIE=' + UIViewer.__file__, flush=True)\n"
            "runpy.run_path(sys.argv[2], run_name='__main__')\n" % SITE)


def copier_vers(cible):
    """Une copie du paquet livre, sans les tests ni les traces."""
    if os.path.isdir(cible):
        shutil.rmtree(cible, ignore_errors=True)
    os.makedirs(cible)
    for nom in os.listdir(RACINE):
        source = os.path.join(RACINE, nom)
        if os.path.isfile(source) and nom.endswith(".py"):
            shutil.copy2(source, os.path.join(cible, nom))
    return os.path.join(cible, "UIViewer.py")


def affiche(texte):
    """Imprime sans mourir : la console Windows est en cp1252, les libelles sont
    en francais."""
    code = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        print(texte)
    except UnicodeEncodeError:
        print(texte.encode(code, "replace").decode(code, "replace"))


def une(nom, paires):
    source = io.open(SOURCE, encoding="utf-8").read()
    for ancien, _nouveau in paires:
        n = source.count(ancien)
        if n != 1:
            return nom, "FRAPPE A COTE", "%dx %s" % (n, ancien[:60])
    cible = os.path.join(MUTANTS, nom)
    chemin = copier_vers(cible)
    mute = source
    for ancien, nouveau in paires:
        mute = mute.replace(ancien, nouveau, 1)
    with io.open(chemin, "w", encoding="utf-8") as fh:
        fh.write(mute)
    try:
        compile(mute, chemin, "exec")
    except SyntaxError as e:
        return nom, "MUTANT CASSE", str(e)[:80]
    try:
        p = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-u", "-B",
                            RUNNER, cible, SUITE],
                           cwd=os.path.dirname(SUITE), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=DELAI)
    except subprocess.TimeoutExpired:
        return nom, "GEL", "aucun bilan apres %ds" % DELAI
    sortie = (p.stdout or "") + (p.stderr or "")
    m = BILAN.search(sortie)
    if not m:
        return nom, "SUITE CRASH", sortie.strip().splitlines()[-3:]
    echouees = [l.split("  <-")[0].strip() for l in sortie.splitlines()
                if LIGNE_ECHEC.match(l)]
    if echouees:
        return nom, "TUE", "%s/%s echecs | %s" % (
            m.group(2), m.group(1), " ; ".join(e[:80] for e in echouees[:2]))
    return nom, "SURVIVANT", "%s controles, 0 echec" % m.group(1)


def main():
    choisis = [e for e in LISTE if not sys.argv[1:] or e[0] in sys.argv[1:]]
    if not choisis:
        print("aucun mutant ne porte ces noms : %s"
              % ", ".join(e[0] for e in LISTE))
        return 1
    if os.path.isdir(ICI):
        shutil.rmtree(ICI, ignore_errors=True)
    os.makedirs(ICI)
    ecrire_runner()
    survivants, incidents = [], []
    for nom, paires in choisis:
        nom, verdict, detail = une(nom, paires)
        if verdict == "SURVIVANT":
            survivants.append(nom)
        elif verdict != "TUE":
            incidents.append((nom, verdict))
        affiche("%-28s %-13s %s" % (nom, verdict, detail))
    shutil.rmtree(ICI, ignore_errors=True)
    affiche("\n%d mutants, %d survivants, %d incidents"
            % (len(choisis), len(survivants), len(incidents)))
    if incidents:
        affiche("incidents (un gel ou un crash n'est pas une note) : %s"
                % (incidents,))
    return 0 if not survivants and not incidents else 1


if __name__ == "__main__":
    sys.exit(main())
