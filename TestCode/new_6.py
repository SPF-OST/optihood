from __future__ import print_function
from __future__ import division
import data_extraction
import xlrd
import os
import shutil
from pyomo.opt import SolverFactory, SolverManagerFactory
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
#import pyomo.core as pyo
import pyomo.environ as pyo
import warnings
from datetime import datetime
from operator import itemgetter
from random import random

# -----------------------------------------------------------------------------#
## Organization of the code :
# Creation of the model
# Global parameters definition
# Sets definition
# Parameters definition
# Variables definition
# Constraints definition
# Objective function creation
# Resolution of the model with instance creation
#
# Some lines must be changed because they contain paths : l34, 544, 565.
# -----------------------------------------------------------------------------#

# excel path for recovery of demand and ambient temperature
excel_path = 'C:/Users/agnes.francois/Case_study/data.xlsx'

# model creation
model = pyo.AbstractModel()
model.name = 'TEST1'

model.created = datetime.now().strftime('%Y%m%dT%H%M')

# -----------------------------------------------------------------------------#
## Global parameters ##
# -----------------------------------------------------------------------------#
# number of hours, technologies, timesteps (from the Excel "Global" sheet)
model.hours = pyo.Param(within=pyo.NonNegativeIntegers)
model.buildings = pyo.Param(within=pyo.NonNegativeIntegers)
model.unique_conv = pyo.Param(within=pyo.NonNegativeIntegers)
model.conv = pyo.Param(within=pyo.NonNegativeIntegers)
model.unique_stor = pyo.Param(within=pyo.NonNegativeIntegers)
model.stor = pyo.Param(within=pyo.NonNegativeIntegers)
model.techs = pyo.Param(within=pyo.NonNegativeIntegers)
model.inputs = pyo.Param(within=pyo.NonNegativeIntegers)
model.demand = pyo.Param(within=pyo.NonNegativeIntegers)

# -----------------------------------------------------------------------------#
## Sets ##
# -----------------------------------------------------------------------------#
# sets are lists of things, elements that compose the model
model.Time = pyo.RangeSet(model.hours)  # [1, 24]
model.SubTime = pyo.RangeSet(2, model.hours)  # used for storage
model.Building = pyo.RangeSet(model.buildings)  # [1, 2]
model.UConv = pyo.Set()  # CHP, HP
model.Conv = pyo.Set()  # CHP(1-2-3), HP(1-2-3)
model.UStor = pyo.Set()  # Battery, Hot water
model.Stor = pyo.Set()  # Battery(1-2-3), Hot water(1-2-3)
model.Techs = pyo.Set()  # CHP(1-2-3), HP(1-2-3), Battery(1-2-3), Hot water(1-2-3)
model.In = pyo.Set()  # Electricity grid, natural gas
model.InCategory = pyo.Set()  # electricity, fuel
model.Out = pyo.Set(initialize=["elec", "sh", "dhw"])  # electricity, space heat, domestic hot water
model.OutCategory = pyo.Set(initialize=["elec", "heat"])
model.Heat = pyo.Set(initialize=["dhw", "sh"])

def conv_HP(model):
    return (x for x in model.Conv if "Heat_Pump" in x)

def conv_CHP(model):
    return (x for x in model.Conv if "CHP" in x)

def stor_battery(model):
    return(x for x in model.Stor if "Battery" in x)

def stor_HW(model):
    return(x for x in model.Stor if "Hot_water" in x)


model.HP = pyo.Set(initialize=conv_HP)  # HP(1-2-3)
model.CHP = pyo.Set(initialize=conv_CHP)  # CHP(1-2-3)
model.Battery = pyo.Set(initialize=stor_battery)  # Battery(1-2-3)
model.HW = pyo.Set(initialize=stor_HW)  # Hot water(1-2-3)

model.ElecIn = pyo.Set()  # HP(1-2-3), Battery(1-2-3)
model.ElecOut = pyo.Set()  # Battery(1-2-3)
model.FuelIn = pyo.Set()  # CHP(1-2-3)
model.HeatIn = pyo.Set()  # Hot water(1-2-3)
model.HeatOut = pyo.Set()  # HP(1-2-3), Hot water(1-2-3)
model.Fuels = pyo.Set()  # Natural gas
model.Elec = pyo.Set()  # Electricity grid

