r"""Notation par mutants de la decouverte et de l'installation de Designer.

Une suite verte ne prouve pas qu'elle regarde : elle peut ne tester que ce qui
etait deja vrai. Chaque mutant ci-dessous est une faute que le code a vraiment
pu contenir — le dossier de l'eleve qui devient un candidat, la recherche qui
s'arrete au premier chemin absent, le --user qui depose trois fichiers tout
seuls, l'environnement prete qui salit celui de Thonny. Un mutant survivant
signale une regle que test_designer.py ne voit pas.

Le paquet livre n'est jamais touche : chaque mutant est une copie, chargee par
un fils qui lance la suite.
"""
import io
import os
import shutil
import subprocess
import sys

import chemins

RACINE = chemins.PAQUET
SOURCE = os.path.join(RACINE, "__init__.py")
SUITE = os.path.join(chemins.TESTS, "test_designer.py")
# les copies mutilees et le fils qui les charge restent dans le tiroir ignore,
# jamais a cote des suites versionnees
ICI = os.path.join(chemins.TESTS, "_sortie", "mutants")
MUTANTS = os.path.join(ICI, "copies")
RUNNER = os.path.join(ICI, "_mut_run.py")

# (nom, texte a remplacer, remplacement)
LISTE = [
    # un chemin relatif de sys.path = le dossier ou travaille l'eleve
    ("chemin_relatif_accepte",
     "        if not entree or not os.path.isabs(entree):\n            continue",
     "        if not entree:\n            continue"),
    # aucun filtre : ni l'entree vide, ni l'entree relative ne sont ecartees
    ("aucun_filtre_de_sys_path",
     "        if not entree or not os.path.isabs(entree):\n            continue",
     "        if False:\n            continue"),
    ("recherche_qui_s_arrete",
     "        exe = _resolve_designer(candidate)\n        if exe:\n            return os.path.abspath(exe)",
     "        exe = _resolve_designer(candidate)\n        if not exe:\n            return None\n        return os.path.abspath(exe)"),
    ("which_avec_le_dossier_courant",
     "    for folder in (os.environ.get(\"PATH\") or \"\").split(os.pathsep):",
     "    for folder in [os.getcwd()] + (os.environ.get(\"PATH\") or \"\").split(os.pathsep):"),
    ("pip_avec_user",
     "            \"--disable-pip-version-check\", \"--progress-bar\", \"off\", paquet]",
     "            \"--disable-pip-version-check\", \"--progress-bar\", \"off\",\n            \"--user\", paquet]"),
    ("cherche_avant_de_proposer",
     "        reponse = _proposer_installation_designer()",
     "        _ask_for_designer()\n        reponse = _proposer_installation_designer()"),
    ("le_refus_installe_quand_meme",
     "    if not messagebox.askyesno(\n        \"Qt Designer\",\n        \"Qt Designer n'est pas installé sur ce poste.\\n\\n\"\n        \"L'installer maintenant ?",
     "    if False and not messagebox.askyesno(\n        \"Qt Designer\",\n        \"Qt Designer n'est pas installé sur ce poste.\\n\\n\"\n        \"L'installer maintenant ?"),
    ("echec_deja_dit_repasse_par_erreur",
     "        if reponse is None:\n            # l'installation a été tentée et a échoué : l'enseignant l'a déjà lu\n            return False",
     "        if reponse is None:\n            pass"),
    ("environnement_salit",
     "    env = os.environ.copy()",
     "    env = os.environ"),
    ("sans_pret_des_plugins",
     "            env[\"QT_QPA_PLATFORM_PLUGIN_PATH\"] = plateformes",
     "            pass"),
    ("sans_le_lanceur_de_pip",
     "        \"pyqt5_qt5_designer.exe\",   # le lanceur que pip crée dans Scripts\\",
     "        # le lanceur de pip n'est plus proposé"),
    ("publicite_du_vieux_module",
     "        \"    pip install %s\\n\\n\"",
     "        \"    pip install pyqt5-designer (ou %s)\\n\\n\""),
    ("le_vieux_module_devient_la_norme",
     "PAQUET_DESIGNER = \"pyqt5-qt5-designer\"",
     "PAQUET_DESIGNER = \"pyqt5-designer\""),
    ("double_candidat_garde",
     "        if candidate and candidate not in retenus:",
     "        if candidate:"),
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


def une(nom, ancien, nouveau):
    source = io.open(SOURCE, encoding="utf-8").read()
    if ancien not in source:
        return nom, "FRAPPE A COTE", ""
    cible = os.path.join(MUTANTS, nom)
    chemin = copier_vers(cible)
    with io.open(chemin, "w", encoding="utf-8") as fh:
        fh.write(source.replace(ancien, nouveau, 1))
    p = subprocess.run([sys.executable, "-B", RUNNER, chemin, SUITE],
                       cwd=os.path.dirname(SUITE), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    sortie = (p.stdout or "") + (p.stderr or "")
    echouees = [l.split("  <-")[0].strip() for l in sortie.splitlines()
                if l.startswith("FAIL")]
    if "checks passed" not in sortie:
        return nom, "SUITE CRASH", sortie.strip().splitlines()[-3:]
    if echouees:
        return nom, "TUE (%d)" % len(echouees), echouees[:3]
    return nom, "SURVIVANT", []


def main():
    if os.path.isdir(ICI):
        shutil.rmtree(ICI, ignore_errors=True)
    os.makedirs(ICI)
    ecrire_runner()
    survivants = []
    for entree in LISTE:
        nom, verdict, detail = une(*entree)
        if verdict == "SURVIVANT":
            survivants.append(nom)
        print("%-34s %-12s %s" % (nom, verdict, detail), flush=True)
    shutil.rmtree(ICI, ignore_errors=True)
    print("\n%d mutants, %d survivants" % (len(LISTE), len(survivants)))
    return 0 if not survivants else 1


if __name__ == "__main__":
    sys.exit(main())
