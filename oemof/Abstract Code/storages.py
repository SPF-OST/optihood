from oemof.thermal.stratified_thermal_storage import (
    calculate_storage_u_value,
    calculate_storage_dimensions,
    calculate_capacities,
    calculate_losses,
)

import oemof.solph as solph
from oemof.tools import economics


class ElectricalStorage(solph.components.GenericStorage):
    def __init__(self, buildingLabel, ioBus, loss_rate, initial_storage, efficiency_in, efficiency_out, capacity_min, capacity_max, epc, base):
        super(ElectricalStorage, self).__init__(
            label="electricalStorage"+'__'+buildingLabel,
            inputs={
                ioBus: solph.Flow()
            },
            outputs={
                ioBus: solph.Flow()
            },
            # nominal_storage_capacity=s["nominal capacity"],
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
            ),
        )

class ThermalStorage(solph.components.GenericStorage):
    def __init__(self, label, stratifiedStorageParams, Temperature_h, iobus, initial_storage, capacity_min, capacity_max, epc, base):
        u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, \
        fixed_losses_absolute = self._precalculate(stratifiedStorageParams, Temperature_h)
        super(ThermalStorage, self).__init__(
            label=label,
            inputs={
                iobus: solph.Flow(),
            },
            outputs={
                iobus: solph.Flow()
            },
            # nominal_storage_capacity=2000,
            loss_rate=loss_rate,
            initial_storage_level=initial_storage,
            fixed_losses_relative=fixed_losses_relative,
            fixed_losses_absolute=fixed_losses_absolute,
            inflow_conversion_factor=stratifiedStorageParams.at[0, 'inflow_conversion_factor'],
            outflow_conversion_factor=stratifiedStorageParams.at[0, 'outflow_conversion_factor'],
            balanced=False,
            invest_relation_input_capacity=stratifiedStorageParams.at[0, 'inflow_conversion_factor'],
            invest_relation_output_capacity=stratifiedStorageParams.at[0, 'outflow_conversion_factor'],
            investment=solph.Investment(
                minimum=capacity_min,
                maximum=capacity_max,
                ep_costs=epc,
                existing=0,
                nonconvex=True,
                offset=base,
            ),
        )

    def _precalculate(self, dataS, Temperature_h, Temperature_c = 15):
        u_value = calculate_storage_u_value(
            dataS.at[0,'s_iso'],
            dataS.at[0,'lamb_iso'],
            dataS.at[0,'alpha_inside'],
            dataS.at[0,'alpha_outside'])

        volume, surface = calculate_storage_dimensions(
            dataS.at[0,'height'],
            dataS.at[0,'diameter']
        )

        nominal_storage_capacity = calculate_capacities(
            volume,
            Temperature_h,
            Temperature_c)

        loss_rate, fixed_losses_relative, fixed_losses_absolute = calculate_losses(
            u_value,
            dataS.at[0,'diameter'],
            Temperature_h,
            Temperature_c,
            dataS.at[0,'temp_env'])

        return u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, fixed_losses_absolute