import os
from datetime import date
from thonny import get_workbench
from thonny.languages import tr
from thonny.misc_utils import get_user_site_packages_dir_for_base
from thonny.ui_utils import select_sequence,askopenfilename
from .UIViewer import UiViewerPlugin

from xml.dom import minidom
global qt_ui_file
qt_ui_file =""

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
                filetypes=[("Fichiers UI", ".ui"), (tr("Tous les fichiers"), ".*")], parent=get_workbench()
            )
    if path:
        global qt_ui_file
        qt_ui_file = path
        get_workbench().get_menu("PyQt5").delete(1, "end")
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
                
            

        get_workbench().get_editor_notebook().get_current_editor().get_code_view().text.insert(
            '0.0','from PyQt5.uic import loadUi\n'+
            'from PyQt5.QtWidgets import QApplication\n'+
            '\n'+mytxt+'\n'+
            'app = QApplication([])\n'+
            'windows = loadUi ("'+ path +'")\n'+
            'windows.show()\n'+
            btnstxt+'\n'
            'app.exec_()'
            )
def open_in_designer():
    """
        Opens a file with a specified program.

        Args:
        - file_path: Path to the file to be opened.
        - program_locations: List of paths where the program can be found.

        Returns:
        - True if the file was successfully opened with the program, False otherwise.
        """
    #program should use most of the known qt designer locations
    #@TODO : improve designer  dir discovery
    program_locations = [ "pyqt5_qt5_designer.exe",#selmen designer bundle
                         
                          #fmain.io designer bundle 
                          "C:\\Program Files (x86)\\Qt Designer\\designer.exe"
                          "C:\\Program Files\\Qt Designer\\designer.exe"
                          "designer.exe",#any designer.exe in path env var
                          #fallback : thonny own python runner with qt5 bins
                          #os.path.join(get_thonny_user_dir() , "qt5_applications\\Qt\\bin\\designer.exe")
                          
                          ] 

    global qt_ui_file
    for location in program_locations:

        
        
        if os.path.exists(location) or location== "pyqt5_qt5_designer.exe" or location== "designer.exe" :
            try:
                print("running ", f'"{location}" "{qt_ui_file}"', " ...")
		if qt_ui_file=="":
			os.system(f'"{location}"')
		else:
                	os.system(f'"{location}" "{qt_ui_file}"')
                return True
            except Exception as e:
                print(f"Error: {e}")
    
    print("Error: Designer not found.")
    return False


def load_plugin():
    get_workbench().add_view(UiViewerPlugin, tr("QT UI Viewer"), "s")
    
    
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
    get_workbench().add_command(
        "pyqt5_open_in_designer",
        "PyQt5",
        tr("Ouvrir dans Designer"),
        open_in_designer,
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
