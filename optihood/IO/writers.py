import abc as _abc
import dataclasses as _dc
import pathlib as _pl
import typing as _tp

import pandas as _pd

import optihood.IO.groupScenarioWriter as _gsw
import optihood.IO.individualScenarioWriter as _isw
import optihood.entities as _ent


@_dc.dataclass()
class ScenarioCreator:
    """ Can be used to get data directly without writing to file using 'ScenarioCreator.get_scenario()'.
        The building_nrs are only used for the individual scenarios.
    """
    config_file_path: _pl.Path
    version: _tp.Literal['grouped', 'individual']
    nr_of_buildings: int = 1
    building_nrs: int = 0
    data: dict[str, _pd.DataFrame] = _dc.field(init=False)

    def __post_init__(self):
        if self.version == 'grouped':
            self.get_scenario = self._get_grouped_scenario
        elif self.version == 'individual':
            self.get_scenario = self._get_individual_scenario

    def _get_grouped_scenario(self):
        data = _gsw.create_scenario_file(self.config_file_path, self.nr_of_buildings)
        return data

    def _get_individual_scenario(self):
        data = _isw.create_scenario_file(self.config_file_path, self.building_nrs, self.nr_of_buildings)
        return data

    @_abc.abstractmethod
    def _write_scenario_to_file(self, file_path: _pl.Path) -> None:
        pass

    def write(self, file_path: _pl.Path) -> None:
        self.data = self.get_scenario()
        self._write_scenario_to_file(file_path)


class ScenarioFileWriterExcel(ScenarioCreator):
    def _write_scenario_to_file(self, file_path: _pl.Path) -> None:
        write_prepared_data_and_sheets_to_excel(file_path, self.data)


class ScenarioFileWriterCSV(ScenarioCreator):
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

    def _write_scenario_to_file(self, folder_path: _pl.Path) -> None:
        for key, sheet in self.data.items():
            file_path = folder_path / self.relative_file_paths[key]
            write_to_csv(file_path, sheet)


def write_prepared_data_and_sheets_to_excel(excel_file_path: _pl.Path, excel_data: dict):
    # maybe this can be inlined?
    with _pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
        for sheet, data in excel_data.items():
            data.to_excel(writer, sheet_name=sheet, index=False)


def write_to_csv(file_path: _pl.Path, data_sheet: _pd.DataFrame) -> None:
    data_sheet.to_csv(file_path, index=False)
