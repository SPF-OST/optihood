from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='optihood',
    packages=find_packages(),
    #version="0.1",
    author="Institute for Solar Technology (SPF), OST Rapperswil",
    author_email="neha.dimri@ost.ch",
    description="optihood optimization framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://optihood.readthedocs.io",
    install_requires=["bokeh", "configparser", "python-dateutil", "matplotlib", "numpy", "oemof.solph==0.4.4",
                      "oemof.thermal", "openpyxl", "pandas", "plotly", "pvlib", "Pyomo", "scipy", "xlrd", "xlwt"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    setup_requires=["setuptools-git-versioning"],
    python_requires="==3.9",
)