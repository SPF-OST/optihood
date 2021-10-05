import numpy as np
import pandas as pd
import oemof.solph as solph
from oemof.tools import logger
from oemof.tools import economics
import logging
import os
import pprint as pp
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from converters import HeatPumpLinear, CHP
from storages import ElectricalStorage, ThermalStorage
from constraints import *
from groups_indiv import Building

intRate = 0.05

class EnergyNetwork(solph.EnergySystem):
    def __init__(self, timestamp, tSH, tDHW):
        self.__temperatureSH = tSH
        self.__temperatureDHW = tDHW
        self.__nodesList = []
        self.__inputs = {}  # dictionary of list of inputs indexed by the building label
        self.__technologies = {}  # dictionary of list of technologies indexed by the building label
        self.__capacitiesTransformersBuilding = {}  # dictionary of dictionary of optimized capacities of transformers indexed by the building label
        self.__capacitiesStoragesBuilding = {}  # dictionary of dictionary of optimized capacities of storages indexed by the building label
        self.__costParam = {}
        self.__envParam = {}
        self.__capex = {}
        self.__opex = {}
        self.__feedIn = {}
        self.__envImpactInputs = {}  # dictionary of dictionary of environmental impact of different inputs indexed by the building label
        self.__envImpactTechnologies = {}  # dictionary of dictionary of environmental impact of different technologies indexed by the building label
        self.__busDict = {}
        logger.define_logging(logpath=os.getcwd())
        logging.info("Initializing the energy network")
        super(EnergyNetwork, self).__init__(timeindex=timestamp)

    def setFromExcel(self, filePath, opt):
        # does Excel file exist?
        if not filePath or not os.path.isfile(filePath):
            logging.error("Excel data file {} not found.".format(filePath))
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        data = pd.ExcelFile(filePath)
        nodesData = {
            "buses": data.parse("buses"),
            "grid_connection": data.parse("grid_connection"),
            "commodity_sources": data.parse("commodity_sources"),
            "electricity_impact": data.parse("electricity_impact"),
            "transformers": data.parse("transformers"),
            "demand": data.parse("demand"),
            "storages": data.parse("storages"),
            "timeseries": data.parse("time_series"),
            "stratified_storage": data.parse("stratified_storage"),
            "links": data.parse("links")
        }
        # update stratified_storage index
        nodesData["stratified_storage"].set_index("label", inplace=True)
        # set datetime index
        nodesData["electricity_impact"].set_index("timestamp", inplace=True)
        nodesData["electricity_impact"].index = pd.to_datetime(nodesData["electricity_impact"].index)
        nodesData["timeseries"].set_index("timestamp", inplace=True)
        nodesData["timeseries"].index = pd.to_datetime(nodesData["timeseries"].index)

        logging.info("Data from Excel file {} imported.".format(filePath))

        self._convertNodes(nodesData, opt)
        logging.info("Nodes from Excel file {} successfully converted".format(filePath))
        self.add(*self.__nodesList)
        logging.info("Nodes successfully added to the energy network")

    def _convertNodes(self, data, opt):
        if not data:
            logging.error("Nodes data is missing.")
        self.__temperatureAmb = np.array(data["timeseries"]["temperature.actual"])
        self._addBuildings(data, opt)
        self._addLinks(data["links"])

    def _addBuildings(self, data, opt):
        numberOfBuildings = max(data["buses"]["building"])
        self.__buildings = [Building('Building'+str(i+1)) for i in range(numberOfBuildings)]
        for b in self.__buildings:
            buildingLabel = b.getBuildingLabel()
            i = int(buildingLabel[8:])
            b.addBus(data["buses"][data["buses"]["building"] == i], opt)
            b.addGridSeparation(data["grid_connection"][data["grid_connection"]["building"] == i])
            b.addSource(data["commodity_sources"][data["commodity_sources"]["building"] == i], data["electricity_impact"], opt)
            b.addSink(data["demand"][data["demand"]["building"] == i], data["timeseries"].filter(regex=str(i)))
            b.addTransformer(data["transformers"][data["transformers"]["building"] == i], self.__temperatureDHW,
                             self.__temperatureSH, self.__temperatureAmb, opt)
            b.addStorage(data["storages"][data["storages"]["building"] == i], data["stratified_storage"], opt)
            self.__nodesList.extend(b.getNodesList())
            self.__inputs[buildingLabel] = b.getInputs()
            self.__technologies[buildingLabel] = b.getTechnologies()
            self.__costParam.update(b.getCostParam())
            self.__envParam.update(b.getEnvParam())
            self.__busDict.update(b.getBusDict())
            self.__capacitiesTransformersBuilding[buildingLabel] = {}
            self.__capacitiesStoragesBuilding[buildingLabel] = {}
            self.__envImpactInputs[buildingLabel] = {}
            self.__envImpactTechnologies[buildingLabel] = {}

    def _addLinks(self, data): # connects buses A and B (denotes a bidirectional link)
        for i, l in data.iterrows():
            if l["active"]:
                busA = self.__busDict["electricityBus"+'__Building'+str(l["buildingA"])]
                busB = self.__busDict["electricityBus"+'__Building'+str(l["buildingB"])]
                self.__nodesList.append(solph.custom.Link(
                    label=l["label"]+str(l["buildingA"])+'_'+str(l["buildingB"]),
                    inputs={busA: solph.Flow(), busB: solph.Flow()},
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

    def optimize(self, solver, envImpactlimit):
        logging.info("Initiating optimization using {} solver".format(solver))
        optimizationModel = solph.Model(self)
        # add constraint to limit the environmental impacts
        optimizationModel, flows, transformerFlowCapacityDict, storageCapacityDict = environmentalImpactlimit(optimizationModel, keyword1="env_per_flow", keyword2="env_per_capa", limit=envImpactlimit)
        optimizationModel.solve(solver=solver)
        # obtain the value of the environmental impact (subject to the limit constraint)
        # the optimization imposes an integral limit constraint on the environmental impacts
        # total environmental impacts <= envImpactlimit
        envImpact = optimizationModel.totalEnvironmentalImpact()

        self.__optimizationResults = solph.processing.results(optimizationModel)
        self.__metaResults = solph.processing.meta_results(optimizationModel)
        logging.info("Optimization successful and results collected")

        # calculate capacities invested for transformers and storages (for the entire energy network and per building)
        capacitiesTransformersNetwork, capacitiesStoragesNetwork = self._calculateInvestedCapacities(optimizationModel, transformerFlowCapacityDict, storageCapacityDict)

        # calculate results (CAPEX, OPEX, FeedIn Costs, environmental impacts etc...) for each building
        self._calculateResultsPerBuilding()

        return envImpact, capacitiesTransformersNetwork, capacitiesStoragesNetwork

    def _calculateInvestedCapacities(self, optimizationModel, transformerFlowCapacityDict, storageCapacityDict):
        capacitiesInvestedTransformers = {}
        capacitiesInvestedStorages = {}
        storageList = []

        for inflow, outflow in transformerFlowCapacityDict:
            index = (str(inflow), str(outflow))
            capacitiesInvestedTransformers[index] = optimizationModel.InvestmentFlow.invest[inflow, outflow].value
            buildingLabel = str(inflow).split("__")[1]
            self.__capacitiesTransformersBuilding[buildingLabel].update({index: capacitiesInvestedTransformers[index]})

        for x in storageCapacityDict:
            index = str(x)
            buildingLabel = index.split("__")[1]
            if x in storageList:  # useful when we want to implement two or more storage units of the same type
                capacitiesInvestedStorages[index] = capacitiesInvestedStorages[index] + \
                                                    optimizationModel.GenericInvestmentStorageBlock.invest[x].value
                self.__capacitiesStoragesBuilding[buildingLabel].update({index: capacitiesInvestedStorages[index]})
            else:
                capacitiesInvestedStorages[str(x)] = optimizationModel.GenericInvestmentStorageBlock.invest[x].value
                self.__capacitiesStoragesBuilding[buildingLabel].update({index: capacitiesInvestedStorages[index]})
            storageList.append(x)

        return capacitiesInvestedTransformers, capacitiesInvestedStorages

    def _calculateResultsPerBuilding(self):
        for b in self.__buildings:
            buildingLabel = b.getBuildingLabel()
            capacityTransformers = self.__capacitiesTransformersBuilding[buildingLabel]
            capacityStorages = self.__capacitiesStoragesBuilding[buildingLabel]
            technologies = self.__technologies[buildingLabel]
            inputs = self.__inputs[buildingLabel]

            # CAPital investment EXpenditure
            self.__capex[buildingLabel] = sum((self.__costParam[i][1] * (capacityTransformers[(i, o)] > 1))             # base investment cost if the technology is implemented
                                              + (capacityTransformers[(i, o)] * self.__costParam[i][0])                 # investment cost per unit capacity
                                              for i, o in capacityTransformers) + \
                                          sum((self.__costParam[x][1] * (capacityStorages[x] > 1))                      # base investment cost if the technology is implemented
                                              + (capacityStorages[x] * self.__costParam[x][0])                          # investment cost per unit capacity
                                              for x in capacityStorages)

            electricitySourceLabel = "electricityResource" + '__' + buildingLabel
            gridBusLabel = "gridBus" + '__' + buildingLabel
            electricityBusLabel = "electricityBus" + '__' + buildingLabel
            excessElectricityBusLabel = "excesselectricityBus" + '__' + buildingLabel

            # OPeration EXpenditure
            self.__opex[buildingLabel] = sum(sum(solph.views.node(self.__optimizationResults, i[1])["sequences"][(i[0], i[1]), "flow"])
                                                    * self.__costParam[i[0]] for i in inputs + [[electricitySourceLabel, gridBusLabel]])

            # Feed-in electricity cost (value will be in negative to signify monetary gain...)
            self.__feedIn[buildingLabel] = sum(solph.views.node(self.__optimizationResults, electricityBusLabel)
                                               ["sequences"][(electricityBusLabel, excessElectricityBusLabel), "flow"])\
                                           * self.__costParam[excessElectricityBusLabel]

            envParamGridElectricity = self.__envParam[electricitySourceLabel].copy()
            envParamGridElectricity.reset_index(inplace=True, drop=True)
            gridElectricityFlow = solph.views.node(self.__optimizationResults, gridBusLabel)["sequences"][
                (electricitySourceLabel, gridBusLabel), "flow"]
            gridElectricityFlow.reset_index(inplace=True, drop=True)

            # Environmental impact due to inputs (natural gas, electricity, etc...)
            self.__envImpactInputs[buildingLabel].update({i[0]: sum(solph.views.node(self.__optimizationResults, i[1])["sequences"][(i[0], i[1]), "flow"] * self.__envParam[i[0]]) for i in inputs})
            self.__envImpactInputs[buildingLabel].update({electricitySourceLabel: (envParamGridElectricity * gridElectricityFlow).sum()})  # impact of grid electricity is added separately based on LCA data

            # Environmental impact due to technologies (converters, storages)
            # calculated by adding both environmental impact per capacity and per flow (electrical flow or heat flow)
            self.__envImpactTechnologies[buildingLabel].update({i: capacityTransformers[(i, o)] * self.__envParam[i][2] +
                                                                   sum(sum(solph.views.node(self.__optimizationResults,
                                                                                            t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                           self.__envParam[t[1]][1] * ('electricityBus' in t[0]) + \
                                                                           solph.views.node(self.__optimizationResults,
                                                                                            t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                           self.__envParam[t[1]][0] * ('electricityBus' not in t[0]))
                                                                       for t in technologies if t[1] == i)
                                                                for i, o in capacityTransformers})
            self.__envImpactTechnologies[buildingLabel].update({x: capacityStorages[x] * self.__envParam[x][2] +
                                                                   sum(sum(
                                                                       solph.views.node(self.__optimizationResults,
                                                                                        t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                       self.__envParam[t[1]][1] * ('electricityBus' in t[0]) + \
                                                                       solph.views.node(self.__optimizationResults,
                                                                                        t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                       self.__envParam[t[1]][0] * ('electricityBus' not in t[0]))
                                                                       for t in technologies if t[1] == x)
                                                                for x in capacityStorages})

    def printMetaresults(self):
        print("Meta Results:")
        pp.pprint(self.__metaResults)
        print("")
        return self.__metaResults

    def printStateofCharge(self, type, building):
        storage = self.groups[type+'__'+building]
        print(f"""********* State of Charge ({type},{building}) *********""")
        print(
            self.__optimizationResults[(storage, None)]["sequences"]
        )
        print("")

    def printInvestedCapacities(self, capacitiesInvestedTransformers, capacitiesInvestedStorages):
        for b in range(len(self.__buildings)):
            buildingLabel = "Building" + str(b + 1)
            print("************** Optimized Capacities for {} **************".format(buildingLabel))
            investSH = capacitiesInvestedTransformers[("HP_SH__" + buildingLabel, "spaceHeatingBus__" + buildingLabel)]
            investDHW = capacitiesInvestedTransformers[("HP_DHW__" + buildingLabel, "dhwStorageBus__" + buildingLabel)]
            print("Invested in {} kW :SH and {} kW :DHW HP.".format(investSH, investDHW))

            investSH = capacitiesInvestedTransformers[("CHP_SH__" + buildingLabel, "electricityBus__" + buildingLabel)] + \
                       capacitiesInvestedTransformers[("CHP_SH__" + buildingLabel, "spaceHeatingBus__" + buildingLabel)]
            investDHW = capacitiesInvestedTransformers[("CHP_DHW__" + buildingLabel, "electricityBus__" + buildingLabel)] + \
                        capacitiesInvestedTransformers[("CHP_DHW__" + buildingLabel, "dhwStorageBus__" + buildingLabel)]
            print("Invested in {} kW :SH and {} kW :DHW CHP.".format(investSH, investDHW))

            invest = capacitiesInvestedStorages["electricalStorage__" + buildingLabel]
            print("Invested in {} kWh Electrical Storage.".format(invest))
            invest = capacitiesInvestedStorages["dhwStorage__" + buildingLabel]
            print("Invested in {} kWh DHW Storage Tank.".format(invest))
            invest = capacitiesInvestedStorages["shStorage__" + buildingLabel]
            print("Invested in {} kWh SH Storage Tank.".format(invest))
            print("")

    def printCosts(self):
        print("Investment Costs for the system: {} CHF".format(sum(self.__capex["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("Operation Costs for the system: {} CHF".format(sum(self.__opex["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("Feed In Costs for the system: {} CHF".format(sum(self.__feedIn["Building"+str(b+1)] for b in range(len(self.__buildings)))))
        print("Total Costs for the system: {} CHF".format(sum(self.__capex["Building"+str(b+1)] + self.__opex["Building"+str(b+1)] + self.__feedIn["Building"+str(b+1)] for b in range(len(self.__buildings)))))

    def printEnvImpacts(self):
        envImpactInputsNetwork = sum(sum(self.__envImpactInputs["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        envImpactTechnologiesNetwork = sum(sum(self.__envImpactTechnologies["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        print("Environmental impact from input resources for the system: {} kg CO2 eq".format(envImpactInputsNetwork))
        print("Environmental impact from energy conversion technologies for the system: {} kg CO2 eq".format(envImpactTechnologiesNetwork))
        print("Total: {} kg CO2 eq".format(envImpactInputsNetwork + envImpactTechnologiesNetwork))

    def exportToExcel(self, file_name):
        with pd.ExcelWriter(file_name) as writer:
            busLabelList = []
            for i in self.nodes:
                if str(type(i)).replace("<class 'oemof.solph.", "").replace("'>", "") == "network.bus.Bus":
                    busLabelList.append(i.label)
            # writing results of each bus into excel
            for i in busLabelList:
                if "domesticHotWaterBus" in i:  # special case for DHW bus (output from transformers --> dhwStorageBus --> DHW storage --> domesticHotWaterBus --> DHW Demand)
                    dhwStorageBusLabel = "dhwStorageBus__" + i.split("__")[1]
                    resultDHW = pd.DataFrame.from_dict(
                        solph.views.node(self.__optimizationResults, i)["sequences"])  # result sequences of DHW bus
                    resultDHWStorage = pd.DataFrame.from_dict(
                        solph.views.node(self.__optimizationResults, dhwStorageBusLabel)[
                            "sequences"])  # result sequences of DHW storage bus
                    result = pd.concat([resultDHW, resultDHWStorage], axis=1, sort=True)
                elif "dhwStorageBus" not in i:  # for all the other buses except DHW storage bus (as it is already considered with DHW bus)
                    result = pd.DataFrame.from_dict(solph.views.node(self.__optimizationResults, i)["sequences"])
                result.to_excel(writer, sheet_name=i)

            # writing the costs and environmental impacts (of different components...) for each building
            for b in self.__buildings:
                buildingLabel = b.getBuildingLabel()
                costs = {"Operation": self.__opex[buildingLabel],
                         "Investment": self.__capex[buildingLabel],
                         "Feed-in": self.__feedIn[buildingLabel],
                         }
                costsBuilding = pd.DataFrame.from_dict(costs, orient='index')
                costsBuilding.to_excel(writer, sheet_name="costs__" + buildingLabel)

                envImpact = self.__envImpactInputs[buildingLabel]
                envImpact.update(self.__envImpactTechnologies[buildingLabel])

                envImpactBuilding = pd.DataFrame.from_dict(envImpact, orient='index')
                envImpactBuilding.to_excel(writer, sheet_name="env_impacts__" + buildingLabel)