# -----------------------------------------------------------------------------#
## Parameters ## (all from the Excel)
# -----------------------------------------------------------------------------#
# Inputs
model.ICategory = pyo.Param(model.In, domain=pyo.Any)
model.IMin_capacity = pyo.Param(model.In, domain=pyo.NonNegativeReals)
model.IMax_capacity = pyo.Param(model.In, domain=pyo.NonNegativeReals)
model.Iho = pyo.Param(model.In, domain=pyo.NonNegativeReals)
model.Ihu = pyo.Param(model.In, domain=pyo.NonNegativeReals)
model.Icostw = pyo.Param(model.In, domain=pyo.NonNegativeReals)
model.IFeedIn = pyo.Param(model.In, domain=pyo.NonNegativeReals)
model.Icostkg = pyo.Param(model.In, domain=pyo.NonNegativeReals)
model.IUBP = pyo.Param(model.In, domain=pyo.Reals)
model.IPrimaryEnergyR = pyo.Param(model.In, domain=pyo.Reals)
model.IPrimaryEnergyNR = pyo.Param(model.In, domain=pyo.Reals)
model.IGWP = pyo.Param(model.In, domain=pyo.Reals)

# Converters
model.CMin_capacity = pyo.Param(model.Conv, domain=pyo.NonNegativeReals)
model.CMax_capacity = pyo.Param(model.Conv, domain=pyo.NonNegativeReals)
model.CSwitching_frequency = pyo.Param(model.Conv, domain=pyo.NonNegativeReals)
model.CNumber_max_per_building = pyo.Param(model.Conv, domain=pyo.Integers)
model.CInput = pyo.Param(model.Conv, domain=pyo.Any)
model.COutput = pyo.Param(model.Conv, domain=pyo.Any)
model.CMaintenanceCost = pyo.Param(model.Conv, domain=pyo.NonNegativeReals)
model.CInstallationCost = pyo.Param(model.Conv, domain=pyo.NonNegativeReals)
model.CPlanificationCost = pyo.Param(model.Conv, domain=pyo.NonNegativeReals)
model.CInvestmentCost = pyo.Param(model.Conv, domain=pyo.NonNegativeReals)
model.CInvestmentCostBase = pyo.Param(model.Conv, domain=pyo.NonNegativeReals)
model.CUBP = pyo.Param(model.Conv, domain=pyo.Reals)
model.CPrimaryEnergyR = pyo.Param(model.Conv, domain=pyo.Reals)
model.CPrimaryEnergyNR = pyo.Param(model.Conv, domain=pyo.Reals)
model.CGWP = pyo.Param(model.Conv, domain=pyo.Reals)

# Storage
model.SMin_capacity = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SMax_capacity = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SNumber_max_per_building = pyo.Param(model.Stor, domain=pyo.Integers)
model.SMin_power_of_charging = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SMax_power_of_charging = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SMin_power_of_discharging = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SMax_power_of_discharging = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SEfficiency_of_charging = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SEfficiency_of_discharging = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SInput = pyo.Param(model.Stor, domain=pyo.Any)
model.SOutput = pyo.Param(model.Stor, domain=pyo.Any)
model.SInstallationCost = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SPlanificationCost = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SInvestmentCost = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SInvestmentCostBase = pyo.Param(model.Stor, domain=pyo.NonNegativeReals)
model.SUBP = pyo.Param(model.Stor, domain=pyo.Reals)
model.SPrimaryEnergyR = pyo.Param(model.Stor, domain=pyo.Reals)
model.SPrimaryEnergyNR = pyo.Param(model.Stor, domain=pyo.Reals)
model.SGWP = pyo.Param(model.Stor, domain=pyo.Reals)

model.InitState = pyo.Param(initialize=0)
model.M = pyo.Param(initialize=10000)  # large number for "Big-M" method

# Ambient temperature
Weather = pd.read_excel(excel_path, sheet_name="Weather", index_col=0, engine='openpyxl')
Tamb = {}

for i in range(1, Weather.shape[0]+1):
    Tamb[i] = Weather.iloc[i-1][0]
model.Tamb = pyo.Param(model.Time, initialize=Tamb)

# Demand
Demand = pd.read_excel(excel_path, sheet_name="Demand", header=1, index_col=0, engine='openpyxl')
elecDemand = {}
shDemand = {}
dhwDemand = {}

for j in range(1, int(Demand.shape[1] / 3 + 1)):
    for i in range(1, Demand.shape[0] + 1):
        elecDemand[j, i] = Demand.iloc[i-1][3 * (j - 1)]
        shDemand[j, i] = Demand.iloc[i-1][3 * (j - 1) + 1]
        dhwDemand[j, i] = Demand.iloc[i-1][3 * (j - 1) + 2]
model.elecDemand = pyo.Param(model.Building, model.Time, initialize=elecDemand)
model.shDemand = pyo.Param(model.Building, model.Time, initialize=shDemand)
model.dhwDemand = pyo.Param(model.Building, model.Time, initialize=dhwDemand)


