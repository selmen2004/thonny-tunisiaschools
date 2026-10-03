r"""Le greffon sait-il trouver, prêter et installer Qt Designer.

Trois metiers dans un seul fichier (`__init__.py`) : deviner ou est designer.exe,
le lancer dans de bonnes conditions, et — depuis le module pyqt5-qt5-designer de
la distribution — le proposer a installer d'un clic. Aucun ne se regarde a
l'ecran : tout passe par de fausses workbenches, de fausses boites de dialogue et
une fausse commande pip, sur des arborescences fabriquees dans `_sortie`.

Le point important de cette reecriture : la suite ne depend plus de l'etat de la
machine. Les versions precedentes affirmaient « Designer n'est pas installe ici »,
ce qui cessait d'etre vrai des que le paquet etait pose — et, pire, laissait
passer une regression le jour ou le paquet est present. Les sources de decouverte
(`_qt_binaries_dir`, `_qt_plugins_dir`, `_thonny_user_dir`, `_sites_de_pip`,
`sys.path`, `sys.executable`, `PATH`) sont donc pincees sur des faux repertoires,
et l'etat reel de la machine n'est plus observe que dans une section aparte qui
nonce une verite d'invariant, jamais une presence.

Sections :
  1  la liste des candidats, sur arborescence controlee
  2  la resolution d'un candidat
  3  rien d'installe : refuser l'installation reste propre
  4  un clic : pip installe et le concepteur s'ouvre dans la seconde
  5  chaque echec de pip est explique dans la langue de l'enseignant
  6  l'environnement prete a designer.exe
  7  les arbres ou pip peut deposer le paquet
  8  choisir le binaire a la main, et le menu « Configurer Designer »
  9  le texte et le code : ce qui est promis, ce qui a disparu
 10  la machine reelle, en invariants et non en presence
"""
import ast
import importlib
import io
import os
import shutil
import sys
import types

PKG = "thonnycontrib.tunisiaschools"
mod = importlib.import_module(PKG)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = HERE                       # les gabarits .ui sont versionnes ici
TEMP = os.path.join(HERE, "_sortie", "designer")

results = []


