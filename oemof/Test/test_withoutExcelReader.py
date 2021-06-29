import numpy as np
import pandas as pd
import oemof.solph as solph
from oemof.network.network import Node
import oemof.thermal.compression_heatpumps_and_chillers as hp
from oemof.tools import logger
from oemof.tools import economics
import logging
import os
from oemof.network.graph import create_nx_graph
import networkx as nx
import pprint as pp
from oemof.thermal.stratified_thermal_storage import (
    calculate_storage_u_value,
    calculate_storage_dimensions,
    calculate_capacities,
    calculate_losses,
)

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

#import oemof_visio as oev


def calculate_cop(TemperatureH, TemperatureL):
    coefCOP = [12.4896, 64.0652, -83.0217, -230.1195, 173.2122]
    coefQ = [13.8603, 120.2178, -7.9046, -164.1900, -17.9805]
    QCondenser = coefQ[0] + (coefQ[1] * TemperatureL/273.15) + (coefQ[2] * TemperatureH/273.15) + (
                coefQ[3] * TemperatureL/273.15 * TemperatureH/273.15) + (coefQ[4] * TemperatureH * TemperatureH)
    WCompressor = coefCOP[0] + (coefCOP[1] * TemperatureL/273.15) + (coefCOP[2] * TemperatureH/273.15) + (
                coefCOP[3] * TemperatureL/273.15 * TemperatureH/273.15) + (coefCOP[4] * TemperatureH/273.15 * TemperatureH/273.15)
    COP = np.divide(QCondenser, WCompressor)
    return COP

def precalculateStratifiedStorage(temp_h=55,temp_c=15,s_iso=50,lamb_iso=0.03,alpha_inside=1,alpha_outside=1,height=30,diameter=10,temp_env=10):
    u_value = calculate_storage_u_value(
        s_iso,
        lamb_iso,
        alpha_inside,
        alpha_outside)

    volume, surface = calculate_storage_dimensions(
        height,
        diameter
    )

    nominal_storage_capacity = calculate_capacities(
        volume,
        temp_h,
        temp_c)

    loss_rate, fixed_losses_relative, fixed_losses_absolute = calculate_losses(
        u_value,
        diameter,
        temp_h,
        temp_c,
        temp_env)

    return u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, fixed_losses_absolute


