r"""Item 4 : tr() autour de chaînes déjà françaises.

`thonny.languages.tr` n'est pas un accessoire décoratif : c'est
`gettext.gettext` branché sur le catalogue de THONNY (`thonny/locale/<code>/
LC_MESSAGES/thonny.mo`, voir languages.py:84-93). Un greffon qui appelle tr()
ne peut donc jamais faire traduire SES propres chaînes — elles ne sont pas dans
ce catalogue — et risque au contraire de voir son texte réécrit si l'une d'elles
coïncide avec un msgid anglais de Thonny. Avec une source déjà française, tr()
est à la fois mort et dangereux.

Ce test compare les fichiers VIVANTS aux copies prises avant la suppression
(`tests\tr_baseline_*.py`, sha1 `68b3ef8e` et `7ff83a1f`) et prouve trois
choses : il ne reste aucun appel à tr() ni aucun import de thonny.languages ;
le texte affiché à l'élève est exactement le même, à la même place ; et les six
seules étiquettes concernées ne sont des msgid de personne — le catalogue
français officiel de Thonny les ignore toutes les six.
"""
import ast
import collections
import importlib
import io
import os
import sys

import chemins

BUNDLE = chemins.BUNDLE
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = chemins.PAQUET             # le paquet sur lequel on travaille
TMP = HERE                        # les deux instantanes d'avant l'item 4 voyagent ici
PAIRS = [("UIViewer.py", "tr_baseline_UIViewer.py"),
         ("__init__.py", "tr_baseline___init__.py")]

FAILS = []
N = [0]


def check(label, cond, detail=""):
    N[0] += 1
    if not cond:
        FAILS.append("%s %s" % (label, detail))
    print("%s %s%s" % ("OK  " if cond else "FAIL", label,
                       (" -> " + str(detail)) if detail else ""))


def lire(chemin):
    return io.open(chemin, encoding="utf-8").read()


def arbre(chemin):
    return ast.parse(lire(chemin))


def nom(noeeud):
    """Le nom d'une fonction appelée : tr(...) ou thonny.languages.tr(...)."""
    if isinstance(noeeud, ast.Name):
        return noeeud.id
    if isinstance(noeeud, ast.Attribute):
        return noeeud.attr
    return ""


def appels_tr(tree):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and nom(n.func) == "tr"]


def imports_langue(tree):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module == "thonny.languages"]


def litteral(noeeud):
    if isinstance(noeeud, ast.Constant) and isinstance(noeeud.value, str):
        return noeeud.value
    return None


def etiquette(noeeud):
    """Le texte visible d'un argument : "X" ou tr("X") rendent tous deux "X"."""
    if isinstance(noeeud, ast.Call) and nom(noeeud.func) == "tr":
        if noeeud.args:
            return litteral(noeeud.args[0])
        return None
    return litteral(noeeud)


def textes_affiches(tree):
    """Les libellés réellement montrés par Thonny : titre de vue, commandes,
    filtres des boîtes de fichier. Comparés AVANT / APRES, ils doivent être
    mot pour mot les mêmes."""
    vus = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = nom(n.func)
        if f in ("add_view", "add_command"):
            for i, a in enumerate(n.args):
                t = etiquette(a)
                if t:
                    vus.append((f, i, t))
            for kw in n.keywords:
                t = etiquette(kw.value)
                if t and kw.arg in ("text", "caption", "description"):
                    vus.append((f, kw.arg, t))
        if f in ("askopenfilename", "asksaveasfilename"):
            for kw in n.keywords:
                if kw.arg != "filetypes":
                    continue
                for paire in getattr(kw.value, "elts", []):
                    vus.append(("filetypes", tuple(etiquette(e) or "?"
                                                   for e in getattr(paire, "elts", []))))
    return sorted(vus, key=lambda x: str(x))


def chaines(tree):
    """Toutes les constantes de texte du fichier, avec répétitions."""
    return collections.Counter(
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str))