def check(label, ok, detail=""):
    # la detail est figure tout de suite : les listes enregistrees (box.calls,
    # lances) vivent encore quand le bilan est reimprime, et elles ont change
    detail = str(detail)
    if len(detail) > 220:
        detail = detail[:220] + "…"
    results.append((label, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + label +
          (("  <- " + detail) if detail else ""))


# ── l'arborescence factice ───────────────────────────────────────────────
PAQUET = os.path.join(TEMP, "paquet")
P_BIN = os.path.join(PAQUET, "PyQt5", "Qt5", "bin")
P_PLUG = os.path.join(PAQUET, "PyQt5", "Qt5", "plugins")
P_PLATE = os.path.join(P_PLUG, "platforms")
USER = os.path.join(TEMP, "user_site", "PyQt5", "Qt5", "bin")
EXT = os.path.join(TEMP, "extensions", "PyQt5", "Qt5", "bin")
DANS_SYS = os.path.join(TEMP, "dans_sys_path", "PyQt5", "Qt5", "bin")
THONNY_UTILISATEUR = os.path.join(TEMP, "thonny_utilisateur")
T_BIN = os.path.join(THONNY_UTILISATEUR, "qt5_applications", "Qt", "bin")
ELEVE = os.path.join(TEMP, "dossier_de_leleve")
DU_PATH = os.path.join(TEMP, "du_path")
# un PyQt5 range sous le dossier courant : ce que « voit » une entree relative
# de sys.path ('' ou 'dossier_relatif'), c'est-a-dire le poste de l'eleve
RELATIF = os.path.join(TEMP, "PyQt5", "Qt5", "bin")
RELATIF_NOMME = os.path.join(TEMP, "dossier_relatif", "PyQt5", "Qt5", "bin")
SYSTEME = r"C:\Windows\System32"
TOUS_BINS = [P_BIN, USER, EXT, DANS_SYS, T_BIN, ELEVE, DU_PATH]


def ecrire(chemin, contenu=b"MZ faux designer"):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as fh:
        fh.write(contenu)
    return chemin


def construire_arbre():
    if os.path.isdir(TEMP):
        shutil.rmtree(TEMP, ignore_errors=True)
    for dossier in (P_BIN, P_PLATE, USER, EXT, DANS_SYS, T_BIN, ELEVE, DU_PATH):
        os.makedirs(dossier, exist_ok=True)
    # le Qt du paquet a ses plugins : c'est ce que l'environnement prete
    for nom in ("qwindows.dll", "qoffscreen.dll"):
        ecrire(os.path.join(P_PLATE, nom), b"MZ plugin")
    ecrire(os.path.join(DU_PATH, "designer.exe"), b"MZ designer du PATH")
    ecrire(os.path.join(ELEVE, "designer.exe"), b"MZ designer egare par un eleve")
    ecrire(os.path.join(RELATIF, "designer.exe"), b"MZ designer d'un PyQt5 relatif")
    ecrire(os.path.join(RELATIF_NOMME, "designer.exe"), b"MZ designer d'un site relatif")


construire_arbre()
FAUX_UI = os.path.join(FIXTURES, "designer_layout.ui")

# ── les faux de service ──────────────────────────────────────────────────
NOMS_PINCES = ("_qt_binaries_dir", "_qt_plugins_dir", "_thonny_user_dir",
               "_sites_de_pip", "subprocess", "messagebox", "get_workbench",
               "askopenfilename", "sys")
ORIG = {n: getattr(mod, n) for n in NOMS_PINCES}
CHERCHE_ORIG = os.environ.get("PATH")
CWD_ORIG = os.getcwd()
SYSPATH_ORIG = list(sys.path)


class FausseVue:
    """La vue du concepteur, reduite a ce que la commande regarde : le fichier
    qu'elle affiche. Depuis l'item 9 il n'y a plus de copie `qt_ui_file` dans le
    module — c'est la vue qui decide de la cible de « Ouvrir dans Designer », si
    bien que c'est ici qu'on pose ce que l'eleve « a a l'ecran ».
    `ui_file = ""` : un document neuf, jamais enregistre."""

    def __init__(self, ui_file=""):
        self.ui_file = ui_file


class FakeWB:
    def __init__(self):
        self.opts = {}
        self.vue = FausseVue()
        self.demandes = []

    def get_view(self, name, create=True):
        # le vrai `get_view` de Thonny leve sur une vue absente quand create est
        # False ; la commande, elle, ne doit jamais demander la creation.
        self.demandes.append((name, create))
        if name != "UiViewerPlugin":
            raise AssertionError("vue inattendue : %s" % name)
        return self.vue

    def get_option(self, name, default=None):
        return self.opts.get(name, default)

    def set_option(self, name, value):
        self.opts[name] = value

    def get_menu(self, name):
        raise AssertionError("menu not used here")


class FakeBox:
    """Boites de Tk enregistrees ; les reponses aux questions se pilotent a la file."""

    def __init__(self):
        self.calls = []
        self.reponses = []
        self.yes = True

    def puis(self, *reponses):
        self.reponses = list(reponses)
        return self

    def showerror(self, title, msg, **kw):
        self.calls.append(("error", title, msg))

    def showinfo(self, title, msg, **kw):
        self.calls.append(("info", title, msg))

    def askyesno(self, title, msg, **kw):
        self.calls.append(("ask", title, msg))
        if self.reponses:
            return self.reponses.pop(0)
        return self.yes


wb = FakeWB()
box = FakeBox()
lances = []
pip_appels = []
pip_reponses = []
pip_effet = []


class Resultat:
    def __init__(self, code=0, sortie="", erreurs=""):
        self.returncode = code
        self.stdout = sortie
        self.stderr = erreurs


def faux_popen(args, **kw):
    lances.append({"args": list(args), "kw": kw})
    return types.SimpleNamespace(args=args)


def faux_run(commande, **kw):
    pip_appels.append({"cmd": list(commande), "kw": kw})
    for effet in pip_effet:
        effet()
    if pip_reponses:
        reponse = pip_reponses.pop(0)
        if isinstance(reponse, BaseException):
            raise reponse
        return reponse
    return Resultat()


PIN = {
    "binaires": P_BIN,
    "plugins": P_PLUG,
    "thonny_user": THONNY_UTILISATEUR,
    "sites_pip": [os.path.dirname(os.path.dirname(os.path.dirname(USER))),
                  os.path.dirname(os.path.dirname(os.path.dirname(EXT)))],
    "sys_path": [DANS_SYS[: -len(os.path.join("PyQt5", "Qt5", "bin"))], ELEVE, ""],
    "executable": os.path.join(PAQUET, "python.exe"),
}


def pincer():
    """Tout ce que la decouverte regarde vient des faux, pas de la machine."""
    mod._qt_binaries_dir = lambda: PIN["binaires"]
    mod._qt_plugins_dir = lambda: PIN["plugins"]
    mod._thonny_user_dir = lambda: PIN["thonny_user"]
    mod._sites_de_pip = lambda: list(PIN["sites_pip"])
    # la liste partagee, pas une copie : les sections qui reecrivent
    # PIN["sys_path"] en cours de route doivent etre vues par le greffon
    mod.sys = types.SimpleNamespace(path=PIN["sys_path"],
                                    version_info=sys.version_info,
                                    executable=PIN["executable"])
    mod.subprocess = types.SimpleNamespace(Popen=faux_popen, run=faux_run)
    mod.messagebox = box
    mod.get_workbench = lambda: wb
    mod.askopenfilename = lambda **kw: ""
    os.environ["PATH"] = os.pathsep.join([DU_PATH, SYSTEME])
    os.environ.pop("QT_DESIGNER_PATH", None)
    wb.opts[mod.DESIGNER_OPTION] = ""
    wb.vue.ui_file = ""
    wb.demandes.clear()
    lances.clear(); pip_appels.clear(); pip_reponses.clear(); pip_effet.clear()
    box.calls.clear(); box.reponses = []; box.yes = True


def retablir():
    for n, v in ORIG.items():
        setattr(mod, n, v)
    if CHERCHE_ORIG is not None:
        os.environ["PATH"] = CHERCHE_ORIG
    os.chdir(CWD_ORIG)
    sys.path[:] = SYSPATH_ORIG


BIN = mod  # raccourci de lecture


def rien_installe():
    """Vider tous les arbres de decouverte, y compris le PATH.

    Le dossier de l'eleve garde son designer.exe egare : c'est justement lui que
    la decouverte ne doit JAMAIS trouver, et il sert aux choix faits a la main.
    """
    for dossier in (P_BIN, USER, EXT, DANS_SYS, T_BIN, DU_PATH):
        for n in os.listdir(dossier):
            os.remove(os.path.join(dossier, n))
    os.environ["PATH"] = SYSTEME
    os.environ.pop("QT_DESIGNER_PATH", None)
    wb.opts[mod.DESIGNER_OPTION] = ""


# ── 1. la liste des candidats, sur arborescence controlee ────────────────
print("=== 1. la liste des candidats ===")
pincer()
for dossier in (P_BIN, USER, EXT, DANS_SYS, T_BIN):
    ecrire(os.path.join(dossier, "designer.exe"))
cands = mod._designer_candidates()
check("candidates: tous les arbres sont explores", len(cands) >= 8, len(cands))
check("candidates: que des chaines non vides",
      all(isinstance(c, str) and c.strip() for c in cands))
check("candidates: aucun doublon", len(cands) == len(set(cands)), str(cands))
check("candidates: le Qt du paquet est le premier chemin existe",
      cands.index(os.path.normpath(os.path.join(P_BIN, "designer.exe"))) == 0, cands[:3])
position_du_paquet = cands.index(os.path.normpath(os.path.join(P_BIN, "designer.exe")))
positions_pip = [cands.index(os.path.normpath(os.path.join(d, "designer.exe")))
                 for d in (USER, EXT, DANS_SYS)]
check("candidates: les arbres de pip viennent apres le Qt du paquet",
      all(p > position_du_paquet for p in positions_pip), (position_du_paquet, positions_pip))
pf = [i for i, c in enumerate(cands) if "Program Files" in c]
check("candidates: les arbres de pip viennent avant « Program Files »",
      all(min(pf) > p for p in positions_pip), (positions_pip, pf))
check("candidates: les deux « Program Files » sont separes", len(pf) == 2, pf)
check("candidates: un nom du PATH reste candidat",
      "designer.exe" in cands and "pyqt5_qt5_designer.exe" in cands)
check("candidates: que des noms de binaire connus",
      all(os.path.basename(c) in ("designer.exe", "pyqt5_qt5_designer.exe")
          for c in cands), str(cands))
check("candidates: les chemins avec dossier sont absolus",
      all(os.path.isabs(c) for c in cands if os.path.dirname(c)), str(cands))
# le choix memorise peut coincider avec un arbre que la decouverte explore de
# toute facon : le repeter ferait repercurer la meme question a l'eleve
wb.opts[mod.DESIGNER_OPTION] = os.path.normpath(os.path.join(P_BIN, "designer.exe"))
doublon = os.path.normpath(os.path.join(P_BIN, "designer.exe"))
check("candidates: un choix deja explore ne compte qu'une fois",
      mod._designer_candidates().count(doublon) == 1,
      [c for c in mod._designer_candidates() if c == doublon])
wb.opts[mod.DESIGNER_OPTION] = os.path.join(ELEVE, "designer.exe")
check("candidates: le choix memorise passe avant tout le monde",
      mod._designer_candidates()[0] == os.path.join(ELEVE, "designer.exe"),
      mod._designer_candidates()[:2])
wb.opts[mod.DESIGNER_OPTION] = ""
os.environ["QT_DESIGNER_PATH"] = os.path.join(ELEVE, "designer.exe")
check("candidates: la variable d'environnement juste apres le choix memorise",
      mod._designer_candidates()[0] == os.path.join(ELEVE, "designer.exe"),
      mod._designer_candidates()[:2])
os.environ.pop("QT_DESIGNER_PATH", None)
check("candidates: rien ne concatene deux chemins",
      not any("exe" + os.sep in c and c.count("designer.exe") > 1 for c in cands),
      [c for c in cands if c.count("designer.exe") > 1])
check("candidates: aucune entree n'est un dossier nu",
      all(not os.path.isdir(c) for c in cands), [c for c in cands if os.path.isdir(c)])

# ── 2. la resolution d'un candidat ───────────────────────────────────────
print("=== 2. resolution ===")
check("resolve: chemin inexistant rejete",
      mod._resolve_designer(os.path.join(TEMP, "nope", "designer.exe")) is None)
check("resolve: nom inconnu du PATH rejete", mod._resolve_designer("designer_absent.exe") is None)
check("resolve: nom du PATH resolu", mod._resolve_designer("designer.exe")
      == os.path.join(DU_PATH, "designer.exe"), mod._resolve_designer("designer.exe"))
check("resolve: chaine vide", mod._resolve_designer("") is None)
check("resolve: un dossier ne suffit pas", mod._resolve_designer(P_BIN) is None)
check("resolve: PATHEXT respecte", mod._resolve_designer("where") is not None,
      mod._resolve_designer("where"))
os.chdir(ELEVE)   # le dossier de l'eleve, avec son designer.exe egare
check("resolve: le dossier courant est ignore",
      os.path.isfile("designer.exe") and mod._resolve_designer("designer.exe")
      == os.path.join(DU_PATH, "designer.exe"), os.getcwd())
check("resolve: find_designer ne prend jamais le fichier de l'eleve",
      mod.find_designer() == os.path.abspath(os.path.normpath(
          os.path.join(P_BIN, "designer.exe"))), mod.find_designer())
os.chdir(CWD_ORIG)
for dossier in (P_BIN,):
    os.remove(os.path.join(dossier, "designer.exe"))
# le Qt du paquet est vide, les arbres de pip sont pleins : la recherche doit
# continuer sa route, sinon le premier dossier absent fermerait le concepteur
check("find: un candidat manquant n'arrete pas la recherche",
      mod.find_designer() == os.path.abspath(os.path.normpath(
          os.path.join(T_BIN, "designer.exe"))), mod.find_designer())
for dossier in (USER, EXT, DANS_SYS, T_BIN):
    for n in os.listdir(dossier):
        os.remove(os.path.join(dossier, n))
check("find: reste le nom du PATH, qui mene au concepteur du PATH",
      mod.find_designer() == os.path.join(DU_PATH, "designer.exe"), mod.find_designer())

# ── 3. rien d'installe : refuser l'installation reste propre ─────────────
print("=== 3. rien d'installe, on refuse ===")
rien_installe()
check("find: plus rien de rien", mod.find_designer() is None, mod.find_designer())
lances.clear(); box.calls.clear()
box.puis(False, False)      # refus d'installer, puis refus de chercher a la main
ok = mod.open_in_designer()
check("open: False quand rien n'est installe et qu'on refuse tout", ok is False, ok)
check("open: la premiere question est l'installation",
      box.calls and box.calls[0][0] == "ask" and "L'installer maintenant" in box.calls[0][2],
      box.calls[:1])
premiere_question = box.calls[0][2] if box.calls else "(aucune question posee)"
check("open: la question dit le nom du module et son poids",
      mod.PAQUET_DESIGNER in premiere_question and "1 Mo" in premiere_question,
      premiere_question[:120])
check("open: apres le refus, on propose encore de chercher a la main",
      [c[0] for c in box.calls] == ["ask", "ask", "error"], [c[0] for c in box.calls])
check("open: rien lance", lances == [], str(lances))
check("open: aucun pip lance apres un refus", pip_appels == [], str(pip_appels))
check("open: le message final nomme le bon module",
      any(c[0] == "error" and mod.PAQUET_DESIGNER in c[2] for c in box.calls),
      box.calls[-1][2][:160] if box.calls else "(aucune boite)")
check("open: il ne renvoie plus l'ancien module",
      all("pyqt5-designer" not in c[2] for c in box.calls), [c[2][:80] for c in box.calls])

# ── 4. un clic suffit ────────────────────────────────────────────────────
print("=== 4. un clic, et cela s'ouvre ===")
pincer()
ecrire(os.path.join(P_BIN, "designer.exe"))
ecrire(os.path.join(P_BIN, "Qt5DesignerComponents.dll"), b"MZ composants")
ecrire(os.path.join(P_BIN, "qt.conf"), b"[Paths]\nprefix = ../\n")
installe = os.path.join(P_BIN, "designer.exe")
os.remove(installe)


def pip_reussit():
    """le pip factice fait ce que fait le vrai : il depose les trois fichiers"""
    ecrire(os.path.join(P_BIN, "designer.exe"))
    ecrire(os.path.join(P_BIN, "Qt5DesignerComponents.dll"), b"MZ composants")
    ecrire(os.path.join(P_BIN, "qt.conf"), b"[Paths]\nprefix = ../\n")


pip_effet.append(pip_reussit)
pip_reponses.append(Resultat(0, "Successfully installed pyqt5-qt5-designer-0.0.14"))
box.puis(True)
wb.vue.ui_file = FAUX_UI
ok = mod.open_in_designer()
check("install: un seul askyesno, un seul pip, un seul lancement",
      ok is True and len(box.calls) == 1 and len(pip_appels) == 1 and len(lances) == 1,
      (ok, box.calls, len(pip_appels), len(lances)))
commande = pip_appels[0]["cmd"] if pip_appels else ["(aucun pip lance)"]
check("pip: avec l'interpreteur de Thonny", commande[0] == PIN["executable"], commande[0])
check("pip: -m pip install", commande[1:4] == ["-m", "pip", "install"], commande[:6])
check("pip: le module de la distribution, en dernier argument",
      commande[-1] == "pyqt5-qt5-designer", commande[-1])
check("pip: PAS de --user (le paquet doit rejoindre le Qt de Thonny)",
      "--user" not in commande and "-u" not in commande, commande)
check("pip: ni index ni cible detournee",
      not any(a.startswith(("--index-url", "--extra-index", "--target", "--prefix",
                            "--no-deps", "--upgrade")) for a in commande), commande)
kw_pip = pip_appels[0]["kw"] if pip_appels else {}
check("pip: silencieux mais avec un timeout",
      kw_pip.get("capture_output") is True and kw_pip.get("timeout") == 900, kw_pip)
check("install: Designer trouve dans la meme cliquee, sans redemarrer Thonny",
      mod.find_designer() == os.path.abspath(os.path.normpath(installe)),
      mod.find_designer())
lance = lances[0] if lances else {"args": ["(rien lance)"], "kw": {}}
check("lance: le binaire installe et le .ui de l'eleve",
      lance["args"] == [os.path.normpath(installe), os.path.abspath(FAUX_UI)],
      lance["args"])
env = lance["kw"].get("env") or {}
check("lance: le PATH prete le dossier des DLLs Qt",
      env.get("PATH", "").split(os.pathsep)[0] == P_BIN, env.get("PATH", "")[:120])
check("lance: les plugins Qt sont pretes aussi",
      env.get("QT_PLUGIN_PATH") == P_PLUG
      and env.get("QT_QPA_PLATFORM_PLUGIN_PATH") == P_PLATE,
      (env.get("QT_PLUGIN_PATH"), env.get("QT_QPA_PLATFORM_PLUGIN_PATH")))
check("lance: l'environnement de Thonny n'est pas salit",
      "QT_PLUGIN_PATH" not in os.environ or os.environ["QT_PLUGIN_PATH"] != P_PLUG,
      os.environ.get("QT_PLUGIN_PATH"))
check("lance: aucun message d'erreur", not any(c[0] == "error" for c in box.calls),
      box.calls)

# ── 5. chaque echec de pip est explique ─────────────────────────────────
print("=== 5. les echecs, un par un ===")
HORS_LIGNE = ("ERROR: Could not find a version that satisfies the requirement "
              "pyqt5-qt5-designer (from versions: none)\n"
              "ERROR: No matching distribution found for pyqt5-qt5-designer")
REFUS = ("ERROR: Could not install packages due to an OSError: "
         "[WinError 5] Accès refusé\nConsider using the --user option or check the permissions.")
INCONNU = "ERROR: cannot import name 'X' (some other trouble)"
for sortie_attendue, etiquette, motif in (
        (HORS_LIGNE, "hors ligne", "hors ligne"),
        (REFUS, "dossier protege", "administrateur"),
        (INCONNU, "pip contrarie", "n'a pas abouti")):
    pincer()
    rien_installe()
    box.puis(True)
    pip_reponses.append(Resultat(1, "", sortie_attendue))
    ok = mod.open_in_designer()
    un_seul = [c for c in box.calls]
    dite = un_seul[1][2] if len(un_seul) > 1 and un_seul[1][0] == "error" else "(rien d'explique)"
    check("echec %s : False, une question puis une erreur, rien lance" % etiquette,
          ok is False and len(un_seul) == 2 and un_seul[1][0] == "error" and lances == [],
          [(c[0], c[2][:40]) for c in un_seul])
    check("echec %s : la raison est dite en francais" % etiquette,
          motif in dite, dite[:200])
    check("echec %s : la reponse de pip reste lisible pour degoter" % etiquette,
          "--- pip ---" in dite and sortie_attendue.splitlines()[-1][:30] in dite,
          dite[-200:])
pincer()
rien_installe()
box.puis(True)
pip_reponses.append(OSError("timed out"))
ok = mod.open_in_designer()
check("echec timeout : la Main reste a l'enseignant, et le dit",
      ok is False and any(c[0] == "error" and "OSError" in c[2] for c in box.calls),
      [c[2][:80] for c in box.calls])
check("echec timeout : pas de poursuite silenciee vers pip", len(pip_appels) == 1)
pincer()
rien_installe()
box.puis(True)
pip_reponses.append(Resultat(0, "Successfully installed pyqt5-qt5-designer-0.0.14"))
ok = mod.open_in_designer()          # pip a reussi, mais le binaire n'est pas la
check("pip vert mais binaire absent : l'eleve n'est pas laisse sans reponse",
      ok is False and any("reste introuvable" in c[2] for c in box.calls if c[0] == "error"),
      [c[2][:60] for c in box.calls])
check("pip vert mais binaire absent : pas de question en plus",
      len(box.calls) == 2 and box.calls[1][0] == "error",
      [c[0] for c in box.calls])
pincer()
rien_installe()
box.puis(False, True)
lances.clear(); box.calls.clear()
mod.askopenfilename = lambda **kw: os.path.join(ELEVE, "designer.exe")
ok = mod.open_in_designer()
check("refus d'installer : la recherche a la main est conservee",
      ok is True and wb.opts.get(mod.DESIGNER_OPTION)
      == os.path.abspath(os.path.join(ELEVE, "designer.exe")),
      (ok, wb.opts, lances))
check("refus d'installer : aucun pip lance", pip_appels == [], str(pip_appels))
wb.opts[mod.DESIGNER_OPTION] = ""

# ── 6. l'environnement prete a designer.exe ─────────────────────────────
print("=== 6. l'environnement prete ===")
pincer()
e = mod._qt_designer_environ(os.path.join(USER, "designer.exe"))
check("env: PATH commence par le Qt du paquet",
      e["PATH"].split(os.pathsep)[0] == P_BIN, e["PATH"][:100])
check("env: le PATH d'origine est conserve derriere",
      DU_PATH in e["PATH"].split(os.pathsep)[1:], e["PATH"][-120:])
check("env: QT_PLUGIN_PATH et les plateformes sont designes",
      e.get("QT_PLUGIN_PATH") == P_PLUG
      and e.get("QT_QPA_PLATFORM_PLUGIN_PATH") == P_PLATE)
PIN["plugins"] = os.path.join(TEMP, "sans_plugins")
e2 = mod._qt_designer_environ("")
check("env: sans dossier de plugins, rien n'est invente",
      "QT_PLUGIN_PATH" not in e2 and "QT_QPA_PLATFORM_PLUGIN_PATH" not in e2,
      sorted(k for k in e2 if "QT_" in k))
os.makedirs(os.path.join(TEMP, "sans_plugins", "styles"), exist_ok=True)
e3 = mod._qt_designer_environ("")
check("env: plugins sans sous-dossier platforms -> platforms absent",
      e3.get("QT_PLUGIN_PATH") == os.path.join(TEMP, "sans_plugins")
      and "QT_QPA_PLATFORM_PLUGIN_PATH" not in e3, sorted(e3))
PIN["plugins"] = P_PLUG
PIN["binaires"] = None
e4 = mod._qt_designer_environ("")
check("env: sans Qt identifiable, l'environnement heredite tel quel",
      e4 == dict(os.environ) and "PATH" in e4 and "QT_PLUGIN_PATH" not in e4,
      sorted(k for k in e4 if "QT_" in k))
PIN["binaires"] = P_BIN
avant = dict(os.environ)
mod._qt_designer_environ("")
check("env: la machine n'est jamais modifiee par l'appel",
      os.environ == avant, sorted(set(os.environ.items()) ^ set(avant.items())))
check("env: une clee d'environnement nouvelle n'efface pas le reste",
      e.get("SYSTEMROOT") == os.environ.get("SYSTEMROOT"), e.get("SYSTEMROOT"))

# ── 7. les arbres ou pip peut deposer le paquet ─────────────────────────
print("=== 7. les arbres de pip ===")
pincer()
for dossier in (USER, EXT, DANS_SYS):
    ecrire(os.path.join(dossier, "designer.exe"))
trouves = mod._designer_des_autres_sites()
check("sites: les trois arbres de pip sont trouves",
      set(trouves) == {os.path.normpath(os.path.join(d, "designer.exe"))
                       for d in (DANS_SYS, USER, EXT)}, sorted(trouves))
check("sites: des chemins absolus et normalises",
      all(os.path.isabs(c) and "\\" in c and "/" not in c for c in trouves), trouves)
PIN["sys_path"][:] = ["", "dossier_relatif", os.path.join(TEMP, "inexistant")]
# place sous le dossier courant : une entree relative de sys.path pointerait sur
# ce PyQt5-la, c'est-a-dire sur celui du dossier ou travaille l'eleve
os.chdir(TEMP)
check("sites: une entree relative de sys.path est ignoree",
      mod._designer_des_autres_sites() ==
      [os.path.normpath(os.path.join(d, "designer.exe")) for d in (USER, EXT)],
      mod._designer_des_autres_sites())
check("sites: les leurres relatifs existent bien, le test n'est pas creux",
      os.path.isfile(os.path.join(RELATIF, "designer.exe"))
      and os.path.isfile(os.path.join(RELATIF_NOMME, "designer.exe")),
      [RELATIF, RELATIF_NOMME])
os.chdir(CWD_ORIG)
PIN["sys_path"][:] = [DANS_SYS[: -len(os.path.join("PyQt5", "Qt5", "bin"))], ELEVE]
check("sites: le dossier de l'eleve n'est pas un site",
      all(ELEVE not in c for c in mod._designer_des_autres_sites()),
      mod._designer_des_autres_sites())
PIN["sys_path"][:] = [DANS_SYS[: -len(os.path.join("PyQt5", "Qt5", "bin"))]]
sites = mod._sites_de_pip()
check("sites_de_pip: deux destinations, absolues", len(sites) == 2
      and all(os.path.isabs(s) for s in sites), sites)
retablir()
pincer_reel = [s for s in mod._sites_de_pip()]
check("a machine reelle: le site utilisateur et le dossier des extensions sont cites",
      any("site-packages" in s.lower() for s in pincer_reel), pincer_reel)
retablir()
pincer()

# ── 8. choisir a la main, et le menu « Configurer Designer » ─────────────
print("=== 8. le choix manuel ===")
rien_installe()
ecrire(os.path.join(ELEVE, "designer.exe"))
chemin_eleve = os.path.abspath(os.path.join(ELEVE, "designer.exe"))
box.puis(False, True)
mod.askopenfilename = lambda **kw: os.path.join(ELEVE, "designer.exe")
lances.clear(); box.calls.clear()
wb.vue.ui_file = FAUX_UI
ok = mod.open_in_designer()
check("manuel: installe refuse, choix accepte, fenetre lancee",
      ok is True and lances and lances[0]["args"][0] == chemin_eleve, (ok, lances))
check("manuel: l'option a enregistre l'absolu",
      wb.opts[mod.DESIGNER_OPTION] == chemin_eleve, wb.opts)
lances.clear(); box.calls.clear()
check("manuel: la prochaine cliquee saute les deux questions",
      mod.open_in_designer() is True and box.calls == [] and len(lances) == 1,
      (box.calls, lances))
wb.opts[mod.DESIGNER_OPTION] = os.path.join(TEMP, "plus_la", "designer.exe")
box.puis(False, True)
lances.clear(); box.calls.clear()
check("manuel: une option devenue fausse relance les questions",
      mod.open_in_designer() is True and box.calls and box.calls[0][0] == "ask",
      (box.calls, wb.opts))
wb.opts[mod.DESIGNER_OPTION] = ""
mod.askopenfilename = lambda **kw: os.path.join(TEMP, "not_exist", "designer.exe")
# a partir d'ici, chaque cas refuse l'installation pour arriver jusqu'a la
# recherche manuelle ; si un pip part ici, c'est que le refus a ete ignore
box.puis(False, True)
box.calls.clear()
check("manuel: un chemin invalide est signale, pas memorise",
      mod.open_in_designer() is False and wb.opts.get(mod.DESIGNER_OPTION, "") == ""
      and any(c[0] == "error" for c in box.calls), (wb.opts, box.calls))
mod.askopenfilename = lambda **kw: ELEVE
box.puis(False, True)
box.calls.clear()
check("manuel: un dossier est refuse",
      mod.open_in_designer() is False and wb.opts.get(mod.DESIGNER_OPTION, "") == "",
      wb.opts)
mod.askopenfilename = lambda **kw: os.path.join(SYSTEME, "notepad.exe")
box.puis(False, True)
box.calls.clear()
check("manuel: un autre executable est refuse sous son nom",
      mod.open_in_designer() is False and wb.opts.get(mod.DESIGNER_OPTION, "") == ""
      and any("pas Qt Designer" in c[2] for c in box.calls if c[0] == "error"),
      [c[2][:60] for c in box.calls])
renomme = ecrire(os.path.join(ELEVE, "mon_designer.exe"))
mod.askopenfilename = lambda **kw: renomme
box.puis(False, True)
box.calls.clear()
check("manuel: un Designer renomme reste acceptable",
      mod.open_in_designer() is True
      and wb.opts[mod.DESIGNER_OPTION] == os.path.abspath(renomme), wb.opts)
wb.opts[mod.DESIGNER_OPTION] = ""
mod.askopenfilename = lambda **kw: ""
box.puis(False, True)
check("manuel: une annulation ne casse rien", mod.open_in_designer() is False)
check("manuel: aucun pip lance pendant qu'on cherchait a la main",
      pip_appels == [], str(pip_appels)[:200])

lances.clear()
def explosion(args, **kw):
    raise OSError(13, "Accès refusé")
mod.subprocess = types.SimpleNamespace(Popen=explosion, run=faux_run)
wb.opts[mod.DESIGNER_OPTION] = os.path.abspath(renomme)
box.calls.clear()
check("lancement impossible: False et la raison sous les yeux",
      mod.open_in_designer() is False
      and any(c[0] == "error" and "Accès refusé" in c[2] for c in box.calls),
      [c[2][:80] for c in box.calls])
mod.subprocess = types.SimpleNamespace(Popen=faux_popen, run=faux_run)

wb.vue.ui_file = os.path.join(TEMP, "introuvable.ui")
lances.clear(); box.calls.clear()
ok = mod.open_in_designer()
check("fichier disparu: Designer s'ouvre quand meme, sans argument",
      ok is True and len(lances) == 1 and lances[0]["args"] == [os.path.abspath(renomme)]
      and "env" in lances[0]["kw"], (ok, lances))
check("fichier disparu: aucune question, aucune erreur",
      box.calls == [], box.calls)
wb.opts[mod.DESIGNER_OPTION] = ""

box.calls.clear(); box.puis(True, False)
mod.askopenfilename = lambda **kw: renomme
check("menu: Configurer Designer enregistre et le confirme",
      mod.configure_designer() is True and wb.opts[mod.DESIGNER_OPTION]
      == os.path.abspath(renomme) and any(c[0] == "info" for c in box.calls),
      (wb.opts, [c[0] for c in box.calls]))
box.calls.clear(); box.puis(False)
wb.opts[mod.DESIGNER_OPTION] = os.path.abspath(renomme)
check("menu: refuser d'en choisir un autre garde la detection",
      mod.configure_designer() is False
      and wb.opts[mod.DESIGNER_OPTION] == os.path.abspath(renomme), wb.opts)
box.calls.clear(); box.puis(True, False)
mod.askopenfilename = lambda **kw: ""
check("menu: annuler le choix n'efface pas l'option",
      mod.configure_designer() is False
      and wb.opts[mod.DESIGNER_OPTION] == os.path.abspath(renomme), wb.opts)
wb.opts[mod.DESIGNER_OPTION] = ""

# ── 9. le texte et le code ──────────────────────────────────────────────
print("=== 9. texte et code ===")
source = io.open(os.path.join(os.path.dirname(mod.__file__), "__init__.py"),
                 encoding="utf-8").read()
arbre = ast.parse(source)
# les anciens noms ont leur place dans les commentaires, qui expliquent pourquoi
# on les a ecartes ; ils n'ont plus le droit d'apparaitre dans un mot que l'eleve lit
MOTS_DITS = [n.value for n in ast.walk(arbre)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)]
check("module: PAQUET_DESIGNER est bien le nom PyPI",
      mod.PAQUET_DESIGNER == "pyqt5-qt5-designer", mod.PAQUET_DESIGNER)
