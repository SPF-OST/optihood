import pathlib as _pl
import unittest as _ut

import pandas as _pd

import optihood as _oh
import optihood.IO.writers as _wr

_SHEET_NAMES = [
            "buses",
            "grid_connection",
            "commodity_sources",
            "solar",
            "transformers",
            "demand",
            "storages",
            "stratified_storage",
            "profiles",
        ]


class TestGroupScenarioWriter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_create_scenario_file(self):
        """
        End2end test to allow refactoring.
        In the future, this test shouldn't touch the file system.

        Checks whether the expected xls file is created when providing the config file.
        """
        packageDir = _pl.Path(_oh.__file__).resolve().parent
        config_file_path = (
            packageDir / ".." / "data" / "configs" / "basic_example_config" / "scenario_HP_GS_PV_group.ini"
        )
        excel_file_path = _pl.Path("test_group_scenario_writer.xls")
        expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
        expected_data_path = str(expected_data_dir / "test_group_scenario_writer.xls")

        scenarioFileWriter = _wr.ScenarioFileWriterExcel(config_file_path, nr_of_buildings=4, version="grouped")
        scenarioFileWriter.write(excel_file_path)

        data = _pd.ExcelFile(str(excel_file_path))
        expected_data = _pd.ExcelFile(expected_data_path)

        for sheet in _SHEET_NAMES:
            _pd.testing.assert_frame_equal(data.parse(sheet), expected_data.parse(sheet))


class TestIndividualScenarioWriter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_create_scenario_file(self):
        """
        End2end test to allow refactoring.
        In the future, this test shouldn't touch the file system.

        Checks whether the expected xls file is created when providing the config file.
        """
        packageDir = _pl.Path(_oh.__file__).resolve().parent
        config_file_path = (
            packageDir / ".." / "data" / "configs" / "basic_example_config" / "scenario_HP_GS_PV_indiv.ini"
        )
        excel_file_path = _pl.Path("test_individual_scenario_writer.xls")
        expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
        expected_data_path = str(expected_data_dir / "test_individual_scenario_writer.xls")

        scenarioFileWriter = _wr.ScenarioFileWriterExcel(config_file_path, building_nrs=0, version="individual")
        scenarioFileWriter.write(excel_file_path)

        data = _pd.ExcelFile(str(excel_file_path))
        expected_data = _pd.ExcelFile(expected_data_path)

        for sheet in _SHEET_NAMES:
            _pd.testing.assert_frame_equal(data.parse(sheet), expected_data.parse(sheet))


if __name__ == "__main__":
    _ut.main()