def docstrings(tree):
    """La documentation du code : elle ne parait jamais a l'ecran, elle n'a
    donc rien a comparer au texte affiche.

    La constante BRUTE, surtout : `ast.get_docstring` retracte et rogne, alors
    que `chaines()` compte les valeurs telles quelles sont ecrites. Soustraire
    l'une de l'autre ne retirait rien, et chaque docstring touchee se
    retrouvait declaree comme libelle perdu puis invente.
    """
    sorts = collections.Counter()
    for n in ast.walk(tree):
        if not isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            continue
        corps = getattr(n, "body", None)
        if not corps:
            continue
        premier = corps[0]
        if (isinstance(premier, ast.Expr)
                and isinstance(premier.value, ast.Constant)
                and isinstance(premier.value.value, str)):
            sorts[premier.value.value] += 1
    return sorts


def chaines_hors_documentation(tree):
    return chaines(tree) - docstrings(tree)


def chaines_lisibles(tree):
    """Les constantes que l'eleve peut lire a l'ecran : c'est la seule famille
    de chaines qu'un controle de traduction doit connaitre. Les noms
    d'attribut XML, les incantations Tk et les cles de dictionnaire changent
    de compte des que l'on restructure le code, sans qu'une seule etiquette
    bouge — ce n'est pas a ce controle de les poursuivre."""
    ds = docstrings(tree)
    return collections.Counter(
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and texte_lisible(n.value) and n.value not in ds)


# Ce que l'item 5 (zone defilable) a ete autorise a retirer du fichier : les
# deux incantations Tk du handler supprime, canvas.bind("<Configure>", ...) et
# canvas.bbox("all"). Elles ne peuvent pas paraitre a l'ecran. Un item qui
# toucherait un libelle doit etre declare ci-dessous, consciemment.
# "styleSheet" vient de l'item « un texte efface doit etre ecrit » : les quatre
# mentions de la clef dans _write_changed (test, comparaison, ecriture, valeur)
# tenaient dans un bloc separre de la boucle text/placeholder/title. La boucle
# les a reunies en une seule mention : la clef est toujours employee, c'est sa
# repetition qui a disparu. test_effacement.py en garde le controle.
# Les quatre derniers viennent de l'item 11 (la couleur du texte ne doit pas
# effacer le fond) : « color: », « background: », « background-color: » et un
# «: » etaient des lamelles de comparaison de ligne — `part.startswith("color:")`,
# `css_prop + ":" not in l`. L'item les remplace par le nom normalise de la
# declaration (`_nom_de_declaration`), compare entier : les litteraux a
# deux-points ne servent plus a rien, et aucune etiquette lisible ne bouge —
# les deux controles du-dessus (« memes libelles avant / apres », « aucun libelle
# lisible perdu ») sont passes, et test_couleurs.py surveille le geste.
ETEINTES_DECLAREES = {"<Configure>", "all", "geometry", "styleSheet",
                      "color:", "background:", "background-color:", ":"}

