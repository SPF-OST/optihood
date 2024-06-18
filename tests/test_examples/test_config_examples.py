import os as _os
import pandas as _pd
import pathlib as _pl
import unittest

import optihood as _oh
import sys

sys.path.append(str(_pl.Path(_oh.__file__).resolve().parent / ".." / "data" / "examples"))
from run_example_config import run_config_example


class TestConfigExamples(unittest.TestCase):
    def test_group_optimization(self):
        cwd = _os.getcwd()
        packageDir = _pl.Path(_oh.__file__).resolve().parent
        scriptDir = packageDir / ".." / "data" / "examples"

        _os.chdir(scriptDir)
        print("")
        print(_os.getcwd())
        print("")

        run_config_example()

        _os.chdir(cwd)

        example_path = packageDir / ".." / "data" / "results" / "HP_GS_PV" / "cost" / "group"
        # example_path = "C:\\Users\\alex.hobe\\Projects\\optihood\\data\\results\\HP_GS_PV\\cost\\group"
        excel_file_path = str(example_path / "scenario_HP_GS_PV.xls")
        # excel_file_path = "C:\\Users\\alex.hobe\\Projects\\optihood\\data\\results\\HP_GS_PV\\cost\\group\scenario_HP_GS_PV.xls"
        expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
        expected_data_path = str(expected_data_dir / "test_run_example_config.xls")

        sheet_names = ['gridBus__Building1', 'electricityProdBus__Building1', 'electricityInBus', 'shDemandBus',
                       'dhwDemandBus', 'shSourceBus__Building1', 'dhwStorageBus__Building1', 'electricityBus',
                       'spaceHeatingBus', 'domesticHotWaterBus', 'gridBus__Building2', 'electricityProdBus__Building2',
                       'shSourceBus__Building2', 'dhwStorageBus__Building2', 'gridBus__Building3',
                       'electricityProdBus__Building3', 'shSourceBus__Building3', 'dhwStorageBus__Building3',
                       'gridBus__Building4', 'electricityProdBus__Building4', 'shSourceBus__Building4',
                       'dhwStorageBus__Building4', 'costs__Building1', 'env_impacts__Building1',
                       'capStorages__Building1', 'capTransformers__Building1', 'costs__Building2',
                       'env_impacts__Building2', 'capStorages__Building2', 'capTransformers__Building2',
                       'costs__Building3', 'env_impacts__Building3', 'capStorages__Building3',
                       'capTransformers__Building3', 'costs__Building4', 'env_impacts__Building4',
                       'capStorages__Building4', 'capTransformers__Building4']

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
