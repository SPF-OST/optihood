import logging
from optihood._helpers import *
from oemof.thermal.stratified_thermal_storage import (
    calculate_storage_u_value,
    calculate_losses,
)
from oemof.network import network as on
from pyomo.core.base.block import ScalarBlock
from pyomo.environ import BuildAction
from pyomo.environ import Constraint
from pyomo.environ import Expression
from pyomo.environ import NonNegativeReals, Reals, Boolean, Binary
from pyomo.environ import Set
from pyomo.environ import Var
import oemof.solph as solph
from oemof.solph._plumbing import sequence as solph_sequence
from optihood.links import LinkStorageDummyInput, Link

class ElectricalStorage(solph.components.GenericStorage):
    def __init__(self, buildingLabel, input, output, loss_rate, initial_storage, efficiency_in, efficiency_out,
                 capacity_min, capacity_max, epc, base, varc, env_flow, env_capa, dispatchMode):
        if dispatchMode:
            investArgs = {'minimum':capacity_min,
                    'maximum':capacity_max,
                    'ep_costs':epc,
                    'custom_attributes': {'env_per_capa': env_capa}}
        else:
            investArgs = {'minimum':capacity_min,
                    'maximum':capacity_max,
                    'ep_costs':epc,
                    'existing':0,
                    'nonconvex':True,
                    'offset':base,
                    'custom_attributes': {'env_per_capa': env_capa}}
        super(ElectricalStorage, self).__init__(
            label="electricalStorage"+'__'+buildingLabel,
            inputs={
                input: solph.Flow(investment=solph.Investment(ep_costs=0)),
            },
            outputs={
                output: solph.Flow(investment=solph.Investment(ep_costs=0), variable_costs=varc, custom_attributes=
                {'env_per_flow':env_flow} )
            },
            loss_rate=loss_rate,
            initial_storage_level=initial_storage,
            inflow_conversion_factor=efficiency_in,
            outflow_conversion_factor=efficiency_out,
            balanced=False,
            invest_relation_input_capacity=efficiency_in,
            invest_relation_output_capacity=efficiency_out,
            investment=solph.Investment(**investArgs),
        )

