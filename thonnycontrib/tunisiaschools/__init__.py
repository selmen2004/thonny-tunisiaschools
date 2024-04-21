import os
from datetime import date
from thonny import get_workbench
from thonny.languages import tr
from thonny.ui_utils import select_sequence,askopenfilename


from xml.dom import minidom


def usefull_commands(w):
    def add_cmd(w ,id, label , fct ):
        get_workbench()._publish_command(
                    "pyqt_text_"+w.attributes['name'].value+id,
                    "PyQt5",
                    label +w.attributes['name'].value ,
                    lambda: get_workbench().get_editor_notebook().get_current_editor().get_code_view().text.insert('insert',"windows."+w.attributes['name'].value +fct)
                )
    add_cmd(w,"text","Contenu de ",".text()")
    add_cmd(w,"settext","Changer le contenu de ",".setText()")
    add_cmd(w,"clear","Effacer le contenu de ",".clear()")
    add_cmd(w,"show","Afficher ",".show()")

    
    
def add_pyqt_code():
    
    btnstxt = ""
    mytxt = ""
    path = askopenfilename(
                filetypes=[("Fichiers UI", ".ui"), (tr("all files"), ".*")], parent=get_workbench()
            )
    if path:
        get_workbench().get_menu("PyQt5").delete(1, "end")
        UiViewerPlugin
        file = minidom.parse(path)
        widgets = file.getElementsByTagName('widget')
        for w in widgets:
            if w.attributes['class'].value == "QPushButton" : #Bouton
                btnstxt = btnstxt + "windows."+w.attributes['name'].value +".clicked.connect ( "+  w.attributes['name'].value +"_click )\n"
                mytxt = mytxt + "def "+  w.attributes['name'].value +"_click():\n    pass\n" 
            elif w.attributes['class'].value in [ "QLineEdit", "QLabel"] : #Zone de texte ou Libellé
                #btnstxt = btnstxt + "windows."+w.attributes['name'].value +".clicked.connect ( "+  w.attributes['name'].value +"_click )"+chr(13)+chr(10)
                usefull_commands(w)
                
            

        get_workbench().get_editor_notebook().get_current_editor().get_code_view().text.insert('0.0','''from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication

'''+mytxt+'''

app = QApplication([])
windows = loadUi ("'''+ path +'''")
windows.show()
'''+btnstxt+'''
app.exec_()'''
)


def load_plugin():
    
    
    image_path = os.path.join(os.path.dirname(__file__), "res", "qt_16.png")
    get_workbench().add_command(
        "selmen_command",
        "PyQt5",
        tr("Ajouter code PyQt5"),
        add_pyqt_code,
		default_sequence=select_sequence("<Control-Shift-B>", "<Command-Shift-B>"),
        include_in_toolbar = True,
		caption  = "PyQt",
        image = image_path
    )
    # Changement de dossier de sauvegarde : 

    # en cas ou la date est erroné sur le pc
    if date.today().year < 2024 :
        cwd = 'C:\\bac2024'
    else:
        cwd = 'C:\\bac'+str(date.today().year)
    if not os.path.exists(cwd):
        os.makedirs(cwd)
    get_workbench().set_local_cwd(cwd)

    # Ne pas ouvrir les derniers fichiers 

    get_workbench().set_option("file.current_file", "")
    get_workbench().set_option("file.open_files", "")