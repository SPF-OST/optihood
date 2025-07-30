import configparser as _cp
import dataclasses as _dc
import datetime as _dt
import logging as _log
import os as _os
import pathlib as _pl
import typing as _tp

import numpy as _np
import pandas as _pd

import optihood.entities as ent


# TODO: extract other stuff from set_using_nodal_data.
# TODO: make excelReader
# TODO: make ConfigConverter and have CsvReader and CsvWriter be standalone.
#       ConfigConverter. read, .convert, .write_to_csv, .write_to_excel.
# TODO: merge ProfileAndOtherDataReader into other readers though:
#       - Inheritance.
#       - Structure
#         CsvScenarioReader = ScenarioReaderAbstract(reader=CsvReader,
#                             ProfileAndOtherDataReader=ProfileAndOtherDataReader)


@_dc.dataclass
class CsvReader:
    """ use_function is currently implemented to deal with deprecation of a pandas feature
    (_pd.to_numeric, errors="ignore").
    This can be set to 'current' or 'future'.
    """

    dir_path: _pl.Path

    def read(self, file_name: str) -> _pd.DataFrame:
        # read_csv does not have as strong a parser as ExcelFile.parse.
        # One issue the following addresses, is the "nr as string" outputs.

        df = _pd.read_csv(self.dir_path / file_name)
        [self.make_nrs_numeric(df, column) for column in df.columns]

        return df

    @staticmethod
    def safe_to_numeric(value):
        # Suggested by pandas developers
        # https://github.com/pandas-dev/pandas/issues/59221#issuecomment-2755021659
        try:
            return _pd.to_numeric(value)
        except (ValueError, TypeError):
            return value

    @staticmethod
    def make_nrs_numeric(df: _pd.DataFrame, column_name: str) -> None:
        df[column_name] = df[column_name].apply(CsvReader.safe_to_numeric)


@_dc.dataclass
class CsvScenarioReader(CsvReader):
    """Very simplified implementation.
    Each CSV file inherently has its own data model.
    This needs to be incorporated into a validation of these inputs.
    """

    relative_file_paths: dict[str, str] = _dc.field(init=False)

    def __post_init__(self):
        paths = ent.CsvInputFilePathsRelative
        self.relative_file_paths = {
            ent.NodeKeys.buses: paths.buses,
            ent.NodeKeys.grid_connection: paths.grid_connection,
            ent.NodeKeys.commodity_sources: paths.commodity_sources,
            ent.NodeKeys.solar: paths.solar,
            ent.NodeKeys.transformers: paths.transformers,
            ent.NodeKeys.demand: paths.demand,
            ent.NodeKeys.storages: paths.storages,
            ent.NodeKeys.stratified_storage: paths.stratified_storage,
            ent.NodeKeys.profiles: paths.profiles,
            ent.NodeKeys.links: paths.links,
        }

    def read_scenario(self) -> dict[str, _pd.DataFrame]:
        # Fine-grained feedback could be provided using validators for the individual files.
        # This would include information related to the models,
        # e.g. T range should be between 7 and 12 deg C for chillers.

        data = {}
        errors = []
        for key, rel_path in self.relative_file_paths.items():
            try:
                data[key] = self.read(rel_path)
                # df_current = _pd.read_csv(path)
            except FileNotFoundError as e:
                if not key == ent.NodeKeys.links:
                    errors.append(e)

            # validation_error = self.validate(key, df_current)
            # if not validation_error:
            #     data[key] = df_current
            # else:
            #     errors.append(validation_error)

        if errors:
            # Should this be added to logging as well?
            raise ExceptionGroup("Issues with CSV files.", errors)

        return data


def parse_config(configFilePath: str):
    # Making this a class method would allow us to provide the parser.
    config = _cp.ConfigParser()
    config.read(configFilePath)
    configData = {}
    for section in config.sections():
        configData[section] = config.items(section)
    configData = {k.lower(): v for k, v in configData.items()}

    return configData


