"""
under-development component for a linear RC model for heating a Building
"""
from optihood._helpers import *
import oemof.solph as solph
from oemof.network import Node
from oemof.solph._plumbing import sequence
from pyomo.core.base.block import ScalarBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint
from pyomo.environ import Expression
from pyomo.environ import NonNegativeReals, Reals, Binary
from pyomo.environ import Set
from pyomo.environ import Var
import numpy as np

class SinkRCModel(Node):
    """
    Building RC Model with a possibility of heat outflow (through chiller) as well

    Parameters
    ----------
    rDistribution : Thermal resistance between indoor and distribution system states [K/kW]
    cDistribution : Thermal capacity of distribution system state [kWh/K]
    rIndoor : Thermal resistance between indoor and wall states [K/kW]
    cIndoor : Thermal capacity of indoor air state [kWh/K]
    rWall : Thermal resistance between wall state and outside [K/kW]
    cWall  : Thermal capacity of wall state [kWh/K]
    gAreaWindows : g-value multiplied with aperture area of windows [m^2]
    qDistributionMin : Minimum operating power from the SC tank to the distribution system [kW]
    qDistributionMax : Maximum operating power from the SC tank to the distribution system [kW]
    tIndoorMin : Indoor minimum comfort temperature [ºC]
    tIndoorMax : Indoor maximum comfort temperature [ºC]
    tIndoorInit : Indoor initial temperature [ºC]
    tWallInit : Wall initial temperature [ºC]
    tDistributionInit : Distribution system initial temperature [ºC]
    tAmbient : Ambient outside air temperature at each timestep [ºC]
    totalIrradiationHorizontal : Total horizontal irradiation at each timestep [kW/m^2]
    heatGainOccupants : Internal heat gains from occupants at each timestep [kW]
    """

    def __init__(
            self,
            tAmbient,
            totalIrradiationHorizontal,
            heatGainOccupants,
            rDistribution=0.75,
            cDistribution=0.26,
            rIndoor=0.09,
            cIndoor=0.97,
            rWall=1.70,
            cWall=226.30,
            gAreaWindows=1.5,
            qDistributionMin=0,
            qDistributionMax=1000,
            tIndoorMin=19,
            tIndoorMax=23,
            tIndoorInit=21,
            tWallInit=21,
            tDistributionInit=21,
            **kwargs,
    ):
        super().__init__(**kwargs)
        self.rDistribution = rDistribution
        self.cDistribution = cDistribution
        self.rIndoor = rIndoor
        self.cIndoor = cIndoor
        self.rWall = rWall
        self.cWall = cWall
        self.gAreaWindows = gAreaWindows
        self.qDistributionMin = qDistributionMin
        self.qDistributionMax = qDistributionMax
        self.tIndoorMin = tIndoorMin
        self.tIndoorMax = tIndoorMax
        self.tIndoorInit = tIndoorInit
        self.tWallInit = tWallInit
        self.tDistributionInit = tDistributionInit
        self.tAmbient = sequence(tAmbient)
        self.totalIrradiationHorizontal = sequence(totalIrradiationHorizontal)
        self.heatGainOccupants = sequence(heatGainOccupants)

    def constraint_group(self):
        return SinkRCModelBlock

