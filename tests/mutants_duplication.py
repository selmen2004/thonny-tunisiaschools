r"""Notation par mutants de la fabrique de noms (item 14).

Une suite verte ne prouve pas qu'elle regarde. Chaque mutant ci-dessous est une
faute que le code a vraiment pu contenir — la reparation oubliee, deplacee dans
la boucle ou arrivee trop tard, les noms du fichier qui ne comptent plus, la
forme recopiee au lieu d'appellee, le repli qui rend une chaine vide. Un mutant
survivant signale une regle que test_duplication.py ne voit pas.

Le paquet livre n'est jamais touche : chaque mutant est une COPIE de UIViewer.py,
chargee par un fils qui lance la suite. La suite lit le produit depuis la
variable d'environnement TUNISIASCHOOLS_COPIE, donc son pere et le fils de mesure
du point 3 jugent la MEME copie — sinon la suite vérifierait le paquet livre
pendant qu'on en mutile un-double.

Deux verdicts ne sont pas des survies :
  • GEL — la suite n'a pas rendu de bilan avant son delai. C'est le gel de
    l'item 14 lui-meme, pas une note : les garde-fous de la suite (watchdogs,
    gate du geste) devaient le transformer en echecs. Un GEL demande a etre
    regarde de pres.
  • SUITE CRASH — la copie mutee fait planter la suite avant son bilan.

    Lancement :

    C:\...\Thonny\python.exe -B tests\mutants_duplication.py
"""
import io
import os
import re
import shutil
import subprocess
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(RACINE, "UIViewer.py")
SUITE = os.path.join(RACINE, "tests", "test_duplication.py")
BUNDLE = r"C:\Users\Selmen\AppData\Local\Programs\Thonny"
SITE = os.path.join(BUNDLE, "Lib", "site-packages")
# les copies mutilees et le fils qui les charge restent dans le tiroir ignore
ICI = os.path.join(RACINE, "tests", "_sortie", "mutants")
MUTANTS = os.path.join(ICI, "copies")
RUNNER = os.path.join(ICI, "_mut_run.py")
DELAI = 600

# (nom, [(texte a remplacer, remplacement), ...])
LISTE = [
    # la reparation de la base n'est plus appellée du tout : retour a l'item 14
    ("reparation_supprimee", [
        ("        base = self._base_reparee(base)\n", "")]),
    # reparee, mais TROP TARD : dans la boucle, plus avant elle
    ("reparation_tardive", [
        ("        base = self._base_reparee(base)\n", ""),
        ('                name = f"{base}{suffix}"\n            # le compteur',
         '                base = self._base_reparee(base)\n'
         '                name = f"{base}{suffix}"\n            # le compteur')]),
    # les noms que le fichier reserve hors du modele ne comptent plus
    ("sans_noms_hors_modele", [
        ("        used = self._used_names(exclude_idx) | self._noms_hors_modele()",
         "        used = self._used_names(exclude_idx)")]),
    # une base reparee serait rendue sans numero : « mon_bouton » serait vole a
    # l'eleve qui veut renommer « mon-bouton » dessus
    ("sans_numero_force", [
        ("        if a_repare or name in used or not self._valid_qt_name(name):",
         "        if name in used or not self._valid_qt_name(name):")]),
    # la regle de forme est recopiee dans le controle au lieu d'etre appelee
    ("forme_recopiee_dans_le_controle", [
        ("        return UiViewerPlugin._forme_valide(name)",
         "        first, rest = name[0], name[1:]\n"
         "        return (first.isalpha() or first == \"_\") and all(\n"
         "            c.isalnum() or c == \"_\" for c in rest)")]),
    # la forme accepterait un chiffre en tete
    ("chiffre_en_tete_accepte", [
        ('        return (first.isalpha() or first == "_") and all(',
         '        return (first.isalnum() or first == "_") and all(')]),
    # une base sans aucune lettre ne tombe plus sur une famille, mais sur vide
    ("sans_repli_sur_la_famille", [
        ("            return UiViewerPlugin.NOM_DE_RECHANGE",
         '            return ""')]),
    # deux ponctuations d'affilee laisseraient deux « _ »
    ("ponctuation_non_repliee", [
        ('        while "__" in reparee:\n'
         '            reparee = reparee.replace("__", "_")',
         "        pass")]),
    # le compteur ne retient plus le plus grand numero emis
    ("compteur_abandonne", [
        ("            self.widget_counter = max(self.widget_counter, suffix)",
         "            pass")]),
    # le clic ne passe plus par la fabrique : il recycle le nom de l'original
    ("duplicate_saute_la_fabrique", [
        ('        new_props["name"] = self._unique_name(stem)',
         '        new_props["name"] = stem')]),
    # le clic retire les chiffres du milieu du nom au lieu de la fin
    ("tige_mal_degeree", [
        ('        stem = props.get("name", "").rstrip("0123456789") or short',
         '        stem = props.get("name", "") or short')]),
    # les <widget> du fichier compteraient comme reserves hors modele
    ("hors_modele_compte_les_widgets", [
        ('            if el.tag in ("layout", "action"):',
         '            if el.tag in ("layout", "action", "widget"):')]),
    # un nom en __double__ ne serait plus tenu pour reserve
    ("dunder_non_reserve", [
        ('            return "dunder"', "            return None")]),
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
    """Imprime sans mourir : la console Windows est en cp1252, les libelles des
    controles sont en francais."""
    code = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        print(texte)
    except UnicodeEncodeError:
        print(texte.encode(code, "replace").decode(code, "replace"))


def une(nom, paires):
    source = io.open(SOURCE, encoding="utf-8").read()
    for ancien, _nouveau in paires:
        if ancien not in source:
            return nom, "FRAPPE A COTE", ancien[:60]
    cible = os.path.join(MUTANTS, nom)
    chemin = copier_vers(cible)
    mute = source
    for ancien, nouveau in paires:
        mute = mute.replace(ancien, nouveau, 1)
    with io.open(chemin, "w", encoding="utf-8") as fh:
        fh.write(mute)
    t0 = time.time()
    try:
        p = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-B", RUNNER,
                            cible, SUITE],
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
        elif verdict not in ("TUE",) and not verdict.startswith("TUE"):
            incidents.append((nom, verdict))
        affiche("%-32s %-14s %s" % (nom, verdict, detail), )
    shutil.rmtree(ICI, ignore_errors=True)
    affiche("\n%d mutants, %d survivants, %d incidents"
            % (len(choisis), len(survivants), len(incidents)))
    if incidents:
        affiche("incidents (un gel n'est pas une note) : %s" % (incidents,))
    return 0 if not survivants and not incidents else 1


if __name__ == "__main__":
    sys.exit(main())
