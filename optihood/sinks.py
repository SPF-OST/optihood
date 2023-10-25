"""
under-development component for a linear RC model for heating a Building
"""

import oemof.solph as solph
from oemof.solph._plumbing import sequence
from pyomo.core.base.block import ScalarBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint
from pyomo.environ import Expression
from pyomo.environ import NonNegativeReals, Reals, Boolean
from pyomo.environ import Set
from pyomo.environ import Var

class SinkRCModel(solph.components.Sink):
    """
    Building RC Model implemented as a custom Sink component

    Parameters
    ----------
    rDistribution : Thermal resistance between indoor and distribution system states [K/kW]
    cDistribution : Thermal capacity of distribution system state [kWh/K]
    rIndoor : Thermal resistance between indoor and wall states [K/kW]
    cIndoor : Thermal capacity of indoor air state [kWh/K]
    rWall : Thermal resistance between wall state and outside [K/kW]
    cWall  : Thermal capacity of wall state [kWh/K]
    areaWindows : aperture area of windows [m^2]
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
            areaWindows=1.5,
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
        self.areaWindows = areaWindows
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

        # for all Sink RC model components get inflow from a bus
        for n in group:
            n.inflow = list(n.inputs)[0]

        #  ************* SET OF CUSTOM SINK COMPONENTS *****************************

        # Set of Sink RC model Components
        self.sinkrc = Set(initialize=[n for n in group])

        #  ************* DECISION VARIABLES *****************************

        # Variable indoor temperature
        self.tIndoor = Var(self.sinkrc, m.TIMESTEPS, within=Reals)

        # Variable wall temperature
        self.tWall = Var(self.sinkrc, m.TIMESTEPS, within=Reals)

        # Variable distribution temperature
        self.tDistribution = Var(self.sinkrc, m.TIMESTEPS, within=Reals)

        # Variable indoor comfort temperature range violation
        self.epsilonIndoor = Var(self.sinkrc, m.TIMESTEPS, within=NonNegativeReals)

        # Variable indoor final temperature requirement violation
        self.deltaIndoor = Var(self.sinkrc, within=NonNegativeReals)

        # Variable binary indicator (0 whenever Q = 0)
        # self.Xsc_dis = Var(self.sinkrc, m.TIMESTEPS, within=Boolean)

        #  ************* CONSTRAINTS *****************************

        def _initial_indoor_temperature_rule(block):
            """set initial values of indoor temperature
            """
            for g in group:
                lhs = self.tIndoor[g, 0]
                rhs = g.tIndoorInit
                block.initial_indoor_temperature.add((g, 0), (lhs == rhs))

        self.initial_indoor_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.initial_indoor_temperature_build = BuildAction(rule=_initial_indoor_temperature_rule)

        def _initial_wall_temperature_rule(block):
            """set initial values of wall temperature
            """
            for g in group:
                lhs = self.tWall[g, 0]
                rhs = g.tWallInit
                block.initial_wall_temperature.add((g, 0), (lhs == rhs))

        self.initial_wall_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.initial_wall_temperature_build = BuildAction(rule=_initial_wall_temperature_rule)

        def _initial_distribution_temperature_rule(block):
            """set initial values of distribution temperature
            """
            for g in group:
                lhs = self.tDistribution[g, 0]
                rhs = g.tDistributionInit
                block.initial_distribution_temperature.add((g, 0), (lhs == rhs))

        self.initial_distribution_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.initial_distribution_temperature_build = BuildAction(rule=_initial_distribution_temperature_rule)

        #def _boolean_indicator_set_rule(block):
        #    """sets the value of boolean indicator self.Xsc_dis
        #    value is set to False whenever qDistribution = 0, otherwise True
        #    """
        #    for t in m.TIMESTEPS:
        #        for g in group:
        #            lhs = self.Xsc_dis[g, t]
        #            rhs = not(m.flow[g.inflow, g, t] == 0)

         #           block.boolean_indicator_set.add((g, t), (lhs == rhs))

        #self.boolean_indicator_set = Constraint(group, m.TIMESTEPS, noruleinit=True)
        #self.boolean_indicator_set_build = BuildAction(rule=_boolean_indicator_set_rule)

        def _indoor_comfort_upper_limit_rule(block):
            """Indoor comfort temperature < = maximum limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = self.tIndoor[g, t]
                    #rhs = g.tIndoorMax
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
                    # rhs = g.tIndoorMin
                    rhs = g.tIndoorMin - self.epsilonIndoor[g, t]
                    block.indoor_comfort_lower_limit.add((g, t), (lhs >= rhs))

        self.indoor_comfort_lower_limit = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.indoor_comfort_lower_limit_build = BuildAction(rule=_indoor_comfort_lower_limit_rule)

        def _indoor_final_temperature_rule(block):
            """Indoor temperature at the final timestamp should be higher than initial indoor temperature
            """
            t = m.TIMESTEPS[-1] #final timestep
            for g in group:
                lhs = self.tIndoor[g, t]
                #rhs = g.tIndoorInit
                rhs = g.tIndoorInit - self.deltaIndoor[g]
                block.indoor_final_temperature.add((g, t), (lhs >= rhs))

        self.indoor_final_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.indoor_final_temperature_build = BuildAction(rule=_indoor_final_temperature_rule)

        def _q_distribution_upper_limit_rule(block):
            """q distribution < = maximum limit
            """
            for t in m.TIMESTEPS:
                for g in group:
                    lhs = m.flow[g.inflow, g, t]
                    rhs = g.qDistributionMax
                    # rhs = g.qDistributionMax * self.Xsc_dis[g, t]
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
                    # rhs = g.qDistributionMin * self.Xsc_dis[g, t]
                    block.q_distribution_lower_limit.add((g, t), (lhs >= rhs))

        self.q_distribution_lower_limit = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.q_distribution_lower_limit_build = BuildAction(rule=_q_distribution_lower_limit_rule)

        def _indoor_temperature_equation_rule(block):
            """discrete state space equation for tIndoor
            """
            for g in group:
                c2 = 1/(g.rIndoor*g.cIndoor)
                c3 = 1/(g.rDistribution*g.cIndoor)
                c1 = 1 - c2 - c3
                c4 = g.areaWindows/g.cIndoor
                for t in m.TIMESTEPS:
                    if t!= m.TIMESTEPS[-1]:
                        lhs = self.tIndoor[g, t+1]
                        rhs = c1*self.tIndoor[g, t] + c2*self.tWall[g, t] + c3*self.tDistribution[g, t] + c4*(g.totalIrradiationHorizontal[t] + g.heatGainOccupants[t])
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
                    if t != m.TIMESTEPS[-1]:
                        lhs = self.tWall[g, t + 1]
                        rhs = c1 * self.tIndoor[g, t] + c2 * self.tWall[g, t] + c3 * g.tAmbient[t]
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
                    if t != m.TIMESTEPS[-1]:
                        lhs = self.tDistribution[g, t + 1]
                        rhs = c1 * self.tIndoor[g, t] + c2 * self.tDistribution[g, t] + c3 * m.flow[g.inflow, g, t]
                        block.distribution_temperature_equation.add((g, t), (lhs == rhs))

        self.distribution_temperature_equation = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.distribution_temperature_equation_build = BuildAction(rule=_distribution_temperature_equation_rule)