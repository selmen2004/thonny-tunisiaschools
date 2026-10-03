"""Les chemins dont les suites ont besoin, calcules au lieu d'etre recopies.

Jusqu'ici chaque suite recopiait deux chemins absolus — le bundle Thonny et le
dossier du paquet. Deux defauts : la suite ne tournait que sur une machine, et
elle devenait fausse des que le paquet bougeait. Or il a bouge le 2026-10-03 :
les sources du paquet sont descendues sous ``thonnycontrib/tunisiaschools``,
comme dans la distribution publiee (``setup.py`` declare
``packages=["thonnycontrib.tunisiaschools"]``), pour que ``python -m build``
fabrique un vrai wheel. Les valeurs viennent donc maintenant de ``__file__`` :

* le paquet : fils de ce depot, quel que soit l'endroit ou le depot est clone ;
* le bundle : ``THONNY_BUNDLE`` si quelqu'un l'a pose, sinon l'interprete qui
  execute la suite (les suites se lancent avec le ``python.exe`` du bundle),
  sinon l'installation par defaut ``%LOCALAPPDATA%\\Programs\\Thonny`` — donc
  aucun nom d'utilisateur n'est ecrit nulle part, et la suite tourne telle
  quelle sur le poste d'un collegue.

Rien n'est pose dans l'environnement ici : ``test_designer_live`` surveille
l'environnement de Thonny et refuse qu'une suite le salisse (pas de
``QT_QPA_PLATFORM``, notamment). La copie mutee d'un gruteur de mutants
s'annonce toujours par ``TUNISIASCHOOLS_COPIE`` : ce sont les suites qui la
lisent, elles gardent donc leur propre ``os.environ.get(...)`` et ne demandent
ici que le chemin du paquet du depot.
"""
import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(TESTS)

# la forme publiee du paquet : <depot>/thonnycontrib/tunisiaschools
PAQUET = os.path.join(DEPOT, "thonnycontrib", "tunisiaschools")


def est_bundle(dossier):
    """Vrai seulement si le dossier contient un Thonny avec PyQt5 a cote.

    Les deux marqueurs sont indispensables : un vieux Python seul passerait
    pour un bundle, et les sondes des suites mourraient alors d'un ImportError
    de ``PyQt5`` au lieu d'un vrai verdict.
    """
    if not dossier:
        return False
    site = os.path.join(dossier, "Lib", "site-packages")
    return (os.path.isfile(os.path.join(site, "thonny", "__init__.py"))
            and os.path.isdir(os.path.join(site, "PyQt5")))


def _trouver_bundle():
    pose = os.environ.get("THONNY_BUNDLE") or ""
    interprete = os.path.dirname(sys.executable)
    par_defaut = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                              "Programs", "Thonny")
    for candidate in (pose, interprete, par_defaut):
        if est_bundle(candidate):
            return candidate
    raise SystemExit(
        "Pas de bundle Thonny trouve.\n"
        "Lancez les suites avec le python.exe du bundle, ou posez\n"
        "THONNY_BUNDLE=C:\\chemin\\vers\\Thonny.\n"
        "Recherches : " + "; ".join(
            c if c else "(vide)" for c in (pose, interprete, par_defaut)))


BUNDLE = _trouver_bundle()
SITE = os.path.join(BUNDLE, "Lib", "site-packages")
PYTHON = os.path.join(BUNDLE, "python.exe")
