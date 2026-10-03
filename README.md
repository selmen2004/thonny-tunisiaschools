# thonny-tunisiaschools

A Thonny plug-in which offers Tunisian computer science secondary teachers / students some help creating Python & PyQt Applications:

- loads QT UI file and :

  - adds needed code to load that file to current document:

  - creates empty functions binded to buttons’ clicks
 
  ![image](https://github.com/selmen2004/thonny-tunisiaschools/assets/3520243/4e4037a8-3157-4f09-99db-1b4543bb6233)
 
  - Adds a view that displays the UI inside Thonny (currently supporting Labels , Text inputs and ttons only )
 
![image](https://github.com/selmen2004/thonny-tunisiaschools/assets/3520243/a3bdb491-6f31-4b92-a5eb-d2842eec95f1)


- adds on new menu (PyQt5) commands to insert call to usual functions ( text , setText , clear , show ) if widget is Label or LineEdit ( as in Tunisian Curriculum )

![image](https://github.com/selmen2004/thonny-tunisiaschools/assets/3520243/3bbd2794-c3f1-4425-92d2-6b5b1933f897)


- changes save location to c:/bac2024 as needed for final exams (baccalaureat)

- disables opening last open files (to reduce risks of students overwriting other students work)