class SinkRCModelBlock(ScalarBlock):
    """
    Constraints for SinkRCModel Class
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        # for all Sink RC model components get inflow and outflow
        for n in group:
            n.inflow = list(n.inputs)[0]
            n.outflow = list(n.outputs)[0]

        #  ************* SET OF CUSTOM SINK COMPONENTS *****************************

        # Set of Sink RC model Components
        self.sinkrc = Set(initialize=[n for n in group])

        #  ************* DECISION VARIABLES *****************************

        # Variable indoor temperature
        self.tIndoor = Var(self.sinkrc, m.TIMESTEPS, within=NonNegativeReals, bounds=(0, 1000))
        self.tIndoor_prev = Var(self.sinkrc, m.TIMESTEPS, within=NonNegativeReals, bounds=(0, 1000))
        # Variable wall temperature
        self.tWall = Var(self.sinkrc, m.TIMESTEPS, within=NonNegativeReals, bounds=(0, 1000))
        self.tWall_prev = Var(self.sinkrc, m.TIMESTEPS, within=NonNegativeReals, bounds=(0, 1000))

        # Variable distribution temperature
        self.tDistribution = Var(self.sinkrc, m.TIMESTEPS, within=NonNegativeReals, bounds=(0, 1000))
        self.tDistribution_prev = Var(self.sinkrc, m.TIMESTEPS, within=NonNegativeReals, bounds=(0, 1000))

        # Variable indoor comfort temperature range violation
        self.epsilonIndoor = Var(self.sinkrc, m.TIMESTEPS, within=NonNegativeReals, bounds=(0, 1000))

        #  ************* CONSTRAINTS *****************************

        def _initial_indoor_temperature_rule(block):
            """set initial values of indoor temperature
            """
            for g in group:
                lhs = self.tIndoor_prev[g, 0]
                rhs = g.tIndoorInit
                block.initial_indoor_temperature.add((g, 0), (lhs == rhs))

        self.initial_indoor_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.initial_indoor_temperature_build = BuildAction(rule=_initial_indoor_temperature_rule)

        def _initial_wall_temperature_rule(block):
            """set initial values of wall temperature
            """
            for g in group:
                lhs = self.tWall_prev[g, 0]
                rhs = g.tWallInit
                block.initial_wall_temperature.add((g, 0), (lhs == rhs))

        self.initial_wall_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.initial_wall_temperature_build = BuildAction(rule=_initial_wall_temperature_rule)

        def _initial_distribution_temperature_rule(block):
            """set initial values of distribution temperature
            """
            for g in group:
                lhs = self.tDistribution_prev[g, 0]
                rhs = g.tDistributionInit
                block.initial_distribution_temperature.add((g, 0), (lhs == rhs))

        self.initial_distribution_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.initial_distribution_temperature_build = BuildAction(rule=_initial_distribution_temperature_rule)

        def _prev_indoor_temperature_rule(block):
            """set initial values of indoor temperature
            """
            for g in group:
                for t in m.TIMESTEPS:
                    if t != 0:
                        lhs = self.tIndoor_prev[g, t]
                        rhs = self.tIndoor[g, t-1]
                        block.prev_indoor_temperature.add((g, t), (lhs == rhs))

        self.prev_indoor_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.prev_indoor_temperature_build = BuildAction(rule=_prev_indoor_temperature_rule)

        def _prev_wall_temperature_rule(block):
            """set initial values of wall temperature
            """
            for g in group:
                for t in m.TIMESTEPS:
                    if t != 0:
                        lhs = self.tWall_prev[g, t]
                        rhs = self.tWall[g, t-1]
                        block.prev_wall_temperature.add((g, t), (lhs == rhs))

        self.prev_wall_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.prev_wall_temperature_build = BuildAction(rule=_prev_wall_temperature_rule)

        def _prev_distribution_temperature_rule(block):
            """set initial values of distribution temperature
            """
            for g in group:
                for t in m.TIMESTEPS:
                    if t != 0:
                        lhs = self.tDistribution_prev[g, t]
                        rhs = self.tDistribution[g, t-1]
                        block.prev_distribution_temperature.add((g, t), (lhs == rhs))

        self.prev_distribution_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.prev_distribution_temperature_build = BuildAction(rule=_prev_distribution_temperature_rule)

        def _indoor_comfort_upper_limit_rule(block):
            """Indoor comfort temperature < = maximum limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = self.tIndoor[g, t]
                    rhs = g.tIndoorMax + self.epsilonIndoor[g, t]
                    block.indoor_comfort_upper_limit.add((g, t), (lhs <= rhs))

        self.indoor_comfort_upper_limit = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.indoor_comfort_upper_limit_build = BuildAction(rule=_indoor_comfort_upper_limit_rule)

        def _indoor_comfort_lower_limit_rule(block):
            """Indoor comfort temperature > = minimum limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = self.tIndoor[g, t]
                    #rhs = g.tIndoorMin[t] - self.epsilonIndoor[g, t]                                                       # commented for MPC branch   !!!!!!!!!!!!!!!
                    rhs = g.tIndoorMin - self.epsilonIndoor[g, t]                                                           # specific to MPC branch   !!!!!!!!!!!!!!
                    block.indoor_comfort_lower_limit.add((g, t), (lhs >= rhs))

        self.indoor_comfort_lower_limit = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.indoor_comfort_lower_limit_build = BuildAction(rule=_indoor_comfort_lower_limit_rule)

        def _q_distribution_upper_limit_rule(block):
            """q distribution < = maximum limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    rhs = g.qDistributionMax
                    block.q_distribution_upper_limit.add((g, t), (lhs <= rhs))

        self.q_distribution_upper_limit = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.q_distribution_upper_limit_build = BuildAction(rule=_q_distribution_upper_limit_rule)

        def _q_distribution_lower_limit_rule(block):
            """q distribution > = minimum limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    rhs = g.qDistributionMin
                    block.q_distribution_lower_limit.add((g, t), (lhs >= rhs))

        self.q_distribution_lower_limit = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.q_distribution_lower_limit_build = BuildAction(rule=_q_distribution_lower_limit_rule)

        def _q_out_lower_limit_rule(block):
            """q out > = minimum limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g, g.outflow, t]
                    rhs = g.qDistributionMin
                    # rhs = g.qDistributionMin * self.Xsc_dis[g, t]
                    block.q_out_lower_limit.add((g, t), (lhs >= rhs))

        self.q_out_lower_limit = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.q_out_lower_limit_build = BuildAction(rule=_q_out_lower_limit_rule)

        def _indoor_temperature_equation_rule(block):
            """discrete state space equation for tIndoor
            """
            for g in group:
                c2 = 1/(g.rIndoor*g.cIndoor)
                c3 = 1/(g.rDistribution*g.cIndoor)
                c1 = 1 - c2 - c3
                c4 = g.gAreaWindows/g.cIndoor
                c5 = 1/g.cIndoor
                for t in m.TIMESTEPS:
                    lhs = self.tIndoor[g, t]
                    rhs = c1*self.tIndoor_prev[g, t] + c2*self.tWall_prev[g, t] + c3*self.tDistribution_prev[g, t] + c4*g.totalIrradiationHorizontal[t] + c5*g.heatGainOccupants[t]
                    block.indoor_temperature_equation.add((g, t), (lhs == rhs))

        self.indoor_temperature_equation = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.indoor_temperature_equation_build = BuildAction(rule=_indoor_temperature_equation_rule)

        def _wall_temperature_equation_rule(block):
            """discrete state space equation for tWall
            """
            for g in group:
                c1 = 1 / (g.rIndoor * g.cWall)
                c3 = 1 / (g.rWall * g.cWall)
                c2 = 1 - c1 - c3
                for t in m.TIMESTEPS:
                    lhs = self.tWall[g, t]
                    rhs = c1 * self.tIndoor_prev[g, t] + c2 * self.tWall_prev[g, t] + c3 * g.tAmbient[t]
                    block.wall_temperature_equation.add((g, t), (lhs == rhs))

        self.wall_temperature_equation = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.wall_temperature_equation_build = BuildAction(rule=_wall_temperature_equation_rule)

        def _distribution_temperature_equation_rule(block):
            """discrete state space equation for tDistribution
            """
            for g in group:
                c1 = 1 / (g.rDistribution * g.cDistribution)
                c2 = 1 - c1
                c3 = 1 /g.cDistribution
                for t in m.TIMESTEPS:
                    lhs = self.tDistribution[g, t]
                    rhs = c1 * self.tIndoor_prev[g, t] + c2 * self.tDistribution_prev[g, t] + c3 * (m.flow[g.inflow, g, t] - m.flow[g, g.outflow, t])
                    block.distribution_temperature_equation.add((g, t), (lhs == rhs))

        self.distribution_temperature_equation = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.distribution_temperature_equation_build = BuildAction(rule=_distribution_temperature_equation_rule)

    def _objective_expression(self):
        r"""Objective expression to add costs to high values of self.epsilon"""
        m = self.parent_block()
        variable_costs = 0
        fixed_costs = 0

        for g in self.sinkrc:
            for t in m.TIMESTEPS:
                variable_costs += self.epsilonIndoor[g,t]*1000000

        self.cost = Expression(expr=variable_costs + fixed_costs)
        return self.cost