class ThermalStorage(solph.components.GenericStorage):
    def __init__(self, label, stratifiedStorageParams, input, output, initial_storage, min, max, volume_cost, base,
                 varc, env_flow, env_cap, dispatchMode, is_tank = True, rho= 1, c=4.186):
        u_value, loss_rate, fixed_losses_relative, fixed_losses_absolute, capacity_min, capacity_max, epc, env_capa = \
            self._precalculate(stratifiedStorageParams,label.split("__")[0],min,max,volume_cost,env_cap, is_tank=
            is_tank, rho=rho, c=c)
        storageLabel = label.split("__")[0]
        if dispatchMode:
            investArgs={'minimum':capacity_min,
                'maximum':capacity_max,
                'ep_costs':epc,
                'custom_attributes': {'env_per_capa': env_capa}}
        else:
            investArgs={'minimum':capacity_min,
                'maximum':capacity_max,
                'ep_costs':epc,
                'existing':0,
                'nonconvex':True,
                'offset':base,
                'custom_attributes': {'env_per_capa': env_capa}}

        super(ThermalStorage, self).__init__(
            label=label,
            inputs={
                input: solph.Flow(investment=solph.Investment(ep_costs=0)),
            },
            outputs={
                output: solph.Flow(investment=solph.Investment(ep_costs=0), variable_costs=varc, custom_attributes=
                {'env_per_flow':env_flow} )
            },
            loss_rate=loss_rate,
            initial_storage_level=initial_storage,
            fixed_losses_relative=fixed_losses_relative,
            fixed_losses_absolute=fixed_losses_absolute,
            inflow_conversion_factor=stratifiedStorageParams.at[storageLabel, 'inflow_conversion_factor'],
            outflow_conversion_factor=stratifiedStorageParams.at[storageLabel, 'outflow_conversion_factor'],
            invest_relation_input_capacity=1,
            invest_relation_output_capacity=1,
            balanced=False,
            investment=solph.Investment(**investArgs),
        )

    def _precalculate(self, data, label,min,max,volume_cost,env_cap, is_tank, rho, c):
        if is_tank:
            tempH = data.at[label, 'temp_h']
            tempC = data.at[label, 'temp_c']
            u_value = calculate_storage_u_value(
                data.at[label, 's_iso'],
                data.at[label, 'lamb_iso'],
                data.at[label, 'alpha_inside'],
                data.at[label, 'alpha_outside'])

            loss_rate, fixed_losses_relative, fixed_losses_absolute = calculate_losses(
                u_value,
                data.at[label, 'diameter'],
                tempH,
                tempC,
                data.at[label, 'temp_env'])

            L_to_kWh = c * rho * (tempH - tempC) / 3600  # converts L data to kWh data for oemof GenericStorage class


        else:
            temp_h = data.at[label, 'temp_h']
            temp_c = data.at[label, 'temp_c']
            temp_env = data.at[label, 'temp_env']
            rho = data.at[label, 'rho']
            c = data.at[label, 'c']
            u_value = data.at[label, 'u_value']
            time_increment =1
            if 'pitStorage' in label:
                height = data.at[label, 'height']
                angle = data.at[label, 'angle']
                fixed_losses_relative = 3 * u_value * (temp_c - temp_env) / (height * c * rho * (temp_h - temp_c)) * time_increment *3600
                loss_rate = 0#0.4 * fixed_losses_relative#2 * u_value / (s_base * c * rho * math.sin(angle * np.pi / 180)) * time_increment
                fixed_losses_absolute = 0
            else:
                loss_rate = 0
                fixed_losses_relative = 0
                fixed_losses_absolute = u_value*(temp_h - temp_env)*1e-6 #convert Wh to MWh
            L_to_kWh = c * rho * (temp_h - temp_env) / 3600  # converts L data to kWh data for oemof GenericStorage class

        capacity_min = min * L_to_kWh
        capacity_max = max * L_to_kWh
        epc = volume_cost / L_to_kWh
        env_capa = env_cap / L_to_kWh

        return u_value, loss_rate, fixed_losses_relative, fixed_losses_absolute, capacity_min, capacity_max, epc, env_capa


