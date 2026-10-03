import os
import subprocess
import sys
from datetime import date
from tkinter import messagebox
from thonny import get_workbench
from thonny.ui_utils import select_sequence,askopenfilename
from .UIViewer import UiViewerPlugin, own_line

from xml.dom import minidom

# Aucun global « fichier en cours » ici, et c'est voulu (item 9). La vue du
# concepteur connait le fichier qu'elle affiche : c'est son attribut `ui_file`,
# qu'elle met a jour elle-meme a chaque ouverture, enregistrement et « Nouveau ».
# Le module en tenait une copie que seule « Ajouter Annexe + interface »
# remplissait, et « Ouvrir dans Designer » lisait cette copie : mesuree, la
# commande envoyait designer.exe editer un autre fichier que celui de l'ecran
# dans quatre gestes sur cinq. Une seule autorite, plus de copie a rater.

# Modèle de code pour les élèves qui travaillent sans fichier .ui
# Un seul geste à montrer, trois blancs à remplacer : Nom_Interface.ui, Nom_Bouton
# et Nom_Module. La ligne de branchement reste dans le squelette : c'est elle qui
# montre le geste (un bouton, un clic, une fonction à appeler). Le gestionnaire que
# l'item 2 y avait ajouté — def Nom_Module, son commentaire « À compléter », pass —
# est retiré sur décision du 2026-10-02 : l'élève écrit la fonction lui-même, et le
# nom qu'il lui donne devient le troisième blanc. Collé tel quel, ce texte s'arrête
# donc à la ligne connect sur « NameError: name 'Nom_Module' is not defined » :
# c'est l'erreur qui nomme le blanc oublié, et elle disparaît dès que l'élève écrit
# sa fonction (ou remplace Nom_Module par le nom qu'il a choisi).
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
                filetypes=[("Fichiers UI", "*.ui"), ("Tous les fichiers", "*.*")],
                parent=get_workbench()
            )
    if path:
        vue = get_workbench().get_view("UiViewerPlugin")
        # On demande d'abord a la vue, et seulement ensuite on touche au menu.
        # load_new_ui_file peut rendre False pour deux raisons : le fichier n'est
        # pas une fenetre (le lecteur l'a refuse), ou l'eleve a repondu « non » a
        # la question qui protege son travail affiche. Dans les deux cas la vue
        # n'a rien ouvert, donc le menu des commandes et l'aide en ligne doivent
        # rester ceux du fichier precedent : annoncer des
        # « windows.bouton.clicked.connect(...) » pour une interface que le
        # concepteur n'a pas ouverte est le piege que cette ligne fermait.
        # Rien n'est note ailleurs non plus : « Ouvrir dans Designer » relit le
        # fichier a la vue, qui n'a pas change (item 9).
        if not vue.load_new_ui_file(path):
            return
        _clear_dynamic_menu_items()
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
                
            

        # askopenfilename rend des antislashes sous Windows ; collés tels quels
        # dans une chaîne Python ils deviendraient des séquences d'échappement
        # (\U de \Users, \t de \tunisiaschools) et loadUi("...") ne serait plus
        # du Python valide. Les bars obliques sont acceptées par Qt.
        path = path.replace("\\", "/")
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
    if exe is None:
        reponse = _proposer_installation_designer()
        if reponse is None:
            # l'installation a été tentée et a échoué : l'enseignant l'a déjà lu
            return False
        if reponse:
            # designer.exe est posé à côté des DLLs Qt du paquet : ni redémarrage
            # de Thonny ni nouvelle commande n'est nécessaire, il s'ouvre dès ici.
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

# Le module PyPI qui fournit Qt Designer à cette distribution. Il ne pèse qu'≈1
# Mo parce qu'il ne contient que trois fichiers (designer.exe,
# Qt5DesignerComponents.dll et un qt.conf « prefix = ../ ») qu'il pose dans le
# dossier des DLLs Qt déjà installées ; il apporte justement le
# Qt5DesignerComponents.dll que le paquet PyQt5-Qt5 ne livre pas. Les modules
# annoncés auparavant (pyqt5-designer, PyQt5Designer) embarquent un Qt complet :
# même besogne, ≈100 Mo retéléchargés et un second Designer qui ne correspond
# pas au Qt de l'élève.
PAQUET_DESIGNER = "pyqt5-qt5-designer"


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


