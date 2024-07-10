import os as _os
import pathlib as _pl
import re as _re
import subprocess as _sp
import sys
import typing as _tp
import unittest as _ut

import pytest as _pt

import optihood as oh
from tests.xls_helpers import compare_xls_files

sys.path.append(str(_pl.Path(oh.__file__).resolve().parent / ".." / "data" / "examples"))
from basic_example import plot_sankey_diagram

cwd = _os.getcwd()
packageDir = _pl.Path(oh.__file__).resolve().parent
scriptDir = packageDir / ".." / "data" / "examples"
example_path = packageDir / ".." / "data" / "results"
expected_data_dir = _pl.Path(__file__).resolve().parent / "expected_files"
test_results_dir = packageDir / ".." / "results"

_SHEET_NAMES = ['naturalGasBus__Building1', 'gridBus__Building1', 'electricityBus__Building1',
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


def compare_html_files(testCase, file_path, file_path_expected, desired_uuid: _tp.Optional[str] = None):
    with open(file_path, encoding="utf8") as f1, open(file_path_expected, encoding="utf8") as f2:
        contents1 = list(f1)
        contents2 = list(f2)
        if desired_uuid:
            contents1 = replace_uuid(contents1, desired_uuid)
        _ut.TestCase.assertListEqual(testCase, contents1[1::], contents2[1::])


def replace_uuid(html_text, desired_uuid: str, html_part: int = 61):
    find = _re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
    html_text[html_part] = find.sub(desired_uuid, html_text[html_part])
    return html_text


class TestXlsExamples(_ut.TestCase):
    def setUp(self):
        self.maxDiff = None

    @_pt.mark.skipif(True, reason='waiting for evaluation. needs to be skipped for CI for now.')
    def test_basic_before_merge(self):

        # =============================
        # make into helper
        _os.chdir(scriptDir)
        _sp.run([packageDir / '..' / 'venv' / 'Scripts' / 'python.exe', scriptDir / "basic_example.py", '/H'],
                shell=True, check=True)
        _os.chdir(cwd)
        # =============================

        excel_file_path = str(example_path / "results_basic_example.xls")
        expected_data_path = str(expected_data_dir / "test_run_basic_example.xls")

        compare_xls_files(self, excel_file_path, expected_data_path, _SHEET_NAMES, abs_tolerance=1e-4)

    def test_basic_after_merge(self):
        """ End2End test to ensure user example is reproducible.
            This test will need to be adjusted, as Gurobi doesn't reproduce exact values between computing systems.
        """

        # =============================
        # make into helper
        _os.chdir(scriptDir)
        _sp.run([packageDir / '..' / 'venv' / 'Scripts' / 'python.exe', scriptDir / "basic_example.py", '/H'],
                shell=True, check=True)
        _os.chdir(cwd)
        # =============================

        excel_file_path = str(example_path / "results_basic_example.xlsx")
        expected_data_path = str(expected_data_dir / "test_results_basic_example_after_merge.xls")

        compare_xls_files(self, excel_file_path, expected_data_path, _SHEET_NAMES, abs_tolerance=1e-4)

    @_pt.mark.skip(reason='Waiting for evaluation of merge differences.')
    def test_sankey_basic_example(self):
        """ End2End test to ensure the Sankey diagram of the user example is reproduced.
            This test is deterministic, as it uses a given result.
        """
        optimizationType = "costs"
        resultFileName = "test_run_basic_example.xls"
        plot_sankey_diagram(test_results_dir, 4, optimizationType, resultFileName, expected_data_dir, show_figs=False)
        uuid_expected = "0fbea2e5-8f67-4d21-8fe7-897e199ac035"
        compare_html_files(self, test_results_dir / "Sankey_4_costs.html",
                           expected_data_dir / "test_Sankey_basic_example.html", uuid_expected)

    def test_sankey_basic_example_after_merge(self):
        """ End2End test to ensure the Sankey diagram of the user example is reproduced.
            This test is deterministic, as it uses a given result.
            However, some of the requirements show up as well, so this will likely be very brittle.
            Needs to be adjusted as more fine-grained tests exist.
        """
        optimizationType = "costs"
        resultFileName = "test_run_basic_example.xls"
        plot_sankey_diagram(test_results_dir, 4, optimizationType, resultFileName, expected_data_dir, show_figs=False)
        compare_html_files(self, test_results_dir / "Sankey_4_costs.html",
                           expected_data_dir / "test_Sankey_basic_example_after_merge.html")

    @_pt.mark.skip()
    def test_bokeh_basic_example(self):
        assert False == True

    def test_html_comparison(self):
        """ The html files tend to only differ by a random UUID.
        """
        uuid_expected = "0fbea2e5-8f67-4d21-8fe7-897e199ac035"
        compare_html_files(self, expected_data_dir / "Sankey_4_costs_old_uuid.html",
                           expected_data_dir / "test_Sankey_basic_example.html", uuid_expected)

    @_pt.mark.skip(reason='Manual test to check quality of feedback when comparing xls files.')
    def test_compare_results_before_and_after_merge(self):
        """ Used to show the quality of feedback between different xls files.
            These examples also show a change in the optimization results, which needs to be evaluated.
        """
        old_data_path = str(expected_data_dir / "test_run_basic_example.xls")
        new_data_path = str(expected_data_dir / "test_results_basic_example_after_merge.xls")
        compare_xls_files(self, new_data_path, old_data_path, _SHEET_NAMES, abs_tolerance=1e-4, manual_test=True)


if __name__ == '__main__':
    _ut.main()
