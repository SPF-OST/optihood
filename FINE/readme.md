# Modeling with FINE
Framework for Integrated Energy System Assessment

https://vsa-fine.readthedocs.io/en/master/

## GitHub
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

## Comparison to OPTIM-EASE project
