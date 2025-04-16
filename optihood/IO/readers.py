import configparser as _cp
import dataclasses as _dc
import pathlib as _pl

import pandas as _pd

import optihood.entities as _ent


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
    def make_nrs_numeric_current(df: _pd.DataFrame, column_name: str):
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
        paths = _ent.CsvInputFilePathsRelative
        self.relative_file_paths = {
            _ent.NodeKeys.buses: paths.buses,
            _ent.NodeKeys.grid_connection: paths.grid_connection,
            _ent.NodeKeys.commodity_sources: paths.commodity_sources,
            _ent.NodeKeys.solar: paths.solar,
            _ent.NodeKeys.transformers: paths.transformers,
            _ent.NodeKeys.demand: paths.demand,
            _ent.NodeKeys.storages: paths.storages,
            _ent.NodeKeys.stratified_storage: paths.stratified_storage,
            _ent.NodeKeys.profiles: paths.profiles,
            _ent.NodeKeys.links: paths.links,
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
                if not key == _ent.NodeKeys.links:
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
