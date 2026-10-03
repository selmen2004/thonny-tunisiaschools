r"""Notation par mutants de la taille des tableaux (item 8).

Une suite verte ne prouve pas qu'elle regarde. Chaque mutant ci-dessous est une
faute que ce code a vraiment pu contenir — ou qu'il a contenue : la porte du
champ supprimee ou placee apres la conversion, la couleur sans l'explication,
l'explication qui ne s'efface plus, le negatif qui redevient une taille, le
plafond oublie, le plafond qui ne regarde plus le fichier, la tranche
`have[-1:]` qui remange un en-tete, l'ecriture neuve qui n'est pas bornee,
l'apercu qui dessine un million de cases. Un mutant survivant signale une regle
que test_tailles.py ne voit pas.

Deux regles de notation particulieres a cet item :

  • le GEL COMPTE COMO UNE NOTE : un mutant qui fait pendre la suite a justement
    ete vu par le watchdog de test_tailles.py, qui imprime son FAIL et sort au
    lieu d'attendre. C'est TUE, pas un incident ;
  • un ancrage compte, pas seulement « present » : une ancre qui frappe deux
    fois muerait a cote du but en silence.

Le paquet livre n'est jamais touche : chaque mutant est une COPIE de UIViewer.py
posee dans tests\_sortie\mutants_tailles\, chargee par un fils qui lance la
suite. La suite lit le produit depuis TUNISIASCHOOLS_COPIE, donc elle et ses
probes Qt jugent la MEME copie.

    Lancement :
    C:\...\Thonny\python.exe -B tests\mutants_tailles.py
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
SUITE = os.path.join(chemins.TESTS, "test_tailles.py")
BUNDLE = chemins.BUNDLE
SITE = os.path.join(BUNDLE, "Lib", "site-packages")
ICI = os.path.join(chemins.TESTS, "_sortie", "mutants_tailles")
MUTANTS = os.path.join(ICI, "copies")
RUNNER = os.path.join(ICI, "_mut_run.py")
DELAI = 900

# ——— ancres (texte exact du paquet livre, une seule fois chacun) ———
PORTE = (
    "            if key in (\"rows\", \"columns\"):\n"
    "                # La porte tient le texte BRUT, avant le cast : un \u00ab abc \u00bb comme\n"
    "                # un champ efface doivent etre refusees ET expliquees comme le\n"
    "                # nombre trop grand, pas s'evanouir dans le ValueError de la\n"
    "                # conversion \u2014 c'est la lecon de l'item 6, appliquee aux tailles.\n"
    "                if not self._accept_taille(key, saisi, props):\n"
    "                    return          # et la derniere taille qui s'inscrivait\n")
APRES_CAST = ("            value = cast(saisi)\n")
OUI_VERT = ("        if voulu is not None and voulu == admissible:\n"
            "            self._dit_taille(cle, \"\")\n"
            "            return True\n")
DIT_MOTIF = ("        self._dit_taille(cle, motif)\n        return False")
TEINTE = ("                entry.config(bg=\"#5a1a1a\" if motif else \"#3c3c3c\")")
DIT_VIDE = ("            self._dit_taille(cle, \"\")\n            return True")
HINT_PACK = ("            self._taille_hint.pack(fill=tk.X, padx=8, pady=(0, 3))")
CHAMP = ("                self._taille_champs[key] = self._entry_field(lbl, v, R())")
CLEAR = ("        self._taille_champs = {}\n        self._taille_hint = None\n")
NEGATIF = ("        if n < 0:\n            return None\n")
MIN_PLAFOND = "        return min(n, plafond)"
PLAFOND_FICHIER = ("        plafond = max(UiViewerPlugin.TAILLE_MAX_TABLE, "
                   "max(0, int(deja_la or 0)))")
DEJA_LA = ("        return max(UiViewerPlugin._taille_brute(props.get(cle)),\n"
           "                   UiViewerPlugin._taille_brute("
           "(props.get(\"_src\") or {}).get(cle)))")
WANT_NEG = "        if want < 0:\n            return\n"
WANT_CAST = ("        try:\n            want = int(want)\n"
             "        except (TypeError, ValueError):\n"
             "            return                 # un compte qui n'est pas un "
             "nombre ne se dessine pas\n")
WANT_NONE = "        if want is None:\n            return\n"
SYNC_ROWS = ("        nrows = self._taille_admissible(props.get(\"rows\", 0), "
             "deja_lignes)")
SYNC_COL = (
    "        if ncols is not None and ncols != int(src.get(\"columns\") or 0):\n"
    "            self._set_number_prop(el, \"columnCount\", ncols)\n"
    "            self._adjust_count(el, \"column\", ncols)\n")
FRESH = ("                nrows = self._taille_admissible(props.get(\"rows\", 0), "
         "0) or 0")
APERCU = "        dessine_lignes = min(lignes, self.APERCU_MAX_LIGNES)"
MESSAGE_PLAFOND = (
    "                     \"La limite de l'editeur est %d %s.\" %\n"
    "                     (etique[1], voulu, voulu, admissible, etique[0]))")
MESSAGE_NEGATIF = (
    "            motif = (\"Un tableau ne peut pas avoir un nombre negatif de %s : 0 \"\n"
    "                     \"est le plus petit compte que Qt sache construire.\"\n"
    "                     % etique[0])")

# (nom, [(texte a remplacer, remplacement), ...]) — l'ordre des paires importe
LISTE = [
    # la porte n'existe plus : le champ ecrit ce que l'eleve tape
    ("porte_supprimee", [(PORTE, "")]),
    # la porte existe mais arrive APRES la conversion : un texte ne l'atteint
    # jamais, il s'evanouit dans le ValueError du cast (la faute d'avant)
    ("porte_apres_cast", [(PORTE, ""),
                          (APRES_CAST,
                           APRES_CAST +
                           "            if key in (\"rows\", \"columns\") and "
                           "not self._accept_taille(key, value, props):\n"
                           "                return\n")]),
    # la porte est verte : tout passe
    ("porte_toujours_verte", [(OUI_VERT,
                               "        self._dit_taille(cle, \"\")\n"
                               "        return True\n")]),
    # elle refuse, mais sans rien dire : la lecon de l'item 6 est perdue
    ("refus_silencieux", [(DIT_MOTIF, "        return False")]),
    # la couleur seule, sans explication
    ("couleur_seule", [(TEINTE,
                        "                entry.config(bg=\"#5a1a1a\" if motif "
                        "else \"#3c3c3c\") if False else None")]),
    # un nombre refuse reste rouge et explique, meme quand l'eleve corrige
    ("effacement_oublie", [(DIT_VIDE, "            return True")]),
    # l'explication n'est jamais montre a l'eleve
    ("explication_non_emballee", [(HINT_PACK,
                                   "            self._taille_hint.pack_forget()\n"
                                   "            self._taille_hint = None")]),
    # le champ n'est pas note : la coloration frappe dans le vide
    ("champ_non_renseigne", [(CHAMP,
                             "                self._entry_field(lbl, v, R())")]),
    # le panneau detruit garde ses champs fantomes (item 7, encore)
    ("clear_props_oublie", [(CLEAR, "")]),
    # le defaut original, bord gauche : -1 redevient une taille
    ("negatif_accepte", [(NEGATIF, "")]),
    # bord droit : plus aucun plafond
    ("plafond_ignore", [(MIN_PLAFOND, "        return n")]),
    # le plafond ne regarde plus ce que le fichier porte deja
    ("plafond_sans_fichier", [(PLAFOND_FICHIER,
                               "        plafond = UiViewerPlugin.TAILLE_MAX_TABLE")]),
    # le plafond suit la derniere saisie : reduire resserre la porte pour toujours
    ("deja_sans_source", [(DEJA_LA,
                           "        return UiViewerPlugin._taille_brute("
                           "props.get(cle))")]),
    # la tranche have[-1:] remange un en-tete de ligne titre
    ("ajust_sans_negatif", [(WANT_NEG, "")]),
    # un texte atteint la tranche
    ("ajust_sans_conversion", [(WANT_CAST, "")]),
    # idem pour None
    ("ajust_sans_none", [(WANT_NONE, "")]),
    # l'ecriture oublie ce que le fichier porte deja : un grand tableau est
    # rogne au plafond de l'editeur, et ses en-tetes partent avec lui. Vise a
    # dessein plus etroit que « plus aucun plafond » (plafond_ignore) : ecrit
    # 999 999 lignes, ce mutant-la fait pendre la suite sous le poids du
    # fichier qu'il produit, et une pendaison n'est pas une note.
    ("sync_sans_borne", [(SYNC_ROWS,
                          "        nrows = self._taille_admissible("
                          "props.get(\"rows\", 0), 0)")]),
    # un cote invalide arrete l'autre : les colonnes d'un eleve ne sortent plus
    ("sync_un_seul_cote", [(SYNC_COL,
                            "        if nrows is None or ncols is None:\n"
                            "            return\n"
                            "        if ncols != int(src.get(\"columns\") or 0):\n"
                            "            self._set_number_prop(el, \"columnCount\", ncols)\n"
                            "            self._adjust_count(el, \"column\", ncols)\n")]),
    # le document neuf a sa propre ecriture, et elle n'est pas bornee
    ("fresh_sans_borne", [(FRESH, "                nrows = props.get(\"rows\", 0)")]),
    # l'apercu dessine une case par cellule : le fichier est borne, plus l'ouverture
    ("apercu_sans_cap", [(APERCU, "        dessine_lignes = lignes")]),
    # le refus ne cite plus le plafond : l'eleve ne sait pas ou s'arreter
    ("message_sans_plafond", [(MESSAGE_PLAFOND,
                               "                     \"C'est trop grand.\" %\n"
                               "                     (etique[1], voulu, voulu))")]),
    # le negatif est refuse sans que le motif soit le bon
    ("negatif_sans_motif", [(MESSAGE_NEGATIF,
                             "            motif = (\"Ce nombre ne convient pas.\" "
                             "% etique[0])")]),
]

BILAN = re.compile(r"(\d+) checks?,\s*(\d+) echecs", re.I)
LIGNE_ECHEC = re.compile(r"^\s*FAIL[\s:]")
WATCHDOG = re.compile(r"ne s'est pas terminee au bout de", re.I)


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
        print(texte, flush=True)
    except UnicodeEncodeError:
        print(texte.encode(code, "replace").decode(code, "replace"), flush=True)


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
    debut = time.time()
    try:
        p = subprocess.run([os.path.join(BUNDLE, "python.exe"), "-u", "-B",
                            RUNNER, cible, SUITE],
                           cwd=os.path.dirname(SUITE), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=DELAI)
    except subprocess.TimeoutExpired:
        return nom, "GEL", "aucun bilan apres %ds" % DELAI
    sortie = (p.stdout or "") + (p.stderr or "")
    duree = time.time() - debut
    m = BILAN.search(sortie)
    echouees = [l.strip() for l in sortie.splitlines() if LIGNE_ECHEC.match(l)]
    if WATCHDOG.search(sortie):
        return nom, "TUE", "watchdog | %.0f s | %s" % (duree, echouees[0][:70])
    if not m:
        return nom, "SUITE CRASH", sortie.strip().splitlines()[-3:]
    if echouees:
        return nom, "TUE", "%s/%s echecs | %.0f s | %s" % (
            m.group(2), m.group(1), duree,
            " ; ".join(e[:80] for e in echouees[:2]))
    return nom, "SURVIVANT", "%s controles, 0 echec, %.0f s" % (m.group(1), duree)


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
        affiche("incidents (un crash de la suite n'est pas une note) : %s"
                % (incidents,))
    return 0 if not survivants and not incidents else 1


if __name__ == "__main__":
    sys.exit(main())
