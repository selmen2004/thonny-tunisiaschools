"""PyQt5 doit charger les fichiers produits a partir d'un fichier a layouts."""
import os
import sys

import chemins

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
BUNDLE = chemins.BUNDLE
sys.path.insert(0, os.path.join(BUNDLE, "Lib", "site-packages"))
HERE = os.path.dirname(os.path.abspath(__file__))

from PyQt5 import QtWidgets, QtCore, uic  # noqa: E402

fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


app = QtWidgets.QApplication([])

for label, path in (("sans modification", os.path.join(HERE, "out_unchanged.ui")),
                    ("modifie", os.path.join(HERE, "out_edited.ui"))):
    print("=== loadUi %s (%s) ===" % (label, os.path.basename(path)))
    try:
        w = uic.loadUi(path)
    except Exception as e:
        check(False, "loadUi a echoue : %r" % e)
        continue
    check(w.objectName() == "Dialog", "nom de la fenetre : %s" % w.objectName())
    check(w.windowTitle() == "Gestion des eleves",
          "titre : %s" % w.windowTitle())
    for name in ("label", "lineEdit", "comboClasse", "checkPresent",
                 "groupNotes", "btnValider", "tableNotes", "btnQuitter"):
        check(hasattr(w, name), "widget present : %s" % name)
    check(w.label.text() in ("Nom :", "Nom complet :"),
          "texte du label : %r" % w.label.text())
    check(w.checkPresent.isChecked() is True,
          "checkbox cochee preservee : %s" % w.checkPresent.isChecked())
    check(w.lineEdit.placeholderText() == "Saisir le nom",
          "placeholder preserve")
    check(w.comboClasse.count() in (2, 3),
          "combo : %d elements" % w.comboClasse.count())
    check(w.tableNotes.columnCount() == 2,
          "table : %d colonnes" % w.tableNotes.columnCount())
    check(w.tableNotes.rowCount() in (1, 4),
          "table : %d lignes" % w.tableNotes.rowCount())
    check(w.tableNotes.horizontalHeaderItem(0).text() == "Matiere",
          "titre de colonne conserve")
    check(w.tableNotes.verticalHeaderItem(0).text() == "Maths",
          "titre de ligne conserve")
    cell = w.tableNotes.item(0, 0)
    check(cell is not None and cell.text() == "Physique",
          "cellule conservee : %s" % (cell.text() if cell else None))
    # les widgets doivent etre parentés du dialogue, pas flottants
    check(w.btnQuitter.parent() is not None, "btnQuitter est bien rattache")
    check(isinstance(w.groupNotes.layout(), QtWidgets.QGridLayout),
          "le QGroupBox garde sa grille : %s"
          % type(w.groupNotes.layout()).__name__)
    check(isinstance(w.parent() if False else w.findChild(QtWidgets.QVBoxLayout),
                     QtWidgets.QVBoxLayout),
          "le dialogue garde son QVBoxLayout")
    w.show()
    geo = w.geometry()
    check(geo.width() > 0 and geo.height() > 0,
          "rendu : %dx%d" % (geo.width(), geo.height()))
    # la connexion du fichier doit fonctionner
    w.btnQuitter.click()
    check(not w.isVisible(), "connection clicked()->close() appliquee")
    if label == "modifie":
        check(w.btnAjoute.text() == "Ajouter", "widget ajoute charge")
        check(not hasattr(w, "labelClasse"), "widget supprime vraiment absent")

print()
print("RESULTAT : %d echecs" % len(fails))
for f in fails:
    print("   -", f)
sys.exit(1 if fails else 0)