class ThermalStorageTemperatureLevels:
    def __init__(self, label, stratifiedStorageParams, inputs, outputs, initial_storage, min, max, volume_cost, base, varc, env_flow, env_cap, dispatchMode):
        self._label = label
        storageLabel = label.split("__")[0]
        self.__TempH, self.__TempC = self._calcTemperatures(stratifiedStorageParams, storageLabel)
        capacity_min, capacity_max, epc, env_capa = self._conversionCapacities(self.__TempH[0], self.__TempC[0], min, max, volume_cost, env_cap)
        # capacity_min, capacity_max should be on the whole storage not individual temperature levels
        self.__capacityMin = capacity_min
        self.__capacityMax = capacity_max
        #self.__baseInvestment=base # offset should be added only once for the whole storage, not for each temperature level
        self._numberOfLevels = len(stratifiedStorageParams.at[storageLabel, 'temp_h'].split(","))
        if dispatchMode:
            investArgs={'ep_costs':epc,
                'custom_attributes': {'env_per_capa': env_capa},
                'minimum': self.__capacityMin / self._numberOfLevels,
                'maximum': self.__capacityMax}
        else:
            investArgs={'ep_costs':epc,
                'existing':0,
                'minimum': self.__capacityMin/self._numberOfLevels,
                'maximum':self.__capacityMax,
                'offset':0,
                'custom_attributes': {'env_per_capa': env_capa}}
        self._s = []  # list of storage volumes
        self._dummyComponents = [] # list of dummy inputs for flow of volume from storage level at lower temperature to higher temperature
        self._dummyInBus = []
        self._dummyOutBus = []
        for i in range(self._numberOfLevels):
            u_value, loss_rate, fixed_losses_relative, fixed_losses_absolute = self._precalculate(stratifiedStorageParams, label.split("__")[0], i)
            newLabel = storageLabel + str(int(self.__TempH[i])) + "__" + label.split("__")[1]
            if i == 0:
                storageInput = {inputs[i]: solph.Flow(investment=solph.Investment(ep_costs=0))}
                dummyInBus = solph.Bus(label="dummyInBus_" + newLabel.replace("thermalStorage", "ts"))
                dummyOutBus = solph.Bus(label="dummyOutBus_" + newLabel.replace("thermalStorage", "ts"))   #Special bus to dummy component for level 0 as GenericStorage can have only one output
                self._dummyInBus.append(dummyInBus)
                self._dummyOutBus.append(dummyOutBus)
                storageOutput = {dummyOutBus: solph.Flow(investment=solph.Investment(ep_costs=0))}
                specialOut = {outputs[0]: solph.Flow(),
                              dummyInBus: solph.Flow()}
                self._dummyComponents.append(Link(                              # special component at the output of storage level 0
                    label="dummy_"+newLabel,
                    inputs={dummyOutBus: solph.Flow()},
                    outputs=specialOut,
                    conversion_factors={b: 1 for b in specialOut}
                ))
            else:
                if i != self._numberOfLevels - 1:
                    dummyInBus = solph.Bus(label="dummyInBus_"+newLabel.replace("thermalStorage", "ts"))
                    self._dummyInBus.append(dummyInBus)
                dummyOutBus = solph.Bus(label="dummyOutBus_" + newLabel.replace("thermalStorage", "ts"))
                self._dummyOutBus.append(dummyOutBus)
                storageInput = {dummyOutBus: solph.Flow(investment=solph.Investment(ep_costs=0))}
                if i == self._numberOfLevels - 1:
                    storageOutput = {
                        outputs[-1]: solph.Flow(investment=solph.Investment(ep_costs=0), variable_costs=varc,
                                               custom_attributes={'env_per_flow':env_flow})}
                    investArgs.update({"offset": base, "nonconvex": True})
                else:
                    storageOutput = {dummyInBus: solph.Flow(investment=solph.Investment(ep_costs=0))}
                self._dummyComponents.append(LinkStorageDummyInput(label="dummy_"+newLabel,
                            inputs={inputs[i]: solph.Flow(),
                                    self._dummyInBus[i-1]: solph.Flow()},
                            outputs={dummyOutBus: solph.Flow()},
                            conversion_factors={k: 1 for k in [inputs[i], self._dummyInBus[i-1]]}))
            self._s.append(solph.components.GenericStorage(label=newLabel,
                                                inputs=storageInput,
                                                outputs=storageOutput,
                                                loss_rate=loss_rate,
                                                initial_storage_level=initial_storage,      # initial storage is applied to each temperature level (if specified)
                                                fixed_losses_relative=fixed_losses_relative,
                                                fixed_losses_absolute=fixed_losses_absolute,
                                                inflow_conversion_factor=stratifiedStorageParams.at[storageLabel, 'inflow_conversion_factor'],
                                                outflow_conversion_factor=stratifiedStorageParams.at[storageLabel, 'outflow_conversion_factor'],
                                                invest_relation_input_capacity=1,
                                                invest_relation_output_capacity=1,
                                                balanced=False,
                                                investment=solph.Investment(**investArgs),))

    @property
    def label(self):
        return self._label

    @property
    def capacityMin(self):
        return self.__capacityMin

    @property
    def capacityMax(self):
        return self.__capacityMax

    """@property
    def baseInvestment(self):
        return self.__baseInvestment"""

    def _calcTemperatures(self, data, label):
        tempH = [float(t) for t in data.at[label, 'temp_h'].split(",")]
        tempC = [float(data.at[label, 'temp_c'])]
        for i in range(len(tempH)):
            if i != len(tempH)-1:
                tempC.append(tempH[i])
        return tempH, tempC

    def _conversionCapacities(self, tempH, tempC, min, max, volume_cost, env_cap):
        L_to_kWh = 4.186 * (tempH - tempC) / 3600  # converts L data to kWh data for oemof GenericStorage class
        capacity_min = min * L_to_kWh
        capacity_max = max * L_to_kWh
        epc = volume_cost / L_to_kWh
        env_capa = env_cap / L_to_kWh
        return capacity_min, capacity_max, epc, env_capa

    def _precalculate(self, data, label, level):
        u_value = calculate_storage_u_value(
            data.at[label, 's_iso'],
            data.at[label, 'lamb_iso'],
            data.at[label, 'alpha_inside'],
            data.at[label, 'alpha_outside'])
        loss_rate, fixed_losses_relative, fixed_losses_absolute = calculate_losses(
            u_value,
            data.at[label, 'diameter'],
            self.__TempH[level],
            self.__TempC[level],
            data.at[label, 'temp_env'])
        if level==0 or level==self._numberOfLevels-1:
            fixed_losses_absolute /= 2
        else:
            fixed_losses_absolute = 0
        return u_value, loss_rate, fixed_losses_relative, fixed_losses_absolute

    def getStorageLevel(self, level):
        if level>=self._numberOfLevels:
            logging.error("Inconsistency in number of storage level buses and temp_h values.")
        else:
            return self._s[level]

    def getDummyComponents(self, level):
        if level>=self._numberOfLevels:
            logging.error("Inconsistency in number of storage level buses and temp_h values.")
        elif level == self._numberOfLevels - 1:
            return [self._dummyOutBus[level], self._dummyComponents[level]]
        else:
            return [self._dummyInBus[level], self._dummyOutBus[level], self._dummyComponents[level]]