# -----------------------------------------------------------------------------#
## Variables ##
# -----------------------------------------------------------------------------#
# Inputs

def bound_tinp_rule(model, t, inp):
    return(model.IMin_capacity[inp], model.IMax_capacity[inp])


model.Tinp = pyo.Var(model.Time, model.In,
                     bounds=bound_tinp_rule, domain=pyo.NonNegativeReals,
                     doc='Quantity of input consumed per time')

model.ElecTech = pyo.Var(model.Time, model.Building, model.ElecIn,
                         domain=pyo.NonNegativeReals,
                         doc='Quantity of electricity from the grid that goes into the corresponding technologies per time')

model.FuelTech = pyo.Var(model.Time, model.Fuels, model.Building, model.FuelIn,
                         domain=pyo.NonNegativeReals,
                         doc='Quantity of fuels that goes into the corresponding technologies per time')

model.FeedIn = pyo.Var(model.Time, model.Building, model.ElecOut | model.CHP,
                       domain=pyo.NonNegativeReals, initialize=0,
                       doc='Quantity of electricity that is sold to the grid')
# Technologies
model.TechCapacity = pyo.Var(model.Building, model.Techs,
                             domain=pyo.NonNegativeReals,
                             doc='Capacity of each technology')

model.TechUse = pyo.Var(model.Building, model.Techs,
                        domain=pyo.Binary,
                        doc='Binary describing the use of a technology during the whole horizon')

model.TechUset = pyo.Var(model.Building, model.Time, model.Techs,
                         domain=pyo.Binary, initialize=0,
                         doc='Binary describing the use of a technology per timestep')

model.Switch = pyo.Var(model.Building, model.Time, model.HP | model.CHP,
                       bounds=(-1, 1), domain=pyo.Integers, initialize=0,
                       doc='Integer describing the switching state of HP and CHP : -1, 0 or 1')

model.TechIn = pyo.Var(model.Building, model.Time, model.Techs - model.HeatIn,
                       domain=pyo.NonNegativeReals, initialize=0,
                       doc='Quantity of power received by every technology (except heat-in) per time')

model.TechHeatInG = pyo.Var(model.Building, model.Time, model.HeatIn, model.Heat,
                            domain=pyo.NonNegativeReals, initialize=0,
                            doc='Quantity of heat received by corresponding technologies per time')

model.TechOut = pyo.Var(model.Building, model.Time, model.Techs - model.CHP - model.HeatOut,
                        domain=pyo.NonNegativeReals,
                        doc='Quantity of power out of every technology (except CHP and heat-out) per time')

model.TechHeatOutG = pyo.Var(model.Building, model.Time, model.HeatOut, model.Heat,
                             domain=pyo.NonNegativeReals,
                             doc='Quantity of heat out of corresponding technologies per time')

model.TechCHPOut = pyo.Var(model.Building, model.Time, model.CHP, model.Out,
                           domain=pyo.NonNegativeReals,
                           doc='Quantity of power out of CHP technologies per time')

model.SOC = pyo.Var(model.Building, model.Time, model.Battery,
                    domain=pyo.NonNegativeReals, initialize=model.InitState,
                    doc='State of charge of the battery per time')

model.SOCdhw = pyo.Var(model.Building, model.Time, model.HW,
                       domain=pyo.NonNegativeReals, initialize=model.InitState,
                       doc='State of charge of the HW DHW storage per time')

model.SOCsh = pyo.Var(model.Building, model.Time, model.HW,
                      domain=pyo.NonNegativeReals, initialize=model.InitState,
                      doc='State of charge of the HW SH storage per time')


model.TechFlow = pyo.Var(model.Building, model.Time, model.Techs, model.Techs, model.Out,
                         domain=pyo.NonNegativeReals, initialize=0)

# Demande
model.DemElec = pyo.Var(model.Building, model.Time, model.Elec | model.ElecOut | model.CHP,
                        domain=pyo.NonNegativeReals,
                        doc='Quantity of electricity satisfying the demand per time and its origin')

model.DemSH = pyo.Var(model.Building, model.Time, model.HeatOut | model.CHP,
                      domain=pyo.NonNegativeReals,
                      doc='Quantity of heat satisfying the demand of SH per time and its origin')

model.DemDHW = pyo.Var(model.Building, model.Time, model.HeatOut | model.CHP,
                       domain=pyo.NonNegativeReals,
                       doc='Quantity of heat satisfying the demand of DHW per time and its origin')

# -----------------------------------------------------------------------------#
## Constraints ##
# -----------------------------------------------------------------------------#

# Demand
def demand_elec_rule(model, b, t):
    return sum(model.DemElec[b, t, x] for x in model.Elec | model.ElecOut | model.CHP) == model.elecDemand[b, t]