if __name__ == '__main__':

    logger.define_logging()

    datetime_index = pd.date_range(
        "2016-01-01 00:00:00", "2016-01-01 23:00:00", freq="60min"
    )
    # model creation and solving
    #logging.info("Starting optimization")

    # initialisation of the energy system
    esys = solph.EnergySystem(timeindex=datetime_index)

    naturalGasBus = solph.Bus(label='naturalGasBus')
    electricityBus = solph.Bus(label='electricityBus')
    spaceHeatingBus = solph.Bus(label='spaceHeatingBus')
    domesticHotWaterBus = solph.Bus(label='domesticHotWaterBus')

    naturalGasResource = solph.Source(
            label='naturalGasResource',
            outputs={
                naturalGasBus: solph.Flow(
                    variable_costs=0.094
                )
            },
        )
    electricityResource = solph.Source(
        label='electricityResource',
        outputs={
            electricityBus: solph.Flow(
                variable_costs=0.2244
            )
        },
    )

    electricityDemand = solph.Sink(
                label='electricityDemand',
                inputs={electricityBus: solph.Flow(fix=[3, 3, 3, 3, 3, 3, 24, 23, 24, 19, 19, 19, 23, 23, 23, 24, 22, 22, 27, 28, 27, 10, 12, 11])},
            )
    spaceHeatingDemand = solph.Sink(
        label='spaceHeatingDemand',
        inputs={spaceHeatingBus: solph.Flow(
            fix=[21, 24, 26, 28, 30, 31, 73, 66, 63, 58, 49, 37, 30, 27, 26, 32, 31, 39, 39, 40, 44, 44, 14, 18])},
    )
    domesticHotWaterDemand = solph.Sink(
        label='domesticHotWaterDemand',
        inputs={domesticHotWaterBus: solph.Flow(
            fix=[0, 0, 0, 0, 0, 10, 10, 15, 5, 5, 5, 15, 15, 10, 5, 0, 0, 5, 15, 20, 25, 10, 0, 0])},
    )

    Temperature_sh = 35
    Temperature_dhw = 55
    Temperature_a = np.array([6, 6, 5, 5, 7, 9, 10, 10, 10, 13, 15, 15, 16, 17, 16, 16, 15, 14, 14, 13, 10, 9, 8, 7])
    copSH = calculate_cop(Temperature_sh, Temperature_a)
    copDHW = calculate_cop(Temperature_dhw, Temperature_a)

    HP = solph.Transformer(
            label='HP',
            inputs={electricityBus: solph.Flow()},
            outputs={
                spaceHeatingBus: solph.Flow(),
                domesticHotWaterBus: solph.Flow()},
            conversion_factors={spaceHeatingBus: copSH,
                                domesticHotWaterBus: copDHW},
        )

    CHP = solph.components.GenericCHP(
            label='CHP',
            fuel_input={
                naturalGasBus: solph.Flow(
                    H_L_FG_share_max=[0.18 for p in range(0, 24)],
                    H_L_FG_share_min=[0.41 for p in range(0, 24)])
            },
            electrical_output={
                electricityBus: solph.Flow(
                    P_max_woDH=[200 for p in range(0, 24)],
                    P_min_woDH=[100 for p in range(0, 24)],
                    Eta_el_max_woDH=[0.44 for p in range(0, 24)],
                    Eta_el_min_woDH=[0.40 for p in range(0, 24)],
                )
            },
            heat_output={spaceHeatingBus: solph.Flow(Q_CW_min=[0 for p in range(0, 24)]),
                         },
            Beta=[0 for p in range(0, 24)],
            back_pressure=False,
        )

    electricalStorage = solph.components.GenericStorage(
                    label='electricalStorage',
                    inputs={
                        electricityBus: solph.Flow()
                    },
                    outputs={
                        electricityBus: solph.Flow()
                    },
                    nominal_storage_capacity=200,
                    loss_rate=0,
                    initial_storage_level=0,
                    inflow_conversion_factor=0.9,
                    outflow_conversion_factor=0.86,
                    balanced=False
                )

    u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, fixed_losses_absolute = precalculateStratifiedStorage(55,15)
    dhwStorage = solph.components.GenericStorage(
                        label='dhwStorage',
                        inputs={
                            domesticHotWaterBus: solph.Flow()},
                        outputs={
                            domesticHotWaterBus: solph.Flow()
                        },
                        nominal_storage_capacity=nominal_storage_capacity,
                        loss_rate=loss_rate,
                        fixed_losses_relative=fixed_losses_relative,
                        fixed_losses_absolute=fixed_losses_absolute,
                        inflow_conversion_factor=0.7,
                        outflow_conversion_factor=0.7,
                        balanced=False
                    )

    u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, fixed_losses_absolute = precalculateStratifiedStorage(35,15)
    shStorage = solph.components.GenericStorage(
                        label='shStorage',
                        inputs={
                            spaceHeatingBus: solph.Flow(),
                        },
                        outputs={
                            spaceHeatingBus: solph.Flow()
                        },
                        nominal_storage_capacity=nominal_storage_capacity,
                        loss_rate=loss_rate,
                        fixed_losses_relative=fixed_losses_relative,
                        fixed_losses_absolute=fixed_losses_absolute,
                        inflow_conversion_factor=0.7,
                        outflow_conversion_factor=0.7,
                        balanced=False
                    )

    # add nodes to energy system
    esys.add(naturalGasBus, electricityBus, spaceHeatingBus, domesticHotWaterBus, naturalGasResource, electricityResource, electricityDemand, spaceHeatingDemand, domesticHotWaterDemand, HP, CHP, electricalStorage, dhwStorage, shStorage)

    print("*********************************************************")
    print("The following objects have been created from excel sheet:")
    for n in esys.nodes:
        oobj = str(type(n)).replace("<class 'oemof.solph.", "").replace("'>", "")
        print(oobj + ":", n.label)
    print("*********************************************************")

    om = solph.Model(esys)
    om.receive_duals()

    om.solve(solver="gurobi")
