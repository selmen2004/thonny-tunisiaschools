r"""Contrôles pour l'issue n° 1 : le bloc de démarrage de load_plugin().

L'ancien code appelait os.makedirs('C:\\bac<année>') sans protection dans
load_plugin(). Or workbench.py:426 invoque load_plugin() HORS du try/except qui
protège l'import des modules (:413-419) : la première exception venue remonte
jusqu'à Workbench() (thonny/__init__.py:284), est attrapée en :288 et n'offre
qu'une fenêtre « Internal error » avec return -1 — Thonny ne s'ouvre pas, et
l'élève ne peut même plus lancer l'application pour récupérer son travail.

Un poste de salle dont la racine C:\ est protégée en écriture déclenche
exactement ce cas. Les contrôles ci-dessous rejouent ce refus de disque, sans
jamais toucher au vrai C:\.
"""
import ast
import importlib
import os
import shutil
import sys
import tempfile
from datetime import date

mod = importlib.import_module("thonnycontrib.tunisiaschools")

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + label + (("  <- " + str(detail)) if detail else ""))


ROOT = tempfile.mkdtemp(prefix="bacworkspace")


def sandbox(*parts):
    """Un chemin dans le bac à sable, jamais sur le disque réel de l'élève."""
    return os.path.join(ROOT, *parts)


def original(fn):
    """Les fonctions du module, avant patch() : pour comparer ou restaurer."""
    return getattr(mod, fn)


def use_roots(*racines):
    """Impose les racines cherchées, sans toucher au reste du code testé."""
    patch("working_dir_roots", lambda: list(racines))


PATCHED = []


def patch(name, value):
    PATCHED.append((name, getattr(mod, name)))
    setattr(mod, name, value)


def unpatch():
    while PATCHED:
        name, value = PATCHED.pop()
        setattr(mod, name, value)


class FakeWB:
    """Le workbench, vu par prepare_student_workspace()."""

    def __init__(self, cwd_error=None, option_error=None):
        self.cwd_calls = []
        self.options = {}
        self.cwd_error = cwd_error
        self.option_error = option_error

    def set_local_cwd(self, path):
        if self.cwd_error:
            raise self.cwd_error
        self.cwd_calls.append(path)

    def set_option(self, name, value):
        if self.option_error:
            raise self.option_error
        self.options[name] = value


# ── 1. Le nom du dossier de l'année ─────────────────────────────────────────
# Le dossier porte le millésime de la PROCHAINE session de juin, pas l'année
# civile : la classe de septembre 2026 passe le bac en juin 2027.
check("septembre 2026 : la classe vise juin 2027, dossier bac2027",
      mod.bac_folder_name(date(2026, 9, 22)) == "bac2027", mod.bac_folder_name(date(2026, 9, 22)))
check("la règle est celle demandée pour aujourd'hui",
      mod.bac_folder_name(date(2026, 9, 1)) == "bac2027", mod.bac_folder_name(date(2026, 9, 1)))
# Balayage mensuel sur une année au-dessus du plancher (2028) : c'est la règle
# roulante que l'on vérifie là, le plancher 2027 interviendrait sur 2026.
for mois, attendue in [(1, "bac2028"), (6, "bac2028"), (7, "bac2029"), (12, "bac2029")]:
    check("2028 mois %02d -> %s (janv-juin = session en cours, juil-déc = suivante)" % (mois, attendue),
          mod.bac_folder_name(date(2028, mois, 15)) == attendue,
          mod.bac_folder_name(date(2028, mois, 15)))
check("la bascule tombe bien après juin : 30 juin vs 1er juillet",
      mod.bac_folder_name(date(2028, 6, 30)) == "bac2028"
      and mod.bac_folder_name(date(2028, 7, 1)) == "bac2029",
      mod.bac_folder_name(date(2028, 6, 30)) + "/" + mod.bac_folder_name(date(2028, 7, 1)))
check("une date antérieure à la rentrée 2026 est volontairement remontée à la session en cours",
      mod.bac_folder_name(date(2026, 1, 15)) == "bac2027"
      and mod.bac_folder_name(date(2026, 6, 15)) == "bac2027",
      mod.bac_folder_name(date(2026, 1, 15)) + "/" + mod.bac_folder_name(date(2026, 6, 15)))
check("le jour de la session reste dans son millésime (juin 2027 -> bac2027)",
      mod.bac_folder_name(date(2027, 6, 15)) == "bac2027", mod.bac_folder_name(date(2027, 6, 15)))
# l'année suivante doit suivre sans retoucher le code
check("renouvellement automatique : septembre 2027 -> bac2028",
      mod.bac_folder_name(date(2027, 9, 1)) == "bac2028", mod.bac_folder_name(date(2027, 9, 1)))
