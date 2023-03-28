.. optihood documentation master file, created by
   sphinx-quickstart on Tue Oct 22 16:02:17 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

optihood
========

optihood provides a complete python-based framework to OPTImize the investment in alternative energy
technologies (heat pump, solar thermal, PV, etc.) as well as the operation of available energy resources (natural gas,
sun, grid electricity, etc.) at a neighbourHOOD-scale. It is designed to facilitate the researchers and energy planners
in optimizing an energy neighbourhood in terms of cost and/or environmental criteria. It enables the users to perform
both single-objective and multi-objective optimization and analysis. The energy model and it's associated parameters
can be defined easily using an excel file. Additionally, a variety of plotting methods are defined for easy and fast
result visualization.

The package was developed at the `SPF - Institute for Solar Technology <https://www.spf.ch/>`_ at the `OST - Eastern
Switzerland University of Applied Sciences <https://www.ost.ch/>`_ and `Haute Ecole d'Ingénierie et de Gestion du Canton Vaud <https://heig-vd.ch/>`_.

.. image:: ./guide/resources/spf_logos.svg
      :width: 500
      :alt: spf_logos

.. image:: ./guide/resources/heig_logo.svg
      :width: 200
      :scale: 40 %
      :alt: heig_logo
      :align: right



Table of contents
=================

.. toctree::
   :maxdepth: 2

   guide/getting_started
   guide/defining_an_energy_network
   guide/optimizing_the_energy_network
   guide/processing_results
   guide/models
   guide/advanced_under_development_features
   Code Reference <modules>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Developers
^^^^^^^^^^

- SPF Institute for Solar Technology, Rapperswil, Switzerland
- HEIG VD, Yverdon-les-Bains, Switzerland

Acknowledgements
^^^^^^^^^^^^^^^^
This framework was created in 2021 and made open-source in 2022. We would like to thank the Swiss Federal Office Of Energy
(SFOE) for the support and funding received in the projects OptimEase and SolHood which allowed us to spend efforts in
developing and sharing the code and becoming a part of the open-source community.
