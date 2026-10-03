import os
import copy
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from xml.etree import ElementTree as ET
from thonny import get_workbench
from thonny.languages import tr

# ── Palette Qt Fusion ────────────────────────────────────────
QT_BG         = "#f0f0f0"
QT_BTN        = "#e1e1e1"
QT_BTN_BD     = "#adadad"
QT_ENTRY_BG   = "#ffffff"
QT_ENTRY_BD   = "#b0b0b0"
QT_FG         = "#000000"
QT_SEL        = "#0078d7"
QT_SEL_TXT    = "#ffffff"

# ── Palette IDE sombre ───────────────────────────────────────
PANEL_HDR   = "#1e1e1e"
PANEL_BG    = "#2b2b2b"
PANEL_FG    = "#cccccc"
TB_BG       = "#252526"
TB_BTN      = "#3c3c3c"
TB_BTN_H    = "#505050"
PROP_BG     = "#252526"
PROP_EVEN   = "#2d2d2d"
PROP_ODD    = "#282828"
PROP_FG     = "#d4d4d4"
PROP_FG2    = "#888888"
ACCENT      = "#0078d7"
SEP_COL     = "#3f3f3f"

# ── Catalogue widgets lycée tunisien ────────────────────────
WIDGET_DEFS = [
    ("QLabel",       "Label",       "T",   "Etiquette de texte"),
    ("QPushButton",  "PushButton",  "OK",  "Bouton cliquable"),
    ("QLineEdit",    "LineEdit",    "___", "Champ texte une ligne"),
    ("QTextEdit",    "TextEdit",    "txt", "Zone texte multi-lignes"),
    ("QCheckBox",    "CheckBox",    "[v]", "Case a cocher"),
    ("QRadioButton", "RadioButton", "(o)", "Bouton radio"),
    ("QComboBox",    "ComboBox",    "v",   "Liste deroulante"),
    ("QListWidget",  "ListWidget",  "::",  "Liste d'elements"),
    ("QTableWidget", "TableWidget", "###", "Tableau"),
]

# ── Lignes de code proposees ─────────────────────────────────
# Une ligne proposee doit s'executer telle quelle : l'eleve copie, colle,
# lance. Les anciens modeles (critical(p,titre,msg), setText(texte),
# connect(fn)) ne collaient que des noms inventes et se payaient un
# NameError a la premiere execution. Chaque entree est
# (libelle, modele_de_code, import_a_verifier) ; dans le modele, {obj} est
# remplace par windows.<nom> et {name} par le nom de l'objet. Les modeles
# tiennent sur une ligne : une definition inseree au milieu du corps d'une
# fonction ne peut pas etre correctement indentee.
_QITEM = "from PyQt5.QtWidgets import QTableWidgetItem"

WIDGET_METHODS = {
    "QLabel":       [("Modifier le texte", '{obj}.setText("Nouveau texte")', ""),
                     ("Lire le texte", "titre = {obj}.text()", "")],
    "QPushButton":  [("Connecter un evenement",
                      "{obj}.clicked.connect({name}_click)", "")],
    "QLineEdit":    [("Lire le contenu", "saisie = {obj}.text()", ""),
                     ("Modifier le contenu", '{obj}.setText("Nouveau texte")', ""),
                     ("Effacer", "{obj}.clear()", "")],
    "QTextEdit":    [("Lire le contenu", "texte = {obj}.toPlainText()", ""),
                     ("Modifier le contenu", '{obj}.setText("Nouveau texte")', ""),
                     ("Effacer", "{obj}.clear()", "")],
    "QCheckBox":    [("Lire l'etat", "coche = {obj}.isChecked()", "")],
    "QRadioButton": [("Lire l'etat", "choisi = {obj}.isChecked()", "")],
    "QComboBox":    [("Lire la selection", "choix = {obj}.currentText()", "")],
    "QListWidget":  [("Ajouter un element", '{obj}.addItem("Nouvel element")', ""),
                     ("Vider la liste", "{obj}.clear()", "")],
    "QTableWidget": [("Ajouter une cellule",
                      '{obj}.setItem(0, 0, QTableWidgetItem("Texte"))', _QITEM),
                     ("Inserer une ligne", "{obj}.insertRow({obj}.rowCount())", "")],
}

ROOT_CLASSES = {"QDialog", "QMainWindow", "QWidget",
                "centralwidget", "QScrollArea"}

# ── Layouts Qt Designer ──────────────────────────────────────
# Un fichier fait dans Qt Designer place les widgets dans des <layout> et
# n'ecrit aucune balise <geometry> : il faut estimer une position pour que
# l'apercu ne superpose pas tout, et il faut rendre la structure du layout
# a l'enregistrement pour ne pas detruire le fichier d'origine.
LAYOUT_AXIS = {"QVBoxLayout": "v",    "QHBoxLayout": "h",
               "QGridLayout": "grid", "QFormLayout": "form",
               "QStackedLayout": "stack", "QCardLayout": "stack"}

# Seuls ces widgets ont des <item> qui sont des elements de liste ; pour un
# QTableWidget les <item> sont des cellules et ne doivent pas y etre confondus.
ITEM_CLASSES = ("QComboBox", "QListWidget")

FALLBACK_SIZE = (100, 30)


def own_line(text, code):
    """Deplace le code insere pour qu'il occupe sa propre ligne.

    Collee en fin de ligne, une suggestion du panneau se souderait au code
    deja la ('windows.show()windows.label.clear()') et le fichier ne se
    lancerait plus, ce qui est exactement le reproche fait aux modeles.
    """
    try:
        before = text.get("insert linestart", "insert")
        after = text.get("insert", "insert lineend")
    except Exception:
        return code
    prefix = "\n" if before.strip() else ""
    suffix = "\n" if after.strip() else ""
    return prefix + code + suffix


