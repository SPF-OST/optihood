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

def read_excel(filePath):
    """Read node data from Excel sheet
            Parameters
            ----------
            filePath : :obj:`str`
                Path to excel file
            Returns
            -------
            :obj:`dict`
                Imported nodes data
    """
    # does Excel file exist?
    if not filePath or not os.path.isfile(filePath):
        raise FileNotFoundError(
            "Excel data file {} not found.".format(filePath)
        )
    data = pd.ExcelFile(filePath)
    nodesData = {
        "buses": data.parse("buses"),
        "commodity_sources": data.parse("commodity_sources"),
        "transformers": data.parse("transformers"),
        "demand": data.parse("demand"),
        "storages": data.parse("storages"),
        "timeseries": data.parse("time_series"),
        "stratified_storage": data.parse("stratified_storage")
    }

    # set datetime index
    nodesData["timeseries"].set_index("timestamp", inplace=True)
    nodesData["timeseries"].index = pd.to_datetime(
        nodesData["timeseries"].index
    )

    print("Data from Excel file {} imported.".format(filePath))

    nodesList = convert_nodes(nodesData)
    return nodesList


def convert_nodes(data):
    """Converts node dict to oemof nodes (oemof objects)
                Parameters
                ----------
                data : :obj:`dict`
                    Nodes data
                Returns
                -------
                nodesList : `obj`:list of :class:`nodes <oemof.network.Node>`
    """
    if not data:
        raise ValueError("No nodes data provided.")

    nodesList = []

    # Create Bus objects from buses table
    busDict = {}
    for i, b in data["buses"].iterrows():
        if b["active"]:
            bus = solph.Bus(label=b["label"])
            nodesList.append(bus)
            busDict[b["label"]] = bus

    # Create excess components for the elec/heat bus to allow overproduction


    # Create Source objects from table 'commodity sources'
    for i, cs in data["commodity_sources"].iterrows():
        if cs["active"]:
            nodesList.append(solph.Source(
                    label=cs["label"],
                    outputs={
                        busDict[cs["to"]]: solph.Flow(
                            variable_costs=cs["variable costs"]
                        )
                    },
                ))

    # Create Sink objects with fixed time series from 'demand' table
    for i, de in data["demand"].iterrows():
        if de["active"]:
            # set static inflow values, if any
            inflow_args = {}
            # get time series for node and parameter
            for col in data["timeseries"].columns.values:
                if col.split(".")[0] == de["label"]:
                    inflow_args[col.split(".")[1]] = data["timeseries"][col]

            # create
            nodesList.append(
                solph.Sink(
                    label=de["label"],
                    inputs={busDict[de["from"]]: solph.Flow(**inflow_args)},
                )
            )

    Temperature_sh = 35
    Temperature_dhw = 55
    Temperature_a = np.array(data["timeseries"]["temperature.actual"])

    # Create Transformer objects from 'transformers' table
    for i, t in data["transformers"].iterrows():
        if t["active"]:
            if t["label"] == "HP":
                copSH = calculate_cop(Temperature_sh,Temperature_a)
                copDHW = calculate_cop(Temperature_dhw,Temperature_a)
                nodesList.append(
                    solph.Transformer(
                        label=t["label"],
                        inputs={busDict[t["from"]]: solph.Flow()},
                        outputs={
                            busDict[t["to"].split(",")[0]]: solph.Flow(),
                            busDict[t["to"].split(",")[1]]: solph.Flow()},
                        conversion_factors={busDict[t["to"].split(",")[0]]: copSH,
                                            busDict[t["to"].split(",")[1]]: copDHW},
                    )
                )
            elif t["label"] == "CHP":
                # motoric CHP
                nodesList.append(
                    solph.components.GenericCHP(
                        label=t["label"],
                        fuel_input={
                            busDict[t["from"]]: solph.Flow(
                                H_L_FG_share_max=[0.18 for p in range(0, 24)],
                                H_L_FG_share_min=[0.41 for p in range(0, 24)])
                        },
                        electrical_output={
                            busDict[t["to"].split(",")[0]]: solph.Flow(
                                P_max_woDH=[200 for p in range(0, 24)],
                                P_min_woDH=[100 for p in range(0, 24)],
                                Eta_el_max_woDH=[0.44 for p in range(0, 24)],
                                Eta_el_min_woDH=[0.40 for p in range(0, 24)],
                            )
                        },
                        heat_output={busDict[t["to"].split(",")[1]]: solph.Flow(Q_CW_min=[0 for p in range(0, 24)]),
                                    },
                        Beta=[0 for p in range(0, 24)],
                        back_pressure=False,
                    )
                )
            else:
                print("Transformer label not identified...")

    # Create Storage objects from 'transformers' table
    for i, s in data["storages"].iterrows():
        if s["active"]:
            if s["label"] == "electricalStorage":
                nodesList.append(
                    solph.components.GenericStorage(
                        label=s["label"],
                        inputs={
                            busDict[s["bus"]]: solph.Flow()
                        },
                        outputs={
                            busDict[s["bus"]]: solph.Flow()
                        },
                        nominal_storage_capacity=s["nominal capacity"],
                        loss_rate=s["capacity loss"],
                        initial_storage_level=s["initial capacity"],
                        inflow_conversion_factor=s["efficiency inflow"],
                        outflow_conversion_factor=s["efficiency outflow"],
                        Balanced=False
                    )
                )
            else:
                if s["label"] == "dhwStorage":
                    u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, fixed_losses_absolute  = precalculateStratifiedStorage(data["stratified_storage"], Temperature_dhw)
                elif s["label"] == "shStorage":
                    u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, fixed_losses_absolute = precalculateStratifiedStorage(data["stratified_storage"], Temperature_sh)
                else:
                    print("Storage label not identified")

                if s["label"] == "dhwStorage" or "shStorage":
                    nodesList.append(
                        solph.components.GenericStorage(
                            label=s["label"],
                            inputs={
                                busDict[s["bus"]]: solph.Flow(),
                            },
                            outputs={
                                busDict[s["bus"]]: solph.Flow()
                            },
                            nominal_storage_capacity=nominal_storage_capacity,
                            loss_rate=loss_rate,
                            fixed_losses_relative=fixed_losses_relative,
                            fixed_losses_absolute=fixed_losses_absolute,
                            inflow_conversion_factor=data["stratified_storage"].at[0, 'inflow_conversion_factor'],
                            outflow_conversion_factor=data["stratified_storage"].at[0, 'outflow_conversion_factor'],
                            balanced=False
                        )
                    )

    return nodesList