def _sites_de_pip():
    """Les dossiers où pip peut déposer un paquet sans toucher à celui de Thonny.

    « Gérer les paquets... » installe avec --user (site utilisateur), « Gérer les
    plug-ins... » avec PYTHONUSERBASE sur le dossier des extensions de Thonny.
    Ces chemins ne rejoignent sys.path qu'au redémarrage : ils sont donc ajoutés
    ici plutôt qu'abandonnés à la seule lecture de sys.path.
    """
    sites = []
    try:
        import site
        sites.append(site.getusersitepackages())
    except Exception:
        pass
    user_dir = _thonny_user_dir()
    if user_dir:
        sites.append(os.path.join(user_dir, "plugins",
                                  "Python%d%d" % sys.version_info[:2],
                                  "site-packages"))
    return [s for s in sites if s and os.path.isabs(s)]


def _designer_des_autres_sites():
    """Les designer.exe déposés par pip à côté d'un PyQt5 qui n'est pas celui de Thonny.

    Dans ces arborescences le binaire se retrouve seul, sans les DLLs Qt : il
    reste utilisable parce que _qt_designer_environ lui prête le Qt de Thonny.
    Le premier choix — le Qt du paquet — demeure meilleur, ces chemins ne viennent
    donc qu'ensuite.

    Seuls les chemins absolus sont retenus : '' (le dossier où travaille l'élève)
    pourrait contenir un designer.exe égaré.
    """
    trouvés = []
    for entree in list(sys.path) + _sites_de_pip():
        if not entree or not os.path.isabs(entree):
            continue
        for orthographe in ("Qt5", "Qt"):
            binaire = os.path.join(entree, "PyQt5", orthographe, "bin", "designer.exe")
            if os.path.isfile(binaire):
                trouvés.append(os.path.normpath(binaire))
    return trouvés


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
    candidates += _designer_des_autres_sites()
    candidates += [
        r"C:\Program Files\Qt Designer\designer.exe",
        r"C:\Program Files (x86)\Qt Designer\designer.exe",
        "pyqt5_qt5_designer.exe",   # le lanceur que pip crée dans Scripts\
        "designer.exe",             # n'importe quel Designer du PATH
    ]
    retenus = []
    for candidate in candidates:
        if candidate and candidate not in retenus:
            retenus.append(candidate)
    return retenus


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


def _vue_concepteur():
    """La vue du concepteur, seulement si elle existe deja.

    `create=False` n'est pas une precauition de style : `get_view` construit le
    widget et l'installe dans un onglet quand il n'existe pas encore. Demander
    « quel fichier affichez-vous ? » n'a pas le droit d'ouvrir l'onglet de
    l'eleve, encore moins de creer une vue vierge pour lui repondre « rien ».
    Une vue jamais ouverte n'affiche aucun fichier, et c'est la bonne reponse.
    """
    try:
        workbench = get_workbench()
        if workbench is None:
            return None
        return workbench.get_view("UiViewerPlugin", create=False)
    except Exception:
        # hors de Thonny (suite sans workbench), vue non enregistree, workbench
        # sans get_view : la reponse est « aucun fichier a l'ecran », pas une
        # exception qui empecherait Designer de s'ouvrir.
        return None


def _current_ui_path():
    """Le fichier .ui que le concepteur a a l'ecran, en absolu, s'il existe encore.

    C'est la vue qui le decide, pas une copie que le module tiendrait :
    `ui_file` est remis a jour par les trois gestes que le module ne voit pas
    passer — « Ouvrir » dans le panneau, « Enregistrer » sous un nom neuf,
    « Nouveau ». Mesure avant ce changement (tests\\_sortie\\probe\\mesure9.py) :
    « Ouvrir dans Designer » envoyait designer.exe editer un fichier autre que
    celui de l'ecran dans quatre gestes sur cinq, et le plus triste n'etait pas
    le fichier en trop (un .ui que l'eleve ne regardait pas) mais le fichier
    manquant : apres un « Ouvrir » depuis la vue, Designer se lancait vide, et
    l'eleve croyait que son interface n'existait pas.

    Un document jamais enregistre n'a pas de fichier : designer.exe recoit alors
    « rien » et s'ouvre sur une forme neuve, comme avant.
    """
    path = getattr(_vue_concepteur(), "ui_file", None) or ""
    if path and os.path.isfile(path):
        return os.path.abspath(path)
    return ""


