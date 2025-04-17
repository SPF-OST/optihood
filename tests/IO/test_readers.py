import pathlib as _pl
import unittest as _ut

import pandas as _pd

import optihood as oh
import optihood.IO.readers as ior
import optihood.energy_network as en
import optihood.entities as ent
import optihood.IO.writers as wr
from tests.xls_helpers import check_assertion, check_dataframe_assertion

package_dir = _pl.Path(oh.__file__).resolve().parent
_CSV_DIR_PATH = package_dir / ".." / "data" / "CSVs" / "basic_example_CSVs"
_input_data_dir = package_dir / ".." / "data" / "excels" / "basic_example"
_input_data_path = str(_input_data_dir / "scenario.xls")


class TestCsvScenarioReader(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

        network = en.EnergyNetworkClass(None)
        data = _pd.ExcelFile(_input_data_path)
        self.expected_nodal_data = network.get_nodal_data_from_Excel(data)
        data.close()

    def test_read(self):
        """Test to ensure new reader produces 'identical' inputs to optihood."""
        csvReader = ior.CsvScenarioReader(_CSV_DIR_PATH, "current")
        nodal_data = csvReader.read_scenario()

        errors = []

        check_assertion(self, errors, nodal_data.keys(), self.expected_nodal_data.keys())

        for key, df_current in nodal_data.items():
            # check_dtype=False to simplify comparison between Excel and CSV files.
            check_dataframe_assertion(errors, df_current, self.expected_nodal_data[key], check_dtype=False)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)

    def test_read_without_future_warning(self):
        """Test to ensure new reader produces 'identical' inputs to optihood."""
        csvReader = ior.CsvScenarioReader(_CSV_DIR_PATH)
        nodal_data = csvReader.read_scenario()

        errors = []

        check_assertion(self, errors, nodal_data.keys(), self.expected_nodal_data.keys())

        for key, df_current in nodal_data.items():
            # check_dtype=False to simplify comparison between Excel and CSV files.
            check_dataframe_assertion(errors, df_current, self.expected_nodal_data[key], check_dtype=False)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)

    def test_get_unique_labels(self):
        df = _pd.DataFrame({ent.CommonLabels.label: ["a", "a", "b", "c"],
                            ent.CommonLabels.building: ["1", "2", "1", "1"],
                            })
        results = ior.get_unique_labels(df)
        self.assertListEqual(results, ['a__B001', 'a__B002', 'b__B001', 'c__B001'])

    def test_get_unique_buses(self):
        df = _pd.DataFrame({ent.CommonLabels.to: ["a", "a,b", "b,d,e", "c"],
                            ent.CommonLabels.building: ["1", "2", "1", "1"],
                            })
        results = ior.get_unique_buses(df, ent.CommonLabels.to)
        self.assertListEqual(results, [['a__B001'],
                                       ['a__B002', 'b__B002'],
                                       ['b__B001', 'd__B001', 'e__B001'],
                                       ['c__B001']])

    def test_add_unique_label_columns(self):
        csvReader = ior.CsvScenarioReader(_CSV_DIR_PATH)
        nodal_data = csvReader.read_scenario()

        nodal_data_with_unique_labels = ior.add_unique_label_columns(nodal_data)

        expected_files_path = _pl.Path(__file__).parent / "expected_files" / "without_building_csvs"
        # writer = wr.ScenarioFileWriterCSV("irrelevant", "individual")
        # writer.data = nodal_data_with_unique_labels
        # writer._write_scenario_to_file(expected_files_path)

        csvReader = ior.CsvScenarioReader(expected_files_path)
        expected_data = csvReader.read_scenario()



        errors = []

        check_assertion(self, errors, nodal_data_with_unique_labels.keys(), expected_data.keys())

        for key, df_current in nodal_data_with_unique_labels.items():
            # check_dtype=False to simplify comparison between Excel and CSV files.
            df_current.equals(expected_data[key])

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)

        # TODO: check against CSVs.


        # TODO: deal with reading building_model_parameters
        # TODO: deal with unique labels and unique buildings in tests.
