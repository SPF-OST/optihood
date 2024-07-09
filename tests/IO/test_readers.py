import pathlib as _pl
import unittest as _ut

import pandas as _pd

import optihood as _oh
import optihood.IO.readers as _ior
import optihood.energy_network as _en
from tests.xls_helpers import check_assertion, check_dataframe_assertion

package_dir = _pl.Path(_oh.__file__).resolve().parent
_CSV_DIR_PATH = package_dir / ".." / "data" / "CSVs" / "basic_example_CSVs"
_input_data_dir = package_dir / ".." / "data" / "excels" / "basic_example"
_input_data_path = str(_input_data_dir / "scenario.xls")


class TestCsvScenarioReader(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

        network = _en.EnergyNetworkClass(None)
        data = _pd.ExcelFile(_input_data_path)
        self.expected_nodal_data = network.get_nodal_data_from_Excel(data)
        data.close()

    def test_read(self):
        """Test to ensure new reader produces 'similar' inputs to optihood."""
        csvReader = _ior.CsvScenarioReader(_CSV_DIR_PATH)
        nodal_data = csvReader.read_scenario()

        errors = []

        check_assertion(self, errors, nodal_data.keys(), self.expected_nodal_data.keys())

        for key, df_current in nodal_data.items():
            # check_dtype=False to simplify comparison between Excel and CSV files.
            check_dataframe_assertion(errors, df_current, self.expected_nodal_data[key], check_dtype=False)

        if errors:
            raise ExceptionGroup(f"found {len(errors)} errors", errors)