# Les libelles neufs de l'item 7a (garde de la mise en page), relus un par un :
# c'est du texte que l'eleve voit, il est donc declare mot pour mot.
LIBELLES_NEUFS = {
    "UIViewer.py": {
        " ",                       # rembourrage de l'etiquette du bouton
        "Libérer la position",     # le bouton du panneau
        "Remettre dans la mise en page",
        "%s est placé par la mise en page — « Libérer la position » "
        "dans le panneau de droite pour le déplacer",     # refus, barre d'etat
        "%s est libéré de la mise en page : vous pouvez le déplacer",
        "%s est remis dans la mise en page : c'est elle qui le place",
        "%s : le conteneur n'a pas de mise en page, rien où le remettre",
        "  Ces valeurs sont réglées par la mise en page et "
        "ne sont qu'estimées par le concepteur.",
        "  Position absolue, écrite dans le fichier.",
        "Faire décider le widget de sa position, ou laisser "
        "la mise en page le faire",                      # infobulle
        "Rendre la position à la mise en page du conteneur",
        # et les deux de la tranche 7b (le glisser reclasse la mise en page)
        "  %s -> position %d sur %d de la mise en page",
        "%s est reclassé en position %d sur %d",
        # et l'avis de l'item 1 : le menage des connexions orphelines, compte a
        # la barre d'etat au moment de l'enregistrement
        "Connexions retirées du fichier : %d — elles visaient "
        "un widget supprimé",
        # et l'avis de l'item 3 : un <ui> sans forme ne se refuse plus en silence
        "Ce fichier n'est pas une fenetre :\nil ne contient aucun widget "
        "a afficher.",
        # et la question de l'item 13 : un fichier qui s'ouvre ne doit pas
        # effacer en silence un travail que l'eleve n'a pas enregistre
        "Le fichier « %s » va remplacer la fenetre affichee.\n\n"
        "Votre travail en cours n'est pas enregistre : enregistrez-le "
        "avant si vous y tenez.\n\n"
        "Remplacer quand meme ?",
        # et le refus de l'item 4 : le nom atteint desormais le fichier, il faut
        # donc refuser les noms que le fichier reserve deja hors du modele
        # (la fenetre, chaque <layout>, chaque <action>)
        "Ce nom appartient a la fenetre, a une mise en page ou a "
        "une action du fichier : deux objets du meme nom ne peuvent "
        "pas coexister.",
        # et son echo a l'enregistrement : _save a la derniere ligne avant le
        # disque, elle doit connaitre les memes noms reserves que le panneau
        "%s : la fenetre, une mise en page ou une action porte deja ce nom",
        # et l'item 6 : un nom n'est pas seulement un identifiant, il doit
        # s'ecrire dans le programme. Les deux motifs de refus (mot reserve de
        # Python, nom en __double__) ont chacun leur phrase au panneau ET leur
        # echo devant le disque, plus la consigne qui remplace les lignes de
        # code que le panneau ne peut plus proposer.
        "%s est un mot reserve de Python : windows.%s ne s'ecrit pas "
        "dans un programme.",
        "%s est un nom reserve par Python (les noms en __double__) : "
        "la fenetre entiere refuserait de se construire.",
        "%s : mot reserve de Python, windows.%s n'est pas du code",
        "%s : nom en __double__ reserve par Python, la fenetre ne se "
        "construirait pas",
        "  Corrigez le nom ci-dessus pour inserer une ligne",
        # et l'item 8 : un compte de lignes ou de colonnes refuse doit dire POURQUOI.
        # Les quatre portes du champ (texte, vide, negatif, trop grand) ont chacune sa
        # phrase, ecrite sous le champ colore plutot que dans une boite.
        "Le compte des %s s'ecrit en chiffres : « %s » ne designe pas un nombre.",
        "Le champ est vide : « 0 » est un compte legal, mais un tableau a un "
        "nombre de %s ecrit en chiffres.",
        "Un tableau ne peut pas avoir un nombre negatif de %s : 0 est le plus "
        "petit compte que Qt sache construire.",
        "Un fichier .ui ecrit une ligne XML par %s reclamee : %d en ecrirait %d, "
        "et le fichier mettrait des minutes a s'ouvrir. La limite de l'editeur "
        "est %d %s.",
        # et son corollaire dans l'apercu : un grand tableau se dessine borne, la
        # ligne et la colonne de trop sont ANNONCEES par un point de suspension
        # plutot que dessinees (deux cases : une en tete de colonne, une en rangee).
        "…",
    },
    "__init__.py": {
        # Le module de Designer de la distribution (pyqt5-qt5-designer) et son
        # installation a un clic : I'enseignant qui n'a rien sur son poste voit
        # desormais une proposition, un echec explique, et le nom du module a
        # taper s'il prefere la boite « Gérer les paquets... ». Chaque phrase est
        # declaree ici mot pour mot, y compris les fragments qui ne sont pas du
        # francais : « Qt Designer » est le titre des trois nouvelles boites, et
        # les suites que pip ecrit quand il échoue servent a deviner pourquoi.
        "Qt Designer",
        "Qt Designer n'est pas installé sur ce poste.\n\n"
        "L'installer maintenant ? Le module %s ne pèse qu'≈ 1 Mo : il dépose "
        "designer.exe à côté des DLLs Qt déjà présentes, sans re-télécharger "
        "Qt.\n\nUne connexion Internet est nécessaire et Thonny patiente le "
        "temps de l'échange.",
        "PyPI est injoignable : ce poste semble hors ligne.\n\nEn salle, "
        "l'installation se fait par la distribution ThonnyTN (le module y est "
        "déjà), sinon indiquez un designer.exe existant avec la commande "
        "« Configurer Designer » du menu PyQt5.",
        "Thonny n'a pas le droit d'écrire dans son propre dossier "
        "(installation sous « Program Files » ?).\n\nRefaites l'installation en "
        "tant qu'administrateur, ou indiquez un designer.exe existant avec "
        "« Configurer Designer ».",
        "L'installation n'a pas abouti.",
        "pip a terminé mais designer.exe reste introuvable.\n\nIndiquez son "
        "emplacement avec la commande « Configurer Designer » du menu PyQt5.",
        "\n\n--- pip ---\n",
        "(aucune sortie)",
        "%s : %s",
        "no matching distribution",
        "could not find a version",
        "max retries",
        "timed out",
        "access is denied",
        "winerror 5",
    },
}