def add_unique_label_columns(nodal_data: dict[str, _pd.DataFrame]) -> dict[str, _pd.DataFrame]:
    """Provides new columns with unique labels for "label", "to", "from", "connect"
    This function also adds a unique label for the buildings in "building_model_parameters".

    The DataFrames in the sheets are updated automatically as each df is a pointer to that sheet.
    """
    sheets = list(nodal_data.keys())
    building_sheet_name = ent.NodeKeysOptional.building_model_parameters

    if building_sheet_name in sheets:
        sheets.remove(building_sheet_name)
        df = nodal_data[building_sheet_name]
        df[ent.BuildingModelParameters.building_unique] = get_unique_buildings(df)

    sheets_with_no_need_for_unique_labels = [ent.NodeKeys.ice_storage, ent.NodeKeys.stratified_storage,
                                             ent.NodeKeys.profiles, ent.NodeKeys.links]
    # TODO: maybe remove time_step_data from sheets as well.

    [sheets.remove(x) for x in sheets_with_no_need_for_unique_labels if x in sheets]
    for sheet in sheets:
        df = nodal_data[sheet]
        df[ent.CommonLabels.label_unique] = get_unique_labels(
            df[[ent.CommonLabels.label, ent.CommonLabels.building]])

        if ent.CommonLabels.from_bus in df.columns:
            df[ent.CommonLabels.from_unique] = get_unique_buses(
                df[[ent.CommonLabels.from_bus, ent.CommonLabels.building]], ent.CommonLabels.from_bus)

        if ent.CommonLabels.to in df.columns:
            df[ent.CommonLabels.to_unique] = get_unique_buses(df[[ent.CommonLabels.to, ent.CommonLabels.building]],
                                                              ent.CommonLabels.to)

        if ent.CommonLabels.connect in df.columns:
            df[ent.CommonLabels.connect_unique] = get_unique_buses(
                df[[ent.CommonLabels.connect, ent.CommonLabels.building]], ent.CommonLabels.connect)

    return nodal_data


def get_unique_labels(df: _pd.DataFrame) -> list[str]:
    return [f"{row[ent.CommonLabels.label.value]}__B{str(row[ent.CommonLabels.building.value]).zfill(3)}" for _, row
            in df.iterrows()]


def get_unique_buses(df: _pd.DataFrame, buses_column: str) -> list[list[str]]:
    """Returns lists of strings for all cases, to simplify usage later."""
    buses = []
    for _, row in df.iterrows():
        row_buses = []
        for bus in row[buses_column].split(","):
            row_buses.append(f"{bus}__B{str(row[ent.CommonLabels.building.value]).zfill(3)}")
        buses.append(row_buses)
    return buses


def get_unique_buildings(df: _pd.DataFrame) -> list[str]:
    """Returns strings for both cases, to simplify usage later."""
    if ent.BuildingModelParameters.Circuit in df.columns:
        return [
            (f"Building_model__B{str(row[ent.BuildingModelParameters.Building_Number]).zfill(3)}"
             f"_C{str(row[ent.BuildingModelParameters.Circuit]).zfill(3)}")
            for _, row in df.iterrows()]

    return [f"Building_model__B{str(row[ent.BuildingModelParameters.Building_Number]).zfill(3)}"
            for _, row in df.iterrows()]


