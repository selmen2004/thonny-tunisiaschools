from setuptools import setup
import os.path
import sys

setupdir = os.path.dirname(__file__)

requirements = []
for line in open(os.path.join(setupdir, "requirements.txt"), encoding="UTF-8"):
    if line.strip() and not line.startswith("#"):
        requirements.append(line)

setup(
    author='Selmen Arous',
    author_email='selmen.arous@gmail.com',
    
    url="https://github.com/selmen2004/thonny-tunisiaschools",

    
    
    
    platforms=["Windows", "macOS", "Linux"],
    python_requires=">=3.7",
    package_data={
        "thonnycontrib.tunisiaschools": ["res/*"]
    },
    
    py_modules=["tunisiaschools"],
    packages=["thonnycontrib.tunisiaschools"],
)