def demand_sh_rule(model, b, t):
    return sum(model.DemSH[b, t, x] for x in model.HeatOut | model.CHP) == model.shDemand[b, t]

def demand_dhw_rule(model, b, t):
    return sum(model.DemDHW[b, t, x] for x in model.HeatOut | model.CHP) == model.dhwDemand[b, t]


model.respect_elec_demand = pyo.Constraint(model.Building, model.Time, rule=demand_elec_rule,
                                           doc='Satisfaction of electricity demand')
model.respect_sh_demand = pyo.Constraint(model.Building, model.Time, rule=demand_sh_rule,
                                         doc='Satisfaction of SH demand')
model.respect_dhw_demand = pyo.Constraint(model.Building, model.Time, rule=demand_dhw_rule,
                                          doc='Satisfaction of DHW demand')

# Definition of the outputs and inputs flows
def outputs_rule(model, b, t, tech, out):
    if tech in model.CHP:
        if out == "elec":
            return model.TechCHPOut[b, t, tech, out] == sum(model.TechFlow[b, t, tech, i, "elec"] for i in model.ElecIn) + model.FeedIn[t, b, tech] + model.DemElec[b, t, tech]
        elif out == "dhw":
            return model.TechCHPOut[b, t, tech, out] == sum(model.TechFlow[b, t, tech, i, out] for i in model.HeatIn) + model.DemDHW[b, t, tech]
        else:
            return model.TechCHPOut[b, t, tech, out] == sum(model.TechFlow[b, t, tech, i, out] for i in model.HeatIn) + model.DemSH[b, t, tech]
    elif tech in model.ElecOut:
        return model.TechOut[b, t, tech] == sum(model.TechFlow[b, t, tech, i, "elec"] for i in model.ElecIn) + model.DemElec[b, t, tech] + model.FeedIn[t, b, tech]
    elif tech in model.HeatOut:
        if out == "dhw":
            return model.TechHeatOutG[b, t, tech, out] == sum(model.TechFlow[b, t, tech, i, out] for i in model.HeatIn) + model.DemDHW[b, t, tech]
        elif out == "sh":
            return model.TechHeatOutG[b, t, tech, out] == sum(model.TechFlow[b, t, tech, i, out] for i in model.HeatIn) + model.DemSH[b, t, tech]
        else:
            return pyo.Constraint.Skip

def inputs_rule(model, b, t, tech, heat):
    if tech in model.ElecIn:
        return model.TechIn[b, t, tech] == sum(model.TechFlow[b, t, x, tech, "elec"] for x in model.ElecOut) + model.ElecTech[t, b, tech]
    elif tech in model.FuelIn:
        return model.TechIn[b, t, tech] == sum(model.FuelTech[t, x, b, tech] for x in model.Fuels)
    else:
        return model.TechHeatInG[b, t, tech, heat] == sum(model.TechFlow[b, t, x, tech, heat] for x in model.HeatOut | model.CHP)

def distribution_input_rule(model, t, input):
    if input in model.Elec:
        return model.Tinp[t, input] == sum(model.ElecTech[t, b, x] for x in model.ElecIn for b in model.Building) + sum(model.DemElec[b, t, input] for b in model.Building)
    elif input in model.Fuels:
        return model.Tinp[t, input] == sum(model.FuelTech[t, input, b, x] for x in model.FuelIn for b in model.Building)

def constraint_flow(model, b, t, techa, techb, a):
    if techa == techb:
        return model.TechFlow[b, t, techa, techb, a] == 0
    else:
        return pyo.Constraint.Skip


model.respect_outputs = pyo.Constraint(model.Building, model.Time, model.Techs, model.Out, rule=outputs_rule,
                                       doc='Definition of the outputs of a technology')

model.respect_inputs = pyo.Constraint(model.Building, model.Time, model.Techs, model.Heat, rule=inputs_rule,
                                      doc='Definition of the input of a technology')

model.respect_distribution_input = pyo.Constraint(model.Time, model.In, rule=distribution_input_rule,
                                                  doc='Definition of the quantity of inputs used')

model.respect_constraint_flow = pyo.Constraint(model.Building, model.Time, model.Techs, model.Techs, model.Out, rule=constraint_flow,
                                               doc='A technology cant use what it produces')

# Definition of the capacities

def min_tech_rule(model, b, tech):
    if tech in model.Conv:
        return model.TechCapacity[b, tech] >= model.CMin_capacity[tech] * model.TechUse[b, tech]
    elif tech in model.Stor:
        return model.TechCapacity[b, tech] >= model.SMin_capacity[tech] * model.TechUse[b, tech]

