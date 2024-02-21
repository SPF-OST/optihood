.. _energy_system_component_models:

Introduction
============

The optihood framework was implemented within this project and extended within the SFOE-sponsored project SolHOOD7. It is written in Python programming language and based on oemof (open energy modelling framework). In oemof, an energy system is defined as a combination of linear component models of different types namely, sources, transformers, sinks, and buses. The components models are linked together using flow objects which may have associated costs (optional) to formulate the target function to optimize. Then, Oemof makes use of pyomo, an open-source modelling language for optimization solutions, to define a MILP optimization problem. The framework optihood offers a flexible and easy-to-use environment with several useful features for a neighborhood beyond what oemof can provide. The basic construct of oemof is modified in a sense that the components are grouped by buildings and the results (time series of energy production/consumption, costs, emissions, etc.) can be obtained per building. 

Grid electricity, natural gas, or any other form of energy consumed by the system can be considered as energy sources. An energy source is modelled simply as a “Source” from oemof solph. An energy demand can be related to electricity, space heat and domestic hot water, and is modelled as a “Sink” from oemof solph. In terms of energy conversion and storage technologies, the following are presently implemented: air-source heat pump (ASHP), ground-source heat pump (GSHP), combined heating and power (CHP), solar thermal collector, PV, electric heating rod, gas boiler, electrical battery and thermal storage. 


.. image:: ./resources/optihood_architecture.png
      :width: 800
      :alt: optihood_architecture


To summarize, the technologies are classified in three categories:

- Energy inputs: all energy vectors that are energy sources for the systems, e.g. fuels, grid electricity, energy from the environment like solar radiation, etc.
- Energy converters: equipment that converts inputs into usable energy (heat or electricity) for the end consumers
- Energy storages: device to store electricity or heat locally in order to be consumed later.

.. image:: ./resources/energy_types.png
      :width: 800
      :alt: energy_types


Modelling of energy system components
=====================================

The energy system components can be classified into energy converters and storages. We use constant efficiency models for CHP, gas boiler and electric heating rods, where a fixed efficiency is pre-defined. These fixed efficiencies are defined by the user in the input scenario file. 

Heat pumps
----------

Heat pumps (ASHP and GSHP) are modelled based on a bi-quadratic polynomial fit of the  condenser heating power (:math:`\dot{ q }_c`) and the electrical consumption power of the compressor (:math:`\dot{w}_{cp}`):

.. math::

    &\dot{q}_c = bq_1 + bq_2 \cdot \bar{T}_{e,in} + bq_3 \cdot \bar{T}_{c,out} + bq_4 \cdot \bar{T}_{e,in} \cdot{\bar{T}_c,out} + bq_5 \cdot \bar{T}^2_{e,in} + bq_6 \\
    &\dot{w}_{cp} = bp_1 + bp_2 \cdot \bar{T}_{e,in} + bp_3 \cdot \bar{T}_{c,out} + bp_4 \cdot \bar{T}_{e,in} \cdot \bar{T}_{c,out} + bp_5 \cdot \bar{T}^2_{e,in} + bp_6 \cdot \bar{T}^2_{c,out}


where, :math:`T_{e,in}` and :math:`T_{c,out}` are fluid temperatures at the inlet of the evaporator and the outlet of the condenser, respectively. :math:`\bar{T}` denotes the normalized temperature and is defined as :math:`\bar{T} = \frac{T[^{\circ} \text{C}]}{273.15}`. For the
solution of the system of equations the Brent solver is used [2]. The polynomial coefficients :math:`b_{qi}` and
:math:`b_{pi}` are calculated from the catalog heat pump data using the multidimensional least square fitting
algorithm of Scipy [3] in Python.


Table 1: Parameters, inputs and outputs of heat pump model.

.. image:: ./resources/HP_model_param.png
      :width: 600
      :alt: HP_model_param


Polynomial fit analysis for heat pump model