class ProfileAndOtherDataReader:
    @staticmethod
    def get_values_from_dataframe(df: _pd.DataFrame, identifier: str, identifier_column: str, desired_column: str,
                                  message: str,
                                  desired_instances: _tp.Tuple = (str, float, int, _np.int64, _np.float64),
                                  nan_allowed: bool = False,
                                  ) -> float | int | str:
        f""" Find any {identifier} entries in the {identifier_column} and return the 
             {desired_column} value of those rows."""
        row_indices = df[identifier_column] == identifier
        values = df.loc[row_indices, desired_column].iloc[0]

        try:
            # This makes this method less reusable.
            # It could be put into a wrapper function instead.
            # We currently pass a tuple for the assert for flexibility instead.
            assert isinstance(values, desired_instances)
        except AssertionError:
            message += f"\n Corrupt value in: \n{df.loc[row_indices]}"
            _log.error(message)
            raise ValueError(message)

        if not nan_allowed and isinstance(values, (float, _np.float64)) and _np.isnan(values):
            message += f"\n Value empty in: \n{df.loc[row_indices]}"
            _log.error(message)
            raise ValueError(message)

        return values

    def read_profiles_and_other_data(self, nodal_data: dict[str, _pd.DataFrame], file_or_folder_path: _pl.Path,
                                     num_buildings: int, cluster_size: dict[str, int] | None,
                                     time_index: _pd.DatetimeIndex,
                                     ) -> dict[str, _pd.DataFrame | dict[str, _pd.DataFrame]]:

        self.drop_inactive_rows(nodal_data)
        self.update_indices(nodal_data)

        # ====================================================
        # extract input data from CSVs
        # TODO: how would this change when getting data from an api connection?
        nodal_data = self.add_demand_profiles(nodal_data, cluster_size, num_buildings, time_index)
        nodal_data = self.add_electricity_impact(nodal_data, cluster_size, time_index)
        nodal_data = self.add_electricity_cost(nodal_data, cluster_size, time_index)
        nodal_data = self.add_weather_profiles(nodal_data, cluster_size, time_index)

        nodal_data = self.maybe_add_natural_gas(nodal_data, cluster_size, time_index)
        nodal_data = self.maybe_add_building_model_with_internal_gains(nodal_data, num_buildings, cluster_size,
                                                                       time_index)
        nodal_data = self.maybe_add_fixed_source_profiles(nodal_data, cluster_size, time_index)
        # ====================================================

        _log.info(f"Data from file {file_or_folder_path} imported.")

        return nodal_data

    @staticmethod
    def drop_inactive_rows(nodal_data):
        for key, df in nodal_data.items():
            if ent.BusesLabels.active not in df.columns:
                continue
            nodal_data[key] = df.where(df[ent.BusesLabels.active] == 1).dropna(how="all")
        return nodal_data

    @staticmethod
    def update_indices(nodal_data):
        """Stratified storages need the labels as indices."""
        # TODO: adjust this at the reading stage.  # pylint: disable=fixme
        nodal_data[ent.NodeKeys.stratified_storage.value].set_index(ent.StratifiedStorageLabels.label.value,
                                                                    inplace=True)
        if ent.NodeKeys.ice_storage.value in nodal_data:
            nodal_data[ent.NodeKeys.ice_storage.value].set_index(ent.IceStorageLabels.label.value, inplace=True)

    def add_weather_profiles(self, nodesData, clusterSize, time_index: _pd.DatetimeIndex):
        weatherDataPath = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.profiles],
            identifier_column=ent.ProfileLabels.name,
            identifier=ent.ProfileTypes.weather,
            desired_column=ent.ProfileLabels.path,
            message="Error in weather data file path",
        )

        if not _os.path.exists(weatherDataPath):
            _log.error("Error in weather data file path")
            raise FileNotFoundError(weatherDataPath)

        nodesData["weather_data"] = _pd.read_csv(weatherDataPath, delimiter=";")
        # add a timestamp column to the dataframe
        for index, row in nodesData['weather_data'].iterrows():
            time = f"{int(row['time.yy'])}.{int(row['time.mm']):02}.{int(row['time.dd']):02} {int(row['time.hh']
                                                                                                  ):02}:00:00"
            nodesData['weather_data'].at[index, 'timestamp'] = _dt.datetime.strptime(time, "%Y.%m.%d  %H:%M:%S")
            # set datetime index
        nodesData["weather_data"].timestamp = _pd.to_datetime(nodesData["weather_data"].timestamp,
                                                              format='%Y.%m.%d %H:%M:%S')
        nodesData["weather_data"].set_index("timestamp", inplace=True)
        if not clusterSize:
            # for data with typical years; we might have 2 years if summer of 1st yr and winter of 2nd yr is considered
            # we need to change index if len > 2 years
            if nodesData["weather_data"].index.year.unique().__len__() > 2:
                new_index = _pd.to_datetime({
                    'year': time_index.year[0],
                    'month': nodesData["weather_data"].index.month,
                    'day': nodesData["weather_data"].index.day,
                    'hour': nodesData["weather_data"].index.hour})
                nodesData["weather_data"].index = new_index
            nodesData["weather_data"] = self.clip_to_time_index(nodesData["weather_data"], time_index)

        if clusterSize:
            weatherData = _pd.concat([nodesData['weather_data'][
                                         nodesData['weather_data']['time.mm'] == int(d.split('-')[1])][
                                         nodesData['weather_data']['time.dd'] == int(d.split('-')[2])][
                                         ['gls', 'str.diffus', 'tre200h0', 'ground_temp']] for d in clusterSize.keys()])

            nodesData["weather_data"] = weatherData

        return nodesData

    def add_electricity_cost(self, nodesData, cluster_size, time_index: _pd.DatetimeIndex):
        electricityCost = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.commodity_sources],
            identifier_column=ent.CommonLabels.label,
            identifier=ent.CommoditySourceTypes.electricityResource,
            desired_column=ent.CommoditySourcesLabels.variable_costs,
            message="Error in electricity cost."
        )

        # int64 is not an instance of int!!
        # float64 is not an instance of float!!
        if isinstance(electricityCost, (float, int, _np.float64, _np.int64)):
            # for constant cost
            electricityCostValue = electricityCost
            _log.info("Constant value for electricity cost")
            nodesData["electricity_cost"] = _pd.DataFrame()
            nodesData["electricity_cost"]["cost"] = (nodesData["demandProfiles"][1].shape[0]) * [
                electricityCostValue]
            nodesData["electricity_cost"].index = nodesData["demandProfiles"][1].index
        elif not _os.path.exists(electricityCost):
            _log.error("Error in electricity cost file path")
            raise FileNotFoundError(electricityCost)
        else:
            nodesData["electricity_cost"] = _pd.read_csv(electricityCost, delimiter=";")
            # set datetime index
            nodesData["electricity_cost"].set_index("timestamp", inplace=True)
            nodesData["electricity_cost"].index = _pd.to_datetime(nodesData["electricity_cost"].index,
                                                                  format='%d.%m.%Y %H:%M')
            nodesData["electricity_cost"] = self.clip_to_time_index(nodesData["electricity_cost"], time_index)

        if cluster_size:
            electricityCost = self.cluster_and_multiply_desired_column(nodesData["electricity_cost"], cluster_size)
            nodesData["electricity_cost"] = electricityCost

        return nodesData

    def add_electricity_impact(self, nodesData, cluster_size, time_index: _pd.DatetimeIndex):
        electricityImpact = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.commodity_sources],
            identifier_column=ent.CommoditySourcesLabels.label,
            identifier=ent.CommoditySourceTypes.electricityResource,
            desired_column=ent.CommoditySourcesLabels.CO2_impact,
            message="Error in electricity impact.",
        )

        if isinstance(electricityImpact, (float, int, _np.float64, _np.int64)):
            # for constant impact
            electricityImpactValue = electricityImpact
            _log.info("Constant value for electricity impact")
            nodesData["electricity_impact"] = _pd.DataFrame()
            nodesData["electricity_impact"]["impact"] = (nodesData["demandProfiles"][1].shape[0]) * [
                electricityImpactValue]
            nodesData["electricity_impact"].index = nodesData["demandProfiles"][1].index
        elif not _os.path.exists(electricityImpact):
            _log.error("Error in electricity impact file path")
            raise FileNotFoundError("Error in electricity impact file path")
        else:
            nodesData["electricity_impact"] = _pd.read_csv(electricityImpact, delimiter=";")
            # set datetime index
            nodesData["electricity_impact"].set_index("timestamp", inplace=True)
            nodesData["electricity_impact"].index = _pd.to_datetime(nodesData["electricity_impact"].index,
                                                                    format='%d.%m.%Y %H:%M')
            nodesData["electricity_impact"] = self.clip_to_time_index(nodesData["electricity_impact"], time_index)

        if cluster_size:
            electricityImpact = self.cluster_and_multiply_desired_column(nodesData["electricity_impact"], cluster_size)
            nodesData["electricity_impact"] = electricityImpact

        return nodesData

    @staticmethod
    def cluster_desired_column(df: _pd.DataFrame, clusterSize: dict[str, int]) -> _pd.DataFrame:
        return _pd.concat([df.loc[d] for d in clusterSize.keys()])

    @staticmethod
    def cluster_and_multiply_desired_column(df: _pd.DataFrame,  cluster_size: dict[str, int]) -> _pd.DataFrame:
        return _pd.concat([df.loc[d] * v for d, v in cluster_size.items()])

    def add_demand_profiles(self, nodesData, clusterSize, numBuildings, time_index: _pd.DatetimeIndex):
        # demandProfilesPath should contain csv file(s) (one for each building's profiles)
        demandProfilesPath = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.profiles],
            identifier_column=ent.ProfileLabels.name,
            identifier=ent.ProfileTypes.demand,
            desired_column=ent.ProfileLabels.path,
            message="Error in the demand profiles path."
        )

        if not _os.path.exists(demandProfilesPath) or not _os.listdir(demandProfilesPath):
            _log.error(f"Error in the demand profiles path: The folder is either empty or does not exist: "
                       f"{demandProfilesPath}")
            raise FileNotFoundError(f"Error in the demand profiles path: The folder is either empty or does not exist: "
                                    f"{demandProfilesPath}")

        demandProfiles = {}  # dictionary of dataframes for each building's demand profiles
        i = 0
        for filename in _os.listdir(demandProfilesPath):
            i += 1  # Building number
            if i > numBuildings:
                _log.warning("Demand profiles folder has more files than the number of buildings specified")
                break
            demandProfiles.update({i: _pd.read_csv(_os.path.join(demandProfilesPath, filename), delimiter=";")})

        nodesData["demandProfiles"] = demandProfiles

        # set datetime index
        for i in range(numBuildings):
            nodesData["demandProfiles"][i + 1].timestamp = _pd.to_datetime(nodesData["demandProfiles"][i + 1].timestamp,
                                                                           format='%Y-%m-%d %H:%M:%S')
            nodesData["demandProfiles"][i + 1].set_index("timestamp", inplace=True)
            if not clusterSize:
                nodesData["demandProfiles"][i + 1] = self.clip_to_time_index(nodesData["demandProfiles"][i + 1],
                                                                             time_index)
        if clusterSize:
            demandProfiles = {}
            for i in range(1, numBuildings + 1):
                demandProfiles[i] = self.cluster_desired_column(nodesData["demandProfiles"][i], clusterSize)
            nodesData["demandProfiles"] = demandProfiles

        return nodesData

    def maybe_add_natural_gas(self, nodesData, cluster_size, time_index: _pd.DatetimeIndex):
        if "naturalGasResource" not in nodesData["commodity_sources"]["label"].values:
            return nodesData

        # Making this a wrapper function simplifies testing.
        nodesData = self.add_natural_gas_impact(nodesData, cluster_size, time_index)
        nodesData = self.add_natural_gas_costs(nodesData, cluster_size, time_index)

        return nodesData

    def maybe_add_fixed_source_profiles(self, nodesData, cluster_size, time_index: _pd.DatetimeIndex):
        if "fixed" in nodesData["commodity_sources"].columns:
            if not (nodesData["commodity_sources"]["fixed"].eq(1)).any():
                return nodesData
        else:
            return nodesData

        fixed_source_profiles_path = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.profiles],
            identifier_column=ent.ProfileLabels.name,
            identifier=ent.ProfileTypes.fixed_sources,
            desired_column=ent.ProfileLabels.path,
            message="Error in the fixed source profiles path."
        )

        if not _os.path.exists(fixed_source_profiles_path) or not _os.listdir(fixed_source_profiles_path):
            _log.error(f"Error in the fixed sources profile path: The folder is either empty or does not exist: "
                       f"{fixed_source_profiles_path}")
            raise FileNotFoundError(f"Error in the fixed sources profile path: The folder is either empty or does not exist: "
                                    f"{fixed_source_profiles_path}")

        fixed_sources_data = {}
        for filename in _os.listdir(fixed_source_profiles_path):
            fixed_sources_data.update({filename.split(".csv")[0]: _pd.read_csv(_os.path.join(fixed_source_profiles_path, filename), delimiter=";")})

        nodesData["fixed_sources"] = fixed_sources_data

        # set datetime index
        for i in nodesData["fixed_sources"].keys():
            nodesData["fixed_sources"][i].timestamp = _pd.to_datetime(nodesData["fixed_sources"][i].timestamp,
                                                                           format='%Y-%m-%d %H:%M:%S')
            nodesData["fixed_sources"][i].set_index("timestamp", inplace=True)
            if not cluster_size:
                nodesData["fixed_sources"][i] = self.clip_to_time_index(nodesData["fixed_sources"][i],
                                                                             time_index)
        if cluster_size:
            fixed_sources_data = {}
            for i in nodesData["fixed_sources"].keys():
                fixed_sources_data[i] = self.cluster_desired_column(nodesData["fixed_sources"][i], cluster_size)
            nodesData["fixed_sources"] = fixed_sources_data

        return nodesData

    def add_natural_gas_costs(self, nodesData, cluster_size, time_index):
        natGasCost = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.commodity_sources],
            identifier_column=ent.CommonLabels.label,
            identifier=ent.CommoditySourceTypes.naturalGasResource,
            desired_column=ent.CommoditySourcesLabels.variable_costs,
            message="Error in natural gas cost.",
        )
        if isinstance(natGasCost, (int, float, _np.float64, _np.int64)):
            # for constant cost
            natGasCostValue = natGasCost
            _log.info("Constant value for natural gas cost")
            nodesData["natGas_cost"] = _pd.DataFrame()
            nodesData["natGas_cost"]["cost"] = (nodesData["demandProfiles"][1].shape[0]) * [natGasCostValue]
            nodesData["natGas_cost"].index = nodesData["demandProfiles"][1].index
        elif not _os.path.exists(natGasCost):
            _log.error("Error in natural gas cost file path")
            raise FileNotFoundError(f"Error in natural gas cost file path: {natGasCost}")

        else:
            nodesData["natGas_cost"] = _pd.read_csv(natGasCost, delimiter=";")
            # set datetime index
            nodesData["natGas_cost"].set_index("timestamp", inplace=True)
            nodesData["natGas_cost"].index = _pd.to_datetime(nodesData["natGas_cost"].index, format='%d.%m.%Y %H:%M')
            nodesData["natGas_cost"] = self.clip_to_time_index(nodesData["natGas_cost"], time_index)
        if cluster_size:
            natGasCost = self.cluster_and_multiply_desired_column(nodesData["natGas_cost"], cluster_size)
            nodesData["natGas_cost"] = natGasCost

        return nodesData

    def add_natural_gas_impact(self, nodesData, cluster_size, time_index):
        natGasImpact = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.commodity_sources],
            identifier_column=ent.CommonLabels.label,
            identifier=ent.CommoditySourceTypes.naturalGasResource,
            desired_column=ent.CommoditySourcesLabels.CO2_impact,
            message="Error in natural gas impact.",
        )
        if isinstance(natGasImpact, (int, float, _np.float64, _np.int64)) or (
                natGasImpact.split('.')[0].replace('-', '').isdigit() and
                natGasImpact.split('.')[1].replace('-', '').isdigit()
        ):
            # for constant impact
            natGasImpactValue = float(natGasImpact)
            _log.info("Constant value for natural gas impact")
            nodesData["natGas_impact"] = _pd.DataFrame()
            nodesData["natGas_impact"]["impact"] = (nodesData["demandProfiles"][1].shape[0]) * [
                natGasImpactValue]
            nodesData["natGas_impact"].index = nodesData["demandProfiles"][1].index
        elif not _os.path.exists(natGasImpact):
            _log.error("Error in natural gas impact file path")
            raise FileNotFoundError(f"Error in natural gas impact file path: {natGasImpact}")
        else:
            nodesData["natGas_impact"] = _pd.read_csv(natGasImpact, delimiter=";")
            # set datetime index
            nodesData["natGas_impact"].set_index("timestamp", inplace=True)
            nodesData["natGas_impact"].index = _pd.to_datetime(nodesData["natGas_impact"].index,
                                                               format='%d.%m.%Y %H:%M')
            nodesData["natGas_impact"] = self.clip_to_time_index(nodesData["natGas_impact"], time_index)
        if cluster_size:
            natGasImpact = self.cluster_and_multiply_desired_column(nodesData["natGas_impact"], cluster_size)
            nodesData["natGas_impact"] = natGasImpact

        return nodesData

    def maybe_add_building_model_with_internal_gains(self, nodesData, numBuildings, clusterSize,
                                                     time_index: _pd.DatetimeIndex):
        nodesData["building_model"] = {}
        if not nodesData['demand']['building model'].notna().any() or not (
                nodesData['demand']['building model'] == 'Yes').any():
            _log.info("Building model either not selected or invalid string value entered")
        else:
            nodesData, internalGains = self.add_internal_gains(nodesData, clusterSize, time_index)

            nodesData = self.add_building_models(nodesData, numBuildings, internalGains)

        return nodesData

    def add_internal_gains(self, nodesData, clusterSize, time_index):
        internalGainsPath = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.profiles],
            identifier_column=ent.ProfileLabels.name,
            identifier=ent.ProfileTypes.internal_gains,
            desired_column=ent.ProfileLabels.path,
            message="Error in internal gains file path for the building model."
        )
        if not _os.path.exists(internalGainsPath):
            _log.error("Error in internal gains file path for the building model.")
            raise FileNotFoundError(f"Error in internal gains file path for the building model{internalGainsPath}")
        internalGains = _pd.read_csv(internalGainsPath, delimiter=';')
        internalGains.timestamp = _pd.to_datetime(internalGains.timestamp, format='%d.%m.%Y %H:%M')
        internalGains.set_index("timestamp", inplace=True)
        if not clusterSize:
            internalGains = self.clip_to_time_index(internalGains, time_index)
        return nodesData, internalGains

    def add_building_models(self, nodesData, numBuildings, internalGains):
        b_model_params_Path = self.get_values_from_dataframe(
            df=nodesData[ent.NodeKeys.profiles],
            identifier_column=ent.ProfileLabels.name,
            identifier=ent.ProfileTypes.building_model_params,
            desired_column=ent.ProfileLabels.path,
            message="Error in building model parameters file path."
        )
        if not _os.path.exists(b_model_params_Path):
            _log.error("Error in building model parameters file path.")
            raise FileNotFoundError(f"Error in building model parameters file path: {b_model_params_Path}")

        bmParamers = _pd.read_csv(b_model_params_Path, delimiter=';')
        for i in range(numBuildings):
            nodesData["building_model"][i + 1] = {}
            nodesData["building_model"][i + 1]["timeseries"] = _pd.DataFrame()
            nodesData["building_model"][i + 1]["timeseries"]["tAmb"] = _np.array(
                nodesData["weather_data"]["tre200h0"])
            nodesData["building_model"][i + 1]["timeseries"]["IrrH"] = _np.array(
                nodesData["weather_data"]["gls"]) / 1000  # conversion from W/m2 to kW/m2
            nodesData["building_model"][i + 1]["timeseries"][f"Qocc"] = internalGains[f'Total (kW) {i + 1}'].values

            if "tIndoorDay" in bmParamers.columns:
                tIndoorDay = float(bmParamers[bmParamers["Building Number"] == (i + 1)]['tIndoorDay'].iloc[0])
                tIndoorNight = float(bmParamers[bmParamers["Building Number"] == (i + 1)]['tIndoorNight'].iloc[0])
                tIndoorSet = [tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight,
                              tIndoorNight, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay,
                              tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay, tIndoorDay,
                              tIndoorNight, tIndoorNight, tIndoorNight, tIndoorNight] * 365
                nodesData["building_model"][i + 1]["timeseries"]["tIndoorSet"] = _pd.DataFrame(tIndoorSet).values
            paramList = ['gAreaWindows', 'rDistribution', 'cDistribution', 'rWall', 'cWall', 'rIndoor',
                         'cIndoor',
                         'qDistributionMin', 'qDistributionMax', 'tIndoorMin', 'tIndoorMax', 'tIndoorInit',
                         'tWallInit', 'tDistributionInit']

            for param in paramList:
                nodesData["building_model"][i + 1][param] = float(
                    bmParamers[bmParamers["Building Number"] == (i + 1)][param].iloc[0])

        return nodesData

    @staticmethod
    def clip_to_time_index(df: _pd.DataFrame, time_index: _pd.DatetimeIndex):
        return df[time_index[0]:time_index[-1]]