# L'item 2 a eu le droit de RETRANSFORMER une maquette : le squelette que
# « Ajouter Annexe » colle dans l'editeur est du texte que l'eleve lit. Les
# constantes implicites étant repliees par Python, c'est le bloc tout entier qui
# change de valeur. Un seul remplacement est autorise, declare mot pour mot
# ci-dessous, et sa brievete est prouvee ligne a ligne plus bas : perdre ou
# inventer n'importe quel autre texte lisible reste interdit.
#
# Aujourd'hui, la table est VIDE, et c'est le resultat le plus strict qu'on
# puisse obtenir : la decision du 2026-10-02 a rendu le squelette mot pour mot a
# l'etat que la copie de reference de l'item 4 avait vu. L'item 2 y avait ajoute
# un gestionnaire complet (def Nom_Module, son commentaire, pass) parce que la
# ligne de branchement employait Nom_Module sans le definir ; la decision a retire
# ce bloc et laisse la ligne de branchement. Ajout et retrait se neutralisent
# donc entre les deux instants compares : le recensement ne doit rien voir passer,
# et section 3b prouve que c'est bien le meme texte, et que le bloc retire n'y
# revienne jamais.
SQUELETTE_DE_REFERENCE = (
    "from PyQt5.uic import loadUi\n"
    "from PyQt5.QtWidgets import QApplication\n"
    "\n\n\n"
    "app = QApplication([])\n"
    'windows = loadUi ("Nom_Interface.ui")\n'
    "windows.show()\n"
    "windows.Nom_Bouton.clicked.connect (Nom_Module)\n"
    "app.exec_()\n"
)
MAQUETTES_REPLACEES = {}
# Les lignes que la decision du 2026-10-02 a retirees, et qui ne doivent pas
# revenir dans le texte que l'eleve lit.
BLOC_DU_GESTIONNAIRE = ["def Nom_Module():", "    pass"]

# Deuxieme registre de remplacements declares, pour les phrases de boite de
# dialogue : la maquette du squelette a sa brievete verifiee ligne a ligne en 3b,
# une phrase de dialogue n'a rien de comparable. Le principe est le meme : une
# phrase lisible perdue n'est pardonnee que si sa remplacante est ecrite ici,
# mot pour mot, et en un seul exemplaire.
#
# L'avertissement du defaut de Designer promettait « pip install pyqt5-designer » :
# un module qui retelecharge un Qt complet (≈100 Mo) a cote de celui de l'eleve.
# La distribution a maintenant son propre module, pyqt5-qt5-designer, qui ne
# depose que designer.exe et sa DLL de composants dans le Qt deja present. La
# phrase change donc de nom et de mode d'emploi ; le reste du message, lui, est
# toujours la.
PHRASE_DU_DEFAUT_ANCIENNE = (
    "Qt Designer n'est pas installé sur ce poste.\n\n"
    "Il est fourni par le module pyqt5-designer :\n"
    "    pip install pyqt5-designer\n\n"
    "Sinon, indiquez son emplacement avec la commande « Configurer Designer » "
    "du menu PyQt5."
)
PHRASE_DU_DEFAUT_NEUVE = (
    "Qt Designer n'est pas installé sur ce poste.\n\n"
    "Il est fourni par le module %s, qui ne pèse qu'≈ 1 Mo parce qu'il range "
    "designer.exe dans le dossier des DLLs Qt déjà installées :\n"
    "    pip install %s\n\n"
    "Sans ligne de commande : menu Outils → « Gérer les paquets... », taper "
    "%s, puis Installer.\n\n"
    "Sinon, indiquez son emplacement avec la commande « Configurer Designer » "
    "du menu PyQt5."
)
PHRASES_REMPLACEES = {"__init__.py": [(PHRASE_DU_DEFAUT_ANCIENNE,
                                       PHRASE_DU_DEFAUT_NEUVE)]}


