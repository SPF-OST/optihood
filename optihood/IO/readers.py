import configparser as _cp
import dataclasses as _dc
import pathlib as _pl

import pandas as _pd

import optihood.entities as ent


@_dc.dataclass
class CsvReader:
    """ use_function is currently implemented to deal with deprecation of a pandas feature
    (_pd.to_numeric, errors="ignore").
    This can be set to 'current' or 'future'.
    """

    dir_path: _pl.Path
    use_function: str = 'future'  # or 'current'

    def __post_init__(self):
        if self.use_function == 'current':
            self.make_nrs_numeric = self.make_nrs_numeric_current
        elif self.use_function == 'future':
            self.make_nrs_numeric = self.make_nrs_numeric_without_future_warning

    def read(self, file_name: str) -> _pd.DataFrame:
        # read_csv does not have as strong a parser as ExcelFile.parse.
        # One issue the following addresses, is the "nr as string" outputs.

        df = _pd.read_csv(self.dir_path / file_name)
        [self.make_nrs_numeric(df, column) for column in df.columns]

        return df

    @staticmethod
    def make_nrs_numeric_current(df: _pd.DataFrame, column_name: str) -> None:
        df[column_name] = df[column_name].apply(_pd.to_numeric, errors="ignore")

    @staticmethod
    def make_nrs_numeric_without_future_warning(df: _pd.DataFrame, column_name: str) -> None:
        # Fix using "coerce" and re-filling NaN values.
        # Unfortunately, this applies to full text columns as well.
        def parse_numbers(x):
            # Suggested by pandas developers
            # https://github.com/pandas-dev/pandas/issues/59221#issuecomment-2755021659
            try:
                return _pd.to_numeric(x)
            except Exception:
                return x

        df[column_name] = df[column_name].apply(parse_numbers)


@_dc.dataclass
class CsvScenarioReader(CsvReader):
    """Very simplified implementation.
    Each CSV file inherently has its own data model.
    This needs to be incorporated into a validation of these inputs.
    """

    relative_file_paths: dict[str, str] = _dc.field(init=False)

    def __post_init__(self):
        super().__post_init__()
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
            f"{row[ent.BuildingModelParameters.Building_Number]}__C{str(row[ent.BuildingModelParameters.Circuit]).zfill(3)}"
            for _, row in df.iterrows()]

    return [f"{row[ent.BuildingModelParameters.Building_Number]}" for _, row in df.iterrows()]
