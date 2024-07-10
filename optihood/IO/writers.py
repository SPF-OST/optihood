import abc as _abc
import dataclasses as _dc
import pathlib as _pl

import pandas as _pd

import optihood.IO.groupScenarioWriter as _gsw
import typing as _tp

import optihood.IO.individualScenarioWriter as _isw


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
            self.get_scenario = self.get_grouped_scenario
        elif self.version == 'individual':
            self.get_scenario = self.get_individual_scenario

    def get_grouped_scenario(self):
        # refactor to remove excel file input
        data = _gsw.create_scenario_file(self.config_file_path, self.config_file_path, self.nr_of_buildings, writeToFileOrReturnData='data')
        return data

    def get_individual_scenario(self):
        # refactor to remove excel file input
        data = _isw.create_scenario_file(self.config_file_path, self.config_file_path, self.building_nrs, self.nr_of_buildings, writeToFileOrReturnData='data')
        return data

    @_abc.abstractmethod
    def write_scenario_to_file(self, file_path: _pl.Path) -> None:
        pass

    def write(self, file_path: _pl.Path) -> None:
        self.data = self.get_scenario()
        self.write_scenario_to_file(file_path)


class ScenarioFileWriterExcel(ScenarioCreator):
    def write_scenario_to_file(self, file_path: _pl.Path) -> None:
        # maybe this can be inlined?
        write_prepared_data_and_sheets_to_excel(file_path, self.data)


def write_prepared_data_and_sheets_to_excel(excel_file_path: _pl.Path, excel_data: dict):
    # better to use pathlib paths.
    with _pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
        for sheet, data in excel_data.items():
            data.to_excel(writer, sheet_name=sheet, index=False)