def max_tech_rule(model, b, tech):
    if tech in model.Conv:
        return model.TechCapacity[b, tech] <= model.CMax_capacity[tech] * model.TechUse[b, tech]
    elif tech in model.Stor:
        return model.TechCapacity[b, tech] <= model.SMax_capacity[tech] * model.TechUse[b, tech]


model.respect_min_tech = pyo.Constraint(model.Building, model.Techs, rule=min_tech_rule,
                                        doc='Minimzation of the capacity of the technologies')

model.respect_max_tech = pyo.Constraint(model.Building, model.Techs, rule=max_tech_rule,
                                        doc='Maximization of the capacity of the technologies')


def capacity_tech_rule(model, b, t, tech):
    if tech in model.CHP:
        return sum(model.TechCHPOut[b, t, tech, a] for a in model.Out) <= model.TechCapacity[b, tech]
    # elif tech in model.Battery:
    #     return model.SOC[t, tech] <= model.TechCapacity[tech]
    elif tech in model.HeatOut:
        return sum(model.TechHeatOutG[b, t, tech, a] for a in model.Heat) <= model.TechCapacity[b, tech]
    else:
        return model.TechOut[b, t, tech] <= model.TechCapacity[b, tech]

def capacity_hw_sh_rule(model, b, t, hw):
    return model.SOCsh[b, t, hw] <= model.TechCapacity[b, hw]/2

def capacity_hw_dhw_rule(model, b, t, hw):
    return model.SOCdhw[b, t, hw] <= model.TechCapacity[b, hw]/2


model.respect_capacity_tech = pyo.Constraint(model.Building, model.Time, model.Techs, rule=capacity_tech_rule,
                                             doc='Maximization of the output of a technology with its capacity')
model.respect_capacity_hw_sh = pyo.Constraint(model.Building, model.Time, model.HW, rule=capacity_hw_sh_rule,
                                              doc='Maximization of the SOC for SH in hot water storage')
model.respect_capacity_hw_dhw = pyo.Constraint(model.Building, model.Time, model.HW, rule=capacity_hw_dhw_rule,
                                               doc='Maximization of the SOC for DHW in hot water storage')

# HP model
# the relation between the temperature of the condensor and of ambient temperature is from the EcoDynbat project
# every temperature must be in Celsius degrees
# ones will be modified when model parameters are defined
def hp_rule(model, b, t, hp):
    coefW = [12.4896, 64.0652, -83.0217, -230.1195, 173.2122]
    coefQ = [13.8603, 120.2178, -7.9046, -164.1900, -17.9805]
    Tconddhw = 55 / 273.15
    efficaciteqdhw = coefQ[0] + coefQ[1] * model.Tamb[t] + coefQ[2] * Tconddhw + coefQ[3] * model.Tamb[t] * Tconddhw + coefQ[4] * (Tconddhw ** 2)
    efficacitewdhw = coefW[0] + coefW[1] * model.Tamb[t] + coefW[2] * Tconddhw + coefW[3] * model.Tamb[t] * Tconddhw + coefW[4] * (Tconddhw ** 2)
    COPdhw = efficaciteqdhw / efficacitewdhw

    Tcond = 25 * (model.Tamb[t] > 15) + (32.5 - 1 / 2 * model.Tamb[t]) * (model.Tamb[t] <= 15)
    Tcondsh = Tcond / 273.15
    efficaciteqsh = coefQ[0] + coefQ[1] * model.Tamb[t] + coefQ[2] * Tcondsh + coefQ[3] * model.Tamb[t] * Tcondsh + coefQ[4] * (Tcondsh ** 2)
    efficacitewsh = coefW[0] + coefW[1] * model.Tamb[t] + coefW[2] * Tcondsh + coefW[3] * model.Tamb[t] * Tcondsh + coefW[4] * (Tcondsh ** 2)
    COPsh = efficaciteqsh / efficacitewsh
    return model.TechIn[b, t, hp] == model.TechHeatOutG[b, t, hp, "dhw"] * COPdhw + model.TechHeatOutG[b, t, hp, "sh"] * COPsh

# Priority of Domestic Hot Water over Space Heat
def hp_sh_rule(model, b, t, hp):
    return model.TechHeatOutG[b, t, hp, "sh"] <= model.TechCapacity[b, hp] - model.TechHeatOutG[b, t, hp, "dhw"]


model.respect_hp = pyo.Constraint(model.Building, model.Time, model.HP, rule=hp_rule,
                                  doc='Efficiency definition of HP technologies')
model.respect_hp_sh = pyo.Constraint(model.Building, model.Time, model.HP, rule=hp_sh_rule,
                                     doc='SH relation for HP model')