check("texte: plus aucune pub pour pyqt5-designer ni PyQt5Designer",
      not any("pyqt5-designer" in t and "pyqt5-qt5-designer" not in t or "PyQt5Designer" in t
              for t in MOTS_DITS),
      [t[:60] for t in MOTS_DITS if "esigner" in t.lower()
       and "pyqt5-qt5-designer" not in t])
check("texte: la route sans ligne de commande est dite",
      "Gérer les paquets" in source, [l for l in source.splitlines()
                                      if "paquets" in l][:2])
check("cle d'option inchangee (les choix deja pris sont gardes)",
      mod.DESIGNER_OPTION == "pyqt5_designer.executable")
check("aucune QMessageBox dans le greffon", source.count("QMessageBox") == 0)
check("plus aucun print() dans le bloc Designer", "print(\"running" not in source)
fonctions = {n.name for n in ast.walk(arbre) if isinstance(n, ast.FunctionDef)}
NEUVES = ("_commande_pip_designer", "_installer_designer",
          "_proposer_installation_designer", "_raison_echec_installation",
          "_qt_designer_environ", "_qt_plugins_dir", "_sites_de_pip",
          "_designer_des_autres_sites")
check("les huit fonctions neuves existent", all(n in fonctions for n in NEUVES),
      [n for n in NEUVES if n not in fonctions])


