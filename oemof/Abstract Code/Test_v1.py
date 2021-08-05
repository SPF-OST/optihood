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

import oemof_visio as oev
from ttictoc import tic,toc
import bokeh

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

class HeatPumpLinear:
    def __init__(self, temperatureDHW, temperatureSH, temperatureLow):
        self.__copDHW = self._calculate_cop(temperatureDHW, temperatureLow)
        self.__copSH= self._calculate_cop(temperatureSH, temperatureLow)

    def _calculate_cop(self,tHigh,tLow):
        coefCOP = [12.4896, 64.0652, -83.0217, -230.1195, 173.2122]
        coefQ = [13.8603, 120.2178, -7.9046, -164.1900, -17.9805]
        QCondenser = coefQ[0] + (coefQ[1] * tLow / 273.15) + (coefQ[2] * tHigh / 273.15) + (
                coefQ[3] * tLow / 273.15 * tHigh / 273.15) + (
                                 coefQ[4] * tHigh / 273.15 * tHigh / 273.15)
        WCompressor = coefCOP[0] + (coefCOP[1] * tLow / 273.15) + (coefCOP[2] * tHigh / 273.15) + (
                coefCOP[3] * tLow / 273.15 * tHigh / 273.15) + (
                                  coefCOP[4] * tHigh / 273.15 * tHigh / 273.15)
        cop = np.divide(QCondenser, WCompressor)
        return cop

    def cop(self,type):
        if type == 'sh':
            return self.__copSH
        elif type == 'dhw':
            return self.__copDHW
        else:
            print("Transformer label not identified...")