# CHP model
# model not yet defined
def chp_rule(model, b, t, chp, a):
    if a == "elec":
        return model.TechCHPOut[b, t, chp, a] == model.TechIn[b, t, chp] * 0.4
    else:
        return model.TechCHPOut[b, t, chp, a] == model.TechIn[b, t, chp] * 0.45

# Priority of Domestic Hot Water over Space Heat
def chp_sh_rule(model, b, t, chp):
    return model.TechCHPOut[b, t, chp, "sh"] <= model.TechCapacity[b, chp] - model.TechCHPOut[b, t, chp, "dhw"]


model.respect_chp = pyo.Constraint(model.Building, model.Time, model.CHP, model.Out, rule=chp_rule,
                                   doc='Efficiency definition of CHP technologies')
model.respect_chp_sh = pyo.Constraint(model.Building, model.Time, model.CHP, rule=chp_sh_rule,
                                      doc="SH relation for CHP model")

# Battery model
# model not yet defined
def SOC_battery_rule(model, b, t, batt):
    return model.SOC[b, t, batt] == model.SOC[b, t-1, batt] + model.TechIn[b, t-1, batt] * model.SEfficiency_of_charging[batt] - \
           model.TechOut[b, t-1, batt] / model.SEfficiency_of_discharging[batt]

def init_state_battery_rule(model, b, batt):
    return model.SOC[b, 1, batt] == model.InitState

def final_state_battery_rule(model, b, batt):
    return model.SOC[b, model.hours, batt] == model.InitState


model.respect_SOC_battery = pyo.Constraint(model.Building, model.SubTime, model.Battery, rule=SOC_battery_rule,
                                           doc='Definition of the state of charge of a battery')

model.respect_init_state_battery = pyo.Constraint(model.Building, model.Battery, rule=init_state_battery_rule,
                                                  doc='Initial state to 0 for a battery (doesnt work with initializing the variable)')

model.respect_final_state_battery = pyo.Constraint(model.Building, model.Battery, rule=final_state_battery_rule,
                                                   doc='Final state to 0 for a battery')

# Hot Water storage model
# model not yet defined
def SOC_HW_dhw_rule(model, b, t, hw):
    return model.SOCdhw[b, t, hw] == model.SOCdhw[b, t-1, hw] + model.TechHeatInG[b, t-1, hw, "dhw"] * model.SEfficiency_of_charging[hw] - \
           model.TechHeatOutG[b, t-1, hw, "dhw"] / model.SEfficiency_of_discharging[hw]

def SOC_HW_sh_rule(model, b, t, hw):
    return model.SOCsh[b, t, hw] == model.SOCsh[b, t-1, hw] + model.TechHeatInG[b, t-1, hw, "sh"] * model.SEfficiency_of_charging[hw] - \
           model.TechHeatOutG[b, t-1, hw, "sh"] / model.SEfficiency_of_discharging[hw]

def init_state_HW_dhw_rule(model, b, hw):
    return model.SOCdhw[b, 1, hw] == model.InitState

def init_state_HW_sh_rule(model, b, hw):
    return model.SOCsh[b, 1, hw] == model.InitState

def final_state_HW_dhw_rule(model, b, hw):
    return model.SOCdhw[b, model.hours, hw] == model.InitState

def final_state_HW_sh_rule(model, b, hw):
    return model.SOCsh[b, model.hours, hw] == model.InitState


model.respect_SOC_HW_dhw = pyo.Constraint(model.Building, model.SubTime, model.HW, rule=SOC_HW_dhw_rule,
                                          doc='Definition of the state of charge of a Hot water storage, dhw part')

model.respect_SOC_HW_sh = pyo.Constraint(model.Building, model.SubTime, model.HW, rule=SOC_HW_sh_rule,
                                         doc='Definition of the state of charge of a Hot water storage, sh part')

model.respect_init_state_HW_dhw = pyo.Constraint(model.Building, model.HW, rule=init_state_HW_dhw_rule,
                                                 doc='Initial state to 0 for hot water storage (doesnt work with initializing the variable)')

model.respect_init_state_HW_sh = pyo.Constraint(model.Building, model.HW, rule=init_state_HW_sh_rule,
                                                doc='Initial state to 0 for hot water storage (doesnt work with initializing the variable)')

model.respect_final_state_HW_dhw = pyo.Constraint(model.Building, model.HW, rule=final_state_HW_dhw_rule,
                                                  doc='Final state to 0 for hot water storage')

model.respect_final_state_HW_sh = pyo.Constraint(model.Building, model.HW, rule=final_state_HW_sh_rule,
                                                 doc='Final state to 0 for hot water storage')

# Use binary
def use_binary1_rule(model, b, tech):
    return model.TechUse[b, tech] <= sum(model.TechUset[b, t, tech] for t in model.Time)