def fonction_ast(nom_fonction):
    for n in ast.walk(arbre):
        if isinstance(n, ast.FunctionDef) and n.name == nom_fonction:
            return n
    return None


ouverture = fonction_ast("open_in_designer")
# l'ordre d'ast.walk suit l'ordre d'ecriture pour des appels freres du corps :
# c'est celui que l'eleve verrait, proposition d'installer puis recherche manuelle
appels_ouverture = [a.func.id for a in ast.walk(ouverture)
                    if isinstance(a, ast.Call) and isinstance(a.func, ast.Name)]
check("ouverture: l'installation est proposee avant la recherche manuelle",
      "_proposer_installation_designer" in appels_ouverture
      and "_ask_for_designer" in appels_ouverture
      and appels_ouverture.index("_proposer_installation_designer")
      < appels_ouverture.index("_ask_for_designer"), appels_ouverture)
check("ouverture: un echec deja dit ne repasse pas par la case erreur",
      any(isinstance(a, ast.Compare) and any(
              isinstance(o, ast.Is) for o in a.ops)
          and isinstance(a.comparators[0], ast.Constant)
          and a.comparators[0].value is None
          for a in ast.walk(ouverture)), "sentinelle None absente")
check("lancement: l'environnement prete est passe a Popen",
      "env=_qt_designer_environ" in source)