.. image:: ./resources/R410A-predict-Cop-1.png
      :width: 600
      :alt: R410A-predict-Cop
Figure 1: Typical coefficient of performance map (COP) for a R410A heat pump obtained using the two equations above.


.. figure:: ./resources/R410A-Qcond-1.png
   :width: 400
   :alt: R410A-Qcond
Figure 2: Differences between experimental and fitted data using the full polynomial formulation from
the two equations above for condenser heat.

.. figure:: ./resources/R410A-COP-1.png
   :width: 400
   :alt: R410A-COP
Figure 3: Differences between experimental and fitted data using the full polynomial formulation from
the two equations above for coefficient of performance (COP).


However, this model is non-linear. A way to overcome the non-linearity would be to fix the :math:`\bar{T}_{c,out}` to 35 °C and 65 °C, respectively, for space heating (SH) and domestic hot water (DHW). Thus we would use for example:


.. math::

      \dot{q}_c = bq_1 + bq_2 \cdot \bar{T}_{e,in} + bq_3 \cdot \frac{35}{273.15}  + bq_4 \cdot \bar{T}_{e,in} \cdot \frac{35}{273.15} + bq_5 \cdot \bar{T}_{e,in}^2 + bq_6 \cdot \frac{35}{273.15}^2 


.. math::

      \dot{w}_{cp} = bp_1 + bp_2 \cdot \bar{T}_{e,in} + bp_3 \cdot \frac{35}{273.15}  + bp_4 \cdot \bar{T}_{e,in} \cdot \frac{35}{273.15} + bp_5 \cdot \bar{T}_{e,in}^2 + bp_6 \cdot \frac{35}{273.15}^2 

The fitted data for the HP08L-M-BC air/water heat pump using the proposed approach described by
the two equations above are provided in Fig. 4-5 and Table 2, while the fitted heat pump coefficients are given in
Table 3. While, the fitted data for the ProDomo13-R410A brine/water heat pump using the proposed
approach described by the two equations above are provided in Fig. 6-7 and Table 4, while the fitted heat pump
coefficients are given in Table 5.

Table 2: Differences between experiments and fitted data for the HP08L-M-BC air/water heat pump using the two equations above. :math:`error=100 \cdot |\frac{Q_{exp}-Q_{num}}{Q_{exp}}|` and :math:`RMS = \sqrt { \sum{\frac{(Q_{exp}-Q_{num})^2}{n_p}} }` where :math:`n_p` is the number of data points.

.. image:: ./resources/HP_table2_new.png
      :width: 800
      :alt: HP_table2


Table 3: Fitted coefficients for the HP08L-M-BC air/water heat pump using the two equations above.

.. image:: ./resources/HP_table3.png
      :width: 600
      :alt: HP_table3

.. image:: ./resources/HP08L-M-BC-COP-1.png
      :width: 400
      :alt: HP08L-M-BC-COP-1
Figure 4: Differences between experimental and fitted data of HP08L-M-BC air/water heat pump using
the proposed approach from the two equations above for coefficient of performance
(COP).

.. image:: ./resources/HP08L-M-BC-Qcond-1.png
      :width: 400
      :alt: HP08L-M-BC-Qcond-1
Figure 5: Differences between experimental and fitted data of HP08L-M-BC air/water heat pump using
the proposed approach from the two equations above for condenser heat.

.. image:: ./resources/ProDomo13-R410A-COP-1.png
      :width: 400
      :alt: ProDomo13-R410A-COP-1
Figure 6: Differences between experimental and fitted data of ProDomo13-R410A brine/water heat pump using
the proposed approach from the two equations above for coefficient of performance
(COP).

.. image:: ./resources/ProDomo13-R410A-Qcond-1.png
      :width: 400
      :alt: ProDomo13-R410A-Qcond-1
Figure 7: Differences between experimental and fitted data of ProDomo13-R410A brine/water heat pump using
the proposed approach from the two equations above for condenser heat.

