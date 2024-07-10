import pandas as _pd
import pathlib as _pl

import unittest as _ut

import optihood as _oh

from optihood.IO import groupScenarioWriter as _gsw
from optihood.IO import individualScenarioWriter as _isw
import optihood.IO.writers as _wr


class TestGroupScenarioWriter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_create_scenario_file(self):
        """
        End2end test to allow refactoring.
        In the future, this test shouldn't touch the file system.
        The argument writeToFileOrReturnData='data' is a preparation for this step.

        Checks whether the expected xls file is created when providing the config file.
        """
        packageDir = _pl.Path(_oh.__file__).resolve().parent
        config_file_path = packageDir / ".." / "data" / "configs" / "basic_example_config" / "scenario_HP_GS_PV_group.ini"
        excel_file_path = "test_group_scenario_writer.xls"
        expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
        expected_data_path = str(expected_data_dir / "test_group_scenario_writer.xls")

        sheet_names = ['buses', 'grid_connection', 'commodity_sources', 'solar', 'transformers', 'demand', 'storages', 'stratified_storage', 'profiles']

        scenarioFileWriter = _wr.ScenarioFileWriterExcel(config_file_path, nr_of_buildings=4, version='grouped')
        scenarioFileWriter.write(excel_file_path)

        data = _pd.ExcelFile(excel_file_path)
        expected_data = _pd.ExcelFile(expected_data_path)

        for sheet in sheet_names:
            _pd.testing.assert_frame_equal(data.parse(sheet), expected_data.parse(sheet))


class TestIndividualScenarioWriter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_create_scenario_file(self):
        """
        End2end test to allow refactoring.
        In the future, this test shouldn't touch the file system.
        The argument writeToFileOrReturnData='data' is a preparation for this step.

        Checks whether the expected xls file is created when providing the config file.
        """
        packageDir = _pl.Path(_oh.__file__).resolve().parent
        config_file_path = packageDir / ".." / "data" / "configs" / "basic_example_config" / "scenario_HP_GS_PV_indiv.ini"
        excel_file_path = _pl.Path("test_individual_scenario_writer.xls")
        expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
        expected_data_path = str(expected_data_dir / "test_individual_scenario_writer.xls")

        sheet_names = ['buses', 'grid_connection', 'commodity_sources', 'solar', 'transformers', 'demand', 'storages', 'stratified_storage', 'profiles']

        scenarioFileWriter = _wr.ScenarioFileWriterExcel(config_file_path, building_nrs=0, version='individual')
        scenarioFileWriter.write(excel_file_path)

        data = _pd.ExcelFile(str(excel_file_path))
        expected_data = _pd.ExcelFile(expected_data_path)

        for sheet in sheet_names:
            _pd.testing.assert_frame_equal(data.parse(sheet), expected_data.parse(sheet))


if __name__ == '__main__':
    _ut.main()
