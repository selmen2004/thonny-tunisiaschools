import os
import copy
import re
import keyword
import colorsys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from xml.etree import ElementTree as ET
from thonny import get_workbench

# ── Palette Qt Fusion ────────────────────────────────────────
QT_BG         = "#f0f0f0"
QT_BTN        = "#e1e1e1"
QT_BTN_BD     = "#adadad"
QT_ENTRY_BG   = "#ffffff"
QT_ENTRY_BD   = "#b0b0b0"
QT_FG         = "#000000"
QT_SEL        = "#0078d7"
QT_SEL_TXT    = "#ffffff"

# Roles de palette que Qt ecrit parfois a la place d'une couleur —
# `background-color: palette(base)` — et leur teinte d'apercu. Le nom est
# cherche sans ses tirets bas, parce que Qt en accepte les deux orthographes.
# Un role absent d'ici rend None : la teinte habituelle du widget vaut mieux
# qu'une fenetre qui refuse de s'ouvrir.
_PALETTES_TK = {
    "window":        QT_BG,
    "windowtext":    QT_FG,
    "text":          QT_FG,
    "foreground":    QT_FG,
    "brighttext":    "#ff0000",
    "base":          QT_ENTRY_BG,
    "alternatebase": "#f7f7f7",
    "button":        QT_BTN,
    "buttontext":    QT_FG,
    "highlight":     QT_SEL,
    "highlightedtext": QT_SEL_TXT,
    "placeholdertext": "#aaaaaa",
    "placeholder":   "#aaaaaa",
    "link":          "#0000ff",
    "tooltipbase":   "#ffffdc",
    "tooltiptext":   QT_FG,
    "light":         "#eeeeee",
    "midlight":      "#cccccc",
    "dark":          "#333333",
    "mid":           "#808080",
    "shadow":        "#555555",
}

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
        self._taille_champs     = {}        # les champs « Lignes » et « Colonnes »
        self._taille_hint       = None      # et son explication, quand un nombre
                                            # refuse ne s'est pas ecrit
        self._active_drag       = None
        self._active_resize     = None
        self._glissement        = None      # (idx, place visee) d'un reclassement
        self._repere            = None      # le trait bleu qui l'annonce
        # Identite de la fenetre d'un document neuf : nom, classe, taille, titre.
        # Un seul endroit la decide (voir _racine_neuve), parce que le
        # constructeur et « Nouveau » doivent poser la MEME fenetre vide.
        self._racine_neuve()
        # Arbre XML d'origine : sert a rendre le fichier tel quel a l'enregistrement
        self._source_ui         = None
        self._source_uids       = []
        self._src_root          = {}
        # Journal des modifications : une copie du modele par pas d'annulation
        self._undo_stack        = []
        self._redo_stack        = []
        self._edit_sig          = None      # derniere cible editee (regroupement)
        self._gesture           = None      # etat avant un glisser / redimensionner
        # Le travail en cours ne correspond-il plus au fichier ? Voir
        # _travail_non_enregistre() : c'est ce drapeau qui decide si « Ouvrir »
        # et « Nouveau » doivent prevenir avant d'effacer l'ecran.
        self._travail_modifie   = False
        self._build_ui()
        # Premiere peinture du document : tant qu'aucun ecrivain n'a pose la zone
        # defilable, la propriete reste vide ('') et le canevas ne defile pas du
        # tout — l'eleve ne verrait pas le bas de sa forme par defaut.
        self._refresh()
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
        # PAS de handler <Configure> ici : la zone defilable suit le document,
        # pas la taille du viewport — voir _zone_defilable().
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
    # _travail_modifie n'est PAS dans STATE_KEYS, et c'est important : une
    # entree de journal copie l'etat AVANT la modification, donc au premier pas
    # elle copie « non modifie ». Remettre ce drapeau a son valeur archivee a
    # chaque Annuler effacerait l'alerte alors que l'ecran ne correspond toujours
    # pas au fichier — l'eleve ouvrirait un autre fichier sans qu'on le lui dise.
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
        # Tout passage par ici est un pas fait par-dessus le fichier : un ajout,
        # une suppression, un renommage, un deplace. Le modele ne correspond plus
        # a ce qui est sur le disque, et c'est durable jusqu'a la prochaine
        # ecriture ou la prochaine lecture (voir _save et reset_history).
        self._travail_modifie = True
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
        # Appelle quand un document remplace l'ancien (lecture d'un fichier,
        # Nouveau) : le journal repart de zero et l'ecran correspond de nouveau
        # a quelque chose de consigne, donc il n'y a plus rien a prevenir.
        self._undo_stack = []
        self._redo_stack = []
        self._edit_sig = None
        self._gesture = None
        self._travail_modifie = False
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

    def _travail_non_enregistre(self):
        """Vrai quand l'ecran montre quelque chose que le fichier ne contient pas.

        Le drapeau se leve au premier pas d'historique (_push) et retombe a
        zero a chaque fois que l'ecran et le disque sont de nouveau d'accord :
        apres une ecriture (_save) ou quand un fichier prend la place du
        document en cours (reset_history, appele par la lecture et par Nouveau).

        Le drapeau peut rester leve alors que le contenu ressemble de nouveau au
        fichier — par exemple apres un ajout puis son Annuler. C'est voulu : une
        alerte de trop est une question, un faux « rien a perdre » est un
        travail d'eleve qui disparait.
        """
        return bool(getattr(self, "_travail_modifie", False))

    def _racine_neuve(self):
        """La fenetre d'un document neuf : ce que pose le constructeur, et ce que
        « Nouveau » doit remettre.

        Les deux doivent passer ici, sinon l'un des deux oublie un champ. C'est
        exactement le defaut que cette methode ferme : « Nouveau » vidait les
        widgets, la taille, l'arbre XML et l'historique, mais ne touchait ni
        root_widget_name, ni root_widget_class, ni root_title — les trois champs
        que seul le lecteur d'un fichier connait, puisqu'aucun champ du panneau
        de proprietes n'y atteint. L'eleve ouvrait « Gestion », cliquait Nouveau,
        voyait un canevas vide et un onglet « Sans titre », ajoutait son bouton,
        enregistrait — et son fichier portait <class>MainWindow</class>, une
        <widget class="QMainWindow" name="Gestion"> et le titre
        « Gestion des eleves » (mesure). Le pire n'est pas le nom herite : c'est
        que la taille, elle, etait remise a 640x480, donc le fichier decrivait une
        fenetre qui n'existe nulle part, un QMainWindow sans centralwidget des que
        l'eleve y pose un widget — forme que Qt construit, mais que Designer ne
        produit jamais et ne relit pas comme une fenetre correcte.
        """
        self.root_widget_name = "Form"
        self.root_widget_class = "QDialog"
        self.root_geometry = (0, 0, 640, 480)
        self.root_title = "Form"

    def _new(self):
        if self._travail_non_enregistre() and not messagebox.askyesno(
                "Nouveau", "Effacer le travail en cours ?"):
            return
        self.widgets_data.clear()
        self.ui_file = None
        self.widget_counter = 0
        self.selected_idx = None
        # Toute l'identite de la fenetre repart de zero, pas seulement sa taille :
        # voir _racine_neuve.
        self._racine_neuve()
        self._source_ui = None
        self._source_uids = []
        self._src_root = {}
        self.reset_history()
        self._title_lbl.config(text="Sans titre")
        self._refresh()
        # Le panneau de proprietes lache aussi le widget d'avant. Sans cette
        # ligne, « Nouveau » laissait l'eleve devant les vingt-trois champs du
        # widget supprime (mesure) : le champ « Nom » affichait encore btnQuitter,
        # y taper un nom changeait ce que la boite affichait sans rien ecrire
        # nulle part — le modele etait vide, et _apply avalait l'IndexError en
        # silence. L'heritage visible, cette fois : il ne restait pas seulement
        # dans le fichier, il etait sous la main de l'eleve.
        self._show_no_selection()

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
        retirees = self._write_ui_file(self.ui_file)
        # Le fichier vient de rattraper l'ecran : il n'y a plus de travail perdu
        # possible, donc « Ouvrir » et « Nouveau » n'ont plus rien a demander.
        # Les deux branches de retour en amont (noms invalides, fenetre de
        # sauvegarde annulee) laissent le drapeau leve, comme il se doit.
        self._travail_modifie = False
        self._title_lbl.config(text=os.path.basename(self.ui_file))
        if retirees:
            # Le fichier vient de perdre un signal qui pointait vers un widget
            # supprime : a dire, sinon l'eleve cherche longtemps pourquoi son
            # bouton ne reagit plus.
            self._history_notice(
                "Connexions retirées du fichier : %d — elles visaient "
                "un widget supprimé" % retirees)
        messagebox.showinfo("Enregistre", f"Fichier enregistre :\n{self.ui_file}")

    def load_new_ui_file(self, path):
        # Lire d'abord, adopter ensuite. Le fichier n'a le droit de devenir « le
        # fichier en cours » qu'une fois reconnu comme une forme : avant, la vue
        # peut afficher un travail deja commence, et si l'eleve choisit un
        # programme .py par erreur, la version precedente de cette methode
        # notait ce chemin dans self.ui_file avant meme de le lire. Le modele se
        # vidait, l'arbre source restait celui de la fenetre d'avant, et le
        # prochain Enregistrer ecrivait du XML par-dessus le programme de l'eleve.
        #
        # Rien n'est ecrit ici avant que la lecture ait rendu une racine : si le
        # fichier est illisible ou sans fenetre, la vue garde ses widgets, son
        # titre, son fichier et son historique, donc Enregistrer ecrira toujours
        # dans le fichier d'avant. Un plantage en plein parcours (bug du lecteur,
        # pas fichier casse) remonte tel quel a l'appelant, et c'est voulu : le
        # trace back dans la console Thonny est la seule trace du bug, et _parse_ui
        # ne commit rien, donc la fenetre affichee reste intacte.
        #
        # Rend True si le fichier est desormais celui affiche, False sinon
        # (refuse par le lecteur, ou eleve qui renonce) : « Ajouter Annexe +
        # interface » s'en sert pour ne pas reecrire son menu autour d'un
        # fichier qu'il n'a pas ouvert.
        avant = self._state()
        data, root_info = self._parse_ui(path)
        if not root_info:
            return False
        # Le fichier est bon, mais il va remplacer ce que l'eleve a a l'ecran.
        # C'est le seul endroit qui sait les deux a la fois : avant la lecture,
        # on ne savait pas si le fichier existait ; apres, il est trop tard pour
        # demander sans avoir deja vide la vue.
        if self._travail_non_enregistre() and not messagebox.askyesno(
                "Ouvrir", "Le fichier « %s » va remplacer la fenetre affichee.\n\n"
                "Votre travail en cours n'est pas enregistre : enregistrez-le "
                "avant si vous y tenez.\n\nRemplacer quand meme ?"
                % os.path.basename(path)):
            # La lecture, elle, a deja rendu ses reperes : _parse_ui commit
            # l'arbre, les uid, la racine et la graine du fichier lu des qu'il
            # est bon. Sans ce retour en arriere, l'eleve qui repond « non »
            # garde ses widgets a l'ecran mais l'arbre XML de celui qu'il vient
            # de refuser — et son prochain Enregistrer fusionnerait les uns dans
            # l'autre : le nom de la fenetre du fichier refuse par-dessus le
            # travail de l'eleve (mesure, avec la racine de « autre.ui » dans
            # « note.ui »). Le refuse est donc annule comme l'item 3 annule un
            # refus, au meme endroit : les clefs du journal, _source_ui compris.
            self._restore(avant)
            return False
        self.ui_file = path
        self.widgets_data = data
        self.root_geometry = root_info.get("geometry", (0, 0, 640, 480))
        self.root_title    = root_info.get("title", "Form")
        self.selected_idx  = None
        # Le compteur de noms est remonte a partir du fichier par _parse_ui.
        # Un fichier qui s'ouvre n'est pas la suite du precedent : Annuler ne
        # doit jamais faire revivre les widgets de la fenetre d'avant.
        self.reset_history()
        self._title_lbl.config(text=os.path.basename(path))
        self._refresh()
        return True

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

        # Rien de l'etat en cours n'est modifie avant la toute fin de la lecture
        # (voir le bloc de commit) : un fichier refuse doit laisser la fenetre
        # affichee exactement telle qu'elle etait.
        root_elem = tree_root.find("widget")
        if root_elem is None:
            # <ui> bien forme, mais sans forme : root_info reste vide, c'est le
            # signal que l'appelant sait reconnaitre. Le fichier est pourtant
            # reste intact et la fenetre affichee aussi, donc on le dit ici :
            # sinon l'eleve clique sur « Ouvrir », voit la meme fenetre qu'avant,
            # et croit que le plugin n'a rien fait.
            messagebox.showerror("Erreur", "Ce fichier n'est pas une fenetre :\n"
                                 "il ne contient aucun widget a afficher.")
            return data, root_info

        rp = read_props(root_elem)
        root_info["geometry"] = rp.get("geometry", (0, 0, 640, 480))
        root_info["title"]    = rp.get("title", rp.get("windowTitle", "Form"))
        nom_racine    = root_elem.get("name", "Form")
        classe_racine = root_elem.get("class", "QDialog")
        uids_lus      = []

        # Les widgets sont numerotes dans l'ordre du document, layouts compris :
        # ce numero (uid) sert de cle pour retrouver l'element XML a l'enregistrement.
        ordered = self._walk_widgets(root_elem)
        est = self._estimate_geometries(root_elem)
        # Carte des mises en page du fichier : qui range qui, dans quel ordre.
        # On la construit sur l'arbre lu, une fois pour toutes : c'est elle qui
        # dit si un widget est « placé » (et donc si son glisser doit reclasser
        # le layout) plutot que de le deviner a l'absence de <geometry> — un
        # fichier absolu sans geometry porterait le meme jugement faux.
        parents_src = self._parents(tree_root)
        uids_de = {id(el): "w%d" % i for i, el in enumerate(ordered)}
        rangs = {}
        for clef, g in self._carte_des_layouts(tree_root, uids_de)[0].items():
            for rang, (uid, _it, _pos) in enumerate(g["items"]):
                rangs[uid] = (clef, g["axe"], rang)
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
            # Un widget rangé dans un <item> de <layout> est placé par Qt : ce
            # que l'on voit a l'ecran n'est qu'une estimation de ce que le
            # concepteur calculera, pas un fait. _pose le dit, et toute
            # l'edition (glisser, champs X/Y, enregistrement) doit traiter cette
            # position comme n'appartenant pas au widget.
            pose = own is None and \
                self._conteneur_de(w, parents_src) is not None
            props["_pose"] = "layout" if pose else "libre"
            if pose and uid in rangs:
                # la mise en page qui le range, son axe, et la place qu'il y
                # occupe : c'est ce triple que le glisser va changer.
                props["_groupe"], props["_axe"], props["_rang"] = rangs[uid]
            # L'empreinte de reference doit decrire le FICHIER, pas l'ecran :
            # snapshotter apres l'injection de l'estimation ferait croire a
            # l'enregistrement qu'une position libre est deja ecrite, et il n'en
            # poserait jamais la balise <geometry>.
            props["_src"] = self._snapshot(props)
            if own is None and props["_est"]:
                props["geometry"] = props["_est"]
            uids_lus.append(uid)
            data.append((cls, props))

        # ── Commit ───────────────────────────────────────────
        # Tout ce qu'une lecture laisse derriere se pose ici, d'un seul coup, et
        # uniquement quand le fichier a bel et bien ete lu jusqu'au bout. Avant
        # ce bloc, la lecture n'ecrit dans aucun attribut de la vue : un fichier
        # illisible, vide de forme, ou qui ferait planter le parcours laisse donc
        # la fenetre affichee intacte. C'est ce qui empeche un « Ouvrir » rate de
        # rendre ensuite un Enregistrer capable d'ecrire le XML de la fenetre
        # d'avant par-dessus le fichier que l'eleve vient de choisir.
        self.root_widget_name  = nom_racine
        self.root_widget_class = classe_racine
        self._source_ui = tree_root
        self._source_uids = uids_lus
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
            recueil = {}
            root = self._merge_into_source(table=recueil)
            # Le menage des connexions se fait ici et pas dans la fusion : la
            # fusion sert aussi a l'affichage, qui n'a rien a retirer de son
            # arbre. Ecrire, en revanche, doit produire un fichier qui se
            # charge. C'est aussi ici que les connexions suivent un renommage :
            # meme arbre, meme passage, mais apres que la fusion a su qui est
            # mort et qui a change de nom.
            retirees = self._purge_orphelines(root, recueil.get("rennames"),
                                              recueil.get("liberes"))
            # Deuxieme menage du meme arbre, dans l'autre sens : le premier
            # coupait les cables qui ne pointent sur rien, celui-ci rend
            # visibles les objets que le chargeur de l'eleve ne voyait pas.
            # Apres le menage, pour que les survivantes seules soient montees.
            self._remonte_actions(root)
        else:
            root = self._build_fresh_ui()
            retirees = 0
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(path, encoding="utf-8",
                                   xml_declaration=True)
        return retirees

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
            # Ici, contrairement a _write_changed, une chaine vide ne s'ecrit PAS :
            # ce document n'existait pas avant, il n'a donc rien a corriger. Une
            # propriete absente vaut la chaine vide pour Qt (mesure faite sur le
            # bundle, reposee par test_effacement.py section 9), et le gabarit de
            # l'eleve reste propre. L'effacement d'un texte deja present
            # au fichier passe par l'autre chemin, la fusion.
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
                # Un tableau neuf n'a rien dans un fichier a protéger : son
                # plafond est TAILLE_MAX_TABLE tout rond.
                nrows = self._taille_admissible(props.get("rows", 0), 0) or 0
                ncols = self._taille_admissible(props.get("columns", 0), 0) or 0
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

    def _merge_into_source(self, table=None):
        """Reconstruit l'arbre à écrire à partir du fichier lu.

        Ne modifie jamais `self._source_ui` : on part d'une copie profonde, et
        l'on peut par conséquent enregistrer deux fois sans que la seconde
        dépende de la première. `table`, quand on le lui passe, reçoit
        {"by_uid": ...} : la table de correspondance uid -> element, utile à
        l'affichage (_repeins_estimations) pour retrouver un élément de CET
        arbre-là.
        """
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
        if table is not None:
            table["by_uid"] = by_uid
        lay = self._root_layout(form)
        seen = set()
        ajoutes = []
        rennames = {}
        for cls, props in self.widgets_data:
            el = by_uid.get(props.get("_uid")) if props.get("_uid") else None
            if el is None:
                # widget ajoute dans le concepteur
                el, src = self._insert_added(form, lay, cls, props)
                ajoutes.append((el, props))
                self._write_changed(el, cls, props, src)
            else:
                seen.add(props["_uid"])
                self._write_changed(el, cls, props, props.get("_src") or {})
            # apres les proprietes : le nom n'est pas une propriete, et le
            # signaler ici garantit qu'un element ajoute comme un element lu
            # portent a la fin l'attribut que l'eleve a saisi
            change = self._renomme_le_widget(el, props)
            if change:
                rennames[change[0]] = change[1]
        if table is not None:
            table["ajoutes"] = ajoutes

        # Les positions changées depuis l'ouverture déménagent : après l'écriture
        # des propriétés (qui n'a pas à savoir qui bouge) et avant le ménage des
        # suppression (qui doit connaître les parents d'après le déménagement).
        self._applique_la_pose(root, by_uid)
        # puis l'ordre que l'élève a demandé dans ses mises en page linéaires
        self._applique_l_ordre(root, by_uid, ajoutes)

        # widgets supprimes dans le concepteur -> retirer l'element et son <item>
        parents = self._parents(root)
        liberes = set()
        for uid in self._source_uids:
            if uid in seen:
                continue
            el = by_uid.get(uid)
            parent = parents.get(el)
            if el is None or parent is None:
                continue
            if el.get("name"):
                # le nom du disparu, tel que le fichier l'ecrivait : les
                # connexions qui le citent sont mortes, meme si un renommage
                # vient de lui redonner vie ailleurs (voir _purge_orphelines)
                liberes.add(el.get("name"))
            if parent.tag == "item":
                grand = parents.get(parent)
                (grand or parent).remove(parent if grand else el)
            else:
                parent.remove(el)
        if table is not None:
            table["rennames"] = rennames
            table["liberes"] = liberes
        return root

    # ── Renommage d'un objet ─────────────────────────────────
    #
    # Le nom d'un widget n'est pas une propriete : c'est l'attribut XML name du
    # <widget>, et c'est lui que l'eleve ecrit dans son programme
    # (windows.boutonValider.clicked.connect(...)). Le panneau le valide, le
    # modele le garde, l'objet list et le canevas l'affichent — mais rien de tout
    # cela n'atteignait le fichier : _write_changed ne patchait que des
    # <property>, et apres une reouverture le nom revenait a celui du disque.
    # Pire, le code suggere par le panneau (windows.<nom saisi>) ne designait
    # plus rien a l'execution : AttributeError sur un objet que l'eleve voyait
    # pourtant dans la liste.

    def _renomme_le_widget(self, el, props):
        """Reporte sur l'element du fichier le nom saisi dans le panneau.

        Rend (ancien, nouveau) quand le nom change, sinon None. Le point de
        depart est l'attribut DE L'ELEMENT (copie de travail), jamais un
        drapeau du modele : _source_ui n'est pas touche, donc Annuler,
        enregistrer deux fois et rouvrir restent coherents sans rien memoriser.

        Un nom vide ou impossible est ignore plutot que ecrit. _save le signale
        avant d'ecrire, mais la vue peut aussi etre enregistree par un chemin
        qui n'est pas passe par ce controle ; un attribut name vide casserait
        bien plus que le nom de l'objet (Designer refuserait le fichier).
        """
        nouveau = props.get("name") or ""
        ancien = el.get("name")
        if not nouveau or nouveau == ancien or not self._valid_qt_name(nouveau):
            return None
        el.set("name", nouveau)
        return (ancien, nouveau)

    # ── Connexions orphelines ────────────────────────────────
    #
    # Qt recopie chaque <connection> en code de setupUi() : un fichier qui
    # designe un objet absent n'est pas un avertissement, c'est un
    # AttributeError sec au moment du loadUi(), et toute la fenetre refuse de
    # se construire. Supprimer un bouton relie dans le concepteur laissait donc
    # son <sender> dans le fichier : le programme de l'eleve mourait sur le
    # nom du bouton qu'il venait d'effacer.
    # Qt Designer fait le menage en meme temps que la suppression ; on le fait
    # au moment d'ecrire, sans toucher au reste du bloc.

    def _purge_orphelines(self, root, rennames=None, liberes=None):
        """Retire les connexions mortes et fait suivre les autres au renommage.

        Rend le nombre de connexions retirees.

        Deux lectures des noms, dans un ordre impose : d'abord ce que la ligne
        VISAIT, texte encore intact, resolue par `rennames` et frappee de mort
        par `liberes` ; le texte n'est reecrit qu'apres, pour les survivantes.
        Resoudre apres avoir reecrit laisserait un trou : supprimer un bouton
        relie puis rebaptiser un autre bouton avec le nom du disparu rendrait
        sa connexion valide, et le survivant heriterait du cable du mort.
        """
        bloc = root.find("connections")
        if bloc is None:
            return 0
        rennames = rennames or {}
        liberes = liberes or set()
        # Seuls les widgets et les actions portent un nom qu'une connexion
        # peut citer. <property name="geometry"> a le meme attribut XML sans
        # designer aucun objet : le prendre en compte masquerait une coupure.
        noms = {el.get("name") for el in root.iter()
                if el.tag in ("widget", "action") and el.get("name")}

        def resout(fils):
            """(vivant, element, nom_a_ecrire)."""
            if fils is None:
                return True, None, None
            nom = (fils.text or "").strip()
            if not nom:
                # un signalement illisible n'est pas une preuve de mort
                return True, None, None
            if nom in liberes:
                return False, None, None
            cible = rennames.get(nom, nom)
            if cible not in noms:
                return False, None, None
            return True, fils, (None if cible == nom else cible)

        orphelines, reecrites = [], 0
        for c in bloc.findall("connection"):
            decisions = [resout(c.find(balise))
                         for balise in ("sender", "receiver")]
            if not all(vivant for vivant, _e, _n in decisions):
                orphelines.append(c)
                continue
            for _v, fils, nouveau in decisions:
                if fils is not None and nouveau:
                    fils.text = nouveau
                    reecrites += 1
        for c in orphelines:
            bloc.remove(c)
        return len(orphelines)

    def _remonte_actions(self, root):
        """Les actions du bloc `<actions>` de racine passent sous le formulaire.

        Rend le nombre d'actions remontees.

        Le format .ui que Qt ecrit aujourd'hui ne connait l'action que comme
        enfant d'un `<widget>` ; le bloc `<actions>` au niveau `<ui>` vient des
        fichiers anciens (les formulaires QMainWindow) ou ecrits a la main. Et
        `uic` — le chargeur du programme de l'eleve — ne lit pas ce bloc : il ne
        cree aucun objet pour ces noms-la. Un cable qui en cite un ne rend donc
        pas un avertissement, mais un `AttributeError` sec au moment du
        `setupUi()`, et c'est toute la fenetre qui refuse de se construire
        (mesure : « 'QWidget' object has no attribute 'cacheAction' »). Le
        menage de l'item 1 ne peut rien ici : le nom, lui, est bien dans le
        fichier — c'est l'objet qui manque. Remonter l'action sous le
        formulaire la rend visible du chargeur sans toucher au cable.

        Une action dont le nom est deja porte par un objet du formulaire n'est
        pas remontee : `setupUi()` cree un attribut par nom, les deux
        s'ecraseraient en silence, et un fichier qui ne se chargeait pas ne
        vaudrait pas mieux qu'avant. Elle reste dans le bloc, et le fichier
        sort tel qu'il est entre.
        """
        bloc = root.find("actions")
        if bloc is None or not [el for el in bloc if el.tag == "action"]:
            return 0
        form = root.find("widget")
        if form is None:
            return 0
        # Ce que le formulaire engage deja comme noms d'objets : ses widgets,
        # ses mises en page, ses actions enfantees, et la fenetre elle-meme.
        pris = {el.get("name") for el in form.iter()
                if el.tag in ("widget", "layout", "action") and el.get("name")}
        if form.get("name"):
            pris.add(form.get("name"))
        # La place des actions dans un formulaire que Designer ecrit lui-meme :
        # avant le premier enfant qui porte un objet.
        index = next((i for i, fils in enumerate(form)
                      if fils.tag in ("widget", "layout", "action")), len(form))
        remontees = 0
        # Une passe seule, et un nom marque a chaque montee : deux actions du
        # meme nom dans le bloc ne montent pas toutes les deux. `setupUi()`
        # cree un attribut par nom, la seconde ecrasait la premiere, et le
        # fichier de l'eleve se serait retrouve avec deux declarations
        # identiques -- inoffensif mais faussement propre.
        for el in list(bloc):
            if el.tag != "action" or not el.get("name"):
                continue
            if el.get("name") in pris:
                continue
            bloc.remove(el)
            form.insert(index + remontees, el)
            pris.add(el.get("name"))
            remontees += 1
        if not len(bloc):
            root.remove(bloc)
        return remontees

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

    # ── Garde de la mise en page ─────────────────────────────
    #
    # Un <widget> rangé dans un <item> de <layout> n'a pas de <geometry> :
    # c'est Qt qui le place, et une balise écrite là ne ferait que mentir à
    # l'élève (le concepteur montrerait un coin, l'exécution un autre) et à
    # Designer (qui l'ignore à l'affichage). Le vérifie le gabarit de Qt
    # Designer lui-même : 9 widgets rangés, 0 <geometry> ; seule la racine en
    # porte une.
    #
    # _pose, porté par chaque widget du modèle, dit qui décide : "layout" ou
    # "libre". _applique_la_pose est le seul écrivain de la STRUCTURE du
    # fichier sauvegardé — il déplace les éléments pour que l'arbre ressemble à
    # ce que l'élève voit, sans jamais toucher l'arbre lu (_source_ui).

    def _parents(self, root):
        return {child: parent for parent in root.iter() for child in parent}

    def _conteneur_de(self, el, parents):
        """(item, layout, hote) si `el` est rangé dans une mise en page, sinon None.

        Le test du grand-parent n'est pas un détail : un <item> porté
        directement par un QComboBox est une entrée de liste, et un <item>
        porté par un QTableWidget est une cellule. Ni l'un ni l'autre ne
        représentent une mise en page.
        """
        item = parents.get(el)
        if item is None or item.tag != "item":
            return None
        lay = parents.get(item)
        if lay is None or lay.tag != "layout":
            return None
        return item, lay, parents.get(lay)

    def _hote_de(self, el, parents):
        """Le <widget> dont dépend `el`, que celui-ci soit rangé ou posé libre.

        Sert à retrouver la mise en page d'accueil quand l'élève rend sa
        position à Qt : on ne peut pas le ranger n'importe où, seulement dans
        le layout du conteneur qui l'héberge déjà.
        """
        place = self._conteneur_de(el, parents)
        if place:
            return place[2]
        hote = parents.get(el)
        return hote if hote is not None and hote.tag == "widget" else None

    def _applique_la_pose(self, root, by_uid):
        """Déplace les éléments dont l'élève a changé le mode de placement.

        "libre"  : le <widget> sort de son <item> et redevient enfant direct de
                   son conteneur, posé avant son <layout> — la place qu'écrit
                   Qt Designer pour un widget absolu.
        "layout" : le <widget> retrouve un <item>, en fin de layout (et en fin
                   de ligne pour une grille ou un formulaire).

        Idempotent : reposé deux fois sur le même arbre, il ne trouve plus rien
        à déplacer. Les parents sont recalculés à chaque widget parce que le
        précédent a pu bouger l'arbre.
        """
        deplaces = 0
        for _cls, props in self.widgets_data:
            uid = props.get("_uid")
            el = by_uid.get(uid) if uid else None
            if el is None:
                continue                      # ajouté : _insert_added l'a déjà placé
            parents = self._parents(root)
            place = self._conteneur_de(el, parents)
            if props.get("_pose", "libre") == "libre":
                if not place:
                    continue
                _item, lay, hote = place
                while hote is not None and hote.tag != "widget":
                    hote = parents.get(hote)   # layout imbrique dans un <item>
                if hote is None:
                    continue
                lay.remove(_item)
                enfants = list(hote)
                # Qt Designer écrit les widgets libres avant le <layout> du
                # conteneur : même ordre, même lecture du fichier.
                pos = next((i for i, c in enumerate(enfants)
                            if c.tag == "layout"), len(enfants))
                hote.insert(pos, el)
                deplaces += 1
            elif place is None:
                hote = self._hote_de(el, parents)
                lay = hote.find("layout") if hote is not None else None
                if lay is None:
                    continue                  # pas de mise en page d'accueil
                # detacher AVANT d'ajouter : ElementTree ne deplace pas un
                # element, il le duplique silencieusement s'il a encore un
                # pere. (list(hote).remove(el) ne retire rien du tout : la
                # copie de la liste n'est pas l'arbre.)
                hote.remove(el)
                item = ET.SubElement(lay, "item")
                if LAYOUT_AXIS.get(lay.get("class", ""), "v") in ("grid", "form"):
                    item.set("row", str(self._next_grid_row(lay)))
                    item.set("column", "0")
                item.append(el)
                deplaces += 1
        return deplaces

    def _carte_des_layouts(self, racine, uid_de):
        """Ce que chaque mise en page du fichier range, et dans quel ordre.

        Retourne (groupes, clefs_ambigues) avec
        groupes = {clef : {"axe": axe, "lay": element,
                           "items": [(uid, <item>, position parmi les enfants)]}}.

        Seules les boites lineaires (verticale ou horizontale) ont un ordre
        qu'un glisser peut vouloir changer : grille, formulaire et pile rangent
        leurs elements par des attributs row/column, et ce n'est pas a une
        souris de decider de ces-la. Un <item> qui en porte est donc exclu.

        La clef (nom, classe, uid du widget-hote) ne depend pas de la position
        du <layout> dans le fichier. Un numero d'ordre ne le pouvait pas : un
        widget que l'on libere demenage son element, et avec lui celui des
        mises en page qu'il portait, ce qui aurait melange deux groupes.
        """
        parents = self._parents(racine)
        groupes, vues = {}, {}
        for lay in racine.iter("layout"):
            axe = LAYOUT_AXIS.get(lay.get("class", ""), "v")
            if axe not in ("v", "h"):
                continue
            items = []
            for pos, it in enumerate(list(lay)):
                if it.tag != "item":
                    continue
                if it.get("row") is not None or it.get("column") is not None:
                    items = None
                    break
                w = it.find("widget")
                uid = uid_de.get(id(w)) if w is not None else None
                if uid is not None:
                    items.append((uid, it, pos))
            if not items:
                continue
            hote = parents.get(lay)
            while hote is not None and hote.tag != "widget":
                hote = parents.get(hote)
            clef = "%s|%s|%s" % (lay.get("name", ""), lay.get("class", ""),
                                 uid_de.get(id(hote), ""))
            vues[clef] = vues.get(clef, 0) + 1
            groupes[clef] = {"axe": axe, "lay": lay, "items": items}
        ambigus = {c for c, n in vues.items() if n > 1}
        for clef in ambigus:
            groupes.pop(clef, None)      # deux mises en page d'un meme nom :
        return groupes, ambigus          # on ne devine pas laquelle est laquelle

    def _applique_l_ordre(self, root, by_uid, ajoutes=()):
        """Reclasse les <item> dont l'eleve a change la place dans leur layout.

        Les widgets ranges permutent entre les <item> qu'ils occupent deja :
        un <layout> imbrique et un <spacer> gardent leur position, parce que
        deplacer un bouton ne doit jamais deplacer la mise en page d'un groupe
        ni la zone qui pousse le contenu vers le bas.

        Le modele ressort d'ici avec un _rang qui raconte le fichier : repose
        sans changement, l'ordre ne bouge plus, et enregistrer deux fois reste
        identique. `ajoutes` porte les (element, props) des widgets_creés dans
        le concepteur : sans eux, un ajout reclasse reviendrait en fin de file
        a l'enregistrement, en desaccord avec ce que le canevas montre.
        """
        uid_de = {id(el): uid for uid, el in by_uid.items()}
        par_cle = {p.get("_uid"): p for _c, p in self.widgets_data
                   if p.get("_uid")}
        for i, (el, props) in enumerate(ajoutes):
            cle = "a%d" % i
            uid_de[id(el)] = cle
            par_cle[cle] = props
        groupes, _ambigus = self._carte_des_layouts(root, uid_de)
        reclasses = 0
        vus = set()
        for clef, g in groupes.items():
            lay, axe = g["lay"], g["axe"]
            membres = []
            for rang, (uid, it, pos) in enumerate(g["items"]):
                vus.add(uid)
                props = par_cle.get(uid)
                if props is None or props.get("_pose", "libre") != "layout":
                    continue
                membres.append((uid, it, pos, props, rang))
            ordre = membres
            if len(membres) > 1:
                # un membre qui arrive d'une autre mise en page (re-wrapping)
                # n'a rien a revendiquer : sa place dans le fichier fait foi
                ordre = sorted(
                    membres,
                    key=lambda m: (m[3]["_rang"]
                                   if isinstance(m[3].get("_rang"), int) and
                                   m[3].get("_groupe") == clef else m[4], m[2]))
                if [m[0] for m in ordre] != [m[0] for m in membres]:
                    enfants = list(lay)
                    for slot, m in zip([m[2] for m in membres], ordre):
                        enfants[slot] = m[1]
                    # tout detacher avant de reposer : ElementTree ecrit deux
                    # fois un element qui a encore un pere
                    for c in list(lay):
                        lay.remove(c)
                    for c in enfants:
                        lay.append(c)
                    reclasses += 1
            # ordre est desormais l'ordre DU FICHIER, slot par slot : c'est lui
            # que le modele doit raconter, pas la position d'avant la permutation.
            for rang, m in enumerate(ordre):
                m[3]["_groupe"], m[3]["_axe"], m[3]["_rang"] = clef, axe, rang
        for _cls, props in self.widgets_data:
            uid = props.get("_uid")
            if uid and uid not in vus and props.get("_groupe"):
                # sorti de toute boite lineaire (libere, ou passe dans une
                # grille) : il n'a plus de rang a faire valoir
                for cle in ("_groupe", "_axe", "_rang"):
                    props.pop(cle, None)
        return reclasses

    def _freres_mobiles(self, props):
        """Les widgets ranges dans la meme mise en page, dans l'ordre demande.

        Le rang absent ou hors service ne classe personne : on tombe alors sur
        l'ordre du fichier, qui est ce que l'enregistrement respecterait.
        """
        clef = props.get("_groupe")
        if not clef or props.get("_pose") != "layout":
            return []

        def rang(p):
            r = p.get("_rang")
            return r if isinstance(r, int) else None

        autres = [(rang(p), i, p) for i, (_cls, p) in enumerate(self.widgets_data)
                  if p is not props and p.get("_groupe") == clef
                  and p.get("_pose") == "layout"]
        autres.sort(key=lambda e: (e[0] if e[0] is not None else 0, e[1]))
        tout = [e[2] for e in autres]
        le_sien = rang(props)
        tout.insert(min(max(0, le_sien), len(tout)) if le_sien is not None
                    else len(tout), props)
        return tout

    def _mode_glissement(self, props):
        """Ce que le glisser d'un widget doit faire.

        "libre"      : il se deplace vraiment, et sa <geometry> est ecrite ;
        "reordonner" : une mise en page lineaire le place : le geste change sa
                       place DANS cette mise en page, sans ecrire de <geometry> ;
        "refus"      : grille, formulaire, pile, ou frere unique — le glisser
                       ne peut rien promettre, on l'explique dans la barre d'etat.
        """
        if props.get("_pose") != "layout":
            return "libre"
        if props.get("_groupe") and len(self._freres_mobiles(props)) > 1:
            return "reordonner"
        return "refus"

    def _cible_reclassement(self, props, nx, ny, gw, gh):
        """La place que le fantome en cours viserait, ou None."""
        freres = self._freres_mobiles(props)
        autres = [p for p in freres if p is not props]
        if not autres:
            return None
        horizontal = props.get("_axe") == "h"
        milieu = nx + gw / 2.0 if horizontal else ny + gh / 2.0
        cles = []
        for p in autres:
            x, y, w, h = p.get("geometry") or (0, 0, 0, 0)
            cles.append(x + w / 2.0 if horizontal else y + h / 2.0)
        return sum(1 for c in cles if c < milieu)

    def _reclasse(self, idx, vers):
        """Applique le reclassement demande par un glisser. Vrai si la place a change."""
        try:
            _cls, props = self.widgets_data[idx]
        except (IndexError, TypeError):
            return False
        if vers is None or props.get("_pose") != "layout":
            return False
        freres = self._freres_mobiles(props)
        place = next((i for i, p in enumerate(freres) if p is props), None)
        if place is None or len(freres) < 2:
            return False
        vers = max(0, min(vers, len(freres) - 1))
        if vers == place:
            return False
        gest = getattr(self, "_gesture", None)
        etat = gest[2] if gest and gest[0] == idx else self._state()
        self._gesture = None
        autres = [p for p in freres if p is not props]
        autres.insert(vers, props)
        for rang, p in enumerate(autres):
            p["_rang"] = rang
        self._edit_sig = None
        self._ensure_history()
        self._redo_stack = []
        self._push(etat)
        self._repeins_estimations()
        self._refresh()
        self._show_properties(idx)
        nom = (props.get("name") or "widget").strip()
        self._history_notice("%s est reclassé en position %d sur %d"
                             % (nom, vers + 1, len(freres)))
        return True

    def _efface_repere(self):
        rep = getattr(self, "_repere", None)
        self._repere = None
        if rep is not None:
            try:
                rep.destroy()
            except tk.TclError:
                pass

    def _dessine_repere(self, props, freres, vers):
        """Le trait bleu qui dit où le widget glisserait s'il etait lache ici."""
        autres = [p for p in freres if p is not props]
        if not autres:
            return
        rects = [p.get("geometry") or (0, 0, 0, 0) for p in autres]
        horizontal = props.get("_axe") == "h"
        if horizontal:
            haut = min(r[1] for r in rects)
            taille = max(r[1] + r[3] for r in rects) - haut
            if not autres or vers <= 0:
                bord = rects[0][0] - 3
            elif vers >= len(rects):
                bord = max(r[0] + r[2] for r in rects) + 2
            else:
                avant = rects[vers - 1]
                bord = avant[0] + avant[2] + 1
            x, y, w, h = bord, haut, 3, max(taille, 8)
        else:
            gauche = min(r[0] for r in rects)
            taille = max(r[0] + r[2] for r in rects) - gauche
            if vers <= 0:
                bord = rects[0][1] - 3
            elif vers >= len(rects):
                bord = max(r[1] + r[3] for r in rects) + 2
            else:
                avant = rects[vers - 1]
                bord = avant[1] + avant[3] + 1
            x, y, w, h = gauche, bord, max(taille, 8), 3
        self._efface_repere()
        try:
            rep = tk.Frame(self.ui_frame, bg="#2f7bd4")
            rep.place(x=max(0, int(x)), y=max(0, int(y)),
                      width=max(1, int(w)), height=max(1, int(h)))
            rep.lift()
            self._repere = rep
        except tk.TclError:
            self._repere = None

    def _positionne_un_ajout(self, props):
        """Un widget sans element XML (ajoute ou duplique) rejoint la boite
        racine par _insert_added : le modele doit le dire tout de suite, sinon
        il ne pourrait pas etre reclassé avant la prochaine ouverture."""
        for cle in ("_groupe", "_axe", "_rang"):
            props.pop(cle, None)
        if props.get("_pose") != "layout":
            return
        src = getattr(self, "_source_ui", None)
        form = src.find("widget") if src is not None else None
        lay = self._root_layout(form) if form is not None else None
        if lay is None:
            return
        uids_de = {id(el): "w%d" % i
                   for i, el in enumerate(self._walk_widgets(form))}
        for clef, g in self._carte_des_layouts(src, uids_de)[0].items():
            if g["lay"] is lay:
                props["_groupe"] = clef
                props["_axe"] = g["axe"]
                # le fichier ne connait que ses propres widgets : les ajouts
                # deja promises a cette boite comptent aussi, sinon deux
                # creations se partageraient la meme place.
                props["_rang"] = sum(
                    1 for _c, q in self.widgets_data
                    if q is not props and q.get("_groupe") == clef
                    and q.get("_pose") == "layout")
                return

    def _peut_changer_de_pose(self, props):
        """Vrai si le widget a une mise en page où revenir.

        Judge sur le fichier lu, jamais sur l'arbre en cours d'écriture : un
        widget que l'élève a libéré dans cette session y est encore rangé, et
        c'est bien ce layout qui doit l'accueillir.
        """
        src = getattr(self, "_source_ui", None)
        uid = props.get("_uid")
        if src is None or not uid:
            return False
        form = src.find("widget")
        if form is None:
            return False
        by_uid = {"w%d" % i: el
                  for i, el in enumerate(self._walk_widgets(form))}
        el = by_uid.get(uid)
        if el is None:
            return False
        hote = self._hote_de(el, self._parents(src))
        return hote is not None and hote.find("layout") is not None

    def _repeins_estimations(self):
        """Recalcule la position affichée des widgets remis dans la mise en page.

        Le fichier ne dit rien de la place qu'ils y prendront — c'est Qt qui
        décide au premier affichage. On repasse donc l'estimateur sur l'arbre
        tel qu'il sera écrit, pour que le canevas montre la même chose que
        l'enregistrement. L'empreinte _src n'y change pas : elle doit continuer
        à décrire le fichier d'origine.
        """
        if getattr(self, "_source_ui", None) is None:
            return
        table = {}
        try:
            root = self._merge_into_source(table)
        except Exception:
            return
        form = root.find("widget")
        by_uid = table.get("by_uid") or {}
        if form is None:
            return
        # props -> element, pour les widgets du fichier comme pour ceux que
        # l'eleve a crees : les seconds n'ont pas d'uid et sans eux le canevas
        # garderait la position d'a-percu du widget ajoute.
        par_cle = {p.get("_uid"): p for _c, p in self.widgets_data
                   if p.get("_uid")}
        el_de = {}
        for uid, el in by_uid.items():
            props = par_cle.get(uid)
            if props is not None:
                el_de[id(props)] = id(el)
        for el, props in table.get("ajoutes") or []:
            el_de[id(props)] = id(el)
        est = self._estimate_geometries(form)
        for _cls, props in self.widgets_data:
            if props.get("_pose") != "layout":
                continue
            el_id = el_de.get(id(props))
            rect = est.get(el_id) if el_id is not None else None
            if rect:
                props["_est"] = rect
                props["geometry"] = rect

    def _bascule_position(self, idx):
        """Libère la position d'un widget rangé, ou la rend à la mise en page."""
        try:
            _cls, props = self.widgets_data[idx]
        except (IndexError, TypeError):
            return
        vers_libre = props.get("_pose") != "libre"
        if not vers_libre and not self._peut_changer_de_pose(props):
            self._history_notice(
                "%s : le conteneur n'a pas de mise en page, "
                "rien où le remettre" % props.get("name", "widget"))
            return
        self._step()
        props["_pose"] = "libre" if vers_libre else "layout"
        self._repeins_estimations()
        self._refresh()
        self._show_properties(idx)
        if vers_libre:
            self._history_notice(
                "%s est libéré de la mise en page : vous pouvez le déplacer"
                % props.get("name", "widget"))
        else:
            self._history_notice(
                "%s est remis dans la mise en page : c'est elle qui le place"
                % props.get("name", "widget"))

    def _insert_added(self, form, lay, cls, props):
        """Insère le widget ajouté, là où le fichier le respectera.

        Retourne (element, etat_de_reference) : la référence indique à
        _write_changed si la position doit être écrite. Un fichier dont la
        racine est occupée par un layout donne sa géométrie à tout ce qu'il
        contient — y déposer un <widget> en pose absolue le fait retomber sur
        (0,0) derrière les autres, visible dans le concepteur mais invisible à
        l'exécution. Il rejoint donc le layout comme nouvel <item>, sans
        <geometry>. Sans layout, la pose absolue reste la bonne réponse : c'est
        alors _write_changed qui écrira la géométrie.
        """
        name = props.get("name", "widget")
        if props.get("_pose") != "layout" or lay is None:
            return ET.SubElement(form, "widget", {"class": cls, "name": name}), {}

        item = ET.SubElement(lay, "item")
        if LAYOUT_AXIS.get(lay.get("class", ""), "v") in ("grid", "form"):
            # une grille place ses enfants par ligne/colonne : à défaut de ces
            # attributs l'item tomberait en (0,0) par-dessus le premier champ
            item.set("row", str(self._next_grid_row(lay)))
            item.set("column", "0")
        el = ET.SubElement(item, "widget", {"class": cls, "name": name})
        return el, {}

    def _write_changed(self, el, cls, props, src):
        """Reecrit dans `el` uniquement les proprietes modifiees depuis l'ouverture."""
        geom = props.get("geometry")
        src_geom = src.get("geometry")
        if props.get("_pose") == "layout":
            # Un widget range dans un <layout> ne porte PAS de propriete
            # geometry : verifie sur le gabarit de Qt Designer lui-meme (9
            # widgets ranges, 0 geometry ; seule la racine en porte une). En
            # ecrire une ne ferait que tromper l'eleve — Qt repose le widget où
            # la mise en page decide des l'affichage — et le fichier ne se
            # retrouverait plus dans Designer. On retire sans regarder l'etat
            # d'origine : la demande de l'eleve prime ce que le fichier
            # contenait, y compris une geometrie heritee d'une position
            # precedemment liberee.
            self._retire_rect(el)
        elif geom and tuple(src_geom or ()) != tuple(geom):
            self._set_rect_prop(el, geom)

        # Une valeur vide est une demande, pas une absence : l'eleve qui efface
        # le texte d'une etiquette ou le « placeholder » d'un champ veut que le
        # fichier n'affiche plus rien. Le filtre « if val » lisait l'effacement
        # comme « rien a ecrire », l'ancien texte restait dans le .ui et loadUi
        # le repeignait — la fenetre du concepteur et le programme ne montraient
        # plus la meme chose.
        # Une cle absente du modele reste un silence : la classe du widget n'a pas
        # ce champ (title pour un QPushButton), ou il etait deja vide a l'ouverture
        # et l'eleve n'y a pas touche — il n'y a rien a comparer.
        # Forme ecrite : la propriete demeure, avec une chaine vide. Qt rend la
        # meme chose d'un <string/> et d'une propriete absente (mesure faite sur
        # le bundle, puis reposee dans test_effacement.py section 3), et la
        # balise conservee garde la place de la propriete parmi ses voisines.
        for key in ("text", "placeholderText", "title", "styleSheet"):
            val = props.get(key)
            if val is None:
                continue
            if (val or "") != (src.get(key) or ""):
                self._set_string_prop(el, key, val)

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

    # Une taille de tableau que l'editeur accepte d'ecrire. Le fichier .ui paye
    # UN element <row> ou <column> par unite reclamee : 10 000 lignes y ecrivaient
    # 151 267 octets et dix mille elements (mesure, item 8). 1 000 reste un grand
    # tableau pour un exercice du secondaire et tient dans une vingtaine de
    # kilo-octets ; au-dela, l'eleve ne dessine plus un tableau, il ecrit une base
    # de donnees — et ce n'est pas le role de ce champ.
    TAILLE_MAX_TABLE = 1000
    # (pluriel pour parler du nombre, singulier pour parler d'une unite) : les
    # deux messages ne construisent pas la meme phrase.
    TAILLE_ETICHETTE = {"rows": ("lignes", "ligne"),
                        "columns": ("colonnes", "colonne")}
    # Le DESSIN du tableau, independant de sa taille : 8 rangees et 6 colonnes
    # suffisent a le reconnaitre dans l'apercu, et c'est le champ « Lignes » du
    # panneau qui porte le compte reel. Le cap est la pour que ouvrir un grand
    # fichier ne puisse jamais couter un million de cases Tk (voir _make_table).
    APERCU_MAX_LIGNES = 8
    APERCU_MAX_COLONNES = 6

    @staticmethod
    def _taille_brute(valeur):
        """Le nombre que ce texte veut dire, jamais negatif, jamais une exception."""
        try:
            return max(0, int(valeur))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _taille_admissible(valeur, deja_la):
        """La taille qu'un tableau peut porter, ou None si ce texte n'est pas une
        taille du tout.

        Borne basse : 0 — et un compte NEGATIF n'est pas une taille, c'est une
        erreur. Qt ne sait pas compter en dessous de zero, et surtout un
        <rowCount>-1</rowCount> se lisait en tableau SANS ligne : les titres que
        l'eleve avait ecrits restaient dans le fichier sans etre atteints par
        aucune cellule (mesure, item 8). La reponse n'est pas d'ecrire zero —
        cela viderait un tableau qui porte des en-tetes — mais de ne rien ecrire.
        Borne haute : TAILLE_MAX_TABLE — sauf si le tableau porte deja plus, parce
        que l'editeur ne doit jamais detruire, d'un geste dans un champ, plus de
        lignes qu'un fichier legitime n'en a posees.
        """
        try:
            n = int(valeur)
        except (TypeError, ValueError):
            return None
        if n < 0:
            return None
        plafond = max(UiViewerPlugin.TAILLE_MAX_TABLE, max(0, int(deja_la or 0)))
        return min(n, plafond)

    @staticmethod
    def _taille_deja(cle, props):
        """Ce que CE tableau porte deja, et qui ne doit donc pas etre refuse.

        Le plafond regarde le fichier lu, pas la derniere saisie : sans cela,
        passer de 1 200 lignes a 500 puis vouloir 900 se verrait refuser par une
        limite que l'eleve vient de franchir lui-meme, et le plafond deviendrait
        un clique qui ne fait que descendre. Le max des deux garde les deux
        regles : on ne grossit jamais au-dela de ce que le document a porte, on
        peut toujours y revenir.
        """
        return max(UiViewerPlugin._taille_brute(props.get(cle)),
                   UiViewerPlugin._taille_brute((props.get("_src") or {}).get(cle)))

    def _accept_taille(self, cle, texte, props):
        """Le texte saisi designe-t-il une taille inscriptible dans un .ui ?

        La porte tient le texte BRUT, pas un nombre deja converti : un « abc »
        comme un champ efface doivent se refuser et s'expliquer comme le nombre
        trop grand, et non disparaitre dans le ValueError du cast. Le refus est
        VISIBLE : le champ se colore et s'explique, comme le champ « Nom » depuis
        l'item 6, et le modele garde la derniere taille qui s'ecrivait vraiment.
        Un props venu d'ailleurs (une restauration d'annulation, un futur lecteur
        qui croirait <rowCount>) est de toute facon rattrape a l'ecriture par
        _taille_admissible.
        """
        admissible = self._taille_admissible(texte, self._taille_deja(cle, props))
        try:
            voulu = int(texte)
        except (TypeError, ValueError):
            voulu = None
        if voulu is not None and voulu == admissible:
            self._dit_taille(cle, "")
            return True
        etique = self.TAILLE_ETICHETTE.get(cle, (cle, cle))
        if voulu is None:
            saisi = str(texte).strip()
            if saisi:
                motif = ("Le compte des %s s'ecrit en chiffres : « %s » ne "
                         "designe pas un nombre." % (etique[0], saisi))
            else:
                motif = ("Le champ est vide : « 0 » est un compte legal, mais un "
                         "tableau a un nombre de %s ecrit en chiffres."
                         % etique[0])
        elif voulu < 0:
            motif = ("Un tableau ne peut pas avoir un nombre negatif de %s : 0 "
                     "est le plus petit compte que Qt sache construire."
                     % etique[0])
        else:
            # Le plafond cite est celui qui s'applique a CE tableau-la : un fichier
            # qui porte deja 1 200 lignes peut les garder, l'eleve ne peut plus que
            # les reduire. Leur annoncer « 1 000 » serait lui mentir.
            motif = ("Un fichier .ui ecrit une ligne XML par %s reclamee : %d en "
                     "ecrirait %d, et le fichier mettrait des minutes a s'ouvrir. "
                     "La limite de l'editeur est %d %s." %
                     (etique[1], voulu, voulu, admissible, etique[0]))
        self._dit_taille(cle, motif)
        return False

    def _dit_taille(self, cle, motif):
        """Colorie le champ de taille et ecrit l'explication sous les deux champs.
        Un panneau detruit sous la main (changement de widget, « Nouveau ») est
        tolere — la lecon de _accept_name."""
        champs = getattr(self, "_taille_champs", None) or {}
        entry = champs.get(cle)
        if entry is not None:
            try:
                entry.config(bg="#5a1a1a" if motif else "#3c3c3c")
            except tk.TclError:
                self._taille_champs[cle] = None       # panneau reconstruit
        hint = getattr(self, "_taille_hint", None)
        if hint is not None:
            try:
                hint.config(text=motif)
            except tk.TclError:
                self._taille_hint = None

    def _sync_table(self, el, props, src):
        # Le modele ne traverse pas cette porte plus gros que ce que le fichier
        # peut porter : la saisie est deja bornee par _accept_taille, mais un
        # props venu d'ailleurs — une restauration d'annulation, un futur lecteur
        # qui croirait <rowCount> — ne doit pas pouvoir ecrire -1.
        deja_lignes = len(el.findall("row"))
        deja_colonnes = len(el.findall("column"))
        nrows = self._taille_admissible(props.get("rows", 0), deja_lignes)
        ncols = self._taille_admissible(props.get("columns", 0), deja_colonnes)
        # les <column> existantes gardent leur titre : on ajuste seulement le nombre
        # Chaque cote se traite seul : ce qui n'est pas une taille ne s'ecrit pas,
        # mais cela n'empeche pas l'autre champ de passer au fichier.
        if ncols is not None and ncols != int(src.get("columns") or 0):
            self._set_number_prop(el, "columnCount", ncols)
            self._adjust_count(el, "column", ncols)
        if nrows is not None and nrows != int(src.get("rows") or 0):
            self._set_number_prop(el, "rowCount", nrows)
            self._adjust_count(el, "row", nrows)

    def _adjust_count(self, el, tag, want):
        # have[want:] avec un want NEGATIF tronque la FIN de la liste : c'est
        # exactement ainsi que « -1 » effacait le <row> qui portait le titre
        # « Eleve 3 » (mesure, item 8). Le plancher est pose ici aussi, pour que
        # la fonction soit sure independamment de ce que son appelant croit — et
        # le plancher ne veut pas dire « zero » : vider un tableau sur un compte
        # qui n'est pas une taille serait la meme faute, en plus grand.
        if want is None:
            return
        try:
            want = int(want)
        except (TypeError, ValueError):
            return                 # un compte qui n'est pas un nombre ne se dessine pas
        if want < 0:
            return
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

    def _retire_rect(self, el):
        """Supprime la propriete geometry d'un element dont la position est
        rendue a la mise en page. Sans effet s'il n'en porte pas — donc sans
        risque pour l'enregistrement d'un fichier que l'on n'a pas touche."""
        prop = self._find_prop(el, "geometry")
        if prop is not None:
            el.remove(prop)

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

    def _noms_hors_modele(self):
        """Les noms d'objets que le fichier declare SANS les passer au modele.

        La fenetre elle-meme, chaque <layout> et chaque <action>. Le modele ne
        les voit pas — il n'aligne que des widgets — donc aucun controle de
        collision ne les atteint par _used_names. Ils comptent quand meme :
        setupUi() cree un attribut par nom, deux objets du meme nom ne peuvent
        pas coexister, le second ecrase le premier sans un mot. Renommer un
        bouton « colonne » ferait disparaitre la mise en page de l'eleve de son
        propre code (windows.colonne serait le bouton).

        Les noms de <widget> du fichier sont exclus volontairement : un nom qui
        ne sert plus a personne est libre, le widget qui le portait soit est
        dans le modele, soit va etre retire de l'arbre a l'ecriture.
        """
        noms = set()
        source = getattr(self, "_source_ui", None)
        if source is None:
            return noms
        for el in source.iter():
            if el.tag in ("layout", "action"):
                nom = el.get("name")
                if nom:
                    noms.add(nom)
        form = source.find("widget")
        if form is not None and form.get("name"):
            noms.add(form.get("name"))
        return noms

    @staticmethod
    def _reserve_python(name):
        """'mot-cle', 'dunder', ou None : les noms que Python garde pour lui.

        La forme « identifiant » ne suffit plus des qu'un nom atteint le
        fichier : elle dit si Qt le stocke, pas si l'eleve peut s'en servir.
        « class » est un identifiant parfaitement forme ET un mot reserve, donc
        « windows.class.setText(...) » — la ligne que le panneau propose juste
        en dessous — ne s'ecrit pas dans un programme. Le widget existe dans la
        fenetre, il est simplement inatteignable : le pupil ne peut pas deviner
        pourquoi son code refuse de s'executer.
        Les noms en __double__ sont pire, mesures sur le bundle : un
        <widget name="__class__"> fait echouer loadUi() d'un TypeError
        (« __class__ must be set to a class, not 'QPushButton' ») et la fenetre
        entiere refuse de se construire, alors que Qt, lui, avale le nom sans un
        mot. « __init__ » se construit meme, en remplacant l'initialiseur de la
        fenetre par un bouton.

        Rien d'autre n'est refuse, et c'est delibere : « match », « case » et « _ »
        sont des mots-cles SOUPLES (ils ne le sont que selon la place qu'ils
        occupent) et « print », « id », « list » sont des noms communs — les
        trois lignes mesurees fonctionnent. Un nom accentue reste un identifiant
        valide, comme pour l'item 4.
        """
        if keyword.iskeyword(name):
            return "mot-cle"
        if len(name) >= 5 and name.startswith("__") and name.endswith("__"):
            return "dunder"
        return None

    @staticmethod
    def _forme_valide(name):
        """La FORME seule d'un nom d'objet : des lettres, des chiffres, « _ »,
        et pas de chiffre au debut.

        Separee de _valid_qt_name parce que deux questions different se posent
        devant la fabrique de noms : « class » est bien forme mais reserve par
        Python (un chiffre le rend libre), alors que « mon-bouton » est mal forme
        et qu'AUCUN chiffre ne le rendra jamais presentable. Les deux moities
        doivent rester la meme regle : c'est parce que la recherche comparait a
        « reserve OU forme » qu'elle pouvait tourner sur une base ou seul le mot
        etait en cause, et parce qu'elle comparait a la forme qu'elle tournait
        sans issue sur « mon-bouton » (item 14).
        """
        if not name:
            return False
        first, rest = name[0], name[1:]
        return (first.isalpha() or first == "_") and all(
            c.isalnum() or c == "_" for c in rest)

    @staticmethod
    def _valid_qt_name(name):
        """Un nom d'objet doit rester un identifiant : Designer et le code
        genere (windows.<nom>) n'acceptent ni espace, ni tiret, ni chiffre initial.
        Et il doit rester utilisable dans le code de l'eleve : un mot reserve de
        Python ou un nom en __double__ est refuse ici, au meme titre qu'un nom
        boiteux, parce qu'aucun des deux ne peut devenir « windows.<nom> »."""
        if not name or UiViewerPlugin._reserve_python(name):
            return False
        return UiViewerPlugin._forme_valide(name)

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

    NOM_DE_RECHANGE = "widget"

    @staticmethod
    def _base_reparee(base):
        """La base dont un chiffre peut faire un nom presentable, ou un repli sur.

        Un tiret, un espace ou un chiffre en tete ne se reparent pas en ajoutant
        un chiffre : « mon-bouton1 », « bouton 12 » et « 1er99 » sont aussi
        boites que « mon-bouton ». La recherche de _unique_name, qui repartait de
        la base telle que le FICHIER la donnait, demandait donc a la boucle
        l'impossible et ne rendait jamais la main — Duplicate sur un widget nommé
        a la main figeait Thonny, sans message et sans CPU libre pour le dessin
        (item 14, mesuree : quatre des sept formes testees y passaient).

        Reparer la forme une fois, ici, plutot que borner la boucle la-bas : le
        numero garde son seul metier, l'unicite, et la forme retrouve le sien.
        Ce que l'eleve avait ecrit n'est pas efface pour autant — cette base ne
        sert qu'a NOMMER UNE COPIE ; le widget d'origine garde « mon-bouton »,
        et c'est son nom que le panneau et l'enregistrement lui reprochent.

        Une base deja bien formee ressort telle quelle, mot reserve compris :
        « class » doit donner « class1 », pas « classe1 » — le numero, pas la
        traduction, est ce qui le rend libre. Les lettres accentuees tiennent
        (item 4 : « élan » est un identifiant valide), donc rien n'est
        translitere ; seuls les caracteres qui ne sont ni alphanumeriques ni « _ »
        deviennent des « _ ».
        """
        if UiViewerPlugin._forme_valide(base):
            return base
        reparee = "".join(c if (c.isalnum() or c == "_") else "_"
                          for c in (base or ""))
        while "__" in reparee:
            reparee = reparee.replace("__", "_")
        reparee = reparee.strip("_")
        if reparee and reparee[0].isdigit():
            reparee = "_" + reparee
        # « !!! » ne laisse rien, et une base vide ne se numerote pas mieux :
        # le repli est une famille toujours numerotable, pas une deuxieme boucle
        if not UiViewerPlugin._forme_valide(reparee):
            return UiViewerPlugin.NOM_DE_RECHANGE
        return reparee

    def _unique_name(self, base, exclude_idx=None):
        """Un nom libre, dans la famille de base, qui ne heurte aucun autre objet.

        La base est rendue numerotable avant la recherche : la boucle n'ajoute
        plus que des chiffres, desormais suffisant pour finir. Les noms que le
        fichier declare hors du modele — la fenetre, chaque mise en page, chaque
        action — comptent comme occupes : setupUi() cree un attribut par nom, un
        nom genere qui reprendrait celui d'une mise en page la ferait disparaitre
        de windows.<nom> sans un mot, et l'enregistrement refuserait le fichier
        apres un clic qui semblait avoir reussi.
        """
        donnee = base
        base = self._base_reparee(base)
        # une base qu'il a fallu reparer garde neanmoins un numero : la place
        # « propre » (« mon_bouton ») doit rester libre pour l'eleve, qui va
        # vouloir renommer l'original « mon-bouton » dessus — deux widgets du
        # meme nom, l'enregistrement le refuserait a l'etape d'apres
        a_repare = base != donnee
        used = self._used_names(exclude_idx) | self._noms_hors_modele()
        name = base
        if a_repare or name in used or not self._valid_qt_name(name):
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
        reserve = self._reserve_python(name)
        if reserve == "mot-cle":
            # La forme du mot est parfaite : c'est son statut qui gene. Renvoyer
            # l'eleve a la regle des lettres et des chiffres lui ferait chercher
            # une faute d'orthographe qu'il n'a pas faite.
            return ("%s est un mot reserve de Python : windows.%s ne s'ecrit pas "
                    "dans un programme." % (name, name))
        if reserve:
            return ("%s est un nom reserve par Python (les noms en __double__) : "
                    "la fenetre entiere refuserait de se construire." % name)
        if not self._valid_qt_name(name):
            return ("Un nom d'objet ne prend que des lettres, chiffres et « _ », "
                    "et ne commence pas par un chiffre.")
        if name in self._used_names(idx):
            return "Ce nom appartient deja a un autre widget de l'interface."
        if name in self._noms_hors_modele():
            return ("Ce nom appartient a la fenetre, a une mise en page ou a "
                    "une action du fichier : deux objets du meme nom ne peuvent "
                    "pas coexister.")
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
        # Un widget ajoute dans un fichier piloté par un layout rejoint ce
        # layout : sa position est donc reglee par la mise en page, comme ceux
        # que le fichier contenait deja.
        props["_pose"] = "layout" if anchor else "libre"
        self._step()
        self.widgets_data.append((cls, props))
        self._positionne_un_ajout(props)
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

    # La zone defilable du canevas de conception : le document (root_geometry)
    # plus la marge qui l'entoure, soit le cadre pose a (20, 20) et son ombre
    # decalee de 4 px.
    #
    # UNIQUEMENT cette fonction decide de canvas["scrollregion"]. L'ancien
    # handler <Configure> calculait canvas.bbox("all") : mesuree, cette valeur
    # vaut (20, 20, 25, 25) avant le premier rafraichissement — le cadre
    # interne n'a encore qu'1 px de large — elle perd la marge externe a
    # chaque changement de taille de la fenetre (684x524 devient 668x508), et
    # elle vaut None sur un canevas vide. La zone suivrait ainsi la fenetre au
    # lieu du document : l'eleve ne pourrait plus atteindre le coin bas droit
    # de sa forme des qu'il reduirait la fenetre Thonny.
    def _zone_defilable(self):
        _, _, rw, rh = self.root_geometry
        return (0, 0, rw + 44, rh + 44)

    def _refresh(self):
        for child in self.ui_frame.winfo_children():
            child.destroy()
        self._repere = None       # detruit avec les autres : ne pas le rappeler
        _, _, rw, rh = self.root_geometry
        self.ui_frame.config(width=rw, height=rh)
        self._shadow.config(width=rw + 4, height=rh + 4)
        for i, (cls, props) in enumerate(self.widgets_data):
            self._draw_widget(i, cls, props)
        self.ui_frame.update_idletasks()
        self.canvas.configure(scrollregion=self._zone_defilable())

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
        reglee = props.get("_pose") == "layout"
        outer = tk.Frame(self.ui_frame,
                         bg=QT_SEL if sel else QT_BG,
                         cursor="dot" if reglee else "fleur")
        outer._widget_idx = idx
        outer._is_outer   = True
        outer._is_label   = False
        outer.place(x=x - bd, y=y - bd,
                    width=w + 2*bd, height=h + 2*bd)

        inner = self._make_qt_widget(outer, cls, props, w, h)
        if inner:
            inner.place(x=bd, y=bd, width=w, height=h)

        # Resize handles (selected only)
        # Pas de poignees pour un widget que la mise en page place et dimensionne :
        # les offrir serait promettre un geste que l'on refuse juste apres.
        if sel and props.get("_pose") != "layout":
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
        """Les deux couleurs d'une feuille de style Qt, en valeurs que Tk accepte.

        Qt Designer ecrit `color: rgb(255, 0, 0)` et `palette(base)` ; Tk ne
        connait ni l'un ni l'autre et refusait la valeur d'un TclError. Comme
        l'apercu passait par la, un fichier colore ne s'ouvrait tout
        simplement pas. Seul l'apercu traduit : le fichier, lui, garde le texte
        de l'eleve mot pour mot. Rend (None, None) quand rien n'est exprimable,
        et le widget reprend alors sa teinte habituelle.
        """
        fg = bg = None
        for part in (ss or "").split(";"):
            part = part.strip()
            # On reconnait la regle sans se soucier de la casse ni des espaces :
            # « COLOR : rgb(...) » est une feuille que Qt applique tres bien, et
            # l'eleve qui l'a ecrite a droit de la voir. Le nom s'arrete au
            # premier deux-points et se compare entier — « color » n'est pas
            # « background-color », et n'est pas davantage « selection-color »
            # ni « alternate-background-color » : la lecon de l'item 11 vaut
            # aussi dans le sens lecture, ou elle peignait une teinte que
            # l'eleve n'avait pas demandee.
            if ":" not in part:
                continue
            nom = self._nom_de_declaration(part)
            valeur = part.split(":", 1)[1]
            if nom == "color":
                fg = self._couleur_tk(valeur)
            elif nom in ("background", "background-color"):
                bg = self._couleur_tk(valeur)
        return fg, bg

    def _couleur_tk(self, valeur):
        """Une couleur ecrite a la maniere Qt, en une valeur que Tk affiche.

        Ne leve jamais d'exception : c'est exactement ce que faisait mal
        l'ancienne version, qui recopiait le texte de Qt dans bg= et fg=.
        """
        v = (valeur or "").strip()
        if not v:
            return None
        bas = v.lower()
        if bas in ("transparent", "none"):
            return None
        if bas.startswith("palette(") and bas.endswith(")"):
            return self._couleur_palette(bas[len("palette("):-1])
        if bas.startswith(("rgb(", "rgba(", "hsl(", "hsla(")):
            return self._couleur_fonction(bas)
        if bas.startswith("#"):
            return self._couleur_hex(bas)
        # Un nom de couleur : c'est Tk qui doit l'afficher, c'est donc lui qui
        # decide s'il le connait. Sans affichage Tk sous la main, on s'abstient.
        try:
            self.winfo_rgb(v)
        except (tk.TclError, AttributeError):
            return None
        return v

    @staticmethod
    def _couleur_palette(entre_parentheses):
        """`base`, ` Button `, `Active, Button`… : le role de palette demande.

        Qt ecrit le role en dernier dans la forme a deux arguments
        (`palette(groupe, role)`), et les deux mots peuvent etre inconnus de la
        table : on prend donc le dernier que la table connait, pas le premier.
        `palette(Window, WindowText)` est du texte, pas le fond de la fenetre.
        """
        trouve = None
        for token in entre_parentheses.split(","):
            role = token.strip().lower().replace("_", "").replace("-", "")
            if role in _PALETTES_TK:
                trouve = _PALETTES_TK[role]
        return trouve

    @staticmethod
    def _couleur_hex(v):
        """#rgb, #rrggbb et les formes longues, reduites a ce que Qt en voit.

        Qt 5 n'accepte que cinq longueurs : 3 (#rgb), 6, 8 (#aarrggbb — l'alpha
        est en PREMIER, contrairement au CSS), 9 (douze bits par canal) et 12
        (seize bits par canal). Tout le reste est refuse par QColor, donc par la
        feuille de style : le widget garde sa teinte a lui, et l'apercu fait
        pareil au lieu d'inventer une couleur que l'eleve ne verra jamais.
        """
        corps = v[1:]
        if not corps or any(c not in "0123456789abcdef" for c in corps):
            return None
        n = len(corps)
        if n == 3:
            corps = "".join(c * 2 for c in corps)
        elif n == 8:
            corps = corps[2:]
        elif n == 9:
            corps = corps[0:2] + corps[3:5] + corps[6:8]
        elif n == 12:
            corps = corps[0:2] + corps[4:6] + corps[8:10]
        elif n != 6:
            return None
        return "#" + corps

    @staticmethod
    def _couleur_fonction(v):
        """rgb()/rgba()/hsl()/hsla() en #rrggbb. L'eventuel canal alpha est
        ignore : l'apercu ne sait pas melanger une couleur a un fond."""
        nom, _, reste = v.partition("(")
        reste = reste.rstrip(")")
        tokens = [t for t in reste.replace(",", " ").replace("/", " ")
                  .split() if t]
        try:
            nombres = [(float(t[:-1]), True) if t.endswith("%")
                       else (float(t), False) for t in tokens]
        except ValueError:
            return None
        if len(nombres) < 3:
            return None
        if nom.startswith("rgb"):
            octets = []
            for n, pct in nombres[:3]:
                n = n * 2.55 if pct else n
                octets.append("%02x" % int(round(min(255.0, max(0.0, n)))))
            return "#" + "".join(octets)
        if nom.startswith("hsl"):
            (h, _), (s, sp), (l, lp) = nombres[:3]
            saturation = (s / 100.0 if sp else s)
            luminosite = (l / 100.0 if lp else l)
            r, g, b = colorsys.hls_to_rgb(h % 360.0 / 360.0,
                                          min(1.0, max(0.0, luminosite)),
                                          min(1.0, max(0.0, saturation)))
            return "#" + "".join("%02x" % int(round(255 * c)) for c in (r, g, b))
        return None

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
            # _make_table borne le dessin : ici on ne fait que lire le modele,
            # et un modele qui porterait un texte ne doit pas faire tomber
            # l'apercu avec max(1, "abc").
            rows = self._taille_brute(props.get("rows", 3))
            cols = self._taille_brute(props.get("columns", 3))
            return self._make_table(parent, rows, cols, font)

        return tk.Label(parent, text=f"[{cls}]",
                        bg=QT_BG, fg="#888", font=font,
                        relief=tk.GROOVE, anchor="center")

    def _make_table(self, parent, rows, cols, font):
        # L'apercu d'un tableau est un DESSIN, pas son contenu : le nombre de
        # cases Tk doit rester borne quel que soit le nombre reclame. Sans ce
        # cap, un tableau de 1 000 lignes sur 1 000 colonnes dessinait un
        # million de Labels a l'ouverture du fichier, et la fenetre ne revenait
        # plus (mesure, item 8). Le modele, lui, garde la taille reelle : c'est
        # le champ « Lignes » du panneau qui la montre, et la derniere rangee
        # « … » dit a l'eleve que le tableau continue sous le dessin.
        lignes = max(1, self._taille_brute(rows))
        colonnes = max(1, self._taille_brute(cols))
        dessine_lignes = min(lignes, self.APERCU_MAX_LIGNES)
        dessine_colonnes = min(colonnes, self.APERCU_MAX_COLONNES)
        plus_lines = lignes > dessine_lignes
        plus_colonnes = colonnes > dessine_colonnes
        nb_colonnes = dessine_colonnes + (1 if plus_colonnes else 0)
        f = tk.Frame(parent, bg=QT_ENTRY_BG,
                     highlightbackground=QT_ENTRY_BD,
                     highlightthickness=1)
        tk.Label(f, bg="#e0e0e0", relief=tk.GROOVE, bd=1,
                 width=2).grid(row=0, column=0, sticky="nsew")
        for c in range(dessine_colonnes):
            tk.Label(f, text=str(c + 1), bg="#e0e0e0", fg="#444",
                     font=font, relief=tk.GROOVE, bd=1,
                     width=6, anchor="center").grid(
                row=0, column=c + 1, sticky="nsew")
        if plus_colonnes:
            tk.Label(f, text="…", bg="#e0e0e0", fg="#444", font=font,
                     relief=tk.GROOVE, bd=1, width=2,
                     anchor="center").grid(
                row=0, column=dessine_colonnes + 1, sticky="nsew")
        for r in range(dessine_lignes):
            tk.Label(f, text=str(r + 1), bg="#e8e8e8", fg="#444",
                     font=font, relief=tk.GROOVE, bd=1,
                     width=2, anchor="center").grid(
                row=r + 1, column=0, sticky="nsew")
            for c in range(nb_colonnes):
                tk.Label(f, text="", bg=QT_ENTRY_BG,
                         relief=tk.GROOVE, bd=1,
                         width=6 if c < dessine_colonnes else 2).grid(
                    row=r + 1, column=c + 1, sticky="nsew")
        if plus_lines:
            tk.Label(f, text="…", bg="#e8e8e8", fg="#444", font=font,
                     relief=tk.GROOVE, bd=1, width=2,
                     anchor="center").grid(
                row=dessine_lignes + 1, column=0, sticky="nsew")
            for c in range(nb_colonnes):
                tk.Label(f, text="", bg=QT_ENTRY_BG, relief=tk.GROOVE, bd=1,
                         width=6 if c < dessine_colonnes else 2).grid(
                    row=dessine_lignes + 1, column=c + 1, sticky="nsew")
        for c in range(nb_colonnes + 1):
            f.columnconfigure(c, weight=1)
        for r in range(dessine_lignes + (2 if plus_lines else 1)):
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
        self._glissement    = None
        self._drag_origin   = {idx: (event.x_root, event.y_root, gx, gy)}

    def _position_reglee_par_layout(self, props):
        """Le message a afficher quand la position n'appartient pas au widget.

        Un widget range dans une mise en page ne lui doit rien : ecrire sa
        geometrie ne changerait rien a l'execution, et le fichier ne se
        retrouverait plus dans Designer. Plutot que de laisser l'eleve glisser
        dans le vide, on le dit dans la barre d'etat — jamais dans une fenetre
        modalisee — et on lui montre le bouton qui libere la position.
        """
        if props.get("_pose") != "layout":
            return None
        return ("%s est placé par la mise en page — « Libérer la position » "
                "dans le panneau de droite pour le déplacer"
                % props.get("name", "widget"))

    def _on_drag(self, event, idx):
        if self._active_drag != idx:
            return
        ox, oy, gx, gy = self._drag_origin[idx]
        dx = event.x_root - ox
        dy = event.y_root - oy
        if dx == 0 and dy == 0:
            return
        _, props = self.widgets_data[idx]
        mode = self._mode_glissement(props)
        if mode == "refus":
            self._history_notice(self._position_reglee_par_layout(props))
            return
        _, _, gw, gh = props.get("geometry", (0, 0, 100, 30))
        if mode == "reordonner":
            # le geste ne deplace pas le widget : il le reclasse. Rien ne change
            # dans le fichier tant que la souris n'est pas lachee — le cadre
            # suit la main, un trait dit où il tomberait, et le modele attend.
            nx, ny = max(0, gx + dx), max(0, gy + dy)
            self._move_outer_frame(idx, nx, ny, gw, gh)
            freres = self._freres_mobiles(props)
            vers = self._cible_reclassement(props, nx, ny, gw, gh)
            self._glissement = (idx, vers)
            if vers is None:
                self._efface_repere()
                return
            self._dessine_repere(props, freres, vers)
            self._info_lbl.config(
                text="  %s -> position %d sur %d de la mise en page"
                     % (props.get("name", "widget"), vers + 1, len(freres)))
            return
        refus = self._position_reglee_par_layout(props)
        if refus:
            self._history_notice(refus)
            return
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
        glisse = getattr(self, "_glissement", None)
        self._glissement = None
        self._efface_repere()
        if glisse and glisse[0] == idx and self._reclasse(idx, glisse[1]):
            return                      # le reclassement a journalise et redessine
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
        _, props = self.widgets_data[idx]
        refus = self._position_reglee_par_layout(props)
        if refus:
            # la taille non plus n'appartient pas au widget : c'est la mise en
            # page qui la distribue (taille préférée, étirements, marges)
            self._history_notice(refus)
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
        # les deux champs de taille du tableau sont detruits avec les autres :
        # les garder pointerait un Entry qui n'existe plus, et la prochaine
        # coloration se ferait dans le vide (la lecon de l'item 7)
        self._taille_champs = {}
        self._taille_hint = None

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

    def _entry_field(self, label, var, row_idx=0, bloque=False):
        row, bg = self._row_frame(label, row_idx)
        e = tk.Entry(row, textvariable=var,
                     bg="#3c3c3c", fg=PROP_FG,
                     insertbackground=PROP_FG,
                     relief=tk.FLAT, bd=0,
                     font=("TkDefaultFont", 8))
        e.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=4, pady=2)
        if bloque:
            # la valeur reste lisible, elle n'est plus editable : c'est la mise
            # en page qui la decide, et l'eleve doit pouvoir la lire sans
            # croire qu'il peut l'ecrire
            e.config(state=tk.DISABLED, readonlybackground="#3c3c3c")
            tk.Label(row, text="auto", bg=bg, fg=PROP_FG2,
                     font=("TkDefaultFont", 7)).pack(side=tk.RIGHT, padx=2)
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
        reglee = props.get("_pose") == "layout"
        gx, gy, gw, gh = props.get("geometry", (0, 0, 100, 30))
        for lbl, key, val in [("X", "geo_x", gx), ("Y", "geo_y", gy),
                               ("Largeur", "geo_w", gw), ("Hauteur", "geo_h", gh)]:
            v = tk.StringVar(value=str(val))
            self._prop_vars[key] = v
            self._entry_field(lbl, v, R(), bloque=reglee)
            v.trace_add("write",
                lambda *_, k=key, vv=v, i=idx: self._apply_geom(k, vv, i))
        if reglee:
            # les valeurs affichees ne sont pas des faits : ce sont nos estimates
            # de ce que Qt calculera. L'eleve doit le savoir avant d'essayer de
            # les accorder a l'execution.
            tk.Label(self.prop_frame,
                     text=("  Ces valeurs sont réglées par la mise en page et "
                           "ne sont qu'estimées par le concepteur."),
                     bg=PROP_BG, fg=PROP_FG2, justify=tk.LEFT, anchor="w",
                     wraplength=190,
                     font=("TkDefaultFont", 7), pady=2).pack(fill=tk.X, padx=6)
        elif not self._peut_changer_de_pose(props):
            tk.Label(self.prop_frame,
                     text="  Position absolue, écrite dans le fichier.",
                     bg=PROP_BG, fg=PROP_FG2, justify=tk.LEFT, anchor="w",
                     wraplength=190,
                     font=("TkDefaultFont", 7), pady=2).pack(fill=tk.X, padx=6)

        # Basculer la façon dont le widget est placé : c'est la seule réponse
        # honnête à « je n'arrive pas à le déplacer ». Le bouton n'apparait que
        # quand le geste a un sens (une mise en page où revenir).
        etiquette = ("Libérer la position" if reglee else
                     "Remettre dans la mise en page"
                     if self._peut_changer_de_pose(props) else None)
        if etiquette:
            bouton = tk.Label(self.prop_frame, text=" " + etiquette + " ",
                              bg="#3c3c3c", fg=PROP_FG, cursor="hand2",
                              font=("TkDefaultFont", 8), pady=4)
            bouton.pack(fill=tk.X, padx=6, pady=(2, 4))
            bouton.bind("<Button-1>",
                        lambda e, i=idx: self._bascule_position(i))
            bouton.bind("<Enter>", lambda e, w=bouton: w.config(bg="#4a4a4a"))
            bouton.bind("<Leave>", lambda e, w=bouton: w.config(bg="#3c3c3c"))
            self._tooltip(bouton,
                          "Faire décider le widget de sa position, ou laisser "
                          "la mise en page le faire" if reglee else
                          "Rendre la position à la mise en page du conteneur")

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
                self._taille_champs[key] = self._entry_field(lbl, v, R())
                v.trace_add("write",
                    lambda *_, k=key, vv=v, i=idx: self._apply(k, vv, i, int))
            # La raison pour laquelle un nombre refuse ne s'est pas ecrit, sous
            # les deux champs : un chiffre barre silencieusement laisse l'eleve
            # croire que le fichier a garde ce qu'il a tape.
            self._taille_hint = tk.Label(self.prop_frame, text="", bg=PROP_BG,
                                         fg="#ff9a9a", font=("TkDefaultFont", 7),
                                         anchor="w", justify=tk.LEFT)
            self._taille_hint.pack(fill=tk.X, padx=8, pady=(0, 3))

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
        # Un fichier ecrit a la main peut porter un nom que le panneau n'aurait
        # jamais accepte (« class », « __init__ »). Le widget est bien la, mais
        # chacune des lignes ci-dessous, collee telle quelle, serait une erreur
        # de syntaxe dans le programme de l'eleve. Autant le dire ici que d'aligner
        # du code faux sous ses yeux : la rangee de modele reste vide, le nom se
        # corrige juste au-dessus.
        reserve = self._reserve_python(wname)
        methodes = [] if reserve else WIDGET_METHODS.get(cls, [])
        if reserve:
            tk.Label(self.prop_frame,
                     text="  Corrigez le nom ci-dessus pour inserer une ligne",
                     bg=PROP_BG, fg="#c8a24a", anchor="w",
                     font=("TkDefaultFont", 8)).pack(fill=tk.X, pady=2)
        for i, (desc, template, needed) in enumerate(methodes):
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
            saisi = var.get()
            if key in ("rows", "columns"):
                # La porte tient le texte BRUT, avant le cast : un « abc » comme
                # un champ efface doivent etre refusees ET expliquees comme le
                # nombre trop grand, pas s'evanouir dans le ValueError de la
                # conversion — c'est la lecon de l'item 6, appliquee aux tailles.
                if not self._accept_taille(key, saisi, props):
                    return          # et la derniere taille qui s'inscrivait
            value = cast(saisi)
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
            reserve = self._reserve_python(name)
            if not name:
                problems.append("un widget sans nom")
            elif reserve == "mot-cle":
                # Le panneau refuse deja la saisie ; la derniere ligne avant le
                # disque doit le savoir aussi, sinon un fichier ecrit a la main
                # avec « name="class" » partirait tel quel chez Qt.
                problems.append("%s : mot reserve de Python, windows.%s n'est pas "
                                "du code" % (name, name))
            elif reserve:
                problems.append("%s : nom en __double__ reserve par Python, la "
                                "fenetre ne se construirait pas" % name)
            elif not self._valid_qt_name(name):
                problems.append(f"{name} : lettres, chiffres et « _ » uniquement")
            elif name in self._noms_hors_modele():
                # le nom atteint desormais le fichier : un widget qui prendrait
                # le nom d'une mise en page, d'une action ou de la fenetre elle-
                # meme écrase son attribut dans setupUi(), et l'eleve perd un
                # objet sans jamais le voir. Le panneau le refuse deja ; la
                # derniere ligne de controle, elle, doit le savoir aussi.
                # Formatee en un seul bloc, et pas en f-string : le guet aux
                # libelles (test_tr.py) compare des phrases entieres.
                problems.append("%s : la fenetre, une mise en page ou une "
                                "action porte deja ce nom" % name)
            elif len(group) > 1:
                problems.append(f"{name} : {len(group)} widgets portent ce nom")
        return problems

    def _apply_geom(self, key, var, idx):
        try:
            val = int(var.get())
            _, props = self.widgets_data[idx]
            refus = self._position_reglee_par_layout(props)
            if refus:
                # les champs sont grises, mais une touche programmee peut quand
                # meme atteindre la variable : la regle ne doit pas dependre de
                # l'interface
                self._history_notice(refus)
                return
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

    @staticmethod
    def _nom_de_declaration(ligne):
        """Le nom de la propriete d'une declaration CSS, en minuscules sans espaces.

        « color » et « background-color » sont deux proprietes distinctes, et le
        texte « color: » est une sous-chaine de « background-color: ». Comparer
        les lignes au lieu des noms faisait donc disparaitre le fond de l'eleve
        des qu'il choisissait une couleur de texte. La casse et les espaces avant
        les deux-points ne comptent pas : Qt les accepte dans une feuille ecrite
        a la main.
        """
        return ligne.split(":", 1)[0].strip().lower()

    def _set_color(self, idx, css_prop, color):
        _, props = self.widgets_data[idx]
        ss = props.get("styleSheet", "")
        # On remplace la declaration qui porte ce nom-la, et rien d'autre : une
        # feuille peut contenir « border-color », « selection-color » ou un bloc
        # « QPushButton { … } » que le modele ne connait pas — ces lignes-la ne
        # sont pas la couleur en train d'etre changee, elles doivent sortir
        # intactes du geste.
        lines = [l.strip() for l in ss.split(";")
                 if l.strip() and self._nom_de_declaration(l) != css_prop]
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
        self._positionne_un_ajout(new_props)
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