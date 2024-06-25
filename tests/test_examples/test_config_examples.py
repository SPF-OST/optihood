import os as _os
import pathlib as _pl
import pytest as _pt
import unittest as _ut
import subprocess as _sp

import optihood as _oh
from tests.xls_helpers import compare_xls_files


@_pt.mark.skip(reason='Waiting for evaluation of changes.')
class TestConfigExamples(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_group_optimization(self):
        """
            End2End test to maximize initial coverage.
            Issue with results ordering solved with a temporary hack
        """
        cwd = _os.getcwd()
        packageDir = _pl.Path(_oh.__file__).resolve().parent
        scriptDir = packageDir / ".." / "data" / "examples"

        # =============================
        # make into helper
        _os.chdir(scriptDir)
        _sp.run([packageDir / '..' / 'venv' / 'Scripts' / 'python.exe', scriptDir / "run_example_config.py"], shell=True, check=True)
        _os.chdir(cwd)
        # =============================

        example_path = packageDir / ".." / "data" / "results" / "HP_GS_PV" / "cost" / "group"
        excel_file_path = str(example_path / "scenario_HP_GS_PV.xls")
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

        compare_xls_files(self, excel_file_path, expected_data_path, sheet_names, manual_test=True) #, abs_tolerance=1e-4)


if __name__ == '__main__':
    _ut.main()
