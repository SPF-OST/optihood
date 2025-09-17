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
import optihood.IO.readers as read

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from optihood.buildings import Building
from optihood.constraints import *
from optihood._helpers import *
from optihood.links import Link
import optihood.IO.readers as _re

# TODO: define nr_of_buildings once  # pylint: disable=fixme


class OptimizationProperties:
    """
    Configurable attributes of energy networks.
    """
    def __init__(self,
                 optimization_type: _tp.Literal["costs", "env"],  # Pycharm highlights the input if anything else.
                 merge_link_buses: bool = False,
                 merge_buses: _tp.Optional[_tp.Sequence[str]] = None,
                 merge_heat_source_sink: bool = False,
                 temperature_levels: bool = False,
                 cluster_size: _tp.Optional[dict[str, int]] = None,
                 dispatch_mode: bool = False,
                 include_carbon_benefits: bool = False
                 ) -> None:
        """
        # TODO: explain inputs
        Parameters
        ----------

        cluster_size:
            Used to provide a selected number of days which could be assumed representative of the entire time range.

        optimization_type:
            "cost", or "env" depending on which criteria should be optimized.

        merge_link_buses:
            False: one bus of provided type per building.
            True: all buildings use the same bus for each type.

        merge_buses:
            Specify which buses to merge when merge_link_buses set to True

        merge_heat_source_sink:

        temperature_levels:

        dispatch_mode:
            True: activate dispatch optimization
            False: do investment + dispatch optimization

        include_carbon_benefits:

        """
        self.optimization_type = optimization_type
        self.merge_link_buses = merge_link_buses
        self.merge_buses = merge_buses
        self.merge_heat_source_sink = merge_heat_source_sink
        self.temperature_levels = temperature_levels
        self.cluster_size = cluster_size
        self.dispatch_mode = dispatch_mode
        self.include_carbon_benefits = include_carbon_benefits

        self.check_mutually_exclusive_inputs()

    def check_mutually_exclusive_inputs(self):
        if self.merge_link_buses and self.temperature_levels:
            logging.error("The options merge_link_buses and temperature_levels should not be set True at the same time."
                          "This use case is not supported in the present version of optihood. Only one of "
                          "mergeLinkBuses and temperatureLevels should be set to True.")


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
        self._storageContentPIT = {}                # TODO: check and update the code for calculation of storage content for pit
        self._storageContent = {}
        self.__technology_efficiency = {}
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
        _pl.Path(".\\log_files").mkdir(parents=True, exist_ok=True)
        screen_format = "%(asctime)s-%(levelname)s:  %(message)s"
        logger.define_logging(screen_format=screen_format, logpath=os.getcwd(), logfile=f'.\\log_files\\optihood_{datetime.now().strftime("%d.%m.%Y %H.%M.%S")}.log')
        logging.info("Initializing the energy network")
        super(EnergyNetworkClass, self).__init__(timeindex=timestamp, infer_last_interval=True)

    def setFromExcel(self, filePath, numberOfBuildings, clusterSize={}, opt="costs", mergeLinkBuses=False, mergeBuses=None, mergeHeatSourceSink=False, dispatchMode=False, includeCarbonBenefits=False):
        self.check_file_path(filePath)
        self.check_mutually_exclusive_inputs(mergeLinkBuses)
        self._dispatchMode = dispatchMode
        self._optimizationType = opt
        self._mergeBuses = mergeBuses
        self.__noOfBuildings = numberOfBuildings
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        data = pd.ExcelFile(filePath)
        initial_nodal_data = self.get_nodal_data_from_Excel(data)
        data.close()
        other_data_reader = read.ProfileAndOtherDataReader()

        nodesData = other_data_reader.read_profiles_and_other_data(initial_nodal_data, filePath, numberOfBuildings, clusterSize,
                                                                   self.timeindex)
        self.set_using_nodal_data(clusterSize, filePath, includeCarbonBenefits, nodesData, mergeBuses,
                                  mergeHeatSourceSink, mergeLinkBuses, numberOfBuildings, opt)

    def set_using_nodal_data(self, clusterSize, filePath, includeCarbonBenefits, nodesData: dict[str, pd.DataFrame], mergeBuses,
                             mergeHeatSourceSink, mergeLinkBuses, numberOfBuildings, opt,
                             grouped_network: bool = False
                             ):
        if grouped_network and not isinstance(self, EnergyNetworkGroup):
            logging.error(f"'grouped_network' flag should not be used without using {EnergyNetworkGroup.__name__}.")

        self._convertNodes(nodesData, opt, mergeLinkBuses, mergeBuses, mergeHeatSourceSink, includeCarbonBenefits,
                           clusterSize)
        logging.info("Nodes from {} successfully converted".format(filePath))

        if grouped_network:
            assert isinstance(self, EnergyNetworkGroup)
            self._addLinks(nodesData["links"], numberOfBuildings, mergeLinkBuses)
            logging.info("Links successfully added to the energy network")

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
            _ent.NodeKeys.profiles.value: func(data, _ent.NodeKeys.profiles.value),
        }

        try:
            # This sheet is usually not included for single buildings.
            nodes_data[_ent.NodeKeys.links.value] = func(data, _ent.NodeKeys.links.value)
        except:  # multiple exceptions possible, each of which leads to the same conclusion.
            logging.warning("No data found for links. Moving on without including links.")
        try:
            if "ice_storage" in data.sheet_names:
                nodes_data.update({_ent.NodeKeys.ice_storage.value: func(data, _ent.NodeKeys.ice_storage.value)})
        except:  # multiple exceptions possible, each of which leads to the same conclusion.
            logging.warning("No data found for an ice storage. Moving on without including one.")

        return nodes_data

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
        for comp in _ent.TransformerTypes:
            mask = data[_ent.NodeKeys.transformers.value][_ent.TransformerLabels.label.value].str.startswith(comp)
            df = data[_ent.NodeKeys.transformers.value][mask]  # Filtered DataFrame
            if not df.empty:
                eff = df[_ent.TransformerLabels.efficiency.value].iloc[0]
                if comp == _ent.TransformerTypes.CHP.value:
                    # electricity bus comes before heating bus(es) for CHP
                    value = float(eff.split(",")[1])
                elif isinstance(eff, str) and comp in [_ent.TransformerTypes.GasBoiler.value, _ent.TransformerTypes.OilBoiler.value, _ent.TransformerTypes.BiomassBoiler.value]:
                    value = float(eff.split(",")[0])
                else:
                    value = float(eff)
                if comp == _ent.TransformerTypes.ElectricRod.value:
                    if df[_ent.TransformerLabels.active.value].iloc[0] == 1:
                        # TODO: check why ElectricRod is not assumed active like other components
                        self.__technology_efficiency[comp] = value
                else:
                    self.__technology_efficiency[comp] = value

        # Storage conversion L - kWh to display the L value
        if self._temperatureLevels:
            self.__Ltank = self._rho * self._c * (self.__operationTemperatures[1] - self.__operationTemperatures[0]) / 3600
        else:
            self.__LgenericStorage = {}
            self.__Lsh = self._rho * self._c * (self.__temperatureSH - data["stratified_storage"].loc["shStorage", "temp_c"]) / 3600
            self.__Ldhw = self._rho * self._c * (self.__temperatureDHW - data["stratified_storage"].loc["dhwStorage", "temp_c"]) / 3600
            if data['storages']['label'].str.match(r'^tankGenericStorage(\d+)?$').any():
                self.__LgenericStorage['tankStorage'] = data["stratified_storage"].loc["tankGenericStorage", "energy_density_per_m3"]/1000
            if data['storages']['label'].str.match(r'^pitGenericStorage(\d+)?$').any():
                self.__LgenericStorage['pitStorage'] = data["stratified_storage"].loc["pitGenericStorage", "energy_density_per_m3"]/1000
            if data['storages']['label'].str.match(r'^boreholeGenericStorage(\d+)?$').any():
                self.__LgenericStorage['boreholeStorage'] = data["stratified_storage"].loc["boreholeGenericStorage", "energy_density_per_m3"]/1000
            if data['storages']['label'].str.match(r'^aquifierGenericStorage(\d+)?$').any():
                self.__LgenericStorage['aquifierStorage'] = data["stratified_storage"].loc["aquifierGenericStorage", "energy_density_per_m3"]/1000
        # For the pit storage (non-generic model which includes losses)
        if data['storages']['label'].str.match(r'^pitStorage(\d+)?$').any():
            self.__LgenericStorage['pitStorageModel'] = self._rho * self._c * (data["stratified_storage"].loc["pitStorage", "temp_h"]
                                                 - data["stratified_storage"].loc["pitStorage", "temp_c"]) / 3600
        # For the tank storage (non-generic model which includes losses)
        if data['storages']['label'].str.match(r'^tankStorage(\d+)?$').any():
            self.__LgenericStorage['tankStorageModel'] = self._rho * self._c * (data["stratified_storage"].loc["tankStorage", "temp_h"]
                                                    - data["stratified_storage"].loc["tankStorage", "temp_c"]) / 3600
        # Storage conversion m3 - kWh for ice storage
        if data['storages']['label'].str.match(r'^iceStorage(\d+)?$').any():
            self.__m3IceStorage = self._rho * 1000 * self._c * (10 - 0) / 3600
        self._generate_transformer_sh_output_flow_dict(data["transformers"])
        self._addBuildings(data, opt, mergeLinkBuses, mergeBuses, mergeHeatSourceSink, includeCarbonBenefits, clusterSize)

    def _generate_transformer_sh_output_flow_dict(self, energy_conversion_tech_data):
        """
        Creates a dictionary that maps each transformer component (transformer label and
        associated building number as dict keys) to its corresponding space heating output
        bus label.

        The mapping is stored in `self._transformer_sh_output_flow`

        This mapping is needed to update the obtained input capacities in the results to output capacities
        """
        self._transformer_sh_output_flow = {}
        for i, r in energy_conversion_tech_data.iterrows():
            dict_key = f"{r[_ent.TransformerLabels.label]}__Building{r[_ent.TransformerLabels.building]}"
            if r[_ent.TransformerLabels.label].startswith(_ent.TransformerTypes.CHP):
                sh_output_bus_label = f"{r[_ent.TransformerLabels.to].split(",")[1]}__Building{r[_ent.TransformerLabels.building]}"
            else:
                sh_output_bus_label = f"{r[_ent.TransformerLabels.to].split(",")[0]}__Building{r[_ent.TransformerLabels.building]}"
            self._transformer_sh_output_flow[dict_key] = sh_output_bus_label

    def _addBuildings(self, data, opt, mergeLinkBuses, mergeBuses, mergeHeatSourceSink, includeCarbonBenefits, clusterSize):
        numberOfBuildings = max(data["buses"]["building"])
        self.__buildings = [Building('Building' + str(i + 1)) for i in range(numberOfBuildings)]
        storageParams = {}
        for s in [_ent.NodeKeys.stratified_storage.value, _ent.NodeKeys.ice_storage.value]:
            if s in data:
                storageParams.update({s: data[s]})
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
            natGasCost = natGasImpact = None
            if "natGas_cost" in data:
                natGasCost = data["natGas_cost"]
                natGasImpact = data["natGas_impact"]
            fixed_sources_data = None
            if "fixed_sources" in data:
                fixed_sources_data = {k: v for k, v in data["fixed_sources"].items() if buildingLabel in k}
            b.addSource(data["commodity_sources"][data["commodity_sources"]["building"] == i], data["electricity_impact"], data["electricity_cost"], natGasCost, natGasImpact, fixed_sources_data, opt, mergeHeatSourceSink, mergeLinkBuses)
            if i in data["building_model"]:
                bmdata = data["building_model"][i]
            else:
                bmdata = {}
            b.addSink(data["demand"][data["demand"]["building"] == i], data["demandProfiles"][i], bmdata, mergeLinkBuses, mergeHeatSourceSink, self._temperatureLevels)
            b.addTransformer(data["transformers"][data["transformers"]["building"] == i], self.__operationTemperatures, self.__temperatureAmb, self.__temperatureGround, opt, mergeLinkBuses, mergeHeatSourceSink, self._dispatchMode, self._temperatureLevels)
            storageList = b.addStorage(data["storages"][data["storages"]["building"] == i], storageParams, self.__temperatureAmb, opt, mergeLinkBuses, self._dispatchMode, self._temperatureLevels)
            b.addSolar(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"].str.match(r"^solarCollector(\d+)?$"))], data["weather_data"], opt, mergeLinkBuses, self._dispatchMode, self._temperatureLevels)
            b.addPV(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"].str.match(r"^pv(\d+)?$"))], data["weather_data"], opt, self._dispatchMode)
            b.addPVT(data["solar"][(data["solar"]["building"] == i) & (data["solar"]["label"].str.match(r"^pvt(\d+)?$"))], data["weather_data"], opt, mergeLinkBuses, self._dispatchMode)
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

        # ======================================================
        # TODO: Because we use "__" here, we break inheritance.  # pylint: disable=fixme
        #       When the EnergyNetworkGroup adds self.__noOfBuildings,
        #       it shows up as self._EnergyNetworkGroup__noOfBuildings.
        #       When the EnergyNetworkClass adds self.__noOfBuildings,
        #       it shows up as self._EnergyNetworkClass__noOfBuildings.
        #       Therefore, when a method in the EnergyNetworkClass tries to call,
        #       self.__noOfBuildings,
        #       then, it will look for self._EnergyNetworkClass__noOfBuildings.
        #       If the self is actually an EnergyNetworkGroup, then it will not find this.
        self.__noOfBuildings = numberOfBuildings
        # ======================================================

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
        # constraint on STC capacity if STC technology is selected
        if any("solarCollector" in n.label for n in self.nodes):
            self._optimizationModel = STCThermalCapacityConstraint(self._optimizationModel, numberOfBuildings)
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

        # todo: return data class
        #       - unprocessed results sheets
        #       - processed results
        #           - total
        #           - per building
        #           - envImpact, capacitiesTransformersNetwork, capacitiesStoragesNetwork
        #           - costs, en
        #       - optimization metadata
        #       -
        # def optimize(self, return_data_class=True):
        # if return_data_class:
        #     return a

        # warning("sunsetting old")
        return envImpact, capacitiesTransformersNetwork, capacitiesStoragesNetwork


    def printbuildingModelTemperatures(self, filename):
        df = pd.DataFrame()
        df["timestamp"] = self.timeindex[0:-1]
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

    def exportIceStorageModelParams(self, filename):
        df = pd.DataFrame()
        df["timestamp"] = self.timeindex[0:-1]
        for i in range(self.__noOfBuildings):
            bNo = i + 1
            tStor = [v for k, v in self._optimizationModel.IceStorageBlock.tStor.get_values().items() if
                       k[0].label.endswith(f"Building{bNo}")]
            mIceStor = [v for k, v in self._optimizationModel.IceStorageBlock.mIceStor.get_values().items() if
                             k[0].label.endswith(f"Building{bNo}")]
            fIce = [v for k, v in self._optimizationModel.IceStorageBlock.fIce.get_values().items() if
                     k[0].label.endswith(f"Building{bNo}")]
            iceStatus = [v for k, v in self._optimizationModel.IceStorageBlock.iceStatus.get_values().items() if
                             k[0].label.endswith(f"Building{bNo}")]
            tStor_prev = [v for k, v in self._optimizationModel.IceStorageBlock.tStor_prev.get_values().items() if
                            k[0].label.endswith(f"Building{bNo}")]
            mIceStor_prev = [v for k, v in
                                  self._optimizationModel.IceStorageBlock.mIceStor_prev.get_values().items() if
                                  k[0].label.endswith(f"Building{bNo}")]
            if tStor:
                df[f"tStor_B{bNo}"] = tStor
                df[f"mIceStor_B{bNo}"] = mIceStor
                df[f"fIce_B{bNo}"] = fIce
                df[f"iceStatus_prev_B{bNo}"] = iceStatus
                df[f"tStor_prev_B{bNo}"] = tStor_prev
                df[f"mIceStor_prev_B{bNo}"] = mIceStor_prev
        df.to_csv(filename, sep=';', index=False)

    def saveUnprocessedResults(self, resultFile=None):
        busLabelList = []
        result = {}
        for i in self.nodes:
            if str(type(i)).replace("<class 'oemof.solph.", "").replace("'>", "") == "buses._bus.Bus":
                busLabelList.append(i.label)
        for i in busLabelList:
            if "sequences" in solph.views.node(self._optimizationResults, i):
                result[i] = pd.DataFrame.from_dict(solph.views.node(self._optimizationResults, i)["sequences"])
                if resultFile is not None:
                    with pd.ExcelWriter(resultFile) as writer:
                        result[i].to_excel(writer, sheet_name=i)
        return result

    def _updateCapacityDictInputInvestment(self, transformerFlowCapacityDict):
        for inflow, outflow in list(transformerFlowCapacityDict):
            index = (inflow, outflow)
            if any(c in str(outflow) for c in _ent.TransformerTypes):
                new_out_flow = self._transformer_sh_output_flow[str(outflow)]
                new_index = (outflow,new_out_flow)
                transformerFlowCapacityDict[new_index] = transformerFlowCapacityDict.pop(index)
            if _ent.BusTypes.electricitySourceBusPVT in str(inflow):   # remove PVT electrical capacity
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
                if str(x).startswith(_ent.StorageTypes.pitStorage):
                    capacitiesInvestedStorages[index] = capacitiesInvestedStorages[index] + \
                                                        optimizationModel.GenericInvestmentStorageBlockPit.invest[x].value
                else:
                    capacitiesInvestedStorages[index] = capacitiesInvestedStorages[index] + \
                                                        optimizationModel.GenericInvestmentStorageBlock.invest[x].value
            else:
                if str(x).startswith(_ent.StorageTypes.pitStorage):
                    capacitiesInvestedStorages[index] = optimizationModel.GenericInvestmentStorageBlockPit.invest[x].value
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
        for inflow_bus, transformer in list(capacitiesTransformers):
            for c in _ent.TransformerTypes:
                if transformer.startswith(c):
                    for index, value in enumerate(self.nodes):
                        if transformer == value.label:
                            if transformer.startswith(_ent.TransformerTypes.Chiller):
                                all_buses_connected_to_transformer = self.nodes[index].outputs
                            else:
                                all_buses_connected_to_transformer = self.nodes[index].conversion_factors
                            for b in all_buses_connected_to_transformer.keys():
                                if self._transformer_sh_output_flow[transformer] in b.label:
                                    capacitiesTransformers[(transformer,b.label)]= capacitiesTransformers[(inflow_bus,transformer)]*self.__technology_efficiency[c]
                                    del capacitiesTransformers[(inflow_bus,transformer)]
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
            elif "tankGenericStorage" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['tankStorage']
            elif "pitGenericStorage" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['pitStorage']
            elif "boreholeGenericStorage" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['boreholeStorage']
            elif "aquifierGenericStorage" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['aquifierStorage']
            elif "pitStorage" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['pitStorageModel']       # non-generic storage model with loss terms depending on geometry
            elif "tankStorage" in storage and not self._temperatureLevels:
                capacitiesStorages[storage] = capacitiesStorages[storage] / self.__LgenericStorage['tankStorageModel']      # non-generic storage model with loss terms depending on geometry
            elif "iceStorage" in storage:
                capacitiesStorages[storage] = capacitiesStorages[storage]/self.__m3IceStorage
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
            if mergeLinkBuses and ("electricity" in self._mergeBuses or "electricityBus" in self._mergeBuses):
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
            if mergeLinkBuses and ("electricity" in self._mergeBuses or "electricityInBus" in self._mergeBuses):
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
                    try:
                        self.__dhwHP[buildingLabel] = sum(
                            solph.views.node(self._optimizationResults, 'HP__' + buildingLabel)["sequences"][
                                ('HP__' + buildingLabel, dhwOutputLabel + buildingLabel), 'flow'])
                    except KeyError as e:
                        """If the dhwStorage is never used, then this will not be available."""
                        pass

                    if buildingLabel in self.__dhwHP.keys():
                        self.__annualCopHP[buildingLabel] = (self.__shHP[buildingLabel] + self.__dhwHP[buildingLabel]) / (
                            self.__elHP[buildingLabel] + 1e-6)
                    else:
                        self.__annualCopHP[buildingLabel] = self.__shHP[buildingLabel] / (
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
        self._communicate_meta_results(self._metaResults, pp.pprint)
        return self._metaResults

    def log_meta_results(self) -> None:
        self._communicate_meta_results(self._metaResults, logging.info)

    @staticmethod
    def _communicate_meta_results(meta_results, communication_method: callable) -> None:
        communication_method("")
        communication_method("Meta Results:")
        communication_method(meta_results)

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
            if building not in self._storageContent:
                self._storageContent[building] = self._optimizationResults[(storage, None)]["sequences"]
            else:
                self._storageContent[building] = pd.concat(
                    [self._storageContent[building], self._optimizationResults[(storage, None)]["sequences"]],
                    axis=1)
            building_number = int(building.replace("Building", ""))
            new_col_name = f"{type}__B{building_number:03d}_storage_content"
            self._storageContent[building].rename(columns={"storage_content": new_col_name}, inplace=True)

    def printInvestedCapacities(self, capacitiesInvestedTransformers, capacitiesInvestedStorages):
        storage_types = {
            _ent.StorageTypes.tankGenericStorage.value: "Tank Generic Storage",
            _ent.StorageTypes.pitStorage.value: "Pit Storage",
            _ent.StorageTypes.pitGenericStorage.value: "Pit Generic Storage",
            _ent.StorageTypes.boreholeGenericStorage.value: "Borehole Generic Storage",
            _ent.StorageTypes.aquifierGenericStorage.value: "Aquifier Generic Storage",
            _ent.StorageTypes.electricalStorage.value: "Electrical Storage",
            _ent.StorageTypes.dhwStorage.value: "DHW Storage Tank",
            _ent.StorageTypes.shStorage.value: "SH Storage Tank",
            _ent.StorageTypes.thermalStorage.value: "Multilayer Thermal Storage Tank"
        }

        transformer_types = {
            _ent.TransformerTypes.HP.value: "Air Source Heat Pump",
            _ent.TransformerTypes.GWHP.value: "Water Source Heat Pump",
            _ent.TransformerTypes.ElectricRod.value: "Electric Rod",
            _ent.TransformerTypes.CHP.value: "CHP",
            _ent.TransformerTypes.GasBoiler.value: "Gas Boiler",
            _ent.TransformerTypes.BiomassBoiler.value: "Biomass Boiler",
            _ent.TransformerTypes.OilBoiler.value: "Oil Boiler",
        }


        for b in range(len(self.__buildings)):
            buildingLabel = "Building" + str(b + 1)
            print("************** Optimized Capacities for {} **************".format(buildingLabel))

            for key, invest in capacitiesInvestedTransformers.items():
                if invest > 0.05 and key[0].endswith("__" + buildingLabel):
                    for transformer_prefix, label_base in transformer_types.items():
                        if key[0].startswith(transformer_prefix):
                            # Extract suffix (e.g., "1" in "BiomassBoiler1__Building1")
                            middle = key[0][len(transformer_prefix):-len("__" + buildingLabel)]
                            suffix = middle if middle.isdigit() else ""

                            # Apply suffix to all transformer types
                            label = f"{label_base} {suffix}" if suffix else label_base

                            unit = "kW"
                            print(f"Invested in {invest:.1f} {unit} {label}.")
                            #TODO: fix the following LOC
                            # printing of Annual COPs does not work currently
                            # most likely due to perfect matching of the string "HP" or "GWHP" while defining self.__annualCopHP
                            if transformer_prefix==_ent.TransformerTypes.HP.value and False:
                                print("     Annual COP = {:.1f}".format(self.__annualCopHP[buildingLabel]))
                            if transformer_prefix == _ent.TransformerTypes.GWHP.value and False:
                                print("     Annual COP = {:.1f}".format(self.__annualCopGWHP[buildingLabel]))

            if ("heatSource_SHsolarCollector__" + buildingLabel, "solarConnectBusSH__" + buildingLabel) in capacitiesInvestedTransformers:
                invest = capacitiesInvestedTransformers[("heatSource_SHsolarCollector__" + buildingLabel, "solarConnectBusSH__" + buildingLabel)]
                if invest > 0.05:
                    print("Invested in {:.1f} m² SolarCollector.".format(invest))
            if ("pv__" + buildingLabel, "electricityProdBus__" + buildingLabel) in capacitiesInvestedTransformers:
                invest = capacitiesInvestedTransformers[("pv__" + buildingLabel, "electricityProdBus__" + buildingLabel)]
                if invest > 0.05:
                    print("Invested in {:.1f} kWp  PV.".format(invest))
            if ("heatSource_SHpvt__" + buildingLabel, "pvtConnectBusSH__" + buildingLabel) in capacitiesInvestedTransformers:
                invest = capacitiesInvestedTransformers[("heatSource_SHpvt__" + buildingLabel, "pvtConnectBusSH__" + buildingLabel)]
                if invest > 0.05:
                    print("Invested in {:.1f} m² PVT collector.".format(invest))

            for key, invest in capacitiesInvestedStorages.items():
                if invest > 0.05 and key.endswith("__" + buildingLabel):
                    for storage_prefix, label_base in storage_types.items():
                        if key.startswith(storage_prefix):
                            # Extract suffix (e.g., "1" in "dhwStorage1__building1")
                            middle = key[len(storage_prefix):-len("__" + buildingLabel)]
                            suffix = middle if middle.isdigit() else ""
                            # Apply suffix to all storage types
                            label = f"{label_base} {suffix}" if suffix else label_base
                            # Choose unit
                            unit = "kWh" if storage_prefix == _ent.StorageTypes.electricalStorage.value else "L"
                            print(f"Invested in {invest:.1f} {unit} {label}.")
            print("")

    def calculate_costs(self) -> tuple[float, float, float]:
        # TODO: reduce to functional programming style by passing required arguments.
        capex_network = sum(self.__capex["Building" + str(b + 1)] for b in range(len(self.__buildings)))
        feed_in_network = sum(self.__feedIn["Building" + str(b + 1)] for b in range(len(self.__buildings)))
        opex_network = sum(sum(self.__opex["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        return capex_network, feed_in_network, opex_network

    def printCosts(self) -> None:
        capex_network, feed_in_network, opex_network = self.calculate_costs()
        self._communicate_costs(capex_network, feed_in_network, opex_network, print)

    def log_costs(self) -> None:
        capex_network, feed_in_network, opex_network = self.calculate_costs()
        self._communicate_costs(capex_network, feed_in_network, opex_network, logging.info)

    @staticmethod
    def _communicate_costs(capex_network: float, feed_in_network: float, opex_network: float,
                           communication_method: callable) -> None:
        communication_method(f"Investment Costs for the system: {capex_network} CHF")
        communication_method(f"Feed In Costs for the system: {feed_in_network} CHF")
        communication_method(f"Operation Costs for the system: {opex_network} CHF")
        communication_method(f"Total Costs for the system: {capex_network + feed_in_network + opex_network} CHF")

    def getTotalCosts(self):
        # TODO: check whether this can be removed.
        capexNetwork, feedinNetwork, opexNetwork = self.calculate_costs()
        return capexNetwork + opexNetwork + feedinNetwork

    def printEnvImpacts(self) -> None:
        env_impact_inputs_network, env_impact_technologies_network = self.calculate_environmental_impacts()
        self._communicate_environmental_impacts(env_impact_inputs_network, env_impact_technologies_network, print)

    def calculate_environmental_impacts(self):
        # TODO: reduce to functional programming style by passing required arguments.
        env_impact_inputs_network = sum(  # operation related impacts, as in "input resources"
            sum(self.__envImpactInputs["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        env_impact_technologies_network = sum(
            sum(self.__envImpactTechnologies["Building" + str(b + 1)].values()) for b in range(len(self.__buildings)))
        return env_impact_inputs_network, env_impact_technologies_network

    def log_environmental_impacts(self) -> None:
        env_impact_inputs, env_impact_technologies = self.calculate_environmental_impacts()
        self._communicate_environmental_impacts(env_impact_inputs, env_impact_technologies, logging.info)

    @staticmethod
    def _communicate_environmental_impacts(env_impact_inputs_network, env_impact_technologies_network,
                                           communication_method: callable) -> None:
        communication_method(f"Environmental impact from input resources for the system: "
                             f"{env_impact_inputs_network} kg CO2 eq")
        communication_method(f"Environmental impact from energy conversion and storage technologies for the system: "
                             f"{env_impact_technologies_network} kg CO2 eq")
        communication_method(f"Total: {env_impact_inputs_network + env_impact_technologies_network} kg CO2 eq")

    def getTotalEnvImpacts(self):
        # TODO: check whether this can be removed.
        env_impact_inputs_network, env_impact_technologies_network = self.calculate_environmental_impacts()
        return env_impact_technologies_network + env_impact_inputs_network

    def exportToExcel(self, file_name, mergeLinkBuses=False):
        hSB_sheet = [] #Special sheet for the merged heatStorageBus
        # Create a mapping between storage content names and their corresponding storage types
        storage_mapping = {
            "SH": "shStorage",
            "DHW": "dhwStorage",
            "Pit": "pitStorage",
            "Borehole": "boreholeStorage",
            "Aquifer": "aquiferStorage",
            "Tank": "tankStorage",
            "Battery": "electricalStorage"
        }

        for i in range(1, self.__noOfBuildings + 1):
            building_label = f"Building{i}"
            if self._temperatureLevels:
                self.calcStateofCharge("thermalStorage", building_label)
            else:
                if not hasattr(self, "_storage_content"):
                    self._storage_content = {}
                for storage_type in storage_mapping.values():
                    for group_key in self.groups:
                        if not isinstance(group_key, str):
                            continue
                        # Check: starts with storage_type, ends with __BuildingX, and only digits (or nothing) in between
                        if group_key.endswith(f"__{building_label}") and group_key.startswith(storage_type):
                            # Extract the part after storage_type and before __BuildingX
                            suffix = group_key[len(storage_type):group_key.index(f"__{building_label}")]
                            if suffix == "" or suffix.isdigit():
                                storage_instance = group_key.split("__")[0]
                                self.calcStateofCharge(storage_instance, building_label)

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

            # writing the storage content, costs and environmental impacts (of different components...) for each building
            for b in self.__buildings:
                buildingLabel = b.getBuildingLabel()

                self._storageContent[buildingLabel].to_excel(writer, sheet_name="storage_content__" + buildingLabel)

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
        self._mergeBuses = mergeBuses
        self.__noOfBuildings = nr_of_buildings
        logging.info(f"Defining the energy network from the input files: {input_data_dir}")

        csvReader = _re.CsvScenarioReader(input_data_dir)
        initial_nodal_data = csvReader.read_scenario()

        other_data_reader = read.ProfileAndOtherDataReader()
        nodal_data = other_data_reader.read_profiles_and_other_data(initial_nodal_data, input_data_dir, nr_of_buildings,
                                                                    clusterSize, self.timeindex)
        self.set_using_nodal_data(clusterSize, input_data_dir, includeCarbonBenefits, nodal_data, mergeBuses,
                                  mergeHeatSourceSink, mergeLinkBuses, nr_of_buildings, opt)

    @staticmethod
    def check_dir_path(dir_path: _pl.Path):
        if not dir_path or not os.path.isdir(dir_path):
            logging.error(f"Directory {dir_path} not found.")


class EnergyNetworkIndiv(EnergyNetworkClass):
    # TODO: sunsetted, please use parent instead  # pylint: disable=fixme

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
        self.check_file_path(filePath)
        logging.info("Defining the energy network from the excel file: {}".format(filePath))
        self.check_mutually_exclusive_inputs(mergeLinkBuses)
        self._dispatchMode = dispatchMode
        self._optimizationType = opt
        self._mergeBuses = mergeBuses
        self.__noOfBuildings = numberOfBuildings
        data = pd.ExcelFile(filePath)
        initial_nodal_data = self.get_nodal_data_from_Excel(data)
        data.close()

        other_data_reader = read.ProfileAndOtherDataReader()
        nodesData = other_data_reader.read_profiles_and_other_data(initial_nodal_data, filePath, numberOfBuildings, clusterSize,
                                                                   self.timeindex)

        self.set_using_nodal_data(clusterSize, filePath, includeCarbonBenefits, nodesData, mergeBuses,
                                  mergeHeatSourceSink, mergeLinkBuses, numberOfBuildings, opt, grouped_network=True)

    def set_from_csv(self, input_data_dir: _pl.Path, nr_of_buildings: int, clusterSize={}, opt: str = "costs",
                   mergeLinkBuses: bool = False, mergeBuses: _tp.Optional[_tp.Sequence[str]] = None,
                   mergeHeatSourceSink: bool = False, dispatchMode: bool = False, includeCarbonBenefits: bool = False):

        self.check_dir_path(input_data_dir)
        self.check_mutually_exclusive_inputs(mergeLinkBuses)
        self._dispatchMode = dispatchMode
        self._optimizationType = opt
        self._mergeBuses = mergeBuses
        self.__noOfBuildings = nr_of_buildings
        logging.info(f"Defining the energy network from the input files: {input_data_dir}")

        csvReader = _re.CsvScenarioReader(input_data_dir)
        initial_nodal_data = csvReader.read_scenario()

        other_data_reader = read.ProfileAndOtherDataReader()
        nodal_data = other_data_reader.read_profiles_and_other_data(initial_nodal_data, input_data_dir, nr_of_buildings,
                                                                    clusterSize, self.timeindex)
        self.set_using_nodal_data(clusterSize, input_data_dir, includeCarbonBenefits, nodal_data, mergeBuses,
                                  mergeHeatSourceSink, mergeLinkBuses, nr_of_buildings, opt, grouped_network=True)

    def _addLinks(self, data, numberOfBuildings, mergeLinkBuses):
        """connects buses A and B (denotes a bidirectional link)"""
        if mergeLinkBuses:
            return
        for i, l in data.iterrows():
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
                    elif "electricity" in l["label"]:
                        busesOut.append(self._busDict["electricityBus" + '__Building' + str(b + 1)])
                        busesIn.append(self._busDict["electricityInBus" + '__Building' + str(b + 1)])
                    elif "dhLink" in l["label"]:
                        if "districtHeatingInBus" + '__Building' + str(b + 1) in self._busDict:
                            busesOut.append(self._busDict["districtHeatingInBus" + '__Building' + str(b + 1)])
                        busesIn.append(self._busDict["districtHeatingBus" + '__Building' + str(b + 1)])

                self._nodesList.append(Link(
                    label=l["label"],
                    inputs={busA: solph.Flow() for busA in busesOut},
                    outputs={busB: solph.Flow(investment=investment) for busB in busesIn},
                    conversion_factors={busB: l["efficiency"] for busB in busesIn}
                ))
