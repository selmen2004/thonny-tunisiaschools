r"""Vérification réelle (sans bouchon) : designer.exe démarre bien, dans l'environnement prêté.

Une cmd.exe copié et renommé designer.exe sert de faux Designer : il ne peut pas
ouvrir le .ui, mais il prouve que le chemin de lancement est valable — et qu'un
processus neuf hérite bien de l'environnement que le greffon prépare.

Le deuxième volet regarde le vrai Designer de la distribution, s'il est installé.
Il est lancé sous QT_QPA_PLATFORM=offscreen : une fenêtre s'ouvrirait sur le poste
de l'enseignant pendant que la batterie tourne. Sous offscreen, un Designer qui
fonctionne n'a AUCUNE fenêtre de premier rang ; une boîte d'erreur Qt en a une.
C'est ce qui distingue « vivant » de « bloqué sur un dialogue », et ce que la
seule table des processus ne dirait pas.

Rien ici n'installe ni ne désinstalle quoi que ce soit : l'installateur est
bouchonné dès l'import, sinon la suite lancerait un vrai pip et ouvrirait le vrai
Designer de l'élève.

Le quatrième volet regarde la cible du lancement. Cette suite est la seule à
démarrer un vrai processus : c'est donc elle qui peut affirmer que le fichier
que le concepteur a à l'écran — `vue.ui_file`, depuis l'item 9 — est bien celui
que `designer.exe` reçoit, et que le module n'en garde plus de copie.
"""
import ctypes
import ctypes.wintypes as w
import glob
import importlib
import os
import shutil
import subprocess
import sys
import time
import types

mod = importlib.import_module("thonnycontrib.tunisiaschools")

HERE = os.path.dirname(os.path.abspath(__file__))
TEMP = os.path.join(HERE, "_sortie", "live")
shutil.rmtree(TEMP, ignore_errors=True)
os.makedirs(TEMP)
fake = os.path.join(TEMP, "designer.exe")
shutil.copy2(r"C:\Windows\System32\cmd.exe", fake)

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + label + (("  <- " + str(detail)) if detail else ""))


class FausseVue:
    """Le fichier que le concepteur a a l'ecran. Depuis l'item 9 c'est la vue
    qui le detient, et « Ouvrir dans Designer » le relit sur elle : cette suite
    est la seule a lancer un vrai processus, elle doit donc le poser ici — le
    vieux `mod.qt_ui_file` ne serait plus lu par personne."""

    def __init__(self, ui_file=""):
        self.ui_file = ui_file


class FakeWB:
    def __init__(self):
        self.opts = {}
        self.vue = FausseVue()

    get_option = lambda self, n, d=None: self.opts.get(n, d)
    set_option = lambda self, n, v: self.opts.__setitem__(n, v)

    def get_view(self, name, create=True):
        # la signature reelle de Thonny : `create=False` promet de ne rien creer
        if name != "UiViewerPlugin":
            raise AssertionError("vue inattendue : %s" % name)
        return self.vue


wb = FakeWB()
mod.get_workbench = lambda: wb
mod.messagebox = types.SimpleNamespace(
    showerror=lambda *a, **k: None, showinfo=lambda *a, **k: None,
    askyesno=lambda *a, **k: True,
)
# garde-fous : une suite ne telecharge pas, ne choisit pas de fichier, n'installe pas
mod.askopenfilename = lambda **kw: ""
mod._installer_designer = lambda: False
mod._proposer_installation_designer = lambda: False
ui = os.path.join(HERE, "designer_layout.ui")
wb.vue.ui_file = ui

# ── 1. le lancement, pour de vrai ─────────────────────────────────────────
os.chdir(TEMP)
proc = mod._run_designer(fake, ui)
try:
    code = proc.wait(timeout=30)
except subprocess.TimeoutExpired:
    proc.kill()
    code = None
check("vrai lancement: un processus a démarré", proc.pid > 0, proc.pid)
check("vrai lancement: le faux Designer s'est terminé", code is not None, code)

mod._set_option(mod.DESIGNER_OPTION, fake)
lances_reels = []
_vrai_popen = subprocess.Popen
mod.subprocess = types.SimpleNamespace(
    Popen=lambda args, **kw: (lances_reels.append((list(args), kw)) or _vrai_popen(args, **kw)),
    run=subprocess.run)
check("open_in_designer: True avec un vrai binaire", mod.open_in_designer() is True)
check("open_in_designer: le binaire mémorisé est utilisé",
      mod.find_designer() == os.path.abspath(fake), mod.find_designer())
check("open_in_designer: le .ui de l'eleve est transmis",
      lances_reels and lances_reels[0][0] == [os.path.abspath(fake), os.path.abspath(ui)],
      [a for a, _ in lances_reels[:1]])