class IceStorage(on.Node):
    r"""
    Models the basic characteristics of an ice storage component
    IceStorage is designed with one input and one output

    Parameters
    ---------------------------------------------------------
    label: label of the ice storage node
    input: input bus of the ice storage node
    output: output bus of the ice storage node
    tStorInit: initial temperature of the ice storage [°C]
    fMax: maximum allowed ice fraction in the ice storage
    rho: density of water [kg/m3]
    V: Volume of the ice storage [m3]
    hfluid: latent heat of fusion of water [kJ/kg]
    cp: specific heat capacity of water [kJ/(kg.°C)]
    T_amb: ambient temperature time-series [°C]
    UA_tank: heat loss coefficient of the ice storage tank [kW/°C]
    inflow_conversion_factor: efficiency of heat exchanger at the inlet of the ice storage
    outflow_conversion_factor: efficiency of heat exchanger at the outlet of the ice storage
    """
    def __init__(self, label, input, output, tStorInit, fIceInit, fMax, rho, V, hfluid, cp, Tamb, UAtank, inflow_conversion_factor, outflow_conversion_factor):
        if tStorInit < 0:
            raise ValueError("The initial temperature of ice storage should be greater than or equal to 0°C.")
        self.tStorInit = tStorInit
        if fIceInit < 0 or fIceInit > 1:
            raise ValueError("The initial ice fraction in ice storage should be in [0,1]")
        self.fIceInit = fIceInit
        if fMax < 0.5 or fMax > 0.8:
            raise ValueError("Maximum ice fraction should be defined within the range 0.5-0.8")
        self.fMax = fMax
        self.massWaterMax = rho*V
        self.hf = hfluid
        self.rho = rho
        self.V = V
        self.cp = cp
        self.Tamb = solph_sequence(Tamb)
        self.UAtank = UAtank
        self.inflow_conversion_factor = inflow_conversion_factor
        self.outflow_conversion_factor = outflow_conversion_factor

        """if dispatchMode:
            investArgs={'minimum':capacity_min,
                'maximum':capacity_max,
                'ep_costs':epc,
                'custom_attributes': {'env_per_capa': env_capa}}
        else:
            investArgs={'minimum':capacity_min,
                'maximum':capacity_max,
                'ep_costs':epc,
                'existing':0,
                'nonconvex':True,
                'offset':base,
                'custom_attributes': {'env_per_capa': env_capa}}"""

        self.investment = None
        self._invest_group = False

        inputs = {input: solph.Flow(),}
        outputs = {output: solph.Flow()}

        super().__init__(
            label,
            inputs=inputs,
            outputs=outputs,
            custom_properties={},
        )

    def constraint_group(self):
        if self._invest_group is True:
            return IceStorageInvestmentBlock
        else:
            return IceStorageBlock