def use_binary2_rule(model, b, tech):
    return model.TechUse[b, tech] >= sum(model.TechUset[b, t, tech] for t in model.Time) / model.hours


model.respect_use_binary1 = pyo.Constraint(model.Building, model.Techs, rule=use_binary1_rule)
model.respect_use_binary2 = pyo.Constraint(model.Building, model.Techs, rule=use_binary2_rule)

# -----------------------------------------------------------------------------#
## Objectives ##
# -----------------------------------------------------------------------------#

model.fcosts = pyo.Var(initialize=0)
model.femissions = pyo.Var(initialize=0)

def objective_costs(model):
    return model.fcosts == sum(model.Icostw[inp]*model.Tinp[time, inp] for inp in model.In for time in model.Time) + \
                            sum(model.CMaintenanceCost[tech] * (model.TechCapacity[b, tech]*model.CInvestmentCost[tech] + model.CInvestmentCostBase[tech]) for b in model.Building for tech in model.Conv) + \
                            sum(model.CInstallationCost[tech] * (model.TechCapacity[b, tech] * model.CInvestmentCost[tech] + model.CInvestmentCostBase[tech]) for b in model.Building for tech in model.Conv) + \
                            sum(model.CPlanificationCost[tech] * (model.TechCapacity[b, tech] * model.CInvestmentCost[tech] + model.CInvestmentCostBase[tech]) for b in model.Building for tech in model.Conv) + \
                            sum(model.TechCapacity[b, tech] * model.CInvestmentCost[tech] + model.CInvestmentCostBase[tech] for b in model.Building for tech in model.Conv) + \
                            sum(model.SInstallationCost[tech] * (model.TechCapacity[b, tech] * model.SInvestmentCost[tech] + model.SInvestmentCostBase[tech]) for b in model.Building for tech in model.Stor) + \
                            sum(model.SPlanificationCost[tech] * (model.TechCapacity[b, tech] * model.SInvestmentCost[tech] + model.SInvestmentCostBase[tech]) for b in model.Building for tech in model.Stor) + \
                            sum(model.TechCapacity[b, tech] * model.SInvestmentCost[tech] + model.SInvestmentCostBase[tech] for b in model.Building for tech in model.Stor) + \
                            -model.IFeedIn["Electricity_grid"] * sum(model.FeedIn[t, b, tech] for t in model.Time for b in model.Building for tech in model.ElecOut | model.CHP)


def objective_emissions(model):
    return model.femissions == sum(model.Tinp[t, inp] * model.IGWP[inp] for t in model.Time for inp in model.In) + \
                                sum(model.TechOut[b, t, tech] * model.CGWP[tech] for b in model.Building for t in model.Time for tech in model.Conv - model.CHP - model.HeatOut) + \
                                sum(model.TechOut[b, t, tech] * model.SGWP[tech] for b in model.Building for t in model.Time for tech in model.Stor - model.CHP - model.HeatOut) + \
                                sum(model.TechHeatOutG[b, t, tech, heat] * model.CGWP[tech] for b in model.Building for t in model.Time for tech in model.HeatOut - model.Stor for heat in model.Heat) + \
                                sum(model.TechHeatOutG[b, t, tech, heat] * model.SGWP[tech] for b in model.Building for t in model.Time for tech in model.HeatOut - model.Conv for heat in model.Heat) + \
                                sum(model.TechCHPOut[b, t, tech, out] * model.CGWP[tech] for b in model.Building for t in model.Time for tech in model.CHP for out in model.Out)


model.C_fcosts = pyo.Constraint(rule=objective_costs)
model.C_femissions = pyo.Constraint(rule=objective_emissions)
model.O_fcosts = pyo.Objective(expr=model.fcosts, sense=pyo.minimize)
model.O_femissions = pyo.Objective(expr=model.femissions, sense=pyo.minimize)

# -----------------------------------------------------------------------------#
## Multi optimization ##
# -----------------------------------------------------------------------------#

model.O_femissions.deactivate()


# create an instance of the model depending on the data in the file 'extraction.dat'
result_path = 'C:/Users/agnes.francois/Case_study/extraction.dat'
data_extraction.extraction(excel_path, result_path)

instance = model.create_instance('extraction.dat')
#instance.pprint()  # print every set, parameter, variable and constraint created

# select the MILP solver
opt = SolverFactory("glpk")  # slover can be chosen here
opt.options["mipgap"] = 0.001  # define optimality gap
opt.Tee = True

solver_manager = SolverManagerFactory("serial")  # solve instances in series
solver_manager.solve(instance, tee=True, opt=opt, timelimit=None)

