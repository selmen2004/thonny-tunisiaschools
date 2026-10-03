import os
import subprocess
from datetime import date
from tkinter import messagebox
from thonny import get_workbench
from thonny.languages import tr
from thonny.ui_utils import select_sequence,askopenfilename
from .UIViewer import UiViewerPlugin, own_line

from xml.dom import minidom
global qt_ui_file
qt_ui_file =""

# Modèle de code pour les élèves qui travaillent sans fichier .ui
PYQT5_TEMPLATE_CODE = (
    "from PyQt5.uic import loadUi\n"
    "from PyQt5.QtWidgets import QApplication\n"
    "\n"
    "\n"
    "\n"
    "app = QApplication([])\n"
    'windows = loadUi ("Nom_Interface.ui")\n'
    "windows.show()\n"
    "windows.Nom_Bouton.clicked.connect (Nom_Module)\n"
    "app.exec_()\n"
)

# Libellés des commandes ajoutées au menu pour les widgets du fichier UI courant
_dynamic_menu_labels = []


def _clear_dynamic_menu_items():
    """Retire les commandes des widgets du fichier UI précédent.
    N'efface que les entrées ajoutées par usefull_commands, jamais les
    commandes permanentes du menu."""
    menu = get_workbench().get_menu("PyQt5")
    for label in reversed(_dynamic_menu_labels):
        try:
            menu.delete(menu.index(label))
        except Exception:
            pass
    del _dynamic_menu_labels[:]


def _insert_in_editor(code, position="insert"):
    """Insère du code dans l'éditeur courant, en ouvrant un fichier neuf au besoin.

    Sans onglet ouvert, get_current_editor() renvoie None : l'ancien code
    enchaînait directement .get_code_view().text et levait un AttributeError
    que Thonny affichait comme une erreur interne, sans rapport avec PyQt5.
    Retourne True si le texte a bien été inséré.
    """
    try:
        notebook = get_workbench().get_editor_notebook()
        editor = notebook.get_current_editor()
        if editor is None:
            notebook.open_new_file()      # aucun onglet : on crée le document
            editor = notebook.get_current_editor()
        code_view = editor.get_code_view() if editor is not None else None
    except Exception:
        code_view = None

    if code_view is None:
        messagebox.showerror(
            "PyQt5",
            "Impossible d'écrire dans l'éditeur de code.\n"
            "Créez un fichier (Fichier > Nouveau) et réessayez.",
            parent=get_workbench(),
        )
        return False

    if position == "insert":
        # une ligne colle(e) en fin de ligne se souderait a celle du curseur
        code = own_line(code_view.text, code)
    code_view.text.insert(position, code)
    code_view.text.see(position)
    editor.focus_set()
    return True


def add_pyqt_template_code():
    """Insère le modèle de code PyQt5 sans demander de fichier UI."""
    return _insert_in_editor(PYQT5_TEMPLATE_CODE)


def usefull_commands(w):
    # Les commandes insèrent du code que l'élève lance tel quel : setText()
    # sans argument lève un TypeError et un .text() seul évalue puis jette le
    # résultat. Chaque entrée porte donc un exemple complet et exécutable.
    name = w.attributes['name'].value

    def add_cmd(id, label, code):
        menu_label = label + name
        get_workbench()._publish_command(
                    "pyqt_text_" + name + id,
                    "PyQt5",
                    menu_label ,
                    lambda: _insert_in_editor(code)
                )
        if menu_label not in _dynamic_menu_labels:
            _dynamic_menu_labels.append(menu_label)
    add_cmd("text", "Contenu de ", f'saisie = windows.{name}.text()')
    add_cmd("settext", "Changer le contenu de ",
            f'windows.{name}.setText("Nouveau texte")')
    add_cmd("clear", "Effacer le contenu de ", f"windows.{name}.clear()")
    add_cmd("show", "Afficher ", f"windows.{name}.show()")

    
    
