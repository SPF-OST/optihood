import numpy as np
import pandas as pd
import oemof.solph as solph
from oemof.network.network import Node
import oemof.thermal.compression_heatpumps_and_chillers as hp
from oemof.tools import logger
import logging
import os
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

if __name__ == '__main__':

    ############################
    # Define The Energy System #
    ############################

    # read data from excel file

    def nodes_from_excel(filePath):
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
        }

        # set datetime index
        nodesData["timeseries"].set_index("timestamp", inplace=True)
        nodesData["timeseries"].index = pd.to_datetime(
            nodes_data["timeseries"].index
        )

        print("Data from Excel file {} imported.".format(filePath))

        return nodes_data

    def create_nodes(nd=None):
        """Create nodes (oemof objects) from node dict
            Parameters
            ----------
            nd : :obj:`dict`
                Nodes data
            Returns
            -------
            nodes : `obj`:dict of :class:`nodes <oemof.network.Node>`
            """

        if not nd:
            raise ValueError("No nodes data provided.")

        nodes = []
        # Create Bus objects from buses table
        busd = {}

        for i, b in nd["buses"].iterrows():
            if b["active"]:
                bus = solph.Bus(label=b["label"])
                nodes.append(bus)

                busd[b["label"]] = bus
                if b["excess"]:
                    nodes.append(
                        solph.Sink(
                            label=b["label"] + "_excess",
                            inputs={
                                busd[b["label"]]: solph.Flow(
                                    variable_costs=b["excess costs"]
                                )
                            },
                        )
                    )
                if b["shortage"]:
                    nodes.append(
                        solph.Source(
                            label=b["label"] + "_shortage",
                            outputs={
                                busd[b["label"]]: solph.Flow(
                                    variable_costs=b["shortage costs"]
                                )
                            },
                        )
                    )

        # Create Source objects from table 'commodity sources'
        for i, cs in nd["commodity_sources"].iterrows():
            if cs["active"]:
                nodes.append(
                    solph.Source(
                        label=cs["label"],
                        outputs={
                            busd[cs["to"]]: solph.Flow(
                                nominal_value=cs["nominal value"],
                                max=1,
                                min=0,
                                variable_costs=cs["variable costs"]
                            )
                        },
                    )
                )

        # Create Sink objects with fixed time series from 'demand' table
        for i, de in nd["demand"].iterrows():
            if de["active"]:
                # set static inflow values
                inflow_args = {"nominal_value": de["nominal value"], "fixed": de["fixed"]}
                # get time series for node and parameter
                for col in nd["timeseries"].columns.values:
                    if col.split(".")[0] == de["label"]:
                        inflow_args[col.split(".")[1]] = nd["timeseries"][col]

                # create
                nodes.append(
                    solph.Sink(
                        label=de["label"],
                        inputs={busd[de["from"]]: solph.Flow(**inflow_args)},
                    )
                )

            # Create Transformer objects from 'transformers' table
        for i, t in nd["transformers"].iterrows():
            if t["active"]:
                if t["label"] == "HP":
                    coefCOP = [12.4896, 64.0652, -83.0217, -230.1195, 173.2122]
                    coefQ = [13.8603,120.2178,-7.9046,-164.1900,-17.9805]
                    Temperature_a = np.array(nd["actual_data"]["temperature.actual"])
                    Temperature_sh = 35/273.15
                    Temperature_dhw = 55/273.15
                    QCondenser_sh = coefQ[0]+(coefQ[1]*Temperature_a)+(coefQ[2]*Temperature_sh)+(coefQ[3]*Temperature_a*Temperature_sh)+(coefQ[4]*Temperature_sh*Temperature_sh)
                    WCompressor_sh = coefCOP[0]+(coefCOP[1]*Temperature_a)+(coefCOP[2]*Temperature_sh)+(coefCOP[3]*Temperature_a*Temperature_sh)+(coefCOP[4]*Temperature_sh*Temperature_sh)
                    QCondenser_dhw = coefQ[0] + (coefQ[1] * Temperature_a) + (coefQ[2] * Temperature_dhw) + (coefQ[3] * Temperature_a * Temperature_dhw) + (coefQ[4] * Temperature_dhw * Temperature_dhw)
                    WCompressor_dhw = coefCOP[0] + (coefCOP[1] * Temperature_a) + (coefCOP[2] * Temperature_dhw) + (coefCOP[3] * Temperature_a * Temperature_dhw) + (coefCOP[4] * Temperature_dhw * Temperature_dhw)
                    COP_sh = np.divide(QCondenser_sh,WCompressor_sh)
                    COP_dhw = np.divide(QCondenser_dhw,WCompressor_dhw)
                    nodes.append(
                        solph.Transformer(
                            label=t["label"],
                            inputs={busd[t["from"]]: solph.Flow(variable_costs=t["variable input costs"])},
                            outputs={
                                busd[t["to"].split(",")[0]]: solph.Flow(nominal_value=t["capacity"].split(",")[0]),
                                busd[t["to"].split(",")[1]]: solph.Flow(nominal_value=t["capacity"].split(",")[1])},
                            conversion_factors={busd[t["to"].split(",")[0]]: COP_sh,
                                                busd[t["to"].split(",")[1]]: COP_dhw},
                        )
                    )
                elif t["label"] == "CHP":  #Combined cycle extraction turbine
                    nodes.append(
                        solph.components.GenericCHP(
                        label=t["label"],
                        fuel_input={
                            busd[t["from"]]: solph.Flow(H_L_FG_share_max=[0.19 for p in range(0, 24)])
                        },
                        electrical_output={
                            busd[t["to"].split(",")[0]]: solph.Flow(
                                P_max_woDH=[200 for p in range(0, 24)],
                                P_min_woDH=[80 for p in range(0, 24)],
                                Eta_el_max_woDH=[0.53 for p in range(0, 24)],
                                Eta_el_min_woDH=[0.43 for p in range(0, 24)],
                            )
                        },
                        heat_output={busd[t["to"].split(",")[1]]: solph.Flow(Q_CW_min=[30 for p in range(0, 24)]),       ##### TO BE CHECKED ###
                                     busd[t["to"].split(",")[2]]: solph.Flow(Q_CW_min=[30 for p in range(0, 24)])},
                        Beta=[0.19 for p in range(0, 24)],
                        back_pressure=False,
                        )
                    )
                   # nodes.append(
                   #     solph.Transformer(
                   #         label=t["label"],
                   #         inputs={busd[t["from"]]: solph.Flow(variable_costs=t["variable input costs"])},
                   #         outputs={
                   #             busd[t["to"].split(",")[0]]: solph.Flow(nominal_value=t["capacity"].split(",")[0]),
                   #             busd[t["to"].split(",")[1]]: solph.Flow(nominal_value=t["capacity"].split(",")[1]),
                   #             busd[t["to"].split(",")[2]]: solph.Flow(nominal_value=t["capacity"].split(",")[2])},
                   #         conversion_factors={busd[t["to"].split(",")[0]]: t["efficiency"].split(",")[0],
                   #                             busd[t["to"].split(",")[1]]: t["efficiency"].split(",")[1],
                   #                             busd[t["to"].split(",")[2]]: t["efficiency"].split(",")[2]},
                   #     )
                   # )
                else:
                    print("Transformer label not identified...")

            # Create Storage objects from 'transformers' table
        for i, s in nd["storages"].iterrows():
            if s["active"]:
                if s["label"] == "electricalStorage":
                    nodes.append(
                        solph.components.GenericStorage(
                            label=s["label"],
                            inputs={
                                busd[s["bus"]]: solph.Flow(
                                    nominal_value=s["capacity inflow"],
                                    variable_costs=s["variable input costs"],
                                )
                            },
                            outputs={
                                busd[s["bus"]]: solph.Flow(
                                    nominal_value=s["capacity outflow"],
                                    variable_costs=s["variable output costs"],
                                )
                            },
                            nominal_storage_capacity=s["nominal capacity"],
                            loss_rate=s["capacity loss"],
                            initial_storage_level=s["initial capacity"],
                            max_storage_level=s["capacity max"],
                            min_storage_level=s["capacity min"],
                            inflow_conversion_factor=s["efficiency inflow"],
                            outflow_conversion_factor=s["efficiency outflow"],
                        )
                    )
                elif s["label"] == "thermalStorage":

                    # Pre-calculation

                    u_value = calculate_storage_u_value(
                        nd["stratified_storage"]['s_iso'],
                        nd["stratified_storage"]['lamb_iso'],
                        nd["stratified_storage"]['alpha_inside'],
                        nd["stratified_storage"]['alpha_outside'])

                    volume, surface = calculate_storage_dimensions(
                        nd["stratified_storage"]['height'],
                        nd["stratified_storage"]['diameter']
                    )

                    nominal_storage_capacity = calculate_capacities(
                        volume,
                        nd["stratified_storage"]['temp_h'],
                        nd["stratified_storage"]['temp_c'])

                    loss_rate, fixed_losses_relative, fixed_losses_absolute = calculate_losses(
                        u_value,
                        nd["stratified_storage"]['diameter'],
                        nd["stratified_storage"]['temp_h'],
                        nd["stratified_storage"]['temp_c'],
                        nd["stratified_storage"]['temp_env'])

                    def print_parameters():
                        parameter = {
                            'U-value [W/(m2*K)]': u_value,
                            'Volume [m3]': volume,
                            'Surface [m2]': surface,
                            'Nominal storage capacity [MWh]': nominal_storage_capacity,
                            'Loss rate [-]': loss_rate,
                            'Fixed relative losses [-]': fixed_losses_relative,
                            'Fixed absolute losses [MWh]': fixed_losses_absolute,
                        }

                        dash = '-' * 50

                        print(dash)
                        print('{:>32s}{:>15s}'.format('Parameter name', 'Value'))
                        print(dash)

                        for name, param in parameter.items():
                            print('{:>32s}{:>15.5f}'.format(name, param))

                        print(dash)

                    print_parameters()

                    nodes.append(
                        solph.components.GenericStorage(
                            label=s["label"],
                            inputs={
                                busd[s["bus"].split(",")[0]]: Flow(nominal_value=nd["stratified_storage"]['maximum_heat_flow_charging']),
                                busd[s["bus"].split(",")[1]]: Flow(nominal_value=nd["stratified_storage"]['maximum_heat_flow_charging'])
                            },
                            outputs={
                                busd[s["bus"].split(",")[0]]: Flow(nominal_value=nd["stratified_storage"]['maximum_heat_flow_discharging'], variable_costs=s["variable output costs"].split(",")[0]),
                                busd[s["bus"].split(",")[1]]: Flow(nominal_value=nd["stratified_storage"]['maximum_heat_flow_discharging'], variable_costs=s["variable output costs"].split(",")[1])
                            },
                            nominal_storage_capacity=nominal_storage_capacity,
                            loss_rate=loss_rate,
                            fixed_losses_relative=fixed_losses_relative,
                            fixed_losses_absolute=fixed_losses_absolute,
                            max_storage_level=nd["stratified_storage"]['max_storage_level'],
                            min_storage_level=nd["stratified_storage"]['min_storage_level'],
                            inflow_conversion_factor=nd["stratified_storage"]['inflow_conversion_factor'],
                            outflow_conversion_factor=nd["stratified_storage"]['outflow_conversion_factor'],
                        )
                    )
                else:
                    print("Storage label not identified...")
        return nodes


    def draw_graph(
            grph,
            edge_labels=True,
            node_color="#AFAFAF",
            edge_color="#CFCFCF",
            plot=True,
            node_size=2000,
            with_labels=True,
            arrows=True,
            layout="neato",
    ):
        """
        Parameters
        ----------
        grph : networkxGraph
            A graph to draw.
        edge_labels : boolean
            Use nominal values of flow as edge label
        node_color : dict or string
            Hex color code oder matplotlib color for each node. If string, all
            colors are the same.
        edge_color : string
            Hex color code oder matplotlib color for edge color.
        plot : boolean
            Show matplotlib plot.
        node_size : integer
            Size of nodes.
        with_labels : boolean
            Draw node labels.
        arrows : boolean
            Draw arrows on directed edges. Works only if an optimization_model has
            been passed.
        layout : string
            networkx graph layout, one of: neato, dot, twopi, circo, fdp, sfdp.
        """
        if type(node_color) is dict:
            node_color = [node_color.get(g, "#AFAFAF") for g in grph.nodes()]

        # set drawing options
        options = {
            "prog": "dot",
            "with_labels": with_labels,
            "node_color": node_color,
            "edge_color": edge_color,
            "node_size": node_size,
            "arrows": arrows,
        }

        # try to use pygraphviz for graph layout
        try:
            import pygraphviz

            pos = nx.drawing.nx_agraph.graphviz_layout(grph, prog=layout)
        except ImportError:
            logging.error("Module pygraphviz not found, I won't plot the graph.")
            return

        # draw graph
        nx.draw(grph, pos=pos, **options)

        # add edge labels for all edges
        if edge_labels is True and plt:
            labels = nx.get_edge_attributes(grph, "weight")
            nx.draw_networkx_edge_labels(grph, pos=pos, edge_labels=labels)

        # show output
        if plot is True:
            plt.show()


    logger.define_logging()
    datetime_index = pd.date_range(
        "2021-01-01 00:00:00", "2021-01-01 23:00:00", freq="60min"
    )

    # model creation and solving
    logging.info("Starting optimization")

    # initialisation of the energy system
    esys = solph.EnergySystem(timeindex=datetime_index)

    # read node data from Excel sheet
    excel_nodes = nodes_from_excel(os.path.join(os.getcwd(), "scenario.xlsx", ))

    # create nodes from Excel sheet data
    my_nodes = create_nodes(nd=excel_nodes)

    # add nodes and flows to energy system
    esys.add(*my_nodes)

    print("*********************************************************")
    print("The following objects have been created from excel sheet:")
    for n in esys.nodes:
        oobj = str(type(n)).replace("<class 'oemof.solph.", "").replace("'>", "")
        print(oobj + ":", n.label)
    print("*********************************************************")

    # creation of a least cost model from the energy system
    om = solph.Model(esys)
    om.receive_duals()

    # solving the linear problem using the selected solver
    om.solve(solver="gurobi")

    # create graph of esys
    # You can use argument filename='/home/somebody/my_graph.graphml'
    # to dump your graph to disc. You can open it using e.g. yEd or gephi
    graph = create_nx_graph(esys)

    # plot esys graph
    draw_graph(
        grph=graph,
        plot=True,
        layout="neato",
        node_size=1000,
        node_color={"electricityBus": "#cd3333", "spaceHeatingBus": "#cd3333", "domesticHotWaterBus": "#cd3333"},
    )

    # print and plot some results
    results = solph.processing.results(om)

    region1 = solph.views.node(results, "spaceHeatingBus")
    region2 = solph.views.node(results, "domesticHotWaterBus")
    region3 = solph.views.node(results, "electricityBus")

    print(region1["sequences"].sum())
    print(region2["sequences"].sum())
    print(region3["sequences"].sum())

    fig, ax = plt.subplots(figsize=(10, 5))
    region1["sequences"].plot(ax=ax)
    ax.legend(
        loc="upper center", prop={"size": 8}, bbox_to_anchor=(0.5, 1.4), ncol=3
    )
    fig.subplots_adjust(top=0.7)
    plt.show()
    logging.info("Done!")

    #filePath = os.path.join(os.getcwd(), "data.xlsx")
    #naturalGasBus = solph.Bus(label='natural gas')
    #ambientTemperatureBus = solph.Bus(label='ambient temperature')
    #electricityBus = solph.Bus(label='electricity')
    #shBus = solph.Bus(label='space heating')
    #dhwBus = solph.Bus(label='domestic hot water')

    #busList = [naturalGasBus, ambientTemperatureBus, electricityBus, shBus, dhwBus]

    #basicEnergySystem.add(*busList)





