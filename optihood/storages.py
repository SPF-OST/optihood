from oemof.thermal.stratified_thermal_storage import (
    calculate_storage_u_value,
    calculate_losses,
)

import oemof.solph as solph

class ElectricalStorage(solph.components.GenericStorage):
    def __init__(self, buildingLabel, input, output, loss_rate, initial_storage, efficiency_in, efficiency_out, capacity_min, capacity_max, epc, base, varc, env_flow, env_capa):
        super(ElectricalStorage, self).__init__(
            label="electricalStorage"+'__'+buildingLabel,
            inputs={
                input: solph.Flow(investment=solph.Investment(ep_costs=0)),
            },
            outputs={
                output: solph.Flow(variable_costs=varc, env_per_flow=env_flow, )
            },
            loss_rate=loss_rate,
            initial_storage_level=initial_storage,
            inflow_conversion_factor=efficiency_in,
            outflow_conversion_factor=efficiency_out,
            Balanced=False,
            invest_relation_input_capacity=efficiency_in,
            invest_relation_output_capacity=efficiency_out,
            investment=solph.Investment(
                minimum=capacity_min,
                maximum=capacity_max,
                ep_costs=epc,
                existing=0,
                nonconvex=True,
                offset=base,
                env_per_capa=env_capa,
            ),
        )

class ThermalStorage(solph.components.GenericStorage):
    def __init__(self, label1, label2, stratifiedStorageParams, input, output, initial_storage, min, max, volume_cost, base, varc, env_flow, env_cap):
        u_value, loss_rate, fixed_losses_relative, fixed_losses_absolute, capacity_min, capacity_max, epc, env_capa = self._precalculate(stratifiedStorageParams,label2,min,max,volume_cost,env_cap)
        super(ThermalStorage, self).__init__(
            label=label1,
            inputs={
                input: solph.Flow(),
            },
            outputs={
                output: solph.Flow(investment=solph.Investment(ep_costs=0), variable_costs=varc, env_per_flow=env_flow, )
            },
            loss_rate=loss_rate,
            initial_storage_level=initial_storage,
            fixed_losses_relative=fixed_losses_relative,
            fixed_losses_absolute=fixed_losses_absolute,
            inflow_conversion_factor=stratifiedStorageParams.at[label2, 'inflow_conversion_factor'],
            outflow_conversion_factor=stratifiedStorageParams.at[label2, 'outflow_conversion_factor'],
            invest_relation_input_capacity=1,
            invest_relation_output_capacity=1,
            Balanced=False,
            investment=solph.Investment(
                minimum=0,
                maximum=capacity_max,
                ep_costs=epc,
                existing=0,
                nonconvex=True,
                offset=base,
                env_per_capa=env_capa,
            ),
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