Table 4: Differences between experiments and fitted data for the ProDomo13-R410A brine/water heat
pump using the two equations above. :math:`error=100 \cdot |\frac{Q_{exp}-Q_{num}}{Q_{exp}}|` and :math:`RMS = \sqrt { \sum{\frac{(Q_{exp}-Q_{num})^2}{n_p}} }` where :math:`n_p` is the number of data points.

.. image:: ./resources/HP_table4.png
      :width: 800
      :alt: HP_table4


Table 5: Fitted coefficients for the ProDomo13-R410A brine/water heat pump using the two equations above.

.. image:: ./resources/HP_table5.png
      :width: 600
      :alt: HP_table5

Solar thermal collector
-----------------------

A module to calculate the usable heat of a flat plate collector is described in details in `Solar thermal collector <https://oemof-thermal.readthedocs.io/en/latest/solar_thermal_collector.html#solar-thermal-collector>`_.
The model for solar thermal collector is taken from the oemof thermal package.

PV
---

The installed PV provides electricity to the building during the irradiation hours. Along with the battery, the usual strategy is to store the PV surplus power in the battery to be consumed at later hours of the planning horizon. The maximum available power :math:`pv_t^{avail}` of the PV is a built function that depends on the PV cell temperature, the ambient temperature and the total solar horizontal irradiation. These formulas, as well as the decision variables and the characteristics of the PV are stated in the next Table.
PV modules production profiles are pre-calculated before the optimization. 

Two-zone thermal energy storage
-------------------------------

A simplified 2-zone-model of a stratified thermal energy storage is implemented and described indetails in `Stratified thermal storage <https://oemof-thermal.readthedocs.io/en/latest/stratified_thermal_storage.html>`_.
The model for stratified thermal storage is taken from the oemof thermal package.

Combined production transformer
-------------------------------

A new transformer called combined production transformer which extends the features of oemof “Transformer” was defined. Since some transformers like HP can have different efficiencies for SH and DHW production (DHW needs a higher temperature than SH), this transformer offers the possibility to consider those different efficiencies. It allows to produce both space heating (SH) and domestic hot water (DHW) during the same timestep while respecting the input/output balance constraint.

.. math::

    P_{input}(t) = \frac{P_{DHW}(t)}{\eta_{DHW}} + \frac{P_{SH}(t)}{\eta_{SH}}, \forall t


where, :math:`P` denotes the operating power for inputs (for example, electricity used by HP) and outputs (SH and DHW), :math:`\eta` denotes efficiency of the transformer and :math:`t` denotes the time step.
Physically the converters cannot supply both SH and DHW at the same time. However, if we consider a timestep of 1 hour it can be considered to be sub-divided into smaller intervals to produce SH and DHW both within 1 hour. The combined production transformer was used for the implementation of heat pumps (ASHP, GSHP), CHP, gas boiler and electric heating rod.

PVT collector
-------------

PVT class was implemented within the converters module, which defines the energy conversion technologies
supported by optihood. The collector output is modelled based on the characteristic curve model reported
in the SwissEnergy sponsored project PVT Wrap-Up (Zenhäusern et al. (2017)). The thermal output of a
PVT collector, :math:`\dot{Q}`, highly depends on the surrounding environment and the operating conditions. The most
significant influencing factors are the solar irradiation per collector surface area (:math:`G`), ambient air temperature
(:math:`T_{amb}`) and the mean temperature of the collector fluid (:math:`T_m`). The characteristic equation of thermal output
of the PVT collector is given by:

.. math::

   \frac{\dot Q}{A} =(G - \frac{P_{el}^{DC}}{(\alpha \tau) \cdot A}) \cdot \eta_0 - a_1(T_m - T_{amb}) - a_2 (T_m - T_{amb})^2

