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
                input: solph.Flow()
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
    def __init__(self, label1, label2, stratifiedStorageParams, input, output, initial_storage, capacity_min, capacity_max, epc, base, varc, env_flow, env_capa):
        u_value, loss_rate, fixed_losses_relative, fixed_losses_absolute = self._precalculate(stratifiedStorageParams, label2)
        super(ThermalStorage, self).__init__(
            label=label1,
            inputs={
                input: solph.Flow(),
            },
            outputs={
                output: solph.Flow(variable_costs=varc, env_per_flow=env_flow, )
            },
            loss_rate=loss_rate,
            initial_storage_level=initial_storage,
            fixed_losses_relative=fixed_losses_relative,
            fixed_losses_absolute=fixed_losses_absolute,
            inflow_conversion_factor=stratifiedStorageParams.at[label2, 'inflow_conversion_factor'],
            outflow_conversion_factor=stratifiedStorageParams.at[label2, 'outflow_conversion_factor'],
            balanced=False,
            invest_relation_input_capacity=stratifiedStorageParams.at[label2, 'inflow_conversion_factor'],
            invest_relation_output_capacity=stratifiedStorageParams.at[label2, 'outflow_conversion_factor'],
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

    def _precalculate(self, data, label):
        u_value = calculate_storage_u_value(
            data.at[label, 's_iso'],
            data.at[label, 'lamb_iso'],
            data.at[label, 'alpha_inside'],
            data.at[label, 'alpha_outside'])

        loss_rate, fixed_losses_relative, fixed_losses_absolute = calculate_losses(
            u_value,
            data.at[label, 'diameter'],
            data.at[label, 'temp_h'],
            data.at[label, 'temp_c'],
            data.at[label, 'temp_env'])

        return u_value, loss_rate, fixed_losses_relative, fixed_losses_absolute
