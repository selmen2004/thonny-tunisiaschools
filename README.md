# thonny-tunisiaschools

A Thonny plug-in which offers Tunisian computer science secondary teachers / students some help creating Python & PyQt Applications:

- loads QT UI file and :

  - adds needed code to load that file to current document

  - creates empty functions binded to buttons’ clicks
 
  - Adds a view that displays the UI inside Thonny (currently supporting Labels , Text inputs and ttons only )

  - adds on new menu (PyQt5) commands to insert call to usual functions ( text , setText , clear , show ) if widget is Label or LineEdit ( as in Tunisian Curriculum )

- changes save location to c:/bac2024 as needed for final exams (baccalaureat)

- disables opening last open files (to reduce risks of students overwriting other students work)
