Introduction
===========


The scenario consisting of the energy network (including buildings and links, if any) to be optimized can be defined using either a configuration (or config) file or an excel file. The input config/excel file define the available energy conversion and storage technologies. The associated parameters and sizing limits of the technologies are also defined within the input scenario file, along with the cost and environmental impact assumptions per technology, a path to the demand profiles and weather data files. The purchased electricity cost as well as the emissions of the grid electricity can either be a time series or a constant value. The demand profiles for space heating can be defined statically or alternatively by means of a dynamic linear building model. After preparing the config/excel file, an energy network can be defined in a Python script for optimization.

.. image:: ./resources/optihood_architecture.png
      :width: 1000
      :alt: optihood_architecture

Grid electricity, natural gas, or any other form of energy consumed by the system can be considered as energy sources. An energy source is modelled simply as a “Source” from oemof solph. An energy demand can be related to electricity, space heat and domestic hot water, and is modelled as a “Sink” from oemof solph. In terms of energy conversion and storage technologies, the following are presently implemented: air-source heat pump (ASHP), ground-source heat pump (GSHP), combined heating and power (CHP), solar thermal collector, PV, electric heating rod, gas boiler, electrical battery and thermal storage. 


To summarize, the technologies are classified in three categories:

- Energy inputs: all energy vectors that are energy sources for the systems, e.g. fuels, grid electricity, energy from the environment like solar radiation, etc.
- Energy converters: equipment that converts inputs into usable energy (heat or electricity) for the end consumers
- Energy storages: device to store electricity or heat locally in order to be consumed later.

.. image:: ./resources/energy_types.png
      :width: 800
      :alt: energy_types


Modelling of energy system components
===========

The energy system components can be classified into energy converters and storages. We use constant efficiency models for CHP, gas boiler and electric heating rods, where a fixed efficiency is pre-defined. These fixed efficiencies are defined by the user in the input scenario file. 

Heat pumps
^^^^^^^^^^^^^^^^

Heat pumps (ASHP and GSHP) are modelled based on a bi-quadratic polynomial fit of the  condenser heating power ($\dot{ q }_c$) and the electrical consumption power of the compressor ($\dot{w}_{cp}$)::

\begin{align}
    
    \dot{q}_c = bq_1 + bq_2 \cdot \bar{T}_{e,in} + bq_3 \cdot \bar{T}_{c,out} + bq_4 \cdot \bar{T}_{e,in} \cdot{\bar{T}_c,out} + bq_5 \cdot \bar{T}^2_{e,in} + bq_6 \\
    \dot{w}_{cp} = bp_1 + bp_2 \cdot \bar{T}_{e,in} + bp_3 \cdot \bar{T}_{c,out} + bp_4 \cdot \bar{T}_{e,in} \cdot \bar{T}_{c,out} + bp_5 \cdot \bar{T}^2_{e,in} + bp_6 \cdot \bar{T}^2_{c,out}

\end{align}

where, $T_{e,in}$ and $T_{c,out}$ are fluid temperatures at the inlet of the evaporator and the outlet of the condenser, respectively. $\bar{T}$ denotes the normalized temperature and is defined as $\bar{T} = \frac{T[^° C]}{273.15}. For the
solution of the system of equations the Brent solver is used [2]. The polynomial coefficients $b_{qi}$ and
$b_{pi}$ are calculated from the catalog heat pump data using the multidimensional least square fitting
algorithm of Scipy [3] in Python.
A reduced model can be proposed:

      \begin{align}
    
          \dot{q}_c = bq_1 + bq_2 \cdot \bar{T}_{e,in} + bq_3 \cdot \bar{T}_{c,out}  \\
          \dot{w}_{cp} = bp_1 + bp_2 \cdot \bar{T}_{e,in} + bp_3 \cdot \bar{T}_{c,out}
      \end{align}


However, this model is still non-linear. A way to overcome the non-linearity would be to fix the $\bar{T}_{c,out}$ to 35 °C and 65 °C, respectively, for space heating (SH) and domestic hot water (DHW).

.. image:: ./resources/HP_model_param.png
      :width: 800
      :alt: HP_model_param

Polynomial fit analysis for heat pump model
~~~~~~~~~~~~~~~~~~~~~~~

.. image:: ./resources/HP_figures.png
      :width: 800
      :alt: HP_figures

.. image:: ./resources/HP_figures_1.png
      :width: 800
      :alt: HP_figures_1

.. image:: ./resources/HP_table2.png
      :width: 800
      :alt: HP_table2

.. image:: ./resources/HP_table3.png
      :width: 800
      :alt: HP_table3

.. image:: ./resources/HP_table4.png
      :width: 800
      :alt: HP_table4

.. image:: ./resources/HP_figure_4_5.png
      :width: 800
      :alt: HP_figure_4_5

.. image:: ./resources/HP_table5.png
      :width: 800
      :alt: HP_table5

Other energy systems
^^^^^^^^^^^^^^^^

Solar thermal collectors and PV modules production profiles are pre-calculated before the optimization. For batteries, a simple model is used that accounts for fixed charging and discharging efficiencies and a loss parameter. For thermal storages, a stratified thermal storage model with two temperature zones is used.