from setuptools import setup
import os.path
import sys

setupdir = os.path.dirname(__file__)

requirements = []
for line in open(os.path.join(setupdir, "requirements.txt"), encoding="UTF-8"):
    if line.strip() and not line.startswith("#"):
        requirements.append(line)

setup(
    name="thonny-tunisiaschools",
    version="1.0.0",
    description="A plug-in which offers Tunisian computer science secondary teachers / students some help creating Python & PyQt Applications. ",
    long_description="""A Thonny plug-in which offers Tunisian computer science secondary teachers / students some help creating Python & PyQt Applications: 
* loads QT UI file and :
  * adds needed code to load that file to current document
  * creates empty functions binded to buttons' clicks
  * adds on new menu (PyQt5) commands to insert call to usual functions ( text , setText , clear , show ) if widget is Label or LineEdit ( as in Tunisian Curriculum )
* changes save location to c:/bac2023 as needed for final exams

More info: https://github.com/selmen2004/thonny-tunisiaschools/""",
    url="https://github.com/selmen2004/thonny-tunisiaschools",
    author="Selmen Arous",
    author_email= "selmen.arous@gmail.com",
    license="GPL",
    classifiers=[
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "License :: Freeware",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Education",
        "Topic :: Software Development",
    ],
    keywords="PyQt QT Tunisia School Teaching Education",
    platforms=["Windows", "macOS", "Linux"],
    python_requires=">=3.7",
    package_data={
        "thonnycontrib.tunisiaschools": ["res/*"]
    },
    
    py_modules=["tunisiaschools"],
    packages=["thonnycontrib.tunisiaschools"],
)
