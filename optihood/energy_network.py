import logging
import os
import pathlib as _pl
import pprint as pp
import typing as _tp
from datetime import datetime, timedelta

import numpy as np
import oemof.solph as solph
import pandas as pd
from oemof.tools import logger

import optihood.IO.writers as _wr
import optihood.entities as _ent

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from optihood.buildings import Building
from optihood.constraints import *
from optihood._helpers import *
from optihood.links import Link
import optihood.IO.readers as _re


class OptimizationProperties:
    """
    class under construction ...
    """
    def __init__(self, optType, mergeLinkBuses, mergeHeatSourceSink, temperatureLevels, clusters, dispatchMode, includeCarbonBenefits):
        self._optType = optType
        self._mergeLinkBuses = mergeLinkBuses
        self._mergeHeatSourceSink = mergeHeatSourceSink
        self._temperatureLevels = temperatureLevels
        self._clusters = clusters
        self._dispatchMode = dispatchMode
        self._includeCarbonBenefits = includeCarbonBenefits

    @property
    def optType(self):
        return self._optType

    @property
    def mergeLinkBuses(self):
        return self._mergeLinkBuses

    @property
    def mergeHeatSourceSink(self):
        return self._mergeHeatSourceSink

    @property
    def temperatureLevels(self):
        return self._temperatureLevels

    @property
    def clusters(self):
        return self._clusters

    @property
    def dispatchMode(self):
        return self._dispatchMode

    @property
    def includeCarbonBenefits(self):
        return self._includeCarbonBenefits


def get_data_from_df(df: pd.DataFrame, column_name: str):
    return df[column_name]


def get_data_from_excel_file(data: pd.ExcelFile, column_name: str):
    return data.parse(column_name)