class IceStorageBlock(ScalarBlock):
    """
    Constraint block for ice storage without investment object
    """
    CONSTRAINT_GROUP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _create(self, group=None):
        if group is None:
            return None

        m = self.parent_block()

        i = {n: [i for i in n.inputs][0] for n in group}
        o = {n: [o for o in n.outputs][0] for n in group}

        #  ************* SET OF ICE STORAGES *****************************
        self.icestorages = Set(initialize=[n for n in group])

        #  ************* DECISION VARIABLES *****************************
        # temperature of ice storage
        self.tStor = Var(self.icestorages, m.TIMESTEPS, within=NonNegativeReals, bounds=(0,90))
        self.tStor_prev = Var(self.icestorages, m.TIMESTEPS, within=NonNegativeReals, bounds=(0,90))
        # mass of ice in storage
        self.mIceStor = Var(self.icestorages, m.TIMESTEPS, within=NonNegativeReals, bounds=(0,1000000))
        self.mIceStor_prev = Var(self.icestorages, m.TIMESTEPS, within=NonNegativeReals, bounds=(0,1000000))
        # ice fraction
        self.fIce = Var(self.icestorages, m.TIMESTEPS, within=NonNegativeReals, bounds=(0,1))
        # binary variable defining the status of ice formation in the storage
        self.iceStatus = Var(self.icestorages, m.TIMESTEPS, within=Binary)

        # for linearization of non-linear constraints with big M method
        M = 2000
        epsilon = 0.000001

        #  ************* CONSTRAINTS *****************************

        def _initial_temperature_rule(block):
            """set initial value of temperature of ice storage
            """
            for g in group:
                lhs = self.tStor_prev[g,0]
                rhs = g.tStorInit
                block.initial_temperature.add((g, 0), (lhs == rhs))

        self.initial_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.initial_temperature_build = BuildAction(rule=_initial_temperature_rule)

        def _initial_ice_state_rule(block):
            """set initial state of ice storage --> no ice formation
            """
            for g in group:
                lhs = self.mIceStor_prev[g,0]
                rhs = g.fIceInit*g.rho*g.V
                block.initial_ice_state.add((g, 0), (lhs == rhs))

        self.initial_ice_state = Constraint(group, m.TIMESTEPS, noruleinit= True)
        self.initial_ice_state_build = BuildAction(rule=_initial_ice_state_rule)

        def _prev_temperature_rule(block):
            for g in group:
                for t in m.TIMESTEPS:
                    if t != 0:
                        lhs = self.tStor_prev[g, t]
                        rhs = self.tStor[g, t - 1]
                        block.prev_temperature.add((g, t), (lhs == rhs))

        self.prev_temperature = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.prev_temperature_build = BuildAction(rule=_prev_temperature_rule)

        def _prev_mass_ice_rule(block):
            for g in group:
                for t in m.TIMESTEPS:
                    if t != 0:
                        lhs = self.mIceStor_prev[g, t]
                        rhs = self.mIceStor[g, t - 1]
                        block.prev_mass_ice.add((g, t), (lhs == rhs))

        self.prev_mass_ice = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.prev_mass_ice_build = BuildAction(rule=_prev_mass_ice_rule)

        def _max_ice_fraction_rule(block):
            """set the value of ice fraction"""
            for g in group:
                for t in m.TIMESTEPS:
                    lhs = self.fIce[g,t]
                    rhs = g.fMax
                    block.max_ice_fraction.add((g, t), (lhs <= rhs))

        self.max_ice_fraction = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.max_ice_fraction_build = BuildAction(rule=_max_ice_fraction_rule)

        def _ice_fraction_rule(block):
            """set the value of ice fraction"""
            for g in group:
                for t in m.TIMESTEPS:
                    lhs = self.fIce[g,t]
                    rhs = self.mIceStor[g,t]/g.massWaterMax     # division is most likely not allowed!!
                    block.ice_fraction.add((g, t), (lhs == rhs))

        self.ice_fraction = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.ice_fraction_build = BuildAction(rule=_ice_fraction_rule)

        def _storage_balance_rule(block):
            """rule defining the energy balance of an ice storage in every timestep"""
            for g in group:
                for t in m.TIMESTEPS:
                    expr = 0
                    expr += g.rho*g.V*g.cp*self.tStor[g,t]
                    expr += - g.rho * g.V * g.cp * self.tStor_prev[g, t]
                    expr += g.UAtank*self.tStor_prev[g,t]*m.timeincrement[t]
                    expr += - g.UAtank * g.Tamb[t] * m.timeincrement[t]
                    expr += - g.hf*self.mIceStor[g,t]
                    expr += g.hf * self.mIceStor_prev[g, t]
                    expr += (-m.flow[i[g], g, t]*g.inflow_conversion_factor*m.timeincrement[t])
                    expr += ((m.flow[g, o[g], t]/g.outflow_conversion_factor)*m.timeincrement[t])
                    block.storage_balance.add((g, t), (expr == 0))

        self.storage_balance = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.storage_balance_build = BuildAction(rule=_storage_balance_rule)

        def _mass_ice_rule(block):
            """rule for calculating the mass of ice in each timestep"""
            for g in group:
                for t in m.TIMESTEPS:
                    lhs = self.mIceStor[g, t]
                    rhs = self.iceStatus[g, t]*(self.mIceStor_prev[g, t] +
                                                (((m.flow[g, o[g], t]/g.outflow_conversion_factor)*m.timeincrement[t]
                                                  - m.flow[i[g], g, t]*g.inflow_conversion_factor*m.timeincrement[t]
                                                  + g.UAtank*(self.tStor_prev[g, t] - g.Tamb[t]) * m.timeincrement[t]
                                                  - g.rho*g.V*g.cp*self.tStor_prev[g, t])/g.hf))
                    block.mass_ice.add((g, t), (lhs == rhs))

        self.mass_ice = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.mass_ice_build = BuildAction(rule=_mass_ice_rule)

        def _ice_state_rule_1(block):
            """rule for calculating the mass of ice in each timestep"""
            for g in group:
                for t in m.TIMESTEPS:
                    lhs = self.tStor[g,t]
                    rhs = M*(1-self.iceStatus[g,t])
                    block.ice_state_1.add((g, t), (lhs <= rhs))

        self.ice_state_1 = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.ice_state_1_build = BuildAction(rule=_ice_state_rule_1)

        def _ice_state_rule_2(block):
            """rule for calculating the mass of ice in each timestep"""
            for g in group:
                for t in m.TIMESTEPS:
                    lhs = self.tStor[g,t]
                    rhs = epsilon*(1-self.iceStatus[g,t])
                    block.ice_state_2.add((g, t), (lhs >= rhs))

        self.ice_state_2 = Constraint(group, m.TIMESTEPS, noruleinit=True)
        self.ice_state_2_build = BuildAction(rule=_ice_state_rule_2)

        # def _max_heating_energy_rule(block):
        #     """rule for calculating the mass of ice in each timestep"""
        #     for g in group:
        #         for t in m.TIMESTEPS:
        #             lhs1 = m.flow[i[g], g, t]
        #             lhs2 = m.flow[g, o[g], t]
        #             rhs = 50
        #             block.max_heating_energy_in.add((g, t), (lhs1 <= rhs))
        #             block.max_heating_energy_out.add((g, t), (lhs2 <= rhs))
        #
        # self.max_heating_energy_in = Constraint(group, m.TIMESTEPS, noruleinit=True)
        # self.max_heating_energy_out = Constraint(group, m.TIMESTEPS, noruleinit=True)
        # self.max_heating_energy_build = BuildAction(rule=_max_heating_energy_rule)

    def _objective_expression(self):
        """objective expression for storages with no investment"""
        m = self.parent_block()
        if not hasattr(self, "icestorages"):
            return 0
        costs = 0   # no cost from using the storage with a fixed capacity
        self.costs = Expression(expr=costs)
        return self.costs

class IceStorageInvestmentBlock(ScalarBlock):
    """
    Constraint block for ice storage with investment attribute set as not None
    """