check("renouvellement automatique : septembre 2028 -> bac2029",
      mod.bac_folder_name(date(2028, 9, 1)) == "bac2029", mod.bac_folder_name(date(2028, 9, 1)))
check("le seul millésime écrit est le plancher de rentrée, à avancer chaque septembre",
      mod.BAC_MIN_SESSION_YEAR == 2027, mod.BAC_MIN_SESSION_YEAR)
check("les dates postérieures à la rentrée ne sont pas écrasées par ce plancher",
      mod.bac_exam_year(date(2027, 9, 1)) == 2028 and mod.bac_exam_year(date(2028, 6, 15)) == 2028,
      (mod.bac_exam_year(date(2027, 9, 1)), mod.bac_exam_year(date(2028, 6, 15))))

# contre-factuel : l'ancienne règle donnait le millésime de l'année civile,
# avec un plancher 2024 (valeur figée ici : c'est l'ancien code que l'on rejoue)
def ancien_nom(jour, plancher=2024):
    return "bac%d" % max(jour.year, plancher)


check("l'ancien code donnait bien bac2026 en septembre 2026 (le bug de nommage)",
      ancien_nom(date(2026, 9, 22)) == "bac2026" and mod.bac_folder_name(date(2026, 9, 22)) == "bac2027",
      ancien_nom(date(2026, 9, 22)))
check("l'ancien plancher laissait une horloge faussée partir en 2024",
      ancien_nom(date(2015, 12, 31)) == "bac2024", ancien_nom(date(2015, 12, 31)))

# horloge repartie en arrière : le travail doit quand même finir dans la session en cours
for jour in [date(2023, 5, 1), date(2023, 11, 1), date(2024, 1, 1), date(2015, 12, 31),
             date(2001, 1, 1), date(1970, 1, 1)]:
    check("horloge en arrière (%s) : rattrapée sur la session 2027" % jour,
          mod.bac_folder_name(jour) == "bac2027", mod.bac_folder_name(jour))
check("le rattrapage s'applique au millésime de session, pas à l'année civile",
      mod.bac_exam_year(date(2023, 5, 1)) == 2027 and mod.bac_exam_year(date(2026, 9, 1)) == 2027,
      (mod.bac_exam_year(date(2023, 5, 1)), mod.bac_exam_year(date(2026, 9, 1))))
check("l'ancien nom de constante a bien disparu (remplacé par le millésime de session)",
      not hasattr(mod, "BAC_FOLDER_MIN_YEAR"))
check("sans date précisée, le module prend la date du jour",
      mod.bac_folder_name() == "bac%d" % mod.bac_exam_year(), mod.bac_folder_name())
check("bac_exam_year est cohérent avec bac_folder_name",
      mod.bac_exam_year(date(2026, 9, 22)) == 2027 and mod.bac_folder_name(date(2026, 9, 22)) == "bac2027",
      (mod.bac_exam_year(date(2026, 9, 22)), mod.bac_folder_name(date(2026, 9, 22))))

# ── 2. L'ordre des candidats ────────────────────────────────────────────────
roots = mod.working_dir_roots()
check("C:\\ reste le premier choix du professeur" if os.name == "nt" else "hors Windows, pas de C:\\",
      (roots[0] == "C:\\" if os.name == "nt" else "C:\\" not in roots), str(roots))
check("le profil de l'élève vient en repli",
      os.path.expanduser("~") in roots, str(roots))
check("toutes les racines proposées existent", all(os.path.isdir(r) for r in roots), str(roots))

cands = mod.working_dir_candidates("bac2030", roots=[ROOT, ROOT, sandbox("x")])
check("les doublons de candidats sont éliminés",
      len(cands) == len(set(cands)) and len(cands) == 2, str(cands))
check("chaque candidat porte le nom de l'année",
      all(os.path.basename(c) == "bac2030" for c in cands), str(cands))
nom_du_jour = mod.working_dir_candidates(roots=[ROOT])[0]
check("sans nom imposé, le candidat porte le millésime de la session visée",
      os.path.basename(nom_du_jour) == mod.bac_folder_name()
      and os.path.basename(nom_du_jour).startswith("bac20"), nom_du_jour)
check("et pour aujourd'hui ce dossier est bien « bac2027 »",
      os.path.basename(nom_du_jour) == "bac2027" or date.today().month <= 6, nom_du_jour)

# ── 3. prepare_dir : créer, réutiliser, refuser ─────────────────────────────
fresh = sandbox("bac2031")
check("dossier absent : il est créé et retourné",
      mod.prepare_dir(fresh) == fresh and os.path.isdir(fresh), fresh)