def add_pyqt_code():
    
    btnstxt = ""
    mytxt = ""
    path = askopenfilename(
                filetypes=[("Fichiers UI", "*.ui"), (tr("Tous les fichiers"), "*.*")],
                parent=get_workbench()
            )
    if path:
        global qt_ui_file
        qt_ui_file = path
        _clear_dynamic_menu_items()
        get_workbench().get_view("UiViewerPlugin").load_new_ui_file(path)
        get_workbench().show_view("UiViewerPlugin",True)
        file = minidom.parse(path)
        widgets = file.getElementsByTagName('widget')
        for w in widgets:
            if w.attributes['class'].value == "QPushButton" : #Bouton
                btnstxt = btnstxt + "windows."+w.attributes['name'].value +".clicked.connect ( "+  w.attributes['name'].value +"_click )\n"
                mytxt = mytxt + "def "+  w.attributes['name'].value +"_click():\n    pass\n" 
            elif w.attributes['class'].value in [ "QLineEdit", "QLabel"] : #Zone de texte ou Libellé
                #btnstxt = btnstxt + "windows."+w.attributes['name'].value +".clicked.connect ( "+  w.attributes['name'].value +"_click )"+chr(13)+chr(10)
                usefull_commands(w)
                
            

        _insert_in_editor(
            'from PyQt5.uic import loadUi\n'+
            'from PyQt5.QtWidgets import QApplication\n'+
            '\n'+mytxt+'\n'+
            'app = QApplication([])\n'+
            'windows = loadUi ("'+ path +'")\n'+
            'windows.show()\n'+
            btnstxt+'\n'
            'app.exec_()',
            '1.0'   # le programme complet se lit depuis le début du fichier
        )


def open_in_designer():
    """Ouvre Qt Designer avec le fichier .ui courant.

    Retourne True seulement si Designer a vraiment été lancé.
    """
    exe = find_designer()
    if exe is None and _ask_for_designer():
        exe = find_designer()

    if exe is None:
        _report_no_designer()
        return False

    # un fichier de la session précédente peut avoir été déplacé ou supprimé
    ui_path = _current_ui_path()
    try:
        _run_designer(exe, ui_path)
    except OSError as e:
        messagebox.showerror(
            "Qt Designer",
            "Impossible de lancer Qt Designer :\n" + str(e)
            + "\n\n" + exe,
            parent=get_workbench(),
        )
        return False
    return True


# ── Découverte de Qt Designer ─────────────────────────────────────
# L'emplacement choisi par l'enseignant est mémorisé dans la configuration de
# Thonny (configuration.ini), clé DESIGNER_OPTION.
DESIGNER_OPTION = "pyqt5_designer.executable"


def _get_option(name):
    try:
        return get_workbench().get_option(name, "") or ""
    except Exception:
        return ""


def _set_option(name, value):
    try:
        get_workbench().set_option(name, value)
    except Exception:
        pass


def _qt_binaries_dir():
    """Répertoire des binaires Qt fourni par PyQt5, ou None."""
    try:
        from PyQt5.QtCore import QLibraryInfo
        return QLibraryInfo.location(QLibraryInfo.BinariesPath)
    except Exception:
        return None


def _thonny_user_dir():
    try:
        import thonny
        return getattr(thonny, "THONNY_USER_DIR", None)
    except Exception:
        return None


def _designer_candidates():
    """Emplacements possibles de Designer, du plus fiable au plus vague.

    Un nom sans chemin (ex. "designer.exe") est cherché dans le PATH.
    """
    candidates = [
        _get_option(DESIGNER_OPTION),                 # choix mémorisé
        os.environ.get("QT_DESIGNER_PATH", ""),        # contournement manuel
    ]
    binaries = _qt_binaries_dir()
    if binaries:
        candidates.append(os.path.normpath(os.path.join(binaries, "designer.exe")))
    user_dir = _thonny_user_dir()
    if user_dir:
        candidates.append(
            os.path.normpath(
                os.path.join(user_dir, "qt5_applications", "Qt", "bin", "designer.exe")
            )
        )
    candidates += [
        r"C:\Program Files\Qt Designer\designer.exe",
        r"C:\Program Files (x86)\Qt Designer\designer.exe",
        "pyqt5_qt5_designer.exe",   # bundle PyPI pyqt5-designer
        "designer.exe",             # n'importe quel Designer du PATH
    ]
    return [c for c in candidates if c]


def _which_in_path(name):
    """Cherche un programme dans PATH, volontairement sans le dossier courant.

    shutil.which() insère le répertoire courant sur Windows : un designer.exe
    égaré dans le dossier de l'élève (C:\\bac20XX) serait alors lancé.
    """
    exts = [""]
    if os.name == "nt":
        pathext = (os.environ.get("PATHEXT") or ".EXE").split(os.pathsep)
        exts += [e if e.startswith(".") else "." + e for e in pathext if e]
    for folder in (os.environ.get("PATH") or "").split(os.pathsep):
        folder = folder.strip('"')
        if not folder:
            continue
        for ext in exts:
            candidate = os.path.join(folder, name + ext)
            if os.path.isfile(candidate):
                return candidate
    return None


def _resolve_designer(candidate):
    """Chemin absolu du binaire, ou None si le candidat n'existe pas.

    Contrairement à l'ancien code, un nom de programme du PATH est vérifié par
    une vraie recherche : os.path.exists("designer.exe") ne le trouve jamais.
    """
    if not candidate:
        return None
    if os.path.dirname(candidate):
        return candidate if os.path.isfile(candidate) else None
    return _which_in_path(candidate)


