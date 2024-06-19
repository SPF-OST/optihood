import os as _os
import pandas as _pd
import pathlib as _pl
import sys
import unittest

import optihood as _oh

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
        run_example(show_plots=False)
        _os.chdir(cwd)

        excel_file_path = str(example_path / "results_basic_example.xls")
        expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
        expected_data_path = str(expected_data_dir / "test_run_basic_example.xls")

        sheet_names = ['naturalGasBus__Building1', 'gridBus__Building1', 'electricityBus__Building1',
                       'electricityProdBus__Building1', 'electricityInBus__Building1', 'shSourceBus__Building1',
                       'spaceHeatingBus__Building1', 'shDemandBus__Building1', 'domesticHotWaterBus__Building1',
                       'dhwDemandBus__Building1', 'solarConnectBus__Building1', 'naturalGasBus__Building2',
                       'gridBus__Building2', 'electricityBus__Building2', 'electricityProdBus__Building2',
                       'electricityInBus__Building2', 'shSourceBus__Building2', 'spaceHeatingBus__Building2',
                       'shDemandBus__Building2', 'domesticHotWaterBus__Building2', 'dhwDemandBus__Building2',
                       'solarConnectBus__Building2', 'naturalGasBus__Building3', 'gridBus__Building3',
                       'electricityBus__Building3', 'electricityProdBus__Building3', 'electricityInBus__Building3',
                       'shSourceBus__Building3', 'spaceHeatingBus__Building3', 'shDemandBus__Building3',
                       'domesticHotWaterBus__Building3', 'dhwDemandBus__Building3', 'solarConnectBus__Building3',
                       'naturalGasBus__Building4', 'gridBus__Building4', 'electricityBus__Building4',
                       'electricityProdBus__Building4', 'electricityInBus__Building4', 'shSourceBus__Building4',
                       'spaceHeatingBus__Building4', 'shDemandBus__Building4', 'domesticHotWaterBus__Building4',
                       'dhwDemandBus__Building4', 'solarConnectBus__Building4', 'costs__Building1',
                       'env_impacts__Building1', 'capStorages__Building1', 'capTransformers__Building1',
                       'costs__Building2', 'env_impacts__Building2', 'capStorages__Building2',
                       'capTransformers__Building2', 'costs__Building3', 'env_impacts__Building3',
                       'capStorages__Building3', 'capTransformers__Building3', 'costs__Building4',
                       'env_impacts__Building4', 'capStorages__Building4', 'capTransformers__Building4']

        data = _pd.ExcelFile(excel_file_path)

        expected_data = _pd.ExcelFile(expected_data_path)

        for sheet in sheet_names:
            print("")
            print(sheet)
            print("")
            df_new = data.parse(sheet)
            df_expected = expected_data.parse(sheet)

            try:
                _pd.testing.assert_frame_equal(df_new, df_expected)
            except AssertionError as ae:
                # Optihood doesn't export the results in a consistent way.
                # Therefore, this hack reorders the results.
                # Instead, the export should be ordered consistently.

                df_new = df_new.sort_values(by=[df_new.columns[0]], ignore_index=True)
                df_expected = df_expected.sort_values(by=[df_new.columns[0]], ignore_index=True)
                _pd.testing.assert_frame_equal(df_new, df_expected)


if __name__ == '__main__':
    unittest.main()
