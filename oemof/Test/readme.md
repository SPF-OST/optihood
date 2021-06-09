# Description

A basic model with a single heat pump and CHP unit is implemented as a test.

The model specific to the oemof framework is designed and depicted in **oemof model basic.svg**

Stratified storage is implemented using oemof.thermal package (with the same constants as defined in the example).

Heat Pump is implemented with COPs calculated at each timestep.

A combined cycle extraction turbine CHP has been implemented using the oemof.solph.GenericCHP class (with the same values of constants as defined in the example).

At present, only the operation costs have been integrated to the model. The investment mode of oemof.solph package still needs to be tested.

Two identical storage units have been implemented (one for space heating and the other for domestic hot water).

## Next steps 
- To implement the energy system with three CHPs and three heat pumps
- Use of investment mode of the oemof.solph package