fabrique = fonction_ast("_commande_pip_designer")
# get_docstring rend la valeur, pas le noeud : c'est le noeud qu'il faut ecarter
premiere = fabrique.body[0]
doc_pip = premiere.value if isinstance(premiere, ast.Expr) else None
# le docstring explique justement pourquoi --user est absent : il ne compte pas
mots_de_la_commande = [n.value for n in ast.walk(fabrique)
                       if isinstance(n, ast.Constant) and isinstance(n.value, str)
                       and n is not doc_pip]
check("pip: la commande est fabriquee sans --user, meme par defaut",
      "--user" not in mots_de_la_commande and "install" in mots_de_la_commande,
      mots_de_la_commande)
check("pip: un timeout garde la main", "timeout=900" in source)
check("decouverte: les arbres de pip sont branches dans la liste des candidats",
      "_designer_des_autres_sites()" in source.split("def _designer_candidates")[1]
      .split("def _which_in_path")[0])

# ── 10. la machine reelle, en invariants ────────────────────────────────
print("=== 10. la machine reelle ===")
retablir()
reel = mod.find_designer()
print("     (find_designer() repond %s sur ce poste)" % (reel or "None"))
check("reel: la reponse est un fichier, ou rien",
      reel is None or (os.path.isabs(reel) and os.path.isfile(reel)), reel)