class EnergyNetworkClass(solph.EnergySystem):
    def __init__(self, timestamp, clusters=None, temperatureLevels=False):
        self._timeIndexReal = timestamp             # the timeindex passed to the energy network, will be made shorter if clustering is selected
        self._clusterDate = {}
        if clusters:
            self._numberOfDays = len(clusters)
            lastDay = datetime(timestamp.year[0], 1, 1) + timedelta(self._numberOfDays - 1)
            lastDay = lastDay.strftime('%Y-%m-%d')
            i = 1
            for day in clusters:
                d_clusterIndex = datetime(timestamp.year[0], 1, 1) + timedelta(i - 1)
                self._clusterDate[day] = d_clusterIndex.strftime('%Y-%m-%d')
                i += 1
            timestamp = pd.date_range(f"{timestamp.year[0]}-01-01 00:00:00", f"{lastDay} 23:00:00", freq=timestamp.freq)
        self._nodesList = []
        self._thermalStorageList = []
        self._storageContentSH = {}
        self._storageContentDHW = {}
        self._storageContentTS = {}
        self._storageContent = {}
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
        self.__intermediateOpTempsHP = {}
        self.__annualCopHP = {}
        self.__elGWHP = {}
        self.__shGWHP = {}
        self.__dhwGWHP = {}
        self.__intermediateOpTempsGWHP = {}
        self.__annualCopGWHP = {}
        self.__elRodEff = np.nan
        self._temperatureLevels = temperatureLevels
        self._dispatchMode = False
        self._c = 4.186 #default value for water in kJ/(kg K)
        self._rho = 1. #default value for water in kg/L
        if not os.path.exists(".\\log_files"):
            os.mkdir(".\\log_files")
        logger.define_logging(logpath=os.getcwd(), logfile=f'.\\log_files\\optihood_{datetime.now().strftime("%d.%m.%Y %H.%M.%S")}.log')
        logging.info("Initializing the energy network")
        super(EnergyNetworkClass, self).__init__(timeindex=timestamp, infer_last_interval=True)

    def setFromExcel(self, filePath, numberOfBuildings, clusterSize={}, opt="costs", mergeLinkBuses=False, mergeBuses=None, mergeHeatSourceSink=False, dispatchMode=False, includeCarbonBenefits=False):
        self.check_file_path(filePath)
        self.check_mutually_exclusive_inputs(mergeLinkBuses)
        self._dispatchMode = dispatchMode
        self._optimizationType = opt
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        data = pd.ExcelFile(filePath)
        initial_nodal_data = self.get_nodal_data_from_Excel(data)
        data.close()

        self.set_using_nodal_data(clusterSize, filePath, includeCarbonBenefits, initial_nodal_data, mergeBuses,
                                  mergeHeatSourceSink, mergeLinkBuses, numberOfBuildings, opt)

    def set_using_nodal_data(self, clusterSize, filePath, includeCarbonBenefits, initial_nodal_data, mergeBuses,
                             mergeHeatSourceSink, mergeLinkBuses, numberOfBuildings, opt):
        nodesData = self.createNodesData(initial_nodal_data, filePath, numberOfBuildings, clusterSize)
        # nodesData["buses"]["excess costs"] = nodesData["buses"]["excess costs indiv"]
        # nodesData["electricity_cost"]["cost"] = nodesData["electricity_cost"]["cost indiv"]
        if clusterSize:
            demandProfiles = {}
            for i in range(1, numberOfBuildings + 1):
                demandProfiles[i] = pd.concat(
                    [nodesData["demandProfiles"][i].loc[d] for d in clusterSize.keys()])
            electricityImpact = pd.concat(
                [nodesData["electricity_impact"].loc[d] * clusterSize[d] for d in clusterSize.keys()])
            electricityCost = pd.concat(
                [nodesData["electricity_cost"].loc[d] * clusterSize[d] for d in clusterSize.keys()])
            if 'natGas_impact' in nodesData:
                natGasImpact = pd.concat(
                    [nodesData["natGas_impact"].loc[d] * clusterSize[d] for d in clusterSize.keys()])
                natGasCost = pd.concat(
                    [nodesData["natGas_cost"].loc[d] * clusterSize[d] for d in clusterSize.keys()])
            weatherData = pd.concat([nodesData['weather_data'][
                                         nodesData['weather_data']['time.mm'] == int(d.split('-')[1])][
                                         nodesData['weather_data']['time.dd'] == int(d.split('-')[2])][
                                         ['gls', 'str.diffus', 'tre200h0', 'ground_temp']] for d in clusterSize.keys()])

            nodesData["demandProfiles"] = demandProfiles
            nodesData["electricity_impact"] = electricityImpact
            nodesData["electricity_cost"] = electricityCost
            if 'natGas_impact' in nodesData:
                nodesData["natGas_impact"] = natGasImpact
                nodesData["natGas_cost"] = natGasCost
            nodesData["weather_data"] = weatherData
        self._convertNodes(nodesData, opt, mergeLinkBuses, mergeBuses, mergeHeatSourceSink, includeCarbonBenefits,
                           clusterSize)
        logging.info("Nodes from Excel file {} successfully converted".format(filePath))
        self.add(*self._nodesList)
        logging.info("Nodes successfully added to the energy network")

    def check_mutually_exclusive_inputs(self, mergeLinkBuses):
        if mergeLinkBuses and self._temperatureLevels:
            logging.error("The options mergeLinkBuses and temperatureLevels should not be set True at the same time. "
                          "This use case is not supported in the present version of optihood. Only one of "
                          "mergeLinkBuses and temperatureLevels should be set to True.")

    @staticmethod
    def check_file_path(filePath):
        if not filePath or not os.path.isfile(filePath):
            logging.error(f"File {filePath} not found.")

    def get_nodal_data_from_df(self, data: pd.DataFrame):
        nodes_data = self.get_nodal_data(get_data_from_df, data)

        return nodes_data

    def get_nodal_data_from_dict_with_dfs(self, data: dict):
        """ Facade as the interface is the same as for the DataFrame version. """
        nodes_data = self.get_nodal_data(get_data_from_df, data)

        return nodes_data

    def get_nodal_data_from_Excel(self, data: pd.ExcelFile):
        nodes_data = self.get_nodal_data(get_data_from_excel_file, data)

        return nodes_data

    @staticmethod
    def get_nodal_data(func, data: _tp.Union[pd.ExcelFile, pd.DataFrame, dict]):
        f""" Uses a specified function to get the nodal data from a specified entry point.
            e.g.:
            func = {get_data_from_excel_file}
            func = {get_data_from_df}            
        """
        nodes_data = {
            _ent.NodeKeys.buses.value: func(data, _ent.NodeKeys.buses.value),
            _ent.NodeKeys.grid_connection.value: func(data, _ent.NodeKeys.grid_connection.value),
            _ent.NodeKeys.commodity_sources.value: func(data, _ent.NodeKeys.commodity_sources.value),
            _ent.NodeKeys.solar.value: func(data, _ent.NodeKeys.solar.value),
            _ent.NodeKeys.transformers.value: func(data, _ent.NodeKeys.transformers.value),
            _ent.NodeKeys.demand.value: func(data, _ent.NodeKeys.demand.value),
            _ent.NodeKeys.storages.value: func(data, _ent.NodeKeys.storages.value),
            _ent.NodeKeys.stratified_storage.value: func(data, _ent.NodeKeys.stratified_storage.value),
            _ent.NodeKeys.profiles.value: func(data, _ent.NodeKeys.profiles.value)
        }
        return nodes_data

    @staticmethod
    def get_values_from_dataframe(df: pd.DataFrame, identifier: str, identifier_column: str, desired_column: str):
        f""" Find any {identifier} entries in the {identifier_column} and return the 
             {desired_column} value of those rows."""
        row_indices = df[identifier_column] == identifier
        values = df.loc[row_indices, desired_column].iloc[0]
        return values

    def createNodesData(self, nodesData, file_or_folder_path, numBuildings, clusterSize):
        self.__noOfBuildings = numBuildings

        # update stratified_storage index
        nodesData[_ent.NodeKeys.stratified_storage.value].set_index(_ent.StratifiedStorageLabels.label.value, inplace=True)

        # extract input data from CSVs
        electricityImpact = self.get_values_from_dataframe(nodesData[_ent.NodeKeys.commodity_sources.value], _ent.CommoditySourceTypes.electricityResource.value, _ent.CommoditySourcesLabels.label.value, _ent.CommoditySourcesLabels.CO2_impact.value)
        electricityCost = nodesData[_ent.NodeKeys.commodity_sources.value].loc[nodesData[_ent.NodeKeys.commodity_sources.value]["label"] == "electricityResource", "variable costs"].iloc[0]
        demandProfilesPath = nodesData[_ent.NodeKeys.profiles.value].loc[nodesData[_ent.NodeKeys.profiles.value][_ent.ProfileLabels.name.value] == _ent.ProfileTypes.demand.value, _ent.ProfileLabels.path.value].iloc[0]
        weatherDataPath = nodesData[_ent.NodeKeys.profiles.value].loc[nodesData[_ent.NodeKeys.profiles.value]["name"] == "weather_data", "path"].iloc[0]

        if "naturalGasResource" in nodesData["commodity_sources"]["label"].values:
            natGasCost = nodesData["commodity_sources"].loc[nodesData["commodity_sources"]["label"] == "naturalGasResource", "variable costs"].iloc[0]
            natGasImpact = nodesData["commodity_sources"].loc[
                nodesData["commodity_sources"]["label"] == "naturalGasResource", "CO2 impact"].iloc[0]

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
                nodesData["demandProfiles"][i + 1].timestamp = pd.to_datetime(nodesData["demandProfiles"][i + 1].timestamp, format='%Y-%m-%d %H:%M:%S')
                nodesData["demandProfiles"][i + 1].set_index("timestamp", inplace=True)
                if not clusterSize:
                    nodesData["demandProfiles"][i + 1] = nodesData["demandProfiles"][i + 1][self.timeindex[0]:self.timeindex[-1]]

        if type(electricityImpact) == np.float64 or type(electricityImpact) == np.int64:
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
            nodesData["electricity_impact"].index = pd.to_datetime(nodesData["electricity_impact"].index, format='%d.%m.%Y %H:%M')

        if type(electricityCost) == np.float64 or type(electricityCost) == np.int64:
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
            nodesData["electricity_cost"].index = pd.to_datetime(nodesData["electricity_cost"].index, format='%d.%m.%Y %H:%M')

        if "naturalGasResource" in nodesData["commodity_sources"]["label"].values:
            if isinstance(natGasImpact, (float, np.float64)) or (natGasImpact.split('.')[0].replace('-','').isdigit() and natGasImpact.split('.')[1].replace('-','').isdigit()):
                # for constant impact
                natGasImpactValue = float(natGasImpact)
                logging.info("Constant value for natural gas impact")
                nodesData["natGas_impact"] = pd.DataFrame()
                nodesData["natGas_impact"]["impact"] = (nodesData["demandProfiles"][1].shape[0]) * [
                    natGasImpactValue]
                nodesData["natGas_impact"].index = nodesData["demandProfiles"][1].index
            elif not os.path.exists(natGasImpact):
                logging.error("Error in natural gas impact file path")
            else:
                nodesData["natGas_impact"] = pd.read_csv(natGasImpact, delimiter=";")
                # set datetime index
                nodesData["natGas_impact"].set_index("timestamp", inplace=True)
                nodesData["natGas_impact"].index = pd.to_datetime(nodesData["natGas_impact"].index, format='%d.%m.%Y %H:%M')

            if type(natGasCost) == np.float64:
                # for constant cost
                natGasCostValue = natGasCost
                logging.info("Constant value for natural gas cost")
                nodesData["natGas_cost"] = pd.DataFrame()
                nodesData["natGas_cost"]["cost"] = (nodesData["demandProfiles"][1].shape[0]) * [natGasCostValue]
                nodesData["natGas_cost"].index = nodesData["demandProfiles"][1].index
            elif not os.path.exists(natGasCost):
                logging.error("Error in natural gas cost file path")
            else:
                nodesData["natGas_cost"] = pd.read_csv(natGasCost, delimiter=";")
                # set datetime index
                nodesData["natGas_cost"].set_index("timestamp", inplace=True)
                nodesData["natGas_cost"].index = pd.to_datetime(nodesData["natGas_cost"].index, format='%d.%m.%Y %H:%M')

        if not os.path.exists(weatherDataPath):
            logging.error("Error in weather data file path")
        else:
            nodesData["weather_data"] = pd.read_csv(weatherDataPath, delimiter=";")
            #add a timestamp column to the dataframe
            for index, row in nodesData['weather_data'].iterrows():
                time = f"{int(row['time.yy'])}.{int(row['time.mm']):02}.{int(row['time.dd']):02} {int(row['time.hh']):02}:00:00"
                nodesData['weather_data'].at[index, 'timestamp'] = datetime.strptime(time, "%Y.%m.%d  %H:%M:%S")
                #set datetime index
            nodesData["weather_data"].timestamp = pd.to_datetime(nodesData["weather_data"].timestamp,
                                                                          format='%Y.%m.%d %H:%M:%S')
            nodesData["weather_data"].set_index("timestamp", inplace=True)
            if (not clusterSize) and nodesData["weather_data"].index.year.unique().__len__() == 1:
                nodesData["weather_data"] = nodesData["weather_data"][self.timeindex[0]:self.timeindex[-1]]

        nodesData["building_model"] = {}
        if (nodesData['demand']['building model'].notna().any()) and (nodesData['demand']['building model'] == 'Yes').any():
            internalGainsPath = nodesData["profiles"].loc[nodesData["profiles"]["name"] == "internal_gains", "path"].iloc[0]
            bmodelparamsPath = nodesData["profiles"].loc[nodesData["profiles"]["name"] == "building_model_params", "path"].iloc[0]
            if not os.path.exists(internalGainsPath):
                logging.error("Error in internal gains file path for building model.")
            internalGains = pd.read_csv(internalGainsPath, delimiter=';')
            internalGains.timestamp = pd.to_datetime(internalGains.timestamp, format='%d.%m.%Y %H:%M')
            internalGains.set_index("timestamp", inplace=True)
            if not clusterSize:
                internalGains = internalGains[self.timeindex[0]:self.timeindex[-1]]
            if not os.path.exists(bmodelparamsPath):
                logging.error("Error in building model parameters file path.")
            bmParamers = pd.read_csv(bmodelparamsPath, delimiter=';')
            for i in range(numBuildings):
                nodesData["building_model"][i + 1] = {}
                nodesData["building_model"][i + 1]["timeseries"] = pd.DataFrame()
                nodesData["building_model"][i + 1]["timeseries"]["tAmb"] = np.array(nodesData["weather_data"]["tre200h0"])
                nodesData["building_model"][i + 1]["timeseries"]["IrrH"] = np.array(nodesData["weather_data"]["gls"])/1000       # conversion from W/m2 to kW/m2
                nodesData["building_model"][i + 1]["timeseries"][f"Qocc"] = internalGains[f'Total (kW) {i+1}'].values
                if "tIndoorDay" in bmParamers.columns:
                    tIndoorDay = float(bmParamers[bmParamers["Building Number"] == (i+1)]['tIndoorDay'].iloc[0])
                    tIndoorNight = float(bmParamers[bmParamers["Building Number"] == (i + 1)]['tIndoorNight'].iloc[0])
                    tIndoorSet = [tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight,
                                  tIndoorNight, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay,
                                  tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay,
                                  tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight]*365
                    nodesData["building_model"][i + 1]["timeseries"]["tIndoorSet"] = pd.DataFrame(tIndoorSet).values
                paramList = ['gAreaWindows', 'rDistribution', 'cDistribution', 'rWall', 'cWall', 'rIndoor',
                             'cIndoor',
                             'qDistributionMin', 'qDistributionMax', 'tIndoorMin', 'tIndoorMax', 'tIndoorInit',
                             'tWallInit', 'tDistributionInit']
                for param in paramList:
                    nodesData["building_model"][i + 1][param] = float(bmParamers[bmParamers["Building Number"] == (i+1)][param].iloc[0])
        else:
            logging.info("Building model either not selected or invalid string value entered")
        logging.info(f"Data from file {file_or_folder_path} imported.")
        return nodesData

    def _checkStorageTemperatureGradient(self, temp_c):
        listTemperatures = [temp_c]
        listTemperatures.extend(self.__operationTemperatures)
        gradient = [h - l for l, h in zip(listTemperatures, listTemperatures[1:])]
        return all(x == gradient[0] for x in gradient)
    
    def _convertNodes(self, data, opt, mergeLinkBuses, mergeBuses, mergeHeatSourceSink, includeCarbonBenefits, clusterSize):
        if not data:
            logging.error("Nodes data is missing.")
        self.__temperatureAmb = np.array(data["weather_data"]["tre200h0"])
        self.__temperatureGround = np.array(data["weather_data"]["ground_temp"])
        if self._temperatureLevels:
            try:
                self.__operationTemperatures = [float(t) for t in data["stratified_storage"].loc["thermalStorage", "temp_h"].split(",")] # temperatures should be saved from low to high separated by commas in the excel input file
                if not self._checkStorageTemperatureGradient(data["stratified_storage"].loc["thermalStorage", "temp_c"]):
                    raise ValueError('Temperature Gradient in each layer of the thermal storage is not equal')
            except AttributeError:
                logging.error("The column temp_h of stratified_storage excel sheet should contain comma separated temperatures"
                              "when temperatureLevels is set to True. The temperatures should be ordered starting from low"
                              "to high and the label of storage should be thermalStorage.")
            self.__temperatureSH = self.__operationTemperatures[0]
            self.__temperatureDHW = self.__operationTemperatures[-1]
        else:
            self.__temperatureSH = data["stratified_storage"].loc["shStorage", "temp_h"]
            self.__temperatureDHW = data["stratified_storage"].loc["dhwStorage", "temp_h"]
            self.__operationTemperatures = [self.__temperatureSH, self.__temperatureDHW]
        # Transformers conversion factors input power - output power
        if any(data["transformers"]["label"] == "CHP"):
            self.__chpEff = float(data["transformers"][data["transformers"]["label"] == "CHP"]["efficiency"].iloc[0].split(",")[1])
        if any(data["transformers"]["label"] == "HP"):
            self.__hpEff = float(data["transformers"][data["transformers"]["label"] == "HP"]["efficiency"].iloc[0])
        if any(data["transformers"]["label"] == "GWHP"):
            self.__gwhpEff = float(data["transformers"][data["transformers"]["label"] == "GWHP"]["efficiency"].iloc[0])
        if any(data["transformers"]["label"] == "GasBoiler"):
            self.__gbEff = float(data["transformers"][data["transformers"]["label"] == "GasBoiler"]["efficiency"].iloc[0].split(",")[0])
        if any(data["transformers"][data["transformers"]["label"]=="ElectricRod"]["active"] == 1):
            self.__elRodEff = float(data["transformers"][data["transformers"]["label"] == "ElectricRod"]["efficiency"].iloc[0])
        if any(data["transformers"]["label"] == "Chiller"):
            self.__chillerEff = float(data["transformers"][data["transformers"]["label"] == "Chiller"]["efficiency"].iloc[0])
        # Storage conversion L - kWh to display the L value
        if self._temperatureLevels:
            self.__Ltank = self._rho * self._c * (self.__operationTemperatures[1] - self.__operationTemperatures[0]) / 3600
        else:
            self.__LgenericStorage = {}
            self.__Lsh = self._rho * self._c * (self.__temperatureSH - data["stratified_storage"].loc["shStorage", "temp_c"]) / 3600
            self.__Ldhw = self._rho * self._c * (self.__temperatureDHW - data["stratified_storage"].loc["dhwStorage", "temp_c"]) / 3600
            if 'tankStorage' in data['storages']['label'].unique():
                self.__LgenericStorage['tankStorage'] = self._rho * self._c * (data["stratified_storage"].loc["tankStorage", "temp_h"] - data["stratified_storage"].loc["tankStorage", "temp_c"]) / 3600 #TO BE IMPROVED
            if 'pitStorage' in data['storages']['label'].unique():
                self.__LgenericStorage['pitStorage'] = self._rho * self._c * (data["stratified_storage"].loc["pitStorage", "temp_h"] - data["stratified_storage"].loc["pitStorage", "temp_c"]) / 3600
            if 'boreholeStorage' in data['storages']['label'].unique():
                self.__LgenericStorage['boreholeStorage'] = self._rho * self._c * (data["stratified_storage"].loc["boreholeStorage", "temp_h"] - data["stratified_storage"].loc["boreholeStorage", "temp_c"]) / 3600
            if 'aquifierStorage' in data['storages']['label'].unique():
                self.__LgenericStorage['aquifierStorage'] = self._rho * self._c * (data["stratified_storage"].loc["aquifierStorage", "temp_h"] - data["stratified_storage"].loc["aquifierStorage", "temp_c"]) / 3600
        self._addBuildings(data, opt, mergeLinkBuses, mergeBuses, mergeHeatSourceSink, includeCarbonBenefits, clusterSize)

    def _addBuildings(self, data, opt, mergeLinkBuses, mergeBuses, mergeHeatSourceSink, includeCarbonBenefits, clusterSize):
        numberOfBuildings = max(data["buses"]["building"])
        self.__buildings = [Building('Building' + str(i + 1)) for i in range(numberOfBuildings)]
        for b in self.__buildings:
            buildingLabel = b.getBuildingLabel()
            i = int(buildingLabel[8:])
            if mergeLinkBuses: b.linkBuses(busesToMerge=mergeBuses)
            if i == 1:
                busDictBuilding1 = b.addBus(data["buses"][data["buses"]["building"] == i], opt, mergeLinkBuses, mergeHeatSourceSink, data["electricity_impact"], clusterSize, includeCarbonBenefits)
            else:
                b.addBus(data["buses"][data["buses"]["building"] == i], opt, mergeLinkBuses, mergeHeatSourceSink, data["electricity_impact"], clusterSize, includeCarbonBenefits)
            if (mergeLinkBuses or mergeHeatSourceSink) and i!=1:
                if mergeLinkBuses: merge = 'links'
                if mergeHeatSourceSink: merge = 'heatSourceSink'
                b.addToBusDict(busDictBuilding1, merge)
            b.addGridSeparation(data["grid_connection"][data["grid_connection"]["building"] == i], mergeLinkBuses)
            if "natGas_cost" in data:
                natGasCost = data["natGas_cost"]
                natGasImpact = data["natGas_impact"]
            else:
                natGasCost = natGasImpact = None
            b.addSource(data["commodity_sources"][data["commodity_sources"]["building"] == i], data["electricity_impact"], data["electricity_cost"], natGasCost, natGasImpact, opt, mergeHeatSourceSink)
            if i in data["building_model"]:
                bmdata = data["building_model"][i]
            else:
                bmdata = {}
            b.addSink(data["demand"][data["demand"]["building"] == i], data["demandProfiles"][i], bmdata, mergeLinkBuses, mergeHeatSourceSink, self._temperatureLevels)
            b.addTransformer(data["transformers"][data["transformers"]["building"] == i], self.__operationTemperatures, self.__temperatureAmb, self.__temperatureGround, opt, mergeLinkBuses, mergeHeatSourceSink, self._dispatchMode, self._temperatureLevels)
            storageList = b.addStorage(data["storages"][data["storages"]["building"] == i], data["stratified_storage"], opt, mergeLinkBuses, self._dispatchMode, self._temperatureLevels)
            b.addSolar(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"] == "solarCollector")], data["weather_data"], opt, mergeLinkBuses, self._dispatchMode, self._temperatureLevels)
            b.addPV(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"] == "pv")], data["weather_data"], opt, self._dispatchMode)
            b.addPVT(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"] == "pvt")], data["weather_data"], opt, mergeLinkBuses, self._dispatchMode)
            self._nodesList.extend(b.getNodesList())
            self._thermalStorageList.extend(storageList)
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
                 optConstraints=None, #optional constraints (implemented for the moment are "roof area"
                 mergeLinkBuses=False):

        if options is None:
            options = {"gurobi": {"MIPGap": 0.01}}

        self._optimizationModel = solph.Model(self)
        logging.info("Optimization model built successfully")

        # add constraint to limit the environmental impacts
        self._optimizationModel, flows, transformerFlowCapacityDict, storageCapacityDict = environmentalImpactlimit(
            self._optimizationModel, keyword1="env_per_flow", keyword2="env_per_capa", limit=envImpactlimit)

        if self._temperatureLevels:
            # add constraint on storage volume capacity
            self._optimizationModel = multiTemperatureStorageCapacityConstaint(self._optimizationModel, self._thermalStorageList, self._optimizationType)

        # optional constraints (available: 'roof area')
        if optConstraints:
            for c in optConstraints:
                if c.lower() == "roof area":
                    # requires 2 additional parameters in the scenario file, tab "solar", zenit angle, roof area
                    try:
                        self._optimizationModel = roof_area_limit(self._optimizationModel,
                                                        keyword1="space", keyword2="roof_area", nb=numberOfBuildings)
                        logging.info(f"Optional constraint {c} successfully added to the optimization model")
                    except ValueError:
                        logging.error(f"Optional constraint {c} not added to the optimization model : "
                                      f"please check if PV efficiency, roof area and zenith angle are present in input "
                                      f"file")
                        pass
                if c.lower() == 'totalpvcapacity':
                    self._optimizationModel = totalPVCapacityConstraint(self._optimizationModel, numberOfBuildings)
                    logging.info(f"Optional constraint {c} successfully added to the optimization model")
        # constraint on elRod combined with HPs:
        if not np.isnan(self.__elRodEff):
            self._optimizationModel = electricRodCapacityConstaint(self._optimizationModel, numberOfBuildings)
        # constraint on PVT capacity if PVT technology is selected
        if any("pvt" in n.label for n in self.nodes):
            self._optimizationModel = PVTElectricalThermalCapacityConstraint(self._optimizationModel, numberOfBuildings)
        # constraint on storage content for clustering
        """if clusterSize:
            self._optimizationModel = dailySHStorageConstraint(self._optimizationModel)"""

        logging.info("Custom constraints successfully added to the optimization model")
        logging.info("Initiating optimization using {} solver".format(solver))

        if solver == 'glpk':
            self._optimizationModel.solve(solver=solver)
        elif solver == 'cbc':
            self._optimizationModel.solve(solver=solver, solve_kwargs=options[solver])
        elif solver == 'gurobi':
            self._optimizationModel.solve(solver=solver, cmdline_options=options[solver])

        # obtain the value of the environmental impact (subject to the limit constraint)
        # the optimization imposes an integral limit constraint on the environmental impacts
        # total environmental impacts <= envImpactlimit
        envImpact = self._optimizationModel.totalEnvironmentalImpact()

        self._optimizationResults = solph.processing.results(self._optimizationModel, remove_last_time_point=True)
        self._metaResults = solph.processing.meta_results(self._optimizationModel)
        logging.info("Optimization successful and results collected")

        # calculate capacities invested for transformers and storages (for the entire energy network and per building)
        capacitiesTransformersNetwork, capacitiesStoragesNetwork = self._calculateInvestedCapacities(self._optimizationModel, transformerFlowCapacityDict, storageCapacityDict)

        if clusterSize:
            self._postprocessingClusters(clusterSize)

        # calculate results (CAPEX, OPEX, FeedIn Costs, environmental impacts etc...) for each building
        self._calculateResultsPerBuilding(mergeLinkBuses)

        return envImpact, capacitiesTransformersNetwork, capacitiesStoragesNetwork

    def printbuildingModelTemperatures(self, filename):
        df = pd.DataFrame()
        df["timestamp"] = self.timeindex
        for i in range(self.__noOfBuildings):
            bNo = i + 1
            tIndoor = [v for k, v in self._optimizationModel.SinkRCModelBlock.tIndoor.get_values().items() if
                       k[0].label.endswith(f"Building{bNo}")]
            tDistribution = [v for k, v in self._optimizationModel.SinkRCModelBlock.tDistribution.get_values().items() if
                             k[0].label.endswith(f"Building{bNo}")]
            tWall = [v for k, v in self._optimizationModel.SinkRCModelBlock.tWall.get_values().items() if
                     k[0].label.endswith(f"Building{bNo}")]
            epsilonIndoor = [v for k, v in self._optimizationModel.SinkRCModelBlock.epsilonIndoor.get_values().items() if
                             k[0].label.endswith(f"Building{bNo}")]
            tIndoor_prev = [v for k, v in self._optimizationModel.SinkRCModelBlock.tIndoor_prev.get_values().items() if
                            k[0].label.endswith(f"Building{bNo}")]
            tDistribution_prev = [v for k, v in
                                  self._optimizationModel.SinkRCModelBlock.tDistribution_prev.get_values().items() if
                                  k[0].label.endswith(f"Building{bNo}")]
            tWall_prev = [v for k, v in self._optimizationModel.SinkRCModelBlock.tWall_prev.get_values().items() if
                          k[0].label.endswith(f"Building{bNo}")]
            df[f"tIndoor_B{bNo}"] = tIndoor
            df[f"tDistribution_B{bNo}"] = tDistribution
            df[f"tWall_B{bNo}"] = tWall
            df[f"tIndoor_prev_B{bNo}"] = tIndoor_prev
            df[f"tDistribution_prev_B{bNo}"] = tDistribution_prev
            df[f"tWall_prev_B{bNo}"] = tWall_prev
            df[f"epsilonIndoor_B{bNo}"] = epsilonIndoor
        df.to_csv(filename, sep=';', index=False)

    def saveUnprocessedResults(self, resultFile):
        with pd.ExcelWriter(resultFile) as writer:
            busLabelList = []
            for i in self.nodes:
                if str(type(i)).replace("<class 'oemof.solph.", "").replace("'>", "") == "network.bus.Bus":
                    busLabelList.append(i.label)
            for i in busLabelList:
                result = pd.DataFrame.from_dict(solph.views.node(self._optimizationResults, i)["sequences"])
                result.to_excel(writer, sheet_name=i)
            writer.save()

    def _updateCapacityDictInputInvestment(self, transformerFlowCapacityDict):
        components = ["CHP", "GWHP", "HP", "GasBoiler", "ElectricRod", "Chiller"]
        for inflow, outflow in list(transformerFlowCapacityDict):
            index = (inflow, outflow)
            if "__" in str(inflow):
                buildingLabel = str(inflow).split("__")[1]
            elif "__" in str(outflow):
                buildingLabel = str(outflow).split("__")[1]
            if any(c in str(outflow) for c in components):
                if "Chiller" in str(outflow):
                    newoutFlow = f"heatSinkBus__{buildingLabel}"
                elif self._temperatureLevels:
                    newoutFlow = f"heatStorageBus0__{buildingLabel}"
                else:
                    newoutFlow = f"shSourceBus__{buildingLabel}"
                newIndex = (outflow,newoutFlow)
                transformerFlowCapacityDict[newIndex] = transformerFlowCapacityDict.pop(index)
            if 'elSource_pvt' in str(inflow):   # remove PVT electrical capacity
                transformerFlowCapacityDict.pop(index)
        return transformerFlowCapacityDict

    def _calculateInvestedCapacities(self, optimizationModel, transformerFlowCapacityDict, storageCapacityDict):
        capacitiesInvestedTransformers = {}
        capacitiesInvestedStorages = {}
        storageList = []

        # Transformers capacities

        for inflow, outflow in transformerFlowCapacityDict:
            index = (str(inflow), str(outflow))
            if (inflow, outflow) in optimizationModel.InvestmentFlowBlock.invest:
                capacitiesInvestedTransformers[index] = optimizationModel.InvestmentFlowBlock.invest[
                    inflow, outflow].value
            else:
                capacitiesInvestedTransformers[index] = optimizationModel.InvestNonConvexFlowBlock.invest[
                    inflow, outflow].value

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

        removeKeysList = []
        if self._temperatureLevels:
            if any("thermalStorage" in key for key in capacitiesInvestedStorages):
                for b in range(len(self.__buildings)):
                    buildingLabel = "Building" + str(b + 1)
                    invest = 0
                    for layer in self.__operationTemperatures:
                        if f"thermalStorage{int(layer)}__" + buildingLabel in capacitiesInvestedStorages:
                            invest += capacitiesInvestedStorages[f"thermalStorage{int(layer)}__" + buildingLabel]
                            removeKeysList.append(f"thermalStorage{int(layer)}__" + buildingLabel)
                    if invest > 0:
                        capacitiesInvestedStorages["thermalStorage__" + buildingLabel] = invest
                        storageCapacityDict["thermalStorage__" + buildingLabel] = invest
                        for k in removeKeysList:
                            capacitiesInvestedStorages.pop(k, None)

        # Update capacities
        for x in storageCapacityDict:
            index = str(x)
            if index in removeKeysList:
                continue
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
                            if ("shSource" in t.label and not self._temperatureLevels) or ("heatStorageBus0" in t.label and self._temperatureLevels):
                                capacitiesTransformers[(second,t.label)]= capacitiesTransformers[(first,second)]*self.__chpEff
                                del capacitiesTransformers[(first,second)]
            elif "GWHP" in second and not any([c.isdigit() for c in second.split("__")[0]]):  # second condition added for splitted GSHPs
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if (("shSource" in t.label or "shDemandBus" in t.label) and not self._temperatureLevels) or ("heatStorageBus0" in t.label and self._temperatureLevels):
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(first, second)] * self.__gwhpEff
                                del capacitiesTransformers[(first, second)]
            elif "HP" in second and "GWHP" not in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if ("shSource" in t.label and not self._temperatureLevels) or ("heatStorageBus0" in t.label and self._temperatureLevels):
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(first, second)]*self.__hpEff
                                del capacitiesTransformers[(first, second)]
            elif "GasBoiler" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if ("shSource" in t.label and not self._temperatureLevels) or ("heatStorageBus0" in t.label and self._temperatureLevels):
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(
                                first, second)] * self.__gbEff
                                del capacitiesTransformers[(first, second)]
            elif "ElectricRod" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].conversion_factors
                        for t in test.keys():
                            if ("shSource" in t.label and not self._temperatureLevels) or ("heatStorageBus0" in t.label and self._temperatureLevels):
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(
                                first, second)] * self.__elRodEff
                                del capacitiesTransformers[(first, second)]
            elif "Chiller" in second:
                for index, value in enumerate(self.nodes):
                    if second == value.label:
                        test = self.nodes[index].outputs
                        for t in test.keys():
                            if "heatSink" in t.label:
                                capacitiesTransformers[(second, t.label)] = capacitiesTransformers[(first, second)] * self.__chillerEff
                                del capacitiesTransformers[(first, second)]
        return capacitiesTransformers

    def _compensateStorageCapacities(self, capacitiesStorages):
        # kWh -> L
        for storage in capacitiesStorages.keys():
            if "sh" in storage:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__Lsh
            elif "dhw" in storage:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__Ldhw
            elif "thermal" in storage and self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__Ltank
            elif "tank" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['tankStorage']
            elif "pitStorage" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['pitStorage']
            elif "borehole" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['boreholeStorage']
            elif "aquifier" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['aquifierStorage']
        return capacitiesStorages

    def _postprocessingClusters(self, clusterSize):
        flows = [x for x in self._optimizationResults.keys() if x[1] is not None]
        for flow in flows:
            extrapolated_results = None
            for day in clusterSize:
                temp = pd.concat([self._optimizationResults[flow]['sequences'].loc[self._clusterDate[day]]] * clusterSize[day])
                if extrapolated_results is not None:
                    extrapolated_results = pd.concat([extrapolated_results, temp])
                else:
                    extrapolated_results = temp
            extrapolated_results.index = self._timeIndexReal
            extrapolated_results.columns = ['flow']
            self._optimizationResults[flow]['sequences'] = extrapolated_results

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
            naturalGasSourceLabel = "naturalGasResource" + '__' + buildingLabel
            naturalGasBusLabel = "naturalGasBus" + '__' + buildingLabel
            if mergeLinkBuses:
                electricityBusLabel = "electricityBus"
                excessElectricityBusLabel = "excesselectricityBus"
            else:
                electricityBusLabel = "electricityBus" + '__' + buildingLabel
                excessElectricityBusLabel = "excesselectricityBus" + '__' + buildingLabel

            if electricitySourceLabel in self.__costParam:
                costParamGridElectricity = self.__costParam[electricitySourceLabel].copy()
                costParamGridElectricity.reset_index(inplace=True, drop=True)
            else:
                costParamGridElectricity = 0

            if naturalGasSourceLabel in self.__costParam:
                costParamNaturalGas = self.__costParam[naturalGasSourceLabel].copy()
                costParamNaturalGas.reset_index(inplace=True, drop=True)
            else:
                costParamNaturalGas = 0

            if "sequences" in solph.views.node(self._optimizationResults, gridBusLabel):
                if ((electricitySourceLabel, gridBusLabel), "flow") in solph.views.node(self._optimizationResults, gridBusLabel)["sequences"]:
                    gridElectricityFlow = solph.views.node(self._optimizationResults, gridBusLabel)["sequences"][
                        (electricitySourceLabel, gridBusLabel), "flow"]
                    gridElectricityFlow.reset_index(inplace=True, drop=True)
                else:
                    gridElectricityFlow = 0
            else:
                gridElectricityFlow = 0

            if "sequences" in solph.views.node(self._optimizationResults, naturalGasBusLabel):
                if ((naturalGasSourceLabel, naturalGasBusLabel), "flow") in solph.views.node(self._optimizationResults, naturalGasBusLabel)["sequences"]:
                    naturalGasFlow = solph.views.node(self._optimizationResults, naturalGasBusLabel)["sequences"][
                        (naturalGasSourceLabel, naturalGasBusLabel), "flow"]
                    naturalGasFlow.reset_index(inplace=True, drop=True)
                else:
                    naturalGasFlow = 0
            else:
                naturalGasFlow = 0

            # OPeration EXpenditure
            self.__opex[buildingLabel].update({i[0]: sum(
                solph.views.node(self._optimizationResults, i[1])["sequences"][(i[0], i[1]), "flow"] * self.__costParam[
                    i[0]]) for i in inputs})
            c = costParamGridElectricity * gridElectricityFlow
            if isinstance(c, (int, float)):
                self.__opex[buildingLabel].update({electricitySourceLabel:c})
            else:
                self.__opex[buildingLabel].update({electricitySourceLabel: c.sum()})  # cost of grid electricity is added separately based on cost data

            c = costParamNaturalGas * naturalGasFlow
            if isinstance(c, (int, float)):
                self.__opex[buildingLabel].update({naturalGasSourceLabel: c})
            else:
                self.__opex[buildingLabel].update({naturalGasSourceLabel: c.sum()})  # cost of natural gas is added separately based on cost data

            # Feed-in electricity cost (value will be in negative to signify monetary gain...)
            if ((mergeLinkBuses and buildingLabel=='Building1') or not mergeLinkBuses) and \
                    (((electricityBusLabel, excessElectricityBusLabel), "flow") in solph.views.node(self._optimizationResults, electricityBusLabel)["sequences"]):
                self.__feedIn[buildingLabel] = sum(solph.views.node(self._optimizationResults, electricityBusLabel)
                                                   ["sequences"][(electricityBusLabel, excessElectricityBusLabel), "flow"]) * self.__costParam[excessElectricityBusLabel]
            else: # in case of merged links feed in for all buildings except Building1 is set to 0 (to avoid repetition)
                self.__feedIn[buildingLabel] = 0
            if mergeLinkBuses:
                elInBusLabel = 'electricityInBus'
            else:
                elInBusLabel = 'electricityInBus__'+buildingLabel
            if self._temperatureLevels:
                shOutputLabel = "heatStorageBus0__"
                dhwOutputLabel = f"heatStorageBus{len(self.__operationTemperatures)-1}__"
            else:
                shOutputLabel = "shSourceBus__"
                dhwOutputLabel = "dhwStorageBus__"

            # HP flows
            if ("HP__" + buildingLabel, shOutputLabel + buildingLabel) in capacityTransformers:
                if capacityTransformers[("HP__" + buildingLabel, shOutputLabel + buildingLabel)] > 1e-3:
                    self.__elHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, elInBusLabel)["sequences"][
                            (elInBusLabel, 'HP__'+buildingLabel), 'flow'])
                    self.__shHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, 'HP__' + buildingLabel)["sequences"][
                            ('HP__' + buildingLabel, shOutputLabel + buildingLabel), 'flow'])
                    for i in range(len(self.__operationTemperatures)-2):
                        self.__intermediateOpTempsHP[buildingLabel] = sum(
                            solph.views.node(self._optimizationResults, 'HP__' + buildingLabel)["sequences"][
                                ('HP__' + buildingLabel, f"heatStorageBus{i+1}__{buildingLabel}"), 'flow'])
                    self.__dhwHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, 'HP__' + buildingLabel)["sequences"][
                            ('HP__' + buildingLabel, dhwOutputLabel + buildingLabel), 'flow'])
                    self.__annualCopHP[buildingLabel] = (self.__shHP[buildingLabel] + self.__dhwHP[buildingLabel]) / (
                        self.__elHP[buildingLabel] + 1e-6)
                else:
                    self.__annualCopHP[buildingLabel] = 0

            # GWHP flows
            if ("GWHP__" + buildingLabel, shOutputLabel + buildingLabel) in capacityTransformers:
                if capacityTransformers[("GWHP__" + buildingLabel, shOutputLabel + buildingLabel)] > 1e-3:
                    self.__elGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, elInBusLabel)["sequences"][
                            (elInBusLabel, 'GWHP__' + buildingLabel), 'flow'])
                    self.__shGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, 'GWHP__' + buildingLabel)["sequences"][
                            ('GWHP__' + buildingLabel, shOutputLabel + buildingLabel), 'flow'])
                    for i in range(len(self.__operationTemperatures)-2):
                        self.__intermediateOpTempsGWHP[buildingLabel] = sum(
                            solph.views.node(self._optimizationResults, 'GWHP__' + buildingLabel)["sequences"][
                                ('GWHP__' + buildingLabel, f"heatStorageBus{i+1}__{buildingLabel}"), 'flow'])
                    self.__dhwGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, 'GWHP__' + buildingLabel)["sequences"][
                            ('GWHP__' + buildingLabel, dhwOutputLabel + buildingLabel), 'flow'])
                    self.__annualCopGWHP[buildingLabel] = (self.__shGWHP[buildingLabel] + self.__dhwGWHP[buildingLabel]) / (
                            self.__elGWHP[buildingLabel] + 1e-6)
                else:
                    self.__annualCopGWHP[buildingLabel] = 0
            else:       # splitted GSHP ( at the moment this only works at 2 temperature levels)
                self.__annualCopGWHP[buildingLabel] = []
                if (f"GWHP{str(self.__temperatureSH)}__" + buildingLabel, shOutputLabel + buildingLabel) in capacityTransformers:
                    self.__elGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, elInBusLabel)["sequences"][
                            (elInBusLabel, f"GWHP{str(self.__temperatureSH)}__" + buildingLabel), 'flow'])
                    self.__shGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, f"GWHP{str(self.__temperatureSH)}__" + buildingLabel)["sequences"][
                            (f"GWHP{str(self.__temperatureSH)}__" + buildingLabel, shOutputLabel + buildingLabel), 'flow'])
                    self.__annualCopGWHP[buildingLabel].append((self.__shGWHP[buildingLabel]) / (self.__elGWHP[buildingLabel] + 1e-6))
                if (f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel, dhwOutputLabel + buildingLabel) in capacityTransformers:
                    self.__elGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, elInBusLabel)["sequences"][
                            (elInBusLabel, f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel), 'flow'])
                    self.__dhwGWHP[buildingLabel] = sum(
                        solph.views.node(self._optimizationResults, f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel)["sequences"][
                            (f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel, dhwOutputLabel + buildingLabel), 'flow'])
                    self.__annualCopGWHP[buildingLabel].append((self.__dhwGWHP[
                        buildingLabel]) / (self.__elGWHP[buildingLabel] + 1e-6))

            if electricitySourceLabel in self.__envParam:
                envParamGridElectricity = self.__envParam[electricitySourceLabel].copy()
                envParamGridElectricity.reset_index(inplace=True, drop=True)
            else:
                envParamGridElectricity = 0

            if naturalGasSourceLabel in self.__envParam:
                envParamNaturalGas = self.__envParam[naturalGasSourceLabel].copy()
                envParamNaturalGas.reset_index(inplace=True, drop=True)
            else:
                envParamNaturalGas = 0
            
            # Environmental impact due to inputs (natural gas, electricity, etc...)
            self.__envImpactInputs[buildingLabel].update({i[0]: sum(solph.views.node(self._optimizationResults, i[1])["sequences"][(i[0], i[1]), "flow"] * self.__envParam[i[0]]) for i in inputs})
            c = envParamGridElectricity * gridElectricityFlow
            if isinstance(c, (int, float)):
                self.__envImpactInputs[buildingLabel].update({electricitySourceLabel: c})
            else:
                self.__envImpactInputs[buildingLabel].update({electricitySourceLabel: c.sum()})  # impact of grid electricity is added separately based on LCA data

            c = envParamNaturalGas * naturalGasFlow
            if isinstance(c, (int, float)):
                self.__envImpactInputs[buildingLabel].update({naturalGasSourceLabel: c})
            else:
                self.__envImpactInputs[buildingLabel].update({naturalGasSourceLabel: c.sum()})  # impact of natural gas is added separately

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
                                                                for x in capacityStorages if "thermalStorage" not in x})
            if self._temperatureLevels:
                impactThermalStorage = 0
                for x in capacityStorages:
                    if "thermalStorage" in x:
                        impactThermalStorage += capacityStorages[x] * self.__envParam["thermalStorage__"+x.split("__")[1]][2] + \
                                                                   sum(sum(
                                                                       solph.views.node(self._optimizationResults,
                                                                                        t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                       self.__envParam["thermalStorage__"+x.split("__")[1]][1] * ('electricityBus' in t[0]) + \
                                                                       solph.views.node(self._optimizationResults,
                                                                                        t[0])["sequences"][((t[1], t[0]), "flow")] *
                                                                       self.__envParam["thermalStorage__"+x.split("__")[1]][0] * ('electricityBus' not in t[0]))
                                                                       for t in technologies if (x.split("__")[0] in t[1].split("__")[0]
                                                                                                 and x.split("__")[1] == t[1].split("__")[1]))
                        self.__envImpactTechnologies[buildingLabel].update({x: impactThermalStorage})

    def printMetaresults(self):
        print("")
        print("Meta Results:")
        pp.pprint(self._metaResults)
        return self._metaResults

    def calcStateofCharge(self, type, building):
        if "thermalStorage" in type:
            for i,temperature in enumerate(self.__operationTemperatures):
                thermal_type = type + str(temperature)[:2]
                if thermal_type + '__' + building in self.groups:
                    storage = self.groups[thermal_type + '__' + building]
                    self._storageContent.setdefault(building, {})[thermal_type] = self._optimizationResults[(storage, None)]["sequences"]
                if temperature == self.__operationTemperatures[-1]:
                    lists = np.array(list(self._storageContent[building].values()))
                    # Calculate the sum of corresponding elements in the arrays
                    sums = np.sum(lists, axis=0)
                    self._storageContent[building][thermal_type][f'Overall_storage_content_{building}'] = sums
        elif type + '__' + building in self.groups:
            storage = self.groups[type + '__' + building]
            self._storageContent[building] = self._optimizationResults[(storage, None)]["sequences"]
        return self._storageContent

    def printInvestedCapacities(self, capacitiesInvestedTransformers, capacitiesInvestedStorages):
        if self._temperatureLevels:
            shOutputLabel = "heatStorageBus0__"
        else:
            shOutputLabel = "shSourceBus__"
        for b in range(len(self.__buildings)):
            buildingLabel = "Building" + str(b + 1)
            print("************** Optimized Capacities for {} **************".format(buildingLabel))
            if ("HP__" + buildingLabel, shOutputLabel + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[("HP__" + buildingLabel, shOutputLabel + buildingLabel)]
                if investSH > 0.05:
                    print("Invested in {:.1f} kW HP.".format(investSH))
                    print("     Annual COP = {:.1f}".format(self.__annualCopHP[buildingLabel]))
            if ("GWHP__" + buildingLabel, shOutputLabel + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[("GWHP__" + buildingLabel, shOutputLabel + buildingLabel)]
                if investSH > 0.05:
                    print("Invested in {:.1f} kW GWHP.".format(investSH))
                    print("     Annual COP = {:.1f}".format(self.__annualCopGWHP[buildingLabel]))
            if (f"GWHP{str(self.__temperatureSH)}__" + buildingLabel, shOutputLabel + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[(f"GWHP{str(self.__temperatureSH)}__" + buildingLabel, shOutputLabel + buildingLabel)]
                if investSH > 0.05:
                    print("Invested in {:.1f} kW GWHP{}.".format(investSH, str(self.__temperatureSH)))
                    print("     Annual COP = {:.1f}".format(self.__annualCopGWHP[buildingLabel][0]))
            if (f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel, "dhwStorageBus__" + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[(f"GWHP{str(self.__temperatureDHW)}__" + buildingLabel, "dhwStorageBus__" + buildingLabel)]
                if investSH > 0.05:
                    print("Invested in {:.1f} kW GWHP{}.".format(investSH, str(self.__temperatureDHW)))
                    print("     Annual COP = {:.1f}".format(self.__annualCopGWHP[buildingLabel][1]))
            if ("ElectricRod__" + buildingLabel, shOutputLabel + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers[("ElectricRod__" + buildingLabel, shOutputLabel + buildingLabel)]
                if investSH > 0.05:
                    print("Invested in {:.1f} kW Electric Rod.".format(investSH))
            if ("CHP__" + buildingLabel, shOutputLabel + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers["CHP__" + buildingLabel, shOutputLabel + buildingLabel]
                if investSH > 0.05:
                    print("Invested in {:.1f} kW CHP.".format(investSH))  # + investEL))
            if ("GasBoiler__" + buildingLabel, shOutputLabel + buildingLabel) in capacitiesInvestedTransformers:
                investSH = capacitiesInvestedTransformers["GasBoiler__" + buildingLabel, shOutputLabel + buildingLabel]
                if investSH > 0.05:
                    print("Invested in {:.1f} kW GasBoiler.".format(investSH))
            if ("heat_solarCollector__" + buildingLabel, "solarConnectBus__" + buildingLabel) in capacitiesInvestedTransformers:
                invest = capacitiesInvestedTransformers[("heat_solarCollector__" + buildingLabel, "solarConnectBus__" + buildingLabel)]
                if invest > 0.05:
                    print("Invested in {:.1f} m² SolarCollector.".format(invest))
            if ("pv__" + buildingLabel, "electricityProdBus__" + buildingLabel) in capacitiesInvestedTransformers:
                invest = capacitiesInvestedTransformers[("pv__" + buildingLabel, "electricityProdBus__" + buildingLabel)]
                if invest > 0.05:
                    print("Invested in {:.1f} kWp  PV.".format(invest))
            if ("heatSource_SHpvt__" + buildingLabel, "pvtConnectBusSH__" + buildingLabel) in capacitiesInvestedTransformers:
                if invest > 0.05:
                    invest = capacitiesInvestedTransformers[("heatSource_SHpvt__" + buildingLabel, "pvtConnectBusSH__" + buildingLabel)]
                    print("Invested in {:.1f} m² PVT collector.".format(invest))
            if "electricalStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["electricalStorage__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} kWh Electrical Storage.".format(invest))
            if "dhwStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["dhwStorage__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L DHW Storage Tank.".format(invest))
            if "dhwStorage1__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["dhwStorage1__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L DHW Storage1 Tank.".format(invest))
            if "shStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["shStorage__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L SH Storage Tank.".format(invest))
            if "thermalStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["thermalStorage__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L Multilayer Thermal Storage Tank.".format(invest))
            if "tankStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["tankStorage__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L Generic Storage.".format(invest))
            if "pitStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["pitStorage__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L Pit Storage.".format(invest))
            if "pitStorage0__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["pitStorage0__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L Pit Storage 0.".format(invest))
            if "pitStorage1__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["pitStorage1__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L Pit Storage 1.".format(invest))
            if "pitStorage2__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["pitStorage2__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L Pit Storage 2.".format(invest))
            if "boreholeStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["boreholeStorage__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L Borehole Storage.".format(invest))
            if "aquifierStorage__" + buildingLabel in capacitiesInvestedStorages:
                invest = capacitiesInvestedStorages["aquifierStorage__" + buildingLabel]
                if invest > 0.05:
                    print("Invested in {:.1f} L Aquifier Storage.".format(invest))
            print("")

    def printCosts(self):
        capexNetwork = sum(self.__capex["Building" + str(b + 1)] for b in range(len(self.__buildings)))
        opexNetwork = sum(sum(self.__opex["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        feedinNetwork = sum(self.__feedIn["Building" + str(b + 1)] for b in range(len(self.__buildings)))
        print("Investment Costs for the system: {} CHF".format(capexNetwork))
        print("Operation Costs for the system: {} CHF".format(opexNetwork))
        print("Feed In Costs for the system: {} CHF".format(feedinNetwork))
        print("Total Costs for the system: {} CHF".format(capexNetwork + opexNetwork + feedinNetwork))

    def printEnvImpacts(self):
        envImpactInputsNetwork = sum(sum(self.__envImpactInputs["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        envImpactTechnologiesNetwork = sum(sum(self.__envImpactTechnologies["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        print("Environmental impact from input resources for the system: {} kg CO2 eq".format(envImpactInputsNetwork))
        print("Environmental impact from energy conversion and storage technologies for the system: {} kg CO2 eq".format(envImpactTechnologiesNetwork))
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
        hSB_sheet = [] #Special sheet for the merged heatStorageBus
        for i in range(1, self.__noOfBuildings+1):
            if self._temperatureLevels:
                self._storageContentTS = self.calcStateofCharge("thermalStorage", f"Building{i}")
            else:
                self._storageContentSH = self.calcStateofCharge("shStorage", f"Building{i}")
                self._storageContentDHW = self.calcStateofCharge("dhwStorage", f"Building{i}")
            hSB_sheet.append(f'heatStorageBus_Building{i}') #name of the different heatStorageBuses
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            busLabelList = []
            for i in self.nodes:
                if "buses._bus.Bus" in str(type(i)).replace("<oemof.solph.", "").replace("'>", ""):
                    busLabelList.append(i.label)
            # writing results of each bus into excel
            result_hSB = pd.DataFrame()
            hSB_building = 0
            for i in busLabelList:
                if "dummy" not in i: #don't print the dummy results anymore
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

                            if "heatStorageBus" in i and i.split("__")[1] in self._storageContentTS:
                                # result = result[result.columns[[0, 3]]]  # get rid of 'status' and 'status_nominal' columns
                                result_hSB = pd.concat([result_hSB, result], axis=1, sort=True)
                                # for j, temperature in enumerate(self.__operationTemperatures): #this was used for the intermediate storage content (layer by layer)
                                #     if f's{j}' in i.split("__")[0]:
                                #         result = pd.concat([result, self._storageContentTS[i.split("__")[1]][
                                #             f'thermalStorage{int(temperature)}']], axis=1, sort=True)
                                if f's{len(self.__operationTemperatures)-1}' in i.split("__")[0]: #if we are at the last storage layer, then add the overall storage content of the building
                                    result_hSB = pd.concat([result_hSB, self._storageContentTS[i.split("__")[1]][
                                             f'thermalStorage{int(self.__operationTemperatures[-1])}'][f'Overall_storage_content_{i.split("__")[1]}']], axis=1, sort=True)

                        else:
                            continue
                    result[result < 0.001] = 0      # to resolve the issue of very low values in the results in certain cases, values less than 1 Watt would be replaced by 0
                    if (mergeLinkBuses or "dhwStorageBus" not in i) and "heatStorageBus" not in i:
                        result.to_excel(writer, sheet_name=i)
                    elif f"heatStorageBus{len(self.__operationTemperatures)-1}" in i: #Special case for merging the heatStorageBuses (only if at the higher thermal layer)
                        result_hSB.to_excel(writer, sheet_name= hSB_sheet[hSB_building])
                        result_hSB = pd.DataFrame() #Clean the temporary heatStorageBus sheet
                        hSB_building += 1  # Prepare for the next building

            # writing the costs and environmental impacts (of different components...) for each building
            for b in self.__buildings:
                buildingLabel = b.getBuildingLabel()
                costs = self.__opex[buildingLabel]
                costs.update({"Investment": self.__capex[buildingLabel],
                              "Feed-in": self.__feedIn[buildingLabel]})

                costsBuilding = pd.DataFrame.from_dict(costs, orient='index')
                costsBuilding.to_excel(writer, sheet_name="costs__" + buildingLabel)

                envImpact = self.__envImpactInputs[buildingLabel].copy()
                envImpact.update(self.__envImpactTechnologies[buildingLabel])

                envImpactBuilding = pd.DataFrame.from_dict(envImpact, orient='index')
                envImpactBuilding.to_excel(writer, sheet_name="env_impacts__" + buildingLabel)

                capacitiesStorages = self.__capacitiesStoragesBuilding[buildingLabel].copy()
                capacitiesStorages.update(self.__capacitiesStoragesBuilding[buildingLabel])

                capacitiesStoragesBuilding = pd.DataFrame.from_dict(capacitiesStorages, orient='index')
                capacitiesStoragesBuilding.to_excel(writer, sheet_name="capStorages__" + buildingLabel)

                capacitiesTransformers = self.__capacitiesTransformersBuilding[buildingLabel].copy()
                capacitiesTransformers.update(self.__capacitiesTransformersBuilding[buildingLabel])

                capacitiesTransformersBuilding = pd.DataFrame.from_dict(capacitiesTransformers, orient='index')
                capacitiesTransformersBuilding.to_excel(writer, sheet_name="capTransformers__" + buildingLabel)

    def set_from_csv(self, input_data_dir: _pl.Path, nr_of_buildings: int, clusterSize={}, opt: str = "costs",
                   mergeLinkBuses: bool = False, mergeBuses: _tp.Optional[_tp.Sequence[str]] = None,
                   mergeHeatSourceSink: bool = False, dispatchMode: bool = False, includeCarbonBenefits: bool = False):
        self.check_dir_path(input_data_dir)
        self.check_mutually_exclusive_inputs(mergeLinkBuses)
        self._dispatchMode = dispatchMode
        self._optimizationType = opt
        logging.info(f"Defining the energy network from the input files: {input_data_dir}")

        csvReader = _re.CsvScenarioReader(input_data_dir)
        initial_nodal_data = csvReader.read_scenario()
        self.set_using_nodal_data(clusterSize, input_data_dir, includeCarbonBenefits, initial_nodal_data, mergeBuses,
                                  mergeHeatSourceSink, mergeLinkBuses, nr_of_buildings, opt)

    @staticmethod
    def check_dir_path(dir_path: _pl.Path):
        if not dir_path or not os.path.isdir(dir_path):
            logging.error(f"Directory {dir_path} not found.")


class EnergyNetworkIndiv(EnergyNetworkClass):
    # # sunsetted, please use parent instead
    # def createScenarioFile(self, configFilePath, excelFilePath, building, numberOfBuildings=1):
    #     # use new function instead
    #     # tell user it is being sunsetted.
    def __init__(self, timestamp):
        warnings.warn(f'"EnergyNetworkIndiv" will be sunsetted. Please use {__name__}.{EnergyNetworkClass.__name__} instead.')
        super().__init__(timestamp)

    @staticmethod
    def createScenarioFile(configFilePath, excelFilePath, building, numberOfBuildings):
        warnings.warn(f'"EnergyNetworkIndiv.createScenarioFile" will be sunsetted. Please use '
                      f'{_wr.__name__}.{_wr.ScenarioFileWriterExcel.__name__} or '
                      f'{_wr.__name__}.{_wr.ScenarioFileWriterCSV} instead.')

        scenarioFileWriter = _wr.ScenarioFileWriterExcel(configFilePath, building_nrs=building, version="individual")
        scenarioFileWriter.write(excelFilePath)


class EnergyNetworkGroup(EnergyNetworkClass):
    @staticmethod
    def createScenarioFile(configFilePath, excelFilePath, numberOfBuildings):
        warnings.warn(f'"EnergyNetworkGroup.createScenarioFile" will be sunsetted. Please use '
                      f'{_wr.__name__}.{_wr.ScenarioFileWriterExcel.__name__} or '
                      f'{_wr.__name__}.{_wr.ScenarioFileWriterCSV} instead.')

        scenarioFileWriter = _wr.ScenarioFileWriterExcel(configFilePath, nr_of_buildings=numberOfBuildings,
                                                         version="grouped")
        scenarioFileWriter.write(excelFilePath)

    def setFromExcel(self, filePath, numberOfBuildings, clusterSize={}, opt="costs", mergeLinkBuses=False, mergeBuses=None, mergeHeatSourceSink=False, dispatchMode=False, includeCarbonBenefits=False):
        # does Excel file exist?
        if not filePath or not os.path.isfile(filePath):
            logging.error("Excel data file {} not found.".format(filePath))
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        self._dispatchMode = dispatchMode
        self._optimizationType = opt
        data = pd.ExcelFile(filePath)
        initial_nodal_data = self.get_nodal_data_from_Excel(data)
        # data.close()
        nodesData = self.createNodesData(initial_nodal_data, filePath, numberOfBuildings, clusterSize)
        # nodesData["buses"]["excess costs"] = nodesData["buses"]["excess costs group"]
        # nodesData["electricity_cost"]["cost"] = nodesData["electricity_cost"]["cost group"]

        demandProfiles = {}
        if clusterSize:
            for i in range(1, numberOfBuildings + 1):
                demandProfiles[i] = pd.concat(
                    [nodesData["demandProfiles"][i].loc[d] for d in clusterSize.keys()])
            electricityImpact = pd.concat(
                [nodesData["electricity_impact"].loc[d]*clusterSize[d] for d in clusterSize.keys()])
            electricityCost = pd.concat(
                [nodesData["electricity_cost"].loc[d]*clusterSize[d] for d in clusterSize.keys()])
            if 'natGas_impact' in nodesData:
                natGasImpact = pd.concat(
                    [nodesData["natGas_impact"].loc[d]*clusterSize[d] for d in clusterSize.keys()])
                natGasCost = pd.concat(
                    [nodesData["natGas_cost"].loc[d]*clusterSize[d] for d in clusterSize.keys()])
            weatherData = pd.concat([nodesData['weather_data'][
                                         nodesData['weather_data']['time.mm'] == int(d.split('-')[1])][
                                         nodesData['weather_data']['time.dd'] == int(d.split('-')[2])][['gls', 'str.diffus', 'tre200h0', 'ground_temp']] for d in clusterSize.keys()])

            nodesData["demandProfiles"] = demandProfiles
            nodesData["electricity_impact"] = electricityImpact
            nodesData["electricity_cost"] = electricityCost
            if 'natGas_impact' in nodesData:
                nodesData["natGas_impact"] = natGasImpact
                nodesData["natGas_cost"] = natGasCost
            nodesData["weather_data"] = weatherData

        nodesData["links"]= data.parse("links")
        self._convertNodes(nodesData, opt, mergeLinkBuses, mergeBuses, mergeHeatSourceSink, includeCarbonBenefits, clusterSize)
        self._addLinks(nodesData["links"], numberOfBuildings, mergeLinkBuses)
        logging.info(f"Nodes from file {filePath} successfully converted")
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
                    elif "heat" in l["label"]:
                        busesOut.append(self._busDict["heatBus" + l["label"][-1] + '__Building' + str(b + 1)])
                        busesIn.append(self._busDict["heatDemandBus" + l["label"][-1] + '__Building' + str(b + 1)])
                    else:
                        busesOut.append(self._busDict["electricityBus" + '__Building' + str(b + 1)])
                        busesIn.append(self._busDict["electricityInBus" + '__Building' + str(b + 1)])

                self._nodesList.append(Link(
                    label=l["label"],
                    inputs={busA: solph.Flow() for busA in busesOut},
                    outputs={busB: solph.Flow(investment=investment) for busB in busesIn},
                    conversion_factors={busB: l["efficiency"] for busB in busesIn}
                ))