check("dossier déjà présent : réutilisé sans erreur",
      mod.prepare_dir(fresh) == fresh, mod.prepare_dir(fresh))

blocked_root = sandbox("bloque")
os.makedirs(blocked_root)
with open(sandbox("bloque", "bac2032"), "w") as fp:      # un FICHIER porte ce nom
    fp.write("pas un dossier")
check("nom déjà pris par un fichier : refusé, pas de casse",
      mod.prepare_dir(sandbox("bloque", "bac2032")) is None)

under_file = sandbox("bloque", "bac2032", "sous")
check("chemin sous un fichier : refusé, pas de casse",
      mod.prepare_dir(under_file) is None)

# ── 4. choose_working_dir : le C:\ protégé de la salle ─────────────────────
primary = sandbox("racine_protegee")
secondary = sandbox("profil_eleve")
os.makedirs(primary)
with open(sandbox("racine_protegee", "bac2099"), "w") as fp:   # premier candidat injoignable
    fp.write("")
use_roots(primary, secondary)
choisi = mod.choose_working_dir("bac2099")
check("premier candidat refusé : on bascule sur le repli",
      choisi == os.path.join(secondary, "bac2099") and os.path.isdir(choisi), choisi)

blocked_again = sandbox("racine_fichier")          # un fichier comme racine : rien n'y est créable
with open(blocked_again, "w") as fp:
    fp.write("")
use_roots(primary, blocked_again)
check("tous les candidats refusés : None, et aucune exception",
      mod.choose_working_dir("bac2099") is None)
unpatch()


# le scénario réel d'une salle : makedirs sur C:\ lève PermissionError
def boom_makedirs(*a, **kw):
    raise PermissionError(13, "Permission denied")


real_makedirs = os.makedirs
os.makedirs = boom_makedirs
try:
    crashed = None
    result = mod.choose_working_dir()
except Exception as e:
    crashed = e
os.makedirs = real_makedirs
check("disque interdit à l'écriture : choose_working_dir ne lève pas",
      crashed is None and result is None, crashed or repr(result))

# Contre-factuel : l'ancien bloc, rejoué à l'identique sur le même poste.
# "C:\bac2026" existe déjà ici, donc makedirs n'y était jamais appelé : le
# plantage ne visait qu'une installation fraîche sur machine verrouillée, où le
# dossier de l'année reste à créer. On rejoue donc ce cas précis.
old_cwd = sandbox("racine_protegee", "bac2098")      # inexistant, disque refusé
check("le dossier du contre-factuel est bien inexistant", not os.path.exists(old_cwd))
os.makedirs = boom_makedirs
try:
    if not os.path.exists(old_cwd):
        os.makedirs(old_cwd)                         # l'ancienne ligne, telle quelle
    old_crashed = None
except Exception as e:
    old_crashed = e
os.makedirs = real_makedirs
check("l'ancien code levait sur ce disque (le correctif traite une vraie cause)",
      isinstance(old_crashed, PermissionError), old_crashed)

os.makedirs = boom_makedirs
new_result = mod.prepare_dir(old_cwd)
os.makedirs = real_makedirs
check("sur le même disque refusé, le nouveau code retourne None sans lever",
      new_result is None, new_result)

# ── 5. prepare_student_workspace : le workbench doit survivre ───────────────
use_roots(ROOT)
target = os.path.join(ROOT, mod.bac_folder_name())

wb = FakeWB()
out = mod.prepare_student_workspace(wb)
check("dossier retenu annoncé au workbench", wb.cwd_calls == [target] and out == target,
      str(wb.cwd_calls) + repr(out))
check("file.current_file vidé au type attendu par Thonny (None)",
      "file.current_file" in wb.options and wb.options["file.current_file"] is None, wb.options)
check("file.open_files vidé au type attendu par Thonny ([])",
      wb.options.get("file.open_files") == [], wb.options)
check("les deux options sont passées, pas une seule",
      set(wb.options) == {"file.current_file", "file.open_files"}, wb.options)

wb2 = FakeWB(cwd_error=OSError(22, "dossier invalide"))
try:
    crashed = None
    out2 = mod.prepare_student_workspace(wb2)
except Exception as e:
    crashed = e
check("set_local_cwd refuse : la séance est quand même nettoyée, aucune exception",
      crashed is None and set(wb2.options) == {"file.current_file", "file.open_files"},
      crashed or wb2.options)

wb3 = FakeWB(option_error=RuntimeError("option inconnue"))
try:
    crashed = None
    out3 = mod.prepare_student_workspace(wb3)
except Exception as e:
    crashed = e
