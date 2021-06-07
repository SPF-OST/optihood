# Modeling with FINE
Framework for Integrated Energy System Assessment

https://vsa-fine.readthedocs.io/en/master/

https://github.com/FZJ-IEK3-VSA/FINE

## Structure of the platform
Many classes compose the platform. The main one is **EnergySystemModel**, defining every parameter of the problem and reuniting every component introduced. The class also defines the objective function and solves the problem.

The two other main classes are **Component** and **ComponentModel**. The former only defines the new component with its parameters while the latter defines its variables and constraints.

Deriving from it, many classes are defined: **Conversion** and **ConversionModel**, **Source** with its subclass **Sink** and **SourceSinkModel**, **Storage** and **StorageModel**, **Transmission** and **TransmissionModel**.

Other subclasses can be defined, for a more complex development of the problem.

## Operation of the platform
1. Required packages are imported and the input data path is set
2. An energy system model instance is created
3. Commodity sources are added to the energy system model
4. Commodity conversion components are added to the energy system model
5. Commodity storages are added to the energy system model
6. Commodity transmissions components are added to the energy system model
7. Commodity sinks are added to the energy system model
8. The energy system model is optimized
9. Selected optimization results are presented

## Comparison with OPTIM-EASE project
- **No multi-objective optimization**

Currently, a CO2 function is calculated, summing every emission of CO2 defined. Then, this function is contrained not to exceed a certain yearly limit. To have a real multi-objective optimization, the sigma-constraint method should be used, as Pyomo does not know how to do it by itself. For that, every class should be updated, as the contribution of every component to the actual cost objective function is defined inside each xModel class.

- **Technologies models are quite simple**

In the examples provided by the platform, models are quite simple, with constant efficiencies for conversion components. However, it seems to be easy to update efficiencies.

Other issue is about hot water storage : no complex model is defined, all storages considered seem to have the same state of charge model.

Finally, the distinction between space heat and domestic hot water, inside a single technology producing heat, is not made in any of the examples. The prioritization of one among the other will also have to be made by hand.

- **Possibility to switch to non-linear problem**

As Pyomo supports non-linear modeling, the only update will have to be in the choice of the solver, inside the main class. Pyomo advises to use **ipopt**.

## Limits we might have to change
- Every component is defined and added to the model by hand
- For now, it seems that the clusterization of the whole horizon by typical days is imposed
- Operation color maps are only available for a one year horizon
- No title on the graphs plotted