def _qt_plugins_dir():
    """Répertoire des plugins Qt (plateformes, styles…) livré avec PyQt5."""
    try:
        from PyQt5.QtCore import QLibraryInfo
        return QLibraryInfo.location(QLibraryInfo.PluginsPath)
    except Exception:
        binaries = _qt_binaries_dir()
        if not binaries:
            return None
        return os.path.normpath(os.path.join(binaries, os.pardir, "plugins"))


def _qt_designer_environ(exe=""):
    """Environnement prêté à designer.exe : les DLLs Qt et les plugins Qt.

    Le paquet range trois fichiers seulement, à côté du PyQt5 visé par pip.
    Quand ce n'est pas celui de Thonny (installation avec --user), le binaire se
    retrouve seul : sans le dossier des DLLs Qt dans PATH il meurt d'un
    « Qt5Core.dll introuvable » (0xC0000135), et son qt.conf « prefix = ../ »
    cherche des plugins qui n'existent pas à ce niveau — il part alors afficher
    la boîte Qt « could not find or load the Qt platform plugin windows » au lieu
    d'ouvrir la fenêtre de l'élève. Ces mesures viennent du binaire du paquet,
    lancé dans l'arborescence exacte que --user produit.

    Le cas normal (le paquet installé dans le Qt de Thonny) passe par la même
    fonction sans rien changer : les chemins prêtés sont ceux qui entourent déjà
    l'exécutable.
    """
    env = os.environ.copy()
    binaries = _qt_binaries_dir()
    if not binaries:
        return env
    env["PATH"] = os.pathsep.join([p for p in (binaries, env.get("PATH", "")) if p])
    plugins = _qt_plugins_dir()
    if plugins and os.path.isdir(plugins):
        env["QT_PLUGIN_PATH"] = plugins
        plateformes = os.path.join(plugins, "platforms")
        if os.path.isdir(plateformes):
            env["QT_QPA_PLATFORM_PLUGIN_PATH"] = plateformes
    return env


def _run_designer(exe, ui_path=""):
    args = [exe] + ([ui_path] if ui_path else [])
    return subprocess.Popen(args, env=_qt_designer_environ(exe))


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


def _commande_pip_designer(interprete=None, paquet=PAQUET_DESIGNER):
    """La commande qui installe le Designer de la distribution.

    Volontairement sans --user : le paquet doit se ranger dans le PyQt5 de Thonny,
    là où sont déjà les DLLs Qt. C'est ce qui rend l'installation utilisable dans
    la seconde qui suit, sans prêt d'environnement et sans redémarrage — un
    --user créerait un second PyQt5 que sys.path de la session ne connait pas
    encore.
    """
    return [interprete or sys.executable, "-m", "pip", "install",
            "--disable-pip-version-check", "--progress-bar", "off", paquet]


def _raison_echec_installation(sortie):
    """Ce que l'enseignant doit retenir de la réponse de pip, en français."""
    bas = (sortie or "").lower()
    if ("no matching distribution" in bas or "could not find a version" in bas
            or "max retries" in bas or "timed out" in bas
            or "connection" in bas or "network" in bas or "resolve" in bas):
        return ("PyPI est injoignable : ce poste semble hors ligne.\n\n"
                "En salle, l'installation se fait par la distribution ThonnyTN "
                "(le module y est déjà), sinon indiquez un designer.exe existant "
                "avec la commande « Configurer Designer » du menu PyQt5.")
    if ("permission" in bas or "access is denied" in bas or "winerror 5" in bas
            or "read-only" in bas or "readonly" in bas):
        return ("Thonny n'a pas le droit d'écrire dans son propre dossier "
                "(installation sous « Program Files » ?).\n\n"
                "Refaites l'installation en tant qu'administrateur, ou indiquez "
                "un designer.exe existant avec « Configurer Designer ».")
    return "L'installation n'a pas abouti."


