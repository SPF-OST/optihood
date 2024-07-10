import pathlib as _pl
import unittest as _ut

import pandas as _pd

import optihood as _oh
import optihood.IO.writers as _wr
from optihood.IO.readers import CsvScenarioReader

_package_dir = _pl.Path(_oh.__file__).resolve().parent
_test_results_dir = _package_dir / ".." / "test-results"

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


def ensure_directory_exists(dir_path: _pl.Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)


class TestGroupScenarioWriters(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_create_scenario_file_excel(self):
        """
        End2end test to allow refactoring.
        In the future, this test shouldn't touch the file system.

        Checks whether the expected xls file is created when providing the config file.
        """
        config_file_path = (
            _package_dir / ".." / "data" / "configs" / "basic_example_config" / "scenario_HP_GS_PV_group.ini"
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

    def test_create_scenario_files_csv(self):
        """
        End2end test to allow refactoring.
        In the future, this test shouldn't touch the file system.

        Checks whether the expected csv files are created when providing the config file.
        """

        config_file_path = (
            _package_dir / ".." / "data" / "configs" / "basic_example_config" / "scenario_HP_GS_PV_group.ini"
        )
        csv_folder_path = _test_results_dir / "group_csvs"
        ensure_directory_exists(csv_folder_path)
        # expected_csv_folder_path = packageDir / ".." / "data" / "CSVs" / "basic_example_CSVs"
        expected_csv_folder_path = _pl.Path(__file__).resolve().parent / "expected_files" / "group_csvs"

        scenarioFileWriter = _wr.ScenarioFileWriterCSV(config_file_path, nr_of_buildings=4, version="grouped")
        scenarioFileWriter.write(csv_folder_path)

        csvScenarioReader = CsvScenarioReader(csv_folder_path)
        data = csvScenarioReader.read_scenario()

        csvScenarioReader_expected = CsvScenarioReader(expected_csv_folder_path)
        expected_data = csvScenarioReader_expected.read_scenario()

        errors = []
        for sheet in _SHEET_NAMES:
            try:
                _pd.testing.assert_frame_equal(data[sheet], expected_data[sheet])
            except AssertionError as e:
                errors.append(e)

        if errors:
            raise ExceptionGroup(f"Found {len(errors)} errors.", errors)


class TestIndividualScenarioWriter(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_create_scenario_file_excel(self):
        """
        End2end test to allow refactoring.
        In the future, this test shouldn't touch the file system.

        Checks whether the expected xls file is created when providing the config file.
        """
        config_file_path = (
            _package_dir / ".." / "data" / "configs" / "basic_example_config" / "scenario_HP_GS_PV_indiv.ini"
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

    def test_create_scenario_files_csv(self):
        """
        End2end test to allow refactoring.
        In the future, this test shouldn't touch the file system.

        Checks whether the expected csv files are created when providing the config file.
        """

        config_file_path = (
            _package_dir / ".." / "data" / "configs" / "basic_example_config" / "scenario_HP_GS_PV_indiv.ini"
        )
        csv_folder_path = _test_results_dir / "individual_csvs"
        ensure_directory_exists(csv_folder_path)
        expected_csv_folder_path = _pl.Path(__file__).resolve().parent / "expected_files" / "individual_csvs"

        scenarioFileWriter = _wr.ScenarioFileWriterCSV(config_file_path, building_nrs=0, version="individual")
        scenarioFileWriter.write(csv_folder_path)

        csvScenarioReader = CsvScenarioReader(csv_folder_path)
        data = csvScenarioReader.read_scenario()

        csvScenarioReader_expected = CsvScenarioReader(expected_csv_folder_path)
        expected_data = csvScenarioReader_expected.read_scenario()

        errors = []
        for sheet in _SHEET_NAMES:
            try:
                _pd.testing.assert_frame_equal(data[sheet], expected_data[sheet])
            except AssertionError as e:
                errors.append(e)

        if errors:
            raise ExceptionGroup(f"Found {len(errors)} errors.", errors)


if __name__ == "__main__":
    _ut.main()
