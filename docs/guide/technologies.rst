The technologies are classified in three categories:

- Energy inputs: all energy vectors that are energy sources for the systems, e.g. fuels, grid electricity, energy from the environment like solar radiation, etc.
- Energy converters: equipment that converts inputs into usable energy (heat or electricity) for the end consumers
- Energy storages: device to store electricity or heat locally in order to be consumed later.

.. image:: ./resources/energy_types.png
      :width: 800
      :alt: energy_types

Modelling of energy system components
--------------------

The energy system components can be classified into energy converters and storages. We use constant efficiency models for CHP, gas boiler and electric heating rods, where a fixed efficiency is pre-defined. Heat pumps (ASHP and GSHP) are modelled based on a bi-quadratic polynomial fit of the condenser heating power ($ \dot{q}_c$) and the electrical consumption power of the compressor ($\dot{w}_{cp})