class UiViewerPlugin(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=PANEL_BG)
        self.ui_file            = None
        self.widgets_data       = []
        self.selected_idx       = None
        self.widget_counter     = 0
        self._drag_origin       = {}
        self._prop_vars         = {}
        self._name_entry        = None      # champ "Nom" du panneau de proprietes
        self._name_hint         = None      # son message d'explication
        self._active_drag       = None
        self._active_resize     = None
        self.root_widget_name   = "Form"
        self.root_widget_class  = "QDialog"
        self.root_geometry      = (0, 0, 640, 480)
        self.root_title         = "Form"
        # Arbre XML d'origine : sert a rendre le fichier tel quel a l'enregistrement
        self._source_ui         = None
        self._source_uids       = []
        self._src_root          = {}
        # Journal des modifications : une copie du modele par pas d'annulation
        self._undo_stack        = []
        self._redo_stack        = []
        self._edit_sig          = None      # derniere cible editee (regroupement)
        self._gesture           = None      # etat avant un glisser / redimensionner
        self._build_ui()
        self._bind_history_keys()
        self._update_history_buttons()

    # ── Construction UI ─────────────────────────────────────

    def _build_ui(self):
        tb = tk.Frame(self, bg=PANEL_HDR, height=36)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)
        for txt, cmd in [("  + Nouveau  ", self._new),
                         ("  Ouvrir     ", self._open),
                         ("  Enregistrer", self._save)]:
            b = tk.Label(tb, text=txt, bg=PANEL_HDR, fg=PANEL_FG,
                         cursor="hand2", font=("TkDefaultFont", 9), pady=6)
            b.pack(side=tk.LEFT)
            b.bind("<Button-1>", lambda e, c=cmd: c())
            b.bind("<Enter>",    lambda e, w=b: w.config(bg="#3a3a3a"))
            b.bind("<Leave>",    lambda e, w=b: w.config(bg=PANEL_HDR))
        tk.Label(tb, text="|", bg=PANEL_HDR, fg="#3c3c3c",
                 font=("TkDefaultFont", 9), pady=6).pack(side=tk.LEFT)
        self._undo_lbl = self._hist_button(tb, "  Annuler  ", self.undo,
                                           "Annuler la derniere modification (Ctrl+Z)")
        self._redo_lbl = self._hist_button(tb, " Retablir  ", self.redo,
                                           "Retablir ce qui vient d'etre annule (Ctrl+Y)")
        self._title_lbl = tk.Label(tb, text="Sans titre",
                                   bg=PANEL_HDR, fg="#555",
                                   font=("TkDefaultFont", 8))
        self._title_lbl.pack(side=tk.RIGHT, padx=8)

        body = tk.Frame(self, bg=PANEL_BG)
        body.pack(fill=tk.BOTH, expand=True)
        self._build_toolbox(body)
        self._build_canvas(body)
        self._build_properties(body)

    def _build_toolbox(self, parent):
        outer = tk.Frame(parent, bg=TB_BG, width=128)
        outer.pack(side=tk.LEFT, fill=tk.Y)
        outer.pack_propagate(False)
        tk.Label(outer, text="WIDGETS", bg=TB_BG, fg="#555",
                 font=("TkDefaultFont", 7, "bold"), pady=6).pack()
        for cls, label, icon, tip in WIDGET_DEFS:
            f = tk.Frame(outer, bg=TB_BTN, cursor="hand2")
            f.pack(fill=tk.X, padx=6, pady=2)
            tk.Label(f, text=icon, bg=TB_BTN, fg="#888",
                     font=("Courier", 8), width=4).pack(
                side=tk.LEFT, padx=(4, 0))
            tk.Label(f, text=label, bg=TB_BTN, fg=PROP_FG,
                     font=("TkDefaultFont", 8), anchor="w",
                     pady=5).pack(side=tk.LEFT, padx=4, fill=tk.X,
                                  expand=True)
            for w in (f,) + tuple(f.winfo_children()):
                w.bind("<Enter>",    lambda e, fr=f: self._tb_h(fr, True))
                w.bind("<Leave>",    lambda e, fr=f: self._tb_h(fr, False))
                w.bind("<Button-1>", lambda e, c=cls: self._add_widget(c))
            self._tooltip(f, tip)

    def _tb_h(self, frame, on):
        col = TB_BTN_H if on else TB_BTN
        frame.config(bg=col)
        for c in frame.winfo_children():
            c.config(bg=col)

    def _hist_button(self, parent, txt, cmd, tip):
        """Bouton de journalise : gris quand il n'a rien a faire, allume quand
        la pile correspond n'est pas vide (_update_history_buttons)."""
        b = tk.Label(parent, text=txt, bg=PANEL_HDR, fg="#5a5a5a",
                     cursor="hand2", font=("TkDefaultFont", 9), pady=6)
        b.pack(side=tk.LEFT)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>",  lambda e, w=b: w.config(bg="#3a3a3a"))
        b.bind("<Leave>",  lambda e, w=b: w.config(bg=PANEL_HDR))
        self._tooltip(b, tip)
        return b

    def _build_canvas(self, parent):
        wrap = tk.Frame(parent, bg=PANEL_BG)
        wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        info_bar = tk.Frame(wrap, bg="#1a1a1a", height=20)
        info_bar.pack(fill=tk.X)
        info_bar.pack_propagate(False)
        self._info_lbl = tk.Label(info_bar, text="", bg="#1a1a1a", fg="#555",
                                  font=("Courier", 8))
        self._info_lbl.pack(side=tk.LEFT, padx=6)
        cf = tk.Frame(wrap, bg=PANEL_BG)
        cf.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(cf, bg="#3a3a3a", highlightthickness=0)
        hbar = ttk.Scrollbar(cf, orient=tk.HORIZONTAL, command=self.canvas.xview)
        vbar = ttk.Scrollbar(cf, orient=tk.VERTICAL,   command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        hbar.grid(row=1, column=0, sticky="ew")
        vbar.grid(row=0, column=1, sticky="ns")
        cf.rowconfigure(0, weight=1)
        cf.columnconfigure(0, weight=1)
        # Ombre
        self._shadow = tk.Frame(self.canvas, bg="#1a1a1a")
        self.canvas.create_window(24, 24, anchor="nw", window=self._shadow)
        # Zone Qt
        self.ui_frame = tk.Frame(self.canvas, bg=QT_BG)
        self._canvas_win = self.canvas.create_window(
            20, 20, anchor="nw", window=self.ui_frame)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.ui_frame.bind("<Button-1>", lambda e: self._deselect())

    def _build_properties(self, parent):
        PROP_W = 220
        outer = tk.Frame(parent, bg=PROP_BG, width=PROP_W)
        outer.pack(side=tk.LEFT, fill=tk.Y)
        outer.pack_propagate(False)

        tk.Label(outer, text="PROPRIETES", bg=PROP_BG, fg="#555",
                 font=("TkDefaultFont", 7, "bold"), pady=6).pack()

        # Canvas + scrollbar
        ps = ttk.Scrollbar(outer, orient=tk.VERTICAL)
        ps.pack(side=tk.RIGHT, fill=tk.Y)

        self._prop_canvas = tk.Canvas(outer, bg=PROP_BG,
                                      borderwidth=0, highlightthickness=0,
                                      yscrollcommand=ps.set)
        self._prop_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ps.configure(command=self._prop_canvas.yview)

        # Inner frame — width pinned to canvas width
        self.prop_frame = tk.Frame(self._prop_canvas, bg=PROP_BG)
        self._prop_win = self._prop_canvas.create_window(
            (0, 0), window=self.prop_frame, anchor="nw")

        # Keep inner frame width == canvas width
        def _on_canvas_resize(e):
            self._prop_canvas.itemconfig(self._prop_win, width=e.width)
        self._prop_canvas.bind("<Configure>", _on_canvas_resize)

        # Update scrollregion whenever content changes
        def _on_frame_configure(e):
            self._prop_canvas.configure(
                scrollregion=self._prop_canvas.bbox("all"))
        self.prop_frame.bind("<Configure>", _on_frame_configure)

        # Mousewheel scrolling (Windows + Linux)
        def _on_mousewheel(e):
            if e.num == 4:          # Linux scroll up
                self._prop_canvas.yview_scroll(-1, "units")
            elif e.num == 5:        # Linux scroll down
                self._prop_canvas.yview_scroll(1, "units")
            else:                   # Windows
                self._prop_canvas.yview_scroll(
                    int(-1 * (e.delta / 120)), "units")

        self._prop_canvas.bind("<MouseWheel>", _on_mousewheel)
        self._prop_canvas.bind("<Button-4>",   _on_mousewheel)
        self._prop_canvas.bind("<Button-5>",   _on_mousewheel)
        self.prop_frame.bind("<MouseWheel>",   _on_mousewheel)
        self.prop_frame.bind("<Button-4>",     _on_mousewheel)
        self.prop_frame.bind("<Button-5>",     _on_mousewheel)

        self._show_no_selection()

    # ── Annuler / retablir ───────────────────────────────────
    #
    # Une entree de journal est une copie COMPLETE du modele. Un fichier
    # d'eleve tient quelques dizaines de widgets : copier coute beaucoup moins
    # cher que de deviner quel champ a change, et une copie ne peut pas etre
    # contredite par un futur correcteur. _source_ui n'est pas copie :
    # l'enregistrement part d'un deepcopy de cet arbre (_merge_into_source) et
    # ne le modifie jamais, le partager est donc sur.

    STATE_KEYS = ("widgets_data", "widget_counter", "selected_idx",
                  "root_widget_name", "root_widget_class", "root_geometry",
                  "root_title", "_source_uids", "_src_root")
    UNDO_LIMIT = 40

    def _ensure_history(self):
        """Le journal ne doit jamais empecher une modification d'aboutir, meme
        sur un objet construit hors du constructeur (les harnais de test)."""
        if not hasattr(self, "_undo_stack"):
            self._undo_stack = []
            self._redo_stack = []
        self._redo_stack = getattr(self, "_redo_stack", [])
        return self._undo_stack

    def _state(self):
        etat = {}
        for key in self.STATE_KEYS:
            if hasattr(self, key):
                etat[key] = copy.deepcopy(getattr(self, key))
        if hasattr(self, "_source_ui"):
            etat["_source_ui"] = self._source_ui
        return etat

    def _restore(self, etat):
        for key in self.STATE_KEYS:
            if key in etat:
                setattr(self, key, etat[key])
        if "_source_ui" in etat:
            self._source_ui = etat["_source_ui"]

    def _push(self, etat):
        pile = self._ensure_history()
        pile.append(etat)
        if len(pile) > self.UNDO_LIMIT:
            del pile[0]
        self._update_history_buttons()

    def _record(self, sig):
        """Journalise l'etat AVANT la mutation. Les frappes successives sur le
        meme champ ne forment qu'un seul pas : sans ce regroupement, effacer
        un mot couterait huit coups d'Annuler."""
        if getattr(self, "_edit_sig", None) == sig:
            return
        self._edit_sig = sig
        self._ensure_history()
        self._redo_stack = []
        self._push(self._state())

    def _step(self):
        """Un ajout, une suppression, un doublon : chaque action compte, meme
        deux fois de suite la meme."""
        self._edit_sig = None
        self._ensure_history()
        self._redo_stack = []
        self._push(self._state())

    def _commit_gesture(self):
        """Valide le glisser/deplacer en cours. Un simple clic qui n'a rien
        deplace ne doit pas couter un coup d'Annuler."""
        gest = getattr(self, "_gesture", None)
        if gest is None:
            return
        idx, geom, etat = gest
        self._gesture = None
        try:
            maintenant = self.widgets_data[idx][1].get("geometry")
        except (IndexError, TypeError, AttributeError):
            return
        if maintenant != geom:
            self._edit_sig = None
            self._ensure_history()
            self._redo_stack = []
            self._push(etat)

    def undo(self):
        pile = self._ensure_history()
        if not pile:
            self._history_notice("Rien a annuler")
            return
        self._redo_stack.append(self._state())
        self._restore(pile.pop())
        self._edit_sig = None
        self._after_history_move()

    def redo(self):
        self._ensure_history()
        if not self._redo_stack:
            self._history_notice("Rien a retablir")
            return
        self._undo_stack.append(self._state())
        if len(self._undo_stack) > self.UNDO_LIMIT:
            del self._undo_stack[0]
        etat = self._redo_stack.pop()
        self._restore(etat)
        self._edit_sig = None
        self._after_history_move()

    def reset_history(self):
        self._undo_stack = []
        self._redo_stack = []
        self._edit_sig = None
        self._gesture = None
        self._update_history_buttons()

    def _after_history_move(self):
        if len(self._redo_stack) > self.UNDO_LIMIT:
            del self._redo_stack[0]
        self._update_history_buttons()
        self.redessine_apres_journal()

    def redessine_apres_journal(self):
        """Redessiner sans repasser par _select : c'est le journal qui remet
        la selection ou elle etait."""
        try:
            self._refresh()
            idx = getattr(self, "selected_idx", None)
            if idx is not None and 0 <= idx < len(self.widgets_data):
                self._show_properties(idx)
            else:
                self.selected_idx = None
                self._show_no_selection()
        except tk.TclError:
            pass          # le panneau etait en train de disparaitre

    def _history_notice(self, msg):
        try:
            self._info_lbl.config(text="  " + msg)
        except (tk.TclError, AttributeError):
            pass

    def _update_history_buttons(self):
        piles = ((getattr(self, "_undo_lbl", None),
                  getattr(self, "_undo_stack", [])),
                 (getattr(self, "_redo_lbl", None),
                  getattr(self, "_redo_stack", [])))
        for lbl, pile in piles:
            if lbl is None:
                continue
            try:
                lbl.config(fg="#cccccc" if pile else "#5a5a5a")
            except tk.TclError:
                pass

    def _bind_history_keys(self):
        """Ctrl+Z / Ctrl+Y pour la vue, et pour elle seule.

        bind_all est necessaire : la frappe a lieu dans un Entry enfant, et Tk
        ne fait pas remonter un Keypress aux Frames intermediaires (widget ->
        classe -> toplevel -> all). La garde sur le widget focalise
        (_event_for_us) laisse donc l'annulation du texte a l'editeur de Thonny.

        add=True n'est pas un detail : sans lui, chaque vue ouverte par-dessus
        la precedente REMPLACE sa liaison sur la balise « all », et une vue
        jamais posee vole Ctrl+Z a celle que l'eleve regarde. Avec lui, toutes
        les vues entendent la frappe et seule celle du focus agit."""
        for seq, action in (("<Control-z>", self.undo),
                            ("<Control-Z>", self.undo),
                            ("<Control-y>", self.redo),
                            ("<Control-Y>", self.redo),
                            ("<Control-Shift-Z>", self.redo),
                            ("<Control-Shift-z>", self.redo)):
            self.bind_all(seq, lambda e, a=action: self._history_key(e, a),
                          add=True)

    def _history_key(self, event, action):
        if not self._event_for_us(event):
            return None          # l'editeur annule son propre texte
        action()
        return "break"

    def _event_for_us(self, event):
        """A qui appartient cette frappe ?

        Attention : sur un bind_all, event.widget designe la FENETRE de
        niveau superieur, jamais le champ qui recoit les touches. Remonter sa
        chaine de maitres ne dirait donc rien d'utile : plusieurs vues (le
        concepteur, l'editeur, la shell) vivent dans la meme fenetre de
        Thonny. C'est le focus qu'il faut interroger."""
        try:
            if not self.winfo_exists():
                return False
        except tk.TclError:
            return False
        cible = self._focus_widget(event)
        if cible is None:
            # personne n'a le clavier : la frappe va a la fenetre visee par
            # l'evenement, et a elle seule.
            w = getattr(event, "widget", None)
            return w is not None and w is self.winfo_toplevel()
        while cible is not None:
            if cible is self:
                return True
            cible = getattr(cible, "master", None)
        return False

    def _focus_widget(self, event):
        """Le widget qui tient le clavier, ou None. Tk repond « none » quand
        la fenetre n'a pas encore recu le focus."""
        w = getattr(event, "widget", None) or self
        try:
            return w.focus_get()
        except (KeyError, tk.TclError):
            return None

    # ── Fichiers ─────────────────────────────────────────────

    def _new(self):
        if self.widgets_data and not messagebox.askyesno(
                "Nouveau", "Effacer le travail en cours ?"):
            return
        self.widgets_data.clear()
        self.ui_file = None
        self.widget_counter = 0
        self.selected_idx = None
        self.root_geometry = (0, 0, 640, 480)
        self._source_ui = None
        self._source_uids = []
        self._src_root = {}
        self.reset_history()
        self._title_lbl.config(text="Sans titre")
        self._refresh()

    def _open(self):
        path = filedialog.askopenfilename(
            title="Ouvrir fichier UI",
            filetypes=[("Fichiers UI", "*.ui"), ("Tous", "*.*")])
        if path:
            self.load_new_ui_file(path)

    def _save(self):
        troubles = self._name_troubles()
        if troubles:
            messagebox.showerror(
                "Noms d'objets",
                "Le fichier aurait plusieurs widgets avec le meme nom, ou un nom\n"
                "impossible a utiliser dans le code. Corrigez avant d'enregistrer :\n\n  • "
                + "\n  • ".join(troubles),
                parent=self)
            return
        if not self.ui_file:
            path = filedialog.asksaveasfilename(
                title="Enregistrer", defaultextension=".ui",
                filetypes=[("Fichiers UI", "*.ui"), ("Tous", "*.*")])
            if not path:
                return
            self.ui_file = path
        self._write_ui_file(self.ui_file)
        self._title_lbl.config(text=os.path.basename(self.ui_file))
        messagebox.showinfo("Enregistre", f"Fichier enregistre :\n{self.ui_file}")

    def load_new_ui_file(self, path):
        self.ui_file = path
        self.widgets_data, root_info = self._parse_ui(path)
        self.root_geometry = root_info.get("geometry", (0, 0, 640, 480))
        self.root_title    = root_info.get("title", "Form")
        self.selected_idx  = None
        # Le compteur de noms est remonte a partir du fichier par _parse_ui.
        # Un fichier qui s'ouvre n'est pas la suite du precedent : Annuler ne
        # doit jamais faire revivre les widgets de la fenetre d'avant.
        self.reset_history()
        self._title_lbl.config(text=os.path.basename(path))
        self._refresh()

    # ── XML ──────────────────────────────────────────────────

    def _parse_ui(self, path):
        data, root_info = [], {}
        try:
            tree_root = ET.parse(path).getroot()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lire :\n{e}")
            return data, root_info

        def read_props(w_elem):
            props = {
                "name":       w_elem.get("name", "widget"),
                "styleSheet": "",
                "font":       {"size": 9, "bold": False,
                               "italic": False, "family": ""},
            }
            for p in w_elem.findall("property"):
                pn = p.get("name", "")
                if pn == "geometry":
                    r = p.find("rect")
                    if r is not None:
                        try:
                            props["geometry"] = (
                                int(r.findtext("x",      "0")),
                                int(r.findtext("y",      "0")),
                                int(r.findtext("width",  "100")),
                                int(r.findtext("height", "30")),
                            )
                        except ValueError:
                            pass
                elif pn in ("text", "placeholderText"):
                    s = p.find("string")
                    if s is not None and s.text:
                        props[pn] = s.text
                elif pn in ("windowTitle", "title"):
                    s = p.find("string")
                    if s is not None and s.text:
                        props["title"] = s.text
                elif pn == "font":
                    fe = p.find("font")
                    if fe is not None:
                        try:
                            sz = int(fe.findtext("pointsize", "9"))
                        except ValueError:
                            sz = 9
                        props["font"] = {
                            "size":   sz,
                            "bold":   fe.findtext("bold",   "false") == "true",
                            "italic": fe.findtext("italic", "false") == "true",
                            "family": fe.findtext("family", "") or "",
                        }
                elif pn == "styleSheet":
                    s = p.find("string")
                    if s is not None and s.text:
                        props["styleSheet"] = s.text
                elif pn == "checked":
                    b = p.find("bool")
                    props["checked"] = b is not None and b.text == "true"
            if w_elem.get("class") in ITEM_CLASSES:
                # attention : un QTableWidget a aussi des <item>, mais ce sont
                # des cellules ; ils ne doivent pas devenir des "items" de liste
                for item in w_elem.findall("item"):
                    props.setdefault("items", [])
                    s = self._item_text(item)
                    if s:
                        props["items"].append(s)
            props["columns"] = len(w_elem.findall("column"))
            props["rows"]    = len(w_elem.findall("row"))
            return props

        self._source_ui = None
        self._source_uids = []
        self._src_root = {}
        root_elem = tree_root.find("widget")
        if root_elem is None:
            return data, root_info

        rp = read_props(root_elem)
        root_info["geometry"] = rp.get("geometry", (0, 0, 640, 480))
        root_info["title"]    = rp.get("title", rp.get("windowTitle", "Form"))
        self.root_widget_name  = root_elem.get("name", "Form")
        self.root_widget_class = root_elem.get("class", "QDialog")

        # Les widgets sont numerotes dans l'ordre du document, layouts compris :
        # ce numero (uid) sert de cle pour retrouver l'element XML a l'enregistrement.
        ordered = self._walk_widgets(root_elem)
        est = self._estimate_geometries(root_elem)
        for i, w in enumerate(ordered):
            uid = "w%d" % i
            cls = w.get("class", "")
            if cls in ROOT_CLASSES:
                continue
            props = read_props(w)
            if not cls:
                continue
            props["_uid"] = uid
            own = self._read_rect(w)
            props["_est"] = None if own else est.get(id(w))
            if own is None and props["_est"]:
                props["geometry"] = props["_est"]
            props["_src"] = self._snapshot(props)
            self._source_uids.append(uid)
            data.append((cls, props))

        self._source_ui = tree_root
        self._src_root = {"geometry": self._read_rect(root_elem),
                          "title": root_info.get("title", "")}
        # Le compteur de noms repart du fichier lu, ou qu'on lise celui-ci :
        # sinon le premier widget ajoute porterait un nom deja present, et
        # loadUi, qui accepte le doublon, ferait viser windows.<nom> au mauvais
        # widget. Ici et pas dans load_new_ui_file : tous les chemins d'ouverture
        # passent par cette lecture.
        self.widget_counter = self._highest_seed(self.widget_counter, data)
        return data, root_info

    # ── Lecture / ecriture XML fine ──────────────────────────

    def _snapshot(self, props):
        """Copie de l'etat lu dans le fichier, pour ne reecrire que ce qui a change."""
        snap = {}
        for key in ("geometry", "text", "placeholderText", "title",
                    "styleSheet", "checked", "rows", "columns", "items"):
            val = props.get(key)
            snap[key] = list(val) if isinstance(val, list) else val
        font = props.get("font")
        snap["font"] = dict(font) if isinstance(font, dict) else None
        return snap

    def _item_text(self, item):
        for p in item.findall("property"):
            if p.get("name") == "text":
                return p.findtext("string", "")
        return ""

    def _walk_widgets(self, form):
        """Tous les <widget> sous form, y compris ceux ranges dans un <layout>."""
        out = []

        def rec(elem):
            for child in elem:
                if child.tag == "widget":
                    out.append(child)
                    rec(child)
                elif child.tag in ("layout", "item"):
                    rec(child)

        rec(form)
        return out

    def _find_prop(self, el, name):
        for p in el.findall("property"):
            if p.get("name") == name:
                return p
        return None

    def _read_rect(self, w):
        """Le <rect> de la propriete geometry, ou None si le widget est pose par un layout."""
        p = self._find_prop(w, "geometry")
        r = p.find("rect") if p is not None else None
        if r is None:
            return None
        try:
            return (int(r.findtext("x", "0")), int(r.findtext("y", "0")),
                    int(r.findtext("width", "100")),
                    int(r.findtext("height", "30")))
        except ValueError:
            return None

    def _prop_num(self, el, name, default=None):
        p = self._find_prop(el, name)
        if p is None:
            return default
        for tag in ("number", "float", "double"):
            txt = p.findtext(tag)
            if txt is not None:
                try:
                    return int(float(txt))
                except ValueError:
                    return default
        return default

    def _size_pref(self, el):
        """Taille figee / preferred / minimum declaree par le fichier, sinon None."""
        for pname in ("fixedSize", "preferredSize", "minimumSize"):
            p = self._find_prop(el, pname)
            s = p.find("size") if p is not None else None
            if s is None:
                continue
            try:
                w = int(s.findtext("width", "0"))
                h = int(s.findtext("height", "0"))
            except ValueError:
                continue
            if w > 0 and h > 0:
                return (w, h)
        return None

    def _layout_margins(self, lay):
        m = self._prop_num(lay, "margin")
        sp = self._prop_num(lay, "spacing")
        if m is None or m < 0:
            m = 9
        if sp is None or sp < 0:
            sp = 6
        return m, sp

    def _layout_items(self, lay):
        """([ (node, row, col, rowspan, colspan) ], axe) ; node = ('w'|'l'|'s', element)."""
        axis = LAYOUT_AXIS.get(lay.get("class", ""), "v")
        out = []
        for it in lay.findall("item"):
            target = None
            for ch in it:
                if ch.tag == "widget":
                    target = ("w", ch)
                    break
                if ch.tag == "layout":
                    target = ("l", ch)
                    break
                if ch.tag == "spacer":
                    target = ("s", ch)
                    break
            if target is None:
                continue
            row = col = None
            rs = cs = 1
            if axis in ("grid", "form"):
                row = self._int_attr(it, "row")
                col = self._int_attr(it, "column")
                if row is None and col is None:
                    # ancien style Designer : propriete top/left/height/width
                    row = self._prop_num(it, "top", 0) or 0
                    col = self._prop_num(it, "left", 0) or 0
                    rs = self._prop_num(it, "height", 1) or 1
                    cs = self._prop_num(it, "width", 1) or 1
                else:
                    row = row or 0
                    col = col or 0
                    rs = self._int_attr(it, "rowspan", 1) or 1
                    cs = self._int_attr(it, "colspan", 1) or 1
            else:
                row, col = len(out), 0
            # un fichier malforme ne doit pas nous faire alouer des grilles geantes
            row, col = min(max(0, row), 200), min(max(0, col), 200)
            rs = min(max(1, rs), 20)
            cs = min(max(1, cs), 20)
            out.append((target, row, col, rs, cs))
        return out, axis

    @staticmethod
    def _int_attr(el, name, default=None):
        try:
            return int(el.get(name))
        except (TypeError, ValueError):
            return default

    def _prop_enum(self, el, name):
        """Texte de <property name=name><enum>…</enum>, ou ""."""
        p = self._find_prop(el, name)
        return (p.findtext("enum", "") or "") if p is not None else ""

    def _stretch(self, node, axis):
        """Facteur d'etirement d'un element le long de l'axe (0 = taille figee)."""
        kind, el = node
        if kind == "s":
            if "Expanding" not in self._prop_enum(el, "sizeType"):
                return 0
            ori = self._prop_enum(el, "orientation")
            want = "Vertical" if axis == "v" else "Horizontal"
            return 0 if (ori and want not in ori) else 1
        if kind != "w":
            return 0
        best = 0
        for pname, attr in (("verticalSizePolicy", "vsizetype"),
                            ("horizontalSizePolicy", "hsizetype")):
            if (pname == "verticalSizePolicy") != (axis == "v"):
                continue
            p = self._find_prop(el, pname)
            sp = p.find("sizepolicy") if p is not None else None
            if sp is None:
                continue
            try:
                best = max(best, int(sp.findtext(
                    "verstretch" if axis == "v" else "horstretch", "0")))
            except ValueError:
                pass
            if "Expanding" in (sp.get(attr) or ""):
                best = max(best, 1)
        return best

    def _estimate_geometries(self, form):
        """Estime (x, y, w, h) des widgets que le layout positionne.

        Retourne {id(element): rectangle}. Les widgets ayant leur propre
        <geometry> n'y figurent pas : ils gardent leur position absolue.
        """
        est = {}

        def pref(node):
            kind, el = node
            if kind == "w":
                sz = self._size_pref(el)
                if sz:
                    return sz
                r = self._read_rect(el)
                if r:
                    return (r[2], r[3])
                lays = el.findall("layout")
                if lays:
                    return layout_pref(lays[0])
                return self._default_size(el.get("class", "")) or FALLBACK_SIZE
            if kind == "l":
                return layout_pref(el)
            p = self._find_prop(el, "sizeHint")
            s = p.find("size") if p is not None else None
            if s is None:
                return (1, 1)
            try:
                return (max(1, int(s.findtext("width", "1"))),
                        max(1, int(s.findtext("height", "1"))))
            except ValueError:
                return (1, 1)

        def spread(total, prefs, stretches, spacing):
            """Repartit `total` entre les elements, etirements compris."""
            n = len(prefs)
            if n == 0:
                return []
            avail = max(0, total - spacing * (n - 1))
            st_total = sum(stretches)
            if st_total > 0:
                fixed = sum(p for p, s in zip(prefs, stretches) if s == 0)
                rest = max(0, avail - fixed)
                return [p if s == 0 else max(8, int(rest * s / st_total))
                        for p, s in zip(prefs, stretches)]
            whole = sum(prefs)
            if whole <= 0:
                return [max(8, int(avail / n))] * n
            return [max(8, int(p * avail / whole)) for p in prefs]

        def layout_pref(lay):
            items, axis = self._layout_items(lay)
            if not items:
                return (10, 10)
            m, sp = self._layout_margins(lay)
            dims = [pref(node) for node, _r, _c, _rs, _cs in items]
            if axis == "h":
                return (sum(d[0] for d in dims) + sp * (len(dims) - 1) + 2 * m,
                        max(d[1] for d in dims) + 2 * m)
            if axis == "v":
                return (max(d[0] for d in dims) + 2 * m,
                        sum(d[1] for d in dims) + sp * (len(dims) - 1) + 2 * m)
            if axis in ("grid", "form"):
                cols, rows = cells(items, dims, axis)
                return (sum(cols) + sp * max(0, len(cols) - 1) + 2 * m,
                        sum(rows) + sp * max(0, len(rows) - 1) + 2 * m)
            return (max(d[0] for d in dims) + 2 * m,
                    max(d[1] for d in dims) + 2 * m)

        def cells(items, dims, axis):
            """Largeurs de colonnes et hauteurs de lignes d'une grille / d'un form."""
            ncols = max((c + cs for _n, _r, c, _rs, cs in items), default=1) + 1
            nrows = max((r + rs for _n, r, _c, rs, _cs in items), default=1) + 1
            colw = [0] * ncols
            rowh = [0] * nrows
            colst = [0] * ncols
            rowst = [0] * nrows
            for (node, r, c, rs, cs), (dw, dh) in zip(items, dims):
                if cs == 1:
                    colw[c] = max(colw[c], dw)
                    colst[c] = max(colst[c], self._stretch(node, "h"))
                if rs == 1:
                    rowh[r] = max(rowh[r], dh)
                    rowst[r] = max(rowst[r], self._stretch(node, "v"))
            if axis == "form" and ncols > 0:
                # colonne 0 = etiquette : on la plafonne pour laisser la place au champ
                colw[0] = min(colw[0], 160)
            return colw, rowh

        def col_stretch(items, axis, k):
            return max([self._stretch(i[0], axis) for i in items
                        if i[2] == k and i[4] == 1] or [0])

        def row_stretch(items, k):
            return max([self._stretch(i[0], "v") for i in items
                        if i[1] == k and i[3] == 1] or [0])

        def place(node, x, y, w, h):
            kind, el = node
            if kind == "l":
                place_layout(el, x, y, w, h)
            elif kind == "w":
                place_widget(el, x, y, w, h)

        def place_widget(el, x, y, w, h):
            r = self._read_rect(el)
            if r:
                rect = r
            else:
                sz = self._size_pref(el)
                nw = min(sz[0], int(w)) if sz else int(w)
                nh = sz[1] if sz else int(h)
                rect = (int(x), int(y), max(8, nw), max(8, nh))
                est[id(el)] = rect
            for sub in el:
                if sub.tag == "layout":
                    place_layout(sub, *rect)
                elif sub.tag == "widget":
                    place_widget(sub, *rect)

        def place_layout(lay, x, y, w, h):
            items, axis = self._layout_items(lay)
            if not items:
                return
            m, sp = self._layout_margins(lay)
            ix, iy = x + m, y + m
            iw = max(1, w - 2 * m)
            ih = max(1, h - 2 * m)
            dims = [pref(node) for node, _r, _c, _rs, _cs in items]
            nodes = [i[0] for i in items]
            if axis == "v":
                hs = spread(ih, [d[1] for d in dims],
                            [self._stretch(n, "v") for n in nodes], sp)
                cur = iy
                for (node, _r, _c, _rs, _cs), hh in zip(items, hs):
                    place(node, ix, cur, iw, hh)
                    cur += hh + sp
            elif axis == "h":
                ws = spread(iw, [d[0] for d in dims],
                            [self._stretch(n, "h") for n in nodes], sp)
                cur = ix
                for (node, _r, _c, _rs, _cs), ww in zip(items, ws):
                    place(node, cur, iy, ww, ih)
                    cur += ww + sp
            elif axis in ("grid", "form"):
                ncols = max(c + cs for _n, _r, c, _rs, cs in items) + 1
                nrows = max(r + rs for _n, r, _c, rs, _cs in items) + 1
                colw, rowh = cells(items, dims, axis)
                cw = spread(iw, colw,
                            [col_stretch(items, "h", k) for k in range(ncols)], sp)
                rh = spread(ih, rowh,
                            [row_stretch(items, k) for k in range(nrows)], sp)
                ox = [ix + sum(cw[:k]) + sp * k for k in range(ncols)]
                oy = [iy + sum(rh[:k]) + sp * k for k in range(nrows)]
                for (node, r, c, rs, cs), (dw, dh) in zip(items, dims):
                    ww = sum(cw[c:c + cs]) + sp * (cs - 1)
                    hh = sum(rh[r:r + rs]) + sp * (rs - 1)
                    place(node, ox[c], oy[r], ww, hh)
            else:
                for node, _r, _c, _rs, _cs in items:
                    place(node, ix, iy, iw, ih)

        place_widget(form, *self._root_rect(form))
        return est

    def _root_rect(self, form):
        return self._read_rect(form) or (0, 0, 640, 480)


    def _root_class_name(self):
        """Nom de la classe générée (balise <class>), tel que l'écrit Qt Designer."""
        return {"QDialog": "Dialog", "QMainWindow": "MainWindow",
                "QWidget": "Form"}.get(self.root_widget_class,
                                       self.root_widget_name or "Form")

    def _write_ui_file(self, path):
        if getattr(self, "_source_ui", None) is not None:
            root = self._merge_into_source()
        else:
            root = self._build_fresh_ui()
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(path, encoding="utf-8",
                                   xml_declaration=True)

    def _build_fresh_ui(self):
        root = ET.Element("ui", version="4.0")
        # <class> est obligatoire : sans cette balise PyQt5.uic lève
        # "'Properties' object has no attribute 'uiname'" et le fichier
        # enregistré devient inutilisable par loadUi.
        ET.SubElement(root, "class").text = self._root_class_name()
        form = ET.SubElement(root, "widget", {
            "class": self.root_widget_class,
            "name":  self.root_widget_name,
        })
        gx, gy, gw, gh = self.root_geometry
        pg = ET.SubElement(form, "property", name="geometry")
        r  = ET.SubElement(pg, "rect")
        for tag, val in zip(["x","y","width","height"], [gx,gy,gw,gh]):
            ET.SubElement(r, tag).text = str(val)
        if getattr(self, "root_title", ""):
            pw = ET.SubElement(form, "property", name="windowTitle")
            ET.SubElement(pw, "string").text = self.root_title
        for cls, props in self.widgets_data:
            w = ET.SubElement(form, "widget", {
                "class": cls, "name": props.get("name", "widget")})
            geom = props.get("geometry", (10, 10, 100, 30))
            pg = ET.SubElement(w, "property", name="geometry")
            r  = ET.SubElement(pg, "rect")
            for tag, val in zip(["x","y","width","height"], geom):
                ET.SubElement(r, tag).text = str(val)
            for key in ("text", "placeholderText", "title"):
                if props.get(key):
                    pt = ET.SubElement(w, "property", name=key)
                    ET.SubElement(pt, "string").text = props[key]
            fp = props.get("font", {})
            if fp.get("size", 9) != 9 or fp.get("bold") or \
               fp.get("italic") or fp.get("family"):
                pf = ET.SubElement(w, "property", name="font")
                fe = ET.SubElement(pf, "font")
                ET.SubElement(fe, "pointsize").text = str(fp.get("size", 9))
                if fp.get("bold"):   ET.SubElement(fe, "bold").text   = "true"
                if fp.get("italic"): ET.SubElement(fe, "italic").text = "true"
                if fp.get("family"): ET.SubElement(fe, "family").text = fp["family"]
            if props.get("styleSheet"):
                ps = ET.SubElement(w, "property", name="styleSheet")
                ET.SubElement(ps, "string").text = props["styleSheet"]
            if cls in ("QCheckBox", "QRadioButton"):
                pc = ET.SubElement(w, "property", name="checked")
                ET.SubElement(pc, "bool").text = (
                    "true" if props.get("checked") else "false")
            if cls == "QTableWidget":
                try:
                    nrows = int(props.get("rows", 0) or 0)
                    ncols = int(props.get("columns", 0) or 0)
                except (TypeError, ValueError):
                    nrows = ncols = 0
                for pname, val in (("columnCount", ncols), ("rowCount", nrows)):
                    pe = ET.SubElement(w, "property", name=pname)
                    ET.SubElement(pe, "number").text = str(val)
                # Designer et notre propre parseur comptent les éléments
                # <column>/<row> pour connaître la taille du tableau.
                for _ in range(ncols):
                    ET.SubElement(w, "column")
                for _ in range(nrows):
                    ET.SubElement(w, "row")
            for it in props.get("items", []):
                ie = ET.SubElement(w, "item")
                ip = ET.SubElement(ie, "property", name="text")
                ET.SubElement(ip, "string").text = it
        return root

    # ── Enregistrement d'un fichier venant de Qt Designer ────
    # On part de l'arbre XML lu (deepcopy) et on n'y touche que ce que
    # l'utilisateur a change : la structure des <layout>, les <connections>,
    # les <resources> et les proprietes inconnues survivent a l'enregistrement.

    def _merge_into_source(self):
        root = copy.deepcopy(self._source_ui)
        form = root.find("widget")
        if form is None:                      # fichier inattendu : on reconstruit
            return self._build_fresh_ui()

        if tuple(self.root_geometry) != self._src_root.get("geometry"):
            self._set_rect_prop(form, self.root_geometry)
        title = getattr(self, "root_title", "")
        if title and title != self._src_root.get("title"):
            self._set_string_prop(form, "windowTitle", title)

        by_uid = {"w%d" % i: el
                  for i, el in enumerate(self._walk_widgets(form))}
        lay = self._root_layout(form)
        seen = set()
        for cls, props in self.widgets_data:
            el = by_uid.get(props.get("_uid")) if props.get("_uid") else None
            if el is None:
                # widget ajoute dans le concepteur
                el, src = self._insert_added(form, lay, cls, props)
                self._write_changed(el, cls, props, src)
            else:
                seen.add(props["_uid"])
                self._write_changed(el, cls, props, props.get("_src") or {})

        # widgets supprimes dans le concepteur -> retirer l'element et son <item>
        parents = {child: parent
                   for parent in root.iter() for child in parent}
        for uid in self._source_uids:
            if uid in seen:
                continue
            el = by_uid.get(uid)
            parent = parents.get(el)
            if el is None or parent is None:
                continue
            if parent.tag == "item":
                grand = parents.get(parent)
                (grand or parent).remove(parent if grand else el)
            else:
                parent.remove(el)
        return root

    def _root_layout(self, form):
        """Le <layout> qui occupe le conteneur racine, ou None si la pose est libre.

        Deux formes de fichier Designer : la racine porte elle-même son layout
        (QDialog, QWidget), ou elle n'a qu'un seul enfant widget qui le porte
        (QMainWindow > centralwidget). Exiger l'enfant unique évite d'aller
        ranger le nouveau widget dans le layout d'un QGroupBox voisin.
        """
        lay = form.find("layout")
        if lay is not None:
            return lay
        enfants = form.findall("widget")
        if len(enfants) == 1:
            return enfants[0].find("layout")
        return None

    def _next_grid_row(self, lay):
        """Prochaine ligne libre d'une grille ou d'un formulaire (les <item>
        à l'ancien style Designer portent leur ligne en propriété <top>)."""
        rang = 0
        for it in lay.findall("item"):
            r = self._int_attr(it, "row")
            if r is None:
                r = self._prop_num(it, "top", 0) or 0
            rang = max(rang, r)
        return rang + 1

    def _insert_added(self, form, lay, cls, props):
        """Insère le widget ajouté, là où le fichier le respectera.

        Retourne (element, etat_de_reference) : la référence indique à
        _write_changed si la position doit être écrite. Un fichier dont la
        racine est occupée par un layout donne sa géométrie à tout ce qu'il
        contient — y déposer un <widget> en pose absolue le fait retomber sur
        (0,0) derrière les autres, visible dans le concepteur mais invisible à
        l'exécution. Il rejoint donc le layout comme nouvel <item>, sans
        <geometry>. Sans layout, la pose absolue reste la bonne réponse.
        """
        name = props.get("name", "widget")
        if lay is None:
            el = ET.SubElement(form, "widget", {"class": cls, "name": name})
            self._set_rect_prop(el, props.get("geometry", (10, 10, 100, 30)))
            return el, {}

        item = ET.SubElement(lay, "item")
        if LAYOUT_AXIS.get(lay.get("class", ""), "v") in ("grid", "form"):
            # une grille place ses enfants par ligne/colonne : à défaut de ces
            # attributs l'item tomberait en (0,0) par-dessus le premier champ
            item.set("row", str(self._next_grid_row(lay)))
            item.set("column", "0")
        el = ET.SubElement(item, "widget", {"class": cls, "name": name})
        return el, {"geometry": list(props.get("geometry") or [])}

    def _write_changed(self, el, cls, props, src):
        """Reecrit dans `el` uniquement les proprietes modifiees depuis l'ouverture."""
        geom = props.get("geometry")
        src_geom = src.get("geometry")
        if geom and (tuple(src_geom or ()) != tuple(geom)):
            # un widget pose par un layout n'a pas de geometry : on n'en écrit
            # une que si l'utilisateur l'a realmente deplace.
            if src_geom or geom != props.get("_est"):
                self._set_rect_prop(el, geom)

        for key in ("text", "placeholderText", "title"):
            val = props.get(key)
            if val and val != src.get(key):
                self._set_string_prop(el, key, val)

        if props.get("styleSheet") and \
           props["styleSheet"] != src.get("styleSheet"):
            self._set_string_prop(el, "styleSheet", props["styleSheet"])

        font = props.get("font") or {}
        if font != (src.get("font") or {}) and self._font_is_custom(font):
            self._set_font_prop(el, font)

        if cls in ("QCheckBox", "QRadioButton") and \
           bool(props.get("checked")) != bool(src.get("checked")):
            self._set_bool_prop(el, "checked", bool(props.get("checked")))

        if cls == "QTableWidget":
            self._sync_table(el, props, src)

        items = props.get("items")
        if items is not None and list(items) != list(src.get("items") or []):
            self._sync_items(el, items)

    def _sync_table(self, el, props, src):
        try:
            nrows = int(props.get("rows", 0) or 0)
            ncols = int(props.get("columns", 0) or 0)
        except (TypeError, ValueError):
            return
        # les <column> existantes gardent leur titre : on ajuste seulement le nombre
        if ncols != int(src.get("columns") or 0):
            self._set_number_prop(el, "columnCount", ncols)
            self._adjust_count(el, "column", ncols)
        if nrows != int(src.get("rows") or 0):
            self._set_number_prop(el, "rowCount", nrows)
            self._adjust_count(el, "row", nrows)

    def _adjust_count(self, el, tag, want):
        have = el.findall(tag)
        for extra in have[want:]:
            el.remove(extra)
        for _ in range(want - len(have)):
            ET.SubElement(el, tag)

    def _sync_items(self, el, texts):
        have = el.findall("item")
        for extra in have[len(texts):]:
            el.remove(extra)
        for i, text in enumerate(texts):
            it = have[i] if i < len(have) else ET.SubElement(el, "item")
            self._set_string_prop(it, "text", text)

    def _insert_prop(self, el, name):
        prop = ET.Element("property", name=name)
        at = 0
        for i, child in enumerate(list(el)):
            if child.tag == "property":
                at = i + 1
        el.insert(at, prop)
        return prop

    def _reset_prop(self, el, name):
        prop = self._find_prop(el, name)
        if prop is None:
            prop = self._insert_prop(el, name)
        for child in list(prop):
            prop.remove(child)
        return prop

    def _set_rect_prop(self, el, rect):
        r = ET.SubElement(self._reset_prop(el, "geometry"), "rect")
        for tag, val in zip(("x", "y", "width", "height"), rect):
            ET.SubElement(r, tag).text = str(int(val))

    def _set_string_prop(self, el, name, text):
        ET.SubElement(self._reset_prop(el, name), "string").text = text

    def _set_number_prop(self, el, name, val):
        ET.SubElement(self._reset_prop(el, name), "number").text = str(int(val))

    def _set_bool_prop(self, el, name, val):
        ET.SubElement(self._reset_prop(el, name), "bool").text = (
            "true" if val else "false")

    def _font_is_custom(self, fp):
        """Vrai si la police doit vraiment produire une balise <font>."""
        return bool(fp.get("size", 9) != 9 or fp.get("bold") or
                    fp.get("italic") or fp.get("family"))

    def _set_font_prop(self, el, fp):
        # on complete le <font> existant plutot que de le remplacer, pour
        # conserver les champs que le concepteur ne gerre pas (weight, kerning…)
        prop = self._find_prop(el, "font")
        fe = prop.find("font") if prop is not None else None
        if fe is None:
            fe = ET.SubElement(self._reset_prop(el, "font"), "font")

        def put(tag, text):
            e = fe.find(tag)
            if e is None:
                e = ET.SubElement(fe, tag)
            e.text = text

        put("pointsize", str(fp.get("size", 9)))
        put("bold", "true" if fp.get("bold") else "false")
        put("italic", "true" if fp.get("italic") else "false")
        if fp.get("family"):
            put("family", fp["family"])

    # ── Ajout widgets ────────────────────────────────────────

    def _used_names(self, exclude_idx=None):
        """Tous les noms d'objet du fichier, hors le widget en cours d'edition."""
        return {props.get("name")
                for i, (_, props) in enumerate(self.widgets_data)
                if i != exclude_idx and props.get("name")}

    @staticmethod
    def _valid_qt_name(name):
        """Un nom d'objet doit rester un identifiant : Designer et le code
        genere (windows.<nom>) n'acceptent ni espace, ni tiret, ni chiffre initial."""
        if not name:
            return False
        first, rest = name[0], name[1:]
        return (first.isalpha() or first == "_") and all(
            c.isalnum() or c == "_" for c in rest)

    def _highest_seed(self, current=0, items=None):
        """Le plus grand numero rencontre dans les noms des widgets lus."""
        highest = current
        for _, props in (self.widgets_data if items is None else items):
            name = props.get("name", "")
            digits = name[len(name.rstrip("0123456789")):]
            if digits:
                highest = max(highest, int(digits))
        return highest

    def _next_seed(self, base, current=0):
        """Prochain suffixe de la famille, cherche dans les widgets presents.
        Le numero ne depend que de la famille elle-meme : un champ de texte
        ajoute a un fichier qui contient deja cinq boutons doit s'appeler
        lineedit1, pas lineedit6. Ce que le numero doit garantir (l'unicite)
        est verifie par _unique_name, qui repart du modele, jamais d'un
        compteur qu'un fichier ouvert aurait pu fausser."""
        start = current + 1
        for _, props in self.widgets_data:
            name = props.get("name", "")
            if not name.startswith(base):
                continue
            digits = name[len(base):]
            if digits.isdigit():
                start = max(start, int(digits) + 1)
        return start

    def _unique_name(self, base, exclude_idx=None):
        """Un nom libre, dans la famille de base, qui ne heurte aucun autre widget."""
        used = self._used_names(exclude_idx)
        name = base
        if name in used or not self._valid_qt_name(name):
            suffix = self._next_seed(base)
            name = f"{base}{suffix}"
            while name in used or not self._valid_qt_name(name):
                suffix += 1
                name = f"{base}{suffix}"
            # le compteur reste la memoire du plus grand numero emis, pour
            # qu'un outil exterieur puisse lire l'etat sans se fier aux noms
            self.widget_counter = max(self.widget_counter, suffix)
        return name

    def _name_problem(self, name, idx):
        """Pourquoi ce nom ne peut pas etre adopte, ou '' s'il est libre."""
        if not name:
            return "Le nom d'objet ne peut pas etre vide."
        if not self._valid_qt_name(name):
            return ("Un nom d'objet ne prend que des lettres, chiffres et « _ », "
                    "et ne commence pas par un chiffre.")
        if name in self._used_names(idx):
            return "Ce nom appartient deja a un autre widget de l'interface."
        return ""

    def _add_widget(self, cls):
        short  = cls.replace("Q", "").lower()
        # _unique_name choisit le suffixe : le compteur n'a pas a etre a jour
        name   = self._unique_name(short)
        gw, gh = self._default_size(cls)
        off    = 10 + (len(self.widgets_data) % 10) * 14
        x = y = off
        anchor = self._layout_anchor()
        if anchor:
            # le fichier est pilote par un layout : a l'enregistrement le widget
            # ira en fin de colonne, autant l'afficher des maintenant a cette
            # place au lieu de la cascade de creation
            x, y = anchor
        props  = {
            "name":       name,
            "geometry":   (x, y, gw, gh),
            "text":       self._default_text(cls),
            "styleSheet": "",
            "font":       {"size": 9, "bold": False,
                           "italic": False, "family": ""},
        }
        if cls in ("QComboBox", "QListWidget"):
            props["items"] = ["Element 1", "Element 2", "Element 3"]
        if cls == "QTableWidget":
            props["rows"]    = 3
            props["columns"] = 3
        if cls in ("QCheckBox", "QRadioButton"):
            props["checked"] = False
        self._step()
        self.widgets_data.append((cls, props))
        self._refresh()
        self._select(len(self.widgets_data) - 1)

    def _layout_anchor(self):
        """Position d'affichage d'un widget ajouté à un fichier piloté par un
        layout : sous le contenu existant, aligné sur sa marge gauche ; None si
        la pose reste absolue.

        La place réelle sera décidée par Qt à l'exécution — il s'agit seulement
        de ne pas dessiner le nouveau widget par-dessus ceux déjà en place.
        """
        src = getattr(self, "_source_ui", None)
        form = src.find("widget") if src is not None else None
        if form is None or self._root_layout(form) is None:
            return None
        rects = [p.get("geometry") for _c, p in self.widgets_data if p.get("geometry")]
        if not rects:
            return None
        left = min(r[0] for r in rects)
        bas = max(r[1] + r[3] for r in rects) + 6
        try:
            hauteur = int(self.root_geometry[3])
        except Exception:
            return (left, bas)
        return (left, max(0, min(bas, max(0, hauteur - 34))))

    def _default_text(self, cls):
        return {"QLabel": "Label", "QPushButton": "Bouton",
                "QCheckBox": "Case a cocher",
                "QRadioButton": "Bouton radio"}.get(cls, "")

    def _default_size(self, cls):
        return {"QLabel":       (120, 22),
                "QPushButton":  (90,  26),
                "QLineEdit":    (150, 22),
                "QTextEdit":    (200, 80),
                "QCheckBox":    (130, 20),
                "QRadioButton": (130, 20),
                "QComboBox":    (150, 22),
                "QListWidget":  (160, 100),
                "QTableWidget": (260, 120)}.get(cls, (120, 28))

    # ── Rafraichissement ─────────────────────────────────────

    def _refresh(self):
        for child in self.ui_frame.winfo_children():
            child.destroy()
        _, _, rw, rh = self.root_geometry
        self.ui_frame.config(width=rw, height=rh)
        self._shadow.config(width=rw + 4, height=rh + 4)
        for i, (cls, props) in enumerate(self.widgets_data):
            self._draw_widget(i, cls, props)
        self.ui_frame.update_idletasks()
        self.canvas.configure(scrollregion=(0, 0, rw + 44, rh + 44))

    def _draw_widget(self, idx, cls, props):
        x, y, w, h = props.get("geometry", (10, 10, 100, 30))
        sel = (idx == self.selected_idx)
        bd  = 2 if sel else 0

        # Name label above the widget
        lbl = tk.Label(self.ui_frame,
                       text=props.get("name", ""),
                       bg="#d0e8ff" if sel else "#e8e8e8",
                       fg="#0055aa" if sel else "#888",
                       font=("TkDefaultFont", 7), anchor="w")
        lbl._widget_idx = idx
        lbl._is_outer   = False
        lbl._is_label   = True
        lbl.place(x=x, y=max(0, y - 14), width=w, height=14)

        # Outer selection frame
        outer = tk.Frame(self.ui_frame,
                         bg=QT_SEL if sel else QT_BG,
                         cursor="fleur")
        outer._widget_idx = idx
        outer._is_outer   = True
        outer._is_label   = False
        outer.place(x=x - bd, y=y - bd,
                    width=w + 2*bd, height=h + 2*bd)

        inner = self._make_qt_widget(outer, cls, props, w, h)
        if inner:
            inner.place(x=bd, y=bd, width=w, height=h)

        # Resize handles (selected only)
        if sel:
            for hx, hy, corner in [(x+w-5, y+h-5, "se"),
                                    (x-5,   y+h-5, "sw"),
                                    (x+w-5, y-5,   "ne")]:
                hdl = tk.Frame(self.ui_frame, bg=QT_SEL,
                               width=9, height=9, cursor="sizing")
                hdl._widget_idx = idx
                hdl._is_outer   = False
                hdl._is_label   = False
                hdl.place(x=hx, y=hy, width=9, height=9)
                hdl.bind("<Button-1>",
                         lambda e, i=idx, c=corner:
                             self._resize_start(e, i, c))
                hdl.bind("<B1-Motion>",
                         lambda e, i=idx, c=corner:
                             self._resize_drag(e, i, c))
                hdl.bind("<ButtonRelease-1>",
                         lambda e, i=idx:
                             self._resize_end(e, i))

        # Bind drag on every part of the widget
        all_parts = ([outer, lbl] +
                     ([inner] + list(inner.winfo_children()) if inner else []))
        for t in all_parts:
            t.bind("<Button-1>",
                   lambda e, i=idx: self._on_click(e, i))
            t.bind("<B1-Motion>",
                   lambda e, i=idx: self._on_drag(e, i))
            t.bind("<ButtonRelease-1>",
                   lambda e, i=idx: self._on_drag_end(e, i))

    # ── Rendu quasi-reel Qt ──────────────────────────────────

    def _tk_font(self, fp):
        fam   = fp.get("family", "") or "TkDefaultFont"
        fsize = max(6, fp.get("size", 9))
        style = []
        if fp.get("bold"):   style.append("bold")
        if fp.get("italic"): style.append("italic")
        return (fam, fsize) + (tuple(style) if style else ())

    def _parse_ss(self, ss):
        fg = bg = None
        for part in (ss or "").split(";"):
            part = part.strip()
            if part.startswith("color:"):
                fg = part.split(":", 1)[1].strip()
            elif "background-color:" in part:
                bg = part.split(":", 1)[1].strip()
            elif part.startswith("background:"):
                bg = part.split(":", 1)[1].strip()
        return fg, bg

    def _make_qt_widget(self, parent, cls, props, w, h):
        text  = props.get("text", "")
        items = props.get("items", [])
        fp    = props.get("font", {"size": 9})
        ss    = props.get("styleSheet", "")
        font  = self._tk_font(fp)
        fg, bg = self._parse_ss(ss)

        if cls == "QLabel":
            return tk.Label(parent, text=text, anchor="w",
                            font=font, fg=fg or QT_FG,
                            bg=bg or QT_BG, padx=3)

        elif cls == "QPushButton":
            btn_bg = bg or QT_BTN
            f = tk.Frame(parent, bg=btn_bg,
                         highlightbackground=QT_BTN_BD,
                         highlightthickness=1)
            tk.Label(f, text=text, font=font, fg=fg or QT_FG,
                     bg=btn_bg, anchor="center").place(
                x=0, y=0, relwidth=1, relheight=1)
            return f

        elif cls == "QLineEdit":
            entry_bg = bg or QT_ENTRY_BG
            f = tk.Frame(parent, bg=entry_bg,
                         highlightbackground=QT_ENTRY_BD,
                         highlightthickness=1)
            e = tk.Entry(f, font=font, fg=fg or QT_FG,
                         bg=entry_bg, relief=tk.FLAT, bd=0,
                         insertbackground="#000")
            ph = props.get("placeholderText", "")
            if text:
                e.insert(0, text)
            elif ph:
                e.insert(0, ph)
                e.config(fg="#aaa")
            e.pack(fill=tk.BOTH, expand=True, padx=3, pady=1)
            return f

        elif cls == "QTextEdit":
            te_bg = bg or QT_ENTRY_BG
            f = tk.Frame(parent, bg=te_bg,
                         highlightbackground=QT_ENTRY_BD,
                         highlightthickness=1)
            t = tk.Text(f, font=font, fg=fg or QT_FG,
                        bg=te_bg, relief=tk.FLAT, bd=0,
                        wrap=tk.WORD, insertbackground="#000")
            if text:
                t.insert("1.0", text)
            vs = ttk.Scrollbar(f, orient=tk.VERTICAL, command=t.yview)
            t.configure(yscrollcommand=vs.set)
            vs.pack(side=tk.RIGHT, fill=tk.Y)
            t.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
            return f

        elif cls == "QCheckBox":
            v = tk.BooleanVar(value=props.get("checked", False))
            return tk.Checkbutton(parent, text=text, variable=v,
                                  font=font, fg=fg or QT_FG,
                                  bg=bg or QT_BG,
                                  activebackground=bg or QT_BG,
                                  selectcolor=QT_ENTRY_BG, anchor="w")

        elif cls == "QRadioButton":
            v = tk.BooleanVar(value=props.get("checked", False))
            return tk.Radiobutton(parent, text=text, variable=v, value=True,
                                  font=font, fg=fg or QT_FG,
                                  bg=bg or QT_BG,
                                  activebackground=bg or QT_BG,
                                  selectcolor=QT_ENTRY_BG, anchor="w")

        elif cls == "QComboBox":
            f = tk.Frame(parent, bg=bg or QT_ENTRY_BG,
                         highlightbackground=QT_ENTRY_BD,
                         highlightthickness=1)
            cb = ttk.Combobox(f, values=items, font=font, state="readonly")
            if items:
                cb.set(items[0])
            cb.pack(fill=tk.BOTH, expand=True)
            return f

        elif cls == "QListWidget":
            f = tk.Frame(parent, bg=bg or QT_ENTRY_BG,
                         highlightbackground=QT_ENTRY_BD,
                         highlightthickness=1)
            lb = tk.Listbox(f, font=font, fg=fg or QT_FG,
                            bg=bg or QT_ENTRY_BG,
                            selectbackground=QT_SEL,
                            selectforeground=QT_SEL_TXT,
                            relief=tk.FLAT, bd=0, activestyle="none")
            for it in items:
                lb.insert(tk.END, it)
            vs = ttk.Scrollbar(f, orient=tk.VERTICAL, command=lb.yview)
            lb.configure(yscrollcommand=vs.set)
            vs.pack(side=tk.RIGHT, fill=tk.Y)
            lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            return f

        elif cls == "QTableWidget":
            rows = max(1, props.get("rows", 3))
            cols = max(1, props.get("columns", 3))
            return self._make_table(parent, rows, cols, font)

        return tk.Label(parent, text=f"[{cls}]",
                        bg=QT_BG, fg="#888", font=font,
                        relief=tk.GROOVE, anchor="center")

    def _make_table(self, parent, rows, cols, font):
        f = tk.Frame(parent, bg=QT_ENTRY_BG,
                     highlightbackground=QT_ENTRY_BD,
                     highlightthickness=1)
        tk.Label(f, bg="#e0e0e0", relief=tk.GROOVE, bd=1,
                 width=2).grid(row=0, column=0, sticky="nsew")
        for c in range(cols):
            tk.Label(f, text=str(c + 1), bg="#e0e0e0", fg="#444",
                     font=font, relief=tk.GROOVE, bd=1,
                     width=6, anchor="center").grid(
                row=0, column=c + 1, sticky="nsew")
        for r in range(rows):
            tk.Label(f, text=str(r + 1), bg="#e8e8e8", fg="#444",
                     font=font, relief=tk.GROOVE, bd=1,
                     width=2, anchor="center").grid(
                row=r + 1, column=0, sticky="nsew")
            for c in range(cols):
                tk.Label(f, text="", bg=QT_ENTRY_BG,
                         relief=tk.GROOVE, bd=1, width=6).grid(
                    row=r + 1, column=c + 1, sticky="nsew")
        for c in range(cols + 1):
            f.columnconfigure(c, weight=1)
        for r in range(rows + 1):
            f.rowconfigure(r, weight=1)
        return f

    # ── Drag / resize ────────────────────────────────────────
    # Approach: bind <B1-Motion> and <ButtonRelease-1> on every widget
    # part using add='+' so existing Tkinter bindings are not replaced.
    # Use a simple is_dragging / is_resizing flag checked on every event.
    # No grab_set() — it fights with Thonny's own event handling.

    def _on_click(self, event, idx):
        self._select(idx)
        _, props = self.widgets_data[idx]
        gx, gy, gw, gh = props.get("geometry", (0, 0, 100, 30))
        # l'etat d'avant le geste n'est journalise que si le geste deplace
        # vraiment quelque chose : un simple clic ne doit pas couter un Annuler
        self._gesture = (idx, props.get("geometry"), self._state())
        self._active_drag   = idx
        self._active_resize = None
        self._drag_origin   = {idx: (event.x_root, event.y_root, gx, gy)}

    def _on_drag(self, event, idx):
        if self._active_drag != idx:
            return
        ox, oy, gx, gy = self._drag_origin[idx]
        dx = event.x_root - ox
        dy = event.y_root - oy
        if dx == 0 and dy == 0:
            return
        _, props = self.widgets_data[idx]
        _, _, gw, gh = props.get("geometry", (0, 0, 100, 30))
        nx, ny = max(0, gx + dx), max(0, gy + dy)
        props["geometry"] = (nx, ny, gw, gh)
        self._info_lbl.config(
            text=f"  {props['name']}  x:{nx}  y:{ny}  w:{gw}  h:{gh}")
        self._move_outer_frame(idx, nx, ny, gw, gh)

    def _on_drag_end(self, event, idx):
        if self._active_drag != idx:
            return
        self._active_drag = None
        self._drag_origin.clear()
        self.selected_idx = idx
        self._commit_gesture()
        self._refresh()
        self._show_properties(idx)

    def _resize_start(self, event, idx, corner):
        _, props = self.widgets_data[idx]
        self._gesture = (idx, props.get("geometry"), self._state())
        self._active_resize = {
            "idx":    idx,
            "corner": corner,
            "ox":     event.x_root,
            "oy":     event.y_root,
            "geom":   props.get("geometry", (0, 0, 100, 30)),
        }
        self._active_drag = None
        self._drag_origin.clear()

    def _resize_drag(self, event, idx, corner):
        ri = self._active_resize
        if ri is None or ri["idx"] != idx:
            return
        dx = event.x_root - ri["ox"]
        dy = event.y_root - ri["oy"]
        gx, gy, gw, gh = ri["geom"]
        if corner == "se":
            nw, nh = max(20, gw + dx), max(14, gh + dy)
        elif corner == "sw":
            nw, nh = max(20, gw - dx), max(14, gh + dy)
        else:
            nw, nh = max(20, gw + dx), max(14, gh - dy)
        _, props = self.widgets_data[idx]
        props["geometry"] = (gx, gy, int(nw), int(nh))
        self._info_lbl.config(
            text=f"  {props['name']}  w:{int(nw)}  h:{int(nh)}")
        self._move_outer_frame(idx, gx, gy, int(nw), int(nh))

    def _resize_end(self, event, idx):
        if self._active_resize is None or self._active_resize["idx"] != idx:
            return
        self._active_resize = None
        self.selected_idx = idx
        self._commit_gesture()
        self._refresh()
        self._show_properties(idx)

    def _move_outer_frame(self, idx, nx, ny, gw, gh):
        """Move/resize the outer frame in place without a full rebuild."""
        bd = 2
        for child in self.ui_frame.winfo_children():
            if getattr(child, "_widget_idx", None) == idx:
                if getattr(child, "_is_outer", False):
                    child.place(x=nx - bd, y=ny - bd,
                                width=gw + 2*bd, height=gh + 2*bd)
                elif getattr(child, "_is_label", False):
                    child.place(x=nx, y=max(0, ny - 14), width=gw)

    def _select(self, idx):
        # changer de cible clot l'edition en cours : deux champs distincts
        # ne doivent pas se retrouver dans le meme pas d'annulation
        self._edit_sig = None
        self.selected_idx = idx
        self._refresh()
        self._show_properties(idx)

    def _deselect(self):
        self._edit_sig = None
        self.selected_idx = None
        self._refresh()
        self._show_no_selection()

    # ── Panneau proprietes ───────────────────────────────────

    def _clear_props(self):
        for c in self.prop_frame.winfo_children():
            c.destroy()
        self._prop_vars.clear()
        self._name_entry = None       # les widgets viennent d'etre detruits
        self._name_hint = None

    def _bind_prop_scroll(self):
        """Propagate mousewheel to the prop canvas for all children."""
        def _mw(e):
            if e.num == 4:
                self._prop_canvas.yview_scroll(-1, "units")
            elif e.num == 5:
                self._prop_canvas.yview_scroll(1, "units")
            else:
                self._prop_canvas.yview_scroll(
                    int(-1 * (e.delta / 120)), "units")

        def _bind_recursive(w):
            w.bind("<MouseWheel>", _mw, add="+")
            w.bind("<Button-4>",   _mw, add="+")
            w.bind("<Button-5>",   _mw, add="+")
            for child in w.winfo_children():
                _bind_recursive(child)

        _bind_recursive(self.prop_frame)

    def _show_no_selection(self):
        self._clear_props()
        tk.Label(self.prop_frame,
                 text="Cliquez sur un widget\npour le selectionner",
                 bg=PROP_BG, fg="#555",
                 font=("TkDefaultFont", 8), justify="center").pack(pady=20)
        self._bind_prop_scroll()

    def _section(self, title):
        tk.Label(self.prop_frame, text=" " + title,
                 bg=PANEL_HDR, fg="#666",
                 font=("TkDefaultFont", 7, "bold"),
                 anchor="w", pady=3).pack(fill=tk.X, pady=(6, 0))

    def _row_frame(self, label, row_idx=0):
        bg = PROP_EVEN if row_idx % 2 == 0 else PROP_ODD
        row = tk.Frame(self.prop_frame, bg=bg)
        row.pack(fill=tk.X)
        tk.Label(row, text=label, bg=bg, fg=PROP_FG2,
                 font=("TkDefaultFont", 8), width=12,
                 anchor="w", padx=6).pack(side=tk.LEFT)
        return row, bg

    def _entry_field(self, label, var, row_idx=0):
        row, bg = self._row_frame(label, row_idx)
        e = tk.Entry(row, textvariable=var,
                     bg="#3c3c3c", fg=PROP_FG,
                     insertbackground=PROP_FG,
                     relief=tk.FLAT, bd=0,
                     font=("TkDefaultFont", 8))
        e.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=4, pady=2)
        return e

    def _color_field(self, label, color, on_pick, row_idx=0):
        row, bg = self._row_frame(label, row_idx)
        preview = tk.Label(row, bg=color or "#888",
                           width=3, relief=tk.GROOVE, bd=1)
        preview.pack(side=tk.LEFT, padx=(0, 4), pady=2)
        val_lbl = tk.Label(row, text=color or "---", bg=bg,
                           fg=PROP_FG, font=("Courier", 7))
        val_lbl.pack(side=tk.LEFT)
        btn = tk.Label(row, text=" ... ", bg="#3c3c3c", fg=PROP_FG,
                       cursor="hand2", font=("TkDefaultFont", 8))
        btn.pack(side=tk.RIGHT, padx=4)
        btn.bind("<Button-1>", lambda e: on_pick(preview, val_lbl))

    def _show_properties(self, idx):
        self._clear_props()
        if idx >= len(self.widgets_data):
            return
        cls, props = self.widgets_data[idx]
        fp = props.get("font", {"size": 9, "bold": False,
                                "italic": False, "family": ""})
        fg, bg_col = self._parse_ss(props.get("styleSheet", ""))
        ri = [0]

        def R():
            ri[0] += 1
            return ri[0]

        # En-tete
        icon = next((d[2] for d in WIDGET_DEFS if d[0] == cls), "?")
        hdr = tk.Frame(self.prop_frame, bg="#0d2a45")
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f" {icon}  {cls}", bg="#0d2a45", fg="#7ab8f5",
                 font=("TkDefaultFont", 9, "bold"), anchor="w",
                 pady=4, padx=6).pack(fill=tk.X)
        tk.Label(hdr, text=f"  {props.get('name', '')}",
                 bg="#0d2a45", fg="#557799",
                 font=("Courier", 8), anchor="w", pady=2).pack(fill=tk.X)

        # Identification
        self._section("IDENTIFICATION")
        v_name = tk.StringVar(value=props.get("name", ""))
        self._prop_vars["name"] = v_name
        self._name_entry = self._entry_field("Nom", v_name, R())
        self._name_hint = tk.Label(self.prop_frame, text="", bg=PROP_BG,
                                   fg="#ff9a9a", font=("TkDefaultFont", 7),
                                   anchor="w", justify=tk.LEFT)
        self._name_hint.pack(fill=tk.X, padx=8, pady=(0, 3))
        v_name.trace_add("write",
            lambda *_: self._apply("name", v_name, idx, str))

        # Geometrie
        self._section("GEOMETRIE")
        gx, gy, gw, gh = props.get("geometry", (0, 0, 100, 30))
        for lbl, key, val in [("X", "geo_x", gx), ("Y", "geo_y", gy),
                               ("Largeur", "geo_w", gw), ("Hauteur", "geo_h", gh)]:
            v = tk.StringVar(value=str(val))
            self._prop_vars[key] = v
            self._entry_field(lbl, v, R())
            v.trace_add("write",
                lambda *_, k=key, vv=v, i=idx: self._apply_geom(k, vv, i))

        # Contenu
        if cls in ("QLabel", "QPushButton", "QCheckBox",
                   "QRadioButton"):
            self._section("CONTENU")
            v_txt = tk.StringVar(value=props.get("text", ""))
            self._prop_vars["text"] = v_txt
            self._entry_field("Texte", v_txt, R())
            v_txt.trace_add("write",
                lambda *_: self._apply("text", v_txt, idx, str))

        if cls == "QLineEdit":
            self._section("CONTENU")
            v_ph = tk.StringVar(value=props.get("placeholderText", ""))
            self._prop_vars["placeholderText"] = v_ph
            self._entry_field("Placeholder", v_ph, R())
            v_ph.trace_add("write",
                lambda *_: self._apply("placeholderText", v_ph, idx, str))

        if cls in ("QComboBox", "QListWidget"):
            self._section("ELEMENTS (un par ligne)")
            txt_items = tk.Text(self.prop_frame, height=5,
                                bg="#3c3c3c", fg=PROP_FG,
                                insertbackground=PROP_FG,
                                font=("Courier", 8), relief=tk.FLAT, bd=0)
            txt_items.insert("1.0", "\n".join(props.get("items", [])))
            txt_items.pack(fill=tk.X, padx=6, pady=2)

            def on_items(_e=None):
                content = txt_items.get("1.0", tk.END).strip()
                _, p = self.widgets_data[idx]
                p["items"] = [l.strip() for l in content.splitlines()
                              if l.strip()]
                self._soft_refresh(idx)
            txt_items.bind("<KeyRelease>", on_items)

        if cls == "QTableWidget":
            self._section("TABLEAU")
            for lbl, key, val in [
                    ("Lignes",   "rows",    props.get("rows",    3)),
                    ("Colonnes", "columns", props.get("columns", 3))]:
                v = tk.StringVar(value=str(val))
                self._prop_vars[key] = v
                self._entry_field(lbl, v, R())
                v.trace_add("write",
                    lambda *_, k=key, vv=v, i=idx: self._apply(k, vv, i, int))

        if cls in ("QCheckBox", "QRadioButton"):
            self._section("ETAT")
            row, bg = self._row_frame("Coche", R())
            v_chk = tk.BooleanVar(value=props.get("checked", False))
            self._prop_vars["checked"] = v_chk
            tk.Checkbutton(row, variable=v_chk, bg=bg,
                           selectcolor="#3c3c3c", activebackground=bg,
                           command=lambda: self._apply(
                               "checked", v_chk, idx, bool)).pack(
                side=tk.LEFT, padx=6)

        # Police
        self._section("POLICE")
        v_fam = tk.StringVar(value=fp.get("family", ""))
        self._prop_vars["font_family"] = v_fam
        self._entry_field("Famille", v_fam, R())
        v_fam.trace_add("write",
            lambda *_: self._apply_font("family", v_fam, idx))

        v_fsize = tk.StringVar(value=str(fp.get("size", 9)))
        self._prop_vars["font_size"] = v_fsize
        self._entry_field("Taille (pt)", v_fsize, R())
        v_fsize.trace_add("write",
            lambda *_: self._apply_font_size(v_fsize, idx))

        row_b, bg_b = self._row_frame("Style", R())
        v_bold   = tk.BooleanVar(value=fp.get("bold",   False))
        v_italic = tk.BooleanVar(value=fp.get("italic", False))
        self._prop_vars["bold"]   = v_bold
        self._prop_vars["italic"] = v_italic
        for txt_chk, var_chk, key_chk in [
                ("Gras",     v_bold,   "bold"),
                ("Italique", v_italic, "italic")]:
            tk.Checkbutton(row_b, text=txt_chk, variable=var_chk,
                           bg=bg_b, fg=PROP_FG,
                           selectcolor="#3c3c3c", activebackground=bg_b,
                           font=("TkDefaultFont", 8),
                           command=lambda k=key_chk, v=var_chk:
                               self._apply_font(k, v, idx, bool)).pack(
                side=tk.LEFT, padx=4)

        # Couleurs
        self._section("COULEURS")

        def pick_fg(preview, lbl):
            c = colorchooser.askcolor(color=fg,
                                      title="Couleur du texte")[1]
            if c:
                self._set_color(idx, "color", c)
                preview.config(bg=c)
                lbl.config(text=c)

        def pick_bg(preview, lbl):
            c = colorchooser.askcolor(color=bg_col,
                                      title="Couleur de fond")[1]
            if c:
                self._set_color(idx, "background-color", c)
                preview.config(bg=c)
                lbl.config(text=c)

        self._color_field("Texte", fg, pick_fg, R())
        self._color_field("Fond",  bg_col, pick_bg, R())

        # Methodes
        self._section("METHODES")
        wname = props.get("name", "obj")
        for i, (desc, template, needed) in enumerate(WIDGET_METHODS.get(cls, [])):
            code = template.format(obj="windows." + wname, name=wname)
            shown = code if len(code) <= 46 else code[:43] + "..."
            bg_m = PROP_EVEN if i % 2 == 0 else PROP_ODD
            mrow = tk.Frame(self.prop_frame, bg=bg_m)
            mrow.pack(fill=tk.X)
            tk.Label(mrow, text="  " + shown, bg=bg_m, fg="#7ab8f5",
                     font=("Courier", 7), anchor="w").pack(
                side=tk.LEFT, fill=tk.X, expand=True, pady=3)
            copy_lbl = tk.Label(mrow, text=" cp ", bg=bg_m, fg="#555",
                                cursor="hand2", font=("TkDefaultFont", 7))
            copy_lbl.pack(side=tk.RIGHT, padx=6)
            for w in (mrow, copy_lbl):
                w.bind("<Button-1>",
                       lambda e, c=code, imp=needed: self._copy_code(c, imp))
                w.bind("<Enter>", lambda e, mr=mrow: mr.config(bg="#2a3a5a"))
                w.bind("<Leave>", lambda e, mr=mrow, b=bg_m: mr.config(bg=b))
            self._tooltip(mrow, f"{desc} — inserer : {code}")

        # Boutons
        tk.Frame(self.prop_frame, bg=SEP_COL, height=1).pack(
            fill=tk.X, pady=8)
        btn_row = tk.Frame(self.prop_frame, bg=PROP_BG)
        btn_row.pack(fill=tk.X, padx=6, pady=(0, 8))

        def mk_btn(par, txt, cmd, fg_c, bg_c, bg_h):
            b = tk.Label(par, text=txt, bg=bg_c, fg=fg_c,
                         font=("TkDefaultFont", 8),
                         pady=5, cursor="hand2", anchor="center")
            b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>",    lambda e: b.config(bg=bg_h))
            b.bind("<Leave>",    lambda e: b.config(bg=bg_c))

        mk_btn(btn_row, "Supprimer", lambda: self._delete(idx),
               "#ffaaaa", "#5a1a1a", "#7a2a2a")
        mk_btn(btn_row, "Dupliquer", lambda: self._duplicate(idx),
               "#aaccff", "#1a3a5a", "#2a4a7a")

        # Scroll back to top and bind mousewheel on all new children
        self._prop_canvas.yview_moveto(0)
        self._bind_prop_scroll()

    # ── Application proprietes ───────────────────────────────

    def _apply(self, key, var, idx, cast=str):
        try:
            _, props = self.widgets_data[idx]
            value = cast(var.get())
            if key == "name" and not self._accept_name(value, idx):
                return          # le modele garde le dernier nom valide
            if props.get(key) == value:
                return          # rien n'a change : rien a annuler
            self._record(("champ", key, idx))
            props[key] = value
            self._soft_refresh(idx)
        except (ValueError, IndexError):
            pass

    def _accept_name(self, name, idx):
        """N'enregistre un nom saisi que s'il est libre et valide ; le champ
        se colore et s'explique au lieu d'etre efface pendant la frappe."""
        problem = self._name_problem(name, idx)
        entry = getattr(self, "_name_entry", None)
        if entry is not None:
            try:
                entry.config(bg="#5a1a1a" if problem else "#3c3c3c")
            except tk.TclError:
                self._name_entry = None       # le panneau a ete reconstruit
        hint = getattr(self, "_name_hint", None)
        if hint is not None:
            try:
                hint.config(text=problem)
            except tk.TclError:
                self._name_hint = None
        return not problem

    def _name_troubles(self):
        """Liste des noms d'objets qui rendraient le fichier inutilisable."""
        vus = {}
        for _, props in self.widgets_data:
            vus.setdefault(props.get("name", ""), []).append(props)
        problems = []
        for name, group in vus.items():
            if not name:
                problems.append("un widget sans nom")
            elif not self._valid_qt_name(name):
                problems.append(f"{name} : lettres, chiffres et « _ » uniquement")
            elif len(group) > 1:
                problems.append(f"{name} : {len(group)} widgets portent ce nom")
        return problems

    def _apply_geom(self, key, var, idx):
        try:
            val = int(var.get())
            _, props = self.widgets_data[idx]
            g = list(props.get("geometry", (0, 0, 100, 30)))
            g[{"geo_x": 0, "geo_y": 1, "geo_w": 2, "geo_h": 3}[key]] = max(0, val)
            if tuple(g) == tuple(props.get("geometry", ())):
                return
            self._record(("champ", key, idx))
            props["geometry"] = tuple(g)
            self._soft_refresh(idx)
        except (ValueError, KeyError, IndexError):
            pass

    def _apply_font(self, key, var, idx, cast=str):
        try:
            _, props = self.widgets_data[idx]
            fp = dict(props.get("font", {}))
            fp[key] = cast(var.get())
            if fp == props.get("font", {}):
                return
            self._record(("champ", ("font", key), idx))
            props["font"] = fp
            self._soft_refresh(idx)
        except (ValueError, IndexError):
            pass

    def _apply_font_size(self, var, idx):
        try:
            _, props = self.widgets_data[idx]
            fp = dict(props.get("font", {}))
            fp["size"] = max(4, int(var.get()))
            if fp == props.get("font", {}):
                return
            self._record(("champ", ("font", "size"), idx))
            props["font"] = fp
            self._soft_refresh(idx)
        except (ValueError, IndexError):
            pass

    def _set_color(self, idx, css_prop, color):
        _, props = self.widgets_data[idx]
        ss = props.get("styleSheet", "")
        lines = [l for l in ss.split(";")
                 if l.strip() and css_prop + ":" not in l]
        lines.append(f"{css_prop}: {color}")
        nouveau = "; ".join(lines) + ";"
        if nouveau != ss:
            self._record(("champ", ("couleur", css_prop), idx))
            props["styleSheet"] = nouveau
            self._soft_refresh(idx)

    def _soft_refresh(self, idx):
        self.selected_idx = idx
        self._refresh()

    # ── Actions ──────────────────────────────────────────────

    def _delete(self, idx):
        if messagebox.askyesno("Supprimer", "Supprimer ce widget ?"):
            self._step()
            del self.widgets_data[idx]
            self.selected_idx = None
            self._refresh()
            self._show_no_selection()

    def _duplicate(self, idx):
        cls, props = self.widgets_data[idx]
        new_props = copy.deepcopy(props)
        # la copie n'a pas d'element XML d'origine : elle sera ajoutee en propre
        for bookkeeping in ("_uid", "_src", "_est"):
            new_props.pop(bookkeeping, None)
        # on garde la famille du nom copie (btnValider -> btnValider1) jusqu'a
        # ce que le nom soit libre : un nom duplique casserait windows.<nom>
        short = cls.replace("Q", "").lower()
        stem = props.get("name", "").rstrip("0123456789") or short
        new_props["name"] = self._unique_name(stem)
        gx, gy, gw, gh = props.get("geometry", (0, 0, 100, 30))
        new_props["geometry"] = (gx + 20, gy + 20, gw, gh)
        self._step()
        self.widgets_data.append((cls, new_props))
        self._refresh()
        self._select(len(self.widgets_data) - 1)

    def _editor_text(self):
        """Le Text de l'editeur courant, ou None s'il n'y en a pas."""
        try:
            editor = get_workbench().get_editor_notebook().get_current_editor()
            return editor.get_code_view().text if editor else None
        except Exception:
            return None

    def _copy_code(self, code, import_line=""):
        """Copie une ligne proposee et l'insere a la position du curseur.

        Une ligne qui cite une classe que loadUi ne cree pas (QTableWidgetItem)
        emporte son import : colle sans lui, elle echoue, ce qui etait le cas de
        toutes les lignes proposees ici. Le presse-papiers
        garde la version autonome ; le fichier, lui, ne recoit l'import qu'une
        fois et en tete, la ou il a sa place."""
        text = self._editor_text()
        needed = ""
        if import_line:
            cls = import_line.rsplit(None, 1)[-1]
            pattern = re.compile(
                r"(?m)^[ \t]*(?:from[ \t]+\S+[ \t]+)?import\b[^\n]*\b%s\b" % cls)
            try:
                source = text.get("1.0", "end") if text is not None else ""
            except tk.TclError:
                source, text = "", None
            if not pattern.search(source):
                needed = import_line
        self.clipboard_clear()
        self.clipboard_append(f"{needed}\n{code}" if needed else code)
        if text is None:
            return
        try:
            if needed:
                text.insert("1.0", needed + "\n")
            text.insert("insert", own_line(text, code))
            text.see("insert")
        except tk.TclError:
            pass

    # ── Utilitaires ──────────────────────────────────────────

    def _on_canvas_resize(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _tooltip(self, widget, text):
        tip = None

        def show(e):
            nonlocal tip
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{e.x_root + 14}+{e.y_root + 10}")
            tk.Label(tip, text=text, bg="#1e1e1e", fg="#d4d4d4",
                     relief=tk.FLAT, bd=0, padx=6, pady=3,
                     font=("TkDefaultFont", 8)).pack()

        def hide(_e):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)