where A stands for the gross area of the collector surface, :math:`P_{el}^{DC}` stands for the DC electrical output of the
collector, (\alpha \tau) is the transmission absorption product of the collector, :math:`\eta_0` is the maximum thermal efficiency,
:math:`a_1` is the linear heat loss coefficient and :math:`a_2` is the quadratic heat loss coefficient of the collector.
A corresponding label :math:`PVT` was added to the energy conversion technology processing function, to allow the
definition of a PVT collector in the input excel/config file while preparing the optimization problem.

Layered thermal energy storage and discrete temperature levels
---------------------------------------------------------------

A discretized thermal energy storage with several predefined discrete temperature levels was implemented.
Moreover, the heat production technologies such as heat pumps, CHP, solar thermal collectors, etc. were
extended to allow multiple output flows (at different temperature levels). It should be noted that the temperature
levels are predefined and each heat production technology, therefore, has a predefined hourly efficiency
related to a specific temperature level. The number of discrete temperature levels is parameterized and can be
defined in the input scenario excel file. In order to use discrete temperature levels, the ``temperatureLevels``
parameters has to be True when the ``EnergyNetwork`` class is instantiated:

.. image:: ./resources/code_snippet_multilayer_nrj_component.png
      :width: 800
      :alt: code_snippet_multilayer_nrj_component
SIMPLY PUT LAST LINE IN TEXT
The discrete temperature levels defined in the input scenario file, set the temperatures of the output
flows of the heat conversion technologies. Depending on the time resolution of the optimization problem, it
may not be acceptable for a heat conversion technology to produce heat at more than one temperature levels
in a single time step. Therefore, ``limit_active_flow_count`` constraint of oemof solph package (Hilpert
et al. (2018)) was used to permit only one of the heat output flows to remain active at a given time step.
A class ``ThermalStorageTemperatureLevels`` was developed to represent a discretized thermal energy storage.
The model of a layered thermal energy storage is a combination of dual temperature zone storages from
oemof thermal python package (Hilpert et al. (2018)). The dual temperature zone storages include predefined
calculations for top/bottom and lateral surface losses. While the lateral surface losses are preserved for the
storage layers at each temperature level, the top and bottom surface losses should only be considered for the topmost (i.e. at the highest temperature level) and the lowest (i.e. at the lowest temperature) layers. The fixed
one-time investment cost of the discretized thermal energy storage should be added to the objective function
only once (instead of being added for each layer separately). These functionalities are implemented within the
``ThermalStorageTemperatureLevels`` class. Moreover, the total storage volume :math:`V_{stor}` is calculated as the
sum of individual layer volumes (:math:`v_i`), as follows:


.. math::

      \sum_{i=1}^n v_i = V_{stor}

where :math:`n` denotes the number of discrete temperature levels.

A constraint called ``multiTemperatureStorageCapacityConstaint`` was developed to implement the following
rule on the storage volume capacity:


.. math::

      V_{stor,min} \leq V_{stor} \leq V_{stor,max}

where :math:`V_{stor,max}` and :math:`V_{stor,min}` represent the minimum and the maximum limits for the storage volume.
The Figure below shows a graphical representation of a layered thermal energy storage with three discrete temperature
levels. The DHW demand is met using the topmost temperature level at 65 °C i.e. highest temperature, while
the lowest temperature level at 35 °C is used to cover the SH demand. A rule for charging the thermal energy
storage was implemented, such that the energy inflow at a given storage layer (except the lowest layer), equals
the energy outflow from the preceding storage layer. Therefore, in order to supply thermal energy at 50 °C
to the storage, the same volume added at the 50 °C layer should be displaced from layer below, i.e. from the
35 °C storage level (as shown in Figure 11). This means that the energy conversion technologies can heat
water from 35 °C to 50 °C and from 50 °C to 65 °C, in that order.

.. image:: ./resources/multilayer_nrj_component.png
      :width: 800
      :alt: multilayer_nrj_component



