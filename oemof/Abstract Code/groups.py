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
            self.__inputs.append([cs["label"]+'__'+self.__buildingLabel, cs["to"]+'__'+self.__buildingLabel])

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
                self.__technologies.append([s["to"]+'__'+self.__buildingLabel, s["label"]+'__'+self.__buildingLabel])
                if s["label"] == "electricalStorage":
                    self.__nodesList.append(ElectricalStorage(self.__buildingLabel, self.__busDict[
                                                                s["from"]+'__'+self.__buildingLabel],
                                                              self.__busDict[s["to"]+'__'+self.__buildingLabel],
                                                              s["capacity loss"],
                                                              s["initial capacity"], s["efficiency inflow"],
                                                              s["efficiency outflow"], s["capacity min"],
                                                              s["capacity max"], self._calculateInvest(s)[0],
                                                              self._calculateInvest(s)[1]))
                else:
                    if s["label"] == "dhwStorage":
                        self.__nodesList.append(ThermalStorage(s["label"]+'__'+self.__buildingLabel,
                                                               stratifiedStorageParams, temperatureDHW,
                                                               self.__busDict[s["from"]+'__'+self.__buildingLabel],
                                                               self.__busDict[s["to"] + '__' + self.__buildingLabel],
                                                               s["initial capacity"], s["capacity min"],
                                                               s["capacity max"], self._calculateInvest(s)[0],
                                                               self._calculateInvest(s)[1]))
                    elif s["label"] == "shStorage":
                        self.__nodesList.append(ThermalStorage(s["label"]+'__'+self.__buildingLabel,
                                                               stratifiedStorageParams, temperatureSH,
                                                               self.__busDict[s["from"]+'__'+self.__buildingLabel],
                                                               self.__busDict[s["to"] + '__' + self.__buildingLabel],
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
        self.__capex = {}
        self.__opex = {}
        self.__feedIn = {}
        self.__envImpactInputs = {}
        self.__envImpactTechnologies = {}
        self.__busDict = {}
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
            "stratified_storage": data.parse("stratified_storage"),
            "links": data.parse("links")
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
        self._addLinks(data["links"])

    def _addBuildings(self, data):
        numberOfBuildings = max(data["buses"]["building"])
        self.__buildings = [Building('Building'+str(i+1)) for i in range(numberOfBuildings)]
        for b in self.__buildings:
            i = int(b.getBuildingLabel()[8:])
            b.addBus(data["buses"][data["buses"]["building"] == i])
            b.addSource(data["commodity_sources"][data["commodity_sources"]["building"] == i])
            b.addSink(data["demand"][data["demand"]["building"] == i], data["timeseries"].filter(regex=str(i)))
            b.addTransformer(data["transformers"][data["transformers"]["building"] == i], self.__temperatureDHW,
                             self.__temperatureSH, self.__temperatureAmb)
            b.addStorage(data["storages"][data["storages"]["building"] == i], data["stratified_storage"],
                         self.__temperatureDHW, self.__temperatureSH)
            self.__nodesList.extend(b.getNodesList())
            self.__inputs.extend(b.getInputs())
            self.__technologies.extend(b.getTechnologies())
            self.__costParam.update(b.getCostParam())
            self.__envParam.update(b.getEnvParam())
            self.__busDict.update(b.getBusDict())

    def _addLinks(self, data):
        for i, l in data.iterrows():
            if l["active"]:
                busA = self.__busDict["electricityBus"+'__Building'+str(l["buildingA"])]
                busB = self.__busDict["electricityBus"+'__Building'+str(l["buildingB"])]
                self.__nodesList.append(solph.custom.Link(
                    label=l["label"]+str(l["buildingA"])+'_'+str(l["buildingB"]),
                    inputs ={busA: solph.Flow(), busB: solph.Flow()},
                    outputs={busA: solph.Flow(), busB: solph.Flow()},
                    conversion_factors={(busA, busB): l["efficiency from A to B"],
                                        (busB, busA): l["efficiency from B to A"]}
                ))

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
        for b in self.__buildings:
            n_techno = []
            n_inputs = []
            for i in range(len(self.__technologies)):
                if b.getBuildingLabel() in self.__technologies[i][0]:
                    n_techno.append(self.__technologies[i])
            for i in range(len(self.__inputs)):
                if b.getBuildingLabel() in self.__inputs[i][0]:
                    n_inputs.append(self.__inputs[i])
            self.__capex[b.getBuildingLabel()] = sum(solph.views.node(self.__optimizationResults, i[0])["scalars"][((i[1], i[0]), "invest")]
                           * self.__costParam[i[1]][0] + self.__costParam[i[1]][1] *
                           (int(solph.views.node(self.__optimizationResults, i[0])["scalars"][((i[1], i[0]), "invest")])
                            > 0) for i in n_techno)
            self.__opex[b.getBuildingLabel()] = sum(sum(solph.views.node(self.__optimizationResults, i[1])["sequences"][(i[0], i[1]), "flow"])
                          * self.__costParam[i[0]] for i in n_inputs)
            self.__feedIn[b.getBuildingLabel()] = sum(solph.views.node(self.__optimizationResults, "electricityBus"+'__'+b.getBuildingLabel())
                                ["sequences"][("electricityBus"+'__'+b.getBuildingLabel(), "excesselectricityBus"
                                               +'__'+b.getBuildingLabel()), "flow"]) * self.__costParam[
                                            "excesselectricityBus"+'__'+b.getBuildingLabel()]
            self.__envImpactInputs[b.getBuildingLabel()] = sum(sum(solph.views.node(self.__optimizationResults, i[1])
                                 ["sequences"][(i[0], i[1]), "flow"]) * self.__envParam[i[0]] for i in n_inputs)
            self.__envImpactTechnologies[b.getBuildingLabel()] = sum(solph.views.node(self.__optimizationResults, i[0])
                                           ["scalars"][((i[1], i[0]),"invest")] * self.__envParam[i[1]][2]
                                           for i in n_techno) + \
                                       sum(sum(solph.views.node(self.__optimizationResults, i[0])["sequences"]
                                               [((i[1], i[0]), "flow")] * self.__envParam[i[1]][1] *
                                               ('electricityBus' in i[0]) + solph.views.node(self.__optimizationResults, i[0])
                                               ["sequences"][((i[1], i[0]), "flow")] * self.__envParam[i[1]][0] *
                                               ('electricityBus' not in i[0]) for i in n_techno))

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

    def printInvestedCapacities(self, building):
        print("************** Optimized Capacities for {} **************".format(building))
        investSH = solph.views.node(self.__optimizationResults, "spaceHeatingBus"+'__'+building)["scalars"][
            (("HP_SH"+'__'+building, "spaceHeatingBus"+'__'+building), "invest")]
        investDHW = solph.views.node(self.__optimizationResults, "dhwStorageBus"+'__'+building)["scalars"][
            (("HP_DHW"+'__'+building, "dhwStorageBus"+'__'+building), "invest")]
        print("{}kW :SH and {}kW :DHW HP.".format(investSH, investDHW))

        invest = solph.views.node(self.__optimizationResults, "spaceHeatingBus"+'__'+building)["scalars"][
            (("CHP"+'__'+building, "spaceHeatingBus"+'__'+building), "invest")] + solph.views.node(
            self.__optimizationResults, "electricityBus"+'__'+building)[
            "scalars"][(("CHP"+'__'+building, "electricityBus"+'__'+building), "invest")]
        print("{} kW CHP.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "electricityBus"+'__'+building)["scalars"][
            (("electricalStorage"+'__'+building, "electricityBus"+'__'+building), "invest")]
        print("{} kW Electrical Storage.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "domesticHotWaterBus"+'__'+building)["scalars"][
            (("dhwStorage"+'__'+building, "domesticHotWaterBus"+'__'+building), "invest")]
        print("{} kW DHW Storage Tank.".format(invest))
        invest = solph.views.node(self.__optimizationResults, "spaceHeatingBus"+'__'+building)["scalars"][
            (("shStorage"+'__'+building, "spaceHeatingBus"+'__'+building), "invest")
        ]
        print("{} kW SH Storage Tank.".format(invest))
        print("")

    def printCosts(self):
        print("Investment Costs for the system: {} CHF".format(sum(self.__capex["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("Operation Costs for the system: {} CHF".format(sum(self.__opex["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("Feed In Costs for the system: {} CHF".format(sum(self.__feedIn["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("Total Costs for the system: {} CHF".format(sum(self.__capex["Building"+str(b+1)] + self.__opex["Building"+str(b+1)] - self.__feedIn["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("")

    def printEnvImpacts(self):
        print("Environmental impact from input resources for the system: {} kg CO2 eq".format(sum(self.__envImpactInputs["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("Environmental impact from energy conversion technologies for the system: {} kg CO2 eq".format(sum(self.__envImpactTechnologies["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("")

    def exportToExcel(self, file_name):
        with pd.ExcelWriter(file_name) as writer:
            list = []
            for i in self.nodes:
                if str(type(i)).replace("<class 'oemof.solph.", "").replace("'>", "") == "network.bus.Bus":
                    list.append(i.label)
            for i in list:
                a = pd.DataFrame.from_dict(solph.views.node(self.__optimizationResults, i)["sequences"])
                a.to_excel(writer, sheet_name=i)
            for b in self.__buildings:
                costs = {"Operation": self.__opex[b.getBuildingLabel()],
                         "Investment": self.__capex[b.getBuildingLabel()],
                         "Feed-in": self.__feedIn[b.getBuildingLabel()],
                         }
                costs_n = pd.DataFrame.from_dict(costs, orient='index')
                costs_n.to_excel(writer, sheet_name="costs__"+b.getBuildingLabel())

                env_impact = {}
                for i in range(len(self.__inputs)):
                    if b.getBuildingLabel() in self.__inputs[i][0]:
                        A = self.__inputs[i][0]
                        B = self.__inputs[i][1]
                        env_impact[A] = sum(
                            solph.views.node(self.__optimizationResults, B)["sequences"][(A, B), "flow"]) * self.__envParam[A]
                for i in range(len(self.__technologies)):
                    if b.getBuildingLabel() in self.__technologies[i][0]:
                        A = self.__technologies[i][0]
                        B = self.__technologies[i][1]
                        env_impact[B] = solph.views.node(self.__optimizationResults, A)["scalars"][
                                           ((B, A), "invest")] * self.__envParam[B][2] + \
                                       sum(solph.views.node(self.__optimizationResults, A)["sequences"]
                                           [((B, A), "flow")] * self.__envParam[B][1] *
                                           ('electricityBus' in A) +
                                           solph.views.node(self.__optimizationResults, A)
                                           ["sequences"][((B, A), "flow")] * self.__envParam[B][0] *
                                           ('electricityBus' not in A))

                env_n = pd.DataFrame.from_dict(env_impact, orient='index')
                env_n.to_excel(writer, sheet_name="env_impacts__"+b.getBuildingLabel())
