import os as _os
import pathlib as _pl
import pytest as _pt
import unittest as _ut
import subprocess as _sp

import optihood as _oh
from tests.xls_helpers import compare_xls_files, compare_txt_files

cwd = _os.getcwd()
packageDir = _pl.Path(_oh.__file__).resolve().parent
scriptDir = packageDir / ".." / "data" / "examples"
example_path = packageDir / ".." / "data" / "results" / "HP_GS_PV" / "cost" / "group"
expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"

_SHEET_NAMES = ['gridBus__Building1', 'electricityProdBus__Building1', 'electricityInBus', 'shDemandBus',
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


class TestConfigExamples(_ut.TestCase):
    # def setUp(self):
    #     self.maxDiff = None

    @_pt.mark.skipif(True, reason='waiting for evaluation. needs to be skipped for CI for now.')
    def test_group_optimization_before_merge(self):
        """
            End2End test to maximize initial coverage.
            Issue with results ordering solved with a temporary hack
        """

        # =============================
        # make into helper
        _os.chdir(scriptDir)
        _sp.run([packageDir / '..' / 'venv' / 'Scripts' / 'python.exe', scriptDir / "run_example_config.py"],
                shell=True, check=True)
        _os.chdir(cwd)
        # =============================

        excel_file_path = str(example_path / "scenario_HP_GS_PV.xls")
        expected_data_path = str(expected_data_dir / "test_run_example_config.xls")

        compare_xls_files(self, excel_file_path, expected_data_path, _SHEET_NAMES, manual_test=True)

    def test_group_optimization_after_merge(self):
        """
            Very flaky test, which was not the case before!
            End2End test to maximize initial coverage.
            Issue with results ordering solved with a temporary hack
        """

        # =============================
        # make into helper
        _os.chdir(scriptDir)
        _sp.run([packageDir / '..' / 'venv' / 'Scripts' / 'python.exe', scriptDir / "run_example_config.py"],
                shell=True, check=True)
        _os.chdir(cwd)
        # =============================

        excel_file_path = example_path / "scenario_HP_GS_PV.xls"
        assert excel_file_path.is_file()
        # expected_data_path = str(expected_data_dir / "test_run_example_config_after_merge.xls")

        # compare_xls_files(self, str(excel_file_path), expected_data_path, _SHEET_NAMES, manual_test=True, abs_tolerance=1e-4)

    @_pt.mark.skip(reason='Manual test to check quality of feedback when comparing xls files.')
    def test_compare_results_before_and_after_merge(self):
        """ Used to show the quality of feedback between different xls files.
            These examples also show a change in the optimization results, which needs to be evaluated.
        """
        old_data_path = str(expected_data_dir / "test_run_example_config.xls")
        new_data_path = str(expected_data_dir / "test_run_example_config_after_merge.xls")
        compare_xls_files(self, new_data_path, old_data_path, _SHEET_NAMES, abs_tolerance=1e-4, manual_test=True)

    @_pt.mark.skip(reason='Manual test to show differences between old and new metadata.')
    def test_compare_meta_data_results_before_and_after_merge(self):
        """ Currently, this does not provide quality feedback.
            Often, pycharm can open a diff window for the test.
            This is not the case for this comparison, however.
         """
        old_data_path = _pl.Path(cwd) / "config_results_metadata_old.txt"
        new_data_path = _pl.Path(cwd) / "config_results_metadata_new.txt"
        compare_txt_files(self, old_data_path, new_data_path)


# Reasonable comparison values for:
# - Investment Costs for the system: 0.1 CHF
# - Operation Costs for the system: 1 CHF
# - Feed In Costs for the system: absolute
# - Total Costs for the system: 1 CHF
# - Environmental impact from input resources for the system: 5 kg CO2 eq
# - Environmental impact from energy conversion technologies for the system: 0.1 kg CO2 eq
# - Total: 5 kg CO2 eq


if __name__ == '__main__':
    _ut.main()