femissions_max = pyo.value(instance.femissions)


# ## max f2

model.O_femissions.activate()
model.O_fcosts.deactivate()

instance = model.create_instance('extraction.dat')
opt = SolverFactory("glpk")  # slover can be chosen here
opt.options["mipgap"] = 0.001  # define optimality gap
opt.Tee = True
solver_manager = SolverManagerFactory("serial")  # solve instances in series
solver_manager.solve(instance, tee=True, opt=opt, timelimit=None)

femissions_min = pyo.value(instance.femissions)
print('Each iteration will keep femissions lower than some values between femissions_min and femissions_max, so ['+str(femissions_min)+', '+ str(femissions_max)+']')

## apply normal $\epsilon$-Constraint

model.O_fcosts.activate()
model.O_femissions.deactivate()

model.e = pyo.Param(initialize=0, mutable=True)
model.C_epsilon = pyo.Constraint(expr=model.femissions <= model.e+1)

instance = model.create_instance('extraction.dat')
opt = SolverFactory("glpk")  # slover can be chosen here
opt.options["mipgap"] = 0.001  # define optimality gap
opt.Tee = True
solver_manager = SolverManagerFactory("serial")  # solve instances in series
solver_manager.solve(instance, tee=True, opt=opt, timelimit=None)

n = 10
step = int((femissions_max - femissions_min) / n)
steps = list(range(int(femissions_min), int(femissions_max), step)) + [femissions_max]

f1_l = []
f2_l = []
for i in steps[::-1]:
    print("etape")
    print(i)
    instance.e = i
    solver_manager.solve(instance, tee=True, opt=opt, timelimit=None)
    f1_l.append(pyo.value(instance.fcosts))
    f2_l.append(pyo.value(instance.femissions))

plt.figure()
plt.plot(f1_l, f2_l, 'o-.')
plt.xlabel('Costs')
plt.ylabel('Emissions')
plt.title('GLPK Pareto-front')
plt.grid(True);
plt.savefig("ParetoFront.png")
print("Costs : ")
print(f1_l)
print("Emissions : ")
print(f2_l)

# -----------------------------------------------------------------------------#
## Work on a single point ##
# -----------------------------------------------------------------------------#
# Choice of the point of the Pareto front we will work on
a = 8
instance.e = steps[len(steps)-a]
results = solver_manager.solve(instance, tee=True, opt=opt, timelimit=None)

instance.solutions.store_to(results)
#instance.TechUset.pprint()
#instance.SOCdhw.pprint()

# Method to save optimisation results to txt file
def pyomo_save_results(resultats):
    OUTPUT = open('C:/Users/agnes.francois/Case_study/ResultsTEST1.txt', 'w')
    print(resultats, file=OUTPUT)
    OUTPUT.close()


pyomo_save_results(resultats=results)    # to activate in order to save the results in txt file

## PLOT OF THE INPUTS CONSUMED PER TIMESTEP
Inputs_per_t = pd.DataFrame((instance.Tinp[v].value for v in instance.Tinp))
Inputs_per_time = []

for h in range(0, len(instance.In.data())):
    Inputs_per_time.append(Inputs_per_t[h::len(instance.In.data())])
Inputs_per_time = np.array(Inputs_per_time)

plt.figure()
plt.plot(instance.Time.data(), Inputs_per_time[0], instance.Time.data(), Inputs_per_time[1])
plt.legend(instance.In.data())
plt.xlabel('Hour')
plt.ylabel('Inputs consumed')
plt.title('Inputs consumed per hour')
plt.grid(True)
plt.savefig("Inputs.png")


## PLOT OF THE ELECTRICITY SOLD PER TIMESTEP
Feedin_per_t = pd.DataFrame((instance.FeedIn[v].value for v in instance.FeedIn))
Feedin_per_time = []

a = len(instance.ElecOut.data()) + len(instance.CHP.data())  # 6 dans notre cas

for t in range(0, len(instance.Time.data())):
    for h in range(0, len(instance.Building.data())):
        Feedin_per_time.append((Feedin_per_t[(t * len(instance.Building.data()) + h) * a : (t * len(instance.Building.data()) + h) * a + a]).sum())

plt.figure()
plt.plot(instance.Time.data(), Feedin_per_time[0::len(instance.Building.data())], instance.Time.data(), Feedin_per_time[1::len(instance.Building.data())])
plt.legend(instance.Building.data(), title="Buildings")
plt.xlabel('Hour')
plt.ylabel('Electricity sold')
plt.title('Electricity sold per hour')
plt.grid(True)
plt.savefig("Feedin.png")

#Example of how to print variables
#print("TOTAL COST")
#print(instance.Tinp[1, "Electricity_grid"].value)