def texte_lisible(s):
    """Une constante qui peut se lire dans l'interface : un espace ou un accent."""
    return " " in s or not s.isascii()


print("=== 1. il ne reste aucun tr() ni aucun import de thonny.languages ===")
for vif, base in PAIRS:
    chemin = os.path.join(LIVE, vif)
    tree = arbre(chemin)
    check("%s : zero appel a tr()" % vif, appels_tr(tree) == [],
          [(a.lineno, a.col_offset) for a in appels_tr(tree)])
    check("%s : zero import de thonny.languages" % vif,
          imports_langue(tree) == [],
          [i.lineno for i in imports_langue(tree)])
    check("%s : le nom « tr » n'est plus employe nulle part" % vif,
          not [n for n in ast.walk(tree)
               if isinstance(n, ast.Name) and n.id == "tr"],
          "le nom subsisterait sans import -> NameError")
    check("%s : le module se compile" % vif,
          compile(lire(chemin), chemin, "exec") is not None)

print("=== 2. ce que le plugin emballait, et ou ===")
bases = {vif: arbre(os.path.join(TMP, base)) for vif, base in PAIRS}
emballes = []
for vif in ("UIViewer.py", "__init__.py"):
    for a in appels_tr(bases[vif]):
        emballes.append((vif, a.lineno, litteral(a.args[0]) if a.args else None))
attendues = ["Tous les fichiers", "QT UI Viewer", "Ajouter Annexe",
             "Ajouter Annexe + interface", "Ouvrir dans Designer",
             "Configurer Designer"]
emballes.sort(key=lambda e: e[1])      # ast.walk parcourt en largeur, pas en ligne
check("six etiquettes seulement, toutes dans __init__.py",
      [e[2] for e in emballes] == attendues and
      all(e[0] == "__init__.py" for e in emballes), emballes)
check("UIViewer.py n'appelait jamais tr() : son import etait mort",
      appels_tr(bases["UIViewer.py"]) == [] and
      imports_langue(bases["UIViewer.py"]) != [],
      [(i.lineno, [a.name for a in i.names]) for i in
       imports_langue(bases["UIViewer.py"])])

