import numpy as np
import pandas as pd
import oemof.solph as solph
from oemof.tools import logger
import logging
import os
import pprint as pp
from datetime import datetime
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from constraints import *
from buildings import Building


class EnergyNetworkClass(solph.EnergySystem):
    def __init__(self, timestamp):
        self._nodesList = []
        self._storageContentSH = {}
        self.__inputs = {}                          # dictionary of list of inputs indexed by the building label
        self.__technologies = {}                    # dictionary of list of technologies indexed by the building label
        self.__capacitiesTransformersBuilding = {}  # dictionary of dictionary of optimized capacities of transformers indexed by the building label
        self.__capacitiesStoragesBuilding = {}      # dictionary of dictionary of optimized capacities of storages indexed by the building label
        self.__costParam = {}
        self.__envParam = {}
        self.__capex = {}
        self.__opex = {}
        self.__feedIn = {}
        self.__envImpactInputs = {}                 # dictionary of dictionary of environmental impact of different inputs indexed by the building label
        self.__envImpactTechnologies = {}           # dictionary of dictionary of environmental impact of different technologies indexed by the building label
        self._busDict = {}
        logger.define_logging(logpath=os.getcwd())
        logging.info("Initializing the energy network")
        super(EnergyNetworkClass, self).__init__(timeindex=timestamp)

    def setFromExcel(self, filePath, numberOfBuildings, clusterSize, opt):
        # does Excel file exist?
        if not filePath or not os.path.isfile(filePath):
            logging.error("Excel data file {} not found.".format(filePath))
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        data = pd.ExcelFile(filePath)
        nodesData = self.createNodesData(data, filePath, numberOfBuildings)

        demandProfiles = {}
        if clusterSize:
            for i in range(1, numberOfBuildings + 1):
                demandProfiles[i] = pd.concat(
                    [nodesData["demandProfiles"][i].loc[d] for d in clusterSize.keys()])
            electricityImpact = pd.concat(
                [nodesData["electricity_impact"].loc[d] for d in clusterSize.keys()])
            weatherData = pd.concat([nodesData['weather_data'][
                                         nodesData['weather_data']['time.mm'] == int(d.split('-')[1])][
                                         nodesData['weather_data']['time.dd'] == int(d.split('-')[2])][
                                         ['gls', 'str.diffus', 'tre200h0']] for d in clusterSize.keys()])

            nodesData["demandProfiles"] = demandProfiles
            nodesData["electricity_impact"] = electricityImpact
            nodesData["weather_data"] = weatherData

        self._convertNodes(nodesData, opt)
        logging.info("Nodes from Excel file {} successfully converted".format(filePath))
        self.add(*self._nodesList)
        logging.info("Nodes successfully added to the energy network")

    def createNodesData(self, data, filePath, numBuildings):
        self.__noOfBuildings = numBuildings
        nodesData = {
            "buses": data.parse("buses"),
            "grid_connection": data.parse("grid_connection"),
            "commodity_sources": data.parse("commodity_sources"),
            "solar": data.parse("solar"),
            "transformers": data.parse("transformers"),
            "demand": data.parse("demand"),
            "storages": data.parse("storages"),
            "stratified_storage": data.parse("stratified_storage"),
            "csv_paths": data.parse("csv_data")
        }
        # update stratified_storage index
        nodesData["stratified_storage"].set_index("label", inplace=True)

        # extract input data from CSVs
        electricityImpactPath = nodesData["csv_paths"].loc[nodesData["csv_paths"]["name"] == "electricity_impact", "path"].iloc[0]
        demandProfilesPath = nodesData["csv_paths"].loc[nodesData["csv_paths"]["name"] == "demand_profiles", "path"].iloc[0]
        weatherDataPath = nodesData["csv_paths"].loc[nodesData["csv_paths"]["name"] == "weather_data", "path"].iloc[0]

        demandProfiles = {}  # dictionary of dataframes for each building's demand profiles

        if (not os.listdir(demandProfilesPath)) or (not os.path.exists(demandProfilesPath)):
            logging.error("Error in the demand profiles path: The folder is either empty or does not exist")
        else:
            i = 0
            for filename in os.listdir(demandProfilesPath): #this path should contain csv file(s) (one for each building's profiles)
                i += 1      # Building number
                if i > numBuildings:
                    break
                demandProfiles.update({i: pd.read_csv(os.path.join(demandProfilesPath, filename), delimiter=";")})

            nodesData["demandProfiles"] = demandProfiles
            # set datetime index
            for i in range(numBuildings):
                nodesData["demandProfiles"][i + 1].set_index("timestamp", inplace=True)
                nodesData["demandProfiles"][i + 1].index = pd.to_datetime(nodesData["demandProfiles"][i + 1].index)

        if not os.path.exists(electricityImpactPath):
            logging.error("Error in electricity impact file path")
        else:
            nodesData["electricity_impact"] = pd.read_csv(electricityImpactPath, delimiter=";")
            # set datetime index
            nodesData["electricity_impact"].set_index("timestamp", inplace=True)
            nodesData["electricity_impact"].index = pd.to_datetime(nodesData["electricity_impact"].index)

        if not os.path.exists(weatherDataPath):
            logging.error("Error in weather data file path")
        else:
            nodesData["weather_data"] = pd.read_csv(weatherDataPath, delimiter=";")
            #add a timestamp column to the dataframe
            for index, row in nodesData['weather_data'].iterrows():
                time = f"{int(row['time.yy'])}.{int(row['time.mm']):02}.{int(row['time.dd']):02} {int(row['time.hh']):02}:00:00"
                nodesData['weather_data'].at[index, 'timestamp'] = datetime.strptime(time, "%Y.%m.%d  %H:%M:%S")
                #set datetime index
            nodesData["weather_data"].set_index("timestamp", inplace=True)
            nodesData["weather_data"].index = pd.to_datetime(nodesData["weather_data"].index)

        logging.info("Data from Excel file {} imported.".format(filePath))
        return nodesData

    def _convertNodes(self, data, opt):
        if not data:
            logging.error("Nodes data is missing.")
        ################## !!!
        self.__temperatureAmb = np.array(data["weather_data"]["tre200h0"])
        self.__temperatureSH = data["stratified_storage"].loc["shStorage","temp_h"]
        self.__temperatureDHW = data["stratified_storage"].loc["dhwStorage","temp_h"]
        # Transformers conversion factors input power - output power
        self.__chpEff = float(data["transformers"][data["transformers"]["label"] == "CHP"]["efficiency"].iloc[0].split(",")[1])
        self.__hpEff = data["transformers"][data["transformers"]["label"]=="HP"]["efficiency"].iloc[0]
        self.__gbEff = float(data["transformers"][data["transformers"]["label"]=="GasBoiler"]["efficiency"].iloc[0].split(",")[0])
        # Storage conversion L - kWh to display the L value
        self.__Lsh = 4.186*(self.__temperatureSH - data["stratified_storage"].loc["shStorage","temp_c"])/3600
        self.__Ldhw = 4.186 * (self.__temperatureDHW - data["stratified_storage"].loc["dhwStorage", "temp_c"]) / 3600
        self._addBuildings(data, opt)

    def _addBuildings(self, data, opt):
        numberOfBuildings = max(data["buses"]["building"])
        self.__buildings = [Building('Building' + str(i + 1)) for i in range(numberOfBuildings)]
        for b in self.__buildings:
            buildingLabel = b.getBuildingLabel()
            i = int(buildingLabel[8:])
            b.addBus(data["buses"][data["buses"]["building"] == i], opt)
            b.addGridSeparation(data["grid_connection"][data["grid_connection"]["building"] == i])
            b.addSource(data["commodity_sources"][data["commodity_sources"]["building"] == i], data["electricity_impact"], opt)
            b.addSink(data["demand"][data["demand"]["building"] == i], data["demandProfiles"][i])
            b.addTransformer(data["transformers"][data["transformers"]["building"] == i], self.__temperatureDHW,
                             self.__temperatureSH, self.__temperatureAmb, opt)
            b.addStorage(data["storages"][data["storages"]["building"] == i], data["stratified_storage"], opt)
            b.addSolar(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"] == "solarCollector")], data["weather_data"], opt)
            b.addPV(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"] == "pv")], data["weather_data"], opt)
            self._nodesList.extend(b.getNodesList())
            self.__inputs[buildingLabel] = b.getInputs()
            self.__technologies[buildingLabel] = b.getTechnologies()
            self.__costParam.update(b.getCostParam())
            self.__envParam.update(b.getEnvParam())
            self._busDict.update(b.getBusDict())
            self.__capacitiesTransformersBuilding[buildingLabel] = {}
            self.__capacitiesStoragesBuilding[buildingLabel] = {}
            self.__envImpactInputs[buildingLabel] = {}
            self.__envImpactTechnologies[buildingLabel] = {}

    def printNodes(self):
        print("*********************************************************")
        print("The following objects have been created from excel sheet:")
        for n in self.nodes:
            oobj = str(type(n)).replace("<class 'oemof.solph.", "").replace("'>", "")
            print(oobj + ":", n.label)
        print("*********************************************************")

    def optimize(self, solver, envImpactlimit, clusterSize, options=None):
        if options is None:
            options = {"gurobi": {"MIPGap": 0.01}}
        if solver == "gurobi":
            logging.info("Initiating optimization using {} solver".format(solver))
        optimizationModel = solph.Model(self)
        # add constraint to limit the environmental impacts
        optimizationModel, flows, transformerFlowCapacityDict, storageCapacityDict = environmentalImpactlimit(optimizationModel, keyword1="env_per_flow", keyword2="env_per_capa", limit=envImpactlimit)
        optimizationModel = dailySHStorageConstraint(optimizationModel)
        optimizationModel.solve(solver=solver, cmdline_options=options[solver])
        # obtain the value of the environmental impact (subject to the limit constraint)
        # the optimization imposes an integral limit constraint on the environmental impacts
        # total environmental impacts <= envImpactlimit
        envImpact = optimizationModel.totalEnvironmentalImpact()

        self.__optimizationResults = solph.processing.results(optimizationModel)
        self.__metaResults = solph.processing.meta_results(optimizationModel)
        logging.info("Optimization successful and results collected")

        # calculate capacities invested for transformers and storages (for the entire energy network and per building)
        capacitiesTransformersNetwork, capacitiesStoragesNetwork = self._calculateInvestedCapacities(optimizationModel, transformerFlowCapacityDict, storageCapacityDict)

        if clusterSize:
            self._postprocessingClusters(clusterSize)

        # calculate results (CAPEX, OPEX, FeedIn Costs, environmental impacts etc...) for each building
        self._calculateResultsPerBuilding()

        return envImpact, capacitiesTransformersNetwork, capacitiesStoragesNetwork

    def _calculateInvestedCapacities(self, optimizationModel, transformerFlowCapacityDict, storageCapacityDict):
        capacitiesInvestedTransformers = {}
        capacitiesInvestedStorages = {}
        storageList = []

        # Transformers capacities
        for inflow, outflow in transformerFlowCapacityDict:
            index = (str(inflow), str(outflow))
            capacitiesInvestedTransformers[index] = optimizationModel.InvestmentFlow.invest[inflow, outflow].value
        # Conversion into output capacity
        capacitiesInvestedTransformers = self._compensateInputCapacities(capacitiesInvestedTransformers)
        # Update capacities
        for inflow, outflow in transformerFlowCapacityDict:
            index = (str(inflow), str(outflow))
            buildingLabel = str(inflow).split("__")[1]
            self.__capacitiesTransformersBuilding[buildingLabel].update({index: capacitiesInvestedTransformers[index]})

        # Storages capacities
        for x in storageCapacityDict:
            index = str(x)
            if x in storageList:  # useful when we want to implement two or more storage units of the same type
                capacitiesInvestedStorages[index] = capacitiesInvestedStorages[index] + \
                                                    optimizationModel.GenericInvestmentStorageBlock.invest[x].value
            else:
                capacitiesInvestedStorages[str(x)] = optimizationModel.GenericInvestmentStorageBlock.invest[x].value
        # Convert kWh into L
        capacitiesInvestedStorages = self._compensateStorageCapacities(capacitiesInvestedStorages)
        # Update capacities
        for x in storageCapacityDict:
            index = str(x)
            buildingLabel = index.split("__")[1]
            if x in storageList:  # useful when we want to implement two or more storage units of the same type
                self.__capacitiesStoragesBuilding[buildingLabel].update({index: capacitiesInvestedStorages[index]})
            else:
                self.__capacitiesStoragesBuilding[buildingLabel].update({index: capacitiesInvestedStorages[index]})
            storageList.append(x)

        return capacitiesInvestedTransformers, capacitiesInvestedStorages

    def _compensateInputCapacities(self, capacitiesTransformers):
        # Input capacity -> output capacity
        for first, second in capacitiesTransformers.keys():
            if "CHP" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if "shSource" in t.label:
                                capacitiesTransformers[(first,second)]= capacitiesTransformers[(first,second)]*self.__chpEff
            elif "HP" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if "shSource" in t.label:
                                capacitiesTransformers[(first,second)] = capacitiesTransformers[(first,second)]*self.__hpEff
            elif "GasBoiler" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if "shSource" in t.label:
                                capacitiesTransformers[(first, second)] = capacitiesTransformers[(first, second)]*self.__gbEff

        return capacitiesTransformers

    def _compensateStorageCapacities(self, capacitiesStorages):
        # kWh -> L
        for storage in capacitiesStorages.keys():
            if "sh" in storage:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__Lsh
            elif "dhw" in storage:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__Ldhw
        return capacitiesStorages

    def _postprocessingClusters(self, clusterSize):
        flows = [x for x in self.__optimizationResults.keys() if x[1] is not None]
        mfactor = np.repeat(list(clusterSize.values()), 24)
        for flow in flows:
            self.__optimizationResults[flow]['sequences'] = self.__optimizationResults[flow]['sequences'].mul(mfactor, axis=0)


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
                                               ["sequences"][(electricityBusLabel, excessElectricityBusLabel), "flow"]) * self.__costParam[excessElectricityBusLabel]

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

    def calcStateofCharge(self, type, building):
        storage = self.groups[type + '__' + building]
        #print(f"""********* State of Charge ({type},{building}) *********""")
        #print(
        #    self.__optimizationResults[(storage, None)]["sequences"]
        #)
        self._storageContentSH[building] = self.__optimizationResults[(storage, None)]["sequences"]
        print("")

    def printInvestedCapacities(self, capacitiesInvestedTransformers, capacitiesInvestedStorages):
        for b in range(len(self.__buildings)):
            buildingLabel = "Building" + str(b + 1)
            print("************** Optimized Capacities for {} **************".format(buildingLabel))
            investSH = capacitiesInvestedTransformers[("electricityInBus__" + buildingLabel, "HP__" + buildingLabel)]
            print("Invested in {} kW HP.".format(investSH))
            investSH = capacitiesInvestedTransformers[("naturalGasBus__" + buildingLabel, "CHP__" + buildingLabel)]
            print("Invested in {} kW CHP.".format(investSH))# + investEL))
            invest = capacitiesInvestedTransformers[("heat_solarCollector__" + buildingLabel, "solarConnectBus__" + buildingLabel)]
            print("Invested in {} m² SolarCollector.".format(invest))
            investSH = capacitiesInvestedTransformers[("naturalGasBus__" + buildingLabel, "GasBoiler__" + buildingLabel)]
            print("Invested in {} kW  GasBoiler.".format(investSH))
            invest = capacitiesInvestedTransformers[("pv__" + buildingLabel, "electricityProdBus__" + buildingLabel)]
            print("Invested in {} kW  PV.".format(invest))
            invest = capacitiesInvestedStorages["electricalStorage__" + buildingLabel]
            print("Invested in {} kWh Electrical Storage.".format(invest))
            invest = capacitiesInvestedStorages["dhwStorage__" + buildingLabel]
            print("Invested in {} L DHW Storage Tank.".format(invest))
            invest = capacitiesInvestedStorages["shStorage__" + buildingLabel]
            print("Invested in {} L SH Storage Tank.".format(invest))
            print("")

    def printCosts(self):
        print("Investment Costs for the system: {} CHF".format(sum(self.__capex["Building" + str(b + 1)] for b in range(len(self.__buildings)))))
        print("Operation Costs for the system: {} CHF".format(sum(self.__opex["Building" + str(b + 1)] for b in range(len(self.__buildings)))))
        print("Feed In Costs for the system: {} CHF".format(sum(self.__feedIn["Building" + str(b + 1)] for b in range(len(self.__buildings)))))
        print("Total Costs for the system: {} CHF".format(sum(self.__capex["Building" + str(b + 1)] + self.__opex["Building" + str(b + 1)] + self.__feedIn["Building" + str(b + 1)] for b in range(len(self.__buildings)))))

    def printEnvImpacts(self):
        envImpactInputsNetwork = sum(sum(self.__envImpactInputs["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        envImpactTechnologiesNetwork = sum(sum(self.__envImpactTechnologies["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        print("Environmental impact from input resources for the system: {} kg CO2 eq".format(envImpactInputsNetwork))
        print("Environmental impact from energy conversion technologies for the system: {} kg CO2 eq".format(envImpactTechnologiesNetwork))
        print("Total: {} kg CO2 eq".format(envImpactInputsNetwork + envImpactTechnologiesNetwork))

    def getTotalCosts(self):
        return sum(self.__capex["Building" + str(b + 1)] + self.__opex["Building" + str(b + 1)] + self.__feedIn[
                "Building" + str(b + 1)] for b in range(len(self.__buildings)))

    def exportToExcel(self, file_name):
        for i in range(1, self.__noOfBuildings+1):
            self.calcStateofCharge("shStorage", f"Building{i}")
        with pd.ExcelWriter(file_name) as writer:
            busLabelList = []
            for i in self.nodes:
                if str(type(i)).replace("<class 'oemof.solph.", "").replace("'>", "") == "network.bus.Bus":
                    busLabelList.append(i.label)
            # writing results of each bus into excel
            for i in busLabelList:
                if "domesticHotWaterBus" in i:  # special case for DHW bus (output from transformers --> dhwStorageBus --> DHW storage --> domesticHotWaterBus --> DHW Demand)
                    dhwStorageBusLabel = "dhwStorageBus__" + i.split("__")[1]
                    resultDHW = pd.DataFrame.from_dict(solph.views.node(self.__optimizationResults, i)["sequences"])  # result sequences of DHW bus
                    resultDHWStorage = pd.DataFrame.from_dict(solph.views.node(self.__optimizationResults, dhwStorageBusLabel)["sequences"])  # result sequences of DHW storage bus
                    result = pd.concat([resultDHW, resultDHWStorage], axis=1, sort=True)
                elif "dhwStorageBus" not in i:  # for all the other buses except DHW storage bus (as it is already considered with DHW bus)
                    result = pd.DataFrame.from_dict(solph.views.node(self.__optimizationResults, i)["sequences"])
                    if "shSourceBus" in i:
                        result = pd.concat([result, self._storageContentSH[i.split("__")[1]]], axis=1, sort=True)

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

                capacitiesStorages = self.__capacitiesStoragesBuilding[buildingLabel]
                capacitiesStorages.update(self.__capacitiesStoragesBuilding[buildingLabel])

                capacitiesStoragesBuilding = pd.DataFrame.from_dict(capacitiesStorages, orient='index')
                capacitiesStoragesBuilding.to_excel(writer, sheet_name="capStorages__" + buildingLabel)

                capacitiesTransformers = self.__capacitiesTransformersBuilding[buildingLabel]
                capacitiesTransformers.update(self.__capacitiesTransformersBuilding[buildingLabel])

                capacitiesTransformersBuilding = pd.DataFrame.from_dict(capacitiesTransformers, orient='index')
                capacitiesTransformersBuilding.to_excel(writer, sheet_name="capTransformers__" + buildingLabel)
            writer.save()

class EnergyNetworkIndiv(EnergyNetworkClass):
    pass

class EnergyNetworkGroup(EnergyNetworkClass):
    def setFromExcel(self, filePath, numberOfBuildings, clusterSize, opt):
        # does Excel file exist?
        if not filePath or not os.path.isfile(filePath):
            logging.error("Excel data file {} not found.".format(filePath))
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        data = pd.ExcelFile(filePath)

        nodesData = self.createNodesData(data, filePath, numberOfBuildings)

        demandProfiles = {}
        if clusterSize:
            for i in range(1, numberOfBuildings + 1):
                demandProfiles[i] = pd.concat(
                    [nodesData["demandProfiles"][i].loc[d] for d in clusterSize.keys()])
            electricityImpact = pd.concat(
                [nodesData["electricity_impact"].loc[d] for d in clusterSize.keys()])
            weatherData = pd.concat([nodesData['weather_data'][
                                         nodesData['weather_data']['time.mm'] == int(d.split('-')[1])][
                                         nodesData['weather_data']['time.dd'] == int(d.split('-')[2])][['gls', 'str.diffus', 'tre200h0']] for d in clusterSize.keys()])

            nodesData["demandProfiles"] = demandProfiles
            nodesData["electricity_impact"] = electricityImpact
            nodesData["weather_data"] = weatherData

        nodesData["links"]= data.parse("links")
        self._convertNodes(nodesData, opt)
        self._addLinks(nodesData["links"])
        logging.info("Nodes from Excel file {} successfully converted".format(filePath))
        self.add(*self._nodesList)
        logging.info("Nodes successfully added to the energy network")


    def _addLinks(self, data):  # connects buses A and B (denotes a bidirectional link)
        for i, l in data.iterrows():
            if "sh" in l["label"]:
                if l["active"]:
                    busA = self._busDict["spaceHeatingBus" + '__Building' + str(l["buildingA"])]
                    busB = self._busDict["spaceHeatingBus" + '__Building' + str(l["buildingB"])]
                    busAIn = self._busDict["shDemandBus" + '__Building' + str(l["buildingA"])]
                    busBIn = self._busDict["shDemandBus" + '__Building' + str(l["buildingB"])]
                    self._nodesList.append(solph.Transformer(
                        label=l["label"] + str(l["buildingA"]) + '_' + str(l["buildingB"]),
                        inputs={busA: solph.Flow()},
                        outputs={busBIn: solph.Flow(
                            investment=solph.Investment(
                                ep_costs=l["invest_cap"],
                                nonconvex=True,
                                maximum=5000,
                                offset=l["invest_base"],
                            ),
                        )},
                        conversion_factors={(busA, busBIn): l["efficiency from A to B"]}
                    ))
                    self._nodesList.append(solph.Transformer(
                        label=l["label"] + str(l["buildingB"]) + '_' + str(l["buildingA"]),
                        inputs={busB: solph.Flow()},
                        outputs={busAIn: solph.Flow(
                            investment=solph.Investment(
                                ep_costs=l["invest_cap"],
                                nonconvex=True,
                                maximum=5000,
                                offset=l["invest_base"],
                            ),
                        )},
                        conversion_factors={(busB, busAIn): l["efficiency from B to A"]}
                    ))
            else:
                if l["active"]:
                    busA = self._busDict["electricityBus" + '__Building' + str(l["buildingA"])]
                    busB = self._busDict["electricityBus" + '__Building' + str(l["buildingB"])]
                    busAIn = self._busDict["electricityInBus" + '__Building' + str(l["buildingA"])]
                    busBIn = self._busDict["electricityInBus" + '__Building' + str(l["buildingB"])]
                    self._nodesList.append(solph.Transformer(
                        label=l["label"] + str(l["buildingA"]) + '_' + str(l["buildingB"]),
                        inputs={busA: solph.Flow()},
                        outputs={busBIn: solph.Flow()},
                        conversion_factors={(busA, busBIn): l["efficiency from A to B"]}
                    ))
                    self._nodesList.append(solph.Transformer(
                        label=l["label"] + str(l["buildingB"]) + '_' + str(l["buildingA"]),
                        inputs={busB: solph.Flow()},
                        outputs={busAIn: solph.Flow()},
                        conversion_factors={(busB, busAIn): l["efficiency from B to A"]}
                    ))