check("set_option refuse : le dossier de travail est quand même appliqué",
      crashed is None and wb3.cwd_calls == [target], crashed or wb3.cwd_calls)

real_get_wb = mod.get_workbench
mod.get_workbench = lambda: (_ for _ in ()).throw(RuntimeError("pas de workbench"))
try:
    crashed = None
    out4 = mod.prepare_student_workspace()
except Exception as e:
    crashed = e
mod.get_workbench = real_get_wb
check("aucun workbench : le dossier est choisi, rien ne casse",
      crashed is None and out4 == target, crashed or repr(out4))

# ── 6. lecture réelle du fichier de configuration ───────────────────────────
# les valeurs écrites doivent être relues telles quelles par Thonny au
# démarrage suivant, sinon la séance précédente ressortirait quand même.
from thonny.config import ConfigurationManager

conf_path = sandbox("conf", "configuration.ini")
mgr = ConfigurationManager(conf_path)
mgr.set_default("file.current_file", None)
mgr.set_default("file.open_files", [])
mod._clear_last_session(mgr)
mgr.save()
mgr2 = ConfigurationManager(conf_path)
check("après redémarrage : current_file relu comme None",
      mgr2.get_option("file.current_file") is None, repr(mgr2.get_option("file.current_file")))
check("après redémarrage : open_files relu comme liste vide",
      mgr2.get_option("file.open_files") == [], repr(mgr2.get_option("file.open_files")))
check("le fichier écrit reste relisible par Thonny",
      "open_files" in open(conf_path, encoding="utf-8").read(),
      open(conf_path, encoding="utf-8").read())

# contre-factuel : l'ancienne valeur «  ""  » pour une option de type liste
mgr3 = ConfigurationManager(sandbox("conf", "ancienne.ini"))
mgr3.set_default("file.open_files", [])
mgr3.set_option("file.open_files", "")
check("l'ancienne chaîne vide reste tolérée par Thonny (bug visible, pas de crash)",
      mgr3.get_option("file.open_files") == "", repr(mgr3.get_option("file.open_files")))

# ── 7. load_plugin() ne contient plus d'appel dangereux en clair ────────────
source = open(mod.__file__, encoding="utf-8").read()
tree = ast.parse(source)
load_plugin = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_plugin")
called = set()
for node in ast.walk(load_plugin):
    if isinstance(node, ast.Call):
        f = node.func
        called.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
check("load_plugin ne crée plus de dossier lui-même",
      "makedirs" not in called and "mkdir" not in called, sorted(called))
check("load_plugin ne touche plus les options de session lui-même",
      "set_option" not in called, sorted(called))
check("load_plugin délègue le démarrage à prepare_student_workspace",
      "prepare_student_workspace" in called, sorted(called))

helpers = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
for name in ("bac_folder_name", "working_dir_roots", "working_dir_candidates",
             "prepare_dir", "choose_working_dir", "_clear_last_session",
             "prepare_student_workspace"):
    check("helper de niveau module disponible : " + name, name in helpers)

check("les helpers sont définis avant load_plugin (lisibilité de l'appel)",
      helpers.index("prepare_student_workspace") < helpers.index("load_plugin"), helpers)

lp_src = ast.get_source_segment(source, load_plugin)
check("load_plugin ne contient plus de chemin « bac » en dur",
      lp_src is not None and "makedirs" not in lp_src and "bac20" not in lp_src,
      [l for l in (lp_src or "").splitlines() if "makedirs" in l or "bac20" in l])
check("load_plugin n'écrit plus les options de session en direct",
      "set_option" not in lp_src,
      [l for l in lp_src.splitlines() if "set_option" in l])
check("le bloc « Ne pas ouvrir les derniers fichiers » a quitté load_plugin",
      "derniers fichiers" not in lp_src, lp_src[-260:])

# ── 8. le module reste importable, sans effet de bord sur le disque ─────────
unpatch()
listing_before = set(os.listdir(ROOT))
try:
    importlib.reload(mod)
    reloaded = True
except Exception as e:
    reloaded = e
check("rechargement du module : sans exception", reloaded is True, reloaded)
check("l'import du module ne crée aucun dossier de travail",
      set(os.listdir(ROOT)) == listing_before,
      sorted(set(os.listdir(ROOT)) ^ listing_before))
check("les helpers survivent au rechargement",
      all(hasattr(mod, n) for n in ("prepare_student_workspace", "choose_working_dir",
                                    "bac_folder_name", "_clear_last_session")))

shutil.rmtree(ROOT, ignore_errors=True)

fails = [r for r in results if not r[1]]
print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
for label, ok in fails:
    print("  echec : " + label)
sys.exit(1 if fails else 0)