print("=== 3. le texte affiche n'a pas bouge, a la meme place ===")
for vif, _base in PAIRS:
    avant = textes_affiches(bases[vif])
    apres = textes_affiches(arbre(os.path.join(LIVE, vif)))
    check("%s : memes libelles avant / apres" % vif, avant == apres,
          [(a, b) for a, b in zip(avant, apres) if a != b] or (len(avant), len(apres)))
    c_avant = chaines_lisibles(bases[vif])
    c_apres = chaines_lisibles(arbre(os.path.join(LIVE, vif)))
    perdues = c_avant - c_apres
    ajoutees = c_apres - c_avant
    # une maquette declaree retire un texte et le rend transforme : les deux se
    # neutralisent, paire par paire, et uniquement la.
    for ancien, nouveau in MAQUETTES_REPLACEES.get(vif, ()):
        n = min(perdues[ancien], ajoutees[nouveau])
        perdues[ancien] -= n
        ajoutees[nouveau] -= n
        check("%s : le remplacement declare a vraiment eu lieu" % vif, n == 1,
              "l'ancien texte a paru %d fois, le nouveau %d fois"
              % (perdues[ancien] + n, ajoutees[nouveau] + n))
    # idem pour les phrases de dialogue declarees a part (voir ci-dessus)
    for ancien, nouveau in PHRASES_REMPLACEES.get(vif, ()):
        n = min(perdues[ancien], ajoutees[nouveau])
        perdues[ancien] -= n
        ajoutees[nouveau] -= n
        check("%s : la phrase remplacee est bien la declaree" % vif, n == 1,
              "l'ancien texte a paru %d fois, le nouveau %d fois"
              % (perdues[ancien] + n, ajoutees[nouveau] + n))
    # Counter garde les cles a zero, et un compteur a une cle compte comme vrai.
    perdues, ajoutees = +perdues, +ajoutees
    permis = LIBELLES_NEUFS.get(vif, set())
    check("%s : aucun libelle lisible perdu, et les ajoutes sont declarees" % vif,
          not perdues and set(ajoutees) <= permis and permis <= set(ajoutees),
          (dict(perdues), dict(ajoutees - collections.Counter(permis)),
           sorted(permis - set(ajoutees))))
    # le reste (noms XML, valeurs Tk, cles de modele) n'est pas du texte
    # d'interface : on ne surveille qu'une chose, qu'il ne disparaisse pas en
    # silence.
    tech_avant = chaines_hors_documentation(bases[vif]) - c_avant
    tech_apres = chaines_hors_documentation(arbre(os.path.join(LIVE, vif))) - c_apres
    check("%s : aucune chaine technique effacee sans declaration" % vif,
          set(tech_avant - tech_apres) <= ETEINTES_DECLAREES,
          dict(tech_avant - tech_apres))
check("les six etiquettes sont toujours dans le fichier vivant",
      all(t in lire(os.path.join(LIVE, "__init__.py")) for t in attendues),
      [t for t in attendues
       if t not in lire(os.path.join(LIVE, "__init__.py"))])

print("=== 3b. le squelette rendu a son etat de reference, ligne a ligne ===")
vivant = chaines_lisibles(arbre(os.path.join(LIVE, "__init__.py")))
check("le fichier vivant colle mot pour mot le squelette de la copie de reference",
      vivant[SQUELETTE_DE_REFERENCE] == 1,
      dict((k, v) for k, v in vivant.items() if "Nom_" in k))
check("et la copie de reference porte bien ce meme texte",
      chaines_lisibles(bases["__init__.py"])[SQUELETTE_DE_REFERENCE] == 1,
      dict((k, v) for k, v in chaines_lisibles(bases["__init__.py"]).items()
           if "Nom_" in k))
lignes = [l for l in SQUELETTE_DE_REFERENCE.splitlines() if l.strip()]
check("le bloc du gestionnaire n'est revenu dans aucune de ces lignes",
      not any(l in BLOC_DU_GESTIONNAIRE for l in lignes)
      and "compléter" not in SQUELETTE_DE_REFERENCE, lignes)
check("la ligne de branchement, elle, est restee : c'est le geste a montrer",
      "windows.Nom_Bouton.clicked.connect (Nom_Module)" in lignes, lignes)
check("les trois blancs que l'eleve doit remplir sont toujours la",
      all(b in SQUELETTE_DE_REFERENCE
          for b in ("Nom_Interface.ui", "Nom_Bouton", "Nom_Module")),
      [l for l in lignes if "Nom_" in l])
check("et le squelette n'emploie aucun autre blanc Nom_ que ces trois-la",
      SQUELETTE_DE_REFERENCE.count("Nom_") == 3
      and sorted(b for b in ("Nom_Interface.ui", "Nom_Bouton", "Nom_Module")
                 if b in SQUELETTE_DE_REFERENCE)
      == sorted(["Nom_Interface.ui", "Nom_Bouton", "Nom_Module"]),
      [l for l in lignes if "Nom_" in l])

