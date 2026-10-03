# thonny-tunisiaschools

A Thonny plug-in for Tunisian computer-science secondary teachers and students:
it lets a class build a PyQt5 interface without leaving Thonny, and it writes
the Python that goes with it.

## What it adds

**A `.ui` editor inside Thonny** — the *QT UI Viewer* view. Open a Qt Designer
file and work on it directly: place, move, duplicate and delete widgets, put
them in a layout, rename them (with the names the pupil will type in his own
program), edit text, placeholder, window title, colours and fonts, resize
tables, and save. Every gesture is written back into the `.ui` file in the form
Qt Designer and `loadUi()` expect, so a file produced here opens in Designer
unchanged and a file produced in Designer opens here.

**A PyQt5 menu** with four commands:

- *Ajouter Annexe* — pastes the skeleton of a PyQt5 program (imports,
  `QApplication`, `loadUi()`, `show()`, one `clicked.connect`, `exec_()`) with
  three blanks for the pupil to fill — `Nom_Interface.ui`, `Nom_Bouton`,
  `Nom_Module` — for the exercises that come with no interface file.
- *Ajouter Annexe + interface* — opens a `.ui` file and inserts the matching
  program: the `loadUi()` call, `windows.show()`, and for each button a
  `clicked.connect` plus its empty handler.
- *Ouvrir dans Designer* — hands the current `.ui` to Qt Designer, looking for
  Designer in the places it can actually be (PATH, the `pyqt5-qt5-designer`
  package, the Qt binaries next to Thonny's own, the folder a teacher chose) and
  offering to install the package when nothing is found.
- *Configurer Designer* — remembers the Designer executable in Thonny's own
  configuration.

The menu also grows one command per widget of the file currently open, for the
calls the curriculum uses on a `QLabel` or a `QLineEdit`: `text()`, `setText()`,
`clear()`, `show()`.

**The exam folder.** Thonny's working directory becomes `C:\bac<session>`, where
the session is that of the *next* June baccalaureate — a class working in the
2026-2027 school year is prepared for June 2027 and files into `C:\bac2027`.
Reopening the previous session's files at startup is turned off, so students
cannot overwrite each other's work.

## Requirements

Thonny 3.2.1 or newer, and PyQt5 in the interpreter Thonny uses — the generated
programs import it. The viewer itself is pure Tk, so editing a `.ui` file needs
no Qt at all; Qt Designer is optional, and the plug-in can install the
`pyqt5-qt5-designer` package for you.

## Installing

`pip install thonny-tunisiaschools` into the Python Thonny uses (or, in Thonny,
*Tools → Manage packages*). Thonny discovers it under the `thonnycontrib`
namespace on the next start; the commands appear in a *PyQt5* menu and the view
in *View*.

## Running the test battery

The repository carries 29 headless suites and 7 mutant graders under `tests/`.
They drive the real `UIViewer`/`__init__` sources and, for the Qt-side checks, an
offscreen PyQt5 — so run them with an interpreter that can import PyQt5, which
on a school machine means Thonny's own bundle:

    <Thonny>\python.exe -u -B tests\run_all.py

Paths are derived, not hardcoded: the plug-in is found relative to the
repository, and the Thonny bundle from `THONNY_BUNDLE`, else the interpreter
running the suites, else `%LOCALAPPDATA%\Programs\Thonny`. Nothing needs to be
installed first.

The graders are separate (`tests/mutants_*.py`): each deliberately breaks one
guard in a copy of the sources and checks that a suite notices.

    <Thonny>\python.exe -B tests\mutants_actions.py

## Screenshots

The screenshots that used to sit here showed the first version of the viewer,
which only rendered labels, inputs and buttons. Fresh ones are owed.

## Licence

GPL version 3.
