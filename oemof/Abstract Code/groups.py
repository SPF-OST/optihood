import numpy as np
import pandas as pd
import oemof.solph as solph
from oemof.tools import logger
from oemof.tools import economics
import logging
import os
import pprint as pp
import oemof_visio as oev
import bokeh
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from converters import HeatPumpLinear, CHP
from storages import ElectricalStorage, ThermalStorage

intRate = 0.05


class Building:
    def __init__(self, label):
        self.__nodesList = []
        self.__inputs = []
        self.__technologies = []
        self.__costParam = {}
        self.__envParam = {}
        self.__busDict = {}
        self.__buildingLabel = label

    def getBuildingLabel(self):
        return self.__buildingLabel

    def getNodesList(self):
        return self.__nodesList

    def getBusDict(self):
        return self.__busDict

    def getInputs(self):
        return self.__inputs

    def getTechnologies(self):
        return self.__technologies

    def getCostParam(self):
        return self.__costParam

    def getEnvParam(self):
        return self.__envParam

    def addBus(self, data):
        # Create Bus objects from buses table
        for i, b in data.iterrows():
            if b["active"]:
                bus = solph.Bus(label=b["label"]+'__'+self.__buildingLabel)
                self.__nodesList.append(bus)
                self.__busDict[b["label"]+'__'+self.__buildingLabel] = bus

                if b["excess"]:
                    self.__nodesList.append(
                        solph.Sink(
                            label="excess"+b["label"]+'__'+self.__buildingLabel,
                            inputs={
                                self.__busDict[b["label"]+'__'+self.__buildingLabel]: solph.Flow(
                                    variable_costs=b["excess costs"]
                                )
                            },
                        )
                    )
                    self.__costParam["excess" + b["label"]+'__'+self.__buildingLabel] = b["excess costs"]

    def addSource(self, data):
        # Create Source objects from table 'commodity sources'
        for i, cs in data.iterrows():
            if cs["active"]:
                self.__nodesList.append(solph.Source(
                    label=cs["label"]+'__'+self.__buildingLabel,
                    outputs={
                        self.__busDict[cs["to"]+'__'+self.__buildingLabel]: solph.Flow(
                            variable_costs=cs["variable costs"]
                        )
                    },
                ))
            self.__costParam[cs["label"]+'__'+self.__buildingLabel] = cs["variable costs"]
            self.__envParam[cs["label"]+'__'+self.__buildingLabel] = cs["CO2 impact"]
            self.__inputs.append([cs["to"]+'__'+self.__buildingLabel, cs["label"]+'__'+self.__buildingLabel])

    def addSink(self, data, timeseries):
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
                        label=de["label"]+'__'+self.__buildingLabel,
                        inputs={self.__busDict[de["from"]+'__'+self.__buildingLabel]: solph.Flow(**inflow_args)},
                    )
                )

    def addTransformer(self, data, temperatureDHW, temperatureSH, temperatureAmb):
        for i, t in data.iterrows():
            if t["active"]:
                if t["label"] == "HP":
                    heatPump = HeatPumpLinear(self.__buildingLabel, temperatureDHW, temperatureSH, temperatureAmb,
                                              self.__busDict[t["from"]+'__'+self.__buildingLabel],
                                              self.__busDict[t["to"].split(",")[0]+'__'+self.__buildingLabel],
                                              self.__busDict[t["to"].split(",")[1]+'__'+self.__buildingLabel],
                                              t["capacity_min"], t["capacity_SH"],
                                              self._calculateInvest(t)[0], self._calculateInvest(t)[1])
                    self.__nodesList.append(heatPump.getHP("sh"))
                    self.__nodesList.append(heatPump.getHP("dhw"))
                    self.__costParam[t["label"] + "_SH"+'__'+self.__buildingLabel] = [self._calculateInvest(t)[0],
                                                                                      self._calculateInvest(t)[1]]
                    self.__envParam[t["label"] + "_SH"+'__'+self.__buildingLabel] = [t["heat_impact"], 0,
                                                                                     t["impact_cap"] / t["lifetime"]]
                    self.__technologies.append([t["to"].split(",")[0]+'__'+self.__buildingLabel, t["label"] + "_SH"+'__'
                                                + self.__buildingLabel])
                    self.__costParam[t["label"] + "_DHW"+'__'+self.__buildingLabel] = [self._calculateInvest(t)[0],
                                                                                       self._calculateInvest(t)[1]]
                    self.__envParam[t["label"] + "_DHW"+'__'+self.__buildingLabel] = [t["heat_impact"], 0,
                                                                                      t["impact_cap"] / t["lifetime"]]
                    self.__technologies.append([t["to"].split(",")[1]+'__'+self.__buildingLabel, t["label"] + "_DHW" +
                                                '__'+self.__buildingLabel])
                elif t["label"] == "CHP":
                    # motoric CHP
                    self.__nodesList.append(CHP(self.__buildingLabel, self.__busDict[t["from"]+'__'+self.__buildingLabel],
                                                self.__busDict[t["to"].split(",")[0]+'__'+self.__buildingLabel],
                                                self.__busDict[t["to"].split(",")[1]+'__'+self.__buildingLabel],
                                                self.__busDict[t["to"].split(",")[2]+'__'+self.__buildingLabel],
                                                float(t["efficiency"].split(",")[0]), float(t["efficiency"].split(",")[1]),
                                                float(t["efficiency"].split(",")[2]), t["capacity_min"], t["capacity_el"],
                                                t["capacity_SH"], t["capacity_DHW"], self._calculateInvest(t)[0],
                                                self._calculateInvest(t)[1]))
                    self.__costParam[t["label"]+'__'+self.__buildingLabel] = [self._calculateInvest(t)[0],
                                                                              self._calculateInvest(t)[1]]
                    self.__envParam[t["label"]+'__'+self.__buildingLabel] = [t["heat_impact"], t["elec_impact"],
                                                                             t["impact_cap"] / t["lifetime"]]
                    self.__technologies.append([t["to"].split(",")[0]+'__'+self.__buildingLabel, t["label"] + '__' +
                                                self.__buildingLabel])
                    self.__technologies.append([t["to"].split(",")[1]+'__'+self.__buildingLabel, t["label"] + '__' +
                                                self.__buildingLabel])
                else:
                    logging.warning("Transformer label not identified...")

    def addStorage(self, data, stratifiedStorageParams, temperatureDHW, temperatureSH):
        for i, s in data.iterrows():
            if s["active"]:
                self.__costParam[s["label"]+'__'+self.__buildingLabel] = [self._calculateInvest(s)[0],
                                                                          self._calculateInvest(s)[1]]
                self.__envParam[s["label"]+'__'+self.__buildingLabel] = [s["heat_impact"], s["elec_impact"],
                                                                         s["impact_cap"] / s["lifetime"]]
                self.__technologies.append([s["bus"]+'__'+self.__buildingLabel, s["label"]+'__'+self.__buildingLabel])
                if s["label"] == "electricalStorage":
                    self.__nodesList.append(ElectricalStorage(self.__buildingLabel, self.__busDict[
                                                                s["bus"]+'__'+self.__buildingLabel], s["capacity loss"],
                                                              s["initial capacity"], s["efficiency inflow"],
                                                              s["efficiency outflow"], s["capacity min"],
                                                              s["capacity max"], self._calculateInvest(s)[0],
                                                              self._calculateInvest(s)[1]))
                else:
                    if s["label"] == "dhwStorage":
                        self.__nodesList.append(ThermalStorage(s["label"]+'__'+self.__buildingLabel,
                                                               stratifiedStorageParams, temperatureDHW,
                                                               self.__busDict[s["bus"]+'__'+self.__buildingLabel],
                                                               s["initial capacity"], s["capacity min"],
                                                               s["capacity max"], self._calculateInvest(s)[0],
                                                               self._calculateInvest(s)[1]))
                    elif s["label"] == "shStorage":
                        self.__nodesList.append(ThermalStorage(s["label"]+'__'+self.__buildingLabel,
                                                               stratifiedStorageParams, temperatureSH,
                                                               self.__busDict[s["bus"]+'__'+self.__buildingLabel],
                                                               s["initial capacity"], s["capacity min"],
                                                               s["capacity max"], self._calculateInvest(s)[0],
                                                               self._calculateInvest(s)[1]))
                    else:
                        logging.warning("Storage label not identified")

    def _calculateInvest(self, data):
        c = data["maintenance"] + data["installation"] + data["planification"] + 1
        perCapacity = economics.annuity(c * data["invest_cap"], data["lifetime"], intRate)
        base = economics.annuity(c * data["invest_base"], data["lifetime"], intRate)
        return perCapacity, base