print("=== 4. ce que tr() faisait vraiment, avec le catalogue officiel ===")
from thonny import languages

catalogue = getattr(languages._translation, "_catalog", {})
languages.set_language("fr_FR")
catalogue = getattr(languages._translation, "_catalog", {})
msgs = {k for k in catalogue if isinstance(k, str)}
check("le catalogue francais de Thonny est bien charge", len(msgs) > 200,
      "%d msgids" % len(msgs))
traduites = {m: languages.tr(m) for m in msgs
             if m.isascii() and languages.tr(m) not in ("", m)}
check("le catalogue traduit vraiment (sinon le test serait vide)",
      len(traduites) > 20, "%d entrees differentes" % len(traduites))
retouches = {t: languages.tr(t) for t in attendues if languages.tr(t) != t}
check("aucune des six chaines francaises n'etait un msgid : tr() ne "
      "changeait rien", retouches == {}, retouches)
check("tr() etait bien un coup de gettext par etiquette, pour rien",
      all(languages.tr(t) == t for t in attendues),
      {t: languages.tr(t) for t in attendues if languages.tr(t) != t})
mots_courants = ["Open", "Save", "New", "Close", "Quit", "Help", "Exit", "Run",
                 "Tools", "View", "Shell", "Clear", "Copy", "Paste", "Reload"]
collisions = {m: languages.tr(m) for m in mots_courants
              if m in msgs and languages.tr(m) != m}
check("le danger etait reel : un libelle anglais courant est deja un msgid de "
      "Thonny et se fait reecrire par la traduction",
      len(collisions) > 0, collisions)
if collisions:
    un, autre = sorted(collisions.items())[0]
    print("     exemple : tr(%r) rend %r une fois le francais active" % (un, autre))

print("=== 5. ce que Thonny va enregistrer comme menu ===")
mod = importlib.import_module("thonnycontrib.tunisiaschools")


class FauteWB:
    def __init__(self):
        self.vues = []
        self.commandes = []
        self.options = {}

    def add_view(self, cls, title, sequence=None):
        self.vues.append(title)

    def add_command(self, name, menu, text, handler=None, **kw):
        self.commandes.append((name, menu, text, kw.get("caption")))

    def set_local_cwd(self, path):
        self.options["cwd"] = path

    def set_option(self, name, value):
        self.options[name] = value

    def get_option(self, name, default=None):
        return self.options.get(name, default)


sandbox = os.path.join(TMP, "tr_menu_sandbox")
if not os.path.isdir(sandbox):
    os.makedirs(sandbox)
wb = FauteWB()
ancien_get = mod.get_workbench
ancien_roots = mod.working_dir_roots
mod.get_workbench = lambda: wb
mod.working_dir_roots = lambda: [sandbox]
try:
    mod.load_plugin()
    erreur = None
except Exception as e:
    erreur = e
finally:
    mod.get_workbench = ancien_get
    mod.working_dir_roots = ancien_roots
check("load_plugin() passe sans tr() dans l'import", erreur is None, repr(erreur))
check("la vue et les quatre commandes portent le meme libelle qu'avant",
      wb.vues == ["QT UI Viewer"] and
      [c[2] for c in wb.commandes] == ["Ajouter Annexe",
                                       "Ajouter Annexe + interface",
                                       "Ouvrir dans Designer",
                                       "Configurer Designer"],
      (wb.vues, [c[2] for c in wb.commandes]))
check("les commandes ont garde leur groupe, leur sequence et leur icone",
      all(c[3] == "PyQt" for c in wb.commandes) and
      len(wb.commandes) == 4,
      [(c[0], c[3]) for c in wb.commandes])
check("__init__.py n'importe plus thonny.languages du tout",
      "languages" not in lire(os.path.join(LIVE, "__init__.py")),
      [l.strip() for l in lire(os.path.join(LIVE, "__init__.py")).splitlines()
       if "languages" in l])

print("\n%d checks, %d echecs" % (N[0], len(FAILS)))
for f in FAILS:
    print("ECHEC " + f)
sys.exit(1 if FAILS else 0)
