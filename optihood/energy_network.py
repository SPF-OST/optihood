import numpy as np
import pandas as pd
import oemof.solph as solph
from oemof.tools import logger
import logging
import os
import pprint as pp
from configparser import ConfigParser
from datetime import datetime
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from optihood.constraints import *
from optihood.buildings import Building
from optihood.links import Link


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
        self.__elHP = {}
        self.__shHP = {}
        self.__dhwHP = {}
        self.__annualCopHP = {}
        self.__elGWHP = {}
        self.__shGWHP = {}
        self.__dhwGWHP = {}
        self.__annualCopGWHP = {}
        self.__elRodEff = np.nan
        if not os.path.exists(".\\log_files"):
            os.mkdir(".\\log_files")
        logger.define_logging(logpath=os.getcwd(), logfile=f'.\\log_files\\optihood_{datetime.now().strftime("%d.%m.%Y_%H.%M.%S")}.log')

        logging.info("Initializing the energy network")
        super(EnergyNetworkClass, self).__init__(timeindex=timestamp)

    def setFromExcel(self, filePath, numberOfBuildings, clusterSize={}, opt="costs", mergeLinkBuses=False):
        # does Excel file exist?
        if not filePath or not os.path.isfile(filePath):
            logging.error("Excel data file {} not found.".format(filePath))
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        data = pd.ExcelFile(filePath)
        nodesData = self.createNodesData(data, filePath, numberOfBuildings)
        # nodesData["buses"]["excess costs"] = nodesData["buses"]["excess costs indiv"]
        # nodesData["electricity_cost"]["cost"] = nodesData["electricity_cost"]["cost indiv"]

        if clusterSize:
            demandProfiles = {}
            for i in range(1, numberOfBuildings + 1):
                demandProfiles[i] = pd.concat(
                    [nodesData["demandProfiles"][i].loc[d] for d in clusterSize.keys()])
            electricityImpact = pd.concat(
                [nodesData["electricity_impact"].loc[d] for d in clusterSize.keys()])
            electricityCost = pd.concat(
                [nodesData["electricity_cost"].loc[d] for d in clusterSize.keys()])
            weatherData = pd.concat([nodesData['weather_data'][
                                         nodesData['weather_data']['time.mm'] == int(d.split('-')[1])][
                                         nodesData['weather_data']['time.dd'] == int(d.split('-')[2])][
                                         ['gls', 'str.diffus', 'tre200h0', 'ground_temp']] for d in clusterSize.keys()])

            nodesData["demandProfiles"] = demandProfiles
            nodesData["electricity_impact"] = electricityImpact
            nodesData["electricity_cost"] = electricityCost
            nodesData["weather_data"] = weatherData

        self._convertNodes(nodesData, opt, mergeLinkBuses)
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
            "profiles": data.parse("profiles")
        }
        # update stratified_storage index
        nodesData["stratified_storage"].set_index("label", inplace=True)

        # extract input data from CSVs
        electricityImpact = nodesData["commodity_sources"].loc[nodesData["commodity_sources"]["label"] == "electricityResource", "CO2 impact"].iloc[0]
        electricityCost = nodesData["commodity_sources"].loc[nodesData["commodity_sources"]["label"] == "electricityResource", "variable costs"].iloc[0]
        demandProfilesPath = nodesData["profiles"].loc[nodesData["profiles"]["name"] == "demand_profiles", "path"].iloc[0]
        weatherDataPath = nodesData["profiles"].loc[nodesData["profiles"]["name"] == "weather_data", "path"].iloc[0]


        demandProfiles = {}  # dictionary of dataframes for each building's demand profiles

        if (not os.listdir(demandProfilesPath)) or (not os.path.exists(demandProfilesPath)):
            logging.error("Error in the demand profiles path: The folder is either empty or does not exist")
        else:
            i = 0
            for filename in os.listdir(demandProfilesPath): #this path should contain csv file(s) (one for each building's profiles)
                i += 1      # Building number
                if i > numBuildings:
                    logging.warning("Demand profiles folder has more files than the number of buildings specified")
                    break
                demandProfiles.update({i: pd.read_csv(os.path.join(demandProfilesPath, filename), delimiter=";")})

            nodesData["demandProfiles"] = demandProfiles
            # set datetime index
            for i in range(numBuildings):
                nodesData["demandProfiles"][i + 1].set_index("timestamp", inplace=True)
                nodesData["demandProfiles"][i + 1].index = pd.to_datetime(nodesData["demandProfiles"][i + 1].index)

        if type(electricityImpact) == np.float64:
            # for constant impact
            electricityImpactValue = electricityImpact
            logging.info("Constant value for electricity impact")
            nodesData["electricity_impact"] = pd.DataFrame()
            nodesData["electricity_impact"]["impact"] = (nodesData["demandProfiles"][1].shape[0]) * [
                electricityImpactValue]
            nodesData["electricity_impact"].index = nodesData["demandProfiles"][1].index
        elif not os.path.exists(electricityImpact):
            logging.error("Error in electricity impact file path")
        else:
            nodesData["electricity_impact"] = pd.read_csv(electricityImpact, delimiter=";")
            # set datetime index
            nodesData["electricity_impact"].set_index("timestamp", inplace=True)
            nodesData["electricity_impact"].index = pd.to_datetime(nodesData["electricity_impact"].index)

        if type(electricityCost) == np.float64:
            # for constant cost
            electricityCostValue = electricityCost
            logging.info("Constant value for electricity cost")
            nodesData["electricity_cost"] = pd.DataFrame()
            nodesData["electricity_cost"]["cost"] = (nodesData["demandProfiles"][1].shape[0]) * [
                electricityCostValue]
            nodesData["electricity_cost"].index = nodesData["demandProfiles"][1].index
        elif not os.path.exists(electricityCost):
            logging.error("Error in electricity cost file path")
        else:
            nodesData["electricity_cost"] = pd.read_csv(electricityCost, delimiter=";")
            # set datetime index
            nodesData["electricity_cost"].set_index("timestamp", inplace=True)
            nodesData["electricity_cost"].index = pd.to_datetime(nodesData["electricity_cost"].index)

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

        nodesData["building_model"] = pd.DataFrame()
        nodesData["building_model"]["tAmb"] = np.array(nodesData["weather_data"]["tre200h0"])
        nodesData["building_model"]["IrrH"] = np.array(nodesData["weather_data"]["gls"])/1000       # conversion from W/m2 to kW/m2
        if (nodesData['demand']['building model'].notna().any()) and (nodesData['demand']['building model'] == 'Yes').any():
            nodesData["building_model"]["Qocc"] = np.array(pd.read_csv(r"..\excels\Internal_gains.csv", delimiter=';', header=0)["Total (kW)"])
        else:
            logging.info("Building model either not selected or invalid string value entered")
        logging.info("Data from Excel file {} imported.".format(filePath))
        return nodesData

    def _convertNodes(self, data, opt, mergeLinkBuses):
        if not data:
            logging.error("Nodes data is missing.")
        ################## !!!
        self.__temperatureAmb = np.array(data["weather_data"]["tre200h0"])
        self.__temperatureGround = np.array(data["weather_data"]["ground_temp"])
        self.__temperatureSH = data["stratified_storage"].loc["shStorage", "temp_h"]
        self.__temperatureDHW = data["stratified_storage"].loc["dhwStorage", "temp_h"]
        # Transformers conversion factors input power - output power
        if any(data["transformers"]["label"] == "CHP"):
            self.__chpEff = float(data["transformers"][data["transformers"]["label"] == "CHP"]["efficiency"].iloc[0].split(",")[1])
        if any(data["transformers"]["label"] == "HP"):
            self.__hpEff = float(data["transformers"][data["transformers"]["label"] == "HP"]["efficiency"].iloc[0])
        if any(data["transformers"]["label"] == "GWHP"):
            self.__gwhpEff = float(data["transformers"][data["transformers"]["label"] == "GWHP"]["efficiency"].iloc[0])
        if any(data["transformers"]["label"] == "GasBoiler"):
            self.__gbEff = float(data["transformers"][data["transformers"]["label"] == "GasBoiler"]["efficiency"].iloc[0].split(",")[0])
        if any(data["transformers"]["label"] == "ElectricRod"):
            self.__elRodEff = float(data["transformers"][data["transformers"]["label"] == "ElectricRod"]["efficiency"].iloc[0])
        # Storage conversion L - kWh to display the L value
        self.__Lsh = 4.186 * (self.__temperatureSH - data["stratified_storage"].loc["shStorage", "temp_c"]) / 3600
        self.__Ldhw = 4.186 * (self.__temperatureDHW - data["stratified_storage"].loc["dhwStorage", "temp_c"]) / 3600
        self._addBuildings(data, opt, mergeLinkBuses)

    def _addBuildings(self, data, opt, mergeLinkBuses):
        numberOfBuildings = max(data["buses"]["building"])
        self.__buildings = [Building('Building' + str(i + 1)) for i in range(numberOfBuildings)]
        for b in self.__buildings:
            buildingLabel = b.getBuildingLabel()
            i = int(buildingLabel[8:])
            if i == 1:
                busDictBuilding1 = b.addBus(data["buses"][data["buses"]["building"] == i], opt, mergeLinkBuses)
            else:
                b.addBus(data["buses"][data["buses"]["building"] == i], opt, mergeLinkBuses)
            if mergeLinkBuses and i!=1:
                b.addToBusDict(busDictBuilding1)
            b.addGridSeparation(data["grid_connection"][data["grid_connection"]["building"] == i], mergeLinkBuses)
            b.addSource(data["commodity_sources"][data["commodity_sources"]["building"] == i], data["electricity_impact"], data["electricity_cost"], opt)
            b.addSink(data["demand"][data["demand"]["building"] == i], data["demandProfiles"][i], data["building_model"], mergeLinkBuses)
            b.addTransformer(data["transformers"][data["transformers"]["building"] == i], self.__temperatureDHW,
                             self.__temperatureSH, self.__temperatureAmb, self.__temperatureGround, opt, mergeLinkBuses)
            #if any(data["transformers"]["label"] == "HP") or any(data["transformers"]["label"] == "GWHP"):   #add electricity rod if HP or GSHP is present in the available technology pool
            #    b.addElectricRodBackup(opt)
            b.addStorage(data["storages"][data["storages"]["building"] == i], data["stratified_storage"], opt, mergeLinkBuses)
            b.addSolar(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"] == "solarCollector")], data["weather_data"], opt, mergeLinkBuses)
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
            self.__opex[buildingLabel] = {}
            self.__envImpactTechnologies[buildingLabel] = {}

    def printNodes(self):
        print("*********************************************************")
        print("The following objects have been created from excel sheet:")
        for n in self.nodes:
            oobj = str(type(n)).replace("<class 'oemof.solph.", "").replace("'>", "")
            print(oobj + ":", n.label)
        print("*********************************************************")

    def optimize(self, numberOfBuildings, solver, envImpactlimit=1000000, clusterSize={},
                 options=None,   # solver options
                 opt_constraints=None, #optinal constraints (implemented for the moment are "roof area"
                 mergeLinkBuses=False):

        if options is None:
            options = {"gurobi": {"MIPGap": 0.01}}

        optimizationModel = solph.Model(self)
        logging.info("Optimization model built successfully")

        # add constraint to limit the environmental impacts
        optimizationModel, flows, transformerFlowCapacityDict, storageCapacityDict = environmentalImpactlimit(
            optimizationModel, keyword1="env_per_flow", keyword2="env_per_capa", limit=envImpactlimit)

        # optional contraints (available: 'roof area')
        if opt_constraints:
            for c in opt_constraints:
                if c.lower() == "roof area":
                    # requires 2 additional parameters in the scenario file, tab "solar", zenit angle, roof area
                    try:
                        optimizationModel = roof_area_limit(optimizationModel,
                                                        keyword1="space", keyword2="roof_area", nb=numberOfBuildings)
                        logging.info(f"Optional constraint {c} successfully added to the optimization model")
                    except ValueError:
                        logging.error(f"Optional constraint {c} not added to the optimization model : "
                                      f"please check if PV efficiency, roof area and zenith angle are present in input "
                                      f"file")
                        pass
                if c.lower() == 'totalPVcapacity':
                    optimizationModel = totalPVCapacityConstraint(optimizationModel, numberOfBuildings)
                    logging.info(f"Optional constraint {c} successfully added to the optimization model")
        # constraint on elRod combined with HPs:
        if not np.isnan(self.__elRodEff):
            optimizationModel = electricRodCapacityConstaint(optimizationModel, numberOfBuildings)

        if clusterSize:
            optimizationModel = dailySHStorageConstraint(optimizationModel)


        logging.info("Custom constraints successfully added to the optimization model")

        if solver == "gurobi":
            logging.info("Initiating optimization using {} solver".format(solver))

        optimizationModel.solve(solver=solver, cmdline_options=options[solver])

        # obtain the value of the environmental impact (subject to the limit constraint)
        # the optimization imposes an integral limit constraint on the environmental impacts
        # total environmental impacts <= envImpactlimit
        envImpact = optimizationModel.totalEnvironmentalImpact()

        self._optimizationResults = solph.processing.results(optimizationModel)
        self._metaResults = solph.processing.meta_results(optimizationModel)
        logging.info("Optimization successful and results collected")

        # calculate capacities invested for transformers and storages (for the entire energy network and per building)
        capacitiesTransformersNetwork, capacitiesStoragesNetwork = self._calculateInvestedCapacities(optimizationModel, transformerFlowCapacityDict, storageCapacityDict)

        if clusterSize:
            self._postprocessingClusters(clusterSize)

        # calculate results (CAPEX, OPEX, FeedIn Costs, environmental impacts etc...) for each building
        self._calculateResultsPerBuilding(mergeLinkBuses)

        return envImpact, capacitiesTransformersNetwork, capacitiesStoragesNetwork

    def _updateCapacityDictInputInvestment(self, transformerFlowCapacityDict):
        components = ["CHP", "GWHP", "HP", "GasBoiler", "ElectricRod"]
        for inflow, outflow in list(transformerFlowCapacityDict):
            index = (inflow, outflow)
            if "__" in str(inflow):
                buildingLabel = str(inflow).split("__")[1]
            elif "__" in str(outflow):
                buildingLabel = str(outflow).split("__")[1]
            if any(c in str(outflow) for c in components):
                newoutFlow = f"shSourceBus__{buildingLabel}"
                newIndex = (outflow,newoutFlow)
                transformerFlowCapacityDict[newIndex] = transformerFlowCapacityDict.pop(index)

        return transformerFlowCapacityDict

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

        # update transformerFlowCapacityDict such that investment objects with input flows are accounted properly in the results calculation
        transformerFlowCapacityDict = self._updateCapacityDictInputInvestment(transformerFlowCapacityDict)

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
                self.__capacitiesStoragesBuilding[buildingLabel].update(
                    {index: capacitiesInvestedStorages[index]})
            else:
                self.__capacitiesStoragesBuilding[buildingLabel].update({index: capacitiesInvestedStorages[index]})
            storageList.append(x)

        return capacitiesInvestedTransformers, capacitiesInvestedStorages

    def _compensateInputCapacities(self, capacitiesTransformers):
        # Input capacity -> output capacity
        for first, second in list(capacitiesTransformers):
            if "CHP" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if "shSource" in t.label:
                                capacitiesTransformers[(second,t.label)]= capacitiesTransformers[(first,second)]*self.__chpEff
                                del capacitiesTransformers[(first,second)]
            elif "GWHP" in second and not any([c.isdigit() for c in second.split("__")[0]]):  # second condition added for splitted GSHPs
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if "shSource" in t.label:
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(first, second)] * self.__gwhpEff
                                del capacitiesTransformers[(first, second)]
            elif "HP" in second and "GWHP" not in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if "shSource" in t.label:
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(first, second)]*self.__hpEff
                                del capacitiesTransformers[(first, second)]
            elif "GasBoiler" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if "shSource" in t.label:
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(
                                first, second)] * self.__gbEff
                                del capacitiesTransformers[(first, second)]
            elif "ElectricRod" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if "shSource" in t.label:
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(
                                first, second)] * self.__elRodEff
                                del capacitiesTransformers[(first, second)]

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
        flows = [x for x in self._optimizationResults.keys() if x[1] is not None]
        mfactor = np.repeat(list(clusterSize.values()), 24)
        for flow in flows:
            self._optimizationResults[flow]['sequences'] = self._optimizationResults[flow]['sequences'].mul(mfactor, axis=0)


    def _calculateResultsPerBuilding(self, mergeLinkBuses):
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
            if mergeLinkBuses:
                electricityBusLabel = "electricityBus"
                excessElectricityBusLabel = "excesselectricityBus"
            else:
                electricityBusLabel = "electricityBus" + '__' + buildingLabel
                excessElectricityBusLabel = "excesselectricityBus" + '__' + buildingLabel

            costParamGridElectricity = self.__costParam[electricitySourceLabel].copy()
            costParamGridElectricity.reset_index(inplace=True, drop=True)
            gridElectricityFlow = solph.views.node(self._optimizationResults, gridBusLabel)["sequences"][
                (electricitySourceLabel, gridBusLabel), "flow"]
            gridElectricityFlow.reset_index(inplace=True, drop=True)

            # OPeration EXpenditure
            self.__opex[buildingLabel].update({i[0]: sum(
                solph.views.node(self._optimizationResults, i[1])["sequences"][(i[0], i[1]), "flow"] * self.__costParam[
                    i[0]]) for i in inputs})
            self.__opex[buildingLabel].update({electricitySourceLabel: (
                        costParamGridElectricity * gridElectricityFlow).sum()})  # cost of grid electricity is added separately based on cost data

            # self.__opex[buildingLabel] = sum(sum(solph.views.node(self._optimizationResults, i[1])["sequences"][(i[0], i[1]), "flow"])
            #                                         * self.__costParam[i[0]] for i in inputs + [[electricitySourceLabel, gridBusLabel]])

            # Feed-in electricity cost (value will be in negative to signify monetary gain...)
            self.__feedIn[buildingLabel] = sum(solph.views.node(self._optimizationResults, electricityBusLabel)
                                               ["sequences"][(electricityBusLabel, excessElectricityBusLabel), "flow"]) * self.__costParam[excessElectricityBusLabel]

            if mergeLinkBuses:
                elInBusLabel = 'electricityInBus'
            else:
                elInBusLabel = 'electricityInBus__'+buildingLabel
            # HP flows
            if ("HP__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacityTransformers:
                self.__elHP[buildingLabel] = sum(
                    solph.views.node(self._optimizationResults, elInBusLabel)["sequences"][
                        (elInBusLabel, 'HP__'+buildingLabel), 'flow'])
                self.__shHP[buildingLabel] = sum(
                    solph.views.node(self._optimizationResults, 'HP__' + buildingLabel)["sequences"][
                        ('HP__' + buildingLabel, 'shSourceBus__' + buildingLabel), 'flow'])
                self.__dhwHP[buildingLabel] = sum(
                    solph.views.node(self._optimizationResults, 'HP__' + buildingLabel)["sequences"][
                        ('HP__' + buildingLabel, 'dhwStorageBus__' + buildingLabel), 'flow'])
                self.__annualCopHP[buildingLabel] = (self.__shHP[buildingLabel] + self.__dhwHP[buildingLabel]) / (
                    self.__elHP[buildingLabel] + 1e-6)

            # GWHP flows
            if ("GWHP__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacityTransformers:
                self.__elGWHP[buildingLabel] = sum(
                    solph.views.node(self._optimizationResults, elInBusLabel)["sequences"][
                        (elInBusLabel, 'GWHP__' + buildingLabel), 'flow'])
                self.__shGWHP[buildingLabel] = sum(
                    solph.views.node(self._optimizationResults, 'GWHP__' + buildingLabel)["sequences"][
                        ('GWHP__' + buildingLabel, 'shSourceBus__' + buildingLabel), 'flow'])
                self.__dhwGWHP[buildingLabel] = sum(
                    solph.views.node(self._optimizationResults, 'GWHP__' + buildingLabel)["sequences"][
                        ('GWHP__' + buildingLabel, 'dhwStorageBus__' + buildingLabel), 'flow'])
                self.__annualCopGWHP[buildingLabel] = (self.__shGWHP[buildingLabel] + self.__dhwGWHP[buildingLabel]) / (
                        self.__elGWHP[buildingLabel] + 1e-6)
            else:       # splitted GSHP
                self.__annualCopGWHP[buildingLabel] = []
                if (f"GWHP{str(self.__temperatureSH)}__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacityTransformers:
                    self.__elGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, elInBusLabel)["sequences"][
                            (elInBusLabel, f"GWHP{str(self.__temperatureSH)}__" + buildingLabel), 'flow'])
                    self.__shGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, f"GWHP{str(self.__temperatureSH)}__" + buildingLabel)["sequences"][
                            (f"GWHP{str(self.__temperatureSH)}__" + buildingLabel, 'shSourceBus__' + buildingLabel), 'flow'])
                    self.__annualCopGWHP[buildingLabel].append((self.__shGWHP[buildingLabel]) / (self.__elGWHP[buildingLabel] + 1e-6))
                if (f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel, "dhwStorageBus__" + buildingLabel) in capacityTransformers:
                    self.__elGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, elInBusLabel)["sequences"][
                            (elInBusLabel, f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel), 'flow'])
                    self.__dhwGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel)["sequences"][
                            (f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel, 'dhwStorageBus__' + buildingLabel), 'flow'])
                    self.__annualCopGWHP[buildingLabel].append((self.__dhwGWHP[
                        buildingLabel]) / (self.__elGWHP[buildingLabel] + 1e-6))

            envParamGridElectricity = self.__envParam[electricitySourceLabel].copy()
            envParamGridElectricity.reset_index(inplace=True, drop=True)
            # gridElectricityFlow = solph.views.node(self._optimizationResults, gridBusLabel)["sequences"][
            #     (electricitySourceLabel, gridBusLabel), "flow"]
            # gridElectricityFlow.reset_index(inplace=True, drop=True)

            # Environmental impact due to inputs (natural gas, electricity, etc...)
            self.__envImpactInputs[buildingLabel].update({i[0]: sum(solph.views.node(self._optimizationResults, i[1])["sequences"][(i[0], i[1]), "flow"] * self.__envParam[i[0]]) for i in inputs})
            self.__envImpactInputs[buildingLabel].update({electricitySourceLabel: (envParamGridElectricity * gridElectricityFlow).sum()})  # impact of grid electricity is added separately based on LCA data

            # Environmental impact due to technologies (converters, storages)
            # calculated by adding both environmental impact per capacity and per flow (electrical flow or heat flow)
            self.__envImpactTechnologies[buildingLabel].update({i: capacityTransformers[(i, o)] * self.__envParam[i][2] +
                                                                   sum(sum(solph.views.node(self._optimizationResults,
                                                                                            t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                           self.__envParam[t[1]][1] * ('electricityBus' in t[0]) + \
                                                                           solph.views.node(self._optimizationResults,
                                                                                            t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                           self.__envParam[t[1]][0] * ('electricityBus' not in t[0]))
                                                                       for t in technologies if t[1] == i)
                                                                for i, o in capacityTransformers})
            self.__envImpactTechnologies[buildingLabel].update({x: capacityStorages[x] * self.__envParam[x][2] +
                                                                   sum(sum(
                                                                       solph.views.node(self._optimizationResults,
                                                                                        t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                       self.__envParam[t[1]][1] * ('electricityBus' in t[0]) + \
                                                                       solph.views.node(self._optimizationResults,
                                                                                        t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                       self.__envParam[t[1]][0] * ('electricityBus' not in t[0]))
                                                                       for t in technologies if t[1] == x)
                                                                for x in capacityStorages})

    def printMetaresults(self):
        print("Meta Results:")
        pp.pprint(self._metaResults)
        print("")
        return self._metaResults

    def calcStateofCharge(self, type, building):
        if type + '__' + building in self.groups:
            storage = self.groups[type + '__' + building]
            # print(f"""********* State of Charge ({type},{building}) *********""")
            # print(
            #    self._optimizationResults[(storage, None)]["sequences"]
            # )
            self._storageContentSH[building] = self._optimizationResults[(storage, None)]["sequences"]
        print("")

    def printInvestedCapacities(self, capacitiesInvestedTransformers, capacitiesInvestedStorages):
        for b in range(len(self.__buildings)):
            buildingLabel = "Building" + str(b + 1)
            print("************** Optimized Capacities for {} **************".format(buildingLabel))
            if ("HP__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[("HP__" + buildingLabel, "shSourceBus__" + buildingLabel)]
                print("Invested in {} kW HP.".format(investSH))
                print("     Annual COP = {}".format(self.__annualCopHP[buildingLabel]))
            if ("GWHP__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[("GWHP__" + buildingLabel, "shSourceBus__" + buildingLabel)]
                print("Invested in {} kW GWHP.".format(investSH))
                print("     Annual COP = {}".format(self.__annualCopGWHP[buildingLabel]))
            if (f"GWHP{str(self.__temperatureSH)}__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[(f"GWHP{str(self.__temperatureSH)}__" + buildingLabel, "shSourceBus__" + buildingLabel)]
                print("Invested in {} kW GWHP{}.".format(investSH, str(self.__temperatureSH)))
                print("     Annual COP = {}".format(self.__annualCopGWHP[buildingLabel][0]))
            if (f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel, "dhwStorageBus__" + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[(f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel, "dhwStorageBus__" + buildingLabel)]
                print("Invested in {} kW GWHP{}.".format(investSH, str(self.__temperatureDHW)))
                print("     Annual COP = {}".format(self.__annualCopGWHP[buildingLabel][1]))
            if ("ElectricRod__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[("ElectricRod__" + buildingLabel, "shSourceBus__" + buildingLabel)]
                print("Invested in {} kW Electric Rod.".format(investSH))
            if ("CHP__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers["CHP__" + buildingLabel, "shSourceBus__" + buildingLabel]
                print("Invested in {} kW CHP.".format(investSH))  # + investEL))
            if ("GasBoiler__" + buildingLabel, "shSourceBus__" + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers["GasBoiler__" + buildingLabel, "shSourceBus__" + buildingLabel]
                print("Invested in {} kW  GasBoiler.".format(investSH))
            if ("heat_solarCollector__" + buildingLabel, "solarConnectBus__" + buildingLabel) in capacitiesInvestedTransformers:
                invest = capacitiesInvestedTransformers[("heat_solarCollector__" + buildingLabel, "solarConnectBus__" + buildingLabel)]
                print("Invested in {} m² SolarCollector.".format(invest))
            if ("pv__" + buildingLabel, "electricityProdBus__" + buildingLabel) in capacitiesInvestedTransformers:
                invest = capacitiesInvestedTransformers[("pv__" + buildingLabel, "electricityProdBus__" + buildingLabel)]
                print("Invested in {} kWp  PV.".format(invest))
            if "electricalStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["electricalStorage__" + buildingLabel]
                print("Invested in {} kWh Electrical Storage.".format(invest))
            if "dhwStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["dhwStorage__" + buildingLabel]
                print("Invested in {} L DHW Storage Tank.".format(invest))
            if "shStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["shStorage__" + buildingLabel]
                print("Invested in {} L SH Storage Tank.".format(invest))
            print("")

    def printCosts(self):
        capexNetwork = sum(self.__capex["Building" + str(b + 1)] for b in range(len(self.__buildings)))
        opexNetwork = sum(sum(self.__opex["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        feedinNetwork = sum(self.__feedIn["Building" + str(b + 1)] for b in range(len(self.__buildings)))
        print("Investment Costs for the system: {} CHF".format(capexNetwork))
        print("Operation Costs for the system: {} CHF".format(opexNetwork))
            # (sum(self.__opex["Building" + str(b + 1)] for b in range(len(self.__buildings)))))
        print("Feed In Costs for the system: {} CHF".format(feedinNetwork))
        print("Total Costs for the system: {} CHF".format(capexNetwork + opexNetwork + feedinNetwork))

    def printEnvImpacts(self):
        envImpactInputsNetwork = sum(sum(self.__envImpactInputs["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        envImpactTechnologiesNetwork = sum(sum(self.__envImpactTechnologies["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        print("Environmental impact from input resources for the system: {} kg CO2 eq".format(envImpactInputsNetwork))
        print("Environmental impact from energy conversion technologies for the system: {} kg CO2 eq".format(envImpactTechnologiesNetwork))
        print("Total: {} kg CO2 eq".format(envImpactInputsNetwork + envImpactTechnologiesNetwork))

    def getTotalCosts(self):
        capexNetwork = sum(self.__capex["Building" + str(b + 1)] for b in range(len(self.__buildings)))
        opexNetwork = sum(
            sum(self.__opex["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        feedinNetwork = sum(self.__feedIn["Building" + str(b + 1)] for b in range(len(self.__buildings)))
        return capexNetwork + opexNetwork + feedinNetwork

    def getTotalEnvImpacts(self):
        envImpactInputsNetwork = sum(
            sum(self.__envImpactInputs["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        envImpactTechnologiesNetwork = sum(
            sum(self.__envImpactTechnologies["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        return envImpactTechnologiesNetwork + envImpactInputsNetwork

    def exportToExcel(self, file_name, mergeLinkBuses=False):
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
                    if not mergeLinkBuses:
                        dhwStorageBusLabel = "dhwStorageBus__" + i.split("__")[1]
                        resultDHW = pd.DataFrame.from_dict(solph.views.node(self._optimizationResults, i)["sequences"])  # result sequences of DHW bus
                        resultDHWStorage = pd.DataFrame.from_dict(solph.views.node(self._optimizationResults, dhwStorageBusLabel)["sequences"])  # result sequences of DHW storage bus
                        result = pd.concat([resultDHW, resultDHWStorage], axis=1, sort=True)
                    else:
                        result = pd.DataFrame.from_dict(solph.views.node(self._optimizationResults, i)["sequences"])  # result sequences of DHW bus
                elif mergeLinkBuses and "dhwStorageBus" in i and "sequences" in solph.views.node(self._optimizationResults, i):
                    result = pd.DataFrame.from_dict(solph.views.node(self._optimizationResults, i)["sequences"])  # result sequences of DHW storage bus
                elif "dhwStorageBus" not in i:  # for all the other buses except DHW storage bus (as it is already considered with DHW bus)
                    if 'sequences' in solph.views.node(self._optimizationResults, i):
                        result = pd.DataFrame.from_dict(solph.views.node(self._optimizationResults, i)["sequences"])
                        if "shSourceBus" in i and i.split("__")[1] in self._storageContentSH:
                            result = pd.concat([result, self._storageContentSH[i.split("__")[1]]], axis=1, sort=True)
                    else:
                        continue
                result[result < 0.001] = 0      # to resolve the issue of very low values in the results in certain cases, values less than 1 Watt would be replaced by 0
                if mergeLinkBuses or "dhwStorageBus" not in i:
                    result.to_excel(writer, sheet_name=i)

            # writing the costs and environmental impacts (of different components...) for each building
            for b in self.__buildings:
                buildingLabel = b.getBuildingLabel()
                costs = self.__opex[buildingLabel]
                costs.update({"Investment": self.__capex[buildingLabel],
                              "Feed-in": self.__feedIn[buildingLabel]})
                    # {"Operation": self.__opex[buildingLabel],
                    #      "Investment": self.__capex[buildingLabel],
                    #      "Feed-in": self.__feedIn[buildingLabel],
                    #      }
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
    def createScenarioFile(self, configFilePath, excelFilePath, building, numberOfBuildings=1):
        """function to create the input excel file from a config file
        saves the generated excel file at the path given by excelFilePath"""
        config = ConfigParser()
        config.read(configFilePath)
        configData = {}
        excelData= {}
        columnNames = {'commodity_sources': ['label', 'building', 'to', 'variable costs', 'CO2 impact', 'active'],# column names are defined for each sheet (key of dict) in the excel file
                       'solar': ['label', 'building', 'from', 'to', 'connect', 'electrical_consumption', 'peripheral_losses', 'latitude', 'longitude', 'tilt', 'azimuth', 'eta_0', 'a_1', 'a_2', 'temp_collector_inlet', 'delta_temp_n', 'capacity_max', 'capacity_min', 'lifetime', 'maintenance', 'installation', 'planification', 'invest_base', 'invest_cap', 'heat_impact', 'elec_impact', 'impact_cap'],
                       'demand': ['label', 'building', 'active', 'from', 'fixed', 'nominal value', 'building model'],
                       'transformers': ['label', 'building', 'active', 'from', 'to', 'efficiency', 'capacity_DHW', 'capacity_SH', 'capacity_el', 'capacity_min', 'lifetime', 'maintenance', 'installation', 'planification', 'invest_base', 'invest_cap', 'heat_impact', 'elec_impact', 'impact_cap'],
                       'storages': ['label', 'building', 'active', 'from', 'to', 'efficiency inflow', 'efficiency outflow', 'initial capacity', 'capacity min', 'capacity max', 'capacity loss', 'lifetime', 'maintenance', 'installation', 'planification', 'invest_base', 'invest_cap', 'heat_impact', 'elec_impact', 'impact_cap'],
                       'stratified_storage': ['label', 'diameter', 'temp_h', 'temp_c', 'temp_env', 'inflow_conversion_factor', 'outflow_conversion_factor', 's_iso', 'lamb_iso', 'alpha_inside', 'alpha_outside']
                       }
        buses = {'naturalgasresource': ['naturalGasBus', '', ''], 'electricityresource': ['gridBus', '', ''], 'solarcollector': ['dhwStorageBus', 'electricityInBus', 'solarConnectBus'],    # [to, from, connect] columns in the excel file
                 'pv': ['electricityProdBus', '', ''], 'electricitydemand': ['', 'electricityInBus', ''], 'spaceheatingdemand': ['', 'shDemandBus', ''],
                 'domestichotwaterdemand': ['', 'domesticHotWaterBus', ''], 'gasboiler': ['shSourceBus,dhwStorageBus', 'naturalGasBus', ''], 'electricrod': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''],
                 'chp': ['electricityProdBus,shSourceBus,dhwStorageBus', 'naturalGasBus', ''], 'ashp': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''], 'gshp': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''],
                 'electricalstorage': ['electricityBus', 'electricityProdBus', ''], 'shstorage': ['spaceHeatingBus', 'shSourceBus', ''], 'dhwstorage': ['domesticHotWaterBus', 'dhwStorageBus', '']}
        sheetToSection = {'commodity_sources':'CommoditySources', 'solar':'Solar', 'demand':'Demands', 'transformers':'Transformers', 'storages':'Storages', 'stratified_storage':'StratifiedStorage'}
        sections = config.sections()
        profiles = pd.DataFrame(columns=['name', 'path'])
        updatedLabels = {'weatherpath':'weather_data', 'path':'demand_profiles', 'ashp':'HP', 'gshp':'GWHP', 'electricityresource':'electricityResource', 'naturalgasresource':'naturalGasResource', 'chp':'CHP', 'gasboiler':'GasBoiler', 'electricrod':'ElectricRod', 'pv':'pv', 'solarcollector':'solarCollector', 'electricalstorage':'electricalStorage', 'shstorage':'shStorage', 'dhwstorage':'dhwStorage', 'stratifiedstorage':'StratifiedStorage'}
        temp_h = {}     # to store temp_h values for stratified storage parameters sheet
        FeedinTariff = 0
        for section in config.sections():
            configData[section]=config.items(section)
        configData = {k.lower(): v for k, v in configData.items()}
        for sheet in columnNames:
            excelData[sheet] = pd.DataFrame(columns=columnNames[sheet])
            if sheet == 'stratified_storage':
                newRow = pd.DataFrame(columns=columnNames[sheet])
                newRow.at[0, 'label'] = list(temp_h)[0]
                newRow.at[0, 'temp_h'] = list(temp_h.values())[0]
                newRow.at[1, 'label'] = list(temp_h)[1]
                newRow.at[1, 'temp_h'] = list(temp_h.values())[1]
            for item in configData[sheetToSection[sheet].lower()]:
                type = item[0]
                if item[1] in ['True', 'False']:  # defines whether or not a component is to be added
                    if item[1] == 'True':
                        newRow = pd.DataFrame(columns=columnNames[sheet])
                        newRow.at[0,'label']=updatedLabels[item[0]]
                        newRow.at[0,'active']=int(bool(item[1]=='True'))
                        # sheet specific options
                        cols = newRow.columns
                        if 'building' in cols:
                            newRow.at[0,'building']=1
                        if 'to' in cols:
                            newRow.at[0,'to'] = buses[type][0]
                        if 'from' in cols:
                            newRow.at[0,'from'] = buses[type][1]
                        if 'connect' in cols:
                            newRow.at[0,'connect'] = buses[type][2]
                        params = configData[type]
                        if sheet == 'commodity_sources':
                            index = [x for x, y in enumerate(params) if y[0] == 'cost'][0]
                            newRow.at[0,'variable costs'] = params[index][1]
                            index = [x for x, y in enumerate(params) if y[0] == 'impact'][0]
                            newRow.at[0,'CO2 impact'] = params[index][1]
                            if type=='electricityresource':
                                index = [x for x, y in enumerate(params) if y[0] == 'feedintariff'][0]
                                FeedinTariff = -float(params[index][1])
                        else:
                            for p in params:
                                if sheet=='transformers' and p[0] == 'capacity_max':
                                    newRow.at[0, 'capacity_DHW'] = p[1]
                                    newRow.at[0, 'capacity_SH'] = p[1]
                                    if updatedLabels[item[0]]=='CHP':
                                        newRow.at[0, 'capacity_el'] = str(round(float(p[1])*float(newRow.at[0, 'efficiency'].split(',')[0])/float(newRow.at[0, 'efficiency'].split(',')[1]),0))
                                elif sheet=='storages' and p[0] == 'temp_h':
                                    temp_h[newRow.at[0,'label']] = p[1]
                                else:
                                    newRow.at[0,p[0]] = p[1]
                        excelData[sheet] = pd.concat([excelData[sheet], newRow])
                elif type=='path':       # demand path
                    buildingFolder = [i[1] for i in configData['demands'] if i[0] == 'folders'][0].split(',')[building]
                    buildingPath = item[1]+'\\'+ buildingFolder
                    profiles = pd.concat([profiles, pd.DataFrame({'name': [updatedLabels[type]], 'path': [buildingPath]})])
                elif 'path' in type:     # weather path
                    profiles = pd.concat([profiles, pd.DataFrame({'name':[updatedLabels[type]], 'path':[item[1]]})])
                elif sheet == 'demand' and type!='folders':
                    newRow = pd.DataFrame(columns=columnNames[sheet])
                    for d in ['electricityDemand', 'spaceHeatingDemand', 'domesticHotWaterDemand']:
                        newRow.at[0, 'label'] = d
                        newRow.at[0, 'from'] = buses[d.lower()][1]
                        if d == 'spaceHeatingDemand' and item[1]==0:
                            newRow.at[0, 'fixed'] = item[1]
                            newRow.at[0, 'building model'] = 'Yes'
                        else:
                            newRow.at[0, 'fixed'] = 1
                        excelData[sheet] = pd.concat([excelData[sheet], newRow])
                    excelData[sheet]['building'] = 1
                    excelData[sheet]['active'] = 1
                    excelData[sheet]['nominal value'] = 1
                elif sheet == 'stratified_storage':
                    newRow.at[0,type] = item[1]
                    newRow.at[1,type] = item[1]
                else: # common parameters of all the components of that section
                    if type!='folders':
                        excelData[sheet][type] = item[1]
            if sheet == 'stratified_storage':
                excelData[sheet] = pd.concat([excelData[sheet], newRow])
        excelData['profiles'] = profiles
        excelData['grid_connection'] = pd.DataFrame({'label':['gridElectricity','electricitySource','producedElectricity','shSource','spaceHeating'], 'building':[1,1,1,1,1], 'from':['gridBus','electricityProdBus','electricityBus','shSourceBus','spaceHeatingBus'], 'to':['electricityInBus','electricityBus','electricityInBus','spaceHeatingBus','shDemandBus'], 'efficiency':[1,1,1,1,1]})

        df = pd.DataFrame(columns=['buses'])
        for sheet, data in excelData.items():
            for col in ['from', 'to', 'connect']:
                if col in data.columns:
                    newBuses = pd.DataFrame(columns=['buses'])
                    newBuses['buses'] = data[col].values
                    df = pd.concat([df, newBuses])
        df = df.assign(buses=df.buses.str.split(',')).explode('buses')['buses'].unique()
        df = df[df != '']
        excelData['buses'] = pd.DataFrame(columns=['label', 'building', 'excess', 'excess costs', 'active'])
        for index in range(len(df)):
            excelData['buses'].at[index,'label'] = df[index]
            if df[index] == 'electricityBus' and FeedinTariff!=0:
                excelData['buses'].at[index,'excess'] = 1
                excelData['buses'].at[index, 'excess costs'] = FeedinTariff
        excelData['buses']['building'] = 1
        excelData['buses']['active'] = 1
        excelData['buses'].loc[excelData['buses']['excess']!=1,'excess'] = 0
        for sheet, data in excelData.items():
            if 'building' in data.columns:
                buildingNo = [i for i in range(1, numberOfBuildings + 1)]* len(excelData[sheet].index)
                excelData[sheet] = pd.DataFrame(np.repeat(data.values, numberOfBuildings, axis=0), columns=data.columns)
                excelData[sheet]['building'] = buildingNo
        with pd.ExcelWriter(excelFilePath, engine='xlwt') as writer:
            for sheet, data in excelData.items():
                data.to_excel(writer, sheet_name=sheet, index=False)
            writer.save()
            writer.close()


class EnergyNetworkGroup(EnergyNetworkClass):
    def createScenarioFile(self, configFilePath, excelFilePath, numberOfBuildings):
        """function to create the input excel file from a config file
        saves the generated excel file at the path given by excelFilePath"""
        config = ConfigParser()
        config.read(configFilePath)
        configData = {}
        excelData = {}
        columnNames = {'commodity_sources': ['label', 'building', 'to', 'variable costs', 'CO2 impact', 'active'],
                       # column names are defined for each sheet (key of dict) in the excel file
                       'solar': ['label', 'building', 'from', 'to', 'connect', 'electrical_consumption',
                                 'peripheral_losses', 'latitude', 'longitude', 'tilt', 'azimuth', 'eta_0', 'a_1', 'a_2',
                                 'temp_collector_inlet', 'delta_temp_n', 'capacity_max', 'capacity_min', 'lifetime',
                                 'maintenance', 'installation', 'planification', 'invest_base', 'invest_cap',
                                 'heat_impact', 'elec_impact', 'impact_cap'],
                       'demand': ['label', 'building', 'active', 'from', 'fixed', 'nominal value', 'building model'],
                       'transformers': ['label', 'building', 'active', 'from', 'to', 'efficiency', 'capacity_DHW',
                                        'capacity_SH', 'capacity_el', 'capacity_min', 'lifetime', 'maintenance',
                                        'installation', 'planification', 'invest_base', 'invest_cap', 'heat_impact',
                                        'elec_impact', 'impact_cap'],
                       'storages': ['label', 'building', 'active', 'from', 'to', 'efficiency inflow',
                                    'efficiency outflow', 'initial capacity', 'capacity min', 'capacity max',
                                    'capacity loss', 'lifetime', 'maintenance', 'installation', 'planification',
                                    'invest_base', 'invest_cap', 'heat_impact', 'elec_impact', 'impact_cap'],
                       'stratified_storage': ['label', 'diameter', 'temp_h', 'temp_c', 'temp_env',
                                              'inflow_conversion_factor', 'outflow_conversion_factor', 's_iso',
                                              'lamb_iso', 'alpha_inside', 'alpha_outside'],
                       'links': ['label', 'active', 'efficiency', 'invest_base', 'invest_cap', 'investment']
                       }
        buses = {'naturalgasresource': ['naturalGasBus', '', ''], 'electricityresource': ['gridBus', '', ''],
                 'solarcollector': ['dhwStorageBus', 'electricityInBus', 'solarConnectBus'],
                 # [to, from, connect] columns in the excel file
                 'pv': ['electricityProdBus', '', ''], 'electricitydemand': ['', 'electricityInBus', ''],
                 'spaceheatingdemand': ['', 'shDemandBus', ''],
                 'domestichotwaterdemand': ['', 'dhwDemandBus', ''],
                 'gasboiler': ['shSourceBus,dhwStorageBus', 'naturalGasBus', ''],
                 'electricrod': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''],
                 'chp': ['electricityProdBus,shSourceBus,dhwStorageBus', 'naturalGasBus', ''],
                 'ashp': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''],
                 'gshp': ['shSourceBus,dhwStorageBus', 'electricityInBus', ''],
                 'electricalstorage': ['electricityBus', 'electricityProdBus', ''],
                 'shstorage': ['spaceHeatingBus', 'shSourceBus', ''],
                 'dhwstorage': ['domesticHotWaterBus', 'dhwStorageBus', '']}
        sheetToSection = {'commodity_sources': 'CommoditySources', 'solar': 'Solar', 'demand': 'Demands',
                          'transformers': 'Transformers', 'storages': 'Storages',
                          'stratified_storage': 'StratifiedStorage', 'links':'Links'}
        sections = config.sections()
        profiles = pd.DataFrame(columns=['name', 'path'])
        updatedLabels = {'weatherpath': 'weather_data', 'path': 'demand_profiles', 'ashp': 'HP', 'gshp': 'GWHP',
                         'electricityresource': 'electricityResource', 'naturalgasresource': 'naturalGasResource',
                         'chp': 'CHP', 'gasboiler': 'GasBoiler', 'electricrod': 'ElectricRod', 'pv': 'pv',
                         'solarcollector': 'solarCollector', 'electricalstorage': 'electricalStorage',
                         'shstorage': 'shStorage', 'dhwstorage': 'dhwStorage', 'stratifiedstorage': 'StratifiedStorage',
                         'ellink': 'electricityLink', 'shlink': 'shLink', 'dhwlink': 'dhwLink'}
        efficiencyLinks = {'ellink': 0.9999, 'shlink': 0.9, 'dhwlink': 0.9}
        temp_h = {}  # to store temp_h values for stratified storage parameters sheet
        FeedinTariff = 0
        for section in config.sections():
            configData[section] = config.items(section)
        configData = {k.lower(): v for k, v in configData.items()}
        for sheet in columnNames:
            excelData[sheet] = pd.DataFrame(columns=columnNames[sheet])
            if sheet == 'stratified_storage':
                newRow = pd.DataFrame(columns=columnNames[sheet])
                newRow.at[0, 'label'] = list(temp_h)[0]
                newRow.at[0, 'temp_h'] = list(temp_h.values())[0]
                newRow.at[1, 'label'] = list(temp_h)[1]
                newRow.at[1, 'temp_h'] = list(temp_h.values())[1]
            for item in configData[sheetToSection[sheet].lower()]:
                type = item[0]
                if item[1] in ['True', 'False']:  # defines whether or not a component is to be added
                    if item[1] == 'True':
                        newRow = pd.DataFrame(columns=columnNames[sheet])
                        newRow.at[0, 'label'] = updatedLabels[item[0]]
                        newRow.at[0, 'active'] = int(bool(item[1] == 'True'))
                        # sheet specific options
                        cols = newRow.columns
                        if 'building' in cols:
                            newRow.at[0, 'building'] = 1
                        if 'to' in cols:
                            newRow.at[0, 'to'] = buses[type][0]
                        if 'from' in cols:
                            newRow.at[0, 'from'] = buses[type][1]
                        if 'connect' in cols:
                            newRow.at[0, 'connect'] = buses[type][2]
                        if type in ['shlink', 'dhwlink']:
                            params = configData['thermallink']
                        else:
                            params = configData[type]
                        if sheet == 'commodity_sources':
                            index = [x for x, y in enumerate(params) if y[0] == 'cost'][0]
                            newRow.at[0, 'variable costs'] = params[index][1]
                            index = [x for x, y in enumerate(params) if y[0] == 'impact'][0]
                            newRow.at[0, 'CO2 impact'] = params[index][1]
                            if type == 'electricityresource':
                                index = [x for x, y in enumerate(params) if y[0] == 'feedintariff'][0]
                                FeedinTariff = -float(params[index][1])
                        else:
                            if sheet == 'links':
                                if not [x for x, y in enumerate(params) if y[0] == 'efficiency']:
                                    newRow.at[0, 'efficiency'] = efficiencyLinks[type]
                                newRow.at[0, 'investment'] = 1
                            for p in params:
                                if sheet == 'transformers' and p[0] == 'capacity_max':
                                    newRow.at[0, 'capacity_DHW'] = p[1]
                                    newRow.at[0, 'capacity_SH'] = p[1]
                                    if updatedLabels[item[0]]=='CHP':
                                        newRow.at[0, 'capacity_el'] = str(round(float(p[1])*float(newRow.at[0, 'efficiency'].split(',')[0])/float(newRow.at[0, 'efficiency'].split(',')[1]),0))
                                elif sheet == 'storages' and p[0] == 'temp_h':
                                    temp_h[newRow.at[0, 'label']] = p[1]
                                else:
                                    newRow.at[0, p[0]] = p[1]
                        excelData[sheet] = pd.concat([excelData[sheet], newRow])
                elif 'path' in type:  # weather path or demand path
                    profiles = pd.concat([profiles, pd.DataFrame({'name': [updatedLabels[type]], 'path': [item[1]]})])
                elif sheet == 'demand':
                    newRow = pd.DataFrame(columns=columnNames[sheet])
                    for d in ['electricityDemand', 'spaceHeatingDemand', 'domesticHotWaterDemand']:
                        newRow.at[0, 'label'] = d
                        newRow.at[0, 'from'] = buses[d.lower()][1]
                        if d == 'spaceHeatingDemand' and item[1] == 0:
                            newRow.at[0, 'fixed'] = item[1]
                            newRow.at[0, 'building model'] = 'Yes'
                        else:
                            newRow.at[0, 'fixed'] = 1
                        excelData[sheet] = pd.concat([excelData[sheet], newRow])
                    excelData[sheet]['building'] = 1
                    excelData[sheet]['active'] = 1
                    excelData[sheet]['nominal value'] = 1
                elif sheet == 'stratified_storage':
                    newRow.at[0, type] = item[1]
                    newRow.at[1, type] = item[1]
                else:  # common parameters of all the components of that section
                    excelData[sheet][type] = item[1]
            if sheet == 'stratified_storage':
                excelData[sheet] = pd.concat([excelData[sheet], newRow])
        excelData['profiles'] = profiles
        excelData['grid_connection'] = pd.DataFrame(
            {'label': ['gridElectricity', 'electricitySource', 'producedElectricity', 'domesticHotWater', 'shSource', 'spaceHeating'],
             'building': [1, 1, 1, 1, 1, 1],
             'from': ['gridBus', 'electricityProdBus', 'electricityBus', 'domesticHotWaterBus', 'shSourceBus', 'spaceHeatingBus'],
             'to': ['electricityInBus', 'electricityBus', 'electricityInBus', 'dhwDemandBus', 'spaceHeatingBus', 'shDemandBus'],
             'efficiency': [1, 1, 1, 1, 1, 1]})

        df = pd.DataFrame(columns=['buses'])
        for sheet, data in excelData.items():
            for col in ['from', 'to', 'connect']:
                if col in data.columns:
                    newBuses = pd.DataFrame(columns=['buses'])
                    newBuses['buses'] = data[col].values
                    df = pd.concat([df, newBuses])
        df = df.assign(buses=df.buses.str.split(',')).explode('buses')['buses'].unique()
        df = df[df != '']
        excelData['buses'] = pd.DataFrame(columns=['label', 'building', 'excess', 'excess costs', 'active'])
        for index in range(len(df)):
            excelData['buses'].at[index, 'label'] = df[index]
            if df[index] == 'electricityBus' and FeedinTariff != 0:
                excelData['buses'].at[index, 'excess'] = 1
                excelData['buses'].at[index, 'excess costs'] = FeedinTariff
        excelData['buses']['building'] = 1
        excelData['buses']['active'] = 1
        excelData['buses'].loc[excelData['buses']['excess'] != 1, 'excess'] = 0
        for sheet, data in excelData.items():
            if 'building' in data.columns:
                buildingNo = [i for i in range(1, numberOfBuildings + 1)] * len(excelData[sheet].index)
                excelData[sheet] = pd.DataFrame(np.repeat(data.values, numberOfBuildings, axis=0), columns=data.columns)
                excelData[sheet]['building'] = buildingNo
        with pd.ExcelWriter(excelFilePath, engine='xlwt') as writer:
            for sheet, data in excelData.items():
                data.to_excel(writer, sheet_name=sheet, index=False)
            writer.save()
            writer.close()

    def setFromExcel(self, filePath, numberOfBuildings, clusterSize={}, opt="costs", mergeLinkBuses=False):
        # does Excel file exist?
        if not filePath or not os.path.isfile(filePath):
            logging.error("Excel data file {} not found.".format(filePath))
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        data = pd.ExcelFile(filePath)

        nodesData = self.createNodesData(data, filePath, numberOfBuildings)
        # nodesData["buses"]["excess costs"] = nodesData["buses"]["excess costs group"]
        # nodesData["electricity_cost"]["cost"] = nodesData["electricity_cost"]["cost group"]

        demandProfiles = {}
        if clusterSize:
            for i in range(1, numberOfBuildings + 1):
                demandProfiles[i] = pd.concat(
                    [nodesData["demandProfiles"][i].loc[d] for d in clusterSize.keys()])
            electricityImpact = pd.concat(
                [nodesData["electricity_impact"].loc[d] for d in clusterSize.keys()])
            electricityCost = pd.concat(
                [nodesData["electricity_cost"].loc[d] for d in clusterSize.keys()])
            weatherData = pd.concat([nodesData['weather_data'][
                                         nodesData['weather_data']['time.mm'] == int(d.split('-')[1])][
                                         nodesData['weather_data']['time.dd'] == int(d.split('-')[2])][['gls', 'str.diffus', 'tre200h0', 'ground_temp']] for d in clusterSize.keys()])

            nodesData["demandProfiles"] = demandProfiles
            nodesData["electricity_impact"] = electricityImpact
            nodesData["electricity_cost"] = electricityCost
            nodesData["weather_data"] = weatherData

        nodesData["links"]= data.parse("links")
        self._convertNodes(nodesData, opt, mergeLinkBuses)
        self._addLinks(nodesData["links"], numberOfBuildings, mergeLinkBuses)
        logging.info("Nodes from Excel file {} successfully converted".format(filePath))
        self.add(*self._nodesList)
        logging.info("Nodes successfully added to the energy network")


    def _addLinks(self, data, numberOfBuildings, mergeLinkBuses):  # connects buses A and B (denotes a bidirectional link)
        if mergeLinkBuses:
            return
        for i, l in data.iterrows():
            if l["active"]:
                if l["investment"]:
                    investment = solph.Investment(
                        ep_costs=l["invest_cap"],
                        nonconvex=True,
                        maximum=500000,
                        offset=l["invest_base"],
                    )
                else:
                    investment = None
                busesOut = []
                busesIn = []
                # add two buses for each building link_out and link_in
                for b in range(numberOfBuildings):
                    if "sh" in l["label"]:
                        busesOut.append(self._busDict["spaceHeatingBus" + '__Building' + str(b+1)])
                        busesIn.append(self._busDict["shDemandBus" + '__Building' + str(b+1)])
                    elif "dhw" in l["label"]:
                        busesOut.append(self._busDict["domesticHotWaterBus" + '__Building' + str(b+1)])
                        busesIn.append(self._busDict["dhwDemandBus" + '__Building' + str(b+1)])
                    else:
                        busesOut.append(self._busDict["electricityBus" + '__Building' + str(b + 1)])
                        busesIn.append(self._busDict["electricityInBus" + '__Building' + str(b + 1)])

                self._nodesList.append(Link(
                    label=l["label"],
                    inputs={busA: solph.Flow() for busA in busesOut},
                    outputs={busB: solph.Flow(investment=investment) for busB in busesIn},
                    conversion_factors={busB: l["efficiency"] for busB in busesIn}
                ))