def calculate_cop(TemperatureH, TemperatureL):
    coefCOP = [12.4896, 64.0652, -83.0217, -230.1195, 173.2122]
    coefQ = [13.8603, 120.2178, -7.9046, -164.1900, -17.9805]
    QCondenser = coefQ[0] + (coefQ[1] * TemperatureL/273.15) + (coefQ[2] * TemperatureH/273.15) + (
                coefQ[3] * TemperatureL/273.15 * TemperatureH/273.15) + (coefQ[4] * TemperatureH * TemperatureH)
    WCompressor = coefCOP[0] + (coefCOP[1] * TemperatureL/273.15) + (coefCOP[2] * TemperatureH/273.15) + (
                coefCOP[3] * TemperatureL/273.15 * TemperatureH/273.15) + (coefCOP[4] * TemperatureH/273.15 * TemperatureH/273.15)
    COP = np.divide(QCondenser, WCompressor)
    return COP


def precalculateStratifiedStorage(dataS, Temperature_h, Temperature_c = 15):
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


if __name__ == '__main__':

    logger.define_logging()

    ###################################################
    # Initialization of Energy System and Optimization
    ###################################################

    datetime_index = pd.date_range(
        "2016-01-01 00:00:00", "2016-01-01 23:00:00", freq="60min"
    )
    # model creation and solving
    logging.info("Starting optimization")

    # initialisation of the energy system
    esys = solph.EnergySystem(timeindex=datetime_index)

    # read node data from Excel sheet
    nodes = read_excel(os.path.join(os.getcwd(), "scenario.xls", ))

    # add nodes to energy system
    esys.add(*nodes)

    print("*********************************************************")
    print("The following objects have been created from excel sheet:")
    for n in esys.nodes:
        oobj = str(type(n)).replace("<class 'oemof.solph.", "").replace("'>", "")
        print(oobj + ":", n.label)
    print("*********************************************************")

    om = solph.Model(esys)

    om.solve(solver="gurobi")

    ######################################
    # Processing and Plotting the Results
    ######################################

    results = solph.processing.results(om)
    elStorage = esys.groups["electricalStorage"]
    dhwStorage = esys.groups["dhwStorage"]
    shStorage = esys.groups["shStorage"]

    # To dump the EnergySystem instance
    esys.dump(os.getcwd(), 'esys_dump.oemof')

    # To restore the dump:
    # esys.restore(PATH, 'esys_dump.oemof')
    # results = esys.results
    # elStorage = esys.groups["electricalStorage"]

    # print a time slice of the state of charge
    print("")
    print("********* State of Charge (Electrical Battery Storage) *********")
    print(
        results[(elStorage, None)]["sequences"]
    )
    print("")

    print("")
    print("********* State of Charge (DHW Storage) *********")
    print(
        results[(dhwStorage, None)]["sequences"]
    )
    print("")

    print("")
    print("********* State of Charge (Space Heating Storage) *********")
    print(
        results[(shStorage, None)]["sequences"]
    )
    print("")

    # Plotting time-series of electricity, DHW and SH buses
    elBus = solph.views.node(results, "electricityBus")
    dhwBus = solph.views.node(results, "domesticHotWaterBus")
    shBus = solph.views.node(results, "spaceHeatingBus")

    if plt is not None:
        fig, ax = plt.subplots(figsize=(10, 5))
        elBus["sequences"].plot(
            ax=ax, kind="line", drawstyle="steps-post"
        )
        plt.legend(
            loc="upper center",
            prop={"size": 8},
            bbox_to_anchor=(0.5, 1.25),
            ncol=2,
        )
        fig.subplots_adjust(top=0.8)
        plt.show()

        fig, ax = plt.subplots(figsize=(10, 5))
        dhwBus["sequences"].plot(
            ax=ax, kind="line", drawstyle="steps-post"
        )
        plt.legend(
            loc="upper center", prop={"size": 8}, bbox_to_anchor=(0.5, 1.3), ncol=2
        )
        fig.subplots_adjust(top=0.8)
        plt.show()

        fig, ax = plt.subplots(figsize=(10, 5))
        shBus["sequences"].plot(
            ax=ax, kind="line", drawstyle="steps-post"
        )
        plt.legend(
            loc="upper center", prop={"size": 8}, bbox_to_anchor=(0.5, 1.3), ncol=2
        )
        fig.subplots_adjust(top=0.8)
        plt.show()

    logging.info("Done!")
