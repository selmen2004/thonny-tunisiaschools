import os
import tkinter as tk
from xml.etree import ElementTree as ET
from thonny import get_workbench
from thonny.languages import tr

class UiViewerPlugin(tk.Frame):
    def __init__(self, master):
        super().__init__(master)  # Provide empty tuple for columns
        self.ui_file = None  # Store the current UI file path
        self.create_widgets()

    def create_widgets(self):
        if self.ui_file:
            if os.path.exists(self.ui_file):
                self.label_file_name = tk.Label(self, text="Ceçi est un aperçu du fichier : "+self.ui_file, anchor="w")
                self.label_file_name.pack(fill="x")
                widgets = self.load_ui_file(self.ui_file)
                self.create_tkinter_widgets( widgets)
            else:
                print(f"File '{self.ui_file}' does not exist.")
        else:
            print("No UI file specified.")

    def load_ui_file(self, ui_file):
        root = ET.parse(ui_file).getroot()
        widgets = []
        for widget_elem in root.findall(".//widget"):
            class_name = widget_elem.attrib.get("class")
            widget = {"class": class_name}
            
            name = widget_elem.attrib.get("name")
            properties = {"name": name}
            for property_elem in widget_elem.findall(".//property"):
                property_name = property_elem.get("name")
                if property_name == "geometry":
                    geometry = property_elem.find("rect")
                    properties["geometry"] = tuple(map(int, (geometry.find("x").text, geometry.find("y").text, 
                                                              geometry.find("width").text, geometry.find("height").text)))
                elif property_name == "font":
                    font = property_elem.find("font")
                    properties["font"] = ("", int(font.find("pointsize").text))  # Assuming default font family
                elif property_name == "text":
                    properties["text"] = property_elem.find("string").text
            widgets.append((class_name, properties))
        return widgets

    def create_tkinter_widgets(self, widgets):
        for widget_class, properties in widgets:
            widget_text = properties.get("text", "")
            widget_geometry = properties.get("geometry", (0, 0, 100, 30))  # Default geometry
            widget_font = properties.get("font", ("", 10))  # Default font size

            # Extract geometry properties
            x, y, width, height = widget_geometry
            widget_label = tk.Label(self, text=tr("Name") + ": "+properties.get("name") ,  bg="green", fg="white", font=("TkDefaultFont", 8))
            widget_label.place(x=x, y=y - 20)
            if widget_class == "QLabel":
                # Create a label with the specified text, geometry, and font
                label = tk.Label(self, text=widget_text)
                label.place(x=x, y=y, width=width, height=height)
                label.config(font=("TkDefaultFont", widget_font[1]))  # Set the font size

            elif widget_class == "QPushButton":
                # Create a button with the specified text, geometry, and font
                tk.Button(self, text=widget_text).place(x=x, y=y, width=width, height=height)

            elif widget_class == "QLineEdit":
                # Create a line edit with the specified text, geometry, and font
                tk.Entry(self, text=widget_text).place(x=x, y=y, width=width, height=height)

            elif widget_class == "QTextEdit":
                # Create a text edit with the specified text, geometry, and font
                text_edit = tk.Text(self)
                text_edit.insert(tk.END, widget_text)
                text_edit.place(x=x, y=y, width=width, height=height)
    def destroy_widgets(self):
        for widget in self.winfo_children():
            widget.destroy()
        
    def load_new_ui_file(self, new_ui_file):
        self.ui_file = new_ui_file
        self.destroy_widgets()  # Destroy existing widgets
        self.create_widgets()   # Load and create widgets for the new UI file