def _installer_designer():
    """Lance pip et en rend compte. Retourne True seulement si pip a réussi.

    L'appel reste synchrone : le paquet ne pèse qu'≈ 1 Mo, l'écran se fige le
    temps de l'échange. Un timeout garde néanmoins la main à l'enseignant dont la
    liaison pend au lieu de bloquer Thonny indéfiniment.
    """
    try:
        resultat = subprocess.run(_commande_pip_designer(), capture_output=True,
                                  text=True, timeout=900)
        code = resultat.returncode
        sortie = (resultat.stdout or "") + (resultat.stderr or "")
    except Exception as e:
        code, sortie = -1, "%s : %s" % (type(e).__name__, e)
    if code == 0:
        return True
    messagebox.showerror(
        "Qt Designer",
        _raison_echec_installation(sortie)
        + "\n\n--- pip ---\n" + (sortie or "(aucune sortie)").strip()[-700:],
        parent=get_workbench(),
    )
    return False


def _proposer_installation_designer():
    """Propose l'installation d'un clic.

    Retourne True quand Designer est prêt, False quand l'enseignant refuse (on
    peut encore lui faire chercher le binaire à la main), None quand une
    installation a été tentée et n'a pas abouti : la raison est déjà affichée,
    une troisième boîte n'apprendrait rien.
    """
    if not messagebox.askyesno(
        "Qt Designer",
        "Qt Designer n'est pas installé sur ce poste.\n\n"
        "L'installer maintenant ? Le module %s ne pèse qu'≈ 1 Mo : il dépose "
        "designer.exe à côté des DLLs Qt déjà présentes, sans re-télécharger Qt.\n\n"
        "Une connexion Internet est nécessaire et Thonny patiente le temps de "
        "l'échange." % PAQUET_DESIGNER,
        parent=get_workbench(),
    ):
        return False
    if not _installer_designer():
        return None
    if find_designer() is None:
        messagebox.showerror(
            "Qt Designer",
            "pip a terminé mais designer.exe reste introuvable.\n\n"
            "Indiquez son emplacement avec la commande « Configurer Designer » "
            "du menu PyQt5.",
            parent=get_workbench(),
        )
        return None
    return True


def _report_no_designer():
    messagebox.showerror(
        "Qt Designer",
        "Qt Designer n'est pas installé sur ce poste.\n\n"
        "Il est fourni par le module %s, qui ne pèse qu'≈ 1 Mo parce qu'il "
        "range designer.exe dans le dossier des DLLs Qt déjà installées :\n"
        "    pip install %s\n\n"
        "Sans ligne de commande : menu Outils → « Gérer les paquets... », taper "
        "%s, puis Installer.\n\n"
        "Sinon, indiquez son emplacement avec la commande « Configurer Designer » "
        "du menu PyQt5." % (PAQUET_DESIGNER, PAQUET_DESIGNER, PAQUET_DESIGNER),
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
    get_workbench().add_view(UiViewerPlugin, "QT UI Viewer", "s")
    
    
    image_path = os.path.join(os.path.dirname(__file__), "res", "qt_16.png")
    designer_image_path = os.path.join(os.path.dirname(__file__), "res", "designer_16.png")

    # group=1 place cette commande tout en haut du menu, avant les commandes par défaut (group=99)
    get_workbench().add_command(
        "pyqt5_add_template",
        "PyQt5",
        "Ajouter Annexe",
        add_pyqt_template_code,
        group=1,
        include_in_toolbar = False,
        caption  = "PyQt",
        image = image_path
    )
    get_workbench().add_command(
        "selmen_command",
        "PyQt5",
        "Ajouter Annexe + interface",
        add_pyqt_code,
	    default_sequence=select_sequence("<Control-Shift-B>", "<Command-Shift-B>"),
        include_in_toolbar = True,
	    caption  = "PyQt",
        image = image_path
    )
    get_workbench().add_command(
        "pyqt5_open_in_designer",
        "PyQt5",
        "Ouvrir dans Designer",
        open_in_designer,
	    #default_sequence=select_sequence("<Control-Shift-B>", "<Command-Shift-B>"),
        include_in_toolbar = True,
	    caption  = "PyQt",
        image = designer_image_path
    )
    get_workbench().add_command(
        "pyqt5_configure_designer",
        "PyQt5",
        "Configurer Designer",
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

