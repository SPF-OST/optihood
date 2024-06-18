import os as _os
import pandas as _pd
import pathlib as _pl
import unittest

import optihood as _oh
import sys
sys.path.append(str(_pl.Path(_oh.__file__).resolve().parent / ".." / "data" / "examples"))
from basic_example import run_example


class TestXlsExamples(unittest.TestCase):
    def test_basic(self):
        cwd = _os.getcwd()
        packageDir = _pl.Path(_oh.__file__).resolve().parent
        scriptDir = packageDir / ".." / "data" / "examples"
        example_path = packageDir / ".." / "data" / "results"

        _os.chdir(scriptDir)
        print("")
        print(_os.getcwd())
        print("")
        # run_example()
        _os.chdir(cwd)

        excel_file_path = str(example_path / "results_basic_example.xlsx")
        expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
        expected_data_path = str(expected_data_dir / "test_run_example_xls.xls")

        sheet_names = ['buses', 'grid_connection', 'commodity_sources', 'solar', 'transformers', 'demand', 'storages', 'stratified_storage', 'profiles']

        data = _pd.ExcelFile(excel_file_path)

        expected_data = _pd.ExcelFile(expected_data_path)

        for sheet in sheet_names:
            _pd.testing.assert_frame_equal(data.parse(sheet), expected_data.parse(sheet))


if __name__ == '__main__':
    unittest.main()