env_prete = lances_reels[0][1].get("env") if lances_reels else {}
# QLibraryInfo rend des barres obliques, abspath les retourne : normaliser des deux cotes
tete_du_path = os.path.normpath((env_prete.get("PATH") or "").split(os.pathsep)[0])
check("open_in_designer: l'environnement prete le Qt de Thonny",
      os.path.isdir(tete_du_path)
      and tete_du_path == os.path.normpath(mod._qt_binaries_dir() or ""), tete_du_path)
check("open_in_designer: rien n'est ajoute a l'environnement de Thonny",
      "QT_QPA_PLATFORM" not in os.environ, os.environ.get("QT_QPA_PLATFORM"))
mod.subprocess = types.SimpleNamespace(Popen=_vrai_popen, run=subprocess.run)

# ── 2. le fichier transmis est bien un .ui PyQt5 ─────────────────────────
from PyQt5.QtWidgets import QApplication
from PyQt5.uic import loadUi
app = QApplication.instance() or QApplication([])
vue = loadUi(ui)
check("le fichier transmis est bien un .ui PyQt5", vue is not None and vue.objectName() != "",
      getattr(vue, "objectName", lambda: "?")())

# ── 3. le vrai Designer de la distribution ───────────────────────────────
# le choix memorise plus haut pointait sur le faux : l'effacer, sinon
# find_designer() repondrait encore cmd.exe et la decouverte reelle ne serait
# plus observee que par la fenetre
mod._set_option(mod.DESIGNER_OPTION, "")
installe = os.path.join(mod._qt_binaries_dir() or "", "designer.exe")
if not os.path.isfile(installe):
    print("     (Designer de la distribution non installe sur ce poste : volet 3 saute)")
else:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    try:
        vrai = mod._run_designer(installe)
        temps = 12
        for _ in range(temps):
            time.sleep(1)
            if vrai.poll() is not None:
                break
        code = vrai.poll()
        fenetres = []

        user32 = ctypes.windll.user32
        procede = ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
        pid_cible = w.DWORD()

        def collecter(hwnd, _lparam):
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_cible))
            if pid_cible.value == vrai.pid and user32.IsWindowVisible(hwnd):
                taille = user32.GetWindowTextLengthW(hwnd)
                tampon = ctypes.create_unicode_buffer(taille + 1)
                user32.GetWindowTextW(hwnd, tampon, taille + 1)
                classe = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, classe, 256)
                fenetres.append((tampon.value, classe.value))
            return True

        user32.EnumWindows(procede(collecter), 0)
        if code is None:
            vrai.terminate()
            try:
                vrai.wait(timeout=10)
            except subprocess.TimeoutExpired:
                vrai.kill()
    finally:
        os.environ.pop("QT_QPA_PLATFORM", None)
    check("designer reel: le binaire du paquet est bien celui decouvert",
          mod.find_designer() == os.path.abspath(installe), mod.find_designer())
    check("designer reel: il tient vivant %ds sans fenetre ni boite d'erreur" % temps,
          code is None and not fenetres,
          (hex(code) if code is not None else "vivant", fenetres[:3]))
    check("designer reel: l'environnement prete n'a rien invente",
          "QT_QPA_PLATFORM" not in mod._qt_designer_environ(installe),
          sorted(k for k in mod._qt_designer_environ(installe) if "QT_" in k))
    composantes = os.path.join(os.path.dirname(installe), "Qt5DesignerComponents.dll")
    check("designer reel: la DLL que seul le paquet apporte est a cote de lui",
          os.path.isfile(composantes), composantes)
    check("designer reel: les DLLs Qt du paquet entourent le binaire",
          bool(glob.glob(os.path.join(os.path.dirname(installe), "Qt5Core*.dll"))),
          os.path.dirname(installe))

# ── 4. le fichier transmis vient de la vue, pas d'une copie du module ─────
# Les autres suites bouchonnent Popen et lisent ses arguments ; celle-ci est la
# seule a demarrer un vrai processus. Le controle suivant est donc celui de la
# realite : ce que le concepteur a a l'ecran est bien ce que designer.exe a
# recu, et le module n'a plus d'avis propre sur la question (item 9).
check("cible : le module ne detient pas le fichier de l'eleve",
      not hasattr(mod, "qt_ui_file"),
      sorted(n for n in dir(mod) if "ui_file" in n))
check("cible : le vrai processus a recu le fichier affiche par la vue",
      lances_reels
      and lances_reels[0][0][-1] == os.path.abspath(wb.vue.ui_file),
      [a for a, _ in lances_reels[:1]])
check("cible : et il l'a recu en absolu",
      lances_reels and os.path.isabs(lances_reels[0][0][-1]),
      lances_reels[0][0] if lances_reels else [])

# ── rangeement : le dossier de l'eleve ne doit pas trainer un faux Designer ──
os.chdir(HERE)
shutil.rmtree(TEMP, ignore_errors=True)

fails = [r for r in results if not r[1]]
print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
sys.exit(1 if fails else 0)