check("reel: un designer.exe trouve a ses composantes Qt a cote de lui",
      reel is None
      or os.path.isfile(os.path.join(os.path.dirname(reel), "Qt5DesignerComponents.dll"))
      or "PyQt5" not in reel,
      reel and os.listdir(os.path.dirname(reel))[:6])
check("reel: le Qt de Thonny est identifiable",
      os.path.isdir(mod._qt_binaries_dir() or ""), mod._qt_binaries_dir())
check("reel: les plugins Qt existent (sinon l'environnement prete serait vain)",
      os.path.isdir(mod._qt_plugins_dir() or ""), mod._qt_plugins_dir())
env_reel = mod._qt_designer_environ(reel or "")
check("reel: l'environnement prete le Qt du paquet, pas un autre",
      env_reel["PATH"].split(os.pathsep)[0] == mod._qt_binaries_dir(),
      env_reel["PATH"].split(os.pathsep)[0])
check("reel: la commande pip nomme le module de la distribution",
      mod._commande_pip_designer()[-1] == mod.PAQUET_DESIGNER
      and "--user" not in mod._commande_pip_designer(),
      mod._commande_pip_designer())
installe_vrai = os.path.isfile(os.path.join(mod._qt_binaries_dir() or "", "designer.exe"))
if installe_vrai:
    check("reel installe: les trois fichiers du paquet sont en place",
          all(os.path.isfile(os.path.join(mod._qt_binaries_dir(), n))
              for n in ("designer.exe", "Qt5DesignerComponents.dll", "qt.conf")),
          sorted(os.listdir(mod._qt_binaries_dir()))[:8])
    check("reel installe: find_designer repond le Qt du paquet",
          os.path.samefile(reel, os.path.join(mod._qt_binaries_dir(), "designer.exe")),
          (reel, mod._qt_binaries_dir()))
else:
    check("reel non installe: la liste des candidats reste exploitable",
          len(mod._designer_candidates()) >= 5, mod._designer_candidates())
    check("reel non installe: la proposition d'installation est la bonne voie",
          mod.PAQUET_DESIGNER in mod._commande_pip_designer()[-1])
check("reel: la liste des candidats n'a jamais de doublon",
      len(mod._designer_candidates()) == len(set(mod._designer_candidates())),
      mod._designer_candidates())

# ── rangeement ──────────────────────────────────────────────────────────
retablir()
# rien a remettre cote cible : l'item 9 a supprime la copie module du fichier
# de l'eleve. Le pin ci-dessous est ce qui empeche la copie de revenir par
# distraction — un `mod.qt_ui_file = ...` remis ici casserait la suite, et une
# reecriture du greffon qui la ramenerait casserait ce check.
check("cible : le module ne detient plus le fichier que l'eleve a a l'ecran",
      not hasattr(mod, "qt_ui_file"), [n for n in dir(mod) if "ui_file" in n])
shutil.rmtree(TEMP, ignore_errors=True)

fails = [r for r in results if not r[1]]
print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
for label, ok, detail in fails:
    print("FAIL  %s  <- %s" % (label, detail))
sys.exit(1 if fails else 0)