class EnergyNetwork(solph.EnergySystem):
    def __init__(self, timestamp, tSH, tDHW):
        self.__temperatureSH = tSH
        self.__temperatureDHW = tDHW
        self.__nodesList = []
        self.__inputs = []
        self.__technologies = []
        self.__costParam = {}
        self.__envParam = {}
        self.__capex = 0
        self.__opex = 0
        self.__feedIn = 0
        self.__envImpactInputs = 0
        self.__envImpactTechnologies = 0
        logger.define_logging(logpath=os.getcwd())
        logging.info("Initializing the energy network")
        super(EnergyNetwork, self).__init__(timeindex=timestamp)

    def setFromExcel(self,filePath):
        # does Excel file exist?
        if not filePath or not os.path.isfile(filePath):
            logging.error("Excel data file {} not found.".format(filePath))
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
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
        logging.info("Data from Excel file {} imported.".format(filePath))
        self._convertNodes(nodesData)
        logging.info("Nodes from Excel file {} successfully converted".format(filePath))
        self.add(*self.__nodesList)
        logging.info("Nodes successfully added to the energy network")

    def _convertNodes(self, data):
        if not data:
            logging.error("Nodes data is missing.")
        self.__temperatureAmb = np.array(data["timeseries"]["temperature.actual"])
        self._addBuildings(data)

    def _addBuildings(self, data):
        numberOfBuildings = max(data["buses"]["building"])
        self.__buildings = [Building('Building'+str(i+1)) for i in range(numberOfBuildings)]
        for b in self.__buildings:
            i = int(b.getBuildingLabel()[8:])
            b.addBus(data["buses"][data["buses"]["building"] == i])
            b.addSource(data["commodity_sources"][data["buses"]["building"] == i])
            b.addSink(data["demand"][data["buses"]["building"] == i], data["timeseries"].filter(regex=str(i)))
            b.addTransformer(data["transformers"][data["buses"]["building"] == i], self.__temperatureDHW,
                             self.__temperatureSH, self.__temperatureAmb)
            b.addStorage(data["storages"][data["buses"]["building"] == i], data["stratified_storage"],
                         self.__temperatureDHW, self.__temperatureSH)
            self.__nodesList.extend(b.getNodesList())
            self.__inputs.extend(b.getInputs())
            self.__technologies.extend(b.getTechnologies())
            self.__costParam.update(b.getCostParam())
            self.__envParam.update(b.getEnvParam())

    def printNodes(self):
        print("*********************************************************")
        print("The following objects have been created from excel sheet:")
        for n in self.nodes:
            oobj = str(type(n)).replace("<class 'oemof.solph.", "").replace("'>", "")
            print(oobj + ":", n.label)
        print("*********************************************************")

    def optimize(self, solver):
        logging.info("Initiating optimization using {} solver".format(solver))
        optimizationModel = solph.Model(self)
        optimizationModel.solve(solver=solver)
        self.__optimizationResults = solph.processing.results(optimizationModel)
        self.__metaResults = solph.processing.meta_results(optimizationModel)
        logging.info("Optimization successful and results collected")
        self.__capex = sum(solph.views.node(self.__optimizationResults, i[0])["scalars"][((i[1], i[0]), "invest")]
                           * self.__costParam[i[1]][0] + self.__costParam[i[1]][1] *
                           (int(solph.views.node(self.__optimizationResults, i[0])["scalars"][((i[1], i[0]), "invest")])
                            > 0) for i in self.__technologies)
        self.__opex = sum(sum(solph.views.node(self.__optimizationResults, i[0])["sequences"][(i[1], i[0]), "flow"])
                          * self.__costParam[i[1]] for i in self.__inputs)
        self.__feedIn = sum(sum(solph.views.node(self.__optimizationResults, "electricityBus"+'__'+b.getBuildingLabel())
                                ["sequences"][("electricityBus"+'__'+b.getBuildingLabel(), "excesselectricityBus"
                                               +'__'+b.getBuildingLabel()), "flow"]) * self.__costParam[
                                            "excesselectricityBus"+'__'+b.getBuildingLabel()] for b in self.__buildings)
        self.__envImpactInputs = sum(sum(solph.views.node(self.__optimizationResults, i[0])
                                 ["sequences"][(i[1], i[0]), "flow"]) * self.__envParam[i[1]] for i in self.__inputs)
        self.__envImpactTechnologies = sum(solph.views.node(self.__optimizationResults, i[0])
                                           ["scalars"][((i[1], i[0]),"invest")] * self.__envParam[i[1]][2]
                                           for i in self.__technologies) + \
                                       sum(sum(solph.views.node(self.__optimizationResults, i[0])["sequences"]
                                               [((i[1], i[0]), "flow")] * self.__envParam[i[1]][1] *
                                               ('electricityBus' in i[0]) + solph.views.node(self.__optimizationResults, i[0])
                                               ["sequences"][((i[1], i[0]), "flow")] * self.__envParam[i[1]][0] *
                                               ('electricityBus' not in i[0]) for i in self.__technologies))

    def printMetaresults(self):
        print("Meta Results:")
        pp.pprint(self.__metaResults)
        print("")

    def printStateofCharge(self, type, building):
        storage = self.groups[type+'__'+building]
        print(f"""********* State of Charge ({type},{building}) *********""")
        print(
            self.__optimizationResults[(storage, None)]["sequences"]
        )
        print("")

    def printInvestedCapacities(self):
        investSH = solph.views.node(self.__optimizationResults, "spaceHeatingBus"+'__'+'Building1')["scalars"][
            (("HP_SH"+'__'+'Building1', "spaceHeatingBus"+'__'+'Building1'), "invest")]
        investDHW = solph.views.node(self.__optimizationResults, "domesticHotWaterBus"+'__'+'Building1')["scalars"][
            (("HP_DHW"+'__'+'Building1', "domesticHotWaterBus"+'__'+'Building1'), "invest")]
        print("Invested in {}kW :SH and {}kW :DHW HP.".format(investSH, investDHW))

        invest = solph.views.node(self.__optimizationResults, "spaceHeatingBus"+'__'+'Building1')["scalars"][
            (("CHP"+'__'+'Building1', "spaceHeatingBus"+'__'+'Building1'), "invest")] + solph.views.node(
            self.__optimizationResults, "electricityBus"+'__'+'Building1')[
            "scalars"][(("CHP"+'__'+'Building1', "electricityBus"+'__'+'Building1'), "invest")]
        print("Invested in {} kW CHP.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "electricityBus"+'__'+'Building1')["scalars"][
            (("electricalStorage"+'__'+'Building1', "electricityBus"+'__'+'Building1'), "invest")]
        print("Invested in {} kW Electrical Storage.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "domesticHotWaterBus"+'__'+'Building1')["scalars"][
            (("dhwStorage"+'__'+'Building1', "domesticHotWaterBus"+'__'+'Building1'), "invest")]
        print("Invested in {} kW DHW Storage Tank.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "spaceHeatingBus"+'__'+'Building1')["scalars"][
            (("shStorage"+'__'+'Building1', "spaceHeatingBus"+'__'+'Building1'), "invest")
        ]
        print("Invested in {} kW SH Storage Tank.".format(invest))

    def printCosts(self):
        print("Investment Cost: {} CHF".format(self.__capex))
        print("Operation Cost: : {} CHF".format(self.__opex))
        print("Feed In Cost: {} CHF".format(self.__feedIn))
        print("Total Cost: : {} CHF".format(self.__capex + self.__opex - self.__feedIn))

    def printEnvImpacts(self):
        print("Environmental impact from input resources: {}".format(self.__envImpactInputs))
        print("Environmental impact from energy conversion technologies: {}".format(self.__envImpactTechnologies))

    def exportToExcel(self, file_name):
        costs = {"Operation": self.__opex,
                 "Investment": self.__capex,
                 "Feed-in": self.__feedIn,
                 }
        env_impact = {}
        list = []

        for i in self.nodes:
            if str(type(i)).replace("<class 'oemof.solph.", "").replace("'>", "") == "network.bus.Bus":
                list.append(i.label)

        for i in self.__inputs:
            env_impact[i[1]] = sum(solph.views.node(self.__optimizationResults, i[0])["sequences"][(i[1], i[0]), "flow"]) * self.__envParam[i[1]]
        for i in self.__technologies:
            env_impact[i[1]] = solph.views.node(self.__optimizationResults, i[0])["scalars"][((i[1], i[0]), "invest")] * self.__envParam[i[1]][2] + \
            sum(solph.views.node(self.__optimizationResults, i[0])["sequences"]
                [((i[1], i[0]), "flow")] * self.__envParam[i[1]][1] *
                ('electricityBus' in i[0]) + solph.views.node(self.__optimizationResults, i[0])
                ["sequences"][((i[1], i[0]), "flow")] * self.__envParam[i[1]][0] *
                ('electricityBus' not in i[0]))
            
        costs_n = pd.DataFrame.from_dict(costs, orient='index')
        env_n = pd.DataFrame.from_dict(env_impact, orient='index')

        with pd.ExcelWriter(file_name) as writer:
            for i in list:
                a = pd.DataFrame.from_dict(solph.views.node(self.__optimizationResults, i)["sequences"])
                a.to_excel(writer, sheet_name=i)
            costs_n.to_excel(writer, sheet_name="costs")
            env_n.to_excel(writer, sheet_name="env_impacts")
