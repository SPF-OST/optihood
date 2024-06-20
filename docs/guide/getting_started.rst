.. _getting_started:

Getting Started
===============

Prerequisites
-------------

In order to use optihood, the following prerequisites are needed on your machine:

- `Python >=3.9 <https://www.python.org/downloads/>`_ is installed. Python 3.12 is recommended.
- Git is installed.
- An active `Github <https://github.com/>`_ account to clone the repo.
- A solver is installed. `Gurobi solver <https://www.gurobi.com/resource/parallelism-linear-mixed-integer-programming/>`_ is recommended, although other solvers like CBC, GLPK, Cplex could also be used.

Installation
------------

As of now, optihood is available as an open source code and needs to be installed from source. Please follow the
instructions mentioned below to complete the installation. The commands given below are suited for the Windows platform
and should be run from within the optihood directory in a Command Prompt. For other platforms, similar alternative
commands could be used.

1. Clone the optihood repo to a folder called 'optihood' on your local machine::

    git clone https://github.com/SPF-OST/OptiHood.git

2. All the next commands should be run from within the optihood folder. Create a virtual environment and activate it::

    py -3.12 -m venv venv
    venv\Scripts\activate

   If using python version other than 3.12, replace -3.12 with -3.X (3.X being the python version).

3. Install the requirements into the created virtual environment::
    
    pip install wheel
    pip install -r requirements.txt

    It might be required to install C++ build tools. To do that, click on the link that appears with the error message and follow the instructions (it is the lapack package that is missing). In order to be able to install the missing package, it is required to have a complete Visual Studio instance and installing it with the "Desktop development with C++" workload.
    The requirements.txt file needs Python 3.12. If using another version, use pip tools to compile the provided requirements.in file before installing the requirements.

4. Verify the installation of the oemof package and the solver by running the installation test in your virtual environment::

    oemof_installation_test

   If the installation is successful the following message would be displayed (the installed solver would be shown as working)::
        
    *****************************
    Solver installed with oemof:

    cbc: not working
    glpk: not working
    gurobi: working
    cplex: not working

    *****************************
    oemof successfully installed.
    *****************************

5. To test whether the installation worked well, you could run a `basic example <https://github.com/SPF-OST/OptiHood/tree/main/data/examples/>`_.


Setting up your optimization model
----------------------------------

Optihood offers several functionalities to define an energy network, optimize it and visualize the results, which
provides the user with a complete framework for optimization without the need to code by hand. You could learn more
about using optihood by walking through the remaining sections of the documentation:

.. toctree::
    :maxdepth: 2
   defining_an_energy_network
