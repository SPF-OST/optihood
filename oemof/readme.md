# Modeling with oemof
**o**pen **e**nergy **mo**delling **f**ramework

https://oemof.org/

https://github.com/oemof

## About the framework
The framework provides a collection of python libraries for energy system modelling. The most relevant packages for the OptimEase project are **oemof.solph** and **oemof.thermal**.

Package | Details
------- | -------
oemof.solph   | includes tools for energy system modelling and optimization (LP/MILP) based on pyomo
oemof.thermal | includes tools for modelling thermal energy components (such as stratified storage, heat pump, solar collectors); serves as an extension of oemof.solph

- An energy system is modelled as a collection of *components* and *buses* 
- *Components* are used to model the energy sources, sinks, transformers and storage units 
- Several component classes are available in the framework to model different types of components 
- *Buses* are used as placeholders for outputs from/inputs into different components 
- Each component is connected to one or more buses
- The connection between a component and a bus represents a *flow* (energy flow) 
- All the flows entering and exiting a bus are balanced.

**oemof.solph** package contains several classes such as oemof.solph.Bus, oemof.solph.Flow, oemof.solph.Source, oemof.solph.Sink, oemof.solph.Transformer, oemof.solph.GenericStorage, oemof.solph.GenericCHP, etc. to model an energy system. It supports LP/MILP based on pyomo.

A detailed information on oemof.solph is available at https://oemof-solph.readthedocs.io/en/latest/usage.html

**oemof.thermal** package offers an extension to oemof.solph by including a collection of functions focusing on thermal energy technologies. It bundles functions for stratified thermal storage, solar thermal collectors, concentrating solar power, compression heat pump and chiller, cogeneration and absorption chiller.

A detailed information on oemof.thermal is available at https://oemof-thermal.readthedocs.io/en/latest/getting_started.html

## Key advantages specific to OptimEase project
  
* **Stratified storage** is supported by oemof.thermal package. Pre-calculations for stratified storage are provided enabling integration with oemof.solph.GenericStorage class. 
  
* Allows **modelling of heat pump** with COPs calculated at each timestep using the ambient air temperature. Efficiency of a component has to be constant within one time step. A different efficiency at each time step can be specified.

* Functions for modelling **different types of CHP plants** (combined cycle extraction turbines, back pressure turbines and motoric CHP) using GenericCHP class within oemof.solph package.

* Functions for implementing **solar thermal collectors** are also included in oemof.thermal package.

* Optimizes the use of the sources (or capacity of components in 'investment mode') to satisfy the demand with minimum costs. The **costs do not have to be monetary costs** but could represent emissions or other variable units.

* Available functions for **data extraction and visualization** allow for simplification of the code. oemof_visio package offers a variety of plotting functions.

## Limitations of oemof.solph

* Does not support non-linear optimization
* Muti-objective optimization is not possible 
* Costs are associated with energy flows (i.e. mainly the operation costs). At the moment, there seems to be no provision to include maintenance costs and feed in costs. Although, feed in costs could be easily implemented by adding an extra component and associating it with a negative cost.

A **solution to these limitations** would be to hook on to the umbrella library **oemof** for modelling the energy system components and then implementing optimization.