class EnergyNetwork:
    def __init__(self,timestamp,tSH,tDHW):
        self.__datetime = timestamp
        self.__numberOfTimeSteps = len(self.__datetime)
        self.__system = solph.EnergySystem(timeindex=self.__datetime)
        self.__temperatureSH = tSH
        self.__temperatureDHW = tDHW
        self.__nodesList = []
        self.__capex = 0
        self.__opex = 0
        self.__feedin = 0

    @property
    def system(self):
        return self.__system

    @property
    def optimizationResults(self):
        return self.__optimizationResults

    @property
    def capex(self):
        return self.__capex

    @property
    def opex(self):
        return self.__opex

    @property
    def datetime(self):
        return self.__datetime

    @datetime.setter
    def datetime(self, new_timestamp):
        self.__datetime = new_timestamp
        self.__numberOfTimeSteps = len(self.__datetime)
        self.__system = solph.EnergySystem(timeindex=self.__datetime)

    def setFromExcel(self,filePath):
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
        self._convertNodes(nodesData, self.__numberOfTimeSteps)
        self.__system.add(*self.__nodesList)

    def _convertNodes(self,data,time):
        if not data:
            raise ValueError("No nodes data provided.")
        self.__temperatureAmb = np.array(data["timeseries"]["temperature.actual"])
        self._addBus(data["buses"])
        self._addSource(data["commodity_sources"])
        self._addSink(data["demand"], data["timeseries"])
        self._addTransformer(data["transformers"])
        self._addStorage(data["storages"], data["stratified_storage"])

    def _addBus(self, data):
        # Create Bus objects from buses table
        self.__busDict = {}
        for i, b in data.iterrows():
            if b["active"]:
                bus = solph.Bus(label=b["label"])
                self.__nodesList.append(bus)
                self.__busDict[b["label"]] = bus

                if b["excess"]:
                    self.__nodesList.append(
                        solph.Sink(
                            label=b["label"] + "_excess",
                            inputs={
                                self.__busDict[b["label"]]: solph.Flow(
                                    variable_costs=b["excess costs"]
                                )
                            },
                        )
                    )

    def _addSource(self, data):
        # Create Source objects from table 'commodity sources'
        for i, cs in data.iterrows():
            if cs["active"]:
                self.__nodesList.append(solph.Source(
                    label=cs["label"],
                    outputs={
                        self.__busDict[cs["to"]]: solph.Flow(
                            variable_costs=cs["variable costs"]
                        )
                    },
                ))

    def _addSink(self, data, timeseries):
        # Create Sink objects with fixed time series from 'demand' table
        for i, de in data.iterrows():
            if de["active"]:
                # set static inflow values, if any
                inflow_args = {"nominal_value": de["nominal value"]}
                # get time series for node and parameter
                for col in timeseries.columns.values:
                    if col.split(".")[0] == de["label"]:
                        inflow_args[col.split(".")[1]] = timeseries[col]

                # create
                self.__nodesList.append(
                    solph.Sink(
                        label=de["label"],
                        inputs={self.__busDict[de["from"]]: solph.Flow(**inflow_args)},
                    )
                )

    def _addTransformer(self,data):
        for i, t in data.iterrows():
            if t["active"]:
                if t["label"] == "HP":
                    heatPump = HeatPumpLinear(self.__temperatureDHW,self.__temperatureSH, self.__temperatureAmb)
                    self.__nodesList.append(
                        solph.Transformer(
                            label=t["label"] + "_SH",
                            inputs={self.__busDict[t["from"]]: solph.Flow()},
                            outputs={
                                self.__busDict[t["to"].split(",")[0]]: solph.Flow(
                                    investment=solph.Investment(
                                        ep_costs=economics.annuity(980, 20, 0.05),
                                        maximum=50,
                                        nonconvex=True,
                                        offset=6950
                                    )
                                )},
                            conversion_factors={self.__busDict[t["to"].split(",")[0]]: heatPump.cop("sh")},
                        )
                    )

                    self.__nodesList.append(
                        solph.Transformer(
                            label=t["label"] + "_DHW",
                            inputs={self.__busDict[t["from"]]: solph.Flow()},
                            outputs={
                                self.__busDict[t["to"].split(",")[1]]: solph.Flow(
                                    investment=solph.Investment(
                                        ep_costs=economics.annuity(980, 20, 0.05),
                                        maximum=50,
                                        nonconvex=True,
                                        offset=6950
                                    )
                                )},
                            conversion_factors={self.__busDict[t["to"].split(",")[1]]: heatPump.cop("dhw")},
                        )
                    )
                elif t["label"] == "CHP":
                    # motoric CHP
                    self.__nodesList.append(
                        solph.components.GenericCHP(
                            label=t["label"],
                            fuel_input={
                                self.__busDict[t["from"]]: solph.Flow(
                                    H_L_FG_share_max=[0.18 for p in range(0, self.__numberOfTimeSteps)],
                                    H_L_FG_share_min=[0.41 for p in range(0, self.__numberOfTimeSteps)])
                            },
                            electrical_output={
                                self.__busDict[t["to"].split(",")[0]]: solph.Flow(
                                    P_max_woDH=[200 for p in range(0, self.__numberOfTimeSteps)],
                                    P_min_woDH=[100 for p in range(0, self.__numberOfTimeSteps)],
                                    Eta_el_max_woDH=[0.44 for p in range(0, self.__numberOfTimeSteps)],
                                    Eta_el_min_woDH=[0.40 for p in range(0, self.__numberOfTimeSteps)],
                                    investment=solph.Investment(
                                        ep_costs=economics.annuity(830, 20, 0.05),
                                        maximum=50,
                                        nonconvex=True,
                                        offset=20700
                                    )
                                )
                            },
                            heat_output={
                                self.__busDict[t["to"].split(",")[1]]: solph.Flow(Q_CW_min=[0 for p in range(0, self.__numberOfTimeSteps)],
                                                                           investment=solph.Investment(
                                                                               ep_costs=economics.annuity(830, 20,
                                                                                                          0.05),
                                                                               maximum=50,
                                                                               nonconvex=True,
                                                                               offset=20700)
                                                                           ),
                                },
                            Beta=[0 for p in range(0, self.__numberOfTimeSteps)],
                            back_pressure=False,
                        )
                    )
                else:
                    print("Transformer label not identified...")

    def _addStorage(self, data, stratifiedStorageParams):
        for i, s in data.iterrows():
            if s["active"]:
                if s["label"] == "electricalStorage":
                    self.__nodesList.append(
                        solph.components.GenericStorage(
                            label=s["label"],
                            inputs={
                                self.__busDict[s["bus"]]: solph.Flow()
                            },
                            outputs={
                                self.__busDict[s["bus"]]: solph.Flow()
                            },
                            # nominal_storage_capacity=s["nominal capacity"],
                            loss_rate=s["capacity loss"],
                            initial_storage_level=s["initial capacity"],
                            inflow_conversion_factor=s["efficiency inflow"],
                            outflow_conversion_factor=s["efficiency outflow"],
                            Balanced=False,
                            invest_relation_input_capacity=s["efficiency inflow"],
                            invest_relation_output_capacity=s["efficiency outflow"],
                            investment=solph.Investment(
                                minimum=s["capacity min"],
                                maximum=s["capacity max"],
                                existing=0,
                                nonconvex=True,
                                offset=1000,
                            ),
                        )
                    )
                else:
                    if s["label"] == "dhwStorage":
                        u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, \
                            fixed_losses_absolute = precalculateStratifiedStorage(stratifiedStorageParams, self.__temperatureDHW)
                    elif s["label"] == "shStorage":
                        u_value, volume, surface, nominal_storage_capacity, loss_rate, fixed_losses_relative, \
                            fixed_losses_absolute = precalculateStratifiedStorage(stratifiedStorageParams, self.__temperatureSH)
                    else:
                        print("Storage label not identified")

                    if s["label"] == "dhwStorage" or "shStorage":
                        self.__nodesList.append(
                            solph.components.GenericStorage(
                                label=s["label"],
                                inputs={
                                    self.__busDict[s["bus"]]: solph.Flow(),
                                },
                                outputs={
                                    self.__busDict[s["bus"]]: solph.Flow()
                                },
                                # nominal_storage_capacity=2000,
                                loss_rate=loss_rate,
                                initial_storage_level=s["initial capacity"],
                                fixed_losses_relative=fixed_losses_relative,
                                fixed_losses_absolute=fixed_losses_absolute,
                                inflow_conversion_factor=stratifiedStorageParams.at[0, 'inflow_conversion_factor'],
                                outflow_conversion_factor=stratifiedStorageParams.at[0, 'outflow_conversion_factor'],
                                balanced=False,
                                invest_relation_input_capacity=stratifiedStorageParams.at[0, 'inflow_conversion_factor'],
                                invest_relation_output_capacity=stratifiedStorageParams.at[0, 'outflow_conversion_factor'],
                                investment=solph.Investment(
                                    minimum=s["capacity min"],
                                    maximum=s["capacity max"],
                                    ep_costs=0,
                                    existing=0,
                                    nonconvex=True,
                                    offset=0,
                                ),
                            )
                        )

    def printNodes(self):
        print("*********************************************************")
        print("The following objects have been created from excel sheet:")
        for n in self.__system.nodes:
            oobj = str(type(n)).replace("<class 'oemof.solph.", "").replace("'>", "")
            print(oobj + ":", n.label)
        print("*********************************************************")

    def optimize(self, solver):
        optimizationModel = solph.Model(self.__system)
        optimizationModel.solve(solver=solver)
        self.__optimizationResults = solph.processing.results(optimizationModel)
        self.__metaResults = solph.processing.meta_results(optimizationModel)
        self.__capex = solph.views.node(self.__optimizationResults, "spaceHeatingBus")["scalars"][
            (("HP_SH", "spaceHeatingBus"), "invest")]*980/2 + 6950/2*bool(solph.views.node(self.__optimizationResults, "spaceHeatingBus")["scalars"][
            (("HP_SH", "spaceHeatingBus"), "invest")]) + solph.views.node(self.__optimizationResults, "domesticHotWaterBus")["scalars"][
            (("HP_DHW", "domesticHotWaterBus"), "invest")]*980/2 + 6950/2*bool(solph.views.node(self.__optimizationResults, "domesticHotWaterBus")["scalars"][
            (("HP_DHW", "domesticHotWaterBus"), "invest")]) + solph.views.node(self.__optimizationResults, "electricityBus")["scalars"][(("electricalStorage", "electricityBus"), "invest")]*830 \
                       + 20700*bool(solph.views.node(self.__optimizationResults, "electricityBus")["scalars"][(("electricalStorage", "electricityBus"), "invest")]) + 1000*bool(solph.views.node(self.__optimizationResults, "electricityBus")["scalars"][(("electricalStorage", "electricityBus"), "invest")])

        #self.__opex = solph.views.node(self.__optimizationResults, "electricityResource")["sequences"][
        #    (("electricityResource", "electricityBus"), "flow")].sum()*0.2244
        self.__opex = 23355.095283 - self.__capex
        #self.__feedin =

    def printMetaresults(self):
        print("Meta Results:")
        pp.pprint(self.__metaResults)

    def printStateofCharge(self,value):
        storage = self.__system.groups[value]
        print(f"""********* State of Charge ({value}) *********""")
        print(
            self.__optimizationResults[(storage, None)]["sequences"]
        )
        print("")

    def printInvestedCapacities(self):
        investSH = solph.views.node(self.__optimizationResults, "spaceHeatingBus")["scalars"][
            (("HP_SH", "spaceHeatingBus"), "invest")]
        investDHW = solph.views.node(self.__optimizationResults, "domesticHotWaterBus")["scalars"][
            (("HP_DHW", "domesticHotWaterBus"), "invest")]
        print("Invested in {} :SH and {} :DHW HP.".format(investSH, investDHW))

        invest = solph.views.node(self.__optimizationResults, "spaceHeatingBus")["scalars"][
            (("CHP", "spaceHeatingBus"), "invest")] + solph.views.node(self.__optimizationResults,
                                                                       "electricityBus")["scalars"][(("CHP", "electricityBus"), "invest")]
        print("Invested in {} CHP.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "electricityBus")["scalars"][(("electricalStorage", "electricityBus"), "invest")]
        print("Invested in {} Electrical Storage.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "domesticHotWaterBus")["scalars"][(("dhwStorage", "domesticHotWaterBus"), "invest")]
        print("Invested in {} DHW Storage Tank.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "spaceHeatingBus")["scalars"][
            (("shStorage", "spaceHeatingBus"), "invest")
        ]
        print("Invested in {} SH Storage Tank.".format(invest))

    def printCosts(self):
        print("CAPEX: {} CHF".format(self.__capex))
        print("OPEX: : {} CHF".format(self.__opex))
        print("Total Cost: : {} CHF".format(self.__capex + self.__opex - self.__feedin))

    def createDump(self, path=os.getcwd(), filename='esys_dump.oemof'):
        self.__system.dump(path, filename)

    def restoreDump(self, path=os.getcwd(), filename='esys_dump.oemof'):
        self.__system.restore(path,filename)
        self.__optimizationResults = self.__system.results


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
    logging.info("Initializing the energy network")
    tic()
    network = EnergyNetwork(pd.date_range("2018-01-01 01:00:00", "2019-01-01 00:00:00", freq="60min"), tSH=35, tDHW=55)
    network.setFromExcel(os.path.join(os.getcwd(), "scenario.xls"))
    network.printNodes()
    network.optimize(solver='gurobi')
    print("Calculation time:")
    print(toc())
    network.printStateofCharge("electricalStorage")
    network.printStateofCharge("dhwStorage")
    network.printStateofCharge("shStorage")
    network.printInvestedCapacities()
    network.printMetaresults()
    network.printCosts()