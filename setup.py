from setuptools import setup, find_packages
import subprocess

with open("README.md", "r") as fh:
    long_description = fh.read()

# Fetch latest tag
latest_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"]).strip().decode("utf-8")

setup(
    name='optihood',
    packages=find_packages(),
    version=latest_tag,
    author="Institute for Solar Technology (SPF), OST Rapperswil",
    author_email="neha.dimri@ost.ch",
    description="optihood optimization framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://optihood.readthedocs.io",
    install_requires=["bokeh", "configparser", "python-dateutil", "matplotlib", "numpy", "oemof.solph",
                      "oemof.thermal", "openpyxl", "pandas", "plotly", "pvlib", "Pyomo", "scipy", "xlrd", "xlwt"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    #setup_requires=["setuptools-git-versioning"],
    python_requires=">=3.12",
)