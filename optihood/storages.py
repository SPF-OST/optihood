import logging

from oemof.thermal.stratified_thermal_storage import (
    calculate_storage_u_value,
    calculate_losses,
)

import oemof.solph as solph
from optihood.links import LinkStorageDummyInput, Link

class ElectricalStorage(solph.components.GenericStorage):
    def __init__(self, buildingLabel, input, output, loss_rate, initial_storage, efficiency_in, efficiency_out, capacity_min, capacity_max, epc, base, varc, env_flow, env_capa, dispatchMode):
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
                output: solph.Flow(investment=solph.Investment(ep_costs=0), variable_costs=varc, custom_attributes={'env_per_flow':env_flow} )
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
    def __init__(self, label, stratifiedStorageParams, input, output, initial_storage, min, max, volume_cost, base, varc, env_flow, env_cap, dispatchMode):
        u_value, loss_rate, fixed_losses_relative, fixed_losses_absolute, capacity_min, capacity_max, epc, env_capa = self._precalculate(stratifiedStorageParams,label.split("__")[0],min,max,volume_cost,env_cap)
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
                output: solph.Flow(investment=solph.Investment(ep_costs=0), variable_costs=varc, custom_attributes={'env_per_flow':env_flow} )
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

    def _precalculate(self, data, label,min,max,volume_cost,env_cap):
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

        L_to_kWh = 4.186*(tempH-tempC)/3600 #converts L data to kWh data for oemof GenericStorage class
        capacity_min = min*L_to_kWh
        capacity_max = max*L_to_kWh
        epc = volume_cost/L_to_kWh
        env_capa = env_cap/L_to_kWh

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
                'custom_attributes': {'env_per_capa': env_capa}}
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
                dummyInBus = solph.Bus(label="dummyInBus_" + newLabel)
                dummyOutBus = solph.Bus(label="dummyOutBus_" + newLabel)   #Special bus to dummy component for level 0 as GenericStorage can have only one output
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
                    dummyInBus = solph.Bus(label="dummyInBus_"+newLabel)
                    self._dummyInBus.append(dummyInBus)
                dummyOutBus = solph.Bus(label="dummyOutBus_" + newLabel)
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

