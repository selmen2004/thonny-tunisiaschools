r"""Lance toutes les suites du dossier, dans l'ordre, sans rien ecrire sur disque.

    C:\...\Thonny\python.exe  tests\run_all.py

Le bundle de Thonny est l'interpreteur a employer : c'est lui qui connait a la
fois PyQt5 et Thonny. Lancer ce fichier avec un autre Python se voit tout de
suite, les suites ne passent plus.

Chaque test_*.py part dans son propre processus : ils installent tous des faux
workbenches differents, et Tk ne supporte pas deux instances en vie. Les
smoke_*.py ne sont pas des suites : ils montrent ce que Qt rend vraiment et
restent a lancer a la main, ainsi que mutants_*.py, qui verifie qu'une suite
verte ne suffit pas : il mutile le greffon et regarde si la suite le voit. mutants_*.py non plus : ils mutilent une copie du
paquet pour verifier que les suites regardent bien, et se lancent seuls.

Une ligne par suite, puis un total. Le code de sortie n'est 0 que si tout est
vert, donc ce script sert aussi de verification rapide avant un push.
"""
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 900

# Les suites ne comptent pas toutes de la meme facon ; chaque motif rend
# (controles, echecs) ou None quand le bilan ne donne qu'un des deux.
BILANS = [
    (re.compile(r"(\d+)/(\d+) checks passed", re.I),
     lambda a, b: (int(b), int(b) - int(a))),
    (re.compile(r"(\d+) checks?,\s*(\d+) echecs", re.I),
     lambda a, b: (int(a), int(b))),
    (re.compile(r"(\d+) controles?,\s*(\d+) echecs", re.I),
     lambda a, b: (int(a), int(b))),
    (re.compile(r"RESULTAT\s*:\s*(\d+) echecs", re.I),
     lambda a: (None, int(a))),
]
LIGNE_ECHEC = re.compile(r"^\s*FAIL[\s:]", re.I)


def suites():
    return sorted(f for f in os.listdir(HERE)
                  if f.startswith("test_") and f.endswith(".py"))


def bilan(sortie):
    """(controles, echecs) lu dans la sortie, echecs recalcules si besoin."""
    lignes = sortie.splitlines()
    for motif, lecture in BILANS:
        for ligne in reversed(lignes):
            m = motif.search(ligne)
            if m:
                return lecture(*m.groups())
    return None, len([l for l in lignes if LIGNE_ECHEC.match(l)])


def une(name):
    t0 = time.time()
    # L'enfant ecrit dans un tube : sans cela il choisit la page de codes de
    # Windows (cp1252) et une chaine du produit contenant un caractere hors
    # table — le « ≈ 1 Mo » de la question d'installation de Designer, par
    # exemple — fait exploser son `print` et tue la suite entiere sans bilan.
    # Les six `mutants_*.py` passent deja utf-8 a leurs enfants pour la meme
    # raison ; la batterie reste la seule a demander QT_QPA_PLATFORM de ne pas
    # bouger (test_designer_live surveille l'environnement de Thonny).
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, "-B", os.path.join(HERE, name)],
                           cwd=HERE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=TIMEOUT,
                           env=env)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT apres %ds" % TIMEOUT, ""
    sortie = (p.stdout or "") + (p.stderr or "")
    n, echecs = bilan(sortie)
    ok = p.returncode == 0 and not echecs
    # certaines suites annoncent « RESULTAT : 0 echecs » sans compter leurs
    # controles : mieux vaut un blanc honnete qu'un point d'interrogation.
    resume = ("%s controles, " % n if n is not None else "") + "%s echecs" % echecs
    return ok, resume + ("  %.0fs" % (time.time() - t0) if time.time() - t0 >= 1 else ""), sortie


def affiche(texte):
    """Imprime sans mourir.

    La console de Windows est en cp1252 alors que la sortie d'une suite cassee
    est pleine d'accents francais : un caractere que la console ne connait pas
    ne doit pas cacher le rapport qu'on est venu lire.
    """
    code = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        print(texte)
    except UnicodeEncodeError:
        print(texte.encode(code, "replace").decode(code, "replace"))


def main():
    vertes, cassees, controles = 0, [], 0
    for name in suites():
        ok, resume, sortie = une(name)
        vertes += ok
        if not ok:
            cassees.append((name, sortie))
        m = re.search(r"(\d+) controles", resume)
        controles += int(m.group(1)) if m else 0
        affiche("%-26s %s %s" % (name, "OK   " if ok else "FAIL", resume))
    affiche("\n%d/%d suites vertes, %d controles au total"
            % (vertes, len(suites()), controles))
    for name, sortie in cassees:
        affiche("\n" + "=" * 70 + "\n%s\n%s" % (name, sortie[-4000:]))
    return 0 if not cassees else 1


if __name__ == "__main__":
    sys.exit(main())
