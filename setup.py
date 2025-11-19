from setuptools import setup, find_packages
import subprocess
import pathlib as _pl

with open("README.md", "r") as fh:
    long_description = fh.read()


# Fetch latest tag
# latest_tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"]).strip().decode("utf-8")


def _getInstallRequirements():
    requirementsFile = (
            _pl.Path(__file__).parent / "requirements" / "requirements.in"
    )
    lines = requirementsFile.read_text().split("\n")
    requirements = [l for l in lines if l.strip() and not l.startswith("#")]
    print("")
    print(requirements)
    print("")
    return requirements


setup(
    name='optihood',
    packages=find_packages(),
    version='v0.2.4',
    author="Institute for Solar Technology (SPF), OST Rapperswil",
    author_email="neha.dimri@ost.ch",
    description="optihood optimization framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://optihood.readthedocs.io",
    install_requires=_getInstallRequirements(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.12",
)