def find_designer():
    """Premier executable Designer valide parmi les candidats."""
    for candidate in _designer_candidates():
        exe = _resolve_designer(candidate)
        if exe:
            return os.path.abspath(exe)
    return None


def _current_ui_path():
    """Le fichier .ui de la session, en chemin absolu, s'il existe encore."""
    if not qt_ui_file:
        return ""
    if os.path.isfile(qt_ui_file):
        return os.path.abspath(qt_ui_file)
    return ""


def _run_designer(exe, ui_path=""):
    args = [exe] + ([ui_path] if ui_path else [])
    return subprocess.Popen(args)


def _ask_for_designer(confirm=True):
    """Propose d'indiquer designer.exe une seule fois ; mémorise le choix.

    confirm=False quand l'appelant a déjà demandé l'accord de l'utilisateur.
    """
    if confirm and not messagebox.askyesno(
        "Qt Designer",
        "Qt Designer n'a pas été trouvé automatiquement.\n\n"
        "Voulez-vous indiquer l'emplacement de designer.exe ?",
        parent=get_workbench(),
    ):
        return False
    path = askopenfilename(
        title="Choisir Qt Designer",
        initialdir="C:\\",
        filetypes=[("Fichiers exécutables", "*.exe"),
                   ("Tous les fichiers", "*.*")],
        parent=get_workbench(),
    )
    exe = _resolve_designer(path)
    if exe is not None and "designer" not in os.path.basename(exe).lower():
        exe = None    # un autre executable ouvrirait n'importe quoi en silence
    if exe is None:
        if path:
            messagebox.showerror(
                "Qt Designer",
                "Ce fichier n'est pas Qt Designer\n"
                "(son nom doit contenir « designer »).",
                parent=get_workbench(),
            )
        return False
    _set_option(DESIGNER_OPTION, os.path.abspath(exe))
    return True


def _report_no_designer():
    messagebox.showerror(
        "Qt Designer",
        "Qt Designer n'est pas installé sur ce poste.\n\n"
        "Il est fourni par le module pyqt5-designer :\n"
        "    pip install pyqt5-designer\n\n"
        "Sinon, indiquez son emplacement avec la commande « Configurer Designer » "
        "du menu PyQt5.",
        parent=get_workbench(),
    )


def configure_designer():
    """Commande de menu : choisir manuellement le binaire de Designer."""
    detected = find_designer()
    if detected and not messagebox.askyesno(
        "Qt Designer",
        "Designer détecté :\n" + detected + "\n\nEn choisir un autre ?",
        parent=get_workbench(),
    ):
        return False
    # l'option existante n'est remplacée que si le nouveau choix est valide
    if _ask_for_designer(confirm=False):
        _report_designer_saved()
        return True
    return False


def _report_designer_saved():
    chosen = find_designer() or ""
    messagebox.showinfo("Qt Designer", "Designer enregistré :\n" + chosen,
                        parent=get_workbench())


# ── Dossier de travail de l'élève ───────────────────────────────────────────
# Ces fonctions sont séparées de load_plugin() pour deux raisons : elles
# s'observent sans workbench réel (donc se testent), et elles doivent encaisser
# un refus du disque. load_plugin() est appelée HORS du try/except qui protège
# l'import des modules (thonny/workbench.py:413-419 puis :426) : une exception
# qui en sort remonte jusqu'à Workbench() et n'offre à l'élève qu'une fenêtre
# « Internal error » sans Thonny ouvert (thonny/__init__.py:281-298). La racine
# C:\ est justement protégée en écriture sur beaucoup de postes de salle.

# Session visée par cette distribution : la rentrée 2026-2027 prépare le bac 2027.
# Avancer ce réglage à chaque rentrée (septembre).
BAC_MIN_SESSION_YEAR = 2027
BAC_EXAM_MONTH = 6          # les épreuves de juin : c'est le millésime de la session


def bac_exam_year(today=None):
    """Millésime du bac visé : l'année des PROCHAINES épreuves, pas l'année civile.

    L'année scolaire court de septembre à juin : en septembre 2026 les candidats
    planchent en juin 2027 et leur travail doit être rangé dans « bac2027 ».
    Janvier à juin appartiennent encore à la session de l'année en cours,
    juillet à décembre ouvrent la suivante.
    """
    jour = today or date.today()
    annee = jour.year + (1 if jour.month > BAC_EXAM_MONTH else 0)
    # Un poste dont l'horloge est repartie en arrière (pile de CMOS à plat, retour
    # d'usine) retomberait sur une session passée : on la remonte à la session en
    # cours, celle où l'élève travaille réellement.
    return max(annee, BAC_MIN_SESSION_YEAR)


def bac_folder_name(today=None):
    """Nom du dossier de travail : « bac2027 » pour la classe qui passe en juin 2027."""
    return "bac%d" % bac_exam_year(today)


def working_dir_roots():
    """Racines cherchées, par ordre de préférence.

    C:\\ d'abord : c'est l'endroit que le professeur connaît. Le profil de
    l'élève ensuite, seul repli garanti accessible sans droits
    d'administration.
    """
    roots = []
    if os.name == "nt":
        roots.append("C:\\")
    home = os.path.expanduser("~")
    if home and home != "~" and os.path.isdir(home):
        roots.append(home)
    return roots


def working_dir_candidates(folder=None, roots=None):
    """Chemins candidats, par ordre de préférence et sans doublon."""
    name = folder or bac_folder_name()
    seen = set()
    paths = []
    for root in working_dir_roots() if roots is None else roots:
        path = os.path.join(root, name)
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def prepare_dir(path):
    """Retourne le dossier, créé au besoin ; None s'il n'est pas utilisable.

    os.makedirs refuse une racine protégée, un fichier déjà présent à ce nom
    ou un disque plein : on passe alors au candidat suivant au lieu de
    propager l'exception jusqu'au démarrage de Thonny.
    """
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        return None
    return path if os.path.isdir(path) else None


def choose_working_dir(folder=None):
    """Premier dossier de travail réellement créable, ou None."""
    for candidate in working_dir_candidates(folder):
        ready = prepare_dir(candidate)
        if ready:
            return ready
    return None


def _clear_last_session(wb):
    """« Ne pas ouvrir les derniers fichiers ».

    Les valeurs vides sont écrites aux types que Thonny attend pour ces
    options — None et [] (thonny/editors.py:611-612) — plutôt qu'une chaîne
    vide que get_option ne reconnaît que par tolérance.
    """
    for name, empty in (("file.current_file", None), ("file.open_files", [])):
        try:
            wb.set_option(name, empty)
        except Exception:
            pass


def prepare_student_workspace(wb=None):
    """Range l'élève dans « bac<session> » et vide la session précédente.

    Ne lève jamais : retourne le dossier retenu, ou None quand aucun candidat
    n'est créable — Thonny garde alors son répertoire courant et démarre
    normalement.
    """
    if wb is None:
        try:
            wb = get_workbench()
        except Exception:
            wb = None

    try:
        folder = choose_working_dir()
    except Exception:
        folder = None

    if wb is None:
        return folder

    if folder:
        try:
            wb.set_local_cwd(folder)
        except Exception:
            pass
    _clear_last_session(wb)
    return folder


def load_plugin():
    get_workbench().add_view(UiViewerPlugin, tr("QT UI Viewer"), "s")
    
    
    image_path = os.path.join(os.path.dirname(__file__), "res", "qt_16.png")
    designer_image_path = os.path.join(os.path.dirname(__file__), "res", "designer_16.png")

    # group=1 place cette commande tout en haut du menu, avant les commandes par défaut (group=99)
    get_workbench().add_command(
        "pyqt5_add_template",
        "PyQt5",
        tr("Ajouter Annexe"),
        add_pyqt_template_code,
        group=1,
        include_in_toolbar = False,
        caption  = "PyQt",
        image = image_path
    )
    get_workbench().add_command(
        "selmen_command",
        "PyQt5",
        tr("Ajouter Annexe + interface"),
        add_pyqt_code,
	    default_sequence=select_sequence("<Control-Shift-B>", "<Command-Shift-B>"),
        include_in_toolbar = True,
	    caption  = "PyQt",
        image = image_path
    )
    get_workbench().add_command(
        "pyqt5_open_in_designer",
        "PyQt5",
        tr("Ouvrir dans Designer"),
        open_in_designer,
	    #default_sequence=select_sequence("<Control-Shift-B>", "<Command-Shift-B>"),
        include_in_toolbar = True,
	    caption  = "PyQt",
        image = designer_image_path
    )
    get_workbench().add_command(
        "pyqt5_configure_designer",
        "PyQt5",
        tr("Configurer Designer"),
        configure_designer,
        group=99,
        include_in_toolbar = False,
	    caption  = "PyQt",
    )
    # Changement de dossier de sauvegarde, puis pas de restauration des
    # fichiers de la séance précédente. Les deux sont dans
    # prepare_student_workspace() pour que ni un C:\ protégé ni un workbench
    # absent n'empêchent Thonny de démarrer.
    prepare_student